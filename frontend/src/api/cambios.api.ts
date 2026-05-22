import { api } from './client'

export interface SolicitudCambio {
  id_cambio: number
  asignacion: number
  asignacion_detalle: {
    id_asignacion: number
    sala: string
    dia: string
    hora_inicio: string
    hora_fin: string
    semestre: string
  }
  solicitante: number
  solicitante_email: string
  solicitante_nombre: string
  monitor_reemplazo: number
  monitor_reemplazo_email: string
  monitor_reemplazo_nombre: string
  tipo: string
  motivo: string
  estado: 'pendiente' | 'aprobada' | 'rechazada'
  respuesta: string
  respondido_por: number | null
  respondido_por_email: string | null
  fecha_creacion: string
  fecha_respuesta: string | null
}

export const cambiosApi = {
  list: (params?: { estado?: string }) =>
    api.get<SolicitudCambio[]>('/api/cambios/', { params }),

  get: (id: number) => api.get<SolicitudCambio>(`/api/cambios/${id}/`),

  create: (data: { asignacion: number; monitor_reemplazo: number; motivo?: string }) =>
    api.post<SolicitudCambio>('/api/cambios/', data),

  responder: (id: number, data: { estado: 'aprobada' | 'rechazada'; respuesta?: string }) =>
    api.post<SolicitudCambio>(`/api/cambios/${id}/responder/`, data),
}
