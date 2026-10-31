/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0a66c2',
          hover: '#074f96',
          light: '#e8f0fe',
        },
        accent: {
          DEFAULT: '#e8890c',
          light: '#fef3e2',
        },
        success: {
          DEFAULT: '#1b7a43',
          light: '#e4f3e8',
        },
        danger: {
          DEFAULT: '#b3261e',
          light: '#fce8e6',
        },
        ink: '#1a2332',
        muted: '#5c6b7a',
        border: '#dde3ea',
        page: '#f4f6f8',
        surface: {
          DEFAULT: '#ffffff',
          raised: '#f8fafc',
        }
      },
      boxShadow: {
        'soft': '0 4px 16px rgba(20, 34, 52, 0.08)',
        'card': '0 2px 10px rgba(20, 34, 52, 0.06)',
        'elevated': '0 8px 30px rgba(20, 34, 52, 0.12)',
        'neumorph': '6px 6px 14px rgba(20, 34, 52, 0.08), -6px -6px 14px rgba(255, 255, 255, 0.9)',
        'neumorph-sm': '3px 3px 8px rgba(20, 34, 52, 0.06), -3px -3px 8px rgba(255, 255, 255, 0.8)',
        'neumorph-inset': 'inset 2px 2px 6px rgba(20, 34, 52, 0.08), inset -2px -2px 6px rgba(255, 255, 255, 0.7)',
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
