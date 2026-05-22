import { useEffect, useState } from 'react'
import { cambiosApi, type SolicitudCambio } from '../api/cambios.api'
import { asignacionesApi, type Asignacion } from '../api/asignaciones.api'
import { monitoresApi } from '../api/monitores.api'
import type { SessionUser } from '../api/auth.api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/ui/Toast'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorMessage from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import { ArrowLeftRight, Plus, CheckCircle, XCircle } from 'lucide-react'
import { formatDate, formatTime } from '../utils/formatDate'
import type { StatusColor } from '../utils/statusMapper'

const estadoVariant: Record<string, StatusColor> = {
  pendiente: 'yellow',
  aprobada:  'green',
  rechazada: 'red',
}

export default function SolicitudesCambioPage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const isAdmin = user?.rol === 'admin'

  const [solicitudes, setSolicitudes]  = useState<SolicitudCambio[]>([])
  const [filterEstado, setFilterEstado] = useState<string>('')
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(false)

  // Create modal (monitor)
  const [createOpen, setCreateOpen] = useState(false)
  const [misAsignaciones, setMisAsignaciones] = useState<Asignacion[]>([])
  const [monitores, setMonitores] = useState<SessionUser[]>([])
  const [createForm, setCreateForm] = useState({ asignacion: '', monitor_reemplazo: '', motivo: '' })
  const [creating, setCreating] = useState(false)

  // Respond modal (admin)
  const [respondOpen,   setRespondOpen]   = useState(false)
  const [respondTarget, setRespondTarget] = useState<SolicitudCambio | null>(null)
  const [respondForm,   setRespondForm]   = useState({ estado: 'aprobada', respuesta: '' })
  const [responding,    setResponding]    = useState(false)

  const load = () => {
    setLoading(true)
    setError(false)
    cambiosApi.list(filterEstado ? { estado: filterEstado } : undefined)
      .then(r => setSolicitudes(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterEstado])

  const openCreate = async () => {
    setCreateForm({ asignacion: '', monitor_reemplazo: '', motivo: '' })
    setCreateOpen(true)
    try {
      const [a, m] = await Promise.all([
        asignacionesApi.list(user?.id ? { monitor: user.id } : {}),
        monitoresApi.list(),
      ])
      setMisAsignaciones(a.data)
      setMonitores(m.data.filter(u => u.rol === 'monitor' && u.id !== user?.id))
    } catch {
      showToast('Error al cargar datos', 'error')
    }
  }

  const handleCreate = async () => {
    if (!createForm.asignacion || !createForm.monitor_reemplazo) return
    setCreating(true)
    try {
      await cambiosApi.create({
        asignacion:         Number(createForm.asignacion),
        monitor_reemplazo:  Number(createForm.monitor_reemplazo),
        motivo:             createForm.motivo || undefined,
      })
      showToast('Solicitud enviada')
      setCreateOpen(false)
      load()
    } catch {
      showToast('Error al enviar solicitud', 'error')
    } finally {
      setCreating(false)
    }
  }

  const openRespond = (s: SolicitudCambio) => {
    setRespondTarget(s)
    setRespondForm({ estado: 'aprobada', respuesta: '' })
    setRespondOpen(true)
  }

  const handleRespond = async () => {
    if (!respondTarget) return
    setResponding(true)
    try {
      await cambiosApi.responder(respondTarget.id_cambio, {
        estado:    respondForm.estado as 'aprobada' | 'rechazada',
        respuesta: respondForm.respuesta || undefined,
      })
      showToast(`Solicitud ${respondForm.estado === 'aprobada' ? 'aprobada' : 'rechazada'}`)
      setRespondOpen(false)
      load()
    } catch {
      showToast('Error al responder solicitud', 'error')
    } finally {
      setResponding(false)
    }
  }

  const asigLabel = (a: Asignacion) =>
    `${a.sala_codigo} · ${a.dia_semana_display} · ${formatTime(a.hora_inicio)}–${formatTime(a.hora_fin)} (${a.semestre_label})`

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-textMain flex items-center gap-2">
            <ArrowLeftRight className="w-6 h-6 text-primary" /> Solicitudes de cambio
          </h1>
          <p className="text-sm text-textMuted mt-1">Peticiones de intercambio de turnos entre monitores</p>
        </div>
        {!isAdmin && (
          <Button onClick={openCreate}>
            <Plus className="w-4 h-4" /> Solicitar cambio
          </Button>
        )}
      </header>

      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-textMain">Estado:</label>
        <select
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          value={filterEstado}
          onChange={e => setFilterEstado(e.target.value)}
        >
          <option value="">Todos</option>
          <option value="pendiente">Pendiente</option>
          <option value="aprobada">Aprobada</option>
          <option value="rechazada">Rechazada</option>
        </select>
      </div>

      <Card>
        {loading ? <Spinner /> : error ? <ErrorMessage onRetry={load} /> : solicitudes.length === 0 ? (
          <EmptyState
            title="Sin solicitudes"
            description="No hay solicitudes de cambio para este filtro."
            action={!isAdmin ? <Button onClick={openCreate}><Plus className="w-4 h-4" /> Solicitar cambio</Button> : undefined}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Solicitante', 'Reemplazo', 'Turno', 'Motivo', 'Estado', 'Fecha', ...(isAdmin ? [''] : [])].map((h, i) => (
                    <th key={i} className={`px-6 py-3 ${i === 6 ? 'text-right' : 'text-left'} text-xs font-medium text-textMuted uppercase tracking-wide`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {solicitudes.map(s => (
                  <tr key={s.id_cambio} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-medium text-textMain">{s.solicitante_nombre}</td>
                    <td className="px-6 py-3 text-textMuted">{s.monitor_reemplazo_nombre}</td>
                    <td className="px-6 py-3 text-textMuted text-xs">
                      {s.asignacion_detalle
                        ? `${s.asignacion_detalle.sala} · ${s.asignacion_detalle.dia} · ${formatTime(s.asignacion_detalle.hora_inicio)}–${formatTime(s.asignacion_detalle.hora_fin)}`
                        : `#${s.asignacion}`
                      }
                    </td>
                    <td className="px-6 py-3 text-textMuted max-w-xs truncate">{s.motivo || '—'}</td>
                    <td className="px-6 py-3">
                      <Badge variant={estadoVariant[s.estado] ?? 'gray'}>
                        {s.estado.charAt(0).toUpperCase() + s.estado.slice(1)}
                      </Badge>
                    </td>
                    <td className="px-6 py-3 text-textMuted">{formatDate(s.fecha_creacion)}</td>
                    {isAdmin && (
                      <td className="px-6 py-3 text-right">
                        {s.estado === 'pendiente' && (
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="sm" onClick={() => openRespond(s)} title="Aprobar / Rechazar">
                              <CheckCircle className="w-4 h-4 text-success" />
                            </Button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Monitor: create solicitud */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Solicitar cambio de turno"
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancelar</Button>
            <Button onClick={handleCreate} disabled={creating}>{creating ? 'Enviando…' : 'Enviar solicitud'}</Button>
          </>
        }
      >
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-textMain">Tu turno a cambiar</span>
            <select
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={createForm.asignacion}
              onChange={e => setCreateForm(f => ({ ...f, asignacion: e.target.value }))}
            >
              <option value="">Seleccionar turno…</option>
              {misAsignaciones.map(a => (
                <option key={a.id_asignacion} value={a.id_asignacion}>{asigLabel(a)}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium text-textMain">Monitor de reemplazo</span>
            <select
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={createForm.monitor_reemplazo}
              onChange={e => setCreateForm(f => ({ ...f, monitor_reemplazo: e.target.value }))}
            >
              <option value="">Seleccionar monitor…</option>
              {monitores.map(m => (
                <option key={m.id} value={m.id}>
                  {[m.first_name, m.last_name].filter(Boolean).join(' ') || m.email}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium text-textMain">Motivo (opcional)</span>
            <textarea
              rows={3}
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 resize-none"
              placeholder="Explica el motivo del cambio…"
              value={createForm.motivo}
              onChange={e => setCreateForm(f => ({ ...f, motivo: e.target.value }))}
            />
          </label>
        </div>
      </Modal>

      {/* Admin: respond to solicitud */}
      <Modal
        open={respondOpen}
        onClose={() => setRespondOpen(false)}
        title="Responder solicitud"
        footer={
          <>
            <Button variant="secondary" onClick={() => setRespondOpen(false)}>Cancelar</Button>
            <Button
              variant={respondForm.estado === 'aprobada' ? 'primary' : 'danger'}
              onClick={handleRespond}
              disabled={responding}
            >
              {responding ? 'Guardando…' : respondForm.estado === 'aprobada' ? 'Aprobar' : 'Rechazar'}
            </Button>
          </>
        }
      >
        {respondTarget && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
              <p><span className="font-medium">Solicitante:</span> {respondTarget.solicitante_nombre}</p>
              <p><span className="font-medium">Reemplazo:</span> {respondTarget.monitor_reemplazo_nombre}</p>
              {respondTarget.motivo && <p><span className="font-medium">Motivo:</span> {respondTarget.motivo}</p>}
            </div>
            <div>
              <span className="text-sm font-medium text-textMain">Decisión</span>
              <div className="mt-2 flex gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="estado"
                    value="aprobada"
                    checked={respondForm.estado === 'aprobada'}
                    onChange={() => setRespondForm(f => ({ ...f, estado: 'aprobada' }))}
                    className="text-success"
                  />
                  <CheckCircle className="w-4 h-4 text-success" />
                  <span className="text-sm">Aprobar</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="estado"
                    value="rechazada"
                    checked={respondForm.estado === 'rechazada'}
                    onChange={() => setRespondForm(f => ({ ...f, estado: 'rechazada' }))}
                    className="text-danger"
                  />
                  <XCircle className="w-4 h-4 text-danger" />
                  <span className="text-sm">Rechazar</span>
                </label>
              </div>
            </div>
            <label className="block">
              <span className="text-sm font-medium text-textMain">Respuesta (opcional)</span>
              <textarea
                rows={3}
                className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 resize-none"
                placeholder="Observaciones…"
                value={respondForm.respuesta}
                onChange={e => setRespondForm(f => ({ ...f, respuesta: e.target.value }))}
              />
            </label>
          </div>
        )}
      </Modal>
    </div>
  )
}
