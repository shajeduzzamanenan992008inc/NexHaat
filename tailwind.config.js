/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1769FF',
          hover: '#1458D4',
          light: '#EAF2FF',
          sky: '#4D91FF',
        },
        accent: {
          DEFAULT: '#FF9900',
          light: '#FFF2D9',
          daraz: '#F85606',
        },
        success: {
          DEFAULT: '#238253',
          light: '#e5f3e9',
        },
        danger: {
          DEFAULT: '#E1251B',
          light: '#FCE9E7',
        },
        navy: '#0B1F3A',
        sky: '#4D91FF',
        ink: '#0B1F3A',
        muted: '#53657C',
        border: '#DBE3ED',
        page: '#F3F4F6',
        surface: {
          DEFAULT: '#ffffff',
          raised: '#F8FAFF',
        }
      },
      boxShadow: {
        'soft': '0 6px 22px rgba(11, 31, 58, 0.08)',
        'card': '0 2px 12px rgba(11, 31, 58, 0.06)',
        'elevated': '0 14px 38px rgba(11, 31, 58, 0.14)',
        'neumorph': '6px 6px 14px rgba(11, 31, 58, 0.07), -6px -6px 14px rgba(255, 255, 255, 0.9)',
        'neumorph-sm': '3px 3px 8px rgba(11, 31, 58, 0.05), -3px -3px 8px rgba(255, 255, 255, 0.8)',
        'neumorph-inset': 'inset 2px 2px 6px rgba(11, 31, 58, 0.07), inset -2px -2px 6px rgba(255, 255, 255, 0.7)',
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
