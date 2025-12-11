import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import urllib.request
import io
import warnings
warnings.filterwarnings('ignore')


def load_manual_eps(filename: str = "EPS_manual.txt") -> Dict[str, pd.DataFrame]:
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


def get_stock_price_history(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Get stock price history for a specific time period from Stooq.
    
    Parameters:
    -----------
    ticker : str
        Stock ticker symbol
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    
    Returns:
    --------
    pd.DataFrame
        Price history with Close prices
    """
    try:
        stooq_ticker = ticker if '.' in ticker else f"{ticker}.US"
        url = f"https://stooq.com/q/d/l/?s={stooq_ticker}&i=d"
        
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read().decode('utf-8')
        
        df = pd.read_csv(io.StringIO(data))
        if df.empty or 'Close' not in df.columns:
            print(f"No price data for {ticker} between {start_date} and {end_date}")
            return pd.DataFrame()
        
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date').sort_index()
        
        # Filter by date range
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        df = df[(df.index >= start) & (df.index <= end)]
        
        return df[['Close']]
    except Exception as e:
        print(f"Error getting price data for {ticker}: {e}")
        return pd.DataFrame()


def calculate_pe_series(ticker: str, start_date: str, end_date: str, 
                       eps_data: Dict[str, pd.DataFrame]) -> pd.Series:
    """
    Calculate P/E ratio series for a stock over a specific time period.
    
    Parameters:
    -----------
    ticker : str
        Stock ticker symbol
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    eps_data : dict
        EPS data loaded from manual file
    
    Returns:
    --------
    pd.Series
        P/E ratios over time
    """
    if ticker not in eps_data:
        print(f"Ticker {ticker} not found in EPS data")
        return pd.Series()
    
    # Get price history
    price_hist = get_stock_price_history(ticker, start_date, end_date)
    if price_hist.empty:
        return pd.Series()
    
    # Get EPS data and calculate TTM EPS
    eps_df = eps_data[ticker].copy()
    eps_df['TTM_EPS'] = eps_df['EPS'].rolling(4, min_periods=1).sum()
    
    # Align EPS data with price data
    aligned_eps = eps_df['TTM_EPS'].reindex(price_hist.index, method='ffill')
    
    # Calculate P/E ratios
    pe_series = price_hist['Close'] / aligned_eps
    pe_series.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    return pe_series


def get_sp500_pe_data(start_date: str, end_date: str) -> pd.Series:
    """
    Get S&P 500 P/E ratio data.
    Note: Stooq doesn't provide P/E data, so this returns empty series.
    Historical P/E data would require a different data source.
    
    Parameters:
    -----------
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    
    Returns:
    --------
    pd.Series
        S&P 500 P/E ratios over time (empty with Stooq)
    """
    print("Warning: S&P 500 P/E data not available with Stooq.")
    return pd.Series()


def plot_pe_comparison(tickers: List[str], 
                      period1_start: str, period1_end: str,
                      period2_start: str, period2_end: str,
                      include_sp500: bool = False,
                      eps_filename: str = "EPS_manual.txt",
                      figsize: Tuple[int, int] = (15, 10),
                      smoothing: int = 0) -> None:
    """
    Plot P/E ratio comparison between different time periods.
    
    Parameters:
    -----------
    tickers : list
        List of stock tickers to analyze
    period1_start : str
        Start date for period 1 (YYYY-MM-DD)
    period1_end : str
        End date for period 1 (YYYY-MM-DD)
    period2_start : str
        Start date for period 2 (YYYY-MM-DD)
    period2_end : str
        End date for period 2 (YYYY-MM-DD)
    include_sp500 : bool
        Whether to include S&P 500 P/E ratio
    eps_filename : str
        Path to EPS manual file
    figsize : tuple
        Figure size
    smoothing : int
        Moving average window for smoothing (0 = no smoothing)
    """
    # Load EPS data
    print("Loading EPS data...")
    eps_data = load_manual_eps(eps_filename)
    
    # Set up the plot
    fig, axes = plt.subplots(len(tickers) + (1 if include_sp500 else 0), 1, 
                           figsize=figsize, sharex=True)
    if len(tickers) + (1 if include_sp500 else 0) == 1:
        axes = [axes]
    
    # Define colors for the two periods
    colors = ['#1f77b4', '#ff7f0e']  # Blue and orange
    period_labels = [f"{period1_start} to {period1_end}", 
                    f"{period2_start} to {period2_end}"]
    
    # Plot each ticker
    for i, ticker in enumerate(tickers):
        ax = axes[i]
        
        pe_data_period1 = calculate_pe_series(ticker, period1_start, period1_end, eps_data)
        pe_data_period2 = calculate_pe_series(ticker, period2_start, period2_end, eps_data)
        
        if pe_data_period1.empty and pe_data_period2.empty:
            ax.text(0.5, 0.5, f'No data for {ticker}', 
                   transform=ax.transAxes, ha='center', va='center')
            ax.set_title(f'{ticker} P/E Ratio Comparison')
            continue
        
        # Apply smoothing if requested
        if smoothing > 1:
            pe_data_period1 = pe_data_period1.rolling(window=smoothing, min_periods=1).mean()
            pe_data_period2 = pe_data_period2.rolling(window=smoothing, min_periods=1).mean()
        
        # Plot both periods
        if not pe_data_period1.empty:
            ax.plot(pe_data_period1.index, pe_data_period1.values, 
                   color=colors[0], linewidth=2, label=period_labels[0])
        
        if not pe_data_period2.empty:
            ax.plot(pe_data_period2.index, pe_data_period2.values, 
                   color=colors[1], linewidth=2, label=period_labels[1])
        
        # Customize subplot
        ax.set_title(f'{ticker} P/E Ratio Comparison', fontsize=12, fontweight='bold')
        ax.set_ylabel('P/E Ratio', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right')
        
        # Add statistics text
        if not pe_data_period1.empty and not pe_data_period2.empty:
            p1_avg = pe_data_period1.mean()
            p2_avg = pe_data_period2.mean()
            p1_max = pe_data_period1.max()
            p2_max = pe_data_period2.max()
            p1_min = pe_data_period1.min()
            p2_min = pe_data_period2.min()
            
            stats_text = f'Period 1: Avg={p1_avg:.1f}, Max={p1_max:.1f}, Min={p1_min:.1f}\n'
            stats_text += f'Period 2: Avg={p2_avg:.1f}, Max={p2_max:.1f}, Min={p2_min:.1f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', fontsize=8, 
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Plot S&P 500 if requested
    if include_sp500:
        ax_sp500 = axes[-1]
        
        sp500_period1 = get_sp500_pe_data(period1_start, period1_end)
        sp500_period2 = get_sp500_pe_data(period2_start, period2_end)
        
        if not sp500_period1.empty:
            ax_sp500.plot(sp500_period1.index, sp500_period1.values, 
                         color=colors[0], linewidth=2, label=f'S&P 500 - {period_labels[0]}')
        
        if not sp500_period2.empty:
            ax_sp500.plot(sp500_period2.index, sp500_period2.values, 
                         color=colors[1], linewidth=2, label=f'S&P 500 - {period_labels[1]}')
        
        ax_sp500.set_title('S&P 500 P/E Ratio Comparison', fontsize=12, fontweight='bold')
        ax_sp500.set_ylabel('P/E Ratio', fontsize=10)
        ax_sp500.grid(True, alpha=0.3)
        ax_sp500.legend(loc='upper right')
    
    # Format x-axis
    axes[-1].set_xlabel('Date', fontsize=10)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=45)
    
    # Overall title
    fig.suptitle('P/E Ratio Comparison Across Time Periods', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.show()


def plot_multiple_period_comparison(ticker: str, 
                                   periods: List[Tuple[str, str, str]],
                                   include_sp500: bool = False,
                                   eps_filename: str = "EPS_manual.txt",
                                   figsize: Tuple[int, int] = (12, 8)) -> None:
    """
    Plot P/E ratio for a single stock across multiple time periods.
    
    Parameters:
    -----------
    ticker : str
        Stock ticker to analyze
    periods : list
        List of tuples (label, start_date, end_date)
    include_sp500 : bool
        Whether to include S&P 500 comparison
    eps_filename : str
        Path to EPS manual file
    figsize : tuple
        Figure size
    """
    # Load EPS data
    eps_data = load_manual_eps(eps_filename)
    
    # Set up the plot
    fig, ax = plt.subplots(figsize=figsize)
    
    # Define colors
    colors = plt.cm.tab10(np.linspace(0, 1, len(periods)))
    
    # Plot each period
    for i, (label, start_date, end_date) in enumerate(periods):
        pe_data = calculate_pe_series(ticker, start_date, end_date, eps_data)
        
        if not pe_data.empty:
            ax.plot(pe_data.index, pe_data.values, 
                   color=colors[i], linewidth=2, label=label)
    
    # Add S&P 500 if requested
    if include_sp500:
        sp500_data = []
        for label, start_date, end_date in periods:
            data = get_sp500_pe_data(start_date, end_date)
            if not data.empty:
                ax.plot(data.index, data.values, 
                       linestyle='--', alpha=0.7, label=f'S&P 500 - {label}')
    
    # Customize plot
    ax.set_title(f'{ticker} P/E Ratio Across Multiple Periods', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('P/E Ratio', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.show()


def get_pe_statistics(ticker: str, start_date: str, end_date: str,
                     eps_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
    """
    Get P/E ratio statistics for a given period.
    
    Parameters:
    -----------
    ticker : str
        Stock ticker
    start_date : str
        Start date
    end_date : str
        End date
    eps_data : dict
        EPS data
    
    Returns:
    --------
    dict
        Statistics including mean, median, min, max, std
    """
    pe_series = calculate_pe_series(ticker, start_date, end_date, eps_data)
    
    if pe_series.empty:
        return {}
    
    return {
        'mean': pe_series.mean(),
        'median': pe_series.median(),
        'min': pe_series.min(),
        'max': pe_series.max(),
        'std': pe_series.std(),
        'count': len(pe_series.dropna())
    }


# Example usage functions
def compare_dot_com_crash_vs_current():
    """Compare dot-com crash period (1999-2001) vs current period (2023-2025)"""
    print("Comparing Dot-Com Crash (1999-2001) vs Current Period (2023-2025)")
    
    tickers = ["AMD", "GOOG", "NVDA", "INTC", "AMZN"]
    
    plot_pe_comparison(
        tickers=tickers,
        period1_start="1999-01-01", period1_end="2001-09-30",
        period2_start="2023-01-01", period2_end="2025-09-30",
        include_sp500=True,
        smoothing=10
    )


def compare_financial_crisis_vs_current():
    """Compare financial crisis period (2007-2009) vs current period (2023-2025)"""
    print("Comparing Financial Crisis (2007-2009) vs Current Period (2023-2025)")
    
    tickers = ["AMD", "GOOG", "NVDA", "INTC", "AMZN"]
    
    plot_pe_comparison(
        tickers=tickers,
        period1_start="2007-01-01", period1_end="2009-12-31",
        period2_start="2023-01-01", period2_end="2025-09-30",
        include_sp500=True,
        smoothing=10
    )


def analyze_nvda_multiple_periods():
    """Analyze NVDA P/E ratios across multiple significant periods"""
    print("Analyzing NVDA P/E ratios across multiple periods")
    
    periods = [
        ("Dot-Com Era (1999-2001)", "1999-01-01", "2001-09-30"),
        ("Financial Crisis (2007-2009)", "2007-01-01", "2009-12-31"),
        ("AI Boom (2023-2025)", "2023-01-01", "2025-09-30"),
        ("Pre-COVID (2018-2020)", "2018-01-01", "2020-02-29")
    ]
    
    plot_multiple_period_comparison(
        ticker="NVDA",
        periods=periods,
        include_sp500=True
    )


if __name__ == "__main__":
    # Example usage
    print("P/E Ratio Comparison Visualizer")
    print("================================")
    
    # Load EPS data to check available tickers
    eps_data = load_manual_eps()
    available_tickers = list(eps_data.keys())
    print(f"Available tickers: {available_tickers}")
    
    # Run example comparisons
    compare_dot_com_crash_vs_current()
    # compare_financial_crisis_vs_current()
    # analyze_nvda_multiple_periods()
