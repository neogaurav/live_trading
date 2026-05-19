"""
Position Manager - JSON read/write for Top20 + All positions
Handles position state management and performance tracking.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from copy import deepcopy

logger = logging.getLogger(__name__)

# Data file paths (relative to this script)
DATA_DIR = Path(__file__).parent / "data"
POSITIONS_FILE = DATA_DIR / "positions.json"
CLOSED_FILE = DATA_DIR / "closed.json"

# Position limits
MAX_TOP20_POSITIONS = 20
POSITION_SIZE = 5000


def get_empty_positions_data() -> Dict[str, Any]:
    """Return empty positions data structure."""
    return {
        "positions_top20": [],
        "positions_all": [],
        "summary": {
            "top20": {
                "open_count": 0,
                "total_unrealized_pnl": 0.0,
                "total_capital_deployed": 0
            },
            "all": {
                "open_count": 0,
                "total_unrealized_pnl": 0.0,
                "total_capital_deployed": 0
            }
        },
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "spy_price": None,
        "spy_above_200sma": None
    }


def get_empty_closed_data() -> Dict[str, Any]:
    """Return empty closed positions data structure."""
    return {
        "closed_top20": [],
        "closed_all": [],
        "performance": {
            "top20": {
                "total_trades": 0,
                "winners": 0,
                "losers": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0
            },
            "all": {
                "total_trades": 0,
                "winners": 0,
                "losers": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0
            }
        }
    }


def load_positions() -> Dict[str, Any]:
    """Load positions from JSON file."""
    try:
        if POSITIONS_FILE.exists():
            with open(POSITIONS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading positions: {e}")
    return get_empty_positions_data()


def save_positions(data: Dict[str, Any]) -> bool:
    """Save positions to JSON file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data['last_updated'] = datetime.utcnow().isoformat() + "Z"
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving positions: {e}")
        return False


