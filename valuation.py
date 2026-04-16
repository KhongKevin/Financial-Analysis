import pandas as pd
import matplotlib.pyplot as plt
import os
import urllib.request
import io
from datetime import datetime, timedelta
import numpy as np

def _get_price_data(ticker, years):
    """
    Get price data from Yahoo Finance via finance_plots.
    """
    from finance_plots import _get_price_data_yahoo
    return _get_price_data_yahoo(ticker, years=years)


def load_manual_eps(filename="DATA/EPS_manual.txt"):
    """
    Parse EPS_manual.txt into a dict of {ticker: DataFrame(date, eps)}
    """
    eps_data = {}
    current_ticker = None
    rows = []

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line == "END":
                if current_ticker and rows:
                    df = pd.DataFrame(rows, columns=["Date", "EPS"])
                    df["Date"] = pd.to_datetime(df["Date"])
                    df["EPS"] = df["EPS"].replace(r"[\$,]", "", regex=True).astype(float)
                    # Deduplicate by Date (keep latest/last)
                    df = df.sort_values("Date").drop_duplicates("Date", keep="last")
                    df = df.set_index("Date").sort_index()
                    eps_data[current_ticker] = df
                current_ticker, rows = None, []
                continue
            if line.isalpha():
                current_ticker = line.strip()
                rows = []
            else:
                parts = line.split()
                if len(parts) >= 2:
                    date = parts[0]
                    eps = parts[1]
                    rows.append([date, eps])
    return eps_data


def value_PE_min_max(ticker, years=1, filename="DATA/EPS_manual.txt"):
    """
    Calculate a valuation score for a stock based on how high/low the current P/E is
    compared to the past N years.

    Parameters
    ----------
    ticker : str
        Stock ticker (must exist in EPS_manual.txt).
    years : int
        Lookback period (e.g., 1 for 1-year, 5 for 5-year).
    filename : str
        Path to EPS_manual.txt file.

    Returns
    -------
    score : float
        Score between 0 (worst/highest P/E) and 1 (best/lowest P/E).
    current_pe : float
        Current P/E ratio.
    pe_history : pd.Series
        Historical P/E ratios over the lookback window.
    """

    eps_data = load_manual_eps(filename)

    if ticker not in eps_data:
        raise ValueError(f"{ticker} not found in {filename}")

    df_eps = eps_data[ticker].copy().sort_index()
    df_eps["TTM_EPS"] = df_eps["EPS"].rolling(4).sum()

    # --- Get stock price history ---
    df_price = _get_price_data(ticker, years)
    
    if df_price.empty:
        raise ValueError(f"No price data found for {ticker}")

    # Make indices tz-naive
    if isinstance(df_price.index, pd.DatetimeIndex) and df_price.index.tz is not None:
        df_price.index = df_price.index.tz_localize(None)
    if isinstance(df_eps.index, pd.DatetimeIndex) and df_eps.index.tz is not None:
        df_eps.index = df_eps.index.tz_localize(None)

    # Align and compute P/E
    df = df_price.join(df_eps["TTM_EPS"], how="left").ffill()
    df["PE"] = df["Close"] / df["TTM_EPS"]

    # Lookback window
    cutoff = df.index.max() - pd.DateOffset(years=years)
    df_window = df[df.index >= cutoff].dropna()

    if df_window.empty:
        raise ValueError(f"Not enough EPS/price data for {ticker} over {years} years")

    # Current P/E
    current_pe = df_window["PE"].iloc[-1]

    # Historical P/E
    pe_history = df_window["PE"]
    min_pe, max_pe = pe_history.min(), pe_history.max()

    # Score: normalize between min (best) and max (worst)
    if max_pe == min_pe:
        score = 0.5
    else:
        score = 1 - (current_pe - min_pe) / (max_pe - min_pe)
        score = max(0, min(1, score))

    return score, current_pe, pe_history


