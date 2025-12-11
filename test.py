from valuation import _get_price_data_stooq
# Test Stooq price data
spy_data = _get_price_data_stooq('SPY', years=1)
print(f"SPY data (last 30 days):\n{spy_data.tail(30)}")
