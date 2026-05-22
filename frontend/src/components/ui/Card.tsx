import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  className?: string
}

export default function Card({ children, className = '' }: Props) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }: Props) {
  return (
    <div className={`px-6 py-4 border-b border-gray-100 ${className}`}>
      {children}
    </div>
  )
}

export function CardBody({ children, className = '' }: Props) {
  return <div className={`px-6 py-4 ${className}`}>{children}</div>
}
