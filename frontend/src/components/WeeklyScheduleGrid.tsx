import type { Horario } from '../api/horarios.api'
import type { Asignacion } from '../api/asignaciones.api'
import UserAvatar from './ui/UserAvatar'
import { formatTime } from '../utils/formatDate'

interface Props {
  /** Horarios del backend (slots posibles). Si esta vacio, no se muestra grilla. */
  horarios: Horario[]
  /** Asignaciones a renderizar en las celdas correspondientes. */
  asignaciones: Asignacion[]
  /** Si esta seteado, los turnos de este monitor se resaltan visualmente. */
  highlightUserId?: number | null
  /** Opcional: callback al click en una celda (admin). */
  onCellClick?: (slot: Slot, asignacionesEnCelda: Asignacion[]) => void
}

const DIAS: { num: number; short: string; long: string }[] = [
  { num: 1, short: 'Lun', long: 'Lunes'     },
  { num: 2, short: 'Mar', long: 'Martes'    },
  { num: 3, short: 'Mié', long: 'Miércoles' },
  { num: 4, short: 'Jue', long: 'Jueves'    },
  { num: 5, short: 'Vie', long: 'Viernes'   },
  { num: 6, short: 'Sáb', long: 'Sábado'    },
]

interface Slot {
  hora_inicio: string  // HH:MM:SS
  hora_fin:    string
}

/** Extrae bloques horarios unicos (hora_inicio, hora_fin) ordenados por inicio. */
function getUniqueSlots(horarios: Horario[]): Slot[] {
  const map = new Map<string, Slot>()
  for (const h of horarios) {
    const key = `${h.hora_inicio}-${h.hora_fin}`
    if (!map.has(key)) map.set(key, { hora_inicio: h.hora_inicio, hora_fin: h.hora_fin })
  }
  return Array.from(map.values()).sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio))
}

export default function WeeklyScheduleGrid({
  horarios, asignaciones, highlightUserId, onCellClick,
}: Props) {
  const slots = getUniqueSlots(horarios)
  if (slots.length === 0) {
    return (
      <div className="p-8 text-center text-sm text-textMuted">
        No hay horarios definidos para esta sala.
      </div>
    )
  }

  // Index asignaciones por (dia_semana, hora_inicio, hora_fin)
  const asigMap = new Map<string, Asignacion[]>()
  for (const a of asignaciones) {
    const k = `${a.dia_semana}|${a.hora_inicio}|${a.hora_fin}`
    if (!asigMap.has(k)) asigMap.set(k, [])
    asigMap.get(k)!.push(a)
  }

  // Index horarios por (dia, hora_inicio, hora_fin) para saber si el slot
  // existe en ese dia (puede que un slot solo aplique a algunos dias)
  const horarioExiste = new Set<string>()
  for (const h of horarios) {
    horarioExiste.add(`${h.dia_semana}|${h.hora_inicio}|${h.hora_fin}`)
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-separate border-spacing-0">
        <thead>
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium text-textMuted uppercase tracking-wide bg-gray-50 border-b border-gray-100 w-24">
              Bloque
            </th>
            {DIAS.map(d => (
              <th
                key={d.num}
                className="px-3 py-2 text-center text-xs font-medium text-textMuted uppercase tracking-wide bg-gray-50 border-b border-gray-100"
              >
                {d.short}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {slots.map(slot => (
            <tr key={`${slot.hora_inicio}-${slot.hora_fin}`}>
              <td className="px-3 py-2 text-xs font-medium text-textMuted bg-gray-50/50 border-b border-gray-100 align-top">
                <div>{formatTime(slot.hora_inicio)}</div>
                <div className="text-gray-400">{formatTime(slot.hora_fin)}</div>
              </td>
              {DIAS.map(d => {
                const key = `${d.num}|${slot.hora_inicio}|${slot.hora_fin}`
                const existe = horarioExiste.has(key)
                const asigs = asigMap.get(key) ?? []
                const isHighlighted = highlightUserId != null && asigs.some(a => a.monitor === highlightUserId)
                const baseClass = 'h-16 border-b border-gray-100 p-1.5 align-top'

                if (!existe) {
                  return (
                    <td key={d.num} className={`${baseClass} bg-gray-50/30`} />
                  )
                }
                if (asigs.length === 0) {
                  return (
                    <td
                      key={d.num}
                      onClick={() => onCellClick?.(slot, [])}
                      className={`${baseClass} bg-white ${onCellClick ? 'cursor-pointer hover:bg-blue-50/50' : ''}`}
                    >
                      <span className="text-xs text-gray-300 italic">Libre</span>
                    </td>
                  )
                }
                return (
                  <td
                    key={d.num}
                    onClick={() => onCellClick?.(slot, asigs)}
                    className={[
                      baseClass,
                      onCellClick ? 'cursor-pointer hover:bg-gray-50/80' : '',
                      isHighlighted ? 'bg-primary/5 ring-2 ring-inset ring-primary/30' : 'bg-white',
                    ].filter(Boolean).join(' ')}
                  >
                    <div className="flex flex-wrap gap-1">
                      {asigs.map(a => (
                        <UserAvatar
                          key={a.id_asignacion}
                          userId={a.monitor}
                          name={a.monitor_nombre}
                          size="xs"
                          ringed
                          selected={a.monitor === highlightUserId}
                        />
                      ))}
                    </div>
                    {asigs.length === 1 && (
                      <p className="text-[10px] text-textMuted mt-1 truncate">
                        {asigs[0].monitor_nombre.split(' ')[0]}
                      </p>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
