import axios from 'axios'

/**
 * Backend: Django + DRF JSON API en https://sistema-de-gestion-de-monitores.onrender.com
 *
 * Estrategia:
 *  - En desarrollo: apunta directo al backend via VITE_API_URL
 *  - En producción (Vercel): VITE_API_URL = "/_api" → pasa por Vercel proxy (ver vercel.json)
 *
 * Auth: Token Authentication (DRF)
 *  - Token se guarda en localStorage
 *  - Se inyecta como "Authorization: Token <key>" en cada request
 */
const BASE_URL =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.PROD ? '/_api' : 'https://sistema-de-gestion-de-monitores.onrender.com')

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Inyecta el token en cada request si existe
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers['Authorization'] = `Token ${token}`
  }
  return config
})

// Limpia el token si el servidor responde 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('auth_token')
    }
    return Promise.reject(err)
  },
)
