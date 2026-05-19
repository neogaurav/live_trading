import { useState, useEffect, useCallback } from 'react';
import { PositionsData, ClosedData } from '../types';
import { fetchPositions, fetchClosed } from '../utils/api';

interface UsePositionsResult {
  positions: PositionsData | null;
  closed: ClosedData | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastRefresh: Date | null;
}

const REFRESH_INTERVAL = 60000; // 1 minute

export function usePositions(): UsePositionsResult {
  const [positions, setPositions] = useState<PositionsData | null>(null);
  const [closed, setClosed] = useState<ClosedData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const loadData = useCallback(async () => {
    try {
      setError(null);

      const [positionsData, closedData] = await Promise.all([
        fetchPositions(),
        fetchClosed()
      ]);

      setPositions(positionsData);
      setClosed(closedData);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(loadData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [loadData]);

  const refresh = useCallback(async () => {
    setLoading(true);
    await loadData();
  }, [loadData]);

  return {
    positions,
    closed,
    loading,
    error,
    refresh,
    lastRefresh
  };
}
