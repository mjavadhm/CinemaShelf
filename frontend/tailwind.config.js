/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Vazirmatn', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        shelf: {
          bg: '#0d0f12',
          card: '#15181e',
          border: '#242933',
          amber: '#f5b921',
          amberHover: '#ffca42',
          emerald: '#10b981',
          danger: '#ef4444',
        },
      },
    },
  },
  plugins: [],
};
