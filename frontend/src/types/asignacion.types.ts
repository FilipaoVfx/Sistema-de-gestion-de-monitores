import type { Monitor } from './monitor.types'
import type { Sala }    from './sala.types'
import type { Horario } from './horario.types'

export interface Asignacion {
  id: number
  monitor: string          // cedula (FK write)
  monitor_detail: Monitor
  sala: number             // id (FK write)
  sala_detail: Sala
  horario: number          // id (FK write)
  horario_detail: Horario
  fecha_inicio: string
  fecha_fin: string | null
  activa: boolean
}

export interface AsignacionCreate {
  monitor: string
  sala: number
  horario: number
  fecha_inicio: string
  fecha_fin?: string
}
