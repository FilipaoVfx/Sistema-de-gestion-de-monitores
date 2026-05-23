/**
 * Asigna un color consistente a cada usuario basado en su ID.
 * Usa una paleta cuidada y deterministica (mismo id -> mismo color siempre).
 */

// Paleta de 12 colores tailwind con buen contraste sobre blanco, balanceados
// para no chocar entre si. Tonalidad 500-600 para fondo, 100 para soft bg.
const PALETTE = [
  { bg: 'bg-blue-500',    soft: 'bg-blue-100',    text: 'text-blue-700',    ring: 'ring-blue-200'    },
  { bg: 'bg-emerald-500', soft: 'bg-emerald-100', text: 'text-emerald-700', ring: 'ring-emerald-200' },
  { bg: 'bg-purple-500',  soft: 'bg-purple-100',  text: 'text-purple-700',  ring: 'ring-purple-200'  },
  { bg: 'bg-amber-500',   soft: 'bg-amber-100',   text: 'text-amber-700',   ring: 'ring-amber-200'   },
  { bg: 'bg-pink-500',    soft: 'bg-pink-100',    text: 'text-pink-700',    ring: 'ring-pink-200'    },
  { bg: 'bg-cyan-500',    soft: 'bg-cyan-100',    text: 'text-cyan-700',    ring: 'ring-cyan-200'    },
  { bg: 'bg-orange-500',  soft: 'bg-orange-100',  text: 'text-orange-700',  ring: 'ring-orange-200'  },
  { bg: 'bg-teal-500',    soft: 'bg-teal-100',    text: 'text-teal-700',    ring: 'ring-teal-200'    },
  { bg: 'bg-indigo-500',  soft: 'bg-indigo-100',  text: 'text-indigo-700',  ring: 'ring-indigo-200'  },
  { bg: 'bg-rose-500',    soft: 'bg-rose-100',    text: 'text-rose-700',    ring: 'ring-rose-200'    },
  { bg: 'bg-lime-600',    soft: 'bg-lime-100',    text: 'text-lime-700',    ring: 'ring-lime-200'    },
  { bg: 'bg-fuchsia-500', soft: 'bg-fuchsia-100', text: 'text-fuchsia-700', ring: 'ring-fuchsia-200' },
]

export interface UserColors {
  bg:   string  // fondo solido (avatar circular)
  soft: string  // fondo suave (badges/tags)
  text: string  // texto de acento
  ring: string  // borde de hover/focus
}

/** Devuelve un set de clases tailwind unico y determinista para un userId. */
export function colorsForUser(userId: number | string | null | undefined): UserColors {
  if (userId === null || userId === undefined) return PALETTE[0]
  const n = typeof userId === 'number' ? userId : userId.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return PALETTE[Math.abs(n) % PALETTE.length]
}

/** Inicial(es) para mostrar dentro de un avatar circular. */
export function initialsFor(name: string | null | undefined, fallback = '?'): string {
  if (!name) return fallback
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}
