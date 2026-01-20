/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        friendly: {
          light: '#86efac',
          DEFAULT: '#4ade80',
          dark: '#22c55e',
        },
        competitive: {
          light: '#93c5fd',
          DEFAULT: '#60a5fa',
          dark: '#3b82f6',
        },
      },
    },
  },
  plugins: [],
}

