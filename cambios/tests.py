from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.timezone import now

from asignaciones.models import Asignacion
from cambios.models import SolicitudCambio
from cambios.services import aprobar_solicitud, crear_solicitud_cambio, rechazar_solicitud
from horarios.models import Horario
from salas.models import Sala
from semestres.models import Semestre

Usuario = get_user_model()


class SolicitudCambioModelTests(TestCase):
	"""Tests para el modelo SolicitudCambio y su lógica de validación."""

	@classmethod
	def setUpTestData(cls):
		cls.sala = Sala.objects.create(codigo="SALA-101", nombre="Laboratorio 101", capacidad=40)
		cls.semestre = Semestre.objects.create(anio=2025, periodo=1, activo=True)
		cls.horario = Horario.objects.create(
			sala=cls.sala,
			dia_semana=1,
			hora_inicio="08:00",
			hora_fin="10:00",
		)
		cls.monitor1 = Usuario.objects.create_user(
			username="mon1",
			email="mo1@test.com",
			password="pass1234",
			rol="monitor",
			cedula="111111"
		)
		cls.monitor2 = Usuario.objects.create_user(
			username="mon2",
			email="mo2@test.com",
			password="pass1234",
			rol="monitor",
			cedula="222222"
		)
		cls.admin = Usuario.objects.create_user(
			username="admin1",
			email="admin@test.com",
			password="pass1234",
			rol="admin",
			cedula="333333"
		)
		cls.asignacion = Asignacion.objects.create(
			monitor=cls.monitor1,
			horario=cls.horario,
			semestre=cls.semestre,
		)

	def test_solicitud_valida(self):
		"""Creación exitosa de una solicitud válida."""
		solicitud = SolicitudCambio(
			asignacion=self.asignacion,
			solicitante=self.monitor1,
			monitor_reemplazo=self.monitor2,
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		)
		solicitud.save()
		self.assertEqual(solicitud.estado, SolicitudCambio.PENDIENTE)

	def test_solicitante_es_dueno(self):
		"""Bloquear si el solicitante no es el dueño de la asignación."""
		solicitud = SolicitudCambio(
			asignacion=self.asignacion,
			solicitante=self.monitor2,  # monitor que NO es dueño
			monitor_reemplazo=self.monitor1,
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		)
		with self.assertRaises(ValidationError) as context:
			solicitud.save()
		selfInContext = "El solicitante debe ser el monitor asignado" in str(context.exception.message_dict.get("solicitante", ""))
		self.assertTrue(selfInContext)

	def test_solicitante_distinto_reemplazo(self):
		"""Bloquear si el reemplazo es el mismo que el solicitante."""
		solicitud = SolicitudCambio(
			asignacion=self.asignacion,
			solicitante=self.monitor1,
			monitor_reemplazo=self.monitor1,  # Mismo solicitante
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		)
		with self.assertRaises(ValidationError) as context:
			solicitud.save()
		selfInContext = "mismo que el solicitante" in str(context.exception.message_dict.get("monitor_reemplazo", ""))
		self.assertTrue(selfInContext)

	def test_reemplazo_rol_monitor(self):
		"""Bloquear si el reemplazo no tiene rol monitor."""
		solicitud = SolicitudCambio(
			asignacion=self.asignacion,
			solicitante=self.monitor1,
			monitor_reemplazo=self.admin,  # admin, no monitor
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		)
		with self.assertRaises(ValidationError) as context:
			solicitud.save()
		selfInContext = "debe tener rol Monitor" in str(context.exception.message_dict.get("monitor_reemplazo", ""))
		self.assertTrue(selfInContext)

	def test_reemplazo_sin_conflicto(self):
		"""Bloquear si el reemplazo tiene conflicto de horario."""
		# Crear otra sala con un horario conflictivo para monitor2
		sala2 = Sala.objects.create(codigo="SALA-102", nombre="Otra Sala", capacidad=40)
		horario2 = Horario.objects.create(
			sala=sala2,
			dia_semana=1,
			hora_inicio="10:00",
			hora_fin="12:00",
		)
		horario_conflictivo = Horario.objects.create(
			sala=sala2,
			dia_semana=1,
			hora_inicio="11:00",
			hora_fin="13:00",
		)
		Asignacion.objects.create(
			monitor=self.monitor2,
			horario=horario_conflictivo,
			semestre=self.semestre,
		)
		asignacion2 = Asignacion.objects.create(
			monitor=self.monitor1,
			horario=horario2,
			semestre=self.semestre,
		)
		solicitud = SolicitudCambio(
			asignacion=asignacion2,
			solicitante=self.monitor1,
			monitor_reemplazo=self.monitor2,
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		)
		with self.assertRaises(ValidationError) as context:
			solicitud.save()
		selfInContext = "ya tiene una asignación que se cruza" in str(context.exception.message_dict.get("monitor_reemplazo", ""))
		self.assertTrue(selfInContext)

	def test_solicitud_unica_pendiente(self):
		"""Bloquear si hay una solicitud pendiente para la misma asignación."""
		SolicitudCambio(
			asignacion=self.asignacion,
			solicitante=self.monitor1,
			monitor_reemplazo=self.monitor2,
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		).save()

		solicitud2 = SolicitudCambio(
			asignacion=self.asignacion,
			solicitante=self.monitor1,
			monitor_reemplazo=self.monitor2,
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		)
		with self.assertRaises(ValidationError) as context:
			solicitud2.save()
		selfInContext = "Ya existe una solicitud pendiente" in str(context.exception)
		self.assertTrue(selfInContext)


