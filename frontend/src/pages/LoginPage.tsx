import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Monitor, Eye, EyeOff } from 'lucide-react'

export default function LoginPage() {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [showPwd,  setShowPwd]  = useState(false)
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const { login } = useAuth()
  const navigate  = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/salas')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Credenciales incorrectas.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bgPage flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-sidebar rounded-2xl mb-4">
            <Monitor className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-textMain">SGMSC</h1>
          <p className="text-textMuted text-sm mt-1">Sistema de Gestión de Monitores de Sala</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
          <h2 className="text-lg font-semibold text-textMain mb-6">Iniciar sesión</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-textMain mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="username"
                className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition"
                placeholder="usuario@dominio.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-textMain mb-1.5">Contraseña</label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="w-full px-3 py-2.5 pr-10 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition"
                  placeholder="Contraseña"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(s => !s)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-textMuted hover:text-textMain transition"
                  tabIndex={-1}
                >
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-sm text-danger bg-red-50 rounded-lg px-3 py-2">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
            >
              {loading ? 'Ingresando…' : 'Entrar'}
            </button>
          </form>
        </div>
        <p className="text-center text-xs text-textMuted mt-4">
          Backend conectado a <span className="font-mono">sgmsc-web.onrender.com</span>
        </p>
      </div>
    </div>
  )
}
