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

  const getEmoji = (category: string) => {
    const map: {[key: string]: string} = {
      'groceries': '🛒',
      'dining': '🍔',
      'fast food': '🍔',
      'gas': '⛽',
      'software': '💻',
      'travel': '✈️',
      'education': '🏫',
      'coffee': '☕',
      'shopping': '🛍️',
    };
    const key = Object.keys(map).find(k => category.toLowerCase().includes(k));
    return key ? map[key] : '📦';
  };

  const getTrendIcon = (trend: string) => {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '↔';
  };

  // Get top 6 categories by this month spending
  const topCategories = Object.entries(comparison.categories)
    .sort(([, a], [, b]) => b.this_month - a.this_month)
    .slice(0, 6);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">This Month vs Last Month</h3>

      <div className="space-y-3">
        {topCategories.map(([category, data]) => (
          <div key={category} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
            <div className="flex items-center gap-2">
              <span className="text-xl">{getEmoji(category)}</span>
              <span className="text-sm font-medium text-gray-700 capitalize">{category}</span>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-sm font-semibold text-gray-900">
                  {formatCurrency(data.this_month)}
                </div>
                <div className="text-xs text-gray-500">
                  was {formatCurrency(data.last_month)}
                </div>
              </div>

              <div className={`text-sm font-medium px-2 py-1 rounded ${
                data.trend === 'up' ? 'bg-red-100 text-red-700' :
                data.trend === 'down' ? 'bg-green-100 text-green-700' :
                'bg-gray-100 text-gray-600'
              }`}>
                {getTrendIcon(data.trend)} {Math.abs(data.change_pct).toFixed(0)}%
              </div>
            </div>
          </div>
        ))}
      </div>

      {Object.keys(comparison.categories).length > 6 && (
        <div className="mt-4 text-center">
          <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            View All Categories →
          </button>
        </div>
      )}
    </div>
  );
}
