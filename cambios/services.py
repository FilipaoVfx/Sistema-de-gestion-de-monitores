"""Logica de negocio para gestionar solicitudes de cambio de turno.

El flujo completo requiere 3 confirmaciones:
1. Admin propone N>=2 opciones de swap          -> proponer_opciones()
2. Solicitante elige una opcion                 -> elegir_opcion()
3. Candidato propuesto en esa opcion confirma   -> aceptar_como_candidato()
   o la rechaza                                 -> rechazar_como_candidato()

Solo cuando el candidato acepta se ejecuta el swap atomico. Si el candidato
rechaza, la opcion queda marcada y el solicitante puede elegir otra. Si no
quedan opciones disponibles, la solicitud queda RECHAZADA automaticamente.

Para el swap en si:
- Pre-validamos los conflictos de horario ANTES de mutar nada
  (excluyendo ambas asignaciones del swap del query).
- Mutamos saltando full_clean() de Asignacion, porque durante la transaccion
  habria un estado intermedio donde un monitor aparece con dos asignaciones
  y Asignacion.clean() reportaria falso positivo.
"""

from __future__ import annotations

from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import now

from asignaciones.models import Asignacion

from .models import OpcionCambio, SolicitudCambio
from .state_machine import assert_transition


# ===========================================================================
# 1) Monitor solicitante crea solicitud
# ===========================================================================

def crear_solicitud_cambio(*, asignacion, solicitante, monitor_reemplazo=None, motivo="") -> SolicitudCambio:
	"""Crea una nueva solicitud de cambio de turno.

	El monitor solo necesita pasar `asignacion` + `motivo`; el reemplazo
	queda pendiente y lo asigna el admin proponiendo opciones.

	Args:
		asignacion: Asignacion del turno que no se podra asistir.
		solicitante: Usuario que solicita el cambio (debe ser el dueno).
		monitor_reemplazo: Ignorado en el nuevo flujo (queda para backward compat).
		motivo: Razon del cambio.

	Returns:
		La SolicitudCambio creada en estado PENDIENTE.
	"""
	solicitud = SolicitudCambio(
		asignacion=asignacion,
		solicitante=solicitante,
		monitor_reemplazo=None,
		tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		motivo=motivo,
	)
	solicitud.save()
	return solicitud


# ===========================================================================
# 2) Admin propone N>=2 opciones de swap
# ===========================================================================

def proponer_opciones(*, solicitud: SolicitudCambio, admin, asignaciones_swap: Iterable, respuesta="") -> SolicitudCambio:
	"""Admin propone 2+ opciones de swap para una solicitud pendiente.

	Transicion: PENDIENTE --(propose, admin)--> CON_PROPUESTAS

	Cada `asignacion_swap` es la asignacion de OTRO monitor con la que se
	haria un swap completo si el solicitante la acepta Y el candidato confirma.

	Args:
		solicitud: Solicitud en estado PENDIENTE.
		admin: Administrador que propone (rol=admin).
		asignaciones_swap: Iterable de Asignacion (al menos 2, no duplicadas).
		respuesta: Mensaje opcional para el solicitante.

	Returns:
		La solicitud actualizada con estado CON_PROPUESTAS y opciones[] llenas.

	Raises:
		ValidationError: Si la transicion no es valida o las opciones no
			cumplen el contrato (<2, duplicadas, OpcionCambio rechaza alguna).
	"""
	target_state = assert_transition(solicitud, "propose", actor=admin)

	asignaciones_list = list(asignaciones_swap)
	if len(asignaciones_list) < 2:
		raise ValidationError("Debe ofrecer al menos 2 opciones de cambio.")
	swap_ids = [a.pk for a in asignaciones_list]
	if len(set(swap_ids)) != len(swap_ids):
		raise ValidationError("Las opciones no pueden repetirse.")

	with transaction.atomic():
		for idx, asig_swap in enumerate(asignaciones_list, start=1):
			OpcionCambio.objects.create(
				solicitud=solicitud,
				asignacion_swap=asig_swap,
				orden=idx,
				estado_candidato=OpcionCambio.EST_PENDIENTE,
				candidato_id=asig_swap.monitor_id,  # snapshot del candidato
			)

		solicitud.estado = target_state
		solicitud.respondido_por = admin
		solicitud.respuesta = respuesta or ""
		solicitud.save(validate=False)

	return solicitud


