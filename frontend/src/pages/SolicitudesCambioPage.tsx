import { useEffect, useState } from 'react'
import { cambiosApi, type SolicitudCambio } from '../api/cambios.api'
import { asignacionesApi, type Asignacion } from '../api/asignaciones.api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/ui/Toast'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Badge from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorMessage from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import UserAvatar from '../components/ui/UserAvatar'
import { ArrowLeftRight, Plus, CheckCircle, XCircle, Lightbulb, Sparkles } from 'lucide-react'
import { formatDate, formatTime } from '../utils/formatDate'
import type { StatusColor } from '../utils/statusMapper'

const estadoVariant: Record<string, StatusColor> = {
  pendiente:           'yellow',
  con_propuestas:      'blue',
  esperando_candidato: 'yellow',
  aprobada:            'green',
  rechazada:           'red',
}

const estadoLabel: Record<string, string> = {
  pendiente:           'Pendiente',
  con_propuestas:      'Con propuestas',
  esperando_candidato: 'Esperando candidato',
  aprobada:            'Aprobada',
  rechazada:           'Rechazada',
}

/** Helper: parsea detail estructurado del backend en un string legible. */
function parseErrorDetail(e: any, fallback: string): string {
  const data = e?.response?.data
  let msg = data?.error || fallback
  const detail = data?.detail
  if (detail) {
    if (typeof detail === 'string') {
      msg = detail
    } else if (Array.isArray(detail)) {
      msg = detail.join(' · ')
    } else if (typeof detail === 'object') {
      const parts: string[] = []
      for (const [field, value] of Object.entries(detail)) {
        const txt = Array.isArray(value) ? value.join(' · ') : String(value)
        parts.push(['swap', 'opcion', 'non_field_errors'].includes(field) ? txt : `${field}: ${txt}`)
      }
      if (parts.length > 0) msg = parts.join(' · ')
    }
  }
  return msg
}

