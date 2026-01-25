import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test_yahoo_api(ticker):
    print(f"\n--- Testing Yahoo API for {ticker} ---")
    # modules: earningsHistory gives last 4 quarters actuals
    # incomeStatementHistoryQuarterly gives financials!
    
    modules = ["earningsHistory", "incomeStatementHistory", "incomeStatementHistoryQuarterly"]
    modules_str = ",".join(modules)
    
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules={modules_str}"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        print(f"Status: {res.status_code}")
        if res.status_code != 200:
            print("Failed")
            return

        data = res.json()
        result = data.get('quoteSummary', {}).get('result', [])
        if not result:
            print("No result found")
            return
            
        data = result[0]
        
        # Check Earnings History
        if 'earningsHistory' in data:
            print("\nEarnings History (Last 4 Q):")
            history = data['earningsHistory']['history']
            for item in history:
                print(f"  {item['quarter']['fmt']}: {item['epsActual']['fmt']}")
                
        # Check Quarterly Income Statement
        if 'incomeStatementHistoryQuarterly' in data:
            print("\nQuarterly Income Statement:")
            stmts = data['incomeStatementHistoryQuarterly']['incomeStatementHistory']
            for stmt in stmts:
                date = stmt['endDate']['fmt']
                # Net Income / Shares? 
                # Yahoo usually provides eps field directly in other modules?
                # "dilutedEPS" might be here? - wait, usually hidden.
                # Let's check keys
                # print(stmt.keys())
                try:
                    eps = stmt.get('dilutedEPS', {}).get('fmt', 'N/A') # Often not in basic structure?
                    # basicEPS?
                    print(f"  {date}: EPS={eps}")
                except:
                    pass

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yahoo_api("ibm")
