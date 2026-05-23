import { colorsForUser, initialsFor } from '../../utils/userAvatar'

interface Props {
  userId: number | string | null | undefined
  name: string | null | undefined
  size?: 'xs' | 'sm' | 'md' | 'lg'
  /** Si true, agrega un ring/border alrededor del avatar. */
  ringed?: boolean
  /** Si true, oscurece el avatar y muestra un check (indica seleccionado). */
  selected?: boolean
}

const SIZES = {
  xs: 'w-6 h-6 text-[10px]',
  sm: 'w-7 h-7 text-xs',
  md: 'w-9 h-9 text-sm',
  lg: 'w-12 h-12 text-base',
} as const

export default function UserAvatar({ userId, name, size = 'sm', ringed = false, selected = false }: Props) {
  const colors = colorsForUser(userId)
  const initials = initialsFor(name)
  return (
    <div
      title={name ?? undefined}
      className={[
        SIZES[size],
        'rounded-full flex items-center justify-center font-semibold text-white shrink-0',
        colors.bg,
        ringed ? `ring-2 ring-white ${colors.ring}` : '',
        selected ? 'ring-2 ring-offset-1 ring-black/40' : '',
      ].filter(Boolean).join(' ')}
    >
      {initials}
    </div>
  )
}
