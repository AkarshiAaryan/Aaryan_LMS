/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#f0f4f8',
          100: '#d9e2ec',
          200: '#bcccdc',
          300: '#9fb3c8',
          400: '#829ab1',
          500: '#627d98',
          600: '#486581',
          700: '#334e68',
          800: '#1e293b',
          900: '#0f172a',
          950: '#0a0f1d',
        },
        academic: {
          blue: '#1d4ed8',
          gold: '#b45309',
          green: '#15803d',
          red: '#b91c1c',
        }
      },
    },
  },
  plugins: [],
}
