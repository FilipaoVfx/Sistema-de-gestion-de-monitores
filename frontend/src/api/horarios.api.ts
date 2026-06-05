import { api } from './client'

export interface Horario {
  id_horario: number
  sala: number
  dia_semana: number
  dia_semana_display: string
  hora_inicio: string
  hora_fin: string
  /** Campos opcionales — solo presentes cuando GET /api/horarios incluye ?semestre=X.
   *  Indican quien tiene este horario asignado en ese semestre, si aplica. */
  asignacion_id?: number | null
  monitor_id?: number | null
  monitor_nombre?: string | null
  monitor_email?: string | null
  ocupado?: boolean
}

export const horariosApi = {
  /** Lista horarios. Si pasas `semestre`, cada horario incluye info de
   *  ocupacion (monitor_*, ocupado, asignacion_id) en ese semestre. */
  list: (salaId?: number, semestreId?: number) => {
    const params: Record<string, number> = {}
    if (salaId !== undefined)     params.sala     = salaId
    if (semestreId !== undefined) params.semestre = semestreId
    return api.get<Horario[]>('/api/horarios/', { params })
  },
  get:    (id: number)          => api.get<Horario>(`/api/horarios/${id}/`),
  create: (data: Partial<Horario>) => api.post<Horario>('/api/horarios/', data),
  update: (id: number, data: Partial<Horario>) => api.patch<Horario>(`/api/horarios/${id}/`, data),
  remove: (id: number)          => api.delete(`/api/horarios/${id}/`),
}
