import { useEffect, useState } from 'react'
import { monitoresApi, type CrearMonitorData } from '../api/monitores.api'
import type { SessionUser } from '../api/auth.api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/ui/Toast'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import ErrorMessage from '../components/ui/ErrorMessage'
import EmptyState from '../components/ui/EmptyState'
import Badge from '../components/ui/Badge'
import { Monitor as MonitorIcon, Plus } from 'lucide-react'

export default function MonitoresPage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const isAdmin = user?.rol === 'admin'

  const [monitores, setMonitores] = useState<SessionUser[]>([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form,      setForm]      = useState<CrearMonitorData>({
    email: '', first_name: '', last_name: '', cedula: '', telefono: '',
  })
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    setError(false)
    monitoresApi.list()
      .then(r => setMonitores(r.data.filter(u => u.rol === 'monitor')))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSave = async () => {
    if (!form.email || !form.first_name || !form.last_name || !form.cedula) return
    setSaving(true)
    try {
      await monitoresApi.create(form)
      showToast('Monitor creado')
      setModalOpen(false)
      setForm({ email: '', first_name: '', last_name: '', cedula: '', telefono: '' })
      load()
    } catch {
      showToast('Error al crear monitor', 'error')
    } finally {
      setSaving(false)
    }
  }

  const displayName = (m: SessionUser) =>
    [m.first_name, m.last_name].filter(Boolean).join(' ') || m.email

  const fields: [keyof CrearMonitorData, string, string, string][] = [
    ['email',      'Correo electrónico', 'email', 'juan@sgmsc.edu.ec'],
    ['first_name', 'Nombre',             'text',  'Juan'],
    ['last_name',  'Apellido',           'text',  'Rodríguez'],
    ['cedula',     'Cédula',             'text',  '1722345678'],
    ['telefono',   'Teléfono (opcional)','tel',   '+593-999123456'],
  ]

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-textMain flex items-center gap-2">
            <MonitorIcon className="w-6 h-6 text-primary" /> Monitores
          </h1>
          <p className="text-sm text-textMuted mt-1">Usuarios con rol monitor registrados</p>
        </div>
        {isAdmin && (
          <Button onClick={() => setModalOpen(true)}>
            <Plus className="w-4 h-4" /> Nuevo monitor
          </Button>
        )}
      </header>

      <Card>
        {loading ? <Spinner /> : error ? <ErrorMessage onRetry={load} /> : monitores.length === 0 ? (
          <EmptyState title="Sin monitores" description="No hay monitores registrados." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {['Nombre', 'Correo', 'Cédula', 'Teléfono', 'Estado'].map(h => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-medium text-textMuted uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {monitores.map(m => (
                  <tr key={m.id} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-medium text-textMain">{displayName(m)}</td>
                    <td className="px-6 py-3 text-textMuted">{m.email}</td>
                    <td className="px-6 py-3 text-textMuted font-mono">{m.cedula}</td>
                    <td className="px-6 py-3 text-textMuted">{m.telefono || '—'}</td>
                    <td className="px-6 py-3">
                      <Badge variant="green">Activo</Badge>
                    </td>
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
        title="Nuevo monitor"
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? 'Guardando…' : 'Crear monitor'}</Button>
          </>
        }
      >
        <div className="space-y-4">
          {fields.map(([field, label, type, placeholder]) => (
            <label key={field} className="block">
              <span className="text-sm font-medium text-textMain">{label}</span>
              <input
                type={type}
                className="mt-1 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                placeholder={placeholder}
                value={form[field] ?? ''}
                onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
              />
            </label>
          ))}
        </div>
      </Modal>
    </div>
  )
}
