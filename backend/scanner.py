#!/usr/bin/env python3
"""
RSI2_Ultra Live Scanner - Main orchestration script
Runs hourly via GitHub Actions to scan for entry/exit signals.
"""
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from data_fetcher import (
    get_sp1500_tickers,
    fetch_all_data,
    fetch_spy_data,
    calculate_indicators
)
from strategy import (
    check_entry_signal,
    check_exit_signal,
    get_strategy_config
)
from position_manager import (
    load_positions,
    save_positions,
    load_closed,
    save_closed,
    add_new_signal,
    update_position,
    rank_and_update_top20,
    move_closed_positions,
    calculate_performance,
    update_summary,
    get_position_by_ticker
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_scanner(dry_run: bool = False):
    """
    Main scanner function.
    1. Load existing positions
    2. Fetch S&P 1500 tickers
    3. Fetch market data in batches
    4. Check exit signals for existing positions
    5. Check entry signals for new positions
    6. Update positions and save
    """
    logger.info("=" * 60)
    logger.info(" RSI2_Ultra Live Scanner")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.utcnow().isoformat()}Z")
    logger.info(f"Dry run: {dry_run}")

    # Load existing positions
    positions_data = load_positions()
    closed_data = load_closed()

    logger.info(f"Loaded {len(positions_data['positions_all'])} open positions "
                f"({len(positions_data['positions_top20'])} in top 20)")

    # Get strategy config
    config = get_strategy_config()
    logger.info(f"Strategy config: RSI2 entry < {config['rsi2_entry']}, "
                f"exit > {config['rsi2_exit']}, max hold {config['max_hold_days']}d")

    # Fetch S&P 1500 tickers
    logger.info("\nFetching S&P 1500 tickers...")
    ticker_list = get_sp1500_tickers()

    if not ticker_list:
        logger.error("Failed to fetch tickers, aborting")
        return False

    logger.info(f"Total tickers: {len(ticker_list)}")

    # Fetch SPY data first
    logger.info("\nFetching SPY data...")
    spy_df = fetch_spy_data(period="1y")

    if spy_df is None or spy_df.empty:
        logger.error("Failed to fetch SPY data, aborting")
        return False

    spy_df = calculate_indicators(spy_df)
    spy_current_price = float(spy_df['Close'].iloc[-1])
    spy_sma200 = float(spy_df['SMA_200'].iloc[-1])
    spy_above_200sma = spy_current_price > spy_sma200

    logger.info(f"SPY: ${spy_current_price:.2f} (200 SMA: ${spy_sma200:.2f}) "
                f"{'ABOVE' if spy_above_200sma else 'BELOW'}")

    # Update SPY info in positions data
    positions_data['spy_price'] = spy_current_price
    positions_data['spy_above_200sma'] = spy_above_200sma

    # Fetch all ticker data with batching
    logger.info("\nFetching ticker data (this may take a few minutes)...")
    all_data = fetch_all_data(ticker_list, period="1y")

    if not all_data:
        logger.error("Failed to fetch ticker data, aborting")
        return False

    logger.info(f"Successfully fetched data for {len(all_data)} tickers")

    # Phase 1: Check exit signals for existing positions
    logger.info("\n" + "-" * 40)
    logger.info("Phase 1: Checking exit signals...")
    logger.info("-" * 40)

    positions_checked = 0
    exits_triggered = 0

    for pos in positions_data['positions_all']:
        if pos['status'] != 'open':
            continue

        ticker = pos['ticker']
        if ticker not in all_data:
            logger.warning(f"No data for open position {ticker}")
            continue

        df, _ = all_data[ticker]
        df = calculate_indicators(df)

        exit_result = check_exit_signal(df, pos, config)

        if exit_result:
            positions_data = update_position(positions_data, pos['id'], exit_result)

            if not exit_result.get('update_only'):
                exits_triggered += 1
                logger.info(f"EXIT: {ticker} - {exit_result['exit_reason']} "
                          f"(P&L: ${exit_result['pnl_dollars']:.2f})")

        positions_checked += 1

    logger.info(f"Checked {positions_checked} positions, {exits_triggered} exits triggered")

    # Phase 2: Check entry signals for new positions
    logger.info("\n" + "-" * 40)
    logger.info("Phase 2: Checking entry signals...")
    logger.info("-" * 40)

    # Skip entry signals if SPY below 200 SMA (market filter)
    if not spy_above_200sma:
        logger.warning("SPY below 200 SMA - skipping entry signals")
        new_signals = 0
    else:
        new_signals = 0
        ticker_to_sector = {t['ticker']: t['sector'] for t in ticker_list}

        for ticker, (df, sector) in all_data.items():
            # Skip if already have position
            existing = get_position_by_ticker(positions_data, ticker)
            if existing:
                continue

            try:
                df = calculate_indicators(df)
                signal = check_entry_signal(df, spy_df, config)

                if signal:
                    sector = ticker_to_sector.get(ticker, sector)
                    positions_data = add_new_signal(positions_data, ticker, sector, signal)
                    new_signals += 1

            except Exception as e:
                logger.debug(f"Error checking {ticker}: {e}")
                continue

        logger.info(f"Found {new_signals} new entry signals")

    # Phase 3: Rank and update top 20
    logger.info("\n" + "-" * 40)
    logger.info("Phase 3: Ranking positions...")
    logger.info("-" * 40)

    positions_data = rank_and_update_top20(positions_data)

    # Log top 20
    top20_open = [p for p in positions_data['positions_top20'] if p['status'] == 'open']
    logger.info(f"Top 20 positions ({len(top20_open)} open):")
    for i, pos in enumerate(top20_open[:10], 1):
        logger.info(f"  {i}. {pos['ticker']} - Score: {pos['entry_score']:.1f}, "
                   f"P&L: ${pos['current_pnl_dollars']:.2f}")

    # Phase 4: Move closed positions
    positions_data, closed_data = move_closed_positions(positions_data, closed_data)

    # Phase 5: Calculate performance metrics
    closed_data = calculate_performance(closed_data)

    # Phase 6: Update summary
    positions_data = update_summary(positions_data)

    # Log summary
    logger.info("\n" + "=" * 60)
    logger.info(" SUMMARY")
    logger.info("=" * 60)

    top20_summary = positions_data['summary']['top20']
    all_summary = positions_data['summary']['all']

    logger.info(f"\nTop 20 Positions:")
    logger.info(f"  Open: {top20_summary['open_count']}")
    logger.info(f"  Unrealized P&L: ${top20_summary['total_unrealized_pnl']:.2f}")
    logger.info(f"  Capital Deployed: ${top20_summary['total_capital_deployed']:,}")

    logger.info(f"\nAll Positions:")
    logger.info(f"  Open: {all_summary['open_count']}")
    logger.info(f"  Unrealized P&L: ${all_summary['total_unrealized_pnl']:.2f}")
    logger.info(f"  Capital Deployed: ${all_summary['total_capital_deployed']:,}")

    top20_perf = closed_data['performance']['top20']
    all_perf = closed_data['performance']['all']

    if top20_perf['total_trades'] > 0:
        logger.info(f"\nTop 20 Performance (closed):")
        logger.info(f"  Total Trades: {top20_perf['total_trades']}")
        logger.info(f"  Win Rate: {top20_perf['win_rate']:.1f}%")
        logger.info(f"  Total P&L: ${top20_perf['total_pnl']:.2f}")
        logger.info(f"  Profit Factor: {top20_perf['profit_factor']:.2f}")

    if all_perf['total_trades'] > 0:
        logger.info(f"\nAll Positions Performance (closed):")
        logger.info(f"  Total Trades: {all_perf['total_trades']}")
        logger.info(f"  Win Rate: {all_perf['win_rate']:.1f}%")
        logger.info(f"  Total P&L: ${all_perf['total_pnl']:.2f}")
        logger.info(f"  Profit Factor: {all_perf['profit_factor']:.2f}")

    # Save data
    if dry_run:
        logger.info("\nDry run - not saving data")
    else:
        logger.info("\nSaving data...")
        save_positions(positions_data)
        save_closed(closed_data)
        logger.info("Data saved successfully")

    logger.info(f"\nCompleted at: {datetime.utcnow().isoformat()}Z")
    return True


def main():
    parser = argparse.ArgumentParser(description='RSI2_Ultra Live Scanner')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without saving changes')
    args = parser.parse_args()

    try:
        success = run_scanner(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Scanner failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
