import { useEffect, useState } from 'react'
import { dashboardApi, type DashboardData } from '../api/dashboard.api'
import { asignacionesApi, type Asignacion } from '../api/asignaciones.api'
import { cambiosApi, type SolicitudCambio } from '../api/cambios.api'
import {
  LayoutDashboard, Building2, Users, CalendarCheck, ArrowLeftRight, Clock, Sparkles,
} from 'lucide-react'
import Card, { CardHeader, CardBody } from '../components/ui/Card'
import Spinner from '../components/ui/Spinner'
import ErrorMessage from '../components/ui/ErrorMessage'
import UserAvatar from '../components/ui/UserAvatar'
import Badge from '../components/ui/Badge'
import { formatTime, formatDate } from '../utils/formatDate'
import { useAuth } from '../context/AuthContext'

const DIAS: Record<number, string> = {
  1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado',
}

export default function DashboardPage() {
  const { user } = useAuth()
  const isAdmin = user?.rol === 'admin'

  return isAdmin ? <AdminDashboard /> : <MonitorDashboard />
}

// ============================================================================
// Admin Dashboard: KPIs globales + ultimas asignaciones
// ============================================================================
function AdminDashboard() {
  const [data,    setData]    = useState<DashboardData | null>(null)
  const [recent,  setRecent]  = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(false)

  const load = () => {
    setLoading(true); setError(false)
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
    { label: 'Monitores activos',      value: data.monitores_activos,      icon: Users          },
    { label: 'Asignaciones activas',   value: data.asignaciones_activas,   icon: CalendarCheck  },
    { label: 'Solicitudes pendientes', value: data.solicitudes_pendientes, icon: ArrowLeftRight },
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
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      <UserAvatar userId={a.monitor} name={a.monitor_nombre} size="sm" />
                      <span className="font-medium text-textMain">{a.monitor_nombre}</span>
                    </div>
                  </td>
                  <td className="px-6 py-3 text-textMuted font-mono">{a.sala_codigo}</td>
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

// ============================================================================
// Monitor Dashboard: mis turnos + mis solicitudes
// ============================================================================
function MonitorDashboard() {
  const { user } = useAuth()
  const [misTurnos, setMisTurnos] = useState<Asignacion[]>([])
  const [misSolicitudes, setMisSolicitudes] = useState<SolicitudCambio[]>([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(false)

  const load = () => {
    setLoading(true); setError(false)
    Promise.all([asignacionesApi.list(), cambiosApi.list()])
      .then(([a, c]) => {
        setMisTurnos(a.data)
        setMisSolicitudes(c.data)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <Spinner />
  if (error) return <ErrorMessage onRetry={load} />

  const pendientes = misSolicitudes.filter(s => s.estado === 'pendiente').length
  const conPropuestas = misSolicitudes.filter(s => s.estado === 'con_propuestas').length

  // Agrupa turnos por dia
  const turnosPorDia = misTurnos.reduce<Record<number, Asignacion[]>>((acc, a) => {
    (acc[a.dia_semana] ||= []).push(a)
    return acc
  }, {})

  const displayName = user?.first_name || user?.email?.split('@')[0] || 'monitor'

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-textMain flex items-center gap-2">
          <LayoutDashboard className="w-6 h-6 text-primary" /> Hola, {displayName}
        </h1>
        <p className="text-sm text-textMuted mt-1">Tu semana de turnos</p>
      </header>

      {/* KPIs personales */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-blue-50">
              <CalendarCheck className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-textMain">{misTurnos.length}</p>
              <p className="text-xs text-textMuted">Mis turnos</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-amber-50">
              <Clock className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-textMain">{pendientes}</p>
              <p className="text-xs text-textMuted">Solicitudes pendientes</p>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-3 rounded-lg bg-purple-50">
              <Sparkles className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-textMain">{conPropuestas}</p>
              <p className="text-xs text-textMuted">Esperando que elijas</p>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Turnos por día */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-textMain">Mis turnos esta semana</h2>
        </CardHeader>
        <CardBody>
          {misTurnos.length === 0 ? (
            <p className="text-sm text-textMuted py-4 text-center">
              Aún no tienes turnos asignados.
            </p>
          ) : (
            <div className="space-y-3">
              {Object.entries(turnosPorDia)
                .sort(([a], [b]) => Number(a) - Number(b))
                .map(([dia, turnos]) => (
                  <div key={dia} className="flex gap-4">
                    <div className="w-24 shrink-0">
                      <p className="text-xs font-medium text-textMuted uppercase tracking-wide">
                        {DIAS[Number(dia)]}
                      </p>
                    </div>
                    <div className="flex-1 flex flex-wrap gap-2">
                      {turnos
                        .sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio))
                        .map(t => (
                          <div
                            key={t.id_asignacion}
                            className="flex items-center gap-2 px-3 py-1.5 bg-primary/5 border border-primary/20 rounded-lg text-xs"
                          >
                            <span className="font-mono font-medium text-primary">{t.sala_codigo}</span>
                            <span className="text-textMuted">
                              {formatTime(t.hora_inicio)}–{formatTime(t.hora_fin)}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Mis solicitudes recientes */}
      {misSolicitudes.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-textMain">Mis solicitudes de cambio</h2>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Turno', 'Estado', 'Fecha'].map(h => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {misSolicitudes.slice(0, 5).map(s => (
                  <tr key={s.id_cambio}>
                    <td className="px-6 py-3 text-textMuted">
                      {s.asignacion_detalle.sala_codigo} · {s.asignacion_detalle.dia} · {formatTime(s.asignacion_detalle.hora_inicio)}–{formatTime(s.asignacion_detalle.hora_fin)}
                    </td>
                    <td className="px-6 py-3">
                      <Badge variant={
                        s.estado === 'pendiente' ? 'yellow' :
                        s.estado === 'con_propuestas' ? 'blue' :
                        s.estado === 'aprobada' ? 'green' : 'red'
                      }>
                        {s.estado === 'con_propuestas' ? 'Elige opción' : s.estado.charAt(0).toUpperCase() + s.estado.slice(1)}
                      </Badge>
                    </td>
                    <td className="px-6 py-3 text-textMuted text-xs">{formatDate(s.fecha_creacion)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
