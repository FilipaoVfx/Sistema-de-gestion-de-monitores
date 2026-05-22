export interface Sala {
  id: number
  nombre: string
  capacidad: number
  descripcion: string
  activa: boolean
  monitor_actual?: { cedula: string; nombre: string } | null
}
