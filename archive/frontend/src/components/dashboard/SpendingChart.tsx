'use client';

import { DonutChart, Legend } from '@tremor/react';
import { formatCurrency, getCategoryColor } from '@/lib/utils';

interface SpendingCategory {
  category: string;
  total: number;
  count: number;
  percentage: number;
}

interface SpendingChartProps {
  categories: SpendingCategory[];
  totalSpending: number;
}

export function SpendingChart({ categories, totalSpending }: SpendingChartProps) {
  const chartData = categories.map((cat) => ({
    name: cat.category.charAt(0).toUpperCase() + cat.category.slice(1),
    value: cat.total,
    percentage: cat.percentage,
  }));

  const colors = categories.map((cat) => {
    const colorMap: Record<string, string> = {
      groceries: 'emerald',
      dining: 'amber',
      shopping: 'violet',
      entertainment: 'pink',
      transportation: 'blue',
      utilities: 'gray',
      healthcare: 'red',
      travel: 'cyan',
      income: 'green',
      transfer: 'slate',
    };
    return colorMap[cat.category.toLowerCase()] || 'gray';
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-neutral-200 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 mb-4">Spending by Category</h3>

      <div className="flex flex-col lg:flex-row items-center gap-6">
        <div className="w-full lg:w-1/2">
          <DonutChart
            data={chartData}
            category="value"
            index="name"
            valueFormatter={formatCurrency}
            colors={colors}
            className="h-52"
            showAnimation
          />
        </div>

        <div className="w-full lg:w-1/2">
          <div className="space-y-3">
            {categories.slice(0, 6).map((cat) => (
              <div key={cat.category} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: getCategoryColor(cat.category) }}
                  />
                  <span className="text-sm text-neutral-600 capitalize">{cat.category}</span>
                </div>
                <div className="text-right">
                  <span className="text-sm font-medium text-neutral-900">
                    {formatCurrency(cat.total)}
                  </span>
                  <span className="text-xs text-neutral-500 ml-2">({cat.percentage}%)</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-neutral-100">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-neutral-600">Total Spending</span>
              <span className="text-lg font-bold text-neutral-900">
                {formatCurrency(totalSpending)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
