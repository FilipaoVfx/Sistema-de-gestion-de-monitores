import { AlertCircle, RefreshCw } from 'lucide-react'
import Button from './Button'

interface Props {
  message?: string
  onRetry?: () => void
}

export default function ErrorMessage({
  message = 'No se pudo cargar la información.',
  onRetry,
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <AlertCircle className="w-10 h-10 text-danger" />
      <p className="text-sm text-textMuted">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RefreshCw className="w-4 h-4" /> Intentar nuevamente
        </Button>
      )}
    </div>
  )
}