def value_PE_avg(ticker, years=1, filename="DATA/EPS_manual.txt"):
    """
    Calculate a valuation score for a stock based on how high/low the current P/E is
    compared to the past N years.

    Parameters
    ----------
    ticker : str
        Stock ticker (must exist in EPS_manual.txt).
    years : int
        Lookback period (e.g., 1 for 1-year, 5 for 5-year).
    filename : str
        Path to EPS_manual.txt file.

    Returns
    -------
    score : float
        Score between 0 (worst/highest P/E) and 1 (best/lowest P/E).
    current_pe : float
        Current P/E ratio.
    pe_history : pd.Series
        Historical P/E ratios over the lookback window.
    """
    eps_data = load_manual_eps(filename)
    if ticker not in eps_data:
        raise ValueError(f"{ticker} not found in {filename}")

    df_eps = eps_data[ticker].copy().sort_index()

    # Calculate TTM EPS based on frequency
    # We detect frequency by checking the median gap between dates
    if len(df_eps) >= 2:
        median_gap = pd.Series(df_eps.index).diff().median().days
        if median_gap > 120: # 120 days is roughly > 1 quarter gap
            # Data is ANNUAL/Sparse -> TTM = Current Value
            df_eps["TTM_EPS"] = df_eps["EPS"]
        else:
            # Data is QUARTERLY -> TTM = Sum of last 4
            df_eps["TTM_EPS"] = df_eps["EPS"].rolling(4).sum()
    else:
        df_eps["TTM_EPS"] = df_eps["EPS"]


    # --- Price data ---
    df_price = _get_price_data(ticker, years)
    
    if df_price.empty:
        raise ValueError(f"No price data found for {ticker}")

    # Ensure tz-naive indices
    if isinstance(df_price.index, pd.DatetimeIndex) and df_price.index.tz is not None:
        df_price.index = df_price.index.tz_localize(None)
    if isinstance(df_eps.index, pd.DatetimeIndex) and df_eps.index.tz is not None:
        df_eps.index = df_eps.index.tz_localize(None)

    # Join and compute P/E
    # We use an outer join so we don't lose EPS data that might be older than the price data (typical for new IPOs)
    df = df_price.join(df_eps["TTM_EPS"], how="outer").ffill()
    
    # After ffilling historical EPS forward, we focus only on dates where we have price data
    df = df.loc[df_price.index]
    
    # Compute true current P/E (allowing negatives)
    valid_eps_rows = df.dropna(subset=["TTM_EPS", "Close"])
    if valid_eps_rows.empty:
        raise ValueError(f"Not enough valid P/E data for {ticker}")
    
    latest_eps = valid_eps_rows["TTM_EPS"].iloc[-1]
    latest_price = valid_eps_rows["Close"].iloc[-1]
    true_current_pe = latest_price / latest_eps if latest_eps != 0 else 999.0

    # Compute P/E, ignoring negative or zero earnings strictly for historical averaging and min/max math
    def calc_pe(row):
        eps = row["TTM_EPS"]
        price = row["Close"]
        if pd.isna(eps) or eps <= 0:
            return None # Return None internally for math
        return price / eps

    df["PE"] = df.apply(calc_pe, axis=1)

    # Restrict to lookback window
    current_date = df.index.max()
    cutoff = current_date - pd.DateOffset(years=years)
    df_window = df[df.index >= cutoff].copy()

    # Filter for periods where P/E is valid (company was profitable)
    valid_pe_window = df_window.dropna(subset=["PE"])
    
    if valid_pe_window.empty or latest_eps <= 0:
        # Non-profitable companies get a Baseline Score of 0 (Highest Risk)
        details = {
            "current_pe": true_current_pe,
            "avg_pe": 999.0,
            "min_pe": 999.0,
            "max_pe": 999.0,
            "score_avg": 0.0,
            "score_range": 0.0,
            "data_points": len(df_window),
            "data_gaps": check_data_completeness(ticker, years, filename, "DATA/Balance_manual.txt"),
            "error": "Negative Earnings (Not Profitable)"
        }
        return 0.0, details

    # Stats based ONLY on profitable periods
    min_pe, max_pe = valid_pe_window["PE"].min(), valid_pe_window["PE"].max()
    avg_pe = valid_pe_window["PE"].mean()

    # --- Scoring ---
    # Range-based
    if max_pe == min_pe:
        score_range = 0.5
    else:
        score_range = 1 - (true_current_pe - min_pe) / (max_pe - min_pe)
        score_range = max(0, min(1, score_range))

    # Average-based
    if true_current_pe <= avg_pe:
        score_avg = 0.5 + 0.5 * (avg_pe - true_current_pe) / max(1e-9, avg_pe - min_pe)
    else:
        score_avg = 0.5 - 0.5 * (true_current_pe - avg_pe) / max(1e-9, max_pe - avg_pe)
    score_avg = max(0, min(1, score_avg))

    # Weighted final score
    score = 0.7 * score_avg + 0.3 * score_range

    details = {
        "current_pe": true_current_pe,
        "avg_pe": avg_pe if not pd.isna(avg_pe) else 999.0,
        "min_pe": min_pe if not pd.isna(min_pe) else 999.0,
        "max_pe": max_pe if not pd.isna(max_pe) else 999.0,
        "score_avg": score_avg,
        "score_range": score_range,
        "data_points": len(df_window),
        "data_gaps": check_data_completeness(ticker, years, filename, "DATA/Balance_manual.txt")
    }

    return score, details


