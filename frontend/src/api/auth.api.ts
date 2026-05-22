import { api, postForm } from './client'

export interface SessionUser {
  email: string
  nombre?: string
  rol?: 'administrador' | 'monitor'
  authenticated: boolean
}

export const authApi = {
  /**
   * POST /usuarios/login/  (form-encoded + CSRF)
   * El backend Django+HTMX responde con redirect 302 + cookie sessionid si OK,
   * o vuelve a renderizar el formulario con error si falla.
   */
  login: (email: string, password: string) =>
    postForm('/usuarios/login/', { email, password }),

  /**
   * POST /usuarios/logout/  (solo POST, requiere CSRF)
   */
  logout: () => postForm('/usuarios/logout/', {}),

  /**
   * GET / para detectar si la sesión sigue activa.
   * - Si NO hay sesión: backend redirige a /usuarios/login/ → status 200 con HTML del login
   * - Si HAY sesión: backend redirige a /dashboard/ (404 actualmente) o a una página interna
   *
   * Como no hay endpoint JSON /api/auth/me/ todavía, hacemos best-effort:
   * intentamos /salas/ (protegido) — si responde 200 estamos logueados.
   */
  me: async (): Promise<SessionUser | null> => {
    try {
      const res = await api.get('/salas/', { maxRedirects: 0, validateStatus: () => true })
      // Si redirigió a /accounts/login/ → no hay sesión
      const redirected =
        res.status === 302 ||
        (typeof res.data === 'string' && res.data.includes('accounts/login'))
      if (redirected) return null
      return { email: 'session', authenticated: true }
    } catch {
      return null
    }
  },
}
