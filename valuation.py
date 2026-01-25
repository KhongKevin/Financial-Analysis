import pandas as pd
import matplotlib.pyplot as plt
import os
import urllib.request
import io
from datetime import datetime, timedelta

def _get_price_data_stooq(ticker, years=None, start_date=None, end_date=None):
    """
    Get price data from Stooq with caching.
    Stooq format: https://stooq.com/q/d/l/?s={ticker}&i=d
    Can filter by years or by start_date/end_date.
    """
    from cache_utils import is_cache_valid, load_from_cache, save_to_cache, cache_covers_range
    
    # Check if we have valid cached data
    cached_df = pd.DataFrame()
    needs_refresh = True
    if is_cache_valid(ticker):
        cached_df = load_from_cache(ticker)
        # Check if cache covers the requested range
        if not cached_df.empty and cache_covers_range(ticker, years=years, start_date=start_date, end_date=end_date):
            needs_refresh = False
    
    # Fetch from Stooq if cache is invalid or empty
    if needs_refresh:
        try:
            stooq_ticker = ticker if '.' in ticker else f"{ticker}.US"
            url = f"https://stooq.com/q/d/l/?s={stooq_ticker}&i=d"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read().decode('utf-8')
            
            df = pd.read_csv(io.StringIO(data))
            if df.empty or 'Close' not in df.columns:
                # If Stooq fails but we have cached data, use that
                if not cached_df.empty:
                    print(f"Using cached data for {ticker}")
                else:
                    return pd.DataFrame()
            else:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date').sort_index()
                
                # Save full dataset to cache
                save_to_cache(ticker, df)
                cached_df = df
        except Exception as e:
            print(f"Stooq failed for {ticker}: {e}")
            if not cached_df.empty:
                print(f"Using cached data for {ticker}")
            else:
                return pd.DataFrame()
    
    # Filter cached data by requested date range
    df = cached_df.copy()
    
    if start_date is not None or end_date is not None:
        if start_date:
            start = pd.to_datetime(start_date)
            df = df[df.index >= start]
        if end_date:
            end = pd.to_datetime(end_date)
            df = df[df.index <= end]
    elif years is not None:
        cutoff_date = df.index.max() - pd.DateOffset(years=years+1)
        df = df[df.index >= cutoff_date]
    
    return df[['Close']]


def _get_price_data(ticker, years):
    """
    Get price data from Stooq.
    """
    return _get_price_data_stooq(ticker, years=years)


def load_manual_eps(filename="EPS_manual.txt"):
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


def value_PE_min_max(ticker, years=1, filename="EPS_manual.txt"):
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
        raise ValueError(f"No price data found for {ticker} from Stooq")

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


def value_PE_avg(ticker, years=1, filename="EPS_manual.txt"):
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

    # --- Price data ---
    df_price = _get_price_data(ticker, years)
    
    if df_price.empty:
        raise ValueError(f"No price data found for {ticker} from Stooq")

    # Ensure tz-naive indices
    if isinstance(df_price.index, pd.DatetimeIndex) and df_price.index.tz is not None:
        df_price.index = df_price.index.tz_localize(None)
    if isinstance(df_eps.index, pd.DatetimeIndex) and df_eps.index.tz is not None:
        df_eps.index = df_eps.index.tz_localize(None)

    # Join and compute P/E
    df = df_price.join(df_eps["TTM_EPS"], how="left").ffill()
    df["PE"] = df["Close"] / df["TTM_EPS"]

    # Restrict to lookback
    cutoff = df.index.max() - pd.DateOffset(years=years)
    df_window = df[df.index >= cutoff].dropna()

    if df_window.empty:
        raise ValueError(f"Not enough EPS/price data for {ticker} over {years} years")

    # Stats
    current_pe = df_window["PE"].iloc[-1]
    min_pe, max_pe, avg_pe = df_window["PE"].min(), df_window["PE"].max(), df_window["PE"].mean()

    # --- Scoring ---
    # Range-based
    if max_pe == min_pe:
        score_range = 0.5
    else:
        score_range = 1 - (current_pe - min_pe) / (max_pe - min_pe)
        score_range = max(0, min(1, score_range))

    # Average-based
    if current_pe <= avg_pe:
        score_avg = 0.5 + 0.5 * (avg_pe - current_pe) / max(1e-9, avg_pe - min_pe)
    else:
        score_avg = 0.5 - 0.5 * (current_pe - avg_pe) / max(1e-9, max_pe - avg_pe)
    score_avg = max(0, min(1, score_avg))

    # Weighted final score
    score = 0.7 * score_avg + 0.3 * score_range

    details = {
        "current_pe": current_pe,
        "avg_pe": avg_pe,
        "min_pe": min_pe,
        "max_pe": max_pe,
        "score_avg": score_avg,
        "score_range": score_range,
        "data_points": len(df_window)
    }

    return score, details