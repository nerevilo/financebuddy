const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Account endpoints
export const getAccounts = () => fetchAPI<any[]>('/accounts/');
export const getBalanceSummary = () => fetchAPI<any>('/accounts/summary/balances');

// Transaction endpoints
export const getTransactions = (params?: {
  limit?: number;
  offset?: number;
  start_date?: string;
  end_date?: string;
}) => {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());
  if (params?.start_date) searchParams.set('start_date', params.start_date);
  if (params?.end_date) searchParams.set('end_date', params.end_date);

  const query = searchParams.toString();
  return fetchAPI<any[]>(`/transactions/${query ? `?${query}` : ''}`);
};

export const getRecentTransactions = (days = 30, limit = 50) =>
  fetchAPI<any[]>(`/transactions/recent?days=${days}&limit=${limit}`);

// Analytics endpoints
export const getSpendingByCategory = (period = 'this_month') =>
  fetchAPI<any>(`/analytics/spending/by-category?period=${period}`);

export const getSpendingByMerchant = (period = 'this_month', limit = 20) =>
  fetchAPI<any>(`/analytics/spending/by-merchant?period=${period}&limit=${limit}`);

export const getSpendingTrends = (months = 6) =>
  fetchAPI<any>(`/analytics/spending/trends?months=${months}`);

export const getPeriodComparison = (period = 'this_month') =>
  fetchAPI<any>(`/analytics/comparison?current_period=${period}`);

export const getIncomeExpenses = (period = 'this_month') =>
  fetchAPI<any>(`/analytics/income-expenses?period=${period}`);

// Teller Connect
export const saveTellerConnection = (payload: {
  accessToken: string;
  enrollment: any;
  user: any;
}) => fetchAPI('/teller/connect', {
  method: 'POST',
  body: JSON.stringify(payload),
});

export const syncInstitution = (institutionId: string) =>
  fetchAPI(`/teller/sync/${institutionId}`, { method: 'POST' });
