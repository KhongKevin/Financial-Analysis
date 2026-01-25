import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/"
}

def test_mw(ticker):
    url = f"https://www.marketwatch.com/investing/stock/{ticker}/financials/income/quarter"
    print(f"Scanning: {url}")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {res.status_code}")
        if res.status_code != 200:
            return
            
        dfs = pd.read_html(res.text)
        print(f"Found {len(dfs)} tables")
        
        for i, df in enumerate(dfs):
            # Clean
            cols = list(df.columns)
            print(f"Table {i} Cols: {cols[:5]}")
            
            # Find EPS
            for idx, row in df.iterrows():
                label = str(row.iloc[0]).lower()
                if "eps (basic)" in label or "diluted eps" in label:
                    print(f"  > Found {label}: {row.iloc[:5].tolist()}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mw("ibm")
