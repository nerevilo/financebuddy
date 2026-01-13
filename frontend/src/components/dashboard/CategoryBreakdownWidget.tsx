'use client';

import { useState } from 'react';
import { CategoryDrillDownModal } from './CategoryDrillDownModal';
import { prefetchCategoryMerchants } from '@/lib/hooks';

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

// Better emoji mapping
const CATEGORY_EMOJIS: Record<string, string> = {
  'rent': '🏠',
  'mortgage': '🏠',
  'housing': '🏠',
  'transfer': '💸',
  'transfer to stock broker': '📈',
  'investment': '📈',
  'stocks': '📈',
  'groceries': '🛒',
  'grocery': '🛒',
  'supermarket': '🛒',
  'gas': '⛽',
  'gas station': '⛽',
  'fuel': '⛽',
  'retail': '🛍️',
  'shopping': '🛍️',
  'fast food': '🍔',
  'restaurant': '🍽️',
  'dining': '🍽️',
  'coffee': '☕',
  'coffee shop': '☕',
  'park': '🅿️',
  'parking': '🅿️',
  'utilities': '💡',
  'electric': '💡',
  'internet': '📡',
  'phone': '📱',
  'subscription': '📺',
  'entertainment': '🎬',
  'healthcare': '🏥',
  'pharmacy': '💊',
  'insurance': '🛡️',
  'travel': '✈️',
  'hotel': '🏨',
  'education': '📚',
};

function getCategoryEmoji(category: string, fallback: string): string {
  const lower = category.toLowerCase();
  // Exact match first
  if (CATEGORY_EMOJIS[lower]) return CATEGORY_EMOJIS[lower];
  // Partial match
  for (const [key, emoji] of Object.entries(CATEGORY_EMOJIS)) {
    if (lower.includes(key) || key.includes(lower)) return emoji;
  }
  return fallback === '📦' ? '💳' : fallback; // Replace generic box with card
}

export function CategoryBreakdownWidget({ categories: data }: CategoryBreakdownWidgetProps) {
  const [selectedCategory, setSelectedCategory] = useState<{category: string; emoji: string} | null>(null);

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);

  const topCategories = data.categories.slice(0, 8);

  return (
    <>
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold text-gray-900">Where Your Money Went</h3>
          <span className="text-xs text-gray-400">tap for details</span>
        </div>

        <div className="space-y-1">
          {topCategories.map((category, index) => {
            const emoji = getCategoryEmoji(category.category, category.emoji);
            return (
              <button
                key={index}
                onClick={() => setSelectedCategory({ category: category.category, emoji })}
                onMouseEnter={() => prefetchCategoryMerchants(category.category)}
                className="w-full flex items-center gap-2 py-1.5 px-2 -mx-2 rounded-lg hover:bg-blue-50 group transition-colors"
              >
                {/* Emoji */}
                <span className="text-base w-6 text-center flex-shrink-0">{emoji}</span>

                {/* Category name */}
                <span className="text-sm text-gray-700 capitalize truncate w-28 text-left flex-shrink-0">
                  {category.category}
                </span>

                {/* Bar + Amount */}
                <div className="flex-1 flex items-center gap-2">
                  <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden relative">
                    <div
                      className="h-full bg-blue-500 group-hover:bg-blue-600 transition-colors rounded-full"
                      style={{ width: `${Math.max(category.percentage, 3)}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-gray-900 w-16 text-right flex-shrink-0">
                    {formatCurrency(category.amount)}
                  </span>
                </div>

                {/* Chevron */}
                <svg
                  className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            );
          })}
        </div>

        {/* Total */}
        <div className="mt-3 pt-3 border-t border-gray-100 flex justify-between items-center">
          <span className="text-sm text-gray-500">Total spent</span>
          <span className="text-base font-semibold text-gray-900">{formatCurrency(data.total)}</span>
        </div>
      </div>

      {/* Drill-down Modal */}
      {selectedCategory && (
        <CategoryDrillDownModal
          category={selectedCategory.category}
          emoji={selectedCategory.emoji}
          isOpen={!!selectedCategory}
          onClose={() => setSelectedCategory(null)}
        />
      )}
    </>
  );
}
