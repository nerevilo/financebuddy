/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './node_modules/@tremor/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // Typography - Plus Jakarta Sans
      fontFamily: {
        sans: ['var(--font-jakarta)', 'Inter', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        tighter: '-0.02em',
        tight: '-0.01em',
      },
      colors: {
        // Slate & Coral Design System

        // Surface colors (backgrounds)
        surface: {
          base: '#F8FAFC',      // Cool, pale grey-blue
          card: '#FFFFFF',      // Pure white for elevated cards
          sidebar: '#0F172A',   // Deep Slate (nav/sidebar)
          hover: '#F1F5F9',     // Subtle hover state
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
          600: '#475569',
          700: '#334155',
          800: '#1E293B',
          900: '#0F172A',
          950: '#020617',
        },

        // Semantic colors (data visualization)
        positive: {
          DEFAULT: '#5A8A5A',   // Sage green - growth (lighter, more green)
          light: '#E5F0E5',     // Soft wash background
          dark: '#3D6B3D',      // Dark text for badges
        },
        negative: {
          DEFAULT: '#E11D48',   // Rose 600 - loss (berry red)
          light: '#FFE4E6',     // Soft wash background
          dark: '#9F1239',      // Dark text for badges
        },
        pending: {
          DEFAULT: '#F59E0B',   // Amber - neutral/pending
          light: '#FEF3C7',     // Soft wash background
          dark: '#92400E',      // Dark text for badges
        },

        // Accent rose for highlights
        rose: {
          50: '#FFF1F2',
          100: '#FFE4E6',
          200: '#FECDD3',
          300: '#FDA4AF',
          400: '#FB7185',
          500: '#F472B6',       // Brand accent
          600: '#E11D48',       // Negative semantic
          700: '#BE123C',
          800: '#9F1239',
          900: '#881337',
        },

        // Sage green for positive values (muted but more green)
        sage: {
          50: '#F2F7F2',
          100: '#E3EFE3',
          200: '#C7DFC7',
          300: '#9CC79C',
          400: '#6FA86F',
          500: '#528A52',       // Positive semantic - balanced sage
          600: '#427042',
          700: '#355A35',
          800: '#2A472A',
          900: '#1F361F',
        },

        // Keep emerald as alias for sage
        emerald: {
          50: '#F2F7F2',
          100: '#E3EFE3',
          200: '#C7DFC7',
          300: '#9CC79C',
          400: '#6FA86F',
          500: '#528A52',       // Balanced sage green
          600: '#427042',
          700: '#355A35',
          800: '#2A472A',
          900: '#1F361F',
        },

        // Amber for warnings/pending
        amber: {
          50: '#FFFBEB',
          100: '#FEF3C7',
          200: '#FDE68A',
          300: '#FCD34D',
          400: '#FBBF24',
          500: '#F59E0B',       // Pending semantic
          600: '#D97706',
          700: '#B45309',
          800: '#92400E',
          900: '#78350F',
        },

        // Tremor colors (for chart compatibility)
        tremor: {
          brand: {
            faint: '#F8FAFC',
            muted: '#E2E8F0',
            subtle: '#94A3B8',
            DEFAULT: '#334155',
            emphasis: '#0F172A',
            inverted: '#FFFFFF',
          },
          background: {
            muted: '#F8FAFC',
            subtle: '#F1F5F9',
            DEFAULT: '#FFFFFF',
            emphasis: '#0F172A',
          },
          border: {
            DEFAULT: '#E2E8F0',
          },
          ring: {
            DEFAULT: '#E2E8F0',
          },
          content: {
            subtle: '#94A3B8',
            DEFAULT: '#64748B',
            emphasis: '#334155',
            strong: '#0F172A',
            inverted: '#FFFFFF',
          },
        },
      },
      borderRadius: {
        sm: '0.25rem',    // 4px - tags/chips
        DEFAULT: '0.5rem', // 8px - buttons
        md: '0.5rem',
        lg: '0.75rem',    // 12px - cards
        xl: '1rem',
        '2xl': '1.5rem',
      },
      boxShadow: {
        sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        DEFAULT: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',  // Card shadow
        md: '0 4px 6px -1px rgba(15, 23, 42, 0.1)', // Button shadow
        lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
        xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
        'button': '0 4px 6px -1px rgba(15, 23, 42, 0.1)',
      },
    },
  },
  plugins: [],
}
