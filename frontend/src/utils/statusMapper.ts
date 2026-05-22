export type StatusColor = 'green' | 'yellow' | 'red' | 'gray' | 'blue'

export function estadoColor(estado: string): StatusColor {
  switch (estado) {
    case 'aprobado':   return 'green'
    case 'pendiente':  return 'yellow'
    case 'rechazado':  return 'red'
    default:           return 'gray'
  }
}

export const DIA_ORDER: Record<string, number> = {
  lunes: 0, martes: 1, miercoles: 2, jueves: 3, viernes: 4, sabado: 5,
}
