/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        pace: {
          bg: '#06080D',
          surface: '#0D111A',
          surfaceHover: '#131824',
          border: '#1E2638',
          borderLight: 'rgba(255, 255, 255, 0.08)',
          lime: '#A3E635',
          emerald: '#10B981',
          lavender: '#C084FC',
          amber: '#F59E0B',
          coral: '#F43F5E',
          cyan: '#38BDF8',
          text: '#F3F4F6',
          muted: '#94A3B8',
          mutedDark: '#64748B',
          accent: '#A3E635',
          accentHover: '#84CC16',
          danger: '#F43F5E',
          success: '#10B981',
          warning: '#F59E0B',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite alternate',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glowPulse: {
          '0%': { boxShadow: '0 0 12px rgba(163, 230, 53, 0.15)' },
          '100%': { boxShadow: '0 0 24px rgba(163, 230, 53, 0.35)' },
        }
      }
    },
  },
  plugins: [],
}
