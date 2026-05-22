import type { Asignacion } from '../types/asignacion.types'

export const DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado'] as const
export const DIAS_DISPLAY: Record<string, string> = {
  lunes: 'Lunes', martes: 'Martes', miercoles: 'Miércoles',
  jueves: 'Jueves', viernes: 'Viernes', sabado: 'Sábado',
}

/** Construye un mapa día→horarioId→asignación para el grid semanal */
export function buildScheduleMap(
  asignaciones: Asignacion[]
): Map<string, Map<number, Asignacion>> {
  const map = new Map<string, Map<number, Asignacion>>()
  for (const a of asignaciones) {
    const dia = a.horario_detail.dia
    if (!map.has(dia)) map.set(dia, new Map())
    map.get(dia)!.set(a.horario_detail.id, a)
  }
  return map
}