# ===========================================================================
# 3) Monitor solicitante elige una opcion (no ejecuta swap todavia)
# ===========================================================================

def elegir_opcion(*, solicitud: SolicitudCambio, opcion: OpcionCambio, monitor) -> SolicitudCambio:
	"""Solicitante elige una opcion: SWAP SE EJECUTA INMEDIATAMENTE.

	Transicion: CON_PROPUESTAS --(choose, solicitante)--> APROBADA

	Cuando el monitor solicitante elige una opcion, el intercambio de turnos
	se realiza en BD de forma atomica:
	  - asignacion_original.monitor pasa a ser el candidato propuesto
	  - asignacion_swap.monitor     pasa a ser el solicitante
	  - opcion.estado_candidato = ACEPTADA, seleccionada=True
	  - resto de opciones marcadas como DESCARTADAS
	  - solicitud queda APROBADA

	El admin solo recibe la notificacion del resultado (puede verlo en su
	dashboard / listado).

	Args:
		solicitud: Solicitud en estado CON_PROPUESTAS.
		opcion: OpcionCambio elegida (debe pertenecer a la solicitud).
		monitor: Usuario que esta eligiendo (debe ser el solicitante).

	Returns:
		La solicitud actualizada con estado APROBADA, monitor_reemplazo
		registrado y las asignaciones intercambiadas.

	Raises:
		ValidationError: Si la transicion no es valida, si la opcion no
			pertenece a la solicitud, o si hay conflicto de horario real.
	"""
	target_state = assert_transition(solicitud, "choose", actor=monitor)

	if opcion.solicitud_id != solicitud.id_cambio:
		raise ValidationError({
			"opcion": "La opcion seleccionada no pertenece a esta solicitud."
		})
	if opcion.estado_candidato not in (
		OpcionCambio.EST_PENDIENTE, OpcionCambio.EST_ELEGIDA,
	):
		raise ValidationError({
			"opcion": (
				f"Esta opcion ya fue procesada (estado: {opcion.estado_candidato}). "
				"Elige otra opcion."
			)
		})

	asignacion_original = solicitud.asignacion
	asignacion_swap     = opcion.asignacion_swap
	monitor_a = solicitud.solicitante  # dueno original del turno A
	monitor_b = asignacion_swap.monitor  # dueno original del turno B (candidato)

	# Pre-validacion de conflictos de horario reales, excluyendo ambas
	# asignaciones del swap del query (asi no contamos como conflicto las
	# propias asignaciones que se van a intercambiar).
	conflicto_a = Asignacion.objects.filter(
		monitor_id=monitor_a.pk,
		semestre_id=asignacion_swap.semestre_id,
		horario__dia_semana=asignacion_swap.horario.dia_semana,
		horario__hora_inicio__lt=asignacion_swap.horario.hora_fin,
		horario__hora_fin__gt=asignacion_swap.horario.hora_inicio,
	).exclude(pk__in=[asignacion_original.pk, asignacion_swap.pk]).first()
	if conflicto_a:
		raise ValidationError({
			"swap": (
				f"Ya tienes otra asignacion ({conflicto_a.horario.sala.codigo} "
				f"{conflicto_a.horario.hora_inicio}-{conflicto_a.horario.hora_fin}) "
				f"que se cruza con el horario de la opcion."
			)
		})

	conflicto_b = Asignacion.objects.filter(
		monitor_id=monitor_b.pk,
		semestre_id=asignacion_original.semestre_id,
		horario__dia_semana=asignacion_original.horario.dia_semana,
		horario__hora_inicio__lt=asignacion_original.horario.hora_fin,
		horario__hora_fin__gt=asignacion_original.horario.hora_inicio,
	).exclude(pk__in=[asignacion_original.pk, asignacion_swap.pk]).first()
	if conflicto_b:
		raise ValidationError({
			"swap": (
				f"El monitor candidato ({monitor_b.email}) ya tiene otra "
				f"asignacion ({conflicto_b.horario.sala.codigo} "
				f"{conflicto_b.horario.hora_inicio}-{conflicto_b.horario.hora_fin}) "
				f"que se cruza con tu horario. Elige otra opcion."
			)
		})

	# SWAP ATOMICO: ejecutar todo en una transaccion para que sea consistente
	with transaction.atomic():
		# Mutamos las dos asignaciones con save(validate=False) para evitar
		# que full_clean() de Asignacion detecte falso positivo durante el
		# estado intermedio (un monitor con 2 asignaciones).
		asignacion_original.monitor = monitor_b
		asignacion_original.save(validate=False)

		asignacion_swap.monitor = monitor_a
		asignacion_swap.save(validate=False)

		# Marca la opcion como aceptada (ganadora) y descarta el resto
		OpcionCambio.objects.filter(pk=opcion.pk).update(
			estado_candidato=OpcionCambio.EST_ACEPTADA,
			seleccionada=True,
			fecha_decision_candidato=now(),
		)
		solicitud.opciones.exclude(pk=opcion.pk).filter(
			estado_candidato__in=[OpcionCambio.EST_PENDIENTE, OpcionCambio.EST_ELEGIDA]
		).update(estado_candidato=OpcionCambio.EST_DESCARTADA)

		# Cierra la solicitud
		solicitud.monitor_reemplazo = monitor_b
		solicitud.estado = target_state
		solicitud.fecha_respuesta = now()
		solicitud.save(validate=False)

	return solicitud


