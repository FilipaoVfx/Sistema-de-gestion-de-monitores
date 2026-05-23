"""Lógica de negocio para gestionar solicitudes de cambio de turno."""

from __future__ import annotations

from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import now

from asignaciones.models import Asignacion

from .models import OpcionCambio, SolicitudCambio


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


def proponer_opciones(*, solicitud: SolicitudCambio, admin, asignaciones_swap: Iterable, respuesta="") -> SolicitudCambio:
	"""Admin propone 2+ opciones de swap para una solicitud pendiente.

	Cada `asignacion_swap` es la asignacion de OTRO monitor con la que se
	haria un swap completo si el solicitante la acepta. La solicitud pasa
	de PENDIENTE a CON_PROPUESTAS.

	Args:
		solicitud: Solicitud en estado PENDIENTE.
		admin: Administrador que propone.
		asignaciones_swap: Iterable de Asignacion (al menos 2).
		respuesta: Mensaje opcional para el solicitante.

	Returns:
		La solicitud actualizada.

	Raises:
		ValidationError: Si la solicitud no esta pendiente, o las opciones
			son menos de 2, o alguna no cumple las validaciones del modelo
			OpcionCambio.
	"""
	if solicitud.estado != SolicitudCambio.PENDIENTE:
		raise ValidationError("La solicitud no esta en estado pendiente.")

	asignaciones_list = list(asignaciones_swap)
	if len(asignaciones_list) < 2:
		raise ValidationError("Debe ofrecer al menos 2 opciones de cambio.")

	# Detectar duplicados
	swap_ids = [a.pk for a in asignaciones_list]
	if len(set(swap_ids)) != len(swap_ids):
		raise ValidationError("Las opciones no pueden repetirse.")

	with transaction.atomic():
		# Crea OpcionCambio para cada swap propuesto
		for idx, asig_swap in enumerate(asignaciones_list, start=1):
			OpcionCambio.objects.create(
				solicitud=solicitud,
				asignacion_swap=asig_swap,
				orden=idx,
			)

		# Actualiza solicitud a CON_PROPUESTAS
		solicitud.estado = SolicitudCambio.CON_PROPUESTAS
		solicitud.respondido_por = admin
		solicitud.respuesta = respuesta or ""
		# fecha_respuesta se setea solo cuando ya hay decision final, no aqui
		solicitud.save(validate=False)

	return solicitud


def elegir_opcion(*, solicitud: SolicitudCambio, opcion: OpcionCambio, monitor) -> SolicitudCambio:
	"""Monitor solicitante elige una opcion de swap y se ejecuta el cambio.

	El swap intercambia los monitores de las 2 asignaciones:
	- asignacion_original.monitor pasa a ser el monitor de asignacion_swap
	- asignacion_swap.monitor pasa a ser el solicitante

	Args:
		solicitud: Solicitud en estado CON_PROPUESTAS.
		opcion: OpcionCambio elegida (debe pertenecer a la solicitud).
		monitor: Usuario que esta eligiendo (debe ser el solicitante).

	Returns:
		La solicitud actualizada con estado APROBADA.

	Raises:
		ValidationError: Si la solicitud no esta CON_PROPUESTAS, la opcion
			no pertenece a la solicitud, el monitor no es el solicitante,
			o hay conflicto de horario que no permita el swap.
	"""
	if solicitud.estado != SolicitudCambio.CON_PROPUESTAS:
		raise ValidationError("La solicitud no esta esperando eleccion de opcion.")

	if opcion.solicitud_id != solicitud.id_cambio:
		raise ValidationError("La opcion no pertenece a esta solicitud.")

	if monitor.pk != solicitud.solicitante_id:
		raise ValidationError("Solo el solicitante puede elegir una opcion.")

	asignacion_original = solicitud.asignacion
	asignacion_swap = opcion.asignacion_swap
	monitor_a = solicitud.solicitante  # dueno original del turno A
	monitor_b = asignacion_swap.monitor  # dueno original del turno B

	# Verificar que no haya conflicto al hacer el swap:
	# Monitor A tendra el horario de B - puede que A tenga OTRA asignacion en ese horario
	conflicto_a = Asignacion.objects.filter(
		monitor_id=monitor_a.pk,
		semestre_id=asignacion_swap.semestre_id,
		horario__dia_semana=asignacion_swap.horario.dia_semana,
		horario__hora_inicio__lt=asignacion_swap.horario.hora_fin,
		horario__hora_fin__gt=asignacion_swap.horario.hora_inicio,
	).exclude(pk=asignacion_original.pk).exists()
	if conflicto_a:
		raise ValidationError(
			"Tienes otra asignacion que se cruza con el horario de la opcion."
		)

	# Monitor B tendra el horario de A - puede que B tenga OTRA asignacion en ese horario
	conflicto_b = Asignacion.objects.filter(
		monitor_id=monitor_b.pk,
		semestre_id=asignacion_original.semestre_id,
		horario__dia_semana=asignacion_original.horario.dia_semana,
		horario__hora_inicio__lt=asignacion_original.horario.hora_fin,
		horario__hora_fin__gt=asignacion_original.horario.hora_inicio,
	).exclude(pk=asignacion_swap.pk).exists()
	if conflicto_b:
		raise ValidationError(
			"El monitor reemplazo tiene otra asignacion que se cruza con tu horario."
		)

	with transaction.atomic():
		# Swap atomico: A toma el horario de B, B toma el horario de A
		asignacion_original.monitor = monitor_b
		asignacion_original.save()

		asignacion_swap.monitor = monitor_a
		asignacion_swap.save()

		# Marca la opcion seleccionada
		opcion.seleccionada = True
		opcion.save()

		# Actualiza la solicitud a APROBADA, registra el reemplazo elegido
		solicitud.monitor_reemplazo = monitor_b
		solicitud.estado = SolicitudCambio.APROBADA
		solicitud.fecha_respuesta = now()
		solicitud.save(validate=False)

	return solicitud


# Backcompat shim: si algun codigo viejo todavia llama a aprobar_solicitud,
# mantenemos la firma pero solo si la solicitud esta CON_PROPUESTAS. En el
# nuevo flujo el admin propone y el monitor elige.
def aprobar_solicitud(*, solicitud: SolicitudCambio, admin, monitor_reemplazo=None, respuesta=None) -> SolicitudCambio:
	"""DEPRECATED: usar proponer_opciones() + elegir_opcion()."""
	raise ValidationError(
		"Aprobacion directa deshabilitada. Use proponer_opciones() y luego "
		"elegir_opcion()."
	)


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
