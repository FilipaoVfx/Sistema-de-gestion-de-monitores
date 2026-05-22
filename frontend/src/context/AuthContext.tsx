import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { authApi, type SessionUser } from '../api/auth.api'

interface AuthContextValue {
  user:    SessionUser | null
  loading: boolean
  login:   (email: string, password: string) => Promise<void>
  logout:  () => Promise<void>
}

const AuthContext = createContext<AuthContextValue>({
  user: null, loading: true,
  login: async () => {}, logout: async () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,    setUser]    = useState<SessionUser | null>(null)
  const [loading, setLoading] = useState(true)

  // Al arrancar: detecta si hay cookie de sesión válida
  useEffect(() => {
    authApi.me()
      .then(u => setUser(u))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    await authApi.login(email, password)
    // Si la cookie sessionid se setea correctamente, asumimos sesión activa
    const u = await authApi.me()
    if (!u) throw new Error('Credenciales inválidas')
    setUser(u)
  }

  const logout = async () => {
    await authApi.logout().catch(() => {})
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
