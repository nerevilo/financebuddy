/**
 * Design System Configuration
 *
 * A comprehensive design system for FinanceBuddy.
 * Professional, accessible, and optimized for financial data visualization.
 */

export const designSystem = {
  /**
   * Color Palette
   *
   * Primary (Slate Blue): Trust, stability, professionalism
   * Secondary (Teal): Growth, balance, secondary actions
   * Success (Emerald): Positive values, gains, confirmations
   * Danger (Red): Warnings, negative values, destructive actions
   * Warning (Amber): Cautions, alerts, important notices
   * Neutral (Gray): Backgrounds, borders, subtle elements
   */
  colors: {
    // Primary - Slate Blue
    primary: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
      950: '#020617',
    },
    // Secondary - Teal
    secondary: {
      50: '#f0fdfa',
      100: '#ccfbf1',
      200: '#99f6e4',
      300: '#5eead4',
      400: '#2dd4bf',
      500: '#14b8a6',
      600: '#0d9488',
      700: '#0f766e',
      800: '#115e59',
      900: '#134e4a',
      950: '#042f2e',
    },
    // Success - Emerald
    success: {
      50: '#ecfdf5',
      100: '#d1fae5',
      200: '#a7f3d0',
      300: '#6ee7b7',
      400: '#34d399',
      500: '#10b981',
      600: '#059669',
      700: '#047857',
      800: '#065f46',
      900: '#064e3b',
      950: '#022c22',
    },
    // Danger - Red
    danger: {
      50: '#fef2f2',
      100: '#fee2e2',
      200: '#fecaca',
      300: '#fca5a5',
      400: '#f87171',
      500: '#ef4444',
      600: '#dc2626',
      700: '#b91c1c',
      800: '#991b1b',
      900: '#7f1d1d',
      950: '#450a0a',
    },
    // Warning - Amber
    warning: {
      50: '#fffbeb',
      100: '#fef3c7',
      200: '#fde68a',
      300: '#fcd34d',
      400: '#fbbf24',
      500: '#f59e0b',
      600: '#d97706',
      700: '#b45309',
      800: '#92400e',
      900: '#78350f',
      950: '#451a03',
    },
    // Neutral - Gray
    neutral: {
      50: '#fafafa',
      100: '#f5f5f5',
      200: '#e5e5e5',
      300: '#d4d4d4',
      400: '#a3a3a3',
      500: '#737373',
      600: '#525252',
      700: '#404040',
      800: '#262626',
      900: '#171717',
      950: '#0a0a0a',
    },
  },

  /**
   * Category Colors
   * Consistent colors for transaction categories
   */
  categoryColors: {
    groceries: '#10b981', // emerald-500
    dining: '#f59e0b', // amber-500
    shopping: '#8b5cf6', // violet-500
    entertainment: '#ec4899', // pink-500
    transportation: '#3b82f6', // blue-500
    utilities: '#6b7280', // gray-500
    healthcare: '#ef4444', // red-500
    travel: '#06b6d4', // cyan-500
    income: '#22c55e', // green-500
    transfer: '#94a3b8', // slate-400
    uncategorized: '#d1d5db', // gray-300
  },

  /**
   * Spacing Scale
   * Consistent spacing throughout the application
   */
  spacing: {
    xs: '0.5rem', // 8px
    sm: '0.75rem', // 12px
    md: '1rem', // 16px
    lg: '1.5rem', // 24px
    xl: '2rem', // 32px
    '2xl': '3rem', // 48px
    '3xl': '4rem', // 64px
  },

  /**
   * Border Radius
   * Consistent rounding for components
   */
  radius: {
    sm: '0.375rem', // 6px
    md: '0.5rem', // 8px
    lg: '0.75rem', // 12px
    xl: '1rem', // 16px
    '2xl': '1.5rem', // 24px
    full: '9999px',
  },

  /**
   * Typography Scale
   * Font sizes and line heights
   */
  typography: {
    xs: {
      fontSize: '0.75rem', // 12px
      lineHeight: '1rem', // 16px
    },
    sm: {
      fontSize: '0.875rem', // 14px
      lineHeight: '1.25rem', // 20px
    },
    base: {
      fontSize: '1rem', // 16px
      lineHeight: '1.5rem', // 24px
    },
    lg: {
      fontSize: '1.125rem', // 18px
      lineHeight: '1.75rem', // 28px
    },
    xl: {
      fontSize: '1.25rem', // 20px
      lineHeight: '1.75rem', // 28px
    },
    '2xl': {
      fontSize: '1.5rem', // 24px
      lineHeight: '2rem', // 32px
    },
    '3xl': {
      fontSize: '1.875rem', // 30px
      lineHeight: '2.25rem', // 36px
    },
  },

  /**
   * Shadows
   * Consistent elevation system
   */
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  },
} as const;

/**
 * Helper function to get category color
 */
export function getCategoryColor(category: string): string {
  const normalizedCategory = category.toLowerCase();
  return designSystem.categoryColors[normalizedCategory as keyof typeof designSystem.categoryColors] || designSystem.categoryColors.uncategorized;
}

/**
 * Helper function to get category icon name (Lucide)
 */
export function getCategoryIcon(category: string): string {
  const iconMap: Record<string, string> = {
    groceries: 'shopping-cart',
    dining: 'utensils',
    shopping: 'shopping-bag',
    entertainment: 'tv',
    transportation: 'car',
    utilities: 'zap',
    healthcare: 'heart-pulse',
    travel: 'plane',
    income: 'trending-up',
    transfer: 'arrow-left-right',
    uncategorized: 'help-circle',
  };

  const normalizedCategory = category.toLowerCase();
  return iconMap[normalizedCategory] || 'help-circle';
}

export type DesignSystem = typeof designSystem;
