import yfinance as yf
import pandas as pd
import numpy as np
from valuation import value_PE_min_max, value_PE_avg

def print_stock_pe_info_ttm(ticker, target_date, years=5):
    target_date = pd.to_datetime(target_date)
    stock = yf.Ticker(ticker)

    # Get historical price
    hist = stock.history(period=f"{years}y")
    if hist.empty:
        print(f"No price data for {ticker}")
        return
    if hist.index.tz is not None:
        hist.index = hist.index.tz_localize(None)

    # Try direct EPS source first
    try:
        earnings = stock.quarterly_earnings.copy()
        # Force index to proper quarter-end dates
        earnings.index = pd.to_datetime(earnings.index) + pd.offsets.QuarterEnd(0)
        earnings = earnings.sort_index()
    except Exception:
        earnings = pd.DataFrame()
    print(earnings)
    # Fallback: compute EPS from income statement
    if earnings.empty or "Earnings" not in earnings.columns:
        qs = stock.quarterly_income_stmt.T
        qs.index = pd.to_datetime(qs.index) + pd.offsets.QuarterEnd(0)
        qs = qs.sort_index()
        print(qs)
        if "Diluted EPS" in qs.columns:
            eps_series = qs["Diluted EPS"]
            eps_source = "Diluted EPS (income stmt)"
        elif "Basic EPS" in qs.columns:
            eps_series = qs["Basic EPS"]
            eps_source = "Basic EPS (income stmt)"
        elif ("Net Income" in qs.columns) and ("Diluted Average Shares" in qs.columns):
            eps_series = qs["Net Income"] / qs["Diluted Average Shares"]
            eps_source = "Net Income ÷ Diluted Shares"
        else:
            print(f"No EPS fields available for {ticker}. Columns: {qs.columns}")
            return
    else:
        eps_series = earnings["Earnings"]  # already EPS per quarter
        eps_source = "Yahoo quarterly_earnings"

    # --- NEW LOGIC ---
    # Find the most recent reported quarter before target_date
    valid_quarters = eps_series.index[eps_series.index <= target_date]
    if valid_quarters.empty:
        print(f"No EPS data available before {target_date.date()}")
        return
    latest_quarter = valid_quarters.max()

    # Take that quarter and the 3 before it (always 4 quarters)
    last4 = eps_series.loc[:latest_quarter].tail(4)
    ttm_eps = last4.sum()

    # Closest price
    closest_idx = hist.index.get_indexer([target_date], method="nearest")[0]
    closest_date = hist.index[closest_idx]
    price = hist.loc[closest_date, "Close"]

    pe = price / ttm_eps if ttm_eps != 0 else float("inf")

    print(f"Ticker: {ticker}")
    print(f"Date: {closest_date.date()}")
    print(f"Price: ${price:,.2f}")
    print(f"Last 4 EPS values:\n{last4}")   # ✅ shows which were summed
    print(f"TTM EPS ({eps_source}): ${ttm_eps:,.2f}")
    print(f"P/E: {pe:,.2f}")

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def plot_pe_ratios_ttm_side_by_side(tickers, years=2):
    n = len(tickers)
    cols = 2
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes = axes.flatten()

    for i, ticker in enumerate(tickers):
        stock = yf.Ticker(ticker)

        # Get historical price data
        try:
            hist = stock.history(period=f"{years}y")
            if hist.empty:
                print(f"No price data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            continue

        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)

        # Get quarterly income statement
        try:
            qfs = stock.quarterly_income_stmt
            if qfs is None or qfs.empty:
                print(f"No quarterly income data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching quarterly income for {ticker}: {e}")
            continue

        qfs = qfs.T
        qfs.index = pd.to_datetime(qfs.index)
        qfs = qfs.sort_index()

        shares = stock.info.get("sharesOutstanding")
        if shares is None:
            print(f"No shares outstanding info for {ticker}, skipping.")
            continue

        # Build TTM EPS series aligned to price dates
        eps_series = pd.Series(index=hist.index, dtype=float)
        for date in hist.index:
            recent_qfs = qfs[qfs.index <= date].tail(4)
            if recent_qfs.empty:
                continue
            ttm_eps = recent_qfs["Net Income"].sum() / shares
            eps_series.loc[date] = ttm_eps

        # Compute P/E
        pe = hist["Close"] / eps_series

        # Plot
        ax = axes[i]
        ax.plot(pe, label="P/E", color="tab:blue")
        ax.set_title(ticker)
        ax.set_xlabel("Date")
        ax.set_ylabel("P/E", color="tab:blue")
        ax.tick_params(axis="y", labelcolor="tab:blue")
        ax.grid(True, which="both", linestyle="--", linewidth=0.5)

        # Overlay stock price on secondary y-axis
        ax2 = ax.twinx()
        ax2.plot(hist.index, hist["Close"], label="Price", color="tab:orange")
        ax2.set_ylabel("Price ($)", color="tab:orange")
        ax2.tick_params(axis="y", labelcolor="tab:orange")

        # Optional: combine legends
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc="upper left")

    # Hide unused subplots
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    plt.show()


