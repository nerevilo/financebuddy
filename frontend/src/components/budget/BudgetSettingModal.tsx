'use client';

import { useState, useEffect } from 'react';
import { useCategories } from '@/lib/hooks';
import { formatCurrency } from '@/lib/utils';

export interface CategoryBudget {
  category: string;
  amount: number;
  enabled: boolean;
}

export interface BudgetSettings {
  totalMonthlyBudget: number;
  categoryBudgets: CategoryBudget[];
  alertThreshold: number; // 0-100, e.g., 80 means alert at 80% spent
  updatedAt: string;
}

interface BudgetSettingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (settings: BudgetSettings) => void;
  currentSettings?: BudgetSettings | null;
  categorySpending?: { category: string; amount: number }[];
}

const CATEGORY_EMOJIS: Record<string, string> = {
  'food & drink': '🍽️',
  'dining': '🍽️',
  'groceries': '🛒',
  'shopping': '🛍️',
  'transportation': '🚗',
  'travel': '✈️',
  'entertainment': '🎬',
  'utilities': '💡',
  'healthcare': '🏥',
  'personal care': '💅',
  'education': '📚',
  'subscriptions': '📱',
  'general merchandise': '📦',
  'general services': '🔧',
  'home improvement': '🏠',
  'recreation': '🎮',
};

const getEmoji = (category: string): string => {
  const lower = category.toLowerCase();
  return CATEGORY_EMOJIS[lower] || '📋';
};

export function BudgetSettingModal({
  isOpen,
  onClose,
  onSave,
  currentSettings,
  categorySpending = [],
}: BudgetSettingModalProps) {
  const { categories } = useCategories();
  const [totalBudget, setTotalBudget] = useState('');
  const [alertThreshold, setAlertThreshold] = useState(80);
  const [categoryBudgets, setCategoryBudgets] = useState<CategoryBudget[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Initialize from current settings or create defaults
  useEffect(() => {
    if (currentSettings) {
      setTotalBudget(currentSettings.totalMonthlyBudget.toString());
      setAlertThreshold(currentSettings.alertThreshold);
      setCategoryBudgets(currentSettings.categoryBudgets);
    } else if (categories.length > 0) {
      // Initialize with all categories, no budgets set
      const defaultBudgets = categories.map(cat => ({
        category: cat.name,
        amount: 0,
        enabled: false,
      }));
      setCategoryBudgets(defaultBudgets);
    }
  }, [currentSettings, categories, isOpen]);

  const handleCategoryBudgetChange = (category: string, amount: string) => {
    setCategoryBudgets(prev =>
      prev.map(cb =>
        cb.category === category
          ? { ...cb, amount: parseFloat(amount) || 0, enabled: parseFloat(amount) > 0 }
          : cb
      )
    );
  };

  const handleToggleCategory = (category: string) => {
    setCategoryBudgets(prev =>
      prev.map(cb =>
        cb.category === category
          ? { ...cb, enabled: !cb.enabled }
          : cb
      )
    );
  };

  const totalCategoryBudgets = categoryBudgets
    .filter(cb => cb.enabled)
    .reduce((sum, cb) => sum + cb.amount, 0);

  const remainingBudget = (parseFloat(totalBudget) || 0) - totalCategoryBudgets;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);

    try {
      const settings: BudgetSettings = {
        totalMonthlyBudget: parseFloat(totalBudget) || 0,
        categoryBudgets: categoryBudgets.filter(cb => cb.enabled && cb.amount > 0),
        alertThreshold,
        updatedAt: new Date().toISOString(),
      };

      onSave(settings);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  // Get spending for a category
  const getSpending = (category: string) => {
    const found = categorySpending.find(
      cs => cs.category.toLowerCase() === category.toLowerCase()
    );
    return found?.amount || 0;
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full m-4 max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Monthly Budget</h2>
              <p className="text-sm text-gray-500">Set spending limits for the month</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-200px)]">
            {/* Total Budget */}
            <div className="bg-green-50 rounded-xl p-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Total Monthly Budget
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 text-lg">$</span>
                <input
                  type="number"
                  value={totalBudget}
                  onChange={(e) => setTotalBudget(e.target.value)}
                  placeholder="0.00"
                  min="0"
                  step="0.01"
                  className="w-full pl-10 pr-4 py-3 text-2xl font-semibold border border-green-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition"
                />
              </div>
              {totalBudget && parseFloat(totalBudget) > 0 && (
                <div className="mt-3 flex justify-between text-sm">
                  <span className="text-gray-600">Allocated to categories</span>
                  <span className={remainingBudget < 0 ? 'text-red-600 font-medium' : 'text-gray-900'}>
                    {formatCurrency(totalCategoryBudgets)} ({remainingBudget >= 0 ? formatCurrency(remainingBudget) + ' unallocated' : formatCurrency(Math.abs(remainingBudget)) + ' over'})
                  </span>
                </div>
              )}
            </div>

            {/* Alert Threshold */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Alert me when I reach
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="50"
                  max="100"
                  step="5"
                  value={alertThreshold}
                  onChange={(e) => setAlertThreshold(parseInt(e.target.value))}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <span className="text-lg font-semibold text-gray-900 w-16 text-right">
                  {alertThreshold}%
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                You'll get alerts when spending reaches {alertThreshold}% of your budget
              </p>
            </div>

            {/* Category Budgets */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-3">Category Budgets</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {categoryBudgets.map((cb) => {
                  const spending = getSpending(cb.category);
                  const percentUsed = cb.amount > 0 ? (spending / cb.amount) * 100 : 0;
                  const isOverBudget = percentUsed > 100;

                  return (
                    <div
                      key={cb.category}
                      className={`flex items-center gap-3 p-3 rounded-lg border transition ${
                        cb.enabled
                          ? 'bg-white border-gray-200'
                          : 'bg-gray-50 border-gray-100'
                      }`}
                    >
                      {/* Enable toggle */}
                      <button
                        type="button"
                        onClick={() => handleToggleCategory(cb.category)}
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition ${
                          cb.enabled
                            ? 'bg-green-500 border-green-500'
                            : 'border-gray-300'
                        }`}
                      >
                        {cb.enabled && (
                          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </button>

                      {/* Category info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{getEmoji(cb.category)}</span>
                          <span className={`font-medium truncate ${cb.enabled ? 'text-gray-900' : 'text-gray-500'}`}>
                            {cb.category}
                          </span>
                        </div>
                        {cb.enabled && cb.amount > 0 && (
                          <div className="mt-1">
                            <div className="flex justify-between text-xs mb-0.5">
                              <span className="text-gray-500">{formatCurrency(spending)} spent</span>
                              <span className={isOverBudget ? 'text-red-600' : 'text-gray-500'}>
                                {percentUsed.toFixed(0)}%
                              </span>
                            </div>
                            <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  isOverBudget ? 'bg-red-500' : percentUsed > 80 ? 'bg-orange-500' : 'bg-green-500'
                                }`}
                                style={{ width: `${Math.min(100, percentUsed)}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Budget input */}
                      <div className="relative w-28">
                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                        <input
                          type="number"
                          value={cb.amount || ''}
                          onChange={(e) => handleCategoryBudgetChange(cb.category, e.target.value)}
                          placeholder="0"
                          min="0"
                          step="1"
                          disabled={!cb.enabled}
                          className="w-full pl-6 pr-2 py-1.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 disabled:bg-gray-100 disabled:text-gray-400 transition"
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-6 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 transition"
            >
              {isSaving ? 'Saving...' : 'Save Budget'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
