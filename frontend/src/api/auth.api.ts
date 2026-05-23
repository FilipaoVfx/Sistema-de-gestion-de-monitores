import { api, TOKEN_ACCESS_KEY, TOKEN_REFRESH_KEY } from './client'

export interface SessionUser {
  id: number
  email: string
  first_name: string
  last_name: string
  cedula: string
  telefono: string
  rol: 'admin' | 'monitor'
  authenticated: boolean
}

interface LoginResponse {
  access:  string
  refresh: string
  user:    SessionUser
}

export const authApi = {
  /**
   * POST /api/auth/login/  →  { access, refresh, user }
   * Guarda ambos tokens en localStorage.
   */
  login: async (email: string, password: string): Promise<SessionUser> => {
    const res = await api.post<LoginResponse>('/api/auth/login/', { email, password })
    localStorage.setItem(TOKEN_ACCESS_KEY,  res.data.access)
    localStorage.setItem(TOKEN_REFRESH_KEY, res.data.refresh)
    return { ...res.data.user, authenticated: true }
  },

  /**
   * POST /api/auth/logout/  →  204
   * Manda el refresh en el body para que el backend lo blacklistee.
   */
  logout: async (): Promise<void> => {
    const refresh = localStorage.getItem(TOKEN_REFRESH_KEY)
    try {
      await api.post('/api/auth/logout/', refresh ? { refresh } : {})
    } finally {
      localStorage.removeItem(TOKEN_ACCESS_KEY)
      localStorage.removeItem(TOKEN_REFRESH_KEY)
    }
  },

  /**
   * GET /api/auth/me/  →  user info
   * Si el access esta expirado, el interceptor de client.ts intenta
   * refresh automatico. Si el refresh tambien falla, limpia tokens.
   */
  me: async (): Promise<SessionUser | null> => {
    if (!localStorage.getItem(TOKEN_ACCESS_KEY)) return null
    try {
      const res = await api.get<SessionUser>('/api/auth/me/')
      return { ...res.data, authenticated: true }
    } catch {
      // Si llegamos aqui es porque ni el access ni el refresh sirven.
      // client.ts ya limpio los tokens en doRefresh() fail.
      return null
    }
  },
}
