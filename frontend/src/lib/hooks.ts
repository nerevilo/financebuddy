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
  TransactionListParams,
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

// Transactions list hook - for spreadsheet view
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
    data: data || { transactions: [], total: 0, limit: 50, offset: 0, has_more: false },
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
