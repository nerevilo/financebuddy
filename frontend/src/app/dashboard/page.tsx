'use client';

import { useEffect, useState } from 'react';
import { getDashboardStats } from '@/lib/api';
import { InsightCard } from '@/components/dashboard/InsightCard';
import { SpendingVelocity } from '@/components/dashboard/SpendingVelocity';
import { MonthlyComparison } from '@/components/dashboard/MonthlyComparison';
import { CategoryBreakdownWidget } from '@/components/dashboard/CategoryBreakdownWidget';
import { TopMerchantsWidget } from '@/components/dashboard/TopMerchantsWidget';
import { RecentTransactionsWidget } from '@/components/dashboard/RecentTransactionsWidget';

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const stats = await getDashboardStats();
        setData(stats);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
        setError('Failed to load dashboard. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your spending insights...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-sm border border-red-200 p-8 max-w-md">
          <div className="text-red-600 text-center">
            <div className="text-5xl mb-4">⚠️</div>
            <h2 className="text-xl font-bold mb-2">Unable to Load Dashboard</h2>
            <p className="text-gray-600 mb-4">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Finance Buddy</h1>
              <p className="text-sm text-gray-500">
                {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-lg hover:bg-gray-100 transition">
                Settings
              </button>
              <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-semibold">
                U
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Daily Insight - Prominent at Top */}
        {data.insight && (
          <InsightCard insight={data.insight} />
        )}

        {/* Spending Velocity + Monthly Comparison */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {data.velocity && (
            <SpendingVelocity velocity={data.velocity} />
          )}
          {data.comparison && (
            <MonthlyComparison comparison={data.comparison} />
          )}
        </div>

        {/* Category Breakdown - Full Width */}
        {data.categories && (
          <CategoryBreakdownWidget categories={data.categories} />
        )}

        {/* Bottom Row: Top Merchants + Recent Transactions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {data.top_merchants && data.top_merchants.length > 0 && (
            <TopMerchantsWidget merchants={data.top_merchants} />
          )}
          {data.recent_transactions && data.recent_transactions.length > 0 && (
            <RecentTransactionsWidget transactions={data.recent_transactions} />
          )}
        </div>

        {/* No Data State */}
        {data.categories.categories.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-6xl mb-4">📊</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">No Spending Data Yet</h2>
            <p className="text-gray-600 max-w-md mx-auto">
              Connect your bank accounts to start tracking your spending and get personalized insights.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
