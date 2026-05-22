import { useEffect, useState } from 'react'
import { dashboardApi, type DashboardData } from '../api/dashboard.api'
import { asignacionesApi, type Asignacion } from '../api/asignaciones.api'
import { LayoutDashboard, Building2, Users, CalendarCheck, ArrowLeftRight } from 'lucide-react'
import Card, { CardHeader, CardBody } from '../components/ui/Card'
import Spinner from '../components/ui/Spinner'
import ErrorMessage from '../components/ui/ErrorMessage'
import { formatTime } from '../utils/formatDate'

export default function DashboardPage() {
  const [data,    setData]    = useState<DashboardData | null>(null)
  const [recent,  setRecent]  = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(false)

  const load = () => {
    setLoading(true)
    setError(false)
    Promise.all([dashboardApi.get(), asignacionesApi.list()])
      .then(([d, a]) => { setData(d); setRecent(a.data.slice(0, 8)) })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <Spinner />
  if (error || !data) return <ErrorMessage onRetry={load} />

  const stats = [
    { label: 'Salas activas',          value: data.salas_activas,          icon: Building2      },
    { label: 'Monitores activos',       value: data.monitores_activos,       icon: Users          },
    { label: 'Asignaciones activas',    value: data.asignaciones_activas,    icon: CalendarCheck  },
    { label: 'Solicitudes pendientes',  value: data.solicitudes_pendientes,  icon: ArrowLeftRight },
  ]

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-textMain flex items-center gap-2">
          <LayoutDashboard className="w-6 h-6 text-primary" /> Dashboard
        </h1>
        <p className="text-sm text-textMuted mt-1">Resumen operativo del sistema</p>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardBody className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-blue-50">
                <Icon className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-textMain">{value}</p>
                <p className="text-xs text-textMuted">{label}</p>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-textMain">Asignaciones recientes</h2>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                {['Monitor', 'Sala', 'Día', 'Horario', 'Semestre'].map(h => (
                  <th key={h} className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {recent.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-textMuted text-sm">
                    Sin asignaciones registradas
                  </td>
                </tr>
              ) : recent.map(a => (
                <tr key={a.id_asignacion} className="hover:bg-gray-50/50">
                  <td className="px-6 py-3 font-medium text-textMain">{a.monitor_nombre}</td>
                  <td className="px-6 py-3 text-textMuted">{a.sala_codigo}</td>
                  <td className="px-6 py-3 text-textMuted">{a.dia_semana_display}</td>
                  <td className="px-6 py-3 text-textMuted">{formatTime(a.hora_inicio)}–{formatTime(a.hora_fin)}</td>
                  <td className="px-6 py-3 text-textMuted">{a.semestre_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
