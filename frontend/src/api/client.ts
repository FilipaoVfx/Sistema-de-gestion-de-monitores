import axios, { type AxiosRequestConfig } from 'axios'

/**
 * Backend: Django + DRF JSON API en https://sistema-de-gestion-de-monitores.onrender.com
 *
 * Estrategia:
 *  - En desarrollo: apunta directo al backend via VITE_API_URL
 *  - En producción (Vercel): VITE_API_URL = "/_api" → pasa por Vercel proxy (ver vercel.json)
 *
 * Auth: JWT (djangorestframework-simplejwt)
 *  - Se guardan access + refresh en localStorage (auth_access, auth_refresh)
 *  - Se inyecta `Authorization: Bearer <access>` en cada request
 *  - Si access expira (401), se intenta refresh automaticamente UNA vez
 *    y se reintenta el request original con el nuevo access
 */
const BASE_URL =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.PROD ? '/_api' : 'https://sistema-de-gestion-de-monitores.onrender.com')

export const TOKEN_ACCESS_KEY  = 'auth_access'
export const TOKEN_REFRESH_KEY = 'auth_refresh'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Inyecta el access token en cada request si existe
api.interceptors.request.use((config) => {
  const access = localStorage.getItem(TOKEN_ACCESS_KEY)
  if (access) {
    config.headers['Authorization'] = `Bearer ${access}`
  }
  return config
})

// Cliente "raw" sin interceptors — se usa para el refresh y evitar loops.
const rawApi = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Manejo de refresh con cola: si llegan varios 401 a la vez, solo se hace
// UN refresh y el resto de requests espera el resultado.
let refreshPromise: Promise<string | null> | null = null

// Para evitar múltiples redirects si varios requests fallan en simultáneo
let redirectingToLogin = false

/** Limpia los tokens y redirige a login. Idempotente: solo redirige una vez. */
function forceReauth(): void {
  localStorage.removeItem(TOKEN_ACCESS_KEY)
  localStorage.removeItem(TOKEN_REFRESH_KEY)
  if (redirectingToLogin) return
  if (typeof window === 'undefined') return
  // Si ya estamos en login, no redirigir
  if (window.location.pathname.includes('/usuarios/login')) return
  redirectingToLogin = true
  window.location.assign('/usuarios/login')
}

async function doRefresh(): Promise<string | null> {
  const refresh = localStorage.getItem(TOKEN_REFRESH_KEY)
  if (!refresh) return null
  try {
    const r = await rawApi.post<{ access: string; refresh?: string }>(
      '/api/auth/refresh/',
      { refresh },
    )
    const newAccess = r.data.access
    localStorage.setItem(TOKEN_ACCESS_KEY, newAccess)
    // Si el backend rota el refresh, guardamos el nuevo. Ver SIMPLE_JWT.ROTATE_REFRESH_TOKENS
    if (r.data.refresh) {
      localStorage.setItem(TOKEN_REFRESH_KEY, r.data.refresh)
    }
    return newAccess
  } catch {
    return null
  }
}

// Desempaqueta respuestas paginadas de DRF ({count, next, previous, results: []})
// y maneja refresh automatico en 401.
api.interceptors.response.use(
  (res) => {
    const d = res.data
    if (
      d && typeof d === 'object' && !Array.isArray(d)
      && Array.isArray(d.results) && typeof d.count === 'number'
    ) {
      res.data = d.results
    }
    return res
  },
  async (err) => {
    const original = err.config as AxiosRequestConfig & { _retry?: boolean }
    const status = err.response?.status

    // 401 + no es un retry previo + no es el endpoint de login/refresh
    const isAuthEndpoint = original?.url?.includes('/api/auth/login')
                         || original?.url?.includes('/api/auth/refresh')

    if (status === 401 && !original?._retry && !isAuthEndpoint) {
      // Lock con promesa compartida para evitar refresh paralelos
      if (!refreshPromise) {
        refreshPromise = doRefresh().finally(() => { refreshPromise = null })
      }
      const newAccess = await refreshPromise
      if (newAccess && original) {
        original._retry = true
        original.headers = { ...(original.headers || {}), Authorization: `Bearer ${newAccess}` }
        return api.request(original)
      }
      // Refresh fallo (refresh expirado, blacklisted, o sin refresh en localStorage):
      // forzamos re-login para evitar que el usuario quede atascado en la app
      // con todos los requests dando 401.
      forceReauth()
    }

    return Promise.reject(err)
  },
)
