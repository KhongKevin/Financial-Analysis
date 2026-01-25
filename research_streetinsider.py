import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test_streetinsider(ticker):
    url = f"https://www.streetinsider.com/ec_earnings.php?q={ticker}"
    print(f"Scanning: {url}")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {res.status_code}")
        
        dfs = pd.read_html(res.text)
        print(f"Found {len(dfs)} tables")
        
        for i, df in enumerate(dfs):
            cols = df.columns.tolist()
            # Check for EPS and Quarter
            # StreetInsider usually has columns: [Date, Quarter, EPS, ...]
            print(f"Table {i} Top: {cols[:5]}")
            if not df.empty:
               print(f"Row 0: {df.iloc[0].tolist()[:5]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_streetinsider("ibm")
