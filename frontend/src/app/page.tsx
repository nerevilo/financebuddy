'use client';

import { useState } from 'react';
import { AccountsSummary } from '@/components/dashboard';
import { CategoryBreakdownWidget } from '@/components/dashboard/CategoryBreakdownWidget';
import { TopMerchantsWidget } from '@/components/dashboard/TopMerchantsWidget';
import { DailyTransactionsTimeline } from '@/components/dashboard/DailyTransactionsTimeline';
import { InstitutionSidebar } from '@/components/dashboard/InstitutionSidebar';
import { SpendingTrendChart } from '@/components/dashboard/SpendingTrendChart';
import { UnusualTransactionsBadge } from '@/components/dashboard/UnusualTransactionsBadge';
import { GoalsWidget, GoalSuggestionsCard, GoalSettingModal } from '@/components/goals';
import { BudgetOverviewWidget, BudgetSettingModal, useBudgetSettings } from '@/components/budget';
import { InsightsWidget } from '@/components/insights';
import { useDashboard, useUnusualTransactions, useGoals } from '@/lib/hooks';
import { formatCurrency } from '@/lib/utils';
import { ProtectedRoute, useAuth } from '@/lib/auth';
import { GoalCreate } from '@/lib/api';

function DashboardContent() {
  const { accounts, balanceSummary, incomeExpenses, dashboardData, isLoading, error, refresh } = useDashboard();
  const { user, logout } = useAuth();
  const { totalUnreviewed } = useUnusualTransactions(1);
  const { createGoal } = useGoals();
  const { settings: budgetSettings, saveSettings: saveBudgetSettings } = useBudgetSettings();

  // Modal states for quick actions from insights
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [isBudgetModalOpen, setIsBudgetModalOpen] = useState(false);

  const hasAccounts = accounts.length > 0;

  // Show skeleton instead of spinner when we have cached data
  const showSkeleton = isLoading && !balanceSummary;

  // Calculate total spent this month from income/expenses data
  const totalSpentThisMonth = incomeExpenses?.total_expenses || 0;

  // Get category spending for budget widget
  const categorySpending = dashboardData?.categories?.map((cat: any) => ({
    category: cat.category,
    amount: cat.amount,
  })) || [];

  // Handle goal creation from insight quick action
  const handleCreateGoalFromInsight = () => {
    setIsGoalModalOpen(true);
  };

  // Handle budget setting from insight quick action
  const handleSetBudgetFromInsight = () => {
    setIsBudgetModalOpen(true);
  };

  // Handle saving a new goal
  const handleSaveGoal = async (goalData: GoalCreate | import('@/lib/api').GoalUpdate) => {
    // When creating from insights, we only create new goals
    await createGoal(goalData as GoalCreate);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <InstitutionSidebar onDataChange={refresh} />

      {/* Main Content */}
      <div className="ml-72 flex flex-col min-h-screen">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              {/* Left: Title + Date */}
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Finance Buddy</h1>
                <p className="text-sm text-gray-500">
                  {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </p>
              </div>

              {/* Right: Net Worth + User */}
              <div className="flex items-center gap-6">
                {balanceSummary ? (
                  <div className="text-right">
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Net Worth</p>
                    <p className={`text-xl font-bold ${
                      balanceSummary.total_balance >= 0 ? 'text-gray-900' : 'text-red-600'
                    }`}>
                      {formatCurrency(balanceSummary.total_balance)}
                    </p>
                  </div>
                ) : showSkeleton ? (
                  <div className="text-right animate-pulse">
                    <div className="h-3 w-16 bg-gray-200 rounded mb-1"></div>
                    <div className="h-6 w-24 bg-gray-200 rounded"></div>
                  </div>
                ) : null}

                {/* User menu */}
                <div className="flex items-center gap-3 pl-6 border-l border-gray-200">
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">{user?.name || user?.email}</p>
                    <button
                      onClick={logout}
                      className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                    >
                      Sign out
                    </button>
                  </div>
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-blue-600">
                      {(user?.name || user?.email || '?')[0].toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Area */}
        <main className="flex-1 overflow-y-auto px-6 py-8">
          {showSkeleton ? (
            <DashboardSkeleton />
          ) : error && !hasAccounts ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
              <p className="text-red-700 mb-4">Failed to load dashboard data</p>
              <button
                onClick={() => refresh()}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
              >
                Try Again
              </button>
            </div>
          ) : !hasAccounts ? (
            /* Empty State */
            <div className="text-center py-16">
              <div className="mx-auto w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center mb-6">
                <svg
                  className="w-12 h-12 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect Your First Account</h2>
              <p className="text-gray-600 mb-4 max-w-md mx-auto">
                Use the sidebar to connect your bank accounts and credit cards.
              </p>
              <p className="text-sm text-gray-500">
                Sandbox mode: Use username <code className="bg-gray-100 px-1 rounded">username</code>{' '}
                and password <code className="bg-gray-100 px-1 rounded">password</code>
              </p>
            </div>
          ) : (
            /* Dashboard Content */
            <div className="space-y-6 max-w-6xl">
              {/* AI Insights - Prominent at top */}
              <InsightsWidget
                onCreateGoal={handleCreateGoalFromInsight}
                onSetBudget={handleSetBudgetFromInsight}
              />

              {/* Spending Trend Chart - Hero visualization */}
              {dashboardData?.spending_trend && (
                <SpendingTrendChart trend={dashboardData.spending_trend} />
              )}

              {/* Budget & Goals - Two column layout */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Budget Overview */}
                <BudgetOverviewWidget
                  totalSpent={totalSpentThisMonth}
                  categorySpending={categorySpending}
                />

                {/* Goals */}
                <GoalsWidget />
              </div>

              {/* Goal Suggestions from AI */}
              <GoalSuggestionsCard />

              {/* Unusual Transactions Alert - links to transactions page */}
              {totalUnreviewed > 0 && (
                <UnusualTransactionsBadge count={totalUnreviewed} />
              )}

              {/* Category Breakdown */}
              {dashboardData?.categories && (
                <CategoryBreakdownWidget categories={dashboardData.categories} />
              )}

              {/* Daily Timeline */}
              <DailyTransactionsTimeline period="month" />

              {/* Top Merchants */}
              {dashboardData?.top_merchants && dashboardData.top_merchants.length > 0 && (
                <TopMerchantsWidget merchants={dashboardData.top_merchants} />
              )}

              {/* Accounts Summary - Collapsible at bottom */}
              {balanceSummary && (
                <details className="bg-white rounded-xl shadow-sm border border-gray-200">
                  <summary className="px-6 py-4 cursor-pointer text-gray-900 font-medium hover:bg-gray-50">
                    Linked Accounts ({accounts.length})
                  </summary>
                  <div className="px-6 pb-4">
                    <AccountsSummary accounts={accounts} summary={balanceSummary} />
                  </div>
                </details>
              )}
            </div>
          )}

          {/* Modals for quick actions from Insights */}
          <GoalSettingModal
            isOpen={isGoalModalOpen}
            onClose={() => setIsGoalModalOpen(false)}
            onSave={handleSaveGoal}
          />

          <BudgetSettingModal
            isOpen={isBudgetModalOpen}
            onClose={() => setIsBudgetModalOpen(false)}
            onSave={saveBudgetSettings}
            currentSettings={budgetSettings}
            categorySpending={categorySpending}
          />

        </main>
      </div>
    </div>
  );
}

