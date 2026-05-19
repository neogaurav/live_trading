import { PositionsData, ClosedData } from '../types';

// Configure these for your repository
const REPO_OWNER = 'neogaurav';  // TODO: Update this to your GitHub username
const REPO_NAME = 'live_trading';  // Repo name

const BASE_URL = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/backend/data`;

export async function fetchPositions(): Promise<PositionsData> {
  const url = `${BASE_URL}/positions.json?t=${Date.now()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch positions: ${response.status}`);
  }

  return response.json();
}

export async function fetchClosed(): Promise<ClosedData> {
  const url = `${BASE_URL}/closed.json?t=${Date.now()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch closed positions: ${response.status}`);
  }

  return response.json();
}

export function formatCurrency(value: number): string {
  const prefix = value >= 0 ? '+$' : '-$';
  return `${prefix}${Math.abs(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatPercent(value: number): string {
  const prefix = value >= 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}

export function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDateTime(isoStr: string | null): string {
  if (!isoStr) return 'Never';
  const date = new Date(isoStr);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short'
  });
}
