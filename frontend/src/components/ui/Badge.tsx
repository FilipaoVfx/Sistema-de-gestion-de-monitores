import type { ReactNode } from 'react'

type Variant = 'green' | 'yellow' | 'red' | 'gray' | 'blue'

const variantClasses: Record<Variant, string> = {
  green:  'bg-green-100  text-green-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  red:    'bg-red-100    text-red-800',
  gray:   'bg-gray-100   text-gray-700',
  blue:   'bg-blue-100   text-blue-800',
}

interface Props {
  variant?: Variant
  children: ReactNode
}

export default function Badge({ variant = 'gray', children }: Props) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variantClasses[variant]}`}>
      {children}
    </span>
  )
}