export default function SolicitudesCambioPage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const isAdmin = user?.rol === 'admin'

  const [solicitudes,  setSolicitudes]  = useState<SolicitudCambio[]>([])
  const [filterEstado, setFilterEstado] = useState<string>('')
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState(false)

  // Crear solicitud (monitor)
  const [createOpen, setCreateOpen] = useState(false)
  const [misAsignaciones, setMisAsignaciones] = useState<Asignacion[]>([])
  const [createForm, setCreateForm] = useState({ asignacion: '', motivo: '' })
  const [creating, setCreating] = useState(false)

  // Proponer opciones (admin)
  const [proposeOpen, setProposeOpen]   = useState(false)
  const [proposeTarget, setProposeTarget] = useState<SolicitudCambio | null>(null)
  const [candidatos, setCandidatos] = useState<Asignacion[]>([])
  const [loadingCand, setLoadingCand] = useState(false)
  const [seleccionadas, setSeleccionadas] = useState<number[]>([])
  const [proposeResp, setProposeResp] = useState('')
  const [proposing, setProposing] = useState(false)

  // Elegir opcion (monitor)
  const [chooseOpen, setChooseOpen] = useState(false)
  const [chooseTarget, setChooseTarget] = useState<SolicitudCambio | null>(null)
  const [chosen, setChosen] = useState<number | null>(null)
  const [choosing, setChoosing] = useState(false)

  // Rechazar (admin)
  const [rejectOpen,  setRejectOpen]   = useState(false)
  const [rejectTarget,setRejectTarget] = useState<SolicitudCambio | null>(null)
  const [rejectMsg,   setRejectMsg]    = useState('')
  const [rejecting,   setRejecting]    = useState(false)

  const load = () => {
    setLoading(true)
    setError(false)
    cambiosApi.list(filterEstado ? { estado: filterEstado } : undefined)
      .then(r => setSolicitudes(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterEstado])

  // ---- Crear (monitor) ----
  const openCreate = async () => {
    setCreateForm({ asignacion: '', motivo: '' })
    setCreateOpen(true)
    try {
      const a = await asignacionesApi.list(user?.id ? { monitor: user.id } : {})
      setMisAsignaciones(a.data)
    } catch {
      showToast('Error al cargar tus turnos', 'error')
    }
  }

  const handleCreate = async () => {
    if (!createForm.asignacion) return
    setCreating(true)
    try {
      await cambiosApi.create({
        asignacion: Number(createForm.asignacion),
        motivo:     createForm.motivo || undefined,
      })
      showToast('Solicitud enviada — el admin propondra opciones de cambio')
      setCreateOpen(false)
      load()
    } catch (e: any) {
      showToast(e?.response?.data?.error || 'Error al enviar solicitud', 'error')
    } finally {
      setCreating(false)
    }
  }

  // ---- Proponer (admin) ----
  const openPropose = async (s: SolicitudCambio) => {
    setProposeTarget(s)
    setSeleccionadas([])
    setProposeResp('')
    setProposeOpen(true)
    setLoadingCand(true)
    try {
      const r = await cambiosApi.candidatos(s.id_cambio)
      setCandidatos(r.data)
    } catch {
      showToast('Error al cargar candidatos', 'error')
      setCandidatos([])
    } finally {
      setLoadingCand(false)
    }
  }

  const toggleCandidato = (id: number) => {
    setSeleccionadas(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const handlePropose = async () => {
    if (!proposeTarget || seleccionadas.length < 2) return
    setProposing(true)
    try {
      await cambiosApi.proponer(proposeTarget.id_cambio, {
        opciones: seleccionadas,
        respuesta: proposeResp || undefined,
      })
      showToast(`${seleccionadas.length} opciones enviadas al monitor`)
      setProposeOpen(false)
      load()
    } catch (e: any) {
      showToast(e?.response?.data?.error || 'Error al proponer opciones', 'error')
    } finally {
      setProposing(false)
    }
  }

  // ---- Elegir (monitor) ----
  const openChoose = (s: SolicitudCambio) => {
    setChooseTarget(s)
    setChosen(null)
    setChooseOpen(true)
  }

  const handleChoose = async () => {
    if (!chooseTarget || chosen === null) return
    setChoosing(true)
    try {
      await cambiosApi.elegir(chooseTarget.id_cambio, { opcion: chosen })
      showToast('Swap ejecutado — tus turnos han sido intercambiados')
      setChooseOpen(false)
      load()
    } catch (e: any) {
      showToast(parseErrorDetail(e, 'Error al ejecutar el swap'), 'error')
    } finally {
      setChoosing(false)
    }
  }

  // ---- Rechazar (admin) ----
  const openReject = (s: SolicitudCambio) => {
    setRejectTarget(s)
    setRejectMsg('')
    setRejectOpen(true)
  }

  const handleReject = async () => {
    if (!rejectTarget) return
    setRejecting(true)
    try {
      await cambiosApi.rechazar(rejectTarget.id_cambio, { respuesta: rejectMsg || undefined })
      showToast('Solicitud rechazada')
      setRejectOpen(false)
      load()
    } catch (e: any) {
      showToast(e?.response?.data?.error || 'Error al rechazar', 'error')
    } finally {
      setRejecting(false)
    }
  }

  const asigLabel = (a: Asignacion) =>
    `${a.sala_codigo} · ${a.dia_semana_display} · ${formatTime(a.hora_inicio)}–${formatTime(a.hora_fin)} (${a.semestre_label})`

  // Agrupa candidatos por monitor para el modal de proponer
  const candidatosPorMonitor = candidatos.reduce<Record<number, Asignacion[]>>((acc, a) => {
    (acc[a.monitor] ||= []).push(a)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-textMain flex items-center gap-2">
            <ArrowLeftRight className="w-6 h-6 text-primary" /> Solicitudes de cambio
          </h1>
          <p className="text-sm text-textMuted mt-1">
            Monitor solicita · Admin propone opciones · Solicitante elige y el swap se ejecuta
          </p>
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
          <option value="con_propuestas">Con propuestas</option>
          <option value="esperando_candidato">Esperando candidato</option>
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
                  {['Solicitante', 'Turno', 'Estado', 'Opciones', 'Motivo', 'Fecha', 'Accion'].map((h, i) => (
                    <th key={i} className={`px-4 py-3 ${i === 6 ? 'text-right' : 'text-left'} text-xs font-medium text-textMuted uppercase tracking-wide`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {solicitudes.map(s => {
                  const esMiSolicitud = s.solicitante === user?.id
                  return (
                    <tr key={s.id_cambio} className="hover:bg-gray-50/50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <UserAvatar userId={s.solicitante} name={s.solicitante_nombre} size="sm" />
                          <span className="font-medium text-textMain">{s.solicitante_nombre}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-textMuted text-xs">
                        {s.asignacion_detalle.sala_codigo} · {s.asignacion_detalle.dia} ·{' '}
                        {formatTime(s.asignacion_detalle.hora_inicio)}–{formatTime(s.asignacion_detalle.hora_fin)}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={estadoVariant[s.estado] ?? 'gray'}>
                          {estadoLabel[s.estado] ?? s.estado}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-textMuted text-xs">
                        {s.estado === 'con_propuestas' && s.opciones.length > 0 ? (
                          <div className="flex gap-1">
                            {s.opciones.map(op => (
                              <UserAvatar
                                key={op.id_opcion}
                                userId={op.asignacion_swap_detalle.id_asignacion}
                                name={op.monitor_swap_nombre}
                                size="xs"
                                ringed
                              />
                            ))}
                          </div>
                        ) : s.estado === 'aprobada' && s.monitor_reemplazo_nombre ? (
                          <div className="flex items-center gap-1">
                            <UserAvatar userId={s.monitor_reemplazo} name={s.monitor_reemplazo_nombre} size="xs" />
                            <span>{s.monitor_reemplazo_nombre}</span>
                          </div>
                        ) : (
                          <span className="italic text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-textMuted max-w-xs truncate">{s.motivo || '—'}</td>
                      <td className="px-4 py-3 text-textMuted text-xs">{formatDate(s.fecha_creacion)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-1">
                          {/* Admin: proponer mientras este pendiente */}
                          {isAdmin && s.estado === 'pendiente' && (
                            <Button variant="ghost" size="sm" onClick={() => openPropose(s)} title="Proponer opciones de cambio">
                              <Lightbulb className="w-4 h-4 text-blue-600" />
                            </Button>
                          )}
                          {/* Admin: rechazar en cualquier estado no terminal */}
                          {isAdmin && ['pendiente', 'con_propuestas'].includes(s.estado) && (
                            <Button variant="ghost" size="sm" onClick={() => openReject(s)} title="Rechazar">
                              <XCircle className="w-4 h-4 text-danger" />
                            </Button>
                          )}
                          {/* Solicitante: elegir opcion (el swap se ejecuta al elegir) */}
                          {!isAdmin && esMiSolicitud && s.estado === 'con_propuestas' && (
                            <Button size="sm" onClick={() => openChoose(s)}>
                              <Sparkles className="w-3.5 h-3.5" /> Elegir opcion
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* ============== MODAL: monitor crea solicitud ============== */}
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

          <div className="flex items-start gap-3 bg-blue-50 border border-blue-200 rounded-lg p-3">
            <ArrowLeftRight className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
            <p className="text-sm text-blue-800 leading-relaxed">
              El administrador te propondra <strong>al menos 2 opciones</strong> de cambio
              (swap con otros monitores). Tu decides cual swap aceptar.
            </p>
          </div>

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

      {/* ============== MODAL: admin propone opciones ============== */}
      <Modal
        open={proposeOpen}
        onClose={() => setProposeOpen(false)}
        title="Proponer opciones de cambio"
        footer={
          <>
            <Button variant="secondary" onClick={() => setProposeOpen(false)}>Cancelar</Button>
            <Button onClick={handlePropose} disabled={proposing || seleccionadas.length < 2}>
              {proposing
                ? 'Enviando…'
                : seleccionadas.length < 2
                  ? `Selecciona ${2 - seleccionadas.length} mas`
                  : `Enviar ${seleccionadas.length} opciones`}
            </Button>
          </>
        }
      >
        {proposeTarget && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
              <div className="flex items-center gap-2">
                <UserAvatar userId={proposeTarget.solicitante} name={proposeTarget.solicitante_nombre} size="sm" />
                <span className="font-medium">{proposeTarget.solicitante_nombre}</span>
              </div>
              <p className="text-textMuted">
                <strong>Turno:</strong> {proposeTarget.asignacion_detalle.sala_codigo} · {proposeTarget.asignacion_detalle.dia} ·{' '}
                {formatTime(proposeTarget.asignacion_detalle.hora_inicio)}–{formatTime(proposeTarget.asignacion_detalle.hora_fin)}
              </p>
              {proposeTarget.motivo && <p className="text-textMuted"><strong>Motivo:</strong> {proposeTarget.motivo}</p>}
            </div>

            <p className="text-sm text-textMain">
              Selecciona <strong>al menos 2</strong> turnos de otros monitores para ofrecer
              como opcion de swap. El solicitante elegira cual acepta.
            </p>

            {loadingCand ? (
              <Spinner text="Cargando candidatos…" />
            ) : Object.keys(candidatosPorMonitor).length === 0 ? (
              <EmptyState
                title="Sin candidatos"
                description="No hay turnos disponibles para swap en este semestre."
              />
            ) : (
              <div className="space-y-3 max-h-72 overflow-y-auto">
                {Object.entries(candidatosPorMonitor).map(([monitorId, asignaciones]) => {
                  const monitorIdNum = Number(monitorId)
                  const nombre = asignaciones[0].monitor_nombre
                  return (
                    <div key={monitorId} className="border border-gray-100 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <UserAvatar userId={monitorIdNum} name={nombre} size="sm" />
                        <span className="font-medium text-sm">{nombre}</span>
                      </div>
                      <div className="space-y-1 ml-2">
                        {asignaciones.map(a => (
                          <label key={a.id_asignacion} className="flex items-center gap-2 cursor-pointer p-1.5 rounded hover:bg-gray-50">
                            <input
                              type="checkbox"
                              className="rounded border-gray-300 text-primary focus:ring-primary/30"
                              checked={seleccionadas.includes(a.id_asignacion)}
                              onChange={() => toggleCandidato(a.id_asignacion)}
                            />
                            <span className="text-xs text-textMuted">
                              {a.sala_codigo} · {a.dia_semana_display} ·{' '}
                              {formatTime(a.hora_inicio)}–{formatTime(a.hora_fin)}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            <label className="block">
              <span className="text-sm font-medium text-textMain">Mensaje al solicitante (opcional)</span>
              <textarea
                rows={2}
                className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 resize-none"
                placeholder="Notas para el monitor…"
                value={proposeResp}
                onChange={e => setProposeResp(e.target.value)}
              />
            </label>
          </div>
        )}
      </Modal>

      {/* ============== MODAL: monitor elige opcion ============== */}
      <Modal
        open={chooseOpen}
        onClose={() => setChooseOpen(false)}
        title="Elige tu cambio de turno"
        footer={
          <>
            <Button variant="secondary" onClick={() => setChooseOpen(false)}>Cancelar</Button>
            <Button onClick={handleChoose} disabled={choosing || chosen === null}>
              {choosing ? 'Ejecutando swap…' : 'Aceptar opcion'}
            </Button>
          </>
        }
      >
        {chooseTarget && (
          <div className="space-y-4">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
              <p>
                <strong>Tu turno actual:</strong> {chooseTarget.asignacion_detalle.sala_codigo} ·{' '}
                {chooseTarget.asignacion_detalle.dia} ·{' '}
                {formatTime(chooseTarget.asignacion_detalle.hora_inicio)}–{formatTime(chooseTarget.asignacion_detalle.hora_fin)}
              </p>
              <p className="mt-1">
                Al elegir una opcion, tu turno se intercambia con el del otro monitor.
              </p>
            </div>

            {chooseTarget.respuesta && (
              <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-800">
                <strong>Nota del admin:</strong> {chooseTarget.respuesta}
              </div>
            )}

            <div className="space-y-2">
              {chooseTarget.opciones.map(op => (
                <label
                  key={op.id_opcion}
                  className={[
                    'block border rounded-lg p-3 cursor-pointer transition-colors',
                    chosen === op.id_opcion
                      ? 'border-primary bg-primary/5 ring-2 ring-primary/30'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50',
                  ].join(' ')}
                >
                  <input
                    type="radio"
                    name="opcion"
                    value={op.id_opcion}
                    checked={chosen === op.id_opcion}
                    onChange={() => setChosen(op.id_opcion)}
                    className="sr-only"
                  />
                  <div className="flex items-start gap-3">
                    <UserAvatar
                      userId={op.asignacion_swap_detalle.id_asignacion}
                      name={op.monitor_swap_nombre}
                      size="md"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-textMain">Opcion {op.orden}: {op.monitor_swap_nombre}</p>
                      <p className="text-xs text-textMuted mt-0.5">
                        Tomarias: <strong>{op.asignacion_swap_detalle.sala_codigo}</strong> ·{' '}
                        {op.asignacion_swap_detalle.dia} ·{' '}
                        {formatTime(op.asignacion_swap_detalle.hora_inicio)}–{formatTime(op.asignacion_swap_detalle.hora_fin)}
                      </p>
                      <p className="text-xs text-textMuted mt-0.5">
                        El tomaria tu turno original.
                      </p>
                    </div>
                    {chosen === op.id_opcion && <CheckCircle className="w-5 h-5 text-primary shrink-0" />}
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}
      </Modal>

      {/* ============== MODAL: admin rechaza ============== */}
      <Modal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        title="Rechazar solicitud"
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejectOpen(false)}>Cancelar</Button>
            <Button variant="danger" onClick={handleReject} disabled={rejecting}>
              {rejecting ? 'Guardando…' : 'Rechazar'}
            </Button>
          </>
        }
      >
        {rejectTarget && (
          <div className="space-y-4">
            <p className="text-sm text-textMuted">
              Solicitud de <strong>{rejectTarget.solicitante_nombre}</strong> para cambiar el turno{' '}
              <strong>{rejectTarget.asignacion_detalle.sala_codigo} · {rejectTarget.asignacion_detalle.dia} ·{' '}
              {formatTime(rejectTarget.asignacion_detalle.hora_inicio)}–{formatTime(rejectTarget.asignacion_detalle.hora_fin)}</strong>.
            </p>
            <label className="block">
              <span className="text-sm font-medium text-textMain">Motivo del rechazo (opcional)</span>
              <textarea
                rows={3}
                className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 resize-none"
                placeholder="Razon…"
                value={rejectMsg}
                onChange={e => setRejectMsg(e.target.value)}
              />
            </label>
          </div>
        )}
      </Modal>
    </div>
  )
}
