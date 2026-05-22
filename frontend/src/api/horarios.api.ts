import { api } from './client'

export interface Horario {
  id_horario: number
  sala: number
  dia_semana: number
  dia_semana_display: string
  hora_inicio: string
  hora_fin: string
}

export const horariosApi = {
  list:   (salaId?: number) =>
    api.get<Horario[]>('/api/horarios/', { params: salaId ? { sala: salaId } : {} }),
  get:    (id: number)          => api.get<Horario>(`/api/horarios/${id}/`),
  create: (data: Partial<Horario>) => api.post<Horario>('/api/horarios/', data),
  update: (id: number, data: Partial<Horario>) => api.patch<Horario>(`/api/horarios/${id}/`, data),
  remove: (id: number)          => api.delete(`/api/horarios/${id}/`),
}
