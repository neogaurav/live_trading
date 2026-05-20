"""
RSI2_Ultra Strategy - Entry/Exit Logic for Live Trading
Adapted from backtest_high_roi.py
"""
import logging
from typing import Dict, Optional, Any
from datetime import datetime

import pandas as pd
import numpy as np

from data_fetcher import calculate_relative_strength

logger = logging.getLogger(__name__)

# Strategy configuration - UltraQ_90_RS2 (72.7% ROI backtested on S&P 1500)
# Optimized for higher ROI with quality filters
DEFAULT_CONFIG = {
    'position_size': 5000,
    'rsi2_entry': 5,       # RSI(2) < 5 for entry
    'rsi2_exit': 65,       # RSI(2) > 65 for exit
    'rsi30_min': 55,       # RSI(30) > 55 for stronger uptrend (was 50)
    'max_hold_days': 2,    # Time stop after 2 days (was 5) - faster capital turnover
    'rs_lookback': 20,     # Relative strength lookback period
    'rs_threshold': 2.0,   # Must outperform SPY by 2% over 20 days (NEW)
    'near_high_pct': 90,   # Must be within 10% of 50-day high (NEW)
}


def calculate_combined_score(rsi2: float, rs_vs_spy: float, volume_ratio: float) -> float:
    """
    Calculate combined score for ranking signals.
    Higher score = stronger signal.

    Score = (10 - RSI2) * 2 + RS_vs_SPY + (Volume_Ratio - 1) * 5

    Example:
    - RSI2 = 3: contributes (10-3)*2 = 14
    - RS_vs_SPY = 5%: contributes 5
    - Volume_Ratio = 1.5: contributes (1.5-1)*5 = 2.5
    - Total = 21.5
    """
    rsi_component = (10 - min(rsi2, 10)) * 2
    rs_component = max(min(rs_vs_spy, 20), -20)  # Cap at +/- 20
    volume_component = (min(volume_ratio, 3) - 1) * 5  # Cap volume ratio at 3x

    return rsi_component + rs_component + volume_component


