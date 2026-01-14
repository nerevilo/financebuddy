'use client';

import { useState } from 'react';
import { useBudgetSettings } from './useBudgetSettings';
import { BudgetSettingModal, BudgetSettings } from './BudgetSettingModal';
import { formatCurrency } from '@/lib/utils';

interface BudgetOverviewWidgetProps {
  totalSpent: number;
  categorySpending: { category: string; amount: number }[];
}

export function BudgetOverviewWidget({ totalSpent, categorySpending }: BudgetOverviewWidgetProps) {
  const { settings, saveSettings, hasBudget, isLoading } = useBudgetSettings();
  const [isModalOpen, setIsModalOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="h-5 w-32 bg-gray-200 rounded mb-4"></div>
          <div className="h-24 bg-gray-100 rounded-lg"></div>
        </div>
      </div>
    );
  }

  const totalBudget = settings?.totalMonthlyBudget || 0;
  const percentSpent = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;
  const remaining = totalBudget - totalSpent;
  const alertThreshold = settings?.alertThreshold || 80;
  const isOverBudget = percentSpent > 100;
  const isNearLimit = percentSpent >= alertThreshold && !isOverBudget;

  // Find categories that are over or near their budget
  const categoryAlerts = settings?.categoryBudgets
    .map(cb => {
      const spent = categorySpending.find(
        cs => cs.category.toLowerCase() === cb.category.toLowerCase()
      )?.amount || 0;
      const percent = cb.amount > 0 ? (spent / cb.amount) * 100 : 0;
      return {
        category: cb.category,
        budget: cb.amount,
        spent,
        percent,
        isOver: percent > 100,
        isNear: percent >= alertThreshold && percent < 100,
      };
    })
    .filter(ca => ca.isOver || ca.isNear)
    .sort((a, b) => b.percent - a.percent) || [];

  const handleSave = (newSettings: BudgetSettings) => {
    saveSettings(newSettings);
  };

  return (
    <>
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <h2 className="text-lg font-semibold text-gray-900">Monthly Budget</h2>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="text-sm font-medium text-blue-600 hover:text-blue-700 transition"
          >
            {hasBudget ? 'Edit' : 'Set Budget'}
          </button>
        </div>

        <div className="p-6">
          {!hasBudget ? (
            // Empty state
            <div className="text-center py-4">
              <div className="w-12 h-12 mx-auto mb-3 bg-green-50 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-gray-600 mb-1">No budget set</p>
              <p className="text-sm text-gray-500 mb-3">Set a monthly budget to track your spending</p>
              <button
                onClick={() => setIsModalOpen(true)}
                className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg font-medium hover:bg-green-700 transition"
              >
                Set Monthly Budget
              </button>
            </div>
          ) : (
            // Budget overview
            <div className="space-y-4">
              {/* Main progress */}
              <div>
                <div className="flex items-end justify-between mb-2">
                  <div>
                    <p className="text-sm text-gray-500">Spent this month</p>
                    <p className={`text-2xl font-bold ${isOverBudget ? 'text-red-600' : 'text-gray-900'}`}>
                      {formatCurrency(totalSpent)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-500">Budget</p>
                    <p className="text-lg font-semibold text-gray-900">{formatCurrency(totalBudget)}</p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="relative h-4 bg-gray-100 rounded-full overflow-hidden">
                  {/* Alert threshold marker */}
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-orange-400 z-10"
                    style={{ left: `${alertThreshold}%` }}
                  />
                  {/* Progress */}
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isOverBudget
                        ? 'bg-red-500'
                        : isNearLimit
                        ? 'bg-orange-500'
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(100, percentSpent)}%` }}
                  />
                </div>

                <div className="flex justify-between mt-2 text-sm">
                  <span className={`font-medium ${isOverBudget ? 'text-red-600' : isNearLimit ? 'text-orange-600' : 'text-green-600'}`}>
                    {percentSpent.toFixed(0)}% used
                  </span>
                  <span className={remaining >= 0 ? 'text-gray-600' : 'text-red-600'}>
                    {remaining >= 0
                      ? `${formatCurrency(remaining)} remaining`
                      : `${formatCurrency(Math.abs(remaining))} over budget`}
                  </span>
                </div>
              </div>

              {/* Category alerts */}
              {categoryAlerts.length > 0 && (
                <div className="pt-3 border-t border-gray-100">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                    Category Alerts
                  </p>
                  <div className="space-y-2">
                    {categoryAlerts.slice(0, 3).map((alert) => (
                      <div
                        key={alert.category}
                        className={`flex items-center justify-between p-2 rounded-lg text-sm ${
                          alert.isOver ? 'bg-red-50' : 'bg-orange-50'
                        }`}
                      >
                        <span className={alert.isOver ? 'text-red-700' : 'text-orange-700'}>
                          {alert.category}
                        </span>
                        <span className={`font-medium ${alert.isOver ? 'text-red-600' : 'text-orange-600'}`}>
                          {formatCurrency(alert.spent)} / {formatCurrency(alert.budget)}
                        </span>
                      </div>
                    ))}
                    {categoryAlerts.length > 3 && (
                      <p className="text-xs text-gray-500 text-center">
                        +{categoryAlerts.length - 3} more categories
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Budget Modal */}
      <BudgetSettingModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSave}
        currentSettings={settings}
        categorySpending={categorySpending}
      />
    </>
  );
}
