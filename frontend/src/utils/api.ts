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

// GitHub API for triggering workflows
const GITHUB_API_URL = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/scanner.yml/dispatches`;
const TOKEN_KEY = 'github_pat_token';

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export async function triggerScannerWorkflow(token: string): Promise<{ success: boolean; message: string }> {
  try {
    const response = await fetch(GITHUB_API_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: 'main'
      })
    });

    if (response.status === 204) {
      // Store token on success for future use
      storeToken(token);
      return { success: true, message: 'Scanner workflow triggered! Check Actions tab for progress.' };
    } else if (response.status === 401) {
      clearToken();
      return { success: false, message: 'Invalid token. Please check your PAT.' };
    } else if (response.status === 404) {
      return { success: false, message: 'Workflow not found. Check repo settings.' };
    } else {
      const error = await response.json().catch(() => ({}));
      return { success: false, message: `Failed: ${error.message || response.statusText}` };
    }
  } catch (error) {
    return { success: false, message: `Network error: ${error instanceof Error ? error.message : 'Unknown'}` };
  }
}
