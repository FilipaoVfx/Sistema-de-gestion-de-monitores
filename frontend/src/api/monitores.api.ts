import { api } from './client'
import type { SessionUser } from './auth.api'

export interface CrearMonitorData {
  email: string
  first_name: string
  last_name: string
  cedula: string
  telefono?: string
  /** Opcional: si se omite, el backend genera una password temporal aleatoria. */
  password?: string
}

/** Respuesta de POST /api/usuarios/monitores/  →  user + password temporal */
export type CrearMonitorResponse = SessionUser & {
  temporary_password?: string
}

export const monitoresApi = {
  /** GET /api/usuarios/ → lista de usuarios */
  list: () => api.get<SessionUser[]>('/api/usuarios/'),

  /** GET /api/usuarios/{id}/ */
  get: (id: number) => api.get<SessionUser>(`/api/usuarios/${id}/`),

  /**
   * POST /api/usuarios/monitores/  →  crea monitor
   *
   * El backend genera una password temporal aleatoria (a menos que `data.password`
   * sea provisto) y la retorna en `temporary_password` para que el admin se la
   * entregue al monitor por canal seguro.
   */
  create: (data: CrearMonitorData) =>
    api.post<CrearMonitorResponse>('/api/usuarios/monitores/', data),
}
