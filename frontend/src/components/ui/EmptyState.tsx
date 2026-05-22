import { Inbox } from 'lucide-react'

interface Props {
  title?: string
  description?: string
  action?: React.ReactNode
}

export default function EmptyState({
  title = 'Sin resultados',
  description = 'No hay elementos para mostrar.',
  action,
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Inbox className="w-12 h-12 text-gray-300 mb-4" />
      <p className="text-lg font-medium text-textMain">{title}</p>
      <p className="text-sm text-textMuted mt-1">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
