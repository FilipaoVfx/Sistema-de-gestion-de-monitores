import { AlertCircle, ExternalLink } from 'lucide-react'

interface Props {
  title: string
  description: string
  backendPath: string
}

/**
 * Componente placeholder usado en todas las páginas mientras el backend
 * Django+HTMX no exponga endpoints JSON consumibles por la SPA.
 */
export default function PendingBackend({ title, description, backendPath }: Props) {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-textMain">{title}</h1>
        <p className="text-sm text-textMuted mt-1">{description}</p>
      </header>

      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 flex gap-4">
        <AlertCircle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-amber-900">Esperando endpoints JSON</h3>
          <p className="text-sm text-amber-800 mt-1 leading-relaxed">
            El backend desplegado en{' '}
            <code className="font-mono bg-amber-100 px-1.5 py-0.5 rounded">
              sgmsc-web.onrender.com
            </code>{' '}
            actualmente sirve esta vista como HTML server-rendered en{' '}
            <code className="font-mono bg-amber-100 px-1.5 py-0.5 rounded">{backendPath}</code>.
            Una SPA React requiere respuestas JSON con DRF para poder renderizar la data.
          </p>
          <p className="text-sm text-amber-800 mt-2">
            En cuanto el backend exponga el endpoint JSON correspondiente, esta página se
            llenará automáticamente con los datos reales.
          </p>
          <a
            href={`https://sgmsc-web.onrender.com${backendPath}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 mt-3 text-sm font-medium text-amber-900 hover:text-amber-700"
          >
            Abrir vista HTML del backend
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      <div className="bg-white border border-gray-100 rounded-2xl p-8 text-center">
        <div className="w-16 h-16 mx-auto rounded-full bg-gray-50 flex items-center justify-center mb-4">
          <span className="text-2xl">🔌</span>
        </div>
        <h3 className="font-semibold text-textMain">Sin datos para mostrar</h3>
        <p className="text-sm text-textMuted mt-1 max-w-md mx-auto">
          La interfaz visual ya está lista. Solo falta que el backend exponga
          el endpoint JSON correspondiente.
        </p>
      </div>
    </div>
  )
}
