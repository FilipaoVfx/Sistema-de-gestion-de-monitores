"""Lógica de negocio para gestionar solicitudes de cambio de turno.

Cada accion del flujo (propose, choose, reject) valida primero su transicion
contra la maquina de estados (state_machine.py) y luego ejecuta la mutacion
correspondiente dentro de una transaccion atomica.

Para el swap concretamente (choose):
- Pre-validamos los conflictos de horario ANTES de mutar nada
  (excluyendo ambas asignaciones del swap del query).
- Mutamos saltando full_clean() de Asignacion, porque durante la transaccion
  habria un estado intermedio donde un monitor aparece con dos asignaciones
  (la suya original + la recien recibida) y Asignacion.clean() reportaria
  conflicto.
- Despues de mutar, las pre-validaciones garantizan el invariante.
"""

from __future__ import annotations

from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import now

from asignaciones.models import Asignacion

from .models import OpcionCambio, SolicitudCambio
from .state_machine import assert_transition


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

	Transicion en la maquina de estados:
		PENDIENTE --(propose, admin)--> CON_PROPUESTAS

	Cada `asignacion_swap` es la asignacion de OTRO monitor con la que se
	haria un swap completo si el solicitante la acepta.

	Args:
		solicitud: Solicitud en estado PENDIENTE.
		admin: Administrador que propone (rol=admin).
		asignaciones_swap: Iterable de Asignacion (al menos 2, no duplicadas).
		respuesta: Mensaje opcional para el solicitante.

	Returns:
		La solicitud actualizada con estado CON_PROPUESTAS y opciones[] llenas.

	Raises:
		ValidationError: Si la transicion no es valida (estado o actor) o si
			las opciones no cumplen el contrato (<2, duplicadas, OpcionCambio
			rechaza alguna por modelo).
	"""
	# 1) Maquina de estados: valida transicion + actor
	target_state = assert_transition(solicitud, "propose", actor=admin)

	# 2) Validacion del payload
	asignaciones_list = list(asignaciones_swap)
	if len(asignaciones_list) < 2:
		raise ValidationError("Debe ofrecer al menos 2 opciones de cambio.")
	swap_ids = [a.pk for a in asignaciones_list]
	if len(set(swap_ids)) != len(swap_ids):
		raise ValidationError("Las opciones no pueden repetirse.")

	# 3) Mutacion atomica
	with transaction.atomic():
		for idx, asig_swap in enumerate(asignaciones_list, start=1):
			OpcionCambio.objects.create(
				solicitud=solicitud,
				asignacion_swap=asig_swap,
				orden=idx,
			)

		solicitud.estado = target_state
		solicitud.respondido_por = admin
		solicitud.respuesta = respuesta or ""
		# fecha_respuesta se setea solo en decision final (aprobada/rechazada)
		solicitud.save(validate=False)

	return solicitud


def elegir_opcion(*, solicitud: SolicitudCambio, opcion: OpcionCambio, monitor) -> SolicitudCambio:
	"""Monitor solicitante elige una opcion y se ejecuta el swap atomico.

	Transicion en la maquina de estados:
		CON_PROPUESTAS --(choose, monitor solicitante)--> APROBADA

	El swap intercambia el monitor de las dos asignaciones:
		asignacion_original.monitor = monitor_b
		asignacion_swap.monitor     = monitor_a

	*Nota critica sobre el swap*:
	Durante la transaccion existe un estado intermedio donde un monitor
	aparece con dos asignaciones (la suya original + la recien recibida).
	Si dejamos que Asignacion.save() ejecute full_clean(), su clean()
	reporta conflicto al detectar esas dos asignaciones del mismo monitor
	en BD. Para evitar este falso positivo:
	1. Pre-validamos los conflictos reales EXCLUYENDO ambas asignaciones
	   del swap del query (lineas conflicto_a / conflicto_b).
	2. Mutamos con save(validate=False) para saltarnos full_clean().

	Las pre-validaciones garantizan que el estado final es valido sin
	necesidad de la validacion de Asignacion durante la mutacion.

	Args:
		solicitud: Solicitud en estado CON_PROPUESTAS.
		opcion: OpcionCambio elegida (debe pertenecer a la solicitud).
		monitor: Usuario que esta eligiendo (debe ser el solicitante).

	Returns:
		La solicitud actualizada con estado APROBADA y monitor_reemplazo
		registrado.

	Raises:
		ValidationError con detalle especifico:
			- transicion invalida (estado/rol/solicitante)
			- opcion no pertenece a la solicitud
			- conflicto de horario real (excluyendo el swap)
	"""
	# 1) Maquina de estados: valida transicion + actor + que sea solicitante
	target_state = assert_transition(solicitud, "choose", actor=monitor)

	# 2) Validacion estructural de la opcion
	if opcion.solicitud_id != solicitud.id_cambio:
		raise ValidationError({
			"opcion": "La opcion seleccionada no pertenece a esta solicitud."
		})

	asignacion_original = solicitud.asignacion
	asignacion_swap     = opcion.asignacion_swap
	monitor_a = solicitud.solicitante       # dueno original del turno A
	monitor_b = asignacion_swap.monitor     # dueno original del turno B

	# 3) Pre-validacion de conflictos (excluyendo AMBAS asignaciones del swap)
	# Si A tiene OTRA asignacion (no la suya original) que cruza con el horario de B → conflicto
	conflicto_a_qs = Asignacion.objects.filter(
		monitor_id=monitor_a.pk,
		semestre_id=asignacion_swap.semestre_id,
		horario__dia_semana=asignacion_swap.horario.dia_semana,
		horario__hora_inicio__lt=asignacion_swap.horario.hora_fin,
		horario__hora_fin__gt=asignacion_swap.horario.hora_inicio,
	).exclude(pk__in=[asignacion_original.pk, asignacion_swap.pk])
	if conflicto_a_qs.exists():
		bloqueante = conflicto_a_qs.first()
		raise ValidationError({
			"swap": (
				f"Ya tienes otra asignacion ({bloqueante.horario.sala.codigo} "
				f"dia {bloqueante.horario.dia_semana} "
				f"{bloqueante.horario.hora_inicio}-{bloqueante.horario.hora_fin}) "
				f"que se cruza con el horario de la opcion."
			)
		})

	# Si B tiene OTRA asignacion (no la suya original) que cruza con el horario de A → conflicto
	conflicto_b_qs = Asignacion.objects.filter(
		monitor_id=monitor_b.pk,
		semestre_id=asignacion_original.semestre_id,
		horario__dia_semana=asignacion_original.horario.dia_semana,
		horario__hora_inicio__lt=asignacion_original.horario.hora_fin,
		horario__hora_fin__gt=asignacion_original.horario.hora_inicio,
	).exclude(pk__in=[asignacion_original.pk, asignacion_swap.pk])
	if conflicto_b_qs.exists():
		bloqueante = conflicto_b_qs.first()
		raise ValidationError({
			"swap": (
				f"El monitor de reemplazo ({monitor_b.email}) ya tiene otra "
				f"asignacion ({bloqueante.horario.sala.codigo} "
				f"{bloqueante.horario.hora_inicio}-{bloqueante.horario.hora_fin}) "
				f"que se cruza con tu horario."
			)
		})

	# 4) Mutacion atomica: swap + opcion + solicitud
	with transaction.atomic():
		# Swap saltando full_clean (las pre-validaciones ya garantizaron
		# que el estado final sera consistente).
		asignacion_original.monitor = monitor_b
		asignacion_original.save(validate=False)

		asignacion_swap.monitor = monitor_a
		asignacion_swap.save(validate=False)

		# Marca la opcion elegida (queda como evidencia historica)
		opcion.seleccionada = True
		opcion.save()

		# Cierra la solicitud
		solicitud.monitor_reemplazo = monitor_b
		solicitud.estado = target_state
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

	Transicion en la maquina de estados:
		PENDIENTE      --(reject, admin)--> RECHAZADA
		CON_PROPUESTAS --(reject, admin)--> RECHAZADA

	Args:
		solicitud: Solicitud no terminal (no aprobada, no rechazada).
		admin: Usuario administrador que rechaza.
		respuesta: Mensaje opcional de respuesta.

	Returns:
		La solicitud actualizada con estado RECHAZADA y fecha_respuesta.

	Raises:
		ValidationError: Si la transicion no es valida (estado terminal o
			actor no autorizado).
	"""
	target_state = assert_transition(solicitud, "reject", actor=admin)

	solicitud.estado = target_state
	solicitud.respondido_por = admin
	solicitud.respuesta = respuesta or ""
	solicitud.fecha_respuesta = now()
	solicitud.save(validate=False)

	return solicitud
