'use client';

interface CategoryBreakdownWidgetProps {
  categories: {
    total: number;
    categories: Array<{
      category: string;
      amount: number;
      count: number;
      percentage: number;
      emoji: string;
    }>;
  };
}

export function CategoryBreakdownWidget({ categories: data }: CategoryBreakdownWidgetProps) {
  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  const topCategories = data.categories.slice(0, 8);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Category Breakdown (This Month)</h3>

      <div className="space-y-3">
        {topCategories.map((category, index) => (
          <div key={index} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="text-lg">{category.emoji}</span>
                <span className="font-medium text-gray-700 capitalize">{category.category}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-semibold text-gray-900">{formatCurrency(category.amount)}</span>
                <span className="text-gray-500 text-xs">{category.percentage.toFixed(0)}%</span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-blue-600"
                style={{ width: `${category.percentage}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      {data.categories.length > 8 && (
        <div className="mt-4 text-center">
          <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            View All Categories →
          </button>
        </div>
      )}
    </div>
  );
}
