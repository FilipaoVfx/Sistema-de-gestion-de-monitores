export type Dia = 'lunes' | 'martes' | 'miercoles' | 'jueves' | 'viernes' | 'sabado'

export interface Horario {
  id: number
  dia: Dia
  dia_display: string
  hora_inicio: string
  hora_fin: string
}
