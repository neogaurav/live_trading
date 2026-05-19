"""
Data Fetcher - yfinance wrapper with batching and rate limiting
"""
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Rate limiting configuration
BATCH_SIZE = 100
BATCH_DELAY_SECONDS = 3
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


def _fetch_wiki_table(url: str) -> Optional[pd.DataFrame]:
    """Fetch Wikipedia table with proper headers to avoid 403."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(response.text, header=0)
        return tables[0] if tables else None
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


def get_sp1500_tickers() -> List[Dict[str, str]]:
    """
    Fetch S&P 1500 tickers (S&P 500 + S&P 400 + S&P 600) from Wikipedia.
    Returns list of dicts with 'ticker' and 'sector' keys.
    """
    tickers = []

    # S&P 500
    try:
        df = _fetch_wiki_table("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        if df is not None:
            # Find the symbol and sector columns
            symbol_col = None
            sector_col = None
            for col in df.columns:
                col_lower = str(col).lower()
                if 'symbol' in col_lower or 'ticker' in col_lower:
                    symbol_col = col
                elif 'sector' in col_lower or 'gics sector' in col_lower:
                    sector_col = col

            if symbol_col is None:
                symbol_col = df.columns[0]
            if sector_col is None:
                sector_col = df.columns[3] if len(df.columns) > 3 else None

            for _, row in df.iterrows():
                ticker = str(row[symbol_col]).strip().replace('.', '-')
                sector = str(row[sector_col]).strip() if sector_col else 'Unknown'
                if ticker and ticker != 'nan':
                    tickers.append({'ticker': ticker, 'sector': sector})
        logger.info(f"S&P 500: {len(tickers)} tickers")
    except Exception as e:
        logger.error(f"Error processing S&P 500: {e}")

    sp500_count = len(tickers)

    # S&P 400 (Mid Cap)
    try:
        df = _fetch_wiki_table("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies")
        if df is not None:
            symbol_col = None
            sector_col = None
            for col in df.columns:
                col_lower = str(col).lower()
                if 'symbol' in col_lower or 'ticker' in col_lower:
                    symbol_col = col
                elif 'sector' in col_lower or 'gics' in col_lower:
                    sector_col = col

            if symbol_col is None:
                symbol_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            if sector_col is None:
                sector_col = df.columns[2] if len(df.columns) > 2 else None

            for _, row in df.iterrows():
                ticker = str(row[symbol_col]).strip().replace('.', '-')
                sector = str(row[sector_col]).strip() if sector_col else 'Unknown'
                if ticker and ticker != 'nan' and not ticker.startswith('–'):
                    tickers.append({'ticker': ticker, 'sector': sector})
        logger.info(f"S&P 400: {len(tickers) - sp500_count} tickers")
    except Exception as e:
        logger.error(f"Error processing S&P 400: {e}")

    sp400_count = len(tickers)

    # S&P 600 (Small Cap)
    try:
        df = _fetch_wiki_table("https://en.wikipedia.org/wiki/List_of_S%26P_600_companies")
        if df is not None:
            symbol_col = None
            sector_col = None
            for col in df.columns:
                col_lower = str(col).lower()
                if 'symbol' in col_lower or 'ticker' in col_lower:
                    symbol_col = col
                elif 'sector' in col_lower or 'gics' in col_lower:
                    sector_col = col

            if symbol_col is None:
                symbol_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            if sector_col is None:
                sector_col = df.columns[2] if len(df.columns) > 2 else None

            for _, row in df.iterrows():
                ticker = str(row[symbol_col]).strip().replace('.', '-')
                sector = str(row[sector_col]).strip() if sector_col else 'Unknown'
                if ticker and ticker != 'nan' and not ticker.startswith('–'):
                    tickers.append({'ticker': ticker, 'sector': sector})
        logger.info(f"S&P 600: {len(tickers) - sp400_count} tickers")
    except Exception as e:
        logger.error(f"Error processing S&P 600: {e}")

    logger.info(f"Total S&P 1500 tickers: {len(tickers)}")
    return tickers


def fetch_data_batch(tickers: List[str], period: str = "1y", interval: str = "1d") -> Dict[str, pd.DataFrame]:
    """
    Fetch data for a batch of tickers using yfinance bulk download.
    Returns dict mapping ticker -> DataFrame.
    """
    if not tickers:
        return {}

    result = {}

    for attempt in range(MAX_RETRIES):
        try:
            # Use yf.download for bulk fetching
            data = yf.download(
                tickers=tickers,
                period=period,
                interval=interval,
                group_by='ticker',
                auto_adjust=True,
                threads=True,
                progress=False
            )

            if data.empty:
                logger.warning(f"Empty data returned for batch")
                return result

            # Handle single ticker case
            if len(tickers) == 1:
                ticker = tickers[0]
                if not data.empty:
                    result[ticker] = data.copy()
                return result

            # Handle multiple tickers - data has MultiIndex columns
            for ticker in tickers:
                try:
                    if ticker in data.columns.get_level_values(0):
                        ticker_data = data[ticker].copy()
                        ticker_data = ticker_data.dropna(how='all')
                        if not ticker_data.empty and len(ticker_data) > 50:
                            result[ticker] = ticker_data
                except Exception as e:
                    logger.debug(f"Error extracting {ticker}: {e}")
                    continue

            return result

        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                wait_time = RETRY_DELAY_SECONDS * (attempt + 1)
                logger.warning(f"Rate limited, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"Error fetching batch: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS)

    return result


def fetch_all_data(ticker_list: List[Dict[str, str]], period: str = "1y") -> Dict[str, Tuple[pd.DataFrame, str]]:
    """
    Fetch data for all tickers with batching and rate limiting.
    Returns dict mapping ticker -> (DataFrame, sector).
    """
    all_data = {}
    tickers = [t['ticker'] for t in ticker_list]
    ticker_to_sector = {t['ticker']: t['sector'] for t in ticker_list}

    # Split into batches
    batches = [tickers[i:i + BATCH_SIZE] for i in range(0, len(tickers), BATCH_SIZE)]

    for batch_num, batch in enumerate(batches):
        logger.info(f"Fetching batch {batch_num + 1}/{len(batches)} ({len(batch)} tickers)...")

        batch_data = fetch_data_batch(batch, period=period)

        for ticker, df in batch_data.items():
            sector = ticker_to_sector.get(ticker, 'Unknown')
            all_data[ticker] = (df, sector)

        # Delay between batches (except for last batch)
        if batch_num < len(batches) - 1:
            time.sleep(BATCH_DELAY_SECONDS)

    logger.info(f"Successfully fetched data for {len(all_data)} tickers")
    return all_data


def fetch_spy_data(period: str = "1y") -> Optional[pd.DataFrame]:
    """Fetch SPY data for relative strength and market filter calculations."""
    try:
        spy = yf.download("SPY", period=period, interval="1d", progress=False, auto_adjust=True)
        if not spy.empty:
            return spy
    except Exception as e:
        logger.error(f"Error fetching SPY data: {e}")
    return None


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators needed for RSI2_Ultra strategy.
    """
    df = df.copy()

    # RSI calculation helper
    def calc_rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # RSI indicators
    df['RSI_2'] = calc_rsi(df['Close'], 2)
    df['RSI_14'] = calc_rsi(df['Close'], 14)
    df['RSI_30'] = calc_rsi(df['Close'], 30)

    # Moving averages
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()

    # Volume metrics
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA_20']

    # Price change
    df['Pct_Change'] = df['Close'].pct_change() * 100

    return df


def calculate_relative_strength(stock_df: pd.DataFrame, spy_df: pd.DataFrame, lookback: int = 20) -> float:
    """
    Calculate relative strength of stock vs SPY over lookback period.
    Returns the outperformance percentage (positive = stock beat SPY).
    """
    try:
        # Align dates
        common_dates = stock_df.index.intersection(spy_df.index)
        if len(common_dates) < lookback:
            return 0.0

        stock_slice = stock_df.loc[common_dates].tail(lookback + 1)
        spy_slice = spy_df.loc[common_dates].tail(lookback + 1)

        if len(stock_slice) < lookback + 1 or len(spy_slice) < lookback + 1:
            return 0.0

        stock_return = (stock_slice['Close'].iloc[-1] / stock_slice['Close'].iloc[0] - 1) * 100
        spy_return = (spy_slice['Close'].iloc[-1] / spy_slice['Close'].iloc[0] - 1) * 100

        return stock_return - spy_return
    except Exception as e:
        logger.debug(f"Error calculating relative strength: {e}")
        return 0.0