def check_entry_signal(
    df: pd.DataFrame,
    spy_df: pd.DataFrame,
    config: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Check if the most recent data shows an entry signal for UltraQ_90_RS2 strategy.

    Entry criteria (UltraQ_90_RS2 - 72.7% ROI backtested):
    - Yesterday RSI(2) < 5 (oversold)
    - Today is a green day (bounce confirmation)
    - RSI(30) > 55 (stronger medium-term uptrend)
    - Close > 200 SMA
    - Relative strength vs SPY > 2% (20-day) - quality filter
    - Stock within 10% of 50-day high - near high filter
    - SPY > 200 SMA (market filter)

    Returns signal dict if entry triggered, None otherwise.
    """
    if config is None:
        config = DEFAULT_CONFIG

    if len(df) < 201:
        return None

    try:
        # Get latest and previous rows
        current = df.iloc[-1]
        previous = df.iloc[-2]
        current_date = df.index[-1]

        # Check SPY is above 200 SMA (market filter)
        if spy_df is not None and len(spy_df) >= 200:
            spy_current = spy_df.iloc[-1]
            spy_sma200 = spy_df['Close'].rolling(200).mean().iloc[-1]
            if pd.isna(spy_sma200) or spy_current['Close'] <= spy_sma200:
                return None

        # Must be above 200 SMA
        if pd.isna(current['SMA_200']) or current['Close'] <= current['SMA_200']:
            return None

        # Yesterday had RSI(2) < threshold (oversold)
        rsi2_entry = config.get('rsi2_entry', 5)
        if pd.isna(previous['RSI_2']) or previous['RSI_2'] >= rsi2_entry:
            return None

        # Today is a green day (bounce confirmation)
        if current['Close'] <= previous['Close']:
            return None

        # RSI(30) > threshold (longer-term bullish)
        rsi30_min = config.get('rsi30_min', 55)
        if pd.isna(current['RSI_30']) or current['RSI_30'] < rsi30_min:
            return None

        # Near 50-day high filter (UltraQ filter)
        near_high_pct = config.get('near_high_pct', 90)
        if near_high_pct > 0:
            high_50 = df['Close'].rolling(50).max().iloc[-1]
            if not pd.isna(high_50):
                pct_of_high = (current['Close'] / high_50) * 100
                if pct_of_high < near_high_pct:
                    return None

        # Relative strength check vs SPY with threshold
        rs_vs_spy = 0.0
        rs_threshold = config.get('rs_threshold', 2.0)
        if spy_df is not None:
            rs_lookback = config.get('rs_lookback', 20)
            rs_vs_spy = calculate_relative_strength(df, spy_df, lookback=rs_lookback)
            # Must outperform SPY by threshold (2% for UltraQ)
            if rs_vs_spy <= rs_threshold:
                return None

        # Get volume ratio
        volume_ratio = current.get('Volume_Ratio', 1.0)
        if pd.isna(volume_ratio):
            volume_ratio = 1.0

        # Calculate combined score for ranking
        score = calculate_combined_score(
            rsi2=previous['RSI_2'],
            rs_vs_spy=rs_vs_spy,
            volume_ratio=volume_ratio
        )

        return {
            'entry_date': current_date.strftime('%Y-%m-%d'),
            'entry_price': float(current['Close']),
            'entry_rsi2': float(previous['RSI_2']),
            'entry_rsi30': float(current['RSI_30']),
            'entry_rs_vs_spy': float(rs_vs_spy),
            'entry_volume_ratio': float(volume_ratio),
            'entry_score': float(score),
            'sma_200': float(current['SMA_200']),
        }

    except Exception as e:
        logger.error(f"Error checking entry signal: {e}")
        return None


def check_exit_signal(
    df: pd.DataFrame,
    position: Dict[str, Any],
    config: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Check if the most recent data shows an exit signal for an open position.

    Exit criteria (UltraQ_90_RS2):
    - RSI(2) > 65 (overbought)
    - Hold days >= 2 (time stop - faster capital turnover)

    Returns exit dict if exit triggered, None otherwise.
    """
    if config is None:
        config = DEFAULT_CONFIG

    if len(df) < 2:
        return None

    try:
        current = df.iloc[-1]
        current_date = df.index[-1]

        # Calculate hold days
        entry_date = datetime.strptime(position['entry_date'], '%Y-%m-%d')
        if isinstance(current_date, pd.Timestamp):
            current_dt = current_date.to_pydatetime()
        else:
            current_dt = current_date

        # Count trading days
        trading_days = len(df.loc[entry_date:current_date]) - 1
        hold_days = max(trading_days, 0)

        # Current price and P&L
        current_price = float(current['Close'])
        entry_price = position['entry_price']
        pnl_pct = ((current_price / entry_price) - 1) * 100
        position_size = position.get('position_size', 5000)
        pnl_dollars = (pnl_pct / 100) * position_size

        # Check RSI exit
        rsi2_exit = config.get('rsi2_exit', 65)
        if not pd.isna(current['RSI_2']) and current['RSI_2'] > rsi2_exit:
            return {
                'exit_reason': f'RSI2 > {rsi2_exit}',
                'exit_date': current_date.strftime('%Y-%m-%d'),
                'exit_price': current_price,
                'hold_days': hold_days,
                'pnl_pct': pnl_pct,
                'pnl_dollars': pnl_dollars,
            }

        # Check time stop
        max_hold = config.get('max_hold_days', 5)
        if hold_days >= max_hold:
            return {
                'exit_reason': f'Time Stop ({max_hold}d)',
                'exit_date': current_date.strftime('%Y-%m-%d'),
                'exit_price': current_price,
                'hold_days': hold_days,
                'pnl_pct': pnl_pct,
                'pnl_dollars': pnl_dollars,
            }

        # No exit signal - update current values
        return {
            'update_only': True,
            'current_price': current_price,
            'current_pnl_pct': pnl_pct,
            'current_pnl_dollars': pnl_dollars,
            'hold_days': hold_days,
            'current_rsi2': float(current['RSI_2']) if not pd.isna(current['RSI_2']) else None,
        }

    except Exception as e:
        logger.error(f"Error checking exit signal: {e}")
        return None


def get_strategy_config() -> Dict[str, Any]:
    """Return the default strategy configuration."""
    return DEFAULT_CONFIG.copy()
