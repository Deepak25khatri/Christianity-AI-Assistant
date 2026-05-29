import type { Config } from 'tailwindcss'
import typography from '@tailwindcss/typography'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#1b1f3a',
          50: '#f4f5fb',
          100: '#e6e8f3',
          200: '#c5c9e1',
          300: '#9aa0c6',
          400: '#6a72a3',
          500: '#454c85',
          600: '#2f3568',
          700: '#23284f',
          800: '#1b1f3a',
          900: '#10132a',
        },
        gold: {
          DEFAULT: '#b8893a',
          50: '#fbf5e7',
          100: '#f3e3b3',
          200: '#e6c87a',
          300: '#d3aa4a',
          400: '#c39831',
          500: '#b8893a',
          600: '#8e6826',
        },
        parchment: {
          DEFAULT: '#f7f1e3',
          50: '#fcfaf3',
          100: '#f7f1e3',
          200: '#ece1c4',
        },
      },
      fontFamily: {
        serif: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 2px 24px -8px rgba(27, 31, 58, 0.18)',
      },
    },
  },
  plugins: [typography],
} satisfies Config
