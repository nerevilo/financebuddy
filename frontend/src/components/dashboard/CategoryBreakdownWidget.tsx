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

// Muted color palette for category bars (not super saturated)
const CATEGORY_COLORS: Record<string, { bar: string; hover: string }> = {
  'rent': { bar: 'bg-slate-500', hover: 'group-hover:bg-slate-400' },
  'mortgage': { bar: 'bg-slate-500', hover: 'group-hover:bg-slate-400' },
  'housing': { bar: 'bg-slate-500', hover: 'group-hover:bg-slate-400' },
  'groceries': { bar: 'bg-sage-500', hover: 'group-hover:bg-sage-400' },
  'grocery': { bar: 'bg-sage-500', hover: 'group-hover:bg-sage-400' },
  'supermarket': { bar: 'bg-sage-500', hover: 'group-hover:bg-sage-400' },
  'gas': { bar: 'bg-amber-400', hover: 'group-hover:bg-amber-300' },
  'gas station': { bar: 'bg-amber-400', hover: 'group-hover:bg-amber-300' },
  'fuel': { bar: 'bg-amber-400', hover: 'group-hover:bg-amber-300' },
  'retail': { bar: 'bg-rose-400', hover: 'group-hover:bg-rose-300' },
  'shopping': { bar: 'bg-rose-400', hover: 'group-hover:bg-rose-300' },
  'fast food': { bar: 'bg-orange-400', hover: 'group-hover:bg-orange-300' },
  'restaurant': { bar: 'bg-orange-400', hover: 'group-hover:bg-orange-300' },
  'dining': { bar: 'bg-orange-400', hover: 'group-hover:bg-orange-300' },
  'coffee': { bar: 'bg-amber-600', hover: 'group-hover:bg-amber-500' },
  'coffee shop': { bar: 'bg-amber-600', hover: 'group-hover:bg-amber-500' },
  'park': { bar: 'bg-sky-400', hover: 'group-hover:bg-sky-300' },
  'parking': { bar: 'bg-sky-400', hover: 'group-hover:bg-sky-300' },
  'utilities': { bar: 'bg-yellow-500', hover: 'group-hover:bg-yellow-400' },
  'electric': { bar: 'bg-yellow-500', hover: 'group-hover:bg-yellow-400' },
  'internet': { bar: 'bg-indigo-400', hover: 'group-hover:bg-indigo-300' },
  'phone': { bar: 'bg-indigo-400', hover: 'group-hover:bg-indigo-300' },
  'subscription': { bar: 'bg-purple-400', hover: 'group-hover:bg-purple-300' },
  'entertainment': { bar: 'bg-purple-400', hover: 'group-hover:bg-purple-300' },
  'healthcare': { bar: 'bg-red-400', hover: 'group-hover:bg-red-300' },
  'pharmacy': { bar: 'bg-red-400', hover: 'group-hover:bg-red-300' },
  'insurance': { bar: 'bg-teal-400', hover: 'group-hover:bg-teal-300' },
  'travel': { bar: 'bg-cyan-400', hover: 'group-hover:bg-cyan-300' },
  'hotel': { bar: 'bg-cyan-400', hover: 'group-hover:bg-cyan-300' },
  'education': { bar: 'bg-blue-400', hover: 'group-hover:bg-blue-300' },
  'transfer': { bar: 'bg-slate-400', hover: 'group-hover:bg-slate-300' },
  'rideshare': { bar: 'bg-violet-400', hover: 'group-hover:bg-violet-300' },
  'income': { bar: 'bg-sage-500', hover: 'group-hover:bg-sage-400' },
};

// Rotating colors for categories without specific colors
const FALLBACK_COLORS = [
  { bar: 'bg-slate-500', hover: 'group-hover:bg-slate-400' },
  { bar: 'bg-sage-500', hover: 'group-hover:bg-sage-400' },
  { bar: 'bg-amber-400', hover: 'group-hover:bg-amber-300' },
  { bar: 'bg-rose-400', hover: 'group-hover:bg-rose-300' },
  { bar: 'bg-sky-400', hover: 'group-hover:bg-sky-300' },
  { bar: 'bg-purple-400', hover: 'group-hover:bg-purple-300' },
  { bar: 'bg-teal-400', hover: 'group-hover:bg-teal-300' },
  { bar: 'bg-orange-400', hover: 'group-hover:bg-orange-300' },
];

function getCategoryColor(category: string, index: number): { bar: string; hover: string } {
  const lower = category.toLowerCase();
  // Exact match first
  if (CATEGORY_COLORS[lower]) return CATEGORY_COLORS[lower];
  // Partial match
  for (const [key, colors] of Object.entries(CATEGORY_COLORS)) {
    if (lower.includes(key) || key.includes(lower)) return colors;
  }
  // Fallback: rotate through colors based on index
  return FALLBACK_COLORS[index % FALLBACK_COLORS.length];
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
      <div className="bg-white rounded-xl shadow border border-slate-200 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold tracking-tight text-slate-900">Where Your Money Went</h3>
          <span className="text-xs text-slate-400">tap for details</span>
        </div>

        <div className="space-y-1">
          {topCategories.map((category, index) => {
            const emoji = getCategoryEmoji(category.category, category.emoji);
            const colors = getCategoryColor(category.category, index);
            return (
              <button
                key={index}
                onClick={() => setSelectedCategory({ category: category.category, emoji })}
                onMouseEnter={() => prefetchCategoryMerchants(category.category)}
                className="w-full flex items-center gap-2 py-1.5 px-2 -mx-2 rounded-lg hover:bg-slate-50 group transition-colors"
              >
                {/* Emoji */}
                <span className="text-base w-6 text-center flex-shrink-0">{emoji}</span>

                {/* Category name */}
                <span className="text-sm text-slate-700 capitalize truncate w-28 text-left flex-shrink-0">
                  {category.category}
                </span>

                {/* Bar + Amount */}
                <div className="flex-1 flex items-center gap-2">
                  <div className="flex-1 bg-slate-100 rounded-full h-5 overflow-hidden relative">
                    <div
                      className={`h-full ${colors.bar} ${colors.hover} transition-colors rounded-full`}
                      style={{ width: `${Math.max(category.percentage, 3)}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-slate-900 w-16 text-right flex-shrink-0">
                    {formatCurrency(category.amount)}
                  </span>
                </div>

                {/* Chevron */}
                <svg
                  className="w-4 h-4 text-slate-300 group-hover:text-slate-500 transition-colors flex-shrink-0"
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
        <div className="mt-3 pt-3 border-t border-slate-100 flex justify-between items-center">
          <span className="text-sm text-slate-500">Total spent</span>
          <span className="text-base font-semibold text-slate-900">{formatCurrency(data.total)}</span>
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
