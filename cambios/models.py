from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.constraints import UniqueConstraint
from django.utils.timezone import now


class SolicitudCambio(models.Model):
	"""Solicitud de cambio de turno entre monitores (RF-06 / RF-07).

	- El solicitante (monitor dueño de la asignación) indica que no podrá
	  asistir a su turno y propone a otro monitor (reemplazo) para que
	  cubra dicho espacio temporal.
	- El sistema mantiene trazabilidad y el administrador aprueba o rechaza.
	"""

	PENDIENTE = "pendiente"
	CON_PROPUESTAS = "con_propuestas"
	ESPERANDO_CANDIDATO = "esperando_candidato"
	APROBADA = "aprobada"
	RECHAZADA = "rechazada"

	TIPO_CAMBIO_TURNO = "cambio_turno"
	TIPO_CHOICES = [
		(TIPO_CAMBIO_TURNO, "Cambio de turno (Monitor Reemplazo)"),
	]

	ESTADO_CHOICES = [
		(PENDIENTE, "Pendiente"),
		(CON_PROPUESTAS, "Con propuestas"),
		(ESPERANDO_CANDIDATO, "Esperando confirmacion del candidato"),
		(APROBADA, "Aprobada"),
		(RECHAZADA, "Rechazada"),
	]

	id_cambio = models.AutoField(primary_key=True)
	asignacion = models.ForeignKey(
		"asignaciones.Asignacion",
		on_delete=models.CASCADE,
		related_name="solicitudes",
	)
	# Monitor que solicita el cambio (debe ser dueño de la asignación)
	solicitante = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.PROTECT,
		related_name="solicitudes_cambio",
	)
	# Monitor que cubrirá el turno. Nullable: el monitor solicita sin elegir
	# reemplazo; el admin asigna al aprobar (los monitores no tienen acceso a
	# la lista completa de usuarios para elegir).
	monitor_reemplazo = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.PROTECT,
		null=True,
		blank=True,
		related_name="solicitudes_reemplazo",
	)
	# Para extensibilidad futura: tipo de solicitud (por ahora solo cambio_turno)
	tipo = models.CharField(max_length=32, choices=TIPO_CHOICES)
	# Motivo del cambio
	motivo = models.TextField(blank=True)
	# Estado de la solicitud
	estado = models.CharField(max_length=16, choices=ESTADO_CHOICES, default=PENDIENTE)
	# Respuesta del administrador
	respuesta = models.TextField(blank=True)
	# Administrador que respondió
	respondido_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.PROTECT,
		related_name="respuestas_solicitud",
	)
	# Fecha de creación (timestamp del sistema, RF-06 elemento 4)
	fecha_creacion = models.DateTimeField(auto_now_add=True)
	# Fecha de respuesta (se establece automáticamente al cambiar estado)
	fecha_respuesta = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ["-fecha_creacion"]
		constraints = [
			UniqueConstraint(
				fields=["asignacion"],
				condition=Q(estado="pendiente"),
				name="unique_pending_solicitud_per_asignacion",
			),
		]

	def clean(self):
		# 1. El solicitante debe ser el dueño de la asignación (solo al crear)
		if self.estado == self.PENDIENTE and self.asignacion and self.solicitante_id and self.asignacion.monitor_id != self.solicitante_id:
			raise ValidationError({
				"solicitante": "El solicitante debe ser el monitor asignado a esta asignación."
			})

		# 2. El reemplazo no puede ser el mismo que el solicitante (RF-06, solo al crear)
		if self.estado == self.PENDIENTE and self.monitor_reemplazo_id and self.solicitante_id and self.monitor_reemplazo_id == self.solicitante_id:
			raise ValidationError({
				"monitor_reemplazo": "El monitor de reemplazo no puede ser el mismo que el solicitante."
			})

		# 3. El reemplazo debe tener rol "monitor" (solo al crear)
		if self.estado == self.PENDIENTE and self.monitor_reemplazo:
			rol = getattr(self.monitor_reemplazo, "rol", None)
			if rol and rol != "monitor":
				raise ValidationError({
					"monitor_reemplazo": "El reemplazo debe tener rol Monitor."
				})

		# 4. Validar que el reemplazo tenga disponibilidad en el horario (solo al crear)
		if self.estado == self.PENDIENTE and self.asignacion and self.monitor_reemplazo:
			from asignaciones.models import Asignacion
			conflicto = Asignacion.objects.filter(
				monitor_id=self.monitor_reemplazo_id,
				semestre_id=self.asignacion.semestre_id,
				horario__dia_semana=self.asignacion.horario.dia_semana,
				horario__hora_inicio__lt=self.asignacion.horario.hora_fin,
				horario__hora_fin__gt=self.asignacion.horario.hora_inicio,
			).exists()
			if conflicto:
				raise ValidationError({
					"monitor_reemplazo": "El monitor de reemplazo ya tiene una asignación que se cruza con este horario."
				})

		# 5. Una sola solicitud pendiente por asignación
		if self.asignacion and self.estado == self.PENDIENTE:
			qs = SolicitudCambio.objects.filter(
				asignacion=self.asignacion,
				estado=self.PENDIENTE,
			)
			if self.pk:
				qs = qs.exclude(pk=self.pk)
			if qs.exists():
				raise ValidationError("Ya existe una solicitud pendiente para esta asignación.")

	def save(self, *args, validate=True, **kwargs):
		if validate:
			self.full_clean()
		# Actualizar fecha_respuesta si cambia el estado de PENDIENTE -> APROBADA/RECHAZADA
		if self.estado != self.PENDIENTE and not self.fecha_respuesta:
			self.fecha_respuesta = now()
		super().save(*args, **kwargs)

	def __str__(self):
		return f"Solicitud de cambio ({self.asignacion}) - {self.estado}"


