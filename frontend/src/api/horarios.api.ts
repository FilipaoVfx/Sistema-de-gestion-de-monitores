import { api } from './client'

export interface Horario {
  id_horario: number
  sala: number
  dia_semana: number
  dia_semana_display: string
  hora_inicio: string
  hora_fin: string
  /** Info de ocupacion en el semestre activo (la maneja el backend automaticamente). */
  asignacion_id?: number | null
  monitor_id?: number | null
  monitor_nombre?: string | null
  monitor_email?: string | null
  ocupado?: boolean
}

export const horariosApi = {
  /** Lista horarios con info de ocupacion en el semestre activo (auto). */
  list: (salaId?: number) => {
    const params: Record<string, number> = {}
    if (salaId !== undefined) params.sala = salaId
    return api.get<Horario[]>('/api/horarios/', { params })
  },
  get:    (id: number)          => api.get<Horario>(`/api/horarios/${id}/`),
  create: (data: Partial<Horario>) => api.post<Horario>('/api/horarios/', data),
  update: (id: number, data: Partial<Horario>) => api.patch<Horario>(`/api/horarios/${id}/`, data),
  remove: (id: number)          => api.delete(`/api/horarios/${id}/`),
}
