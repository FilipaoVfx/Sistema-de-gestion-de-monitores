import type { Monitor }    from './monitor.types'
import type { Asignacion } from './asignacion.types'

export type EstadoCambio = 'pendiente' | 'aprobado' | 'rechazado'

export interface SolicitudCambio {
  id: number
  asignacion: number
  asignacion_detail: Asignacion
  monitor_solicitante: string
  monitor_solicitante_detail: Monitor
  monitor_receptor: string
  monitor_receptor_detail: Monitor
  motivo: string
  estado: EstadoCambio
  estado_display: string
  fecha_solicitud: string
  fecha_resolucion: string | null
  observaciones: string
}

export interface SolicitudCambioCreate {
  asignacion: number
  monitor_solicitante: string
  monitor_receptor: string
  motivo: string
}
