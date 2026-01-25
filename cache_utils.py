import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path

CACHE_DIR = Path("cache")
CACHE_TTL_HOURS = 24  # Cache expires after 24 hours


def get_cache_path(ticker: str) -> Path:
    """Get the cache file path for a ticker."""
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / f"{ticker.upper()}.csv"


def is_cache_valid(ticker: str) -> bool:
    """
    Check if cache exists and is still valid (within TTL).
    Returns True if cache exists and is fresh, False otherwise.
    """
    cache_path = get_cache_path(ticker)
    if not cache_path.exists():
        return False
        
    # Check file modification time
    file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
    age = datetime.now() - file_time
        
    return age < timedelta(hours=CACHE_TTL_HOURS)


def load_from_cache(ticker: str) -> pd.DataFrame:
    """
    Load price data from cache file.
    Returns empty DataFrame if cache doesn't exist or is invalid.
    """
    cache_path = get_cache_path(ticker)
    if not cache_path.exists():
        return pd.DataFrame()
        
    try:
        df = pd.read_csv(cache_path, index_col='Date', parse_dates=True)
        return df
    except Exception as e:
        print(f"Error loading cache for {ticker}: {e}")
        return pd.DataFrame()


def save_to_cache(ticker: str, df: pd.DataFrame):
    """
    Save price data to cache file.
    Only saves the 'Close' column to keep files small.
    """
    if df.empty:
        return
        
    cache_path = get_cache_path(ticker)
    try:
        # Save only Close column to reduce file size
        df[['Close']].to_csv(cache_path)
    except Exception as e:
        print(f"Error saving cache for {ticker}: {e}")


def cache_covers_range(ticker: str, years: int = None, start_date: str = None, end_date: str = None) -> bool:
    """
    Check if cached data covers the requested date range.
    Returns True if cache has enough data, False otherwise.
    """
    cached_df = load_from_cache(ticker)
    if cached_df.empty:
        return False
        
    cache_min = cached_df.index.min()
    cache_max = cached_df.index.max()
        
    if years is not None:
        required_start = cache_max - pd.DateOffset(years=years)
        return cache_min <= required_start
    elif start_date is not None or end_date is not None:
        if start_date:
            start = pd.to_datetime(start_date)
            if cache_min > start:
                return False
        if end_date:
            end = pd.to_datetime(end_date)
            if cache_max < end:
                return False
        return True
        
    return True  # If no specific range requested, assume it's covered


def clear_cache(ticker: str = None):
    """Clear cache for a specific ticker or all tickers."""
    if ticker:
        cache_path = get_cache_path(ticker)
        if cache_path.exists():
            cache_path.unlink()
    else:
        # Clear all
        CACHE_DIR.mkdir(exist_ok=True)
        for cache_file in CACHE_DIR.glob("*.csv"):
            cache_file.unlink()


def get_cache_info():
    """Get information about cached files."""
    info = []
    CACHE_DIR.mkdir(exist_ok=True)
    for cache_file in CACHE_DIR.glob("*.csv"):
        ticker = cache_file.stem
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age = datetime.now() - file_time
        size = cache_file.stat().st_size
                
        info.append({
            'ticker': ticker,
            'age_hours': age.total_seconds() / 3600,
            'size_kb': size / 1024,
            'valid': is_cache_valid(ticker)
        })
    return info