import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def plot_price_vs_eps_side_by_side(tickers, years=5, smoothing=0):
    """
    Plot stock price vs TTM EPS with optional smoothing.
    
    Parameters:
        tickers (list): list of tickers
        years (int): years of history to fetch
        smoothing (int): window size for moving average (0 = no smoothing)
    """
    n = len(tickers)
    cols = 2
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes = axes.flatten()

    for i, ticker in enumerate(tickers):
        stock = yf.Ticker(ticker)

        # Get historical price data
        try:
            hist = stock.history(period=f"{years}y")
            if hist.empty:
                print(f"No price data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            continue

        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)

        # Get quarterly income statement
        try:
            qfs = stock.quarterly_income_stmt
            if qfs is None or qfs.empty:
                print(f"No quarterly income data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching quarterly income for {ticker}: {e}")
            continue

        qfs = qfs.T
        qfs.index = pd.to_datetime(qfs.index)
        qfs = qfs.sort_index()

        shares = stock.info.get("sharesOutstanding")
        if shares is None:
            print(f"No shares outstanding info for {ticker}, skipping.")
            continue

        # Build TTM EPS series aligned to price dates
        eps_series = pd.Series(index=hist.index, dtype=float)
        for date in hist.index:
            recent_qfs = qfs[qfs.index <= date].tail(4)
            if recent_qfs.empty:
                continue
            ttm_eps = recent_qfs["Net Income"].sum() / shares
            eps_series.loc[date] = ttm_eps

        # Apply smoothing (moving average)
        if smoothing > 1:
            eps_series = eps_series.rolling(window=smoothing, min_periods=1).mean()
            hist["Close"] = hist["Close"].rolling(window=smoothing, min_periods=1).mean()

        # Plot
        ax = axes[i]
        ax.plot(eps_series, label="TTM EPS", color="tab:blue")
        ax.set_title(ticker)
        ax.set_xlabel("Date")
        ax.set_ylabel("TTM EPS ($)", color="tab:blue")
        ax.tick_params(axis="y", labelcolor="tab:blue")
        ax.grid(True, which="both", linestyle="--", linewidth=0.5)

        # Overlay stock price on secondary y-axis
        ax2 = ax.twinx()
        ax2.plot(hist.index, hist["Close"], label="Price", color="tab:orange")
        ax2.set_ylabel("Price ($)", color="tab:orange")
        ax2.tick_params(axis="y", labelcolor="tab:orange")

        # Optional: combine legends
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc="upper left")

    # Hide unused subplots
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    


import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import os
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


def plot_price_vs_manual_eps(tickers, years=5, smoothing=0, filename="EPS_manual.txt"):
    """
    Plot stock price vs manually provided EPS with optional smoothing.
    """
    # Load EPS data
    eps_data = load_manual_eps(filename)

    n = len(tickers)
    cols = 2
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes = axes.flatten()

    for i, ticker in enumerate(tickers):
        stock = yf.Ticker(ticker)

        # Get historical price data
        try:
            hist = stock.history(period=f"{years}y")
            if hist.empty:
                print(f"No price data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            continue

        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)

        # Get EPS data from manual file
        if ticker not in eps_data:
            print(f"No manual EPS data for {ticker}, skipping.")
            continue
        eps_df = eps_data[ticker]

        # Reindex EPS to match daily price index (forward-fill between quarters)
        eps_series = eps_df["EPS"].reindex(hist.index, method="ffill")

        # Apply smoothing (moving average)
        if smoothing > 1:
            eps_series = eps_series.rolling(window=smoothing, min_periods=1).mean()
            hist["Close"] = hist["Close"].rolling(window=smoothing, min_periods=1).mean()

        # Plot
        ax = axes[i]
        ax.plot(eps_series, label="EPS", color="tab:blue")
        ax.set_title(ticker + " Stock Price vs EPS")
        ax.set_xlabel("Date")
        ax.set_ylabel("EPS ($)", color="tab:blue")
        ax.tick_params(axis="y", labelcolor="tab:blue")
        ax.grid(True, which="both", linestyle="--", linewidth=0.5)

        # Overlay stock price on secondary y-axis
        ax2 = ax.twinx()
        ax2.plot(hist.index, hist["Close"], label="Price", color="tab:orange")
        ax2.set_ylabel("Price ($)", color="tab:orange")
        ax2.tick_params(axis="y", labelcolor="tab:orange")

        # Optional: combine legends
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc="upper left")

    # Hide unused subplots
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()

