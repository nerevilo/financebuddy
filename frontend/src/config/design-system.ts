/**
 * Slate & Coral Design System Configuration
 *
 * A premium, professional design system for Ledgi.
 * Cool slate tones with coral accents - sophisticated yet approachable.
 */

export const designSystem = {
  /**
   * Color Palette
   *
   * Surface: Cool grey-blue backgrounds (not harsh white)
   * Brand Primary: Slate 700 - strong, neutral interaction color
   * Brand Accent: Muted Rose/Coral - high-visibility highlights
   * Positive: Sage green (muted, grey-green) - growth
   * Negative: Rose 600 (berry red) - loss
   * Pending: Amber (warm, not neon) - neutral/pending
   */
  colors: {
    // Surface colors (backgrounds)
    surface: {
      base: '#F8FAFC',     // Cool, pale grey-blue (not harsh white)
      card: '#FFFFFF',     // Pure white for elevated cards
      sidebar: '#0F172A',  // Deep Slate (nav/sidebar)
      hover: '#F1F5F9',    // Subtle hover state
    },

    // Brand colors
    brand: {
      primary: '#334155',   // Slate 700 - main interaction color
      accent: '#F472B6',    // Muted Rose/Coral - highlights
      tertiary: '#64748B',  // Cool Grey - subtitles/icons
    },

    // Slate scale (primary neutral)
    slate: {
      50: '#F8FAFC',
      100: '#F1F5F9',
      200: '#E2E8F0',
      300: '#CBD5E1',
      400: '#94A3B8',
      500: '#64748B',
      600: '#475569',    // Body text color (never pure black)
      700: '#334155',    // Primary action color
      800: '#1E293B',    // H2 color
      900: '#0F172A',    // H1 color, sidebar
      950: '#020617',
    },

    // Semantic colors
    positive: {
      DEFAULT: '#5C7C5C',  // Sage green - growth
      light: '#E8EFE8',    // Soft wash background
      dark: '#3D5A3D',     // Dark text for badges
    },
    negative: {
      DEFAULT: '#E11D48',  // Rose 600 - berry red (not fire engine)
      light: '#FFE4E6',    // 10% opacity equivalent for soft wash
      dark: '#9F1239',     // Dark text for badges
    },
    pending: {
      DEFAULT: '#F59E0B',  // Amber - warm (not neon yellow)
      light: '#FEF3C7',    // 10% opacity equivalent for soft wash
      dark: '#92400E',     // Dark text for badges
    },

    // Rose scale (accent & negative)
    rose: {
      50: '#FFF1F2',
      100: '#FFE4E6',
      200: '#FECDD3',
      300: '#FDA4AF',
      400: '#FB7185',
      500: '#F472B6',     // Brand accent
      600: '#E11D48',     // Negative semantic
      700: '#BE123C',
      800: '#9F1239',
      900: '#881337',
    },

    // Sage green scale (positive) - muted, grey-green
    sage: {
      50: '#F4F7F4',
      100: '#E8EFE8',
      200: '#D1DFD1',
      300: '#A8C4A8',
      400: '#7DA07D',
      500: '#5C7C5C',     // Positive semantic - dark sage
      600: '#4A6B4A',
      700: '#3D5A3D',
      800: '#2F472F',
      900: '#243824',
    },

    // Keep emerald as alias for sage
    emerald: {
      50: '#F4F7F4',
      100: '#E8EFE8',
      200: '#D1DFD1',
      300: '#A8C4A8',
      400: '#7DA07D',
      500: '#5C7C5C',     // Dark sage green
      600: '#4A6B4A',
      700: '#3D5A3D',
      800: '#2F472F',
      900: '#243824',
    },

    // Amber scale (pending/warning)
    amber: {
      50: '#FFFBEB',
      100: '#FEF3C7',
      200: '#FDE68A',
      300: '#FCD34D',
      400: '#FBBF24',
      500: '#F59E0B',     // Pending semantic
      600: '#D97706',
      700: '#B45309',
      800: '#92400E',
      900: '#78350F',
    },
  },

  /**
   * Category Colors
   * Using the Slate & Coral palette for transaction categories
   */
  categoryColors: {
    groceries: '#5C7C5C',    // Sage (positive)
    dining: '#F59E0B',       // Amber
    shopping: '#F472B6',     // Rose accent
    entertainment: '#FB7185', // Rose 400
    transportation: '#64748B', // Slate 500
    utilities: '#94A3B8',    // Slate 400
    healthcare: '#E11D48',   // Rose 600 (negative)
    travel: '#7DA07D',       // Sage 400
    income: '#5C7C5C',       // Sage (positive)
    transfer: '#CBD5E1',     // Slate 300
    uncategorized: '#E2E8F0', // Slate 200
  },

  /**
   * Typography
   *
   * Font Family: Plus Jakarta Sans / Inter
   * H1: 700 weight, 2.25rem, -0.02em tracking, #0F172A
   * H2: 600 weight, 1.5rem, -0.01em tracking, #1E293B
   * Body: 400 weight, 1rem, #475569 (never pure black)
   */
  typography: {
    fontFamily: "'Plus Jakarta Sans', 'Inter', system-ui, sans-serif",
    h1: {
      fontSize: '2.25rem',    // 36px
      fontWeight: 700,
      letterSpacing: '-0.02em',
      lineHeight: '2.5rem',   // 40px
      color: '#0F172A',       // Slate 900
    },
    h2: {
      fontSize: '1.5rem',     // 24px
      fontWeight: 600,
      letterSpacing: '-0.01em',
      lineHeight: '2rem',     // 32px
      color: '#1E293B',       // Slate 800
    },
    h3: {
      fontSize: '1.25rem',    // 20px
      fontWeight: 600,
      letterSpacing: '-0.01em',
      lineHeight: '1.75rem',  // 28px
      color: '#1E293B',       // Slate 800
    },
    body: {
      fontSize: '1rem',       // 16px
      fontWeight: 400,
      lineHeight: '1.5rem',   // 24px
      color: '#475569',       // Slate 600 (never pure black)
    },
    small: {
      fontSize: '0.875rem',   // 14px
      fontWeight: 400,
      lineHeight: '1.25rem',  // 20px
      color: '#64748B',       // Slate 500
    },
    tag: {
      fontSize: '0.75rem',    // 12px
      fontWeight: 600,
      letterSpacing: '0.05em',
      textTransform: 'uppercase' as const,
    },
  },

  /**
   * Component Styling
   */
  components: {
    // Primary Button
    buttonPrimary: {
      background: '#0F172A',    // Deep Slate
      text: '#FFFFFF',
      radius: '8px',
      shadow: '0 4px 6px -1px rgba(15, 23, 42, 0.1)',
      hover: {
        background: '#1E293B',
        transform: 'translateY(-1px)',
      },
    },

    // Secondary/Outline Button
    buttonSecondary: {
      background: 'transparent',
      border: '1px solid #CBD5E1',
      text: '#334155',
      radius: '8px',
      hover: {
        background: '#F8FAFC',
        borderColor: '#94A3B8',
      },
    },

    // Cards/Containers
    card: {
      background: '#FFFFFF',
      border: '1px solid #E2E8F0',
      shadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
      radius: '12px',
    },

    // Tags/Chips (Soft Wash style)
    tag: {
      radius: '4px',
      // Background: 10% opacity of semantic color
      // Text: Darker shade of same hue
      // Font: Semi-bold, 0.75rem, uppercase, wide tracking
    },

    // Input fields
    input: {
      background: '#FFFFFF',
      border: '1px solid #E2E8F0',
      radius: '8px',
      text: '#334155',
      placeholder: '#94A3B8',
      focus: {
        ring: '2px solid #334155',
        border: 'transparent',
      },
    },
  },

  /**
   * Spacing Scale
   */
  spacing: {
    xs: '0.5rem',   // 8px
    sm: '0.75rem',  // 12px
    md: '1rem',     // 16px
    lg: '1.5rem',   // 24px
    xl: '2rem',     // 32px
    '2xl': '3rem',  // 48px
    '3xl': '4rem',  // 64px
  },

  /**
   * Border Radius
   */
  radius: {
    sm: '0.25rem',  // 4px - tags/chips
    md: '0.5rem',   // 8px - buttons
    lg: '0.75rem',  // 12px - cards
    xl: '1rem',     // 16px
    '2xl': '1.5rem', // 24px
    full: '9999px',
  },

  /**
   * Shadows
   */
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    DEFAULT: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
    md: '0 4px 6px -1px rgba(15, 23, 42, 0.1)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
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

/**
 * Helper to get semantic color with opacity for soft wash tags
 */
export function getSemanticTagStyle(type: 'positive' | 'negative' | 'pending' | 'neutral') {
  const styles = {
    positive: {
      background: 'rgba(92, 124, 92, 0.1)',   // Sage 10%
      color: '#3D5A3D',                        // Sage 700
    },
    negative: {
      background: 'rgba(225, 29, 72, 0.1)',   // Rose 10%
      color: '#9F1239',                        // Rose 800
    },
    pending: {
      background: 'rgba(245, 158, 11, 0.1)',  // Amber 10%
      color: '#92400E',                        // Amber 800
    },
    neutral: {
      background: 'rgba(100, 116, 139, 0.1)', // Slate 10%
      color: '#334155',                        // Slate 700
    },
  };
  return styles[type];
}

export type DesignSystem = typeof designSystem;