# ===========================================================================
# 4a) Candidato acepta -> swap atomico ejecutado
# ===========================================================================

def aceptar_como_candidato(*, solicitud: SolicitudCambio, candidato) -> SolicitudCambio:
	"""Candidato confirma el swap propuesto.

	Transicion: ESPERANDO_CANDIDATO --(candidato_acepta, candidato)--> APROBADA

	Encuentra la opcion en estado ELEGIDA, valida que `candidato` sea el
	monitor de esa opcion, ejecuta el swap atomico y cierra la solicitud.

	Args:
		solicitud: Solicitud en estado ESPERANDO_CANDIDATO.
		candidato: Usuario candidato propuesto (debe coincidir con
			opcion.candidato_id de la opcion elegida).

	Returns:
		La solicitud actualizada con estado APROBADA, monitor_reemplazo
		registrado, y las asignaciones intercambiadas.

	Raises:
		ValidationError: Si la transicion no es valida, si no hay opcion
			elegida, o si el actor no es el candidato de esa opcion.
	"""
	# Busca la opcion elegida
	opcion = solicitud.opciones.filter(estado_candidato=OpcionCambio.EST_ELEGIDA).first()
	if not opcion:
		raise ValidationError({
			"opcion": "No hay opcion elegida pendiente de confirmacion."
		})

	target_state = assert_transition(
		solicitud, "candidato_acepta", actor=candidato, candidato_id=opcion.candidato_id,
	)

	asignacion_original = solicitud.asignacion
	asignacion_swap     = opcion.asignacion_swap
	monitor_a = solicitud.solicitante
	monitor_b = opcion.candidato  # snapshot del candidato original

	# Re-validar conflictos por si algo cambio entre choose y accept
	# (otro swap completado mientras esperabamos, etc.)
	conflicto_a = Asignacion.objects.filter(
		monitor_id=monitor_a.pk,
		semestre_id=asignacion_swap.semestre_id,
		horario__dia_semana=asignacion_swap.horario.dia_semana,
		horario__hora_inicio__lt=asignacion_swap.horario.hora_fin,
		horario__hora_fin__gt=asignacion_swap.horario.hora_inicio,
	).exclude(pk__in=[asignacion_original.pk, asignacion_swap.pk]).first()
	if conflicto_a:
		raise ValidationError({
			"swap": (
				f"El solicitante ya tiene otra asignacion ({conflicto_a.horario.sala.codigo} "
				f"{conflicto_a.horario.hora_inicio}-{conflicto_a.horario.hora_fin}) "
				f"que se cruza. El swap ya no es posible."
			)
		})

	conflicto_b = Asignacion.objects.filter(
		monitor_id=monitor_b.pk,
		semestre_id=asignacion_original.semestre_id,
		horario__dia_semana=asignacion_original.horario.dia_semana,
		horario__hora_inicio__lt=asignacion_original.horario.hora_fin,
		horario__hora_fin__gt=asignacion_original.horario.hora_inicio,
	).exclude(pk__in=[asignacion_original.pk, asignacion_swap.pk]).first()
	if conflicto_b:
		raise ValidationError({
			"swap": (
				f"Tienes otra asignacion ({conflicto_b.horario.sala.codigo} "
				f"{conflicto_b.horario.hora_inicio}-{conflicto_b.horario.hora_fin}) "
				f"que se cruza con el horario del solicitante. El swap no es posible."
			)
		})

	# Re-validar que monitor_b sigue siendo dueno de asignacion_swap
	# (podria haber cambiado por otro swap concurrente)
	asignacion_swap.refresh_from_db()
	if asignacion_swap.monitor_id != monitor_b.pk:
		raise ValidationError({
			"swap": "El horario propuesto ya no pertenece al candidato original."
		})

	with transaction.atomic():
		# Swap atomico saltando full_clean (las pre-validaciones lo garantizan)
		asignacion_original.monitor = monitor_b
		asignacion_original.save(validate=False)

		asignacion_swap.monitor = monitor_a
		asignacion_swap.save(validate=False)

		# Marca opcion como aceptada y ganadora
		OpcionCambio.objects.filter(pk=opcion.pk).update(
			estado_candidato=OpcionCambio.EST_ACEPTADA,
			seleccionada=True,
			fecha_decision_candidato=now(),
		)
		# Las opciones restantes que aun estaban pendientes/elegidas quedan descartadas
		solicitud.opciones.exclude(pk=opcion.pk).filter(
			estado_candidato__in=[OpcionCambio.EST_PENDIENTE, OpcionCambio.EST_ELEGIDA]
		).update(estado_candidato=OpcionCambio.EST_DESCARTADA)

		# Cierra la solicitud
		solicitud.monitor_reemplazo = monitor_b
		solicitud.estado = target_state
		solicitud.fecha_respuesta = now()
		solicitud.save(validate=False)

	return solicitud


