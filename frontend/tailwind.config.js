/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f4ff',
          100: '#e1e9ff',
          200: '#c2d3ff',
          300: '#a3bdff',
          400: '#668fff',
          500: '#4a6cf7',
          600: '#3f5bdb',
          700: '#3248b8',
          800: '#263794',
          900: '#1d2a70',
        },
        nexus: {
          dark: '#1a1a2e',
          card: 'rgba(255, 255, 255, 0.05)',
          border: 'rgba(255, 255, 255, 0.1)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}