def load_closed() -> Dict[str, Any]:
    """Load closed positions from JSON file."""
    try:
        if CLOSED_FILE.exists():
            with open(CLOSED_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading closed positions: {e}")
    return get_empty_closed_data()


def save_closed(data: Dict[str, Any]) -> bool:
    """Save closed positions to JSON file."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CLOSED_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving closed positions: {e}")
        return False


def generate_position_id(ticker: str, entry_date: str) -> str:
    """Generate unique position ID."""
    return f"{ticker}_{entry_date}"


def add_new_signal(
    positions_data: Dict[str, Any],
    ticker: str,
    sector: str,
    signal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add a new signal to positions_all.
    The signal will be ranked and potentially added to positions_top20 later.
    """
    position_id = generate_position_id(ticker, signal['entry_date'])

    # Check if already exists
    existing_ids = {p['id'] for p in positions_data['positions_all']}
    if position_id in existing_ids:
        logger.debug(f"Position {position_id} already exists, skipping")
        return positions_data

    new_position = {
        "id": position_id,
        "ticker": ticker,
        "sector": sector,
        "entry_date": signal['entry_date'],
        "entry_price": signal['entry_price'],
        "entry_rsi2": signal['entry_rsi2'],
        "entry_rsi30": signal.get('entry_rsi30'),
        "entry_rs_vs_spy": signal['entry_rs_vs_spy'],
        "entry_volume_ratio": signal['entry_volume_ratio'],
        "entry_score": signal['entry_score'],
        "current_price": signal['entry_price'],
        "current_pnl_pct": 0.0,
        "current_pnl_dollars": 0.0,
        "hold_days": 0,
        "status": "open",
        "exit_signal": None,
        "position_size": POSITION_SIZE,
        "in_top20": False  # Will be updated by rank_and_update_top20
    }

    positions_data['positions_all'].append(new_position)
    logger.info(f"Added new signal: {ticker} (score: {signal['entry_score']:.1f})")

    return positions_data


def update_position(
    positions_data: Dict[str, Any],
    position_id: str,
    update: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing position with new price/status data.
    Updates both positions_all and positions_top20 if present.
    """
    for positions_list in [positions_data['positions_all'], positions_data['positions_top20']]:
        for pos in positions_list:
            if pos['id'] == position_id:
                if update.get('update_only'):
                    # Just updating current values
                    pos['current_price'] = update.get('current_price', pos['current_price'])
                    pos['current_pnl_pct'] = update.get('current_pnl_pct', pos['current_pnl_pct'])
                    pos['current_pnl_dollars'] = update.get('current_pnl_dollars', pos['current_pnl_dollars'])
                    pos['hold_days'] = update.get('hold_days', pos['hold_days'])
                else:
                    # Exit signal triggered
                    pos['status'] = 'pending_close'
                    pos['exit_signal'] = {
                        'reason': update['exit_reason'],
                        'date': update['exit_date'],
                        'price': update['exit_price'],
                    }
                    pos['current_price'] = update['exit_price']
                    pos['current_pnl_pct'] = update['pnl_pct']
                    pos['current_pnl_dollars'] = update['pnl_dollars']
                    pos['hold_days'] = update['hold_days']

    return positions_data


def rank_and_update_top20(positions_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rank all open positions by score and update top 20 list.
    Only considers positions with status='open' (not pending_close).
    """
    # Get all open positions (not pending_close)
    open_positions = [
        p for p in positions_data['positions_all']
        if p['status'] == 'open'
    ]

    # Sort by score (descending)
    open_positions.sort(key=lambda x: x['entry_score'], reverse=True)

    # Reset in_top20 flag for all
    for pos in positions_data['positions_all']:
        pos['in_top20'] = False

    # Mark top 20 and build top20 list
    top20_ids = set()
    for i, pos in enumerate(open_positions[:MAX_TOP20_POSITIONS]):
        pos['in_top20'] = True
        top20_ids.add(pos['id'])

    # Keep existing pending_close positions in top20 list
    existing_pending = [
        p for p in positions_data['positions_top20']
        if p['status'] == 'pending_close'
    ]

    # Build new top20 list: pending_close + top open positions
    new_top20 = existing_pending.copy()
    for pos in positions_data['positions_all']:
        if pos['id'] in top20_ids:
            # Deep copy to avoid reference issues
            new_top20.append(deepcopy(pos))

    positions_data['positions_top20'] = new_top20

    return positions_data


def move_closed_positions(
    positions_data: Dict[str, Any],
    closed_data: Dict[str, Any]
) -> tuple:
    """
    Move pending_close positions to closed lists.
    Returns updated (positions_data, closed_data).
    """
    positions_to_close = []

    # Find pending_close positions
    for pos in positions_data['positions_all']:
        if pos['status'] == 'pending_close':
            positions_to_close.append(pos)

    # Move to closed
    for pos in positions_to_close:
        closed_position = {
            "id": pos['id'],
            "ticker": pos['ticker'],
            "sector": pos.get('sector', 'Unknown'),
            "entry_date": pos['entry_date'],
            "exit_date": pos['exit_signal']['date'],
            "entry_price": pos['entry_price'],
            "exit_price": pos['exit_signal']['price'],
            "pnl_pct": pos['current_pnl_pct'],
            "pnl_dollars": pos['current_pnl_dollars'],
            "hold_days": pos['hold_days'],
            "exit_reason": pos['exit_signal']['reason'],
            "entry_score": pos['entry_score'],
            "was_in_top20": pos['in_top20'],
            "position_size": pos['position_size'],
        }

        # Add to closed_all
        closed_data['closed_all'].append(closed_position)

        # Add to closed_top20 if was in top20
        if pos['in_top20']:
            closed_data['closed_top20'].append(closed_position)

        logger.info(f"Closed position: {pos['ticker']} ({pos['exit_signal']['reason']}), "
                   f"P&L: ${pos['current_pnl_dollars']:.2f} ({pos['current_pnl_pct']:.2f}%)")

    # Remove closed positions from positions_all and positions_top20
    closed_ids = {p['id'] for p in positions_to_close}
    positions_data['positions_all'] = [
        p for p in positions_data['positions_all']
        if p['id'] not in closed_ids
    ]
    positions_data['positions_top20'] = [
        p for p in positions_data['positions_top20']
        if p['id'] not in closed_ids
    ]

    return positions_data, closed_data


def calculate_performance(closed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate performance metrics for top20 and all closed positions."""

    def calc_metrics(positions: List[Dict]) -> Dict[str, Any]:
        if not positions:
            return {
                "total_trades": 0,
                "winners": 0,
                "losers": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0
            }

        total = len(positions)
        winners = [p for p in positions if p['pnl_dollars'] > 0]
        losers = [p for p in positions if p['pnl_dollars'] <= 0]

        total_pnl = sum(p['pnl_dollars'] for p in positions)
        gross_profit = sum(p['pnl_dollars'] for p in winners) if winners else 0
        gross_loss = abs(sum(p['pnl_dollars'] for p in losers)) if losers else 0

        return {
            "total_trades": total,
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": (len(winners) / total * 100) if total > 0 else 0.0,
            "total_pnl": round(total_pnl, 2),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0,
            "avg_win": round(gross_profit / len(winners), 2) if winners else 0.0,
            "avg_loss": round(gross_loss / len(losers), 2) if losers else 0.0
        }

    closed_data['performance']['top20'] = calc_metrics(closed_data['closed_top20'])
    closed_data['performance']['all'] = calc_metrics(closed_data['closed_all'])

    return closed_data


def update_summary(positions_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update summary statistics for open positions."""

    def calc_summary(positions: List[Dict]) -> Dict[str, Any]:
        open_positions = [p for p in positions if p['status'] == 'open']
        return {
            "open_count": len(open_positions),
            "total_unrealized_pnl": round(sum(p['current_pnl_dollars'] for p in open_positions), 2),
            "total_capital_deployed": sum(p['position_size'] for p in open_positions)
        }

    positions_data['summary']['top20'] = calc_summary(positions_data['positions_top20'])
    positions_data['summary']['all'] = calc_summary(positions_data['positions_all'])

    return positions_data


def get_open_position_ids(positions_data: Dict[str, Any]) -> set:
    """Get set of all open position IDs (not pending_close)."""
    return {
        p['id'] for p in positions_data['positions_all']
        if p['status'] == 'open'
    }


def get_position_by_ticker(positions_data: Dict[str, Any], ticker: str) -> Optional[Dict[str, Any]]:
    """Get open position for a ticker if exists."""
    for pos in positions_data['positions_all']:
        if pos['ticker'] == ticker and pos['status'] == 'open':
            return pos
    return None
