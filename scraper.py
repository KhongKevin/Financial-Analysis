import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re

def fetch_eps_data(ticker):
    """
    Scrapes EPS data - tries quarterly first, falls back to annual.
    Returns (data_lines, warning_message) where warning indicates if annual data was used.
    """
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/quarterly/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            url_alt = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/"
            response = requests.get(url_alt, headers=headers, timeout=15)
            if response.status_code != 200:
                return None, f"Failed to fetch data: HTTP {response.status_code}"

        soup = BeautifulSoup(response.text, 'html.parser')
        dfs = pd.read_html(str(soup))
        if not dfs:
            return None, "Could not parse table from HTML"
            
        eps_row = None
        target_df = None
        
        # Find table with EPS
        for df in dfs:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(col).strip() for col in df.columns.values]
            df = df.reset_index(drop=True)
            
            for i, row in df.iterrows():
                label = str(row.iloc[0]).lower()
                if "eps (diluted)" in label or "earnings per share" in label:
                    eps_row = row
                    target_df = df
                    break
            if eps_row is not None:
                break
        
        if eps_row is None:
            return None, "EPS row not found in any table"

        cols = target_df.columns.tolist()
        quarterly_results = []
        annual_results = []
        
        # Try to extract both quarterly and annual data
        for i in range(1, len(cols)):
            col_header = str(cols[i])
            val = eps_row.iloc[i]
            
            # Parse Date
            match = re.search(r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4})', col_header)
            if not match:
                continue
            
            date_str_raw = match.group(1)
            try:
                dt = datetime.strptime(date_str_raw, "%b %d, %Y")
                
                # Filter Future Dates
                if dt > datetime.now():
                    continue
                    
                date_fmt = dt.strftime("%Y-%m-%d")
            except:
                continue
                
            # Parse Value
            val_str = str(val).strip()
            if val_str == '-' or val_str == '' or "nan" in val_str.lower():
                continue
                
            try:
                val_clean = val_str.replace('$', '').replace(',', '')
                float(val_clean)
                data_line = f"{date_fmt}\t${val_clean}"
                
                # Categorize as quarterly or annual
                if "FY" in col_header or "Year" in col_header:
                    annual_results.append(data_line)
                elif "TTM" not in col_header:
                    quarterly_results.append(data_line)
            except:
                continue
        
        # Prefer quarterly, fallback to annual
        if quarterly_results:
            return quarterly_results, None
        elif annual_results:
            return annual_results, "WARNING: Only annual data available (quarterly data not found)"
        else:
            return None, "No valid EPS data found"

    except Exception as e:
        return None, f"Scraper Error: {str(e)}"

def fetch_balance_sheet(ticker):
    """
    Scrapes balance sheet data (Debt/Equity).
    """
    url = f"https://stockanalysis.com/stocks/{ticker.lower()}/financials/balance-sheet/quarterly/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None, f"Failed to fetch balance sheet: HTTP {response.status_code}"

        soup = BeautifulSoup(response.text, 'html.parser')
        dfs = pd.read_html(str(soup))
        if not dfs:
            return None, "No tables found on balance sheet page"

        # Look for Debt and Equity
        debt_row = None
        equity_row = None
        target_df = None

        for df in dfs:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(col).strip() for col in df.columns.values]
            df = df.reset_index(drop=True)
            
            for i, row in df.iterrows():
                label = str(row.iloc[0]).lower().strip()
                if "total debt" in label:
                    debt_row = row
                if "shareholders' equity" in label or label == "total equity":
                    equity_row = row
                
                if debt_row is not None and equity_row is not None:
                    target_df = df
                    break
            if target_df is not None:
                break

        if debt_row is None or equity_row is None:
            return None, f"Could not find both Debt and Equity rows ({'Debt found' if debt_row else 'Debt missing'}, {'Equity found' if equity_row else 'Equity missing'})"

        cols = target_df.columns.tolist()
        results = []
        for i in range(1, len(cols)):
            col_header = str(cols[i])
            debt_val = str(debt_row.iloc[i]).strip().replace('$', '').replace(',', '')
            equity_val = str(equity_row.iloc[i]).strip().replace('$', '').replace(',', '')

            match = re.search(r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4})', col_header)
            if match:
                date_str = datetime.strptime(match.group(1), "%b %d, %Y").strftime("%Y-%m-%d")
            else:
                # Try simple YYYY-MM-DD or other variations
                try:
                    date_str = pd.to_datetime(col_header).strftime("%Y-%m-%d")
                except:
                    continue
            
            if debt_val != '-' and equity_val != '-':
                results.append(f"{date_str}\tDebt:{debt_val}\tEquity:{equity_val}")

        return results, None
    except Exception as e:
        return None, f"Balance Scraper Error: {str(e)}"

def append_to_file(ticker, data_lines, filename="EPS_manual.txt"):
    """
    Appends data (EPS or Balance) to specified file.
    """
    try:
        with open(filename, "a") as f:
            f.write(f"\n{ticker.upper()}\n")
            for line in data_lines:
                f.write(f"{line}\n")
            f.write("END\n")
        return True, None
    except Exception as e:
        return False, str(e)
