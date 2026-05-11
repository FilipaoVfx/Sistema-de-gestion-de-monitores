from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from horarios.models import Horario
from salas.models import Sala
from semestres.models import Semestre
from usuarios.models import Usuario

from .models import Asignacion
from .services import crear_asignaciones


class CrearAsignacionesServiceTests(TestCase):
	def _crear_usuario(self, *, email: str, rol: str, cedula: str) -> Usuario:
		return Usuario.objects.create_user(
			username=email,
			email=email,
			password="testpass123",
			cedula=cedula,
			rol=rol,
			first_name="Test",
			last_name="User",
		)

	def _crear_sala(self, *, codigo: str) -> Sala:
		return Sala.objects.create(codigo=codigo, nombre=f"{codigo} Nombre", capacidad=30)

	def _crear_semestre(self, *, anio: int = 2026, periodo: int = 1, activo: bool = True) -> Semestre:
		return Semestre.objects.create(anio=anio, periodo=periodo, activo=activo)

	def test_crea_horario_y_asignacion_desde_bloque_nuevo(self):
		sala = self._crear_sala(codigo="SALA-101")
		semestre = self._crear_semestre()
		monitor = self._crear_usuario(email="monitor1@uni.edu", rol=Usuario.MONITOR, cedula="1001")

		creadas = crear_asignaciones(
			monitor=monitor,
			semestre=semestre,
			sala_id=sala.id_sala,
			seleccion_tokens=["n:1|08:00|10:00"],
		)

		self.assertEqual(creadas, 1)
		self.assertEqual(Horario.objects.count(), 1)
		self.assertEqual(Asignacion.objects.count(), 1)
		asignacion = Asignacion.objects.select_related("horario", "monitor", "semestre").get()
		self.assertEqual(asignacion.monitor_id, monitor.id)
		self.assertEqual(asignacion.semestre_id, semestre.id_semestre)
		self.assertEqual(asignacion.horario.sala_id, sala.id_sala)
		self.assertEqual(asignacion.horario.dia_semana, 1)
		self.assertEqual(asignacion.horario.hora_inicio, time(8, 0))
		self.assertEqual(asignacion.horario.hora_fin, time(10, 0))

	def test_falla_si_horario_existente_no_pertenece_a_la_sala(self):
		sala_1 = self._crear_sala(codigo="SALA-101")
		sala_2 = self._crear_sala(codigo="SALA-102")
		semestre = self._crear_semestre()
		monitor = self._crear_usuario(email="monitor1@uni.edu", rol=Usuario.MONITOR, cedula="1001")

		h = Horario.objects.create(
			sala=sala_1,
			dia_semana=1,
			hora_inicio=time(8, 0),
			hora_fin=time(10, 0),
		)

		with self.assertRaises(ValidationError) as ctx:
			crear_asignaciones(
				monitor=monitor,
				semestre=semestre,
				sala_id=sala_2.id_sala,
				seleccion_tokens=[f"h:{h.id_horario}"],
			)

		self.assertIn("no pertenecen", " ".join(ctx.exception.messages).lower())
		self.assertEqual(Asignacion.objects.count(), 0)
		self.assertEqual(Horario.objects.count(), 1)

	def test_falla_si_bloque_ya_esta_ocupado_en_el_semestre(self):
		sala = self._crear_sala(codigo="SALA-101")
		semestre = self._crear_semestre()
		monitor_1 = self._crear_usuario(email="monitor1@uni.edu", rol=Usuario.MONITOR, cedula="1001")
		monitor_2 = self._crear_usuario(email="monitor2@uni.edu", rol=Usuario.MONITOR, cedula="1002")

		h = Horario.objects.create(
			sala=sala,
			dia_semana=1,
			hora_inicio=time(8, 0),
			hora_fin=time(10, 0),
		)
		Asignacion.objects.create(monitor=monitor_1, horario=h, semestre=semestre)

		with self.assertRaises(ValidationError) as ctx:
			crear_asignaciones(
				monitor=monitor_2,
				semestre=semestre,
				sala_id=sala.id_sala,
				seleccion_tokens=[f"h:{h.id_horario}"],
			)

		self.assertIn("ocupad", " ".join(ctx.exception.messages).lower())
		self.assertEqual(Asignacion.objects.count(), 1)

	def test_rollback_no_deja_horarios_si_falla_por_conflicto_de_monitor(self):
		sala_1 = self._crear_sala(codigo="SALA-101")
		sala_2 = self._crear_sala(codigo="SALA-102")
		semestre = self._crear_semestre()
		monitor = self._crear_usuario(email="monitor1@uni.edu", rol=Usuario.MONITOR, cedula="1001")

		h1 = Horario.objects.create(
			sala=sala_1,
			dia_semana=1,
			hora_inicio=time(8, 0),
			hora_fin=time(10, 0),
		)
		Asignacion.objects.create(monitor=monitor, horario=h1, semestre=semestre)
		self.assertEqual(Horario.objects.count(), 1)
		self.assertEqual(Asignacion.objects.count(), 1)

		# Intentar asignar el mismo monitor a un bloque que se cruza (09:00-11:00) en otra sala.
		with self.assertRaises(ValidationError) as ctx:
			crear_asignaciones(
				monitor=monitor,
				semestre=semestre,
				sala_id=sala_2.id_sala,
				seleccion_tokens=["n:1|09:00|11:00"],
			)

		self.assertIn("cruza", " ".join(ctx.exception.messages).lower())
		# Debe permanecer todo igual (sin horario nuevo ni asignación nueva)
		self.assertEqual(Horario.objects.count(), 1)
		self.assertEqual(Asignacion.objects.count(), 1)
