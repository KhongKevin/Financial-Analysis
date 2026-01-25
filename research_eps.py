import requests
import pandas as pd
from bs4 import BeautifulSoup
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test_stockanalysis_json(ticker):
    print(f"\n--- Testing StockAnalysis JSON for {ticker} ---")
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/quarterly/"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {res.status_code}")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        script = soup.find('script', {'id': '__NEXT_DATA__'})
        if not script:
            print("No __NEXT_DATA__ script found")
            return
            
        data = json.loads(script.string)
        print("JSON Parsed!")
        
        # Traverse JSON to find financial data
        # Usually props -> pageProps -> data
        try:
            page_props = data['props']['pageProps']
            if 'data' in page_props:
                print("Found 'data' in pageProps")
                # print keys
                # print(page_props['data'].keys()) 
                # usually it's list of dicts or dict
                print(f"Data type: {type(page_props['data'])}")
                
                # Check for EPS
                # Iterate if list
                financials = page_props['data']
                if isinstance(financials, list):
                    print(f"Items: {len(financials)}")
                    print(f"Item 0: {financials[0]}")
            else:
                print(f"Keys in pageProps: {page_props.keys()}")
                
        except Exception as e:
            print(f"JSON Structure Error: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_stockanalysis_json("ibm")
