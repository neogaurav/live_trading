import { useState } from 'react';
import { PositionsData, ClosedData } from '../types';
import { formatCurrency, formatDateTime, getStoredToken, triggerScannerWorkflow } from '../utils/api';

interface SummaryProps {
  positions: PositionsData | null;
  closed: ClosedData | null;
  lastRefresh: Date | null;
  onRefresh: () => void;
  loading: boolean;
}

export function Summary({ positions, closed, lastRefresh, onRefresh, loading }: SummaryProps) {
  const [triggerStatus, setTriggerStatus] = useState<{ type: 'success' | 'error' | null; message: string }>({ type: null, message: '' });
  const [isTriggering, setIsTriggering] = useState(false);

  const top20Summary = positions?.summary.top20;
  const allSummary = positions?.summary.all;
  const top20Perf = closed?.performance.top20;
  const allPerf = closed?.performance.all;

  const handleTriggerScan = async () => {
    // Check for stored token first
    let token = getStoredToken();

    if (!token) {
      // Prompt for token
      token = window.prompt(
        'Enter your GitHub Personal Access Token (PAT):\n\n' +
        'To create one:\n' +
        '1. Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)\n' +
        '2. Generate new token with "repo" and "workflow" scopes\n\n' +
        'Token will be stored in session only (cleared on tab close):'
      );

      if (!token) {
        return; // User cancelled
      }
    }

    setIsTriggering(true);
    setTriggerStatus({ type: null, message: '' });

    const result = await triggerScannerWorkflow(token);

    setTriggerStatus({
      type: result.success ? 'success' : 'error',
      message: result.message
    });
    setIsTriggering(false);

    // Auto-clear success message after 5 seconds
    if (result.success) {
      setTimeout(() => {
        setTriggerStatus({ type: null, message: '' });
      }, 5000);
    }
  };

  return (
    <div className="summary">
      <div className="summary-header">
        <h1>RSI2 Ultra Dashboard</h1>
        <div className="summary-meta">
          <span className="last-update">
            Last scan: {formatDateTime(positions?.last_updated || null)}
          </span>
          <span className={`spy-status ${positions?.spy_above_200sma ? 'bullish' : 'bearish'}`}>
            SPY: ${positions?.spy_price?.toFixed(2) || '--'}
            ({positions?.spy_above_200sma ? 'Above' : 'Below'} 200 SMA)
          </span>
          <div className="button-group">
            <button onClick={onRefresh} disabled={loading} className="refresh-btn">
              {loading ? 'Loading...' : 'Refresh'}
            </button>
            <button
              onClick={handleTriggerScan}
              disabled={isTriggering}
              className="trigger-btn"
              title="Manually trigger the scanner workflow"
            >
              {isTriggering ? 'Triggering...' : 'Run Scanner'}
            </button>
          </div>
        </div>
      </div>

      {triggerStatus.type && (
        <div className={`trigger-status ${triggerStatus.type}`}>
          {triggerStatus.message}
          {triggerStatus.type === 'error' && (
            <button
              className="retry-token-btn"
              onClick={() => {
                sessionStorage.removeItem('github_pat_token');
                setTriggerStatus({ type: null, message: '' });
                handleTriggerScan();
              }}
            >
              Try different token
            </button>
          )}
        </div>
      )}

      <div className="summary-cards">
        <div className="summary-card top20">
          <h3>Top 20 Signals</h3>
          <div className="card-section">
            <h4>Open Positions</h4>
            <div className="stat-row">
              <span>Count:</span>
              <span className="value">{top20Summary?.open_count ?? 0}</span>
            </div>
            <div className="stat-row">
              <span>Unrealized P&L:</span>
              <span className={`value ${(top20Summary?.total_unrealized_pnl ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                {formatCurrency(top20Summary?.total_unrealized_pnl ?? 0)}
              </span>
            </div>
            <div className="stat-row">
              <span>Capital:</span>
              <span className="value">${(top20Summary?.total_capital_deployed ?? 0).toLocaleString()}</span>
            </div>
          </div>
          <div className="card-section">
            <h4>Closed Performance</h4>
            <div className="stat-row">
              <span>Trades:</span>
              <span className="value">{top20Perf?.total_trades ?? 0}</span>
            </div>
            <div className="stat-row">
              <span>Win Rate:</span>
              <span className="value">{(top20Perf?.win_rate ?? 0).toFixed(1)}%</span>
            </div>
            <div className="stat-row">
              <span>Total P&L:</span>
              <span className={`value ${(top20Perf?.total_pnl ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                {formatCurrency(top20Perf?.total_pnl ?? 0)}
              </span>
            </div>
            <div className="stat-row">
              <span>Profit Factor:</span>
              <span className="value">{(top20Perf?.profit_factor ?? 0).toFixed(2)}</span>
            </div>
          </div>
        </div>

        <div className="summary-card all">
          <h3>All Signals</h3>
          <div className="card-section">
            <h4>Open Positions</h4>
            <div className="stat-row">
              <span>Count:</span>
              <span className="value">{allSummary?.open_count ?? 0}</span>
            </div>
            <div className="stat-row">
              <span>Unrealized P&L:</span>
              <span className={`value ${(allSummary?.total_unrealized_pnl ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                {formatCurrency(allSummary?.total_unrealized_pnl ?? 0)}
              </span>
            </div>
            <div className="stat-row">
              <span>Capital:</span>
              <span className="value">${(allSummary?.total_capital_deployed ?? 0).toLocaleString()}</span>
            </div>
          </div>
          <div className="card-section">
            <h4>Closed Performance</h4>
            <div className="stat-row">
              <span>Trades:</span>
              <span className="value">{allPerf?.total_trades ?? 0}</span>
            </div>
            <div className="stat-row">
              <span>Win Rate:</span>
              <span className="value">{(allPerf?.win_rate ?? 0).toFixed(1)}%</span>
            </div>
            <div className="stat-row">
              <span>Total P&L:</span>
              <span className={`value ${(allPerf?.total_pnl ?? 0) >= 0 ? 'positive' : 'negative'}`}>
                {formatCurrency(allPerf?.total_pnl ?? 0)}
              </span>
            </div>
            <div className="stat-row">
              <span>Profit Factor:</span>
              <span className="value">{(allPerf?.profit_factor ?? 0).toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="client-refresh">
        Client refresh: {lastRefresh?.toLocaleTimeString() || '--'}
      </div>
    </div>
  );
}