def plot_price_vs_manual_pe(tickers, years=5, smoothing=0, filename="EPS_manual.txt"):
    """
    Plot stock price vs manually provided P/E ratios with optional smoothing.
    """
    # Load EPS data
    eps_data = load_manual_eps(filename)

    n = len(tickers)
    cols = 2
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes = axes.flatten()

    for i, ticker in enumerate(tickers):
        stock = yf.Ticker(ticker)

        # Get historical price data
        try:
            hist = stock.history(period=f"{years}y")
            if hist.empty:
                print(f"No price data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            continue

        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)

        # Get EPS data from manual file
        if ticker not in eps_data:
            print(f"No manual EPS data for {ticker}, skipping.")
            continue
        eps_df = eps_data[ticker]

        # Reindex EPS to match daily price index (forward-fill between quarters)
        eps_series = eps_df["EPS"].reindex(hist.index, method="ffill")

        # Compute P/E ratio
        pe_series = hist["Close"] / eps_series
        pe_series.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Apply smoothing (moving average)
        if smoothing > 1:
            pe_series = pe_series.rolling(window=smoothing, min_periods=1).mean()
            hist["Close"] = hist["Close"].rolling(window=smoothing, min_periods=1).mean()

        # Plot
        ax = axes[i]
        ax.plot(pe_series, label="P/E", color="tab:blue")
        ax.set_title(ticker + " Price vs P/E")
        ax.set_xlabel("Date")
        ax.set_ylabel("P/E", color="tab:blue")
        ax.tick_params(axis="y", labelcolor="tab:blue")
        ax.grid(True, which="both", linestyle="--", linewidth=0.5)

        # Overlay stock price on secondary y-axis
        ax2 = ax.twinx()
        ax2.plot(hist.index, hist["Close"], label="Price", color="tab:orange")
        ax2.set_ylabel("Price ($)", color="tab:orange")
        ax2.tick_params(axis="y", labelcolor="tab:orange")

        # Combine legends
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc="upper left")

    # Hide unused subplots
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    plt.show()

def plot_pe_ratios_with_forward(tickers, years=2):
    """
    Plot TTM P/E and Forward P/E ratios vs price for a list of tickers.
    - TTM P/E is calculated from trailing 4 quarters of GAAP EPS.
    - Forward P/E comes from analyst EPS estimates (forwardEps in yfinance).
    """
    n = len(tickers)
    cols = 2
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes = axes.flatten()

    for i, ticker in enumerate(tickers):
        stock = yf.Ticker(ticker)

        # Get historical price data
        try:
            hist = stock.history(period=f"{years}y")
            if hist.empty:
                print(f"No price data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            continue

        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)

        # Get quarterly income statement
        try:
            qfs = stock.quarterly_income_stmt
            if qfs is None or qfs.empty:
                print(f"No quarterly income data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching quarterly income for {ticker}: {e}")
            continue

        qfs = qfs.T
        qfs.index = pd.to_datetime(qfs.index)
        qfs = qfs.sort_index()

        shares = stock.info.get("sharesOutstanding")
        if shares is None:
            print(f"No shares outstanding info for {ticker}, skipping.")
            continue

        # Build TTM EPS series aligned to price dates
        eps_series = pd.Series(index=hist.index, dtype=float)
        for date in hist.index:
            recent_qfs = qfs[qfs.index <= date].tail(4)
            if recent_qfs.empty:
                continue
            ttm_eps = recent_qfs["Net Income"].sum() / shares
            eps_series.loc[date] = ttm_eps

        # Compute TTM P/E
        pe_ttm = hist["Close"] / eps_series

        # Forward P/E (constant line, based on forwardEps)
        forward_eps = stock.info.get("forwardEps")
        if forward_eps and forward_eps > 0:
            pe_forward = hist["Close"] / forward_eps
        else:
            pe_forward = None

        # Plot
        ax = axes[i]
        ax.plot(pe_ttm, label="TTM P/E", color="tab:blue")
        if pe_forward is not None:
            ax.plot(hist.index, pe_forward, label="Forward P/E", color="tab:green", linestyle="--")
        ax.set_title(ticker + " P/E Ratios")
        ax.set_xlabel("Date")
        ax.set_ylabel("P/E")
        ax.grid(True, which="both", linestyle="--", linewidth=0.5)

        # Overlay stock price on secondary y-axis
        ax2 = ax.twinx()
        ax2.plot(hist.index, hist["Close"], label="Price", color="tab:orange")
        ax2.set_ylabel("Price ($)", color="tab:orange")
        ax2.tick_params(axis="y", labelcolor="tab:orange")

        # Combine legends
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc="upper left")

    # Hide unused subplots
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    plt.show()


