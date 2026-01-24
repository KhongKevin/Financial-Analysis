import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import urllib.request
import io
from datetime import datetime, timedelta


def load_manual_eps(filename: str = "EPS_manual.txt") -> dict:
    """
    Parse EPS_manual.txt into a dict of {ticker: DataFrame(index=Date, columns=[EPS])}.
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


def _get_price_data_stooq(ticker: str, years: int = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Get price data from Stooq with caching.
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
            # If Stooq fails but we have cached data, use that
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
        cutoff_date = df.index.max() - pd.DateOffset(years=years)
        df = df[df.index >= cutoff_date]
    
    return df


def _get_price_history(ticker: str, years: int) -> pd.DataFrame:
    """
    Get price history from Stooq.
    """
    return _get_price_data_stooq(ticker, years=years)


def _get_auto_ttm_eps_series(ticker: str, price_index: pd.DatetimeIndex) -> pd.Series:
    """
    Build a TTM EPS time series. 
    Note: Stooq doesn't provide EPS data, so this requires manual EPS data.
    Returns empty series - use manual EPS source instead.
    """
    print(f"Warning: Auto EPS not available with Stooq. Use manual EPS source for {ticker}.")
    return pd.Series(index=price_index, dtype=float)


def _get_manual_eps_series(ticker: str, price_index: pd.DatetimeIndex, manual_eps_by_ticker: dict, compute_ttm: bool) -> pd.Series:
    if ticker not in manual_eps_by_ticker:
        return pd.Series(index=price_index, dtype=float)
    eps_df = manual_eps_by_ticker[ticker].copy()
    if compute_ttm:
        eps_df["TTM_EPS"] = eps_df["EPS"].rolling(4, min_periods=1).sum()
        series = eps_df["TTM_EPS"].reindex(price_index, method="ffill")
    else:
        series = eps_df["EPS"].reindex(price_index, method="ffill")
    return series


def plot_price_vs_eps(
    tickers,
    years: int = 5,
    smoothing: int = 0,
    source: str = "auto",
    manual_filename: str = "EPS_manual.txt",
    paginate: bool = True,
    page_size: int = 4,
):
    """
    Plot stock price vs EPS/TTM EPS.

    Parameters:
        tickers: list of tickers
        years: number of years for price history
        smoothing: moving average window; 0 or 1 disables smoothing
        source: "manual" uses EPS from manual file (not TTM; quarterly EPS forward-filled).
                Note: Auto EPS source not available with Stooq.
    """
    n = len(tickers)
    manual_eps_by_ticker = load_manual_eps(manual_filename) if source == "manual" else {}

    # Pre-compute all data once
    print("Loading data for all tickers...")
    ticker_data = {}
    for ticker in tickers:
        hist = _get_price_history(ticker, years)
        if hist.empty:
            print(f"No price data for {ticker}, skipping.")
            continue

        if source == "auto":
            print(f"Warning: Auto EPS source not available with Stooq for {ticker}. Skipping.")
            continue
        elif source == "manual":
            eps_series = _get_manual_eps_series(ticker, hist.index, manual_eps_by_ticker, compute_ttm=False)
            y_label = "EPS ($)"
            title = f"{ticker} Stock Price vs EPS"
        else:
            print(f"Unknown source '{source}' for {ticker}, skipping.")
            continue

        if smoothing and smoothing > 1:
            eps_series = eps_series.rolling(window=smoothing, min_periods=1).mean()
            hist_close = hist["Close"].rolling(window=smoothing, min_periods=1).mean()
        else:
            hist_close = hist["Close"]

        ticker_data[ticker] = {
            'eps_series': eps_series,
            'hist_close': hist_close,
            'hist_index': hist.index,
            'y_label': y_label,
            'title': title
        }

    if not ticker_data:
        print("No valid ticker data found.")
        return

    def draw_page(fig, page_idx):
        fig.clf()
        start = page_idx * page_size
        end = min(start + page_size, n)
        subset = [t for t in tickers[start:end] if t in ticker_data]
        
        if not subset:
            fig.text(0.5, 0.5, "No data for this page", ha='center', va='center')
            fig.canvas.draw_idle()
            return
            
        cols = 2
        rows = (len(subset) + cols - 1) // cols
        gs = fig.add_gridspec(rows, cols)
        axes = []
        for r in range(rows):
            for c in range(cols):
                axes.append(fig.add_subplot(gs[r, c]))

        for i, ticker in enumerate(subset):
            if i >= len(axes):
                break
                
            data = ticker_data[ticker]
            ax = axes[i]
            
            ax.plot(data['eps_series'], label="TTM EPS" if source == "auto" else "EPS", color="tab:blue")
            ax.set_title(data['title'])
            ax.set_xlabel("Date")
            ax.set_ylabel(data['y_label'], color="tab:blue")
            ax.tick_params(axis="y", labelcolor="tab:blue")
            ax.grid(True, which="both", linestyle="--", linewidth=0.5)

            ax2 = ax.twinx()
            ax2.plot(data['hist_index'], data['hist_close'], label="Price", color="tab:orange")
            ax2.set_ylabel("Price ($)", color="tab:orange")
            ax2.tick_params(axis="y", labelcolor="tab:orange")

            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines + lines2, labels + labels2, loc="upper left")

        # remove any unused axes
        for j in range(len(subset), len(axes)):
            fig.delaxes(axes[j])

        fig.suptitle(f"Page {page_idx + 1} / {((n + page_size - 1) // page_size)}", y=0.98)
        fig.tight_layout()
        fig.canvas.draw_idle()

    if paginate and page_size < n:
        total_pages = (n + page_size - 1) // page_size
        fig = plt.figure(figsize=(12, 4 * ((min(page_size, n) + 1) // 2)))
        state = {"page": 0}

        def on_key(event):
            if event.key in ("right", "down", "pagedown"):
                state["page"] = (state["page"] + 1) % total_pages
                draw_page(fig, state["page"])
            elif event.key in ("left", "up", "pageup"):
                state["page"] = (state["page"] - 1) % total_pages
                draw_page(fig, state["page"])

        def on_scroll(event):
            if event.button == "up":
                state["page"] = (state["page"] - 1) % total_pages
            else:
                state["page"] = (state["page"] + 1) % total_pages
            draw_page(fig, state["page"])

        fig.canvas.mpl_connect("key_press_event", on_key)
        fig.canvas.mpl_connect("scroll_event", on_scroll)
        draw_page(fig, 0)
        plt.show()
    else:
        # single page behavior (original)
        fig = plt.figure()
        page_size = n
        draw_page(fig, 0)
        plt.show()


def plot_pe_ratios(
    tickers,
    years: int = 5,
    smoothing: int = 0,
    source: str = "auto",
    manual_filename: str = "EPS_manual.txt",
    include_forward: bool = False,
    max_pe: float | None = None,
    paginate: bool = True,
    page_size: int = 4,
):
    """
    Plot P/E ratios (TTM and optional Forward) alongside price.

    Parameters:
        source: "manual" uses manual EPS. Note: Auto EPS source not available with Stooq.
        include_forward: if True, include forward P/E (not available with Stooq).
        max_pe: if provided, set y-axis max; otherwise auto-scales per subplot.
    """
    n = len(tickers)
    manual_eps_by_ticker = load_manual_eps(manual_filename) if source == "manual" else {}

    # Pre-compute all data once
    print("Loading data for all tickers...")
    ticker_data = {}
    for ticker in tickers:
        hist = _get_price_history(ticker, years)
        if hist.empty:
            print(f"No price data for {ticker}, skipping.")
            continue

        if source == "auto":
            print(f"Warning: Auto EPS source not available with Stooq. Switching to manual for {ticker}.")
            source = "manual"
            ttm_eps_series = _get_manual_eps_series(ticker, hist.index, manual_eps_by_ticker, compute_ttm=True)
        elif source == "manual":
            ttm_eps_series = _get_manual_eps_series(ticker, hist.index, manual_eps_by_ticker, compute_ttm=True)
        else:
            print(f"Unknown source '{source}' for {ticker}, skipping.")
            continue

        pe_ttm = hist["Close"] / ttm_eps_series
        pe_ttm.replace([np.inf, -np.inf], np.nan, inplace=True)

        pe_forward = None
        if include_forward:
            print(f"Warning: Forward P/E not available with Stooq for {ticker}.")
            # Forward P/E requires yfinance data which is not available

        if smoothing and smoothing > 1:
            pe_ttm = pe_ttm.rolling(window=smoothing, min_periods=1).mean()
            price_series = hist["Close"].rolling(window=smoothing, min_periods=1).mean()
            if pe_forward is not None:
                pe_forward = pe_forward.rolling(window=smoothing, min_periods=1).mean()
        else:
            price_series = hist["Close"]

        ticker_data[ticker] = {
            'pe_ttm': pe_ttm,
            'pe_forward': pe_forward,
            'price_series': price_series,
            'hist_index': hist.index
        }

    if not ticker_data:
        print("No valid ticker data found.")
        return

    def draw_page(fig, page_idx):
        fig.clf()
        start = page_idx * page_size
        end = min(start + page_size, n)
        subset = [t for t in tickers[start:end] if t in ticker_data]
        
        if not subset:
            fig.text(0.5, 0.5, "No data for this page", ha='center', va='center')
            fig.canvas.draw_idle()
            return
            
        cols = 2
        rows = (len(subset) + cols - 1) // cols
        gs = fig.add_gridspec(rows, cols)
        axes = []
        for r in range(rows):
            for c in range(cols):
                axes.append(fig.add_subplot(gs[r, c]))

        for i, ticker in enumerate(subset):
            if i >= len(axes):
                break
                
            data = ticker_data[ticker]
            ax = axes[i]
            
            ax.plot(data['pe_ttm'], label=("TTM P/E (manual EPS)" if source == "manual" else "TTM P/E"), color="tab:blue")
            if data['pe_forward'] is not None:
                ax.plot(data['hist_index'], data['pe_forward'], label=("Forward P/E (analyst est.)"), color="tab:green", linestyle="--")
            ax.set_title(f"{ticker} P/E Ratios")
            ax.set_xlabel("Date")
            ax.set_ylabel("P/E", color="tab:blue")
            ax.tick_params(axis="y", labelcolor="tab:blue")
            ax.grid(True, which="both", linestyle="--", linewidth=0.5)

            if max_pe is not None:
                ax.set_ylim(0, max_pe)
            else:
                max_val = np.nanmax(data['pe_ttm'].values)
                if data['pe_forward'] is not None:
                    max_val = max(max_val, np.nanmax(data['pe_forward'].values))
                if np.isfinite(max_val) and max_val > 0:
                    ax.set_ylim(0, max_val * 1.1)

            ax2 = ax.twinx()
            ax2.plot(data['hist_index'], data['price_series'], label="Price", color="tab:orange")
            ax2.set_ylabel("Price ($)", color="tab:orange")
            ax2.tick_params(axis="y", labelcolor="tab:orange")

            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines + lines2, labels + labels2, loc="upper left")

        # remove any unused axes
        for j in range(len(subset), len(axes)):
            fig.delaxes(axes[j])

        fig.suptitle(f"Page {page_idx + 1} / {((n + page_size - 1) // page_size)}", y=0.98)
        fig.tight_layout()
        fig.canvas.draw_idle()

    if paginate and page_size < n:
        total_pages = (n + page_size - 1) // page_size
        fig = plt.figure(figsize=(12, 4 * ((min(page_size, n) + 1) // 2)))
        state = {"page": 0}

        def on_key(event):
            if event.key in ("right", "down", "pagedown"):
                state["page"] = (state["page"] + 1) % total_pages
                draw_page(fig, state["page"])
            elif event.key in ("left", "up", "pageup"):
                state["page"] = (state["page"] - 1) % total_pages
                draw_page(fig, state["page"])

        def on_scroll(event):
            if event.button == "up":
                state["page"] = (state["page"] - 1) % total_pages
            else:
                state["page"] = (state["page"] + 1) % total_pages
            draw_page(fig, state["page"])

        fig.canvas.mpl_connect("key_press_event", on_key)
        fig.canvas.mpl_connect("scroll_event", on_scroll)
        draw_page(fig, 0)
        plt.show()
    else:
        fig = plt.figure()
        page_size = n
        draw_page(fig, 0)
        plt.show()


