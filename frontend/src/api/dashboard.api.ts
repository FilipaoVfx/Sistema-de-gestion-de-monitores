/**
 * Backend desplegado NO expone /dashboard/ (404).
 * Mantenemos la firma para que las páginas compilen; cuando se exponga, basta
 * añadir el endpoint en el backend y la app empezará a poblar datos reales.
 */
import { api } from './client'

export interface DashboardData {
  salas_activas: number
  monitores_activos: number
  asignaciones_activas: number
  solicitudes_pendientes: number
  asignaciones_por_dia: Record<string, number>
  ultimas_solicitudes: unknown[]
}

export const dashboardApi = {
  get: () => api.get<DashboardData>('/dashboard/'),
}
