import { useState, useCallback } from 'react';
import { usePositions } from './hooks/usePositions';
import { Summary } from './components/Summary';
import { Header } from './components/Header';
import { OpenPositionGrid, ClosedPositionGrid } from './components/PositionGrid';
import { TabType } from './types';

const ACKNOWLEDGED_KEY = 'rsi2ultra_acknowledged';

function getAcknowledgedIds(): Set<string> {
  try {
    const stored = localStorage.getItem(ACKNOWLEDGED_KEY);
    if (stored) {
      return new Set(JSON.parse(stored));
    }
  } catch {
    // Ignore parse errors
  }
  return new Set();
}

function saveAcknowledgedIds(ids: Set<string>) {
  localStorage.setItem(ACKNOWLEDGED_KEY, JSON.stringify([...ids]));
}

function App() {
  const { positions, closed, loading, error, refresh, lastRefresh } = usePositions();
  const [activeTab, setActiveTab] = useState<TabType>('open-top20');
  const [acknowledgedIds, setAcknowledgedIds] = useState<Set<string>>(getAcknowledgedIds);

  const handleAcknowledge = useCallback((id: string) => {
    setAcknowledgedIds(prev => {
      const newSet = new Set(prev);
      newSet.add(id);
      saveAcknowledgedIds(newSet);
      return newSet;
    });
  }, []);

  const renderContent = () => {
    if (error) {
      return (
        <div className="error-message">
          <h3>Error loading data</h3>
          <p>{error}</p>
          <p className="hint">
            Make sure to update REPO_OWNER and REPO_NAME in src/utils/api.ts
          </p>
          <button onClick={refresh}>Retry</button>
        </div>
      );
    }

    switch (activeTab) {
      case 'open-top20':
        return (
          <OpenPositionGrid
            positions={positions?.positions_top20 ?? []}
            acknowledgedIds={acknowledgedIds}
            onAcknowledge={handleAcknowledge}
          />
        );
      case 'open-all':
        return (
          <OpenPositionGrid
            positions={positions?.positions_all ?? []}
            showInTop20Column={true}
            acknowledgedIds={acknowledgedIds}
            onAcknowledge={handleAcknowledge}
          />
        );
      case 'closed-top20':
        return (
          <ClosedPositionGrid
            positions={closed?.closed_top20 ?? []}
          />
        );
      case 'closed-all':
        return (
          <ClosedPositionGrid
            positions={closed?.closed_all ?? []}
            showWasTop20Column={true}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="app">
      <Summary
        positions={positions}
        closed={closed}
        lastRefresh={lastRefresh}
        onRefresh={refresh}
        loading={loading}
      />

      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        positions={positions}
        closed={closed}
      />

      <main className="main-content">
        {loading && !positions ? (
          <div className="loading">Loading...</div>
        ) : (
          renderContent()
        )}
      </main>
    </div>
  );
}

export default App;
