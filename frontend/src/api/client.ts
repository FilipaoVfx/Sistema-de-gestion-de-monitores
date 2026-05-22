import axios from 'axios'

/**
 * Backend: Django + HTMX server-rendered en https://sgmsc-web.onrender.com
 *
 * Estrategia:
 *  - En desarrollo: VITE_API_URL apunta directo al backend (con CORS si está habilitado)
 *  - En producción (Vercel): VITE_API_URL = "" → todas las llamadas pasan por Vercel rewrites
 *    (ver vercel.json) que proxean a sgmsc-web.onrender.com, evitando CORS.
 *
 * IMPORTANTE: este backend usa autenticación por cookie de sesión + CSRF (no Token).
 * Por eso withCredentials = true y leemos el csrftoken de las cookies.
 */
/**
 * En producción (Vercel) usamos el prefijo /_api que se rewrite a sgmsc-web.onrender.com.
 * En desarrollo apuntamos directo al backend (requiere CORS habilitado en Django).
 */
const BASE_URL =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.PROD ? '/_api' : 'https://sgmsc-web.onrender.com')

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Accept': 'application/json, text/html;q=0.9, */*;q=0.8' },
  withCredentials: true, // necesario para enviar/recibir cookie de sesión
})

// Lee la cookie csrftoken (Django la setea tras visitar cualquier vista)
function getCsrfToken(): string | null {
  const match = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[2]) : null
}

// Inyecta X-CSRFToken en métodos no-safe
api.interceptors.request.use((config) => {
  const method = (config.method ?? 'get').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    const token = getCsrfToken()
    if (token) config.headers['X-CSRFToken'] = token
  }
  return config
})

// Maneja sesiones expiradas
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 || err.response?.status === 403) {
      // Sesión inválida — la app redirigirá a /login desde el AuthContext
    }
    return Promise.reject(err)
  },
)

/**
 * Helper: POST tipo formulario (application/x-www-form-urlencoded).
 * Django con HTMX espera form-encoded, no JSON.
 */
export async function postForm<T = unknown>(
  url: string,
  data: Record<string, string | number | boolean>,
) {
  // Hacemos un GET previo para asegurar que tenemos cookie csrftoken
  if (!getCsrfToken()) {
    try { await api.get('/usuarios/login/') } catch {}
  }
  const params = new URLSearchParams()
  Object.entries(data).forEach(([k, v]) => params.append(k, String(v)))

  return api.post<T>(url, params.toString(), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}