class OpcionCambio(models.Model):
	"""Opcion de SWAP propuesta por el admin para una solicitud de cambio.

	Ciclo de vida de una opcion (campo `estado_candidato`):
		PENDIENTE       - admin la propuso pero el solicitante aun no la elige
		ELEGIDA         - solicitante la eligio, candidato debe confirmar
		ACEPTADA        - candidato acepto, swap se ejecuto (queda como ganadora)
		RECHAZADA       - candidato rechazo, solicitante puede elegir otra
		DESCARTADA      - no fue elegida (otra opcion gano o solicitud rechazada)

	El campo `seleccionada` es alias historico de `estado_candidato == ACEPTADA`
	(la opcion ganadora). Se mantiene por backward compat de la constraint.
	"""

	# Estados de la opcion frente al candidato
	EST_PENDIENTE  = "pendiente"
	EST_ELEGIDA    = "elegida"
	EST_ACEPTADA   = "aceptada"
	EST_RECHAZADA  = "rechazada"
	EST_DESCARTADA = "descartada"
	ESTADO_CANDIDATO_CHOICES = [
		(EST_PENDIENTE,  "Pendiente"),
		(EST_ELEGIDA,    "Elegida por solicitante"),
		(EST_ACEPTADA,   "Aceptada por candidato"),
		(EST_RECHAZADA,  "Rechazada por candidato"),
		(EST_DESCARTADA, "Descartada"),
	]

	id_opcion = models.AutoField(primary_key=True)
	solicitud = models.ForeignKey(
		SolicitudCambio,
		on_delete=models.CASCADE,
		related_name="opciones",
	)
	# La asignacion del OTRO monitor que se ofrece para swap
	asignacion_swap = models.ForeignKey(
		"asignaciones.Asignacion",
		on_delete=models.CASCADE,
		related_name="opciones_swap",
	)
	# Snapshot del candidato al momento de proponer la opcion. Si la asignacion_swap
	# cambia de dueno antes de la decision, este campo conserva el candidato original.
	candidato = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.PROTECT,
		related_name="opciones_como_candidato",
		null=True,
		blank=True,
	)
	# Orden de presentacion (1, 2, 3...)
	orden = models.PositiveSmallIntegerField(default=1)
	# Estado de la opcion frente al candidato (ver ciclo de vida arriba)
	estado_candidato = models.CharField(
		max_length=16,
		choices=ESTADO_CANDIDATO_CHOICES,
		default=EST_PENDIENTE,
	)
	# Marcador historico: True cuando la opcion fue aceptada (ganadora del swap).
	# Solo una opcion por solicitud puede tener seleccionada=True.
	seleccionada = models.BooleanField(default=False)
	fecha_creacion = models.DateTimeField(auto_now_add=True)
	fecha_decision_candidato = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ["solicitud", "orden"]
		constraints = [
			# No se puede ofrecer la misma asignacion dos veces en la misma solicitud
			UniqueConstraint(
				fields=["solicitud", "asignacion_swap"],
				name="unique_asignacion_swap_per_solicitud",
			),
			# Solo una opcion seleccionada (ganadora) por solicitud
			UniqueConstraint(
				fields=["solicitud"],
				condition=Q(seleccionada=True),
				name="unique_selected_opcion_per_solicitud",
			),
		]

	def clean(self):
		"""Valida la opcion al CREARLA (no en updates).

		Las validaciones del swap (mismo semestre, otro monitor, no misma asignacion)
		solo aplican antes de que el swap se ejecute. Una vez que la opcion fue
		aceptada/rechazada el snapshot puede cambiar y las validaciones no aplican.
		"""
		# Skip validaciones si la opcion ya tiene una decision (post-swap el state
		# de asignacion_swap ya no representa el snapshot original)
		if self.estado_candidato in (self.EST_ACEPTADA, self.EST_RECHAZADA):
			return

		if self.solicitud_id and self.asignacion_swap_id:
			if self.solicitud.asignacion_id == self.asignacion_swap_id:
				raise ValidationError({
					"asignacion_swap": "La opcion no puede ser la misma asignacion del solicitante."
				})
			if self.asignacion_swap.monitor_id == self.solicitud.solicitante_id:
				raise ValidationError({
					"asignacion_swap": "El swap debe ser con la asignacion de otro monitor."
				})
			if self.asignacion_swap.semestre_id != self.solicitud.asignacion.semestre_id:
				raise ValidationError({
					"asignacion_swap": "Las asignaciones deben ser del mismo semestre."
				})

	def save(self, *args, validate=True, **kwargs):
		if validate:
			self.full_clean()
		# Snapshot del candidato al primer save (cuando la opcion se crea)
		if not self.pk and self.candidato_id is None and self.asignacion_swap_id:
			self.candidato_id = self.asignacion_swap.monitor_id
		super().save(*args, **kwargs)

	def __str__(self):
		return f"Opcion {self.orden} para solicitud {self.solicitud_id}"


