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
import { Monitor as MonitorIcon, Plus, Copy, KeyRound, CheckCheck } from 'lucide-react'

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

  // Modal de exito mostrando la password temporal del monitor recien creado
  const [credentialsModal, setCredentialsModal] = useState<{ email: string; password: string } | null>(null)
  const [copied, setCopied] = useState<'none' | 'email' | 'password' | 'both'>('none')

  const copyToClipboard = async (text: string, label: 'email' | 'password' | 'both') => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(label)
      setTimeout(() => setCopied('none'), 1500)
    } catch {
      showToast('No se pudo copiar al portapapeles', 'error')
    }
  }

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
      const res = await monitoresApi.create(form)
      showToast('Monitor creado')
      setModalOpen(false)
      setForm({ email: '', first_name: '', last_name: '', cedula: '', telefono: '' })
      load()
      if (res.data.temporary_password) {
        setCredentialsModal({ email: res.data.email, password: res.data.temporary_password })
      }
    } catch (e: any) {
      // Extrae detail estructurado del backend para mostrar la causa real
      const status = e?.response?.status
      const data   = e?.response?.data
      let msg = data?.error || 'Error al crear monitor'

      if (status === 403 && data?.detail && typeof data.detail === 'object') {
        // 403 con detalle del rol detectado por el backend
        const d = data.detail
        msg = `${data.error || 'Acceso denegado'} · Tu sesion es ${d.usuario || '?'} con rol "${d.rol_detectado || '?'}". ${d.hint || ''}`
      } else if (data?.detail) {
        // Otros 4xx con detail estructurado
        const d = data.detail
        if (typeof d === 'string') {
          msg = d
        } else if (Array.isArray(d)) {
          msg = d.join(' · ')
        } else if (typeof d === 'object') {
          const parts: string[] = []
          for (const [field, value] of Object.entries(d)) {
            const txt = Array.isArray(value) ? value.join(' · ') : String(value)
            parts.push(`${field}: ${txt}`)
          }
          msg = parts.join(' · ')
        }
      }
      showToast(msg, 'error')
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

      {/* Modal de credenciales temporales (se muestra una sola vez al crear) */}
      <Modal
        open={credentialsModal !== null}
        onClose={() => setCredentialsModal(null)}
        title="Monitor creado — credenciales temporales"
        footer={
          <Button
            onClick={() =>
              credentialsModal && copyToClipboard(
                `Email: ${credentialsModal.email}\nPassword: ${credentialsModal.password}`,
                'both',
              )
            }
          >
            {copied === 'both' ? <><CheckCheck className="w-4 h-4" /> Copiado</> : <><Copy className="w-4 h-4" /> Copiar ambos</>}
          </Button>
        }
      >
        {credentialsModal && (
          <div className="space-y-4">
            <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-lg p-3">
              <KeyRound className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <p className="text-sm text-amber-800 leading-relaxed">
                Guarda esta contraseña — solo se muestra una vez. Entrégala al monitor por
                un canal seguro (WhatsApp, Slack, etc). El monitor podrá cambiarla luego.
              </p>
            </div>

            <div className="space-y-2">
              <label className="block">
                <span className="text-xs font-medium text-textMuted uppercase tracking-wide">Email</span>
                <div className="mt-1 flex items-center gap-2">
                  <code className="flex-1 font-mono text-sm bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-textMain">
                    {credentialsModal.email}
                  </code>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => copyToClipboard(credentialsModal.email, 'email')}
                    title="Copiar email"
                  >
                    {copied === 'email' ? <CheckCheck className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </label>

              <label className="block">
                <span className="text-xs font-medium text-textMuted uppercase tracking-wide">Password temporal</span>
                <div className="mt-1 flex items-center gap-2">
                  <code className="flex-1 font-mono text-sm bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-textMain select-all">
                    {credentialsModal.password}
                  </code>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => copyToClipboard(credentialsModal.password, 'password')}
                    title="Copiar password"
                  >
                    {copied === 'password' ? <CheckCheck className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </label>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