class SolicitudCambioServiceTests(TestCase):
	"""Tests para la lógica de negocio (services.py)."""

	@classmethod
	def setUpTestData(cls):
		cls.sala = Sala.objects.create(codigo="SALA-101", nombre="Laboratorio 101", capacidad=40)
		cls.semestre = Semestre.objects.create(anio=2025, periodo=1, activo=True)
		cls.horario = Horario.objects.create(
			sala=cls.sala,
			dia_semana=1,
			hora_inicio="08:00",
			hora_fin="10:00",
		)
		cls.monitor1 = Usuario.objects.create_user(
			username="mon1",
			email="mo1@test.com",
			password="pass1234",
			rol="monitor",
			cedula="111111"
		)
		cls.monitor2 = Usuario.objects.create_user(
			username="mon2",
			email="mo2@test.com",
			password="pass1234",
			rol="monitor",
			cedula="222222"
		)
		cls.admin = Usuario.objects.create_user(
			username="admin1",
			email="admin@test.com",
			password="pass1234",
			rol="admin",
			cedula="333333"
		)
		cls.asignacion = Asignacion.objects.create(
			monitor=cls.monitor1,
			horario=cls.horario,
			semestre=cls.semestre,
		)

	def test_crear_solicitud(self):
		solicitud = crear_solicitud_cambio(
			asignacion=self.asignacion,
			solicitante=self.monitor1,
			monitor_reemplazo=self.monitor2,
		)
		self.assertEqual(solicitud.estado, SolicitudCambio.PENDIENTE)

	def test_aprobar_solicitud(self):
		solicitud = SolicitudCambio(
			asignacion=self.asignacion,
			solicitante=self.monitor1,
			monitor_reemplazo=self.monitor2,
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		)
		solicitud.save()

		aprobar_solicitud(
			solicitud=solicitud,
			admin=self.admin,
			respuesta="Aprobado, cubre tu turno.",
		)
		solicitud.refresh_from_db()
		self.asignacion.refresh_from_db()
		self.assertEqual(solicitud.estado, SolicitudCambio.APROBADA)
		self.assertEqual(solicitud.respondido_por, self.admin)
		self.assertIsNotNone(solicitud.fecha_respuesta)
		# Verificar que la asignación se actualizó al monitor de reemplazo
		self.assertEqual(self.asignacion.monitor, self.monitor2)

	def test_rechazar_solicitud(self):
		solicitud = SolicitudCambio(
			asignacion=self.asignacion,
			solicitante=self.monitor1,
			monitor_reemplazo=self.monitor2,
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
		)
		solicitud.save()

		rechazar_solicitud(
			solicitud=solicitud,
			admin=self.admin,
			respuesta="No hay disponibilidad.",
		)
		solicitud.refresh_from_db()
		self.assertEqual(solicitud.estado, SolicitudCambio.RECHAZADA)
		self.assertEqual(solicitud.respondido_por, self.admin)

	def test_no_reaprobar(self):
		"""No se puede aprobar o rechazar una solicitud ya respondida."""
		solicitud = SolicitudCambio(
			asignacion=self.asignacion,
			solicitante=self.monitor1,
			monitor_reemplazo=self.monitor2,
			tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
			estado=SolicitudCambio.APROBADA,
		)
		solicitud.save()

		with self.assertRaises(ValidationError):
			aprobar_solicitud(solicitud=solicitud, admin=self.admin)
