/** @type {import('tailwindcss').Config} */
// Paleta dinamica de avatares (utils/userAvatar.ts). Las clases se generan
// runtime a partir del id de usuario, por lo que NO aparecen en el codigo
// estaticamente y Tailwind las tree-shake. Las safelist aqui para que el
// build las incluya en el bundle final.
const AVATAR_COLORS = [
  'blue', 'emerald', 'purple', 'amber', 'pink', 'cyan',
  'orange', 'teal', 'indigo', 'rose', 'lime', 'fuchsia',
]
const AVATAR_SAFELIST = AVATAR_COLORS.flatMap(c => [
  `bg-${c}-500`,
  `bg-${c}-600`,
  `bg-${c}-100`,
  `text-${c}-700`,
  `ring-${c}-200`,
])

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  safelist: AVATAR_SAFELIST,
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
