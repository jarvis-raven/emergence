/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Core theme colors from UX flows
        background: '#0f172a',
        surface: '#1e293b',
        text: '#f8fafc',
        textMuted: '#94a3b8',
        primary: '#3b82f6',
        secondary: '#64748b',
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
        // Drive-specific colors (for gradients)
        care: {
          from: '#22d3ee',
          to: '#2dd4bf',
        },
        maintenance: {
          from: '#94a3b8',
          to: '#64748b',
        },
        rest: {
          from: '#818cf8',
          to: '#c084fc',
        },
        curiosity: {
          from: '#fbbf24',
          to: '#f97316',
        },
        social: {
          from: '#f472b6',
          to: '#ef4444',
        },
        creative: {
          from: '#a78bfa',
          to: '#8b5cf6',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-medium': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      transitionDuration: {
        600: '600ms',
      },
    },
  },
  plugins: [],
};
