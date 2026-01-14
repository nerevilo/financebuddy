import useSWR, { mutate, preload } from 'swr';
import {
  getAccounts,
  getBalanceSummary,
  getIncomeExpenses,
  getDashboardStats,
  getInstitutions,
  getTransactionsByPeriod,
  getCategories,
  getTransactionsList,
  getCategoryMerchants,
  getUnusualTransactions,
  markTransactionOneTime,
  markTransactionNormal,
  getTags,
  TransactionListParams,
  TagsListResponse,
  // Goals
  getGoals,
  createGoal,
  updateGoal,
  deleteGoal,
  addGoalProgress,
  getGoalSuggestions,
  Goal,
  GoalCreate,
  GoalUpdate,
  GoalSuggestion,
  // Insights
  getDailyInsights,
  submitInsightFeedback,
  markInsightRead,
  regenerateInsights,
  Insight,
  DailyInsightsResponse,
} from './api';

// Global refresh - invalidates all SWR caches
export async function refreshAllData() {
  await Promise.all([
    mutate('dashboard'),
    mutate('institutions'),
    mutate((key) => Array.isArray(key) && key[0] === 'transactions-period', undefined, { revalidate: true }),
  ]);
}

// SWR configuration for dashboard data
const swrConfig = {
  revalidateOnFocus: true,
  revalidateOnReconnect: true,
  dedupingInterval: 5000, // Dedupe requests within 5s
  errorRetryCount: 3,
};

// Fetcher that handles errors
async function multiFetcher<T>(fetchers: (() => Promise<any>)[]): Promise<T> {
  const results = await Promise.all(
    fetchers.map(fn => fn().catch(() => null))
  );
  return results as T;
}

// Main dashboard data hook - caches all dashboard data together
export function useDashboard() {
  const { data, error, isLoading, mutate } = useSWR(
    'dashboard',
    () => multiFetcher<[any[], any, any, any]>([
      getAccounts,
      getBalanceSummary,
      getIncomeExpenses,
      getDashboardStats,
    ]),
    {
      ...swrConfig,
      // Keep data fresh for 30 seconds before revalidating
      dedupingInterval: 30000,
      // Show stale data while revalidating
      revalidateIfStale: true,
      // Cache data for 5 minutes
      focusThrottleInterval: 300000,
    }
  );

  const [accounts, balanceSummary, incomeExpenses, dashboardData] = data || [[], null, null, null];

  return {
    accounts: accounts || [],
    balanceSummary,
    incomeExpenses,
    dashboardData,
    isLoading,
    error,
    refresh: mutate,
  };
}

// Institutions hook - for sidebar
export function useInstitutions() {
  const { data, error, isLoading, mutate } = useSWR(
    'institutions',
    getInstitutions,
    swrConfig
  );

  return {
    institutions: data || [],
    isLoading,
    error,
    refresh: mutate,
  };
}

// Transactions by period hook - for timeline
export function useTransactionsByPeriod(period: 'day' | 'week' | 'month') {
  const { data, error, isLoading } = useSWR(
    ['transactions-period', period],
    () => getTransactionsByPeriod(period),
    {
      ...swrConfig,
      dedupingInterval: 60000, // Cache for 1 minute
    }
  );

  return {
    transactions: data || [],
    isLoading,
    error,
  };
}

// Categories hook - for category dropdowns
export function useCategories() {
  const { data, error, isLoading } = useSWR(
    'categories',
    getCategories,
    {
      ...swrConfig,
      dedupingInterval: 300000, // Cache for 5 minutes
    }
  );

  return {
    categories: data || [],
    isLoading,
    error,
  };
}

// Transactions list hook - for spreadsheet view (with anomaly info)
export function useTransactionsList(params?: TransactionListParams) {
  const { data, error, isLoading, mutate } = useSWR(
    ['transactions-list', params],
    () => getTransactionsList(params),
    {
      ...swrConfig,
      dedupingInterval: 30000, // Cache for 30 seconds
    }
  );

  return {
    data: data || { transactions: [], total: 0, limit: 50, offset: 0, has_more: false, anomaly_count: 0 },
    isLoading,
    error,
    refresh: mutate,
  };
}

// Tags hook - for tag management
export function useTags() {
  const { data, error, isLoading, mutate } = useSWR<TagsListResponse>(
    'tags',
    getTags,
    {
      ...swrConfig,
      dedupingInterval: 300000, // Cache for 5 minutes
    }
  );

  return {
    predefinedTags: data?.predefined || [],
    customTags: data?.custom || [],
    allTags: [...(data?.predefined || []), ...(data?.custom || [])],
    isLoading,
    error,
    refresh: mutate,
  };
}

