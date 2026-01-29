import useSWR, { mutate, preload } from 'swr';
import { useState, useCallback, useEffect } from 'react';
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
  // Chat
  getConversations,
  createConversation as createConversationAPI,
  getConversation,
  sendChatMessage,
  ConversationListResponse,
  Conversation,
  ConversationSummary,
  ChatMessage,
  ChatResponse,
  // API Keys
  getAPIKeys,
  createAPIKey,
  revokeAPIKey,
  APIKey,
  APIKeyCreated,
  APIKeyCreate,
  APIKeyListResponse,
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
  dedupingInterval: 10000, // Dedupe requests within 10s (was 5s)
  errorRetryCount: 3,
};

// Longer cache config for stable data (categories, merchants)
const stableDataConfig = {
  ...swrConfig,
  dedupingInterval: 600000, // 10 minutes - stable data changes rarely
  revalidateOnFocus: false, // Don't refetch on tab focus
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
    stableDataConfig // Categories rarely change - use 10 min cache
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
    stableDataConfig // Tags rarely change - use 10 min cache
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
    stableDataConfig // Merchant data rarely changes - use 10 min cache
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
    stableDataConfig // Suggestions are computed, use 10 min cache
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
    mutateInsights(newInsights, false); // Update cache immediately with new data
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

// ==================== Chat hooks ====================

// Conversations list hook - manages conversation history and active selection
export function useConversations() {
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const { data, error, isLoading, mutate: mutateConversations } = useSWR<ConversationListResponse>(
    'conversations',
    () => getConversations(20, 0),
    {
      ...swrConfig,
      dedupingInterval: 30000, // Cache for 30 seconds
      revalidateOnFocus: false,
    }
  );

  const handleCreateConversation = useCallback(async (): Promise<Conversation | null> => {
    try {
      const newConv = await createConversationAPI();
      mutateConversations();
      setActiveConversationId(newConv.id);
      return newConv;
    } catch (err) {
      console.error('Failed to create conversation:', err);
      return null;
    }
  }, [mutateConversations]);

  const setActiveConversation = useCallback((id: string | null) => {
    setActiveConversationId(id);
  }, []);

  return {
    conversations: data?.conversations || [],
    total: data?.total || 0,
    hasMore: data?.has_more || false,
    activeConversationId,
    setActiveConversation,
    createConversation: handleCreateConversation,
    isLoading,
    error,
    refresh: mutateConversations,
  };
}

// Single chat hook - manages messages and sending for an active conversation
export function useChat(conversationId: string | null) {
  const [isSending, setIsSending] = useState(false);
  const [optimisticMessages, setOptimisticMessages] = useState<ChatMessage[]>([]);
  const [optimisticConvId, setOptimisticConvId] = useState<string | null>(null);

  const { data, error, isLoading, mutate: mutateChat } = useSWR<Conversation>(
    conversationId ? ['conversation', conversationId] : null,
    () => getConversation(conversationId!),
    {
      ...swrConfig,
      dedupingInterval: 5000, // Cache for 5 seconds
      revalidateOnFocus: false,
    }
  );

  // Clear optimistic messages only when server data includes them
  // This prevents clearing messages during conversation switches
  useEffect(() => {
    if (data?.messages && data.messages.length > 0 && optimisticConvId === conversationId) {
      // Check if server data now includes our optimistic messages
      const serverHasMessages = optimisticMessages.length > 0 &&
        optimisticMessages.every(optMsg =>
          optMsg.id.startsWith('temp-') ||
          data.messages.some(serverMsg => serverMsg.id === optMsg.id)
        );

      if (serverHasMessages || data.messages.length >= optimisticMessages.length) {
        setOptimisticMessages([]);
        setOptimisticConvId(null);
      }
    }
  }, [data?.messages, conversationId, optimisticConvId, optimisticMessages]);

  // Clear optimistic messages when switching to a different conversation
  useEffect(() => {
    if (optimisticConvId && optimisticConvId !== conversationId && !isSending) {
      setOptimisticMessages([]);
      setOptimisticConvId(null);
    }
  }, [conversationId, optimisticConvId, isSending]);

  const handleSendMessage = useCallback(async (
    convId: string,
    message: string
  ): Promise<ChatResponse | null> => {
    setIsSending(true);
    setOptimisticConvId(convId);

    // Add optimistic user message immediately
    const userMessage: ChatMessage = {
      id: `temp-user-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    setOptimisticMessages(prev => [...prev, userMessage]);

    try {
      const response = await sendChatMessage(convId, message);

      // Replace temp user message with real one, add assistant response
      setOptimisticMessages(prev => {
        const withoutTemp = prev.filter(m => m.id !== userMessage.id);
        return [...withoutTemp, { ...userMessage, id: `sent-${Date.now()}` }, response.message];
      });

      // Refresh the conversation to get the real data
      // Use mutate with the specific key for the new conversation
      mutate(['conversation', convId]);

      // Also refresh conversation list to update titles/previews
      mutate('conversations');

      return response;
    } catch (err) {
      console.error('Failed to send message:', err);
      // Remove the optimistic message on error
      setOptimisticMessages(prev => prev.filter(m => m.id !== userMessage.id));
      return null;
    } finally {
      setIsSending(false);
    }
  }, []);

  // Combine server messages with optimistic messages
  // Only show optimistic messages if they belong to this conversation
  const shouldShowOptimistic = optimisticConvId === conversationId || optimisticConvId === null;
  const allMessages = data?.messages
    ? [...data.messages, ...(shouldShowOptimistic ? optimisticMessages : [])]
    : (shouldShowOptimistic ? optimisticMessages : []);

  return {
    messages: allMessages,
    conversation: data || null,
    isLoading: isLoading || isSending,
    isSending,
    error,
    sendMessage: handleSendMessage,
    refresh: mutateChat,
  };
}

// ==================== API Keys hooks ====================

// API Keys hook - for managing API keys
export function useApiKeys() {
  const { data, error, isLoading, mutate: mutateKeys } = useSWR<APIKeyListResponse>(
    'api-keys',
    getAPIKeys,
    {
      ...swrConfig,
      dedupingInterval: 30000, // Cache for 30 seconds
      revalidateOnFocus: false,
    }
  );

  const handleCreateKey = async (keyData: APIKeyCreate): Promise<APIKeyCreated> => {
    const newKey = await createAPIKey(keyData);
    mutateKeys();
    return newKey;
  };

  const handleRevokeKey = async (keyId: string): Promise<void> => {
    await revokeAPIKey(keyId);
    mutateKeys();
  };

  return {
    keys: data?.keys || [],
    total: data?.total || 0,
    isLoading,
    error,
    createKey: handleCreateKey,
    revokeKey: handleRevokeKey,
    refresh: mutateKeys,
  };
}
