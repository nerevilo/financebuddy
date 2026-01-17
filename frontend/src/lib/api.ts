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

export const getSpendingTrend = (view: 'daily' | 'monthly' | 'yearly' = 'daily', budget?: number) => {
  const params = new URLSearchParams();
  params.set('view', view);
  if (budget) params.set('budget', budget.toString());
  return fetchAPI<any>(`/api/dashboard/spending-trend?${params.toString()}`);
};

// Category management
export interface Category {
  name: string;
  transaction_count: number | null;
}

export const getCategories = () => fetchAPI<Category[]>('/transactions/categories');

// ==================== Merchant Category Rule types ====================

export interface MerchantCheckResponse {
  merchant_name: string;
  has_existing_rule: boolean;
  existing_category: string | null;
  matching_transactions: number;
}

export interface CategoryUpdateWithRuleResponse {
  transaction: TransactionDetail;
  rule_created: boolean;
  rule_id: string | null;
  transactions_updated: number;
}

export interface MerchantCategoryRule {
  id: string;
  merchant_name: string;
  category: string;
  is_active: boolean;
  times_applied: number;
  created_at: string;
  updated_at: string | null;
}

export interface MerchantCategoryRulesListResponse {
  rules: MerchantCategoryRule[];
  total: number;
}

// Update transaction category with optional rule creation
export const updateTransactionCategoryWithRule = (
  transactionId: string,
  category: string,
  applyToAll: boolean = false
) =>
  fetchAPI<CategoryUpdateWithRuleResponse>(`/transactions/${transactionId}/category`, {
    method: 'PATCH',
    body: JSON.stringify({ category, apply_to_all: applyToAll }),
  });

// Legacy function for backward compatibility (calls the new endpoint with applyToAll=false)
export const updateTransactionCategory = (transactionId: string, category: string) =>
  updateTransactionCategoryWithRule(transactionId, category, false);

// Check merchant for rule opportunity
export const checkMerchantRule = (merchantName: string) =>
  fetchAPI<MerchantCheckResponse>(
    `/transactions/rules/check-merchant/${encodeURIComponent(merchantName)}`
  );

// Get all merchant category rules
export const getMerchantCategoryRules = () =>
  fetchAPI<MerchantCategoryRulesListResponse>('/transactions/rules/merchant-categories');

