import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

export function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(date));
}

export function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    groceries: '#10B981',
    dining: '#F59E0B',
    shopping: '#8B5CF6',
    entertainment: '#EC4899',
    transportation: '#3B82F6',
    utilities: '#6B7280',
    healthcare: '#EF4444',
    travel: '#06B6D4',
    income: '#22C55E',
    transfer: '#94A3B8',
    uncategorized: '#D1D5DB',
  };

  return colors[category.toLowerCase()] || '#6B7280';
}
