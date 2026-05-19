export interface OpenPosition {
  id: string;
  ticker: string;
  sector: string;
  entry_date: string;
  entry_price: number;
  entry_rsi2: number;
  entry_rsi30: number | null;
  entry_rs_vs_spy: number;
  entry_volume_ratio: number;
  entry_score: number;
  current_price: number;
  current_pnl_pct: number;
  current_pnl_dollars: number;
  hold_days: number;
  status: 'open' | 'pending_close';
  exit_signal: {
    reason: string;
    date: string;
    price: number;
  } | null;
  position_size: number;
  in_top20: boolean;
}

export interface ClosedPosition {
  id: string;
  ticker: string;
  sector: string;
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  pnl_pct: number;
  pnl_dollars: number;
  hold_days: number;
  exit_reason: string;
  entry_score: number;
  was_in_top20: boolean;
  position_size: number;
}

export interface SummaryStats {
  open_count: number;
  total_unrealized_pnl: number;
  total_capital_deployed: number;
}

export interface PerformanceStats {
  total_trades: number;
  winners: number;
  losers: number;
  win_rate: number;
  total_pnl: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
}

export interface PositionsData {
  positions_top20: OpenPosition[];
  positions_all: OpenPosition[];
  summary: {
    top20: SummaryStats;
    all: SummaryStats;
  };
  last_updated: string | null;
  spy_price: number | null;
  spy_above_200sma: boolean | null;
}

export interface ClosedData {
  closed_top20: ClosedPosition[];
  closed_all: ClosedPosition[];
  performance: {
    top20: PerformanceStats;
    all: PerformanceStats;
  };
}

export type TabType = 'open-top20' | 'open-all' | 'closed-top20' | 'closed-all';
