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
  // Pastel macaron color palette
  const colors: Record<string, string> = {
    groceries: '#6DB88A',    // Sage mint
    dining: '#F5CE4D',       // Butter yellow
    shopping: '#BBA7F2',     // Soft lavender
    entertainment: '#FFB3B3', // Soft pink
    transportation: '#A18AE8', // Lavender
    utilities: '#B3B3AA',    // Warm gray
    healthcare: '#F07878',   // Soft coral
    travel: '#8ECCA6',       // Mint
    income: '#B3DEC2',       // Light sage
    transfer: '#D9D9D2',     // Light beige
    uncategorized: '#E8E8E3', // Cream gray
  };

  return colors[category.toLowerCase()] || '#B3B3AA';
}
