import { asignacionesApi } from './asignaciones.api'
import { cambiosApi } from './cambios.api'
import { monitoresApi } from './monitores.api'
import { salasApi } from './salas.api'

export interface DashboardData {
  salas_activas: number
  monitores_activos: number
  asignaciones_activas: number
  solicitudes_pendientes: number
}

/** Agrega datos de múltiples endpoints para construir el dashboard */
export const dashboardApi = {
  get: async (): Promise<DashboardData> => {
    const [salas, monitores, asignaciones, cambios] = await Promise.allSettled([
      salasApi.list(),
      monitoresApi.list(),
      asignacionesApi.list(),
      cambiosApi.list({ estado: 'pendiente' }),
    ])

    return {
      salas_activas:          salas.status       === 'fulfilled' ? salas.value.data.length       : 0,
      monitores_activos:      monitores.status   === 'fulfilled' ? monitores.value.data.length   : 0,
      asignaciones_activas:   asignaciones.status === 'fulfilled' ? asignaciones.value.data.length : 0,
      solicitudes_pendientes: cambios.status     === 'fulfilled' ? cambios.value.data.length     : 0,
    }
  },
}