def load_manual_balance_sheet(filename="DATA/Balance_manual.txt"):
    """
    Parse Balance_manual.txt into a dict of {ticker: {date: {total_debt, total_equity}}}
    Format:
    TICKER
    2023-12-31	Debt:1000	Equity:500
    END
    """
    data = {}
    if not os.path.exists(filename):
        return data
        
    current_ticker = None
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line == "END":
                current_ticker = None
                continue
            if line.isalpha():
                current_ticker = line
                data[current_ticker] = {}
            else:
                parts = line.split()
                if current_ticker and len(parts) >= 2:
                    date = parts[0]
                    debt = 0
                    equity = 0
                    for p in parts[1:]:
                        if p.startswith("Debt:"):
                            debt = float(p.replace("Debt:", "").replace(",", ""))
                        if p.startswith("Equity:"):
                            equity = float(p.replace("Equity:", "").replace(",", ""))
                    data[current_ticker][date] = {"debt": debt, "equity": equity}
    return data


def check_data_completeness(ticker, years, eps_filename="DATA/EPS_manual.txt", balance_filename="DATA/Balance_manual.txt"):
    """
    Checks if there are gaps in EPS or Balance Sheet data over the last `years` years.
    Returns a list of warning strings.
    """
    gaps = []
    
    # Check EPS
    try:
        eps_data = load_manual_eps(eps_filename)
        if ticker in eps_data:
            df = eps_data[ticker].copy().sort_index()
            if not df.empty:
                max_date = df.index.max()
                cutoff = max_date - pd.DateOffset(years=years)
                df_window = df[df.index >= cutoff]
                
                if df_window.empty:
                    gaps.append(f"Missing all EPS data over the last {years} years")
                else:
                    earlier_df = df[df.index < cutoff]
                    df_check = pd.concat([earlier_df.tail(1), df_window]) if not earlier_df.empty else df_window
                        
                    diffs = df_check.index.to_series().diff()
                    large_gaps = diffs[diffs.dt.days > 120]
                    if not large_gaps.empty:
                        for idx, row in large_gaps.items():
                            prev_date = (idx - row).strftime('%Y-%m')
                            curr_date = idx.strftime('%Y-%m')
                            gaps.append(f"EPS missing: {prev_date} to {curr_date}")
                    
                    if len(df_window) < years * 4 - 2:
                         gaps.append(f"Sparse EPS: Expect {years * 4} qtrs, found {len(df_window)}")
            else:
                gaps.append("EPS data is empty")
        else:
            gaps.append("Missing EPS data entirely")
    except Exception as e:
         pass

    # Check Balance Sheet
    try:
        balance_data = load_manual_balance_sheet(balance_filename)
        if ticker in balance_data:
            dates = sorted([pd.to_datetime(d) for d in balance_data[ticker].keys()])
            if dates:
                max_date = dates[-1]
                cutoff = max_date - pd.DateOffset(years=years)
                recent_dates = [d for d in dates if d >= cutoff]
                
                if len(recent_dates) < years - 1:
                    gaps.append(f"Sparse Balance Sheet: Expect {years} yrs, found {len(recent_dates)}")
            else:
                gaps.append("Balance Sheet data is empty")
        else:
            gaps.append("Missing Balance Sheet data entirely")
    except Exception:
        pass

    return gaps

