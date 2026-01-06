'use client';

import { formatCurrency, formatPercent } from '@/lib/utils';

interface CategoryComparison {
  category: string;
  current: number;
  previous: number;
  change: number;
  change_percentage: number;
}

interface PeriodComparisonProps {
  currentTotal: number;
  previousTotal: number;
  changeAmount: number;
  changePercentage: number;
  categories: CategoryComparison[];
}

export function PeriodComparison({
  currentTotal,
  previousTotal,
  changeAmount,
  changePercentage,
  categories,
}: PeriodComparisonProps) {
  const isIncrease = changeAmount > 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">vs Last Month</h3>

      {/* Overall Change */}
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">This Month</span>
          <span className="text-lg font-bold text-gray-900">{formatCurrency(currentTotal)}</span>
        </div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Last Month</span>
          <span className="text-sm text-gray-500">{formatCurrency(previousTotal)}</span>
        </div>
        <div className="border-t border-gray-200 pt-2 mt-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-600">Change</span>
            <span
              className={`text-sm font-bold ${isIncrease ? 'text-red-600' : 'text-green-600'}`}
            >
              {isIncrease ? '+' : ''}{formatCurrency(changeAmount)} ({formatPercent(changePercentage)})
            </span>
          </div>
        </div>
      </div>

      {/* Category Changes */}
      <div className="space-y-3">
        <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">By Category</p>
        {categories.slice(0, 6).map((cat) => {
          const isUp = cat.change > 0;
          return (
            <div
              key={cat.category}
              className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0"
            >
              <div>
                <p className="text-sm font-medium text-gray-900 capitalize">{cat.category}</p>
                <p className="text-xs text-gray-500">
                  {formatCurrency(cat.previous)} → {formatCurrency(cat.current)}
                </p>
              </div>
              <div
                className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                  isUp
                    ? 'bg-red-50 text-red-700'
                    : cat.change < 0
                    ? 'bg-green-50 text-green-700'
                    : 'bg-gray-50 text-gray-700'
                }`}
              >
                {isUp ? '↑' : cat.change < 0 ? '↓' : '–'}
                {Math.abs(cat.change_percentage).toFixed(0)}%
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
