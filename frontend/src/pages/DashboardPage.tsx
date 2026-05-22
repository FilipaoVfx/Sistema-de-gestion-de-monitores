import PendingBackend from '../components/PendingBackend'

export default function DashboardPage() {
  return (
    <PendingBackend
      title="Dashboard"
      description="Resumen operativo — KPIs, asignaciones de la semana y solicitudes recientes"
      backendPath="/"
    />
  )
}
