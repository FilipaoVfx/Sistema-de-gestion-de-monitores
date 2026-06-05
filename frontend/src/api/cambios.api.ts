import { api } from './client'
import type { Asignacion } from './asignaciones.api'

export type EstadoCandidato =
  | 'pendiente'    // admin la propuso, solicitante aun no la elige
  | 'elegida'      // solicitante la eligio, candidato debe confirmar
  | 'aceptada'     // candidato acepto, swap ejecutado
  | 'rechazada'    // candidato rechazo
  | 'descartada'   // ya no aplica (otra opcion gano o solicitud rechazada)

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
  /** Snapshot del candidato propuesto (no cambia tras swap). */
  candidato_id: number | null
  candidato_nombre: string | null
  candidato_email: string | null
  orden: number
  estado_candidato: EstadoCandidato
  seleccionada: boolean  // alias historico de estado_candidato === 'aceptada'
  fecha_creacion: string
  fecha_decision_candidato: string | null
}

export type EstadoSolicitud =
  | 'pendiente'             // recien creada por monitor
  | 'con_propuestas'        // admin propuso 2+ opciones
  | 'esperando_candidato'   // solicitante eligio, candidato debe confirmar
  | 'aprobada'              // candidato acepto, swap ejecutado
  | 'rechazada'             // admin rechazo o todos los candidatos rechazaron

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
  /** Solo se llena cuando candidato acepto (estado=aprobada). */
  monitor_reemplazo: number | null
  monitor_reemplazo_email: string | null
  monitor_reemplazo_nombre: string | null
  tipo: string
  motivo: string
  estado: EstadoSolicitud
  respuesta: string
  respondido_por: number | null
  respondido_por_email: string | null
  /** Opciones propuestas. Vacio si estado=pendiente. */
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

  /** Admin: lista de asignaciones candidatas para swap. */
  candidatos: (idCambio: number) =>
    api.get<Asignacion[]>(`/api/cambios/${idCambio}/candidatos/`),

  /** Admin propone 2+ opciones (asignacion_ids). */
  proponer: (idCambio: number, data: { opciones: number[]; respuesta?: string }) =>
    api.post<SolicitudCambio>(`/api/cambios/${idCambio}/proponer/`, data),

  /** Solicitante elige una opcion. Swap NO se ejecuta aun, candidato debe confirmar. */
  elegir: (idCambio: number, data: { opcion: number }) =>
    api.post<SolicitudCambio>(`/api/cambios/${idCambio}/elegir/`, data),

  /** Candidato acepta el swap. Si todo OK, swap se ejecuta atomicamente. */
  aceptarComoCandidato: (idCambio: number) =>
    api.post<SolicitudCambio>(`/api/cambios/${idCambio}/aceptar/`, {}),

  /** Candidato declina el swap. La opcion queda rechazada y solicitante puede elegir otra. */
  rechazarComoCandidato: (idCambio: number, data?: { motivo?: string }) =>
    api.post<SolicitudCambio>(`/api/cambios/${idCambio}/rechazar-candidato/`, data || {}),

  /** Admin rechaza la solicitud completa en cualquier estado no-terminal. */
  rechazar: (idCambio: number, data?: { respuesta?: string }) =>
    api.post<SolicitudCambio>(`/api/cambios/${idCambio}/rechazar/`, data || {}),
}
