import { api } from './client'
import type { SessionUser } from './auth.api'

export interface CrearMonitorData {
  email: string
  first_name: string
  last_name: string
  cedula: string
  telefono?: string
}

export const monitoresApi = {
  /** GET /api/usuarios/ → lista de usuarios */
  list: () => api.get<SessionUser[]>('/api/usuarios/'),

  /** GET /api/usuarios/{id}/ */
  get: (id: number) => api.get<SessionUser>(`/api/usuarios/${id}/`),

  /** POST /api/usuarios/monitores/ → crea monitor y envía correo de activación */
  create: (data: CrearMonitorData) =>
    api.post<SessionUser>('/api/usuarios/monitores/', data),
}
