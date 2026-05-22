/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        sidebar:   '#0F172A',
        primary:   '#2563EB',
        success:   '#16A34A',
        warning:   '#F59E0B',
        danger:    '#DC2626',
        bgPage:    '#F8FAFC',
        textMain:  '#0F172A',
        textMuted: '#64748B',
      },
    },
  },
  plugins: [],
}
