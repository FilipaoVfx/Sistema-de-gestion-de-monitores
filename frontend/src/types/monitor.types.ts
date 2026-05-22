export interface Monitor {
  cedula: string
  nombre: string
  email: string
  rol: 'monitor' | 'administrador'
  is_active: boolean
  fecha_registro: string
  asignaciones_count?: number
}
