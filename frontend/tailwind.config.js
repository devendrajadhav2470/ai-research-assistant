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
          50: '#EEECFF',
          100: '#DBD8FF',
          200: '#B8B1FF',
          300: '#948AFF',
          400: '#7F73FF',
          500: '#6C63FF',
          600: '#5A50E6',
          700: '#473ECC',
          800: '#352DB3',
          900: '#221D99',
        },
        surface: '#FFFFFF',
        page: '#F0F2F5',
        'text-primary': '#1A1A2E',
        'text-secondary': '#6B7280',
        border: '#E5E7EB',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        'card': '12px',
        'bubble': '20px',
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px -1px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 12px 0 rgba(0, 0, 0, 0.08)',
        'sidebar': '2px 0 8px 0 rgba(0, 0, 0, 0.04)',
        'modal': '0 20px 60px -12px rgba(0, 0, 0, 0.25)',
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-in-left': 'slideInLeft 0.25s ease-out',
        'slide-in-up': 'slideInUp 0.15s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideInLeft: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInUp: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
