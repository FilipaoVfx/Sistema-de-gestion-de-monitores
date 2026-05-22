import { api } from './client'
import type { Sala } from '../types/sala.types'

export const salasApi = {
  list:   ()                    => api.get<Sala[]>('/api/salas/'),
  get:    (id: number)          => api.get<Sala>(`/api/salas/${id}/`),
  create: (data: Partial<Sala>) => api.post<Sala>('/api/salas/', data),
  update: (id: number, data: Partial<Sala>) => api.patch<Sala>(`/api/salas/${id}/`, data),
  remove: (id: number)          => api.delete(`/api/salas/${id}/`),
}
