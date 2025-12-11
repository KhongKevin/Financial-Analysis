import pandas as pd
import numpy as np
from valuation import value_PE_min_max, value_PE_avg, _get_price_data_stooq
from finance_plots import plot_price_vs_eps, plot_pe_ratios

def print_stock_pe_info_ttm(ticker, target_date, years=5):
    target_date = pd.to_datetime(target_date)

    # Get historical price from Stooq
    hist = _get_price_data_stooq(ticker, years=years)
    if hist.empty:
        print(f"No price data for {ticker}")
        return
    
    # Note: Stooq doesn't provide EPS data, so this function requires manual EPS
    print(f"Warning: EPS data from yfinance not available with Stooq.")
    print(f"Please use manual EPS data or the valuation functions that use EPS_manual.txt")
    return

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

 


 


 


tickers = ["AAPL", "NVDA", "INTC", "AMD", "GOOG"]
tickers2 = ["NFLX", "AMD", "GOOG", "TSLA", "INTC", "NVDA", "UNH", "AMZN"]
# Example usage
#print_stock_pe_info_ttm("AMD", "2024-08-15")

# Examples using consolidated API in finance_plots
# plot_price_vs_eps(tickers, years=1, smoothing=10, source="auto")
# plot_price_vs_eps(["AMD"], years=15, smoothing=10, source="manual")
# plot_pe_ratios(tickers, years=5, source="auto")

tickers_to_value = ["NFLX", "AMD", "GOOG", "NVDA", "INTC", "AMZN"]
for ticker in tickers_to_value:
    try:
        result = value_PE_avg(ticker, 5, "EPS_manual.txt")[0]
        print(f"{ticker}: {result}")
    except (ValueError, Exception) as e:
        print(f"{ticker}: Error - {e}")
plot_pe_ratios(tickers2, years=5, source="manual", include_forward=True)