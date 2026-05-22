import { api } from './client'

export interface Asignacion {
  id_asignacion: number
  monitor: number
  monitor_email: string
  monitor_nombre: string
  horario: number
  semestre: number
  semestre_label: string
  fecha_creacion: string
  sala_codigo: string
  sala_nombre: string
  id_sala: number
  dia_semana: number
  dia_semana_display: string
  hora_inicio: string
  hora_fin: string
}

export interface CrearAsignacionesBulkData {
  monitor: number
  semestre: number
  sala: number
  horarios: string[]  // tokens: "h:<id>" o "n:<dia>|<HH:MM>|<HH:MM>"
}

export const asignacionesApi = {
  list: (params?: { semestre?: number; sala?: number; monitor?: number }) =>
    api.get<Asignacion[]>('/api/asignaciones/', { params }),

  get: (id: number) => api.get<Asignacion>(`/api/asignaciones/${id}/`),

  /** Crea asignaciones en bulk por tokens de horario */
  bulk: (data: CrearAsignacionesBulkData) =>
    api.post<{ creadas: number }>('/api/asignaciones/bulk/', data),

  remove: (id: number) => api.delete(`/api/asignaciones/${id}/`),
}