# ===========================================================================
# 4b) Candidato rechaza -> solicitud vuelve a CON_PROPUESTAS o RECHAZADA
# ===========================================================================

def rechazar_como_candidato(*, solicitud: SolicitudCambio, candidato, motivo: str = "") -> SolicitudCambio:
	"""Candidato declina el swap propuesto.

	Transicion: ESPERANDO_CANDIDATO --(candidato_rechaza, candidato)--> CON_PROPUESTAS

	La opcion queda marcada como RECHAZADA por candidato. La solicitud vuelve
	a CON_PROPUESTAS para que el solicitante pueda elegir otra de las opciones
	restantes. Si no quedan opciones disponibles, la solicitud transita
	automaticamente a RECHAZADA.

	Args:
		solicitud: Solicitud en estado ESPERANDO_CANDIDATO.
		candidato: Usuario candidato propuesto que esta rechazando.
		motivo: Razon opcional del rechazo (se guarda en solicitud.respuesta).

	Returns:
		La solicitud actualizada en CON_PROPUESTAS o RECHAZADA.
	"""
	opcion = solicitud.opciones.filter(estado_candidato=OpcionCambio.EST_ELEGIDA).first()
	if not opcion:
		raise ValidationError({
			"opcion": "No hay opcion elegida pendiente de confirmacion."
		})

	# Valida la transicion (target = CON_PROPUESTAS)
	assert_transition(
		solicitud, "candidato_rechaza", actor=candidato, candidato_id=opcion.candidato_id,
	)

	with transaction.atomic():
		# Marca la opcion como rechazada por el candidato
		OpcionCambio.objects.filter(pk=opcion.pk).update(
			estado_candidato=OpcionCambio.EST_RECHAZADA,
			fecha_decision_candidato=now(),
		)

		# Cuenta opciones aun disponibles (pendientes que el solicitante podria elegir)
		quedan_opciones = solicitud.opciones.filter(
			estado_candidato=OpcionCambio.EST_PENDIENTE
		).exists()

		if quedan_opciones:
			# Vuelve a CON_PROPUESTAS para que solicitante elija otra
			solicitud.estado = SolicitudCambio.CON_PROPUESTAS
			# Acumula motivo del rechazo en respuesta
			if motivo:
				prev = solicitud.respuesta or ""
				solicitud.respuesta = (
					f"{prev}\n[Candidato {candidato.email} rechazo opcion {opcion.orden}]: {motivo}"
				).strip()
			solicitud.save(validate=False)
		else:
			# Sin opciones disponibles: solicitud queda RECHAZADA
			solicitud.estado = SolicitudCambio.RECHAZADA
			solicitud.fecha_respuesta = now()
			if motivo:
				prev = solicitud.respuesta or ""
				solicitud.respuesta = (
					f"{prev}\n[Candidato {candidato.email} rechazo opcion {opcion.orden} - sin alternativas]: {motivo}"
				).strip()
			else:
				solicitud.respuesta = (
					(solicitud.respuesta or "") +
					"\n[Sin opciones disponibles: todos los candidatos rechazaron el swap]"
				).strip()
			solicitud.save(validate=False)

	return solicitud


