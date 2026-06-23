import type { Config } from 'tailwindcss';

// Tokens mirror docs/DESIGN.md exactly. No saturated accents, no dark mode.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        // EB Garamond is the open-source Waldenburg substitute (weight 300, never bold).
        display: ["'EB Garamond'", "'Times New Roman'", 'serif'],
        body: ["'Inter'", 'sans-serif'],
      },
      colors: {
        // Brand / ink
        primary: '#292524',
        'primary-active': '#0c0a09',
        ink: '#0c0a09',
        body: '#4e4e4e',
        'body-strong': '#292524',
        muted: '#777169',
        'muted-soft': '#a8a29e',
        // Hairlines
        hairline: '#e7e5e4',
        'hairline-soft': '#f0efed',
        'hairline-strong': '#d6d3d1',
        // Surfaces
        canvas: '#f5f5f5',
        'canvas-soft': '#fafafa',
        'surface-card': '#ffffff',
        'surface-strong': '#f0efed',
        // Atmospheric gradient stops (decoration only)
        'gradient-mint': '#a7e5d3',
        'gradient-peach': '#f4c5a8',
        'gradient-lavender': '#c8b8e0',
        'gradient-sky': '#a8c8e8',
        'gradient-rose': '#e8b8c4',
        // Semantic
        'semantic-error': '#dc2626',
        'semantic-success': '#16a34a',
      },
      borderRadius: {
        xs: '4px',
        sm: '6px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        xxl: '24px',
        pill: '9999px',
      },
      letterSpacing: {
        body: '0.16px',
        caption: '0.96px',
        'display-tight': '-0.32px',
      },
      boxShadow: {
        soft: '0 4px 16px rgba(0, 0, 0, 0.04)',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(24px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
      animation: {
        'fade-in-up': 'fadeInUp 360ms cubic-bezier(0.16,1,0.3,1) both',
        'slide-in-right': 'slideInRight 320ms cubic-bezier(0.16,1,0.3,1) both',
      },
    },
  },
  plugins: [],
} satisfies Config;