def score_debt_to_equity(ticker, years=2, filename="DATA/Balance_manual.txt"):
    """
    Calculate Debt-to-Equity score.
    Lower is better.
    """
    balance_data = load_manual_balance_sheet(filename)
    if ticker not in balance_data:
        raise ValueError(f"{ticker} not found in {filename}")
        
    dates = sorted(balance_data[ticker].keys(), reverse=True)
    if not dates:
        raise ValueError(f"No balance sheet data for {ticker}")
        
    current_date = dates[0]
    debt = balance_data[ticker][current_date]["debt"]
    equity = balance_data[ticker][current_date]["equity"]
    
    if equity <= 0:
        ratio = 999.0 # High cap instead of infinity for JSON safety
    else:
        ratio = min(999.0, debt / equity)
        
    # Scoring logic:
    # 0.0 -> 1.0 (Best)
    # 0.5 -> 0.8
    # 1.0 -> 0.6
    # 2.0 -> 0.3
    # 4.0+ -> 0.0
    if ratio <= 0.5:
        score = 0.8 + (0.2 * (0.5 - ratio) / 0.5)
    elif ratio <= 1.5:
        score = 0.5 + (0.3 * (1.5 - ratio) / 1.0)
    elif ratio <= 3.0:
        score = 0.2 + (0.3 * (3.0 - ratio) / 1.5)
    else:
        score = max(0, 0.2 * (5.0 - ratio) / 2.0)
        
    details = {
        "current_ratio": ratio,
        "total_debt": debt,
        "total_equity": equity,
        "date": current_date,
        "score": score,
        "data_gaps": check_data_completeness(ticker, years, "DATA/EPS_manual.txt", filename)
    }
    
    
    return score, details


def calculate_growth_rate(ticker, years=3, filename="DATA/EPS_manual.txt"):
    """
    Calculate the exponential growth rate (CAGR) of EPS using Log-Linear Regression.
    
    Parameters
    ----------
    ticker : str
        Stock ticker.
    years : int
        Number of years to look back.
    filename : str
        Path to EPS data.
        
    Returns
    -------
    growth_rate : float
        Exponential growth rate (e.g., 0.15 for 15%).
        Returns None if not enough data or negative estimates.
    r_squared : float
        R-squared of the fit to measure consistency.
    data_points : int
        Number of data points used.
    """
    eps_data = load_manual_eps(filename)
    if ticker not in eps_data:
        return None, 0, 0
        
    df = eps_data[ticker].copy().sort_index()
    
    # Filter for last N years
    cutoff = df.index.max() - pd.DateOffset(years=years)
    df = df[df.index >= cutoff]
    
    if len(df) < 4: # Need at least 4 quarters for a decent fit
        return None, 0, len(df)
        
    # We need positive EPS for Log-Linear: ln(EPS) = A + B*t
    # If we have negative or zero EPS, we can't strictly use log regression.
    # We filter out non-positive EPS, but if too many are missing, it's invalid.
    df_pos = df[df["EPS"] > 0].copy()
    
    if len(df_pos) < len(df) * 0.75: # If > 25% of data is negative/zero, growth is undefined/bad
        return None, 0, len(df)
        
    if len(df_pos) < 3:
        return None, 0, len(df_pos)
        
    # Prepare estimates
    # y = ln(EPS)
    # x = time in years (or fractions)
    
    # Use integer index or day-difference for X
    # Let's use days from start / 365.25
    start_date = df_pos.index.min()
    days = (df_pos.index - start_date).days
    x = days / 365.25
    y = np.log(df_pos["EPS"].values)
    
    # Linear Regression: y = mx + c
    # m = growth rate (approx continuous compounding)
    try:
        slope, intercept = np.polyfit(x, y, 1)
        
        # R-squared calculation
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return slope, r_squared, len(df_pos)
    except:
        return None, 0, len(df_pos)


