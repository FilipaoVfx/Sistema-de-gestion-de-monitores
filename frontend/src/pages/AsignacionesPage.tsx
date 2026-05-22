import PendingBackend from '../components/PendingBackend'

export default function AsignacionesPage() {
  return (
    <PendingBackend
      title="Asignaciones"
      description="Turnos semanales de monitores en salas"
      backendPath="/asignaciones/crear/"
    />
  )
}
