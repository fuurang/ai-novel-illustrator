/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        base: '#0f0f0f',
        surface: '#1a1a1a',
        elevated: '#222222',
        border: '#2a2a2a',
        'border-hover': '#3a3a3a',
        'text-primary': '#ffffff',
        'text-secondary': '#a0a0a0',
        'text-muted': '#666666',
        accent: {
          DEFAULT: '#f97316',
          hover: '#fb923c',
          muted: '#9a3412',
        },
        success: '#22c55e',
        error: '#ef4444',
        warning: '#eab308',
      },
    },
  },
  plugins: [],
};
