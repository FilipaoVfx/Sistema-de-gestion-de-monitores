import { api } from './client'
import type { Asignacion } from './asignaciones.api'

export interface OpcionCambio {
  id_opcion: number
  solicitud: number
  asignacion_swap: number
  asignacion_swap_detalle: {
    id_asignacion: number
    sala: string
    sala_codigo: string
    dia: string
    dia_semana: number
    hora_inicio: string
    hora_fin: string
    semestre: string
  }
  monitor_swap_nombre: string
  monitor_swap_email: string
  orden: number
  seleccionada: boolean
  fecha_creacion: string
}

export interface SolicitudCambio {
  id_cambio: number
  asignacion: number
  asignacion_detalle: {
    id_asignacion: number
    sala: string
    sala_codigo: string
    dia: string
    dia_semana: number
    hora_inicio: string
    hora_fin: string
    semestre: string
  }
  solicitante: number
  solicitante_email: string
  solicitante_nombre: string
  /** Solo se llena cuando el monitor eligio una opcion (estado=aprobada). */
  monitor_reemplazo: number | null
  monitor_reemplazo_email: string | null
  monitor_reemplazo_nombre: string | null
  tipo: string
  motivo: string
  estado: 'pendiente' | 'con_propuestas' | 'aprobada' | 'rechazada'
  respuesta: string
  respondido_por: number | null
  respondido_por_email: string | null
  /** Opciones de swap propuestas por el admin (vacio si estado=pendiente o rechazada). */
  opciones: OpcionCambio[]
  fecha_creacion: string
  fecha_respuesta: string | null
}

export const cambiosApi = {
  list: (params?: { estado?: string }) =>
    api.get<SolicitudCambio[]>('/api/cambios/', { params }),

  get: (id: number) => api.get<SolicitudCambio>(`/api/cambios/${id}/`),

  /** Monitor crea solicitud (solo asignacion + motivo). */
  create: (data: { asignacion: number; motivo?: string }) =>
    api.post<SolicitudCambio>('/api/cambios/', data),

  /** Admin: lista de asignaciones candidatas para swap (mismo semestre, otros monitores). */
  candidatos: (idCambio: number) =>
    api.get<Asignacion[]>(`/api/cambios/${idCambio}/candidatos/`),

  /** Admin: propone 2+ opciones de swap (asignacion_ids). */
  proponer: (idCambio: number, data: { opciones: number[]; respuesta?: string }) =>
    api.post<SolicitudCambio>(`/api/cambios/${idCambio}/proponer/`, data),

  /** Monitor solicitante: elige una opcion; se ejecuta el swap. */
  elegir: (idCambio: number, data: { opcion: number }) =>
    api.post<SolicitudCambio>(`/api/cambios/${idCambio}/elegir/`, data),

  /** Admin rechaza la solicitud (sin proponer). */
  rechazar: (idCambio: number, data?: { respuesta?: string }) =>
    api.post<SolicitudCambio>(`/api/cambios/${idCambio}/rechazar/`, data || {}),
}
