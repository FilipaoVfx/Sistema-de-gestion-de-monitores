"""Lógica de negocio para gestionar solicitudes de cambio de turno."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import now

from asignaciones.models import Asignacion

from .models import SolicitudCambio


def crear_solicitud_cambio(*, asignacion, solicitante, monitor_reemplazo, motivo="") -> SolicitudCambio:
	"""Crea una nueva solicitud de cambio de turno.

	Args:
		asignacion: Asignación del turno que no se podrá asistir.
		solicitante: Usuario que solicita el cambio (debe ser el dueño).
		monitor_reemplazo: Usuario que cubrirá el turno.
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


def aprobar_solicitud(*, solicitud: SolicitudCambio, admin, respuesta=None) -> SolicitudCambio:
	"""Aprueba una solicitud de cambio de turno.

	Al aprobar, se actualiza la asignación original para que el monitor
	de reemplazo quede formalmente como responsable del turno.
	La SolicitudCambio mantiene la trazabilidad histórica completa.

	Args:
		solicitud: Solicitud a aprobar.
		admin: Usuario administrador que aprueba.
		respuesta: Mensaje opcional de respuesta.

	Returns:
		La solicitud actualizada.

	Raises:
		ValidationError: Si la solicitud ya fue respondida o hay conflictos.
	"""
	if solicitud.estado != SolicitudCambio.PENDIENTE:
		raise ValidationError("La solicitud ya fue respondida.")

	asignacion = solicitud.asignacion
	reemplazo = solicitud.monitor_reemplazo

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