# ===========================================================================
# 5) Admin rechaza la solicitud en cualquier estado no-terminal
# ===========================================================================

def rechazar_solicitud(*, solicitud: SolicitudCambio, admin, respuesta=None) -> SolicitudCambio:
	"""Admin rechaza la solicitud en cualquier estado no terminal.

	Transicion: PENDIENTE | CON_PROPUESTAS | ESPERANDO_CANDIDATO
	            --(reject, admin)--> RECHAZADA

	Args:
		solicitud: Solicitud no terminal.
		admin: Administrador que rechaza.
		respuesta: Mensaje opcional.

	Returns:
		La solicitud actualizada en RECHAZADA.
	"""
	target_state = assert_transition(solicitud, "reject", actor=admin)

	with transaction.atomic():
		# Marca todas las opciones aun en juego como descartadas
		solicitud.opciones.filter(
			estado_candidato__in=[
				OpcionCambio.EST_PENDIENTE,
				OpcionCambio.EST_ELEGIDA,
			]
		).update(estado_candidato=OpcionCambio.EST_DESCARTADA)

		solicitud.estado = target_state
		solicitud.respondido_por = admin
		solicitud.respuesta = respuesta or ""
		solicitud.fecha_respuesta = now()
		solicitud.save(validate=False)

	return solicitud


# ===========================================================================
# Deprecated - mantenido para no romper imports antiguos
# ===========================================================================

def aprobar_solicitud(*, solicitud: SolicitudCambio, admin, monitor_reemplazo=None, respuesta=None) -> SolicitudCambio:
	"""DEPRECATED: usar proponer_opciones() + elegir_opcion() + aceptar_como_candidato()."""
	raise ValidationError(
		"Aprobacion directa deshabilitada. El admin debe proponer opciones, "
		"el solicitante elegir una y el candidato confirmar el swap."
	)