def score_peg(ticker, years=3, filename="DATA/EPS_manual.txt"):
    """
    Calculate PEG Ratio Score.
    PEG = (P/E) / (Growth Rate * 100)
    
    Score:
    PEG < 1.0 -> 1.0 (Best)
    PEG 1.0 - 3.0 -> Linear decay
    PEG > 3.0 -> 0.0 (Worst)
    """
    # 1. Get Current P/E
    # We reuse value_PE_avg logic or just fetch price and latest TTM EPS
    try:
        # Quick price fetch (1 year just to get latest)
        df_price = _get_price_data(ticker, years=1)
        if df_price.empty:
             raise ValueError("No price data")
             
        current_price = df_price["Close"].iloc[-1]
        
        # Get EPS
        eps_data = load_manual_eps(filename)
        if ticker not in eps_data:
            raise ValueError("No EPS data")
            
        df_eps = eps_data[ticker].copy().sort_index()
        
        # Calculate recent TTM EPS
        # Check frequency logic similiar to value_PE_avg
        if len(df_eps) >= 2:
            median_gap = pd.Series(df_eps.index).diff().median().days
            if median_gap > 120:
                ttm_eps = df_eps["EPS"].iloc[-1]
            else:
                if len(df_eps) >= 4:
                    ttm_eps = df_eps["EPS"].iloc[-4:].sum()
                else:
                    ttm_eps = df_eps["EPS"].sum() # Fallback
        else:
            ttm_eps = df_eps["EPS"].iloc[-1]
            
        if ttm_eps <= 0:
            return 0.0, {
                "peg": 999.0, "pe": 999.0, "growth_rate": 0.0,
                "data_points": len(df_eps),
                "data_gaps": check_data_completeness(ticker, years, filename, "DATA/Balance_manual.txt"),
                "error": "Negative TTM EPS"
            }
            
        pe_ratio = current_price / ttm_eps
        
        # 2. Calculate Growth Rate
        growth_rate, r2, n_points = calculate_growth_rate(ticker, years=years, filename=filename)
        
        if growth_rate is None or growth_rate <= 0:
            # Negative or invalid growth -> High Risk -> Score 0
            return 0.0, {
                "peg": 999.0, 
                "pe": pe_ratio, 
                "growth_rate": growth_rate if growth_rate else 0.0,
                "r_squared": r2,
                "data_points": n_points,
                "data_gaps": check_data_completeness(ticker, years, filename, "DATA/Balance_manual.txt"),
                "error": "Negative/Invalid Growth"
            }
            
        # Convert to percentage (e.g. 0.15 -> 15.0)
        growth_percent = growth_rate * 100
        
        # 3. Calculate PEG
        peg = pe_ratio / growth_percent
        
        # 4. Score
        # < 0.75 is great (Score 1.0)
        # > 3.0 is expensive (Score 0.0)
        if peg <= 0.75:
            score = 1.0
        elif peg >= 3.0:
            score = 0.0
        else:
            # Linear decay from 0.75 to 3.0
            # PEG=0.75 -> Score=1
            # PEG=3.0 -> Score=0
            # Range is 2.25
            score = 1.0 - (peg - 0.75) / 2.25
            
        details = {
            "peg": peg,
            "pe": pe_ratio,
            "growth_rate": growth_percent,
            "r_squared": r2,
            "data_points": n_points,
            "score": score,
            "data_gaps": check_data_completeness(ticker, years, filename, "DATA/Balance_manual.txt")
        }
        
        return score, details
        
    except Exception as e:
        return 0.0, {"error": str(e), "score": 0.0}