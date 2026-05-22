"""Lógica de negocio para gestionar solicitudes de cambio de turno."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import now

from asignaciones.models import Asignacion

from .models import SolicitudCambio


def crear_solicitud_cambio(*, asignacion, solicitante, monitor_reemplazo=None, motivo="") -> SolicitudCambio:
	"""Crea una nueva solicitud de cambio de turno.

	El monitor solo necesita pasar `asignacion` + `motivo`; el reemplazo
	queda pendiente y lo asigna el admin al aprobar.

	Args:
		asignacion: Asignación del turno que no se podrá asistir.
		solicitante: Usuario que solicita el cambio (debe ser el dueño).
		monitor_reemplazo: Opcional. Si se pasa al crear, queda registrado;
			si no, se setea al aprobar.
		motivo: Razón del cambio.

	Returns:
		La SolicitudCambio creada.

	Raises:
		ValidationError: Si alguna validación del modelo falla.
	"""
	solicitud = SolicitudCambio(
		asignacion=asignacion,
		solicitante=solicitante,
		monitor_reemplazo=monitor_reemplazo,
		tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		motivo=motivo,
	)
	solicitud.save()
	return solicitud


def aprobar_solicitud(*, solicitud: SolicitudCambio, admin, monitor_reemplazo=None, respuesta=None) -> SolicitudCambio:
	"""Aprueba una solicitud de cambio de turno.

	Al aprobar, se actualiza la asignación original para que el monitor
	de reemplazo quede formalmente como responsable del turno.
	La SolicitudCambio mantiene la trazabilidad histórica completa.

	Args:
		solicitud: Solicitud a aprobar.
		admin: Usuario administrador que aprueba.
		monitor_reemplazo: Monitor que cubrira el turno. Obligatorio si la
			solicitud no tenia uno asignado. Si se pasa, sobrescribe el
			actual.
		respuesta: Mensaje opcional de respuesta.

	Returns:
		La solicitud actualizada.

	Raises:
		ValidationError: Si la solicitud ya fue respondida, no hay reemplazo,
			el reemplazo no es valido (mismo solicitante, no monitor) o tiene
			conflicto de horario.
	"""
	if solicitud.estado != SolicitudCambio.PENDIENTE:
		raise ValidationError("La solicitud ya fue respondida.")

	asignacion = solicitud.asignacion

	# Resolver el reemplazo: el del argumento gana sobre el guardado
	reemplazo = monitor_reemplazo or solicitud.monitor_reemplazo
	if reemplazo is None:
		raise ValidationError(
			"Para aprobar la solicitud debe asignarse un monitor de reemplazo."
		)

	# El reemplazo no puede ser el mismo solicitante
	if reemplazo.pk == solicitud.solicitante_id:
		raise ValidationError(
			"El monitor de reemplazo no puede ser el mismo que el solicitante."
		)

	# El reemplazo debe tener rol monitor
	if getattr(reemplazo, "rol", None) != "monitor":
		raise ValidationError("El reemplazo debe tener rol Monitor.")

	# Verificar que el reemplazo no tenga conflicto de horario al momento de aprobar
	conflicto = Asignacion.objects.filter(
		monitor_id=reemplazo.pk,
		semestre_id=asignacion.semestre_id,
		horario__dia_semana=asignacion.horario.dia_semana,
		horario__hora_inicio__lt=asignacion.horario.hora_fin,
		horario__hora_fin__gt=asignacion.horario.hora_inicio,
	).exists()
	if conflicto:
		raise ValidationError(
			"El monitor de reemplazo ya tiene una asignación que se cruza con este horario."
		)

	with transaction.atomic():
		# Setear el reemplazo en la solicitud (si vino del argumento)
		solicitud.monitor_reemplazo = reemplazo

		# Actualizar el monitor de la asignación al reemplazo
		asignacion.monitor = reemplazo
		asignacion.save()

		# Registrar la aprobación en la solicitud
		solicitud.estado = SolicitudCambio.APROBADA
		solicitud.respondido_por = admin
		solicitud.respuesta = respuesta or ""
		solicitud.fecha_respuesta = now()
		solicitud.save()

	return solicitud


def rechazar_solicitud(*, solicitud: SolicitudCambio, admin, respuesta=None) -> SolicitudCambio:
	"""Rechaza una solicitud de cambio de turno.

	Args:
		solicitud: Solicitud a rechazar.
		admin: Usuario administrador que rechaza.
		respuesta: Mensaje opcional de respuesta.

	Returns:
		La solicitud actualizada.

	Raises:
		ValidationError: Si la solicitud ya fue respondida.
	"""
	if solicitud.estado != SolicitudCambio.PENDIENTE:
		raise ValidationError("La solicitud ya fue respondida.")

	solicitud.estado = SolicitudCambio.RECHAZADA
	solicitud.respondido_por = admin
	solicitud.respuesta = respuesta or ""
	solicitud.fecha_respuesta = now()
	solicitud.save()

	return solicitud
