import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def plot_pe_ratios_side_by_side(tickers, years=5):
    n = len(tickers)
    cols = 2  # number of columns in subplot grid
    rows = (n + cols - 1) // cols  # compute rows needed

    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes = axes.flatten()  # flatten for easy indexing

    for i, ticker in enumerate(tickers):
        stock = yf.Ticker(ticker)

        # Get historical price
        try:
            hist = stock.history(period=f"{years}y")
            if hist.empty:
                print(f"No price data for {ticker}, skipping.")
                continue
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            continue

        # Remove timezone if present
        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)

        # Try annual financials
        fin = stock.financials
        shares_out = stock.info.get("sharesOutstanding", None)

        if fin is not None and "Net Income" in fin.index and shares_out:
            net_income = fin.loc["Net Income"]
            eps = net_income / shares_out
            eps.index = pd.to_datetime(eps.index)
            eps = eps.sort_index()

            # Align EPS to price dates using forward-fill per period
            eps_series = pd.Series(index=hist.index, dtype=float)
            for j in range(len(eps)):
                start_date = eps.index[j]
                if j < len(eps) - 1:
                    end_date = eps.index[j + 1]
                    eps_series[(hist.index >= start_date) & (hist.index < end_date)] = eps[start_date]
                else:
                    eps_series[hist.index >= start_date] = eps[start_date]
        else:
            # fallback to trailing EPS
            eps_value = stock.info.get("trailingEps")
            if eps_value is None:
                print(f"No EPS available for {ticker}, skipping.")
                continue
            eps_series = pd.Series(eps_value, index=hist.index)

        # Compute P/E
        pe = hist["Close"] / eps_series

        # Plot in its own subplot
        ax = axes[i]
        ax.plot(pe, label=f"{ticker} P/E")
        ax.set_title(ticker)
        ax.set_xlabel("Date")
        ax.set_ylabel("P/E")
        ax.grid(True)

    # Hide any unused subplots
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    plt.show()


import yfinance as yf
import pandas as pd

def print_stock_pe_info(ticker, target_date, years=5):
    target_date = pd.to_datetime(target_date)
    stock = yf.Ticker(ticker)

    # Get historical price
    hist = stock.history(period=f"{years}y")
    if hist.empty:
        print(f"No price data for {ticker}")
        return

    if hist.index.tz is not None:
        hist.index = hist.index.tz_localize(None)

    # Try annual financials
    fin = stock.financials
    shares_out = stock.info.get("sharesOutstanding", None)

    if fin is not None and "Net Income" in fin.index and shares_out:
        net_income = fin.loc["Net Income"]
        eps = net_income / shares_out
        eps.index = pd.to_datetime(eps.index)
        eps = eps.sort_index()

        # Align EPS to price dates
        eps_series = pd.Series(index=hist.index, dtype=float)
        for j in range(len(eps)):
            start_date = eps.index[j]
            if j < len(eps) - 1:
                end_date = eps.index[j + 1]
                eps_series[(hist.index >= start_date) & (hist.index < end_date)] = eps[start_date]
            else:
                eps_series[hist.index >= start_date] = eps[start_date]
    else:
        # fallback to trailing EPS
        eps_value = stock.info.get("trailingEps")
        if eps_value is None:
            print(f"No EPS available for {ticker}")
            return
        eps_series = pd.Series(eps_value, index=hist.index)

    # Compute P/E
    pe_series = hist["Close"] / eps_series

    # Find closest available date
    closest_idx = hist.index.get_indexer([target_date], method="nearest")[0]
    closest_date = hist.index[closest_idx]

    price = hist.loc[closest_date, "Close"]
    eps_val = eps_series.loc[closest_date]
    pe_val = pe_series.loc[closest_date]

    # Print neatly
    print(f"Ticker: {ticker}")
    print(f"Date: {closest_date.date()}")
    print(f"Price: ${price:,.2f}")
    print(f"EPS: ${eps_val:,.2f}")
    print(f"P/E: {pe_val:,.2f}")



# Example usage
print_stock_pe_info("GOOG", "2025-08-15")


# Example usage
tickers = ["AAPL", "NVDA", "INTC", "AMD", "GOOG", "DKING"]
plot_pe_ratios_side_by_side(tickers, years=5)
