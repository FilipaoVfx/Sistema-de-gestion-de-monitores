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
  /** Puede ser null: el monitor solicita sin reemplazo, admin asigna al aprobar. */
  monitor_reemplazo: number | null
  monitor_reemplazo_email: string | null
  monitor_reemplazo_nombre: string | null
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

  /** Monitor crea solicitud: solo asignacion + motivo. El admin elige reemplazo al aprobar. */
  create: (data: { asignacion: number; motivo?: string }) =>
    api.post<SolicitudCambio>('/api/cambios/', data),

  /** Admin responde: si estado=aprobada, monitor_reemplazo es obligatorio. */
  responder: (
    id: number,
    data: {
      estado: 'aprobada' | 'rechazada'
      monitor_reemplazo?: number
      respuesta?: string
    },
  ) => api.post<SolicitudCambio>(`/api/cambios/${id}/responder/`, data),
}