// Delete a merchant category rule
export const deleteMerchantCategoryRule = (ruleId: string) =>
  fetchAPI<{ message: string }>(`/transactions/rules/merchant-categories/${ruleId}`, {
    method: 'DELETE',
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
  show_unusual_only?: boolean;
  tag_ids?: string[];
  q?: string; // Search query for description/merchant
}

// ==================== Tag types ====================

export interface Tag {
  id: string;
  name: string;
  color: string | null;
  tag_type: 'predefined' | 'custom';
}

export interface TagsListResponse {
  predefined: Tag[];
  custom: Tag[];
}

// ==================== Extended Transaction types ====================

export interface TransactionDetail extends Transaction {
  is_anomaly: boolean;
  anomaly_score: number | null;
  anomaly_reason: string | null;
  is_one_time: boolean;
  user_reviewed: boolean;
  tags: Tag[];
}

export interface TransactionListWithAnomaliesResponse {
  transactions: TransactionDetail[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  anomaly_count: number;
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
  if (params?.show_unusual_only) searchParams.set('show_unusual_only', 'true');
  if (params?.tag_ids?.length) searchParams.set('tag_ids', params.tag_ids.join(','));
  if (params?.q) searchParams.set('q', params.q);

  const query = searchParams.toString();
  return fetchAPI<TransactionListWithAnomaliesResponse>(`/transactions/list${query ? `?${query}` : ''}`);
};

// ==================== Tag endpoints ====================

export const getTags = () => fetchAPI<TagsListResponse>('/tags/');

export const createTag = (name: string, color?: string) =>
  fetchAPI<Tag>('/tags/', {
    method: 'POST',
    body: JSON.stringify({ name, color }),
  });

export const deleteTag = (tagId: string) =>
  fetchAPI<{ message: string }>(`/tags/${tagId}`, {
    method: 'DELETE',
  });

// ==================== Extended Transaction endpoints ====================

export const getTransactionDetail = (transactionId: string) =>
  fetchAPI<TransactionDetail>(`/transactions/${transactionId}/detail`);

export const updateTransaction = (
  transactionId: string,
  update: {
    merchant_name?: string;
    category?: string;
    tag_ids?: string[];
  }
) =>
  fetchAPI<TransactionDetail>(`/transactions/${transactionId}`, {
    method: 'PATCH',
    body: JSON.stringify(update),
  });

export const addTagToTransaction = (transactionId: string, tagId: string) =>
  fetchAPI<{ message: string }>(`/transactions/${transactionId}/tags/${tagId}`, {
    method: 'POST',
  });

export const removeTagFromTransaction = (transactionId: string, tagId: string) =>
  fetchAPI<{ message: string }>(`/transactions/${transactionId}/tags/${tagId}`, {
    method: 'DELETE',
  });

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

// ==================== Goals types ====================

export interface Goal {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  target_amount: number;
  current_amount: number;
  monthly_allocation: number | null;
  deadline: string | null;
  priority: 'high' | 'medium' | 'low';
  status: 'active' | 'completed' | 'paused' | 'cancelled';
  auto_suggested: boolean;
  suggestion_reason: string | null;
  related_category: string | null;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  // Computed fields
  progress_percentage: number | null;
  months_to_goal: number | null;
  on_track: boolean | null;
}

export interface GoalCreate {
  name: string;
  description?: string;
  target_amount: number;
  current_amount?: number;
  monthly_allocation?: number;
  deadline?: string;
  priority?: 'high' | 'medium' | 'low';
}

export interface GoalUpdate {
  name?: string;
  description?: string;
  target_amount?: number;
  current_amount?: number;
  monthly_allocation?: number;
  deadline?: string;
  priority?: 'high' | 'medium' | 'low';
  status?: 'active' | 'completed' | 'paused' | 'cancelled';
}

export interface GoalSuggestion {
  name: string;
  target_amount: number;
  monthly_allocation: number;
  reason: string;
  related_category: string | null;
  priority: 'high' | 'medium' | 'low';
}

// ==================== Goals endpoints ====================

export const getGoals = (status?: string) => {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  const query = params.toString();
  return fetchAPI<Goal[]>(`/api/goals/${query ? `?${query}` : ''}`);
};

export const createGoal = (goal: GoalCreate) =>
  fetchAPI<Goal>('/api/goals/', {
    method: 'POST',
    body: JSON.stringify(goal),
  });

export const getGoal = (goalId: string) =>
  fetchAPI<Goal>(`/api/goals/${goalId}`);

export const updateGoal = (goalId: string, update: GoalUpdate) =>
  fetchAPI<Goal>(`/api/goals/${goalId}`, {
    method: 'PATCH',
    body: JSON.stringify(update),
  });

export const addGoalProgress = (goalId: string, amount: number) =>
  fetchAPI<Goal>(`/api/goals/${goalId}/progress?amount=${amount}`, {
    method: 'POST',
  });

export const deleteGoal = (goalId: string) =>
  fetchAPI<{ status: string }>(`/api/goals/${goalId}`, {
    method: 'DELETE',
  });

export const getGoalSuggestions = () =>
  fetchAPI<GoalSuggestion[]>('/api/goals/suggestions');

// ==================== Insights types ====================

export interface Insight {
  id: string;
  type: 'alert' | 'opportunity' | 'optimization';
  title: string;
  description: string;
  action: string | null;
  category: string | null;
  amount_referenced: number | null;
  comparison_period: string | null;
  priority_score: number;
  emoji: string | null;
  feedback: 'none' | 'helpful' | 'acted_on' | 'dismissed';
  feedback_at: string | null;
  generated_at: string;
  is_read: boolean;
  expires_at: string | null;
}

export interface DailyInsightsResponse {
  date: string;
  insights: Insight[];
  generation_source: string;
  total_cost: number;
}

// ==================== Insights endpoints ====================

export const getDailyInsights = () =>
  fetchAPI<DailyInsightsResponse>('/api/insights/daily');

export const getInsightHistory = (limit = 20, offset = 0) =>
  fetchAPI<{ insights: Insight[]; total: number }>(
    `/api/insights/history?limit=${limit}&offset=${offset}`
  );

export const submitInsightFeedback = (
  insightId: string,
  feedback: 'helpful' | 'acted_on' | 'dismissed'
) =>
  fetchAPI<Insight>(`/api/insights/${insightId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ feedback }),
  });

export const markInsightRead = (insightId: string) =>
  fetchAPI<Insight>(`/api/insights/${insightId}/read`, {
    method: 'POST',
  });

export const regenerateInsights = () =>
  fetchAPI<DailyInsightsResponse>('/api/insights/regenerate', {
    method: 'POST',
  });

// ==================== Chat types ====================

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  result?: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  tool_calls?: ToolCall[];
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_preview?: string | null;
}

export interface Conversation {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages: ChatMessage[];
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
  has_more: boolean;
}

export interface ChatResponse {
  message: ChatMessage;
  tool_results?: ToolCall[];
  conversation_id: string;
}

// ==================== Chat endpoints ====================

export const getConversations = (limit = 20, offset = 0, status?: string) => {
  const params = new URLSearchParams();
  params.set('limit', limit.toString());
  params.set('offset', offset.toString());
  if (status) params.set('status', status);
  return fetchAPI<ConversationListResponse>(`/api/chat/conversations?${params.toString()}`);
};

export const createConversation = () =>
  fetchAPI<Conversation>('/api/chat/conversations', {
    method: 'POST',
  });

export const getConversation = (conversationId: string) =>
  fetchAPI<Conversation>(`/api/chat/conversations/${conversationId}`);

export const deleteConversation = (conversationId: string) =>
  fetchAPI<{ status: string; conversation_id: string }>(
    `/api/chat/conversations/${conversationId}`,
    { method: 'DELETE' }
  );

export const sendChatMessage = (conversationId: string, message: string) =>
  fetchAPI<ChatResponse>(`/api/chat/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
