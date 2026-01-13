const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Get auth token from localStorage
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('fintrack_access_token');
}

export async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options?.headers,
  };

  // Add auth header if token exists
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized - redirect to login
  if (response.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('fintrack_access_token');
      localStorage.removeItem('fintrack_refresh_token');
      localStorage.removeItem('fintrack_user');
      window.location.href = '/login';
    }
    throw new Error('Session expired. Please log in again.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API error: ${response.status}`);
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

export const disconnectInstitution = (institutionId: string) =>
  fetchAPI(`/teller/disconnect/${institutionId}`, { method: 'DELETE' });

// Institution endpoints
export interface AccountSummary {
  id: string;
  name: string;
  type: string;
  subtype: string | null;
  last_four: string | null;
  current_balance: number;
  available_balance: number | null;
}

export interface Institution {
  id: string;
  name: string;
  status: string;
  last_synced_at: string | null;
  accounts: AccountSummary[];
}

export const getInstitutions = () => fetchAPI<Institution[]>('/institutions/');

// Dashboard endpoints (new insight-driven dashboard)
export const getDashboardStats = () => fetchAPI<any>('/api/dashboard/stats');
export const getDailyInsight = () => fetchAPI<any>('/api/dashboard/insight');
export const getSpendingVelocity = () => fetchAPI<any>('/api/dashboard/velocity');
export const getMonthlyComparison = () => fetchAPI<any>('/api/dashboard/comparison');
export const getCategoryBreakdown = (month?: number, year?: number) => {
  const params = new URLSearchParams();
  if (month) params.set('month', month.toString());
  if (year) params.set('year', year.toString());
  const query = params.toString();
  return fetchAPI<any>(`/api/dashboard/categories${query ? `?${query}` : ''}`);
};
export const getTopMerchants = (limit = 10) =>
  fetchAPI<any[]>(`/api/dashboard/top-merchants?limit=${limit}`);
export const getDashboardRecentTransactions = (limit = 10) =>
  fetchAPI<any[]>(`/api/dashboard/recent-transactions?limit=${limit}`);
export const getCategoryMerchants = (category: string, month?: number, year?: number) => {
  const params = new URLSearchParams();
  if (month) params.set('month', month.toString());
  if (year) params.set('year', year.toString());
  const query = params.toString();
  return fetchAPI<any>(`/api/dashboard/category/${encodeURIComponent(category)}/merchants${query ? `?${query}` : ''}`);
};
export const getTransactionsByPeriod = (period: 'day' | 'week' | 'month' = 'month') =>
  fetchAPI<any[]>(`/api/dashboard/transactions/by-period?period=${period}`);

// Category management
export interface Category {
  name: string;
  transaction_count: number | null;
}

export const getCategories = () => fetchAPI<Category[]>('/transactions/categories');

export const updateTransactionCategory = (transactionId: string, category: string) =>
  fetchAPI<Transaction>(`/transactions/${transactionId}/category`, {
    method: 'PATCH',
    body: JSON.stringify({ category }),
  });

// Transaction types
export interface Transaction {
  id: string;
  account_id: string;
  date: string;
  amount: number;
  description: string;
  merchant_name: string | null;
  category: string | null;
  type: string | null;
  status: string;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface TransactionListParams {
  account_id?: string;
  category?: string;
  start_date?: string;
  end_date?: string;
  sort_by?: 'date' | 'amount' | 'merchant' | 'category';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export const getTransactionsList = (params?: TransactionListParams) => {
  const searchParams = new URLSearchParams();
  if (params?.account_id) searchParams.set('account_id', params.account_id);
  if (params?.category) searchParams.set('category', params.category);
  if (params?.start_date) searchParams.set('start_date', params.start_date);
  if (params?.end_date) searchParams.set('end_date', params.end_date);
  if (params?.sort_by) searchParams.set('sort_by', params.sort_by);
  if (params?.sort_order) searchParams.set('sort_order', params.sort_order);
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());

  const query = searchParams.toString();
  return fetchAPI<TransactionListResponse>(`/transactions/list${query ? `?${query}` : ''}`);
};

// ==================== Anomaly Detection endpoints ====================

export interface UnusualTransaction {
  id: string;
  amount: number;
  merchant: string | null;
  category: string | null;
  date: string;
  anomaly_score: number;
  anomaly_reason: string;
  description: string;
  is_one_time: boolean;
  user_reviewed: boolean;
}

export interface UnusualTransactionsResponse {
  transactions: UnusualTransaction[];
  total_unreviewed: number;
  last_scan: string;
}

export interface AnomalySummary {
  unreviewed_count: number;
  one_time_count: number;
  one_time_total: number;
  top_unreviewed: UnusualTransaction[];
}

export const getUnusualTransactions = (limit = 10, includeReviewed = false) =>
  fetchAPI<UnusualTransactionsResponse>(
    `/anomalies/unusual?limit=${limit}&include_reviewed=${includeReviewed}`
  );

export const runAnomalyDetection = () =>
  fetchAPI<{ message: string; new_anomalies_found: number }>('/anomalies/detect', {
    method: 'POST',
  });

export const markTransactionOneTime = (transactionId: string, reason?: string) =>
  fetchAPI<{ message: string; transaction_id: string }>(`/anomalies/${transactionId}/mark-one-time`, {
    method: 'POST',
    body: JSON.stringify({ reason, exclude_from_budget: true }),
  });

export const markTransactionNormal = (transactionId: string) =>
  fetchAPI<{ message: string; transaction_id: string }>(`/anomalies/${transactionId}/mark-normal`, {
    method: 'POST',
  });

export const getAnomalySummary = () =>
  fetchAPI<AnomalySummary>('/anomalies/summary');

export const getOneTimeExpenses = (startDate?: string, endDate?: string) => {
  const params = new URLSearchParams();
  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);
  const query = params.toString();
  return fetchAPI<any>(`/anomalies/one-time-expenses${query ? `?${query}` : ''}`);
};
