'use client';

import { useEffect, useState } from 'react';
import {
  TellerConnect,
  SpendingChart,
  TopMerchants,
  AccountsSummary,
  PeriodComparison,
} from '@/components/dashboard';
import {
  getAccounts,
  getBalanceSummary,
  getSpendingByCategory,
  getSpendingByMerchant,
  getPeriodComparison,
  getIncomeExpenses,
} from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

export default function Dashboard() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [balanceSummary, setBalanceSummary] = useState<any>(null);
  const [spendingByCategory, setSpendingByCategory] = useState<any>(null);
  const [spendingByMerchant, setSpendingByMerchant] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [incomeExpenses, setIncomeExpenses] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [accountsData, summaryData, categoryData, merchantData, comparisonData, ieData] =
        await Promise.all([
          getAccounts().catch(() => []),
          getBalanceSummary().catch(() => null),
          getSpendingByCategory().catch(() => null),
          getSpendingByMerchant().catch(() => null),
          getPeriodComparison().catch(() => null),
          getIncomeExpenses().catch(() => null),
        ]);

      setAccounts(accountsData);
      setBalanceSummary(summaryData);
      setSpendingByCategory(categoryData);
      setSpendingByMerchant(merchantData);
      setComparison(comparisonData);
      setIncomeExpenses(ieData);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleConnectionSuccess = () => {
    // Refresh data after connecting a new bank
    fetchData();
  };

  const hasAccounts = accounts.length > 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">FinTrack</h1>
              <p className="text-sm text-gray-500">Personal Finance Dashboard</p>
            </div>
            <TellerConnect onSuccess={handleConnectionSuccess} />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
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
            <p className="text-gray-600 mb-8 max-w-md mx-auto">
              Link your bank accounts and credit cards to start tracking your spending and see
              where your money goes.
            </p>
            <TellerConnect onSuccess={handleConnectionSuccess} />
            <p className="text-sm text-gray-500 mt-4">
              Sandbox mode: Use username <code className="bg-gray-100 px-1 rounded">username</code>{' '}
              and password <code className="bg-gray-100 px-1 rounded">password</code>
            </p>
          </div>
        ) : (
          /* Dashboard Content */
          <div className="space-y-6">
            {/* Summary Cards */}
            {incomeExpenses && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <p className="text-sm text-gray-500">Net Worth</p>
                  <p
                    className={`text-2xl font-bold ${
                      balanceSummary?.total_balance >= 0 ? 'text-gray-900' : 'text-red-600'
                    }`}
                  >
                    {formatCurrency(balanceSummary?.total_balance || 0)}
                  </p>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <p className="text-sm text-gray-500">Income (This Month)</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(incomeExpenses.income)}
                  </p>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <p className="text-sm text-gray-500">Spending (This Month)</p>
                  <p className="text-2xl font-bold text-red-600">
                    {formatCurrency(incomeExpenses.expenses)}
                  </p>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <p className="text-sm text-gray-500">Savings Rate</p>
                  <p
                    className={`text-2xl font-bold ${
                      incomeExpenses.savings_rate >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {incomeExpenses.savings_rate.toFixed(1)}%
                  </p>
                </div>
              </div>
            )}

            {/* Main Dashboard Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Spending by Category */}
              <div className="lg:col-span-2">
                {spendingByCategory && (
                  <SpendingChart
                    categories={spendingByCategory.categories}
                    totalSpending={spendingByCategory.total_spending}
                  />
                )}
              </div>

              {/* Accounts */}
              <div>
                {balanceSummary && (
                  <AccountsSummary accounts={accounts} summary={balanceSummary} />
                )}
              </div>
            </div>

            {/* Second Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Merchants */}
              {spendingByMerchant && (
                <TopMerchants merchants={spendingByMerchant.merchants} />
              )}

              {/* Period Comparison */}
              {comparison && (
                <PeriodComparison
                  currentTotal={comparison.current_total}
                  previousTotal={comparison.previous_total}
                  changeAmount={comparison.change_amount}
                  changePercentage={comparison.change_percentage}
                  categories={comparison.categories}
                />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
