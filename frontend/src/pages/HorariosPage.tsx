import { useEffect, useState } from 'react'
import { horariosApi, type Horario } from '../api/horarios.api'
import { salasApi } from '../api/salas.api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/ui/Toast'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import ErrorMessage from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import { Clock, Plus, Trash2 } from 'lucide-react'

interface SalaR { id_sala: number; codigo: string; nombre: string }

const DIAS: Record<number, string> = {
  1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado',
}

export default function HorariosPage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const isAdmin = user?.rol === 'admin'

  const [horarios,   setHorarios]   = useState<Horario[]>([])
  const [salas,      setSalas]      = useState<SalaR[]>([])
  const [filterSala, setFilterSala] = useState<number | ''>('')
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(false)
  const [modalOpen,  setModalOpen]  = useState(false)
  const [form,       setForm]       = useState({ sala: '', dia_semana: '1', hora_inicio: '08:00', hora_fin: '10:00' })
  const [saving,     setSaving]     = useState(false)

  const load = () => {
    setLoading(true)
    setError(false)
    Promise.all([
      horariosApi.list(filterSala !== '' ? filterSala : undefined),
      salasApi.list(),
    ])
      .then(([h, s]) => { setHorarios(h.data); setSalas(s.data as unknown as SalaR[]) })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterSala])

  const handleSave = async () => {
    if (!form.sala) return
    setSaving(true)
    try {
      await horariosApi.create({
        sala: Number(form.sala),
        dia_semana: Number(form.dia_semana),
        hora_inicio: form.hora_inicio,
        hora_fin: form.hora_fin,
      })
      showToast('Horario creado')
      setModalOpen(false)
      load()
    } catch {
      showToast('Error al crear horario', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (h: Horario) => {
    if (!confirm('¿Eliminar este horario?')) return
    try {
      await horariosApi.remove(h.id_horario)
      showToast('Horario eliminado')
      load()
    } catch {
      showToast('No se pudo eliminar el horario', 'error')
    }
  }

  const salaLabel = (id: number) => salas.find(s => s.id_sala === id)?.codigo ?? String(id)

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-textMain flex items-center gap-2">
            <Clock className="w-6 h-6 text-primary" /> Horarios
          </h1>
          <p className="text-sm text-textMuted mt-1">Bloques horarios disponibles por sala</p>
        </div>
        {isAdmin && (
          <Button onClick={() => setModalOpen(true)}>
            <Plus className="w-4 h-4" /> Nuevo horario
          </Button>
        )}
      </header>

      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-textMain">Filtrar por sala:</label>
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

      <Card>
        {loading ? <Spinner /> : error ? <ErrorMessage onRetry={load} /> : horarios.length === 0 ? (
          <EmptyState title="Sin horarios" description="No hay horarios registrados para esta selección." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Sala', 'Día', 'Inicio', 'Fin', ...(isAdmin ? [''] : [])].map((h, i) => (
                    <th key={i} className={`px-6 py-3 ${i === 4 ? 'text-right' : 'text-left'} text-xs font-medium text-textMuted uppercase tracking-wide`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {horarios.map(h => (
                  <tr key={h.id_horario} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-mono font-medium text-textMain">{salaLabel(h.sala)}</td>
                    <td className="px-6 py-3 text-textMain">{h.dia_semana_display || DIAS[h.dia_semana]}</td>
                    <td className="px-6 py-3 text-textMuted">{h.hora_inicio?.slice(0, 5)}</td>
                    <td className="px-6 py-3 text-textMuted">{h.hora_fin?.slice(0, 5)}</td>
                    {isAdmin && (
                      <td className="px-6 py-3 text-right">
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(h)}>
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

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nuevo horario"
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? 'Guardando…' : 'Crear'}</Button>
          </>
        }
      >
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-textMain">Sala</span>
            <select
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={form.sala}
              onChange={e => setForm(f => ({ ...f, sala: e.target.value }))}
            >
              <option value="">Seleccionar sala…</option>
              {salas.map(s => (
                <option key={s.id_sala} value={s.id_sala}>{s.codigo} — {s.nombre}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium text-textMain">Día</span>
            <select
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              value={form.dia_semana}
              onChange={e => setForm(f => ({ ...f, dia_semana: e.target.value }))}
            >
              {Object.entries(DIAS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-sm font-medium text-textMain">Hora inicio</span>
              <input
                type="time"
                className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                value={form.hora_inicio}
                onChange={e => setForm(f => ({ ...f, hora_inicio: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-textMain">Hora fin</span>
              <input
                type="time"
                className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                value={form.hora_fin}
                onChange={e => setForm(f => ({ ...f, hora_fin: e.target.value }))}
              />
            </label>
          </div>
        </div>
      </Modal>
    </div>
  )
}
