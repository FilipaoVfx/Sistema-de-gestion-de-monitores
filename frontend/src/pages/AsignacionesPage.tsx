import { useEffect, useState } from 'react'
import { asignacionesApi, type Asignacion } from '../api/asignaciones.api'
import { monitoresApi } from '../api/monitores.api'
import type { SessionUser } from '../api/auth.api'
import { salasApi } from '../api/salas.api'
import { horariosApi, type Horario } from '../api/horarios.api'
// Semestre ya no se usa en este componente — el backend infiere del activo
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/ui/Toast'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import ErrorMessage from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import UserAvatar from '../components/ui/UserAvatar'
import WeeklyScheduleGrid from '../components/WeeklyScheduleGrid'
import { CalendarCheck, Plus, Trash2, LayoutGrid, Table as TableIcon } from 'lucide-react'
import { formatTime } from '../utils/formatDate'

interface SalaR { id_sala: number; codigo: string; nombre: string }
type ViewMode = 'grid' | 'table'

const DIAS: Record<number, string> = {
  1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb',
}

export default function AsignacionesPage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const isAdmin = user?.rol === 'admin'

  // Vista: admin tiene toggle grid/table; monitor solo grid (mi cronograma)
  const [view, setView] = useState<ViewMode>('grid')

  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [horariosAll,  setHorariosAll]  = useState<Horario[]>([])
  const [salas,        setSalas]        = useState<SalaR[]>([])
  const [filterSala,   setFilterSala]   = useState<number | ''>('')
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState(false)

  // Bulk create modal (admin) - semestre se infiere del activo en backend
  const [modalOpen, setModalOpen] = useState(false)
  const [monitores, setMonitores] = useState<SessionUser[]>([])
  const [salaHorarios, setSalaHorarios] = useState<Horario[]>([])
  const [form, setForm] = useState({ monitor: '', sala: '' })
  const [selectedHorarios, setSelectedHorarios] = useState<number[]>([])
  const [loadingHorarios, setLoadingHorarios] = useState(false)
  const [saving, setSaving] = useState(false)

  // Cell detail modal (admin click en celda de la grilla)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailAsignaciones, setDetailAsignaciones] = useState<Asignacion[]>([])
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const load = () => {
    setLoading(true); setError(false)

    // El backend filtra por semestre activo automaticamente.
    // Monitor: backend ya filtra a sus asignaciones.
    const asigParams: Record<string, number> = {}
    if (isAdmin && filterSala !== '') {
      asigParams.sala = filterSala as number
    }

    Promise.all([
      asignacionesApi.list(Object.keys(asigParams).length > 0 ? asigParams : undefined),
      horariosApi.list(isAdmin && filterSala !== '' ? (filterSala as number) : undefined),
      isAdmin ? salasApi.list() : Promise.resolve({ data: [] }),
    ])
      .then(([a, h, s]) => {
        setAsignaciones(a.data)
        setHorariosAll(h.data)
        setSalas(s.data as unknown as SalaR[])
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterSala])

  // ---- Bulk create (admin) ----
  const openModal = async () => {
    setForm({ monitor: '', sala: '' })
    setSelectedHorarios([])
    setSalaHorarios([])
    setModalOpen(true)
    try {
      const m = await monitoresApi.list()
      setMonitores(m.data.filter(u => u.rol === 'monitor'))
    } catch {
      showToast('Error al cargar monitores', 'error')
    }
  }

  /** Recarga horarios de la sala. El backend anota ocupacion con el semestre activo. */
  const reloadHorariosSala = async (salaId: string) => {
    if (!salaId) { setSalaHorarios([]); return }
    setLoadingHorarios(true)
    try {
      const h = await horariosApi.list(Number(salaId))
      setSalaHorarios(h.data)
    } catch {
      setSalaHorarios([])
    } finally {
      setLoadingHorarios(false)
    }
  }

  const onSalaChange = async (salaId: string) => {
    setForm(f => ({ ...f, sala: salaId }))
    setSelectedHorarios([])
    await reloadHorariosSala(salaId)
  }

  const toggleHorario = (id: number) => {
    setSelectedHorarios(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const handleSave = async () => {
    if (!form.monitor || !form.sala || selectedHorarios.length === 0) return
    setSaving(true)
    try {
      // semestre se infiere automaticamente del activo en backend
      const res = await asignacionesApi.bulk({
        monitor:  Number(form.monitor),
        sala:     Number(form.sala),
        horarios: selectedHorarios.map(id => `h:${id}`),
      })
      showToast(`${res.data.creadas} asignación(es) creada(s)`)
      setModalOpen(false)
      load()
    } catch (e: any) {
      const status = e?.response?.status
      const data   = e?.response?.data
      let msg = data?.error || 'Error al crear asignaciones'

      if (status === 403 && data?.detail && typeof data.detail === 'object') {
        const d = data.detail
        msg = `${data.error || 'Acceso denegado'} · Sesion: ${d.usuario || '?'} (rol "${d.rol_detectado || '?'}"). ${d.hint || ''}`
      } else if (data?.detail) {
        const d = data.detail
        if (typeof d === 'string') {
          msg = d
        } else if (Array.isArray(d)) {
          msg = d.join(' · ')
        } else if (typeof d === 'object') {
          // 500 con type/msg/traceback: mostramos type+msg en toast, traceback en console
          if (d.type && d.msg) {
            msg = `${data.error || 'Error'}: ${d.type}: ${d.msg}`
            console.error('Backend error detail:', d)
          } else {
            const parts: string[] = []
            for (const [field, value] of Object.entries(d)) {
              if (field === 'traceback') continue
              const txt = Array.isArray(value) ? value.join(' · ') : String(value)
              parts.push(`${field}: ${txt}`)
            }
            msg = parts.join(' · ') || msg
          }
        }
      }
      showToast(msg, 'error')
    } finally {
      setSaving(false)
    }
  }

  // ---- Delete (admin) ----
  const handleDelete = async (a: Asignacion) => {
    if (!confirm(`¿Liberar a ${a.monitor_nombre} del turno ${a.sala_codigo} · ${a.dia_semana_display} · ${formatTime(a.hora_inicio)}–${formatTime(a.hora_fin)}?`)) return
    setDeletingId(a.id_asignacion)
    try {
      await asignacionesApi.remove(a.id_asignacion)
      showToast('Asignación eliminada — monitor liberado')
      // Quita la asignación del modal de detalle también
      setDetailAsignaciones(prev => prev.filter(x => x.id_asignacion !== a.id_asignacion))
      load()
    } catch {
      showToast('No se pudo eliminar la asignación', 'error')
    } finally {
      setDeletingId(null)
    }
  }

  const handleCellClick = (_slot: unknown, asigs: Asignacion[]) => {
    if (!isAdmin) return
    if (asigs.length === 0) return
    setDetailAsignaciones(asigs)
    setDetailOpen(true)
  }


  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-textMain flex items-center gap-2">
            <CalendarCheck className="w-6 h-6 text-primary" />
            {isAdmin ? 'Asignaciones' : 'Mi cronograma'}
          </h1>
          <p className="text-sm text-textMuted mt-1">
            {isAdmin
              ? 'Cronograma semanal — click en una celda para liberar al monitor del turno'
              : 'Tus turnos asignados en el semestre activo'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Toggle solo para admin */}
          {isAdmin && (
            <div className="inline-flex rounded-lg border border-gray-200 p-0.5 bg-gray-50">
              <button
                onClick={() => setView('grid')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${view === 'grid' ? 'bg-white text-textMain shadow-sm' : 'text-textMuted hover:text-textMain'}`}
              >
                <LayoutGrid className="w-3.5 h-3.5" /> Grilla
              </button>
              <button
                onClick={() => setView('table')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${view === 'table' ? 'bg-white text-textMain shadow-sm' : 'text-textMuted hover:text-textMain'}`}
              >
                <TableIcon className="w-3.5 h-3.5" /> Tabla
              </button>
            </div>
          )}
          {isAdmin && (
            <Button onClick={openModal}>
              <Plus className="w-4 h-4" /> Nueva asignación
            </Button>
          )}
        </div>
      </header>

      {/* Filtros solo para admin - el semestre se infiere del activo */}
      {isAdmin && (
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium text-textMain">Sala:</label>
          <select
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            value={filterSala}
            onChange={e => setFilterSala(e.target.value !== '' ? Number(e.target.value) : '')}
          >
            <option value="">Todas las salas</option>
            {salas.map(s => (
              <option key={s.id_sala} value={s.id_sala}>{s.codigo} — {s.nombre}</option>
            ))}
          </select>
        </div>
      )}

      <Card>
        {loading ? (
          <Spinner />
        ) : error ? (
          <ErrorMessage onRetry={load} />
        ) : !isAdmin ? (
          /* Monitor: solo grilla con sus turnos. Si no tiene, empty state. */
          asignaciones.length === 0 ? (
            <EmptyState
              title="Sin turnos asignados"
              description="Aún no tienes turnos en el semestre activo. Contacta al administrador."
            />
          ) : (
            <WeeklyScheduleGrid
              horarios={asignaciones.map(a => ({
                id_horario: a.horario,
                sala: a.id_sala,
                dia_semana: a.dia_semana,
                dia_semana_display: a.dia_semana_display,
                hora_inicio: a.hora_inicio,
                hora_fin: a.hora_fin,
              }))}
              asignaciones={asignaciones}
              highlightUserId={user?.id}
            />
          )
        ) : view === 'grid' ? (
          horariosAll.length === 0 ? (
            <EmptyState title="Sin horarios" description="No hay horarios para construir la grilla. Crea algunos en la página de Horarios." />
          ) : (
            <WeeklyScheduleGrid
              horarios={horariosAll}
              asignaciones={asignaciones}
              onCellClick={handleCellClick}
            />
          )
        ) : asignaciones.length === 0 ? (
          <EmptyState
            title="Sin asignaciones"
            description="No hay asignaciones para este filtro."
            action={<Button onClick={openModal}><Plus className="w-4 h-4" /> Nueva asignación</Button>}
          />
        ) : (
          /* Vista tabla admin */
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Monitor', 'Sala', 'Día', 'Horario', ''].map((h, i) => (
                    <th key={i} className={`px-6 py-3 ${i === 4 ? 'text-right' : 'text-left'} text-xs font-medium text-textMuted uppercase tracking-wide`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {asignaciones.map(a => (
                  <tr key={a.id_asignacion} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2">
                        <UserAvatar userId={a.monitor} name={a.monitor_nombre} size="sm" />
                        <span className="font-medium text-textMain">{a.monitor_nombre}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3 text-textMuted font-mono">{a.sala_codigo}</td>
                    <td className="px-6 py-3 text-textMuted">{a.dia_semana_display || DIAS[a.dia_semana]}</td>
                    <td className="px-6 py-3 text-textMuted">{formatTime(a.hora_inicio)}–{formatTime(a.hora_fin)}</td>
                    <td className="px-6 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(a)}
                        disabled={deletingId === a.id_asignacion}
                        title="Eliminar asignación y liberar monitor"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-danger" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Modal: detalle de celda (admin) — permite eliminar asignaciones */}
      <Modal
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title="Asignaciones en este horario"
        footer={
          <Button variant="secondary" onClick={() => setDetailOpen(false)}>Cerrar</Button>
        }
      >
        {detailAsignaciones.length === 0 ? (
          <p className="text-sm text-textMuted">No quedan asignaciones en este horario.</p>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-textMuted">
              Click en el ícono de eliminar para liberar al monitor de su turno.
            </p>
            {detailAsignaciones.map(a => (
              <div key={a.id_asignacion} className="flex items-center justify-between gap-3 p-3 border border-gray-100 rounded-lg">
                <div className="flex items-center gap-3 min-w-0">
                  <UserAvatar userId={a.monitor} name={a.monitor_nombre} size="md" />
                  <div className="min-w-0">
                    <p className="font-medium text-textMain truncate">{a.monitor_nombre}</p>
                    <p className="text-xs text-textMuted">
                      {a.sala_codigo} · {a.dia_semana_display} · {formatTime(a.hora_inicio)}–{formatTime(a.hora_fin)}
                    </p>
                    <p className="text-xs text-textMuted">{a.semestre_label}</p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(a)}
                  disabled={deletingId === a.id_asignacion}
                  title="Eliminar asignación y liberar monitor"
                >
                  <Trash2 className="w-4 h-4 text-danger" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>

      {/* Modal bulk create (admin) */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nueva asignación"
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving || selectedHorarios.length === 0}>
              {saving ? 'Guardando…' : `Asignar ${selectedHorarios.length > 0 ? `(${selectedHorarios.length})` : ''}`}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-textMain">Monitor</span>
            <select
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={form.monitor}
              onChange={e => setForm(f => ({ ...f, monitor: e.target.value }))}
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
            <span className="text-sm font-medium text-textMain">Sala</span>
            <select
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={form.sala}
              onChange={e => onSalaChange(e.target.value)}
            >
              <option value="">Seleccionar sala…</option>
              {salas.map(s => (
                <option key={s.id_sala} value={s.id_sala}>{s.codigo} — {s.nombre}</option>
              ))}
            </select>
          </label>

          {form.sala && (
            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-textMain">Horarios</span>
                {salaHorarios.length > 0 && (
                  <span className="text-xs text-textMuted">
                    {salaHorarios.filter(h => !h.ocupado).length} libres /{' '}
                    {salaHorarios.length} totales
                  </span>
                )}
              </div>
              {loadingHorarios ? (
                <p className="text-sm text-textMuted mt-2">Cargando horarios…</p>
              ) : salaHorarios.length === 0 ? (
                <p className="text-sm text-textMuted mt-2">No hay horarios para esta sala.</p>
              ) : (
                <div className="mt-2 space-y-1 max-h-56 overflow-y-auto">
                  {salaHorarios.map(h => {
                    const isOcupado = h.ocupado === true
                    const isMine = isOcupado && form.monitor !== '' && h.monitor_id === Number(form.monitor)
                    return (
                      <label
                        key={h.id_horario}
                        className={[
                          'flex items-center gap-2 p-2 rounded-lg',
                          isOcupado
                            ? 'bg-gray-50 cursor-not-allowed opacity-70'
                            : 'cursor-pointer hover:bg-gray-50',
                          isMine ? 'border border-amber-200 bg-amber-50' : '',
                        ].join(' ')}
                      >
                        <input
                          type="checkbox"
                          className="rounded border-gray-300 text-primary focus:ring-primary/30"
                          checked={selectedHorarios.includes(h.id_horario)}
                          onChange={() => !isOcupado && toggleHorario(h.id_horario)}
                          disabled={isOcupado}
                        />
                        <span className="text-sm text-textMain flex-1">
                          {h.dia_semana_display || DIAS[h.dia_semana]} ·{' '}
                          {formatTime(h.hora_inicio)}–{formatTime(h.hora_fin)}
                        </span>
                        {isOcupado && (
                          <span
                            className={[
                              'text-xs rounded-full px-2 py-0.5',
                              isMine
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-gray-200 text-textMuted',
                            ].join(' ')}
                            title={`Ocupado por ${h.monitor_email || ''}`}
                          >
                            {isMine ? 'Ya es tuyo' : h.monitor_nombre || 'Ocupado'}
                          </span>
                        )}
                      </label>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
