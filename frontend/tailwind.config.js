/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        tenzing: {
          50: '#f0f4ff',
          100: '#dde6ff',
          500: '#3b5bdb',
          600: '#2f4acf',
          700: '#2541c0',
          900: '#1a2d8f',
        },
      },
    },
  },
  plugins: [],
}