def plot_price_vs_manual_pe_with_forward(tickers, years=5, smoothing=0, filename="EPS_manual.txt", max_pe=None):
    """
    Plot TTM and Forward P/E ratios using manual EPS data.
    - TTM P/E is computed from trailing 4 quarters of manual EPS.
    - Forward P/E comes from analyst forward EPS estimates (via yfinance).
    - max_pe: optional limit for the y-axis (P/E). If None, uses each ticker's max.
    """
    eps_data = load_manual_eps(filename)

    n = len(tickers)
    cols = 2
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes = axes.flatten()

    for i, ticker in enumerate(tickers):
        stock = yf.Ticker(ticker)

        # Get historical price data
        try:
            hist = stock.history(period=f"{years}y")
            if hist.empty:
                print(f"No price data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            continue

        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)

        # Get EPS data from manual file
        if ticker not in eps_data:
            print(f"No manual EPS data for {ticker}, skipping.")
            continue
        eps_df = eps_data[ticker].copy()

        # Compute rolling TTM EPS
        eps_df["TTM_EPS"] = eps_df["EPS"].rolling(4, min_periods=1).sum()

        # Reindex to daily prices
        ttm_eps_series = eps_df["TTM_EPS"].reindex(hist.index, method="ffill")

        # Compute TTM P/E
        pe_ttm = hist["Close"] / ttm_eps_series
        pe_ttm.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Forward P/E
        forward_eps = stock.info.get("forwardEps")
        if forward_eps and forward_eps > 0:
            pe_forward = hist["Close"] / forward_eps
        else:
            pe_forward = None

        # Apply smoothing
        if smoothing > 1:
            pe_ttm = pe_ttm.rolling(window=smoothing, min_periods=1).mean()
            hist["Close"] = hist["Close"].rolling(window=smoothing, min_periods=1).mean()
            if pe_forward is not None:
                pe_forward = pe_forward.rolling(window=smoothing, min_periods=1).mean()

        # Plot
        ax = axes[i]
        ax.plot(pe_ttm, label="TTM P/E (manual EPS)", color="tab:blue")
        if pe_forward is not None:
            ax.plot(hist.index, pe_forward, label="Forward P/E (analyst est.)", color="tab:green", linestyle="--")
        ax.set_title(f"{ticker} P/E Ratios")
        ax.set_xlabel("Date")
        ax.set_ylabel("P/E", color="tab:blue")
        ax.tick_params(axis="y", labelcolor="tab:blue")
        ax.grid(True, which="both", linestyle="--", linewidth=0.5)

        # Apply y-axis scaling
        if max_pe is not None:
            ax.set_ylim(0, max_pe)
        else:
            max_val = np.nanmax(pe_ttm.values)
            if pe_forward is not None:
                max_val = max(max_val, np.nanmax(pe_forward.values))
            ax.set_ylim(0, max_val * 1.1)  # add 10% padding

        # Overlay stock price on secondary axis
        ax2 = ax.twinx()
        ax2.plot(hist.index, hist["Close"], label="Price", color="tab:orange")
        ax2.set_ylabel("Price ($)", color="tab:orange")
        ax2.tick_params(axis="y", labelcolor="tab:orange")

        # Combine legends
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc="upper left")

    # Hide unused subplots
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    plt.show()


tickers = ["AAPL", "NVDA", "INTC", "AMD", "GOOG"]
tickers2 = ["AMD", "GOOG", "TSLA", "INTC", "NVDA", "UNH", "AMZN"]
# Example usage
#print_stock_pe_info_ttm("AMD", "2024-08-15")

#plot_price_vs_manual_eps(["AMD"], years=15, smoothing=10)
#plot_price_vs_manual_eps(["GOOG"], years=15, smoothing=10)
#plot_price_vs_manual_eps(["TSLA"], years=15, smoothing=10)
#plot_price_vs_eps_side_by_side(tickers, years=1, smoothing= 10)
# Example usage
#plot_pe_ratios_ttm_side_by_side(tickers, years=5)

print(value_PE_avg("AMD", 5, "EPS_manual.txt")[0])
print(value_PE_avg("GOOG", 5, "EPS_manual.txt")[0])
print(value_PE_avg("NVDA", 5, "EPS_manual.txt")[0])
print(value_PE_avg("INTC", 5, "EPS_manual.txt")[0])
print(value_PE_avg("AMZN", 5, "EPS_manual.txt")[0])
plot_price_vs_manual_pe_with_forward(tickers2)
#plot_price_vs_manual_pe(tickers2,years=5)
plt.show()