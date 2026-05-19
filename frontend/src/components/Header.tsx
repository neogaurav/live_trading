import { TabType, PositionsData, ClosedData } from '../types';

interface HeaderProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  positions: PositionsData | null;
  closed: ClosedData | null;
}

export function Header({ activeTab, onTabChange, positions, closed }: HeaderProps) {
  const openTop20Count = positions?.positions_top20.filter(p => p.status === 'open').length ?? 0;
  const openAllCount = positions?.positions_all.filter(p => p.status === 'open').length ?? 0;
  const closedTop20Count = closed?.closed_top20.length ?? 0;
  const closedAllCount = closed?.closed_all.length ?? 0;

  const pendingTop20 = positions?.positions_top20.filter(p => p.status === 'pending_close').length ?? 0;
  const pendingAll = positions?.positions_all.filter(p => p.status === 'pending_close').length ?? 0;

  const tabs: { id: TabType; label: string; count: number; pending: number }[] = [
    { id: 'open-top20', label: 'Open (Top 20)', count: openTop20Count, pending: pendingTop20 },
    { id: 'open-all', label: 'Open (All)', count: openAllCount, pending: pendingAll },
    { id: 'closed-top20', label: 'Closed (Top 20)', count: closedTop20Count, pending: 0 },
    { id: 'closed-all', label: 'Closed (All)', count: closedAllCount, pending: 0 },
  ];

  return (
    <nav className="tab-header">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
          <span className="tab-count">[{tab.count}]</span>
          {tab.pending > 0 && (
            <span className="tab-pending" title="Pending close">
              ({tab.pending})
            </span>
          )}
        </button>
      ))}
    </nav>
  );
}
