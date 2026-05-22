import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'

const variantClasses: Record<Variant, string> = {
  primary:   'bg-primary text-white hover:bg-blue-700',
  secondary: 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50',
  danger:    'bg-red-600  text-white hover:bg-red-700',
  ghost:     'text-gray-600 hover:bg-gray-100',
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md'
  children: ReactNode
}

export default function Button({
  variant = 'primary', size = 'md', children, className = '', ...rest
}: Props) {
  const sizeClass = size === 'sm' ? 'px-3 py-1.5 text-sm' : 'px-4 py-2 text-sm'
  return (
    <button
      className={`inline-flex items-center gap-1.5 font-medium rounded-lg transition-colors disabled:opacity-50 ${sizeClass} ${variantClasses[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
