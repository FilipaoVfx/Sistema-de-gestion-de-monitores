import { useEffect, useState } from 'react'
import { asignacionesApi, type Asignacion } from '../api/asignaciones.api'
import { monitoresApi } from '../api/monitores.api'
import type { SessionUser } from '../api/auth.api'
import { salasApi } from '../api/salas.api'
import { horariosApi, type Horario } from '../api/horarios.api'
import { semestresApi, type Semestre } from '../api/semestres.api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/ui/Toast'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import ErrorMessage from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import { CalendarCheck, Plus, Trash2 } from 'lucide-react'
import { formatTime } from '../utils/formatDate'

interface SalaR { id_sala: number; codigo: string; nombre: string }

export default function AsignacionesPage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const isAdmin = user?.rol === 'admin'

  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [semestres,    setSemestres]    = useState<Semestre[]>([])
  const [filterSem,    setFilterSem]   = useState<number | ''>('')
  const [loading,      setLoading]     = useState(true)
  const [error,        setError]       = useState(false)

  // Bulk modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [monitores, setMonitores] = useState<SessionUser[]>([])
  const [salas,     setSalas]     = useState<SalaR[]>([])
  const [salaHorarios, setSalaHorarios] = useState<Horario[]>([])
  const [form, setForm] = useState({ monitor: '', semestre: '', sala: '' })
  const [selectedHorarios, setSelectedHorarios] = useState<number[]>([])
  const [loadingHorarios, setLoadingHorarios] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    setError(false)
    const params: Record<string, number> = {}
    if (filterSem !== '') params.semestre = filterSem
    if (!isAdmin && user?.id) params.monitor = user.id
    Promise.all([
      asignacionesApi.list(params),
      semestresApi.list(),
    ])
      .then(([a, s]) => { setAsignaciones(a.data); setSemestres(s.data) })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterSem])

  const openModal = async () => {
    setForm({ monitor: '', semestre: '', sala: '' })
    setSelectedHorarios([])
    setSalaHorarios([])
    setModalOpen(true)
    try {
      const [m, s] = await Promise.all([monitoresApi.list(), salasApi.list()])
      setMonitores(m.data.filter(u => u.rol === 'monitor'))
      setSalas(s.data as unknown as SalaR[])
    } catch {
      showToast('Error al cargar datos del formulario', 'error')
    }
  }

  const onSalaChange = async (salaId: string) => {
    setForm(f => ({ ...f, sala: salaId }))
    setSelectedHorarios([])
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

  const toggleHorario = (id: number) => {
    setSelectedHorarios(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const handleSave = async () => {
    if (!form.monitor || !form.semestre || !form.sala || selectedHorarios.length === 0) return
    setSaving(true)
    try {
      const res = await asignacionesApi.bulk({
        monitor:  Number(form.monitor),
        semestre: Number(form.semestre),
        sala:     Number(form.sala),
        horarios: selectedHorarios.map(id => `h:${id}`),
      })
      showToast(`${res.data.creadas} asignación(es) creada(s)`)
      setModalOpen(false)
      load()
    } catch {
      showToast('Error al crear asignaciones', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (a: Asignacion) => {
    if (!confirm('¿Eliminar esta asignación?')) return
    try {
      await asignacionesApi.remove(a.id_asignacion)
      showToast('Asignación eliminada')
      load()
    } catch {
      showToast('No se pudo eliminar la asignación', 'error')
    }
  }

  const semLabel = (s: Semestre) => `${s.anio}-${s.periodo}${s.activo ? ' (activo)' : ''}`

  const DIAS: Record<number, string> = {
    1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb',
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-textMain flex items-center gap-2">
            <CalendarCheck className="w-6 h-6 text-primary" /> Asignaciones
          </h1>
          <p className="text-sm text-textMuted mt-1">
            {isAdmin ? 'Turnos semanales de monitores en salas' : 'Tus turnos semanales asignados'}
          </p>
        </div>
        {isAdmin && (
          <Button onClick={openModal}>
            <Plus className="w-4 h-4" /> Nueva asignación
          </Button>
        )}
      </header>

      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-textMain">Semestre:</label>
        <select
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          value={filterSem}
          onChange={e => setFilterSem(e.target.value !== '' ? Number(e.target.value) : '')}
        >
          <option value="">Todos</option>
          {semestres.map(s => (
            <option key={s.id_semestre} value={s.id_semestre}>{semLabel(s)}</option>
          ))}
        </select>
      </div>

      <Card>
        {loading ? <Spinner /> : error ? <ErrorMessage onRetry={load} /> : asignaciones.length === 0 ? (
          <EmptyState
            title="Sin asignaciones"
            description="No hay asignaciones para este filtro."
            action={isAdmin ? <Button onClick={openModal}><Plus className="w-4 h-4" /> Nueva asignación</Button> : undefined}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Monitor', 'Sala', 'Día', 'Horario', 'Semestre', ...(isAdmin ? [''] : [])].map((h, i) => (
                    <th key={i} className={`px-6 py-3 ${i === 5 ? 'text-right' : 'text-left'} text-xs font-medium text-textMuted uppercase tracking-wide`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {asignaciones.map(a => (
                  <tr key={a.id_asignacion} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-medium text-textMain">{a.monitor_nombre}</td>
                    <td className="px-6 py-3 text-textMuted font-mono">{a.sala_codigo}</td>
                    <td className="px-6 py-3 text-textMuted">{a.dia_semana_display || DIAS[a.dia_semana]}</td>
                    <td className="px-6 py-3 text-textMuted">{formatTime(a.hora_inicio)}–{formatTime(a.hora_fin)}</td>
                    <td className="px-6 py-3 text-textMuted">{a.semestre_label}</td>
                    {isAdmin && (
                      <td className="px-6 py-3 text-right">
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(a)}>
                          <Trash2 className="w-3.5 h-3.5 text-danger" />
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Bulk create modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nueva asignación"
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button
              onClick={handleSave}
              disabled={saving || selectedHorarios.length === 0}
            >
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
            <span className="text-sm font-medium text-textMain">Semestre</span>
            <select
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={form.semestre}
              onChange={e => setForm(f => ({ ...f, semestre: e.target.value }))}
            >
              <option value="">Seleccionar semestre…</option>
              {semestres.map(s => (
                <option key={s.id_semestre} value={s.id_semestre}>{semLabel(s)}</option>
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
              <span className="text-sm font-medium text-textMain">Horarios disponibles</span>
              {loadingHorarios ? (
                <p className="text-sm text-textMuted mt-2">Cargando horarios…</p>
              ) : salaHorarios.length === 0 ? (
                <p className="text-sm text-textMuted mt-2">No hay horarios para esta sala.</p>
              ) : (
                <div className="mt-2 space-y-1 max-h-48 overflow-y-auto">
                  {salaHorarios.map(h => (
                    <label key={h.id_horario} className="flex items-center gap-2 cursor-pointer p-2 rounded-lg hover:bg-gray-50">
                      <input
                        type="checkbox"
                        className="rounded border-gray-300 text-primary focus:ring-primary/30"
                        checked={selectedHorarios.includes(h.id_horario)}
                        onChange={() => toggleHorario(h.id_horario)}
                      />
                      <span className="text-sm text-textMain">
                        {h.dia_semana_display || DIAS[h.dia_semana]} · {formatTime(h.hora_inicio)}–{formatTime(h.hora_fin)}
                      </span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