// Category merchants hook - for drill-down modal
export function useCategoryMerchants(category: string | null) {
  const { data, error, isLoading } = useSWR(
    category ? ['category-merchants', category] : null,
    () => getCategoryMerchants(category!),
    {
      ...swrConfig,
      dedupingInterval: 120000, // Cache for 2 minutes
      revalidateOnFocus: false,
    }
  );

  return {
    data,
    isLoading,
    error,
  };
}

// Prefetch category merchants on hover
export function prefetchCategoryMerchants(category: string) {
  preload(['category-merchants', category], () => getCategoryMerchants(category));
}

// Unusual transactions hook - for anomaly detection widget
export function useUnusualTransactions(limit = 5) {
  const { data, error, isLoading, mutate } = useSWR(
    ['unusual-transactions', limit],
    () => getUnusualTransactions(limit, false),
    {
      ...swrConfig,
      dedupingInterval: 60000, // Cache for 1 minute
    }
  );

  const handleMarkOneTime = async (transactionId: string, reason?: string) => {
    await markTransactionOneTime(transactionId, reason);
    mutate();
  };

  const handleMarkNormal = async (transactionId: string) => {
    await markTransactionNormal(transactionId);
    mutate();
  };

  return {
    transactions: data?.transactions || [],
    totalUnreviewed: data?.total_unreviewed || 0,
    isLoading,
    error,
    markAsOneTime: handleMarkOneTime,
    markAsNormal: handleMarkNormal,
    refresh: mutate,
  };
}

// ==================== Goals hooks ====================

// Goals hook - for managing financial goals
export function useGoals(status?: 'active' | 'completed' | 'paused' | 'cancelled') {
  const { data, error, isLoading, mutate: mutateGoals } = useSWR<Goal[]>(
    ['goals', status],
    () => getGoals(status),
    {
      ...swrConfig,
      dedupingInterval: 30000, // Cache for 30 seconds
    }
  );

  const handleCreateGoal = async (goal: GoalCreate): Promise<Goal> => {
    const newGoal = await createGoal(goal);
    mutateGoals();
    return newGoal;
  };

  const handleUpdateGoal = async (goalId: string, update: GoalUpdate): Promise<Goal> => {
    const updated = await updateGoal(goalId, update);
    mutateGoals();
    return updated;
  };

  const handleDeleteGoal = async (goalId: string): Promise<void> => {
    await deleteGoal(goalId);
    mutateGoals();
  };

  const handleAddProgress = async (goalId: string, amount: number): Promise<Goal> => {
    const updated = await addGoalProgress(goalId, amount);
    mutateGoals();
    return updated;
  };

  return {
    goals: data || [],
    isLoading,
    error,
    createGoal: handleCreateGoal,
    updateGoal: handleUpdateGoal,
    deleteGoal: handleDeleteGoal,
    addProgress: handleAddProgress,
    refresh: mutateGoals,
  };
}

// Goal suggestions hook - AI-suggested goals based on spending
export function useGoalSuggestions() {
  const { data, error, isLoading } = useSWR<GoalSuggestion[]>(
    'goal-suggestions',
    getGoalSuggestions,
    {
      ...swrConfig,
      dedupingInterval: 300000, // Cache for 5 minutes
      revalidateOnFocus: false,
    }
  );

  return {
    suggestions: data || [],
    isLoading,
    error,
  };
}

// ==================== Insights hooks ====================

// Daily insights hook - for AI-generated insights
export function useDailyInsights() {
  const { data, error, isLoading, mutate: mutateInsights } = useSWR<DailyInsightsResponse>(
    'daily-insights',
    getDailyInsights,
    {
      ...swrConfig,
      dedupingInterval: 60000, // Cache for 1 minute
      revalidateOnFocus: false,
    }
  );

  const handleFeedback = async (
    insightId: string,
    feedback: 'helpful' | 'acted_on' | 'dismissed'
  ): Promise<Insight> => {
    const updated = await submitInsightFeedback(insightId, feedback);
    mutateInsights();
    return updated;
  };

  const handleMarkRead = async (insightId: string): Promise<Insight> => {
    const updated = await markInsightRead(insightId);
    mutateInsights();
    return updated;
  };

  const handleRegenerate = async (): Promise<DailyInsightsResponse> => {
    const newInsights = await regenerateInsights();
    mutateInsights();
    return newInsights;
  };

  return {
    insights: data?.insights || [],
    date: data?.date || null,
    generationSource: data?.generation_source || null,
    totalCost: data?.total_cost || 0,
    isLoading,
    error,
    submitFeedback: handleFeedback,
    markAsRead: handleMarkRead,
    regenerate: handleRegenerate,
    refresh: mutateInsights,
  };
}