// Skeleton loader for instant perceived performance
function DashboardSkeleton() {
  return (
    <div className="space-y-6 max-w-6xl animate-pulse">
      {/* Trend chart skeleton */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-start mb-6">
          <div>
            <div className="h-6 w-40 bg-gray-200 rounded mb-2"></div>
            <div className="h-4 w-56 bg-gray-100 rounded"></div>
          </div>
          <div className="h-8 w-24 bg-gray-200 rounded-full"></div>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[1, 2, 3].map((i) => (
            <div key={i}>
              <div className="h-3 w-12 bg-gray-100 rounded mb-1"></div>
              <div className="h-8 w-24 bg-gray-200 rounded mb-1"></div>
              <div className="h-3 w-20 bg-gray-100 rounded"></div>
            </div>
          ))}
        </div>
        <div className="h-64 bg-gray-100 rounded"></div>
      </div>

      {/* Category breakdown skeleton */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="h-5 w-40 bg-gray-200 rounded mb-4"></div>
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="h-8 flex-1 bg-gray-100 rounded"></div>
              <div className="h-6 w-20 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      </div>

      {/* Timeline skeleton */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="h-5 w-40 bg-gray-200 rounded mb-4"></div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-gray-100 rounded"></div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Export the protected dashboard
export default function Dashboard() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
