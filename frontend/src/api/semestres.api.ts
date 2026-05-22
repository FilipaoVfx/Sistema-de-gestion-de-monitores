import { api } from './client'

export interface Semestre {
  id_semestre: number
  anio: number
  periodo: number
  activo: boolean
}

export const semestresApi = {
  list:   ()                        => api.get<Semestre[]>('/api/semestres/'),
  get:    (id: number)              => api.get<Semestre>(`/api/semestres/${id}/`),
  create: (data: Partial<Semestre>) => api.post<Semestre>('/api/semestres/', data),
  update: (id: number, data: Partial<Semestre>) => api.patch<Semestre>(`/api/semestres/${id}/`, data),
  remove: (id: number)              => api.delete(`/api/semestres/${id}/`),
}
