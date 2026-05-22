import { useEffect, useState } from 'react'
import { salasApi } from '../api/salas.api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/ui/Toast'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import ErrorMessage from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import { Building2, Plus, Pencil, Trash2 } from 'lucide-react'

interface SalaR { id_sala: number; codigo: string; nombre: string; capacidad: number }

export default function SalasPage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const isAdmin = user?.rol === 'admin'

  const [salas,    setSalas]    = useState<SalaR[]>([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing,  setEditing]  = useState<SalaR | null>(null)
  const [form,     setForm]     = useState({ codigo: '', nombre: '', capacidad: '' })
  const [saving,   setSaving]   = useState(false)

  const load = () => {
    setLoading(true)
    setError(false)
    salasApi.list()
      .then(r => setSalas(r.data as unknown as SalaR[]))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditing(null)
    setForm({ codigo: '', nombre: '', capacidad: '' })
    setModalOpen(true)
  }

  const openEdit = (s: SalaR) => {
    setEditing(s)
    setForm({ codigo: s.codigo, nombre: s.nombre, capacidad: String(s.capacidad) })
    setModalOpen(true)
  }

  const handleSave = async () => {
    if (!form.codigo.trim() || !form.nombre.trim() || !form.capacidad) return
    setSaving(true)
    try {
      const payload = { codigo: form.codigo, nombre: form.nombre, capacidad: Number(form.capacidad) }
      if (editing) {
        await salasApi.update(editing.id_sala, payload as any)
        showToast('Sala actualizada')
      } else {
        await salasApi.create(payload as any)
        showToast('Sala creada')
      }
      setModalOpen(false)
      load()
    } catch {
      showToast('Error al guardar sala', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (s: SalaR) => {
    if (!confirm(`¿Eliminar sala ${s.codigo}?`)) return
    try {
      await salasApi.remove(s.id_sala)
      showToast('Sala eliminada')
      load()
    } catch {
      showToast('No se pudo eliminar la sala', 'error')
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-textMain flex items-center gap-2">
            <Building2 className="w-6 h-6 text-primary" /> Salas
          </h1>
          <p className="text-sm text-textMuted mt-1">Laboratorios y salas de cómputo</p>
        </div>
        {isAdmin && (
          <Button onClick={openCreate}>
            <Plus className="w-4 h-4" /> Nueva sala
          </Button>
        )}
      </header>

      <Card>
        {loading ? <Spinner /> : error ? <ErrorMessage onRetry={load} /> : salas.length === 0 ? (
          <EmptyState
            title="Sin salas"
            description="No hay salas registradas."
            action={isAdmin ? <Button onClick={openCreate}><Plus className="w-4 h-4" /> Nueva sala</Button> : undefined}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wide">Código</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wide">Nombre</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wide">Capacidad</th>
                  {isAdmin && <th className="px-6 py-3 text-right text-xs font-medium text-textMuted uppercase tracking-wide">Acciones</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {salas.map(s => (
                  <tr key={s.id_sala} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-mono font-medium text-textMain">{s.codigo}</td>
                    <td className="px-6 py-3 text-textMain">{s.nombre}</td>
                    <td className="px-6 py-3 text-textMuted">{s.capacidad} puestos</td>
                    {isAdmin && (
                      <td className="px-6 py-3 text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => openEdit(s)}>
                            <Pencil className="w-3.5 h-3.5" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(s)}>
                            <Trash2 className="w-3.5 h-3.5 text-danger" />
                          </Button>
                        </div>
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
        title={editing ? 'Editar sala' : 'Nueva sala'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? 'Guardando…' : 'Guardar'}</Button>
          </>
        }
      >
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-textMain">Código</span>
            <input
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              placeholder="LAB-01"
              value={form.codigo}
              onChange={e => setForm(f => ({ ...f, codigo: e.target.value }))}
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-textMain">Nombre</span>
            <input
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              placeholder="Laboratorio 1"
              value={form.nombre}
              onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-textMain">Capacidad</span>
            <input
              type="number"
              min={1}
              className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              placeholder="30"
              value={form.capacidad}
              onChange={e => setForm(f => ({ ...f, capacidad: e.target.value }))}
            />
          </label>
        </div>
      </Modal>
    </div>
  )
}
