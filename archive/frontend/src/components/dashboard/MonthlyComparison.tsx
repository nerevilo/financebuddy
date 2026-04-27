'use client';

interface MonthlyComparisonProps {
  comparison: {
    month: string;
    last_month: string;
    categories: {
      [key: string]: {
        this_month: number;
        last_month: number;
        change: number;
        change_pct: number;
        trend: 'up' | 'down' | 'same';
      };
    };
  };
}

export function MonthlyComparison({ comparison }: MonthlyComparisonProps) {
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const getCategoryColor = (category: string) => {
    const colors: {[key: string]: string} = {
      'groceries': 'bg-success-100 text-success-700',
      'dining': 'bg-warning-100 text-warning-700',
      'fast food': 'bg-warning-100 text-warning-700',
      'gas': 'bg-slate-100 text-slate-700',
      'software': 'bg-violet-100 text-violet-700',
      'travel': 'bg-sky-100 text-sky-700',
      'education': 'bg-primary-100 text-primary-700',
      'coffee': 'bg-warning-100 text-warning-700',
      'shopping': 'bg-pink-100 text-pink-700',
    };
    const key = Object.keys(colors).find(k => category.toLowerCase().includes(k));
    return key ? colors[key] : 'bg-neutral-100 text-neutral-700';
  };

  // Get top 6 categories by this month spending
  const topCategories = Object.entries(comparison.categories)
    .sort(([, a], [, b]) => b.this_month - a.this_month)
    .slice(0, 6);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-neutral-200 p-6">
      <h3 className="text-lg font-semibold text-neutral-900 mb-4">This Month vs Last Month</h3>

      <div className="space-y-3">
        {topCategories.map(([category, data]) => (
          <div key={category} className="flex items-center justify-between py-2 border-b border-neutral-100 last:border-0">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-semibold ${getCategoryColor(category)}`}>
                {category.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm font-medium text-neutral-700 capitalize">{category}</span>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-sm font-semibold text-neutral-900">
                  {formatCurrency(data.this_month)}
                </div>
                <div className="text-xs text-neutral-500">
                  was {formatCurrency(data.last_month)}
                </div>
              </div>

              <div className={`text-sm font-medium px-2 py-1 rounded flex items-center gap-1 ${
                data.trend === 'up' ? 'bg-danger-100 text-danger-600' :
                data.trend === 'down' ? 'bg-success-100 text-success-600' :
                'bg-neutral-100 text-neutral-600'
              }`}>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={
                    data.trend === 'up' ? "M5 15l7-7 7 7" :
                    data.trend === 'down' ? "M19 9l-7 7-7-7" :
                    "M5 12h14"
                  } />
                </svg>
                {Math.abs(data.change_pct).toFixed(0)}%
              </div>
            </div>
          </div>
        ))}
      </div>

      {Object.keys(comparison.categories).length > 6 && (
        <div className="mt-4 text-center">
          <button className="text-sm text-primary-600 hover:text-primary-700 font-medium">
            View All Categories →
          </button>
        </div>
      )}
    </div>
  );
}
