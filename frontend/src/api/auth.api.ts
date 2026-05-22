import { api } from './client'

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

export const authApi = {
  /**
   * POST /api/auth/login/  → { token, user }
   */
  login: async (email: string, password: string): Promise<SessionUser> => {
    const res = await api.post<{ token: string; user: SessionUser }>(
      '/api/auth/login/',
      { email, password },
    )
    localStorage.setItem('auth_token', res.data.token)
    return { ...res.data.user, authenticated: true }
  },

  /**
   * POST /api/auth/logout/  → 204
   */
  logout: async (): Promise<void> => {
    try {
      await api.post('/api/auth/logout/')
    } finally {
      localStorage.removeItem('auth_token')
    }
  },

  /**
   * GET /api/auth/me/  → user info
   */
  me: async (): Promise<SessionUser | null> => {
    const token = localStorage.getItem('auth_token')
    if (!token) return null
    try {
      const res = await api.get<SessionUser>('/api/auth/me/')
      return { ...res.data, authenticated: true }
    } catch {
      localStorage.removeItem('auth_token')
      return null
    }
  },
}
