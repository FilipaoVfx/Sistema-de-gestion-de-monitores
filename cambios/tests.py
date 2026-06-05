"""Tests para el flujo completo de SolicitudCambio (swap mixto).

Cubre 3 capas:
1. ModelTests       - validaciones de SolicitudCambio y OpcionCambio
2. ServiceTests     - lógica de negocio (services.py)
3. ApiTests         - endpoints REST con autenticación JWT

Flujo del swap:
    PENDIENTE  ──admin propone N≥2 opciones──>  CON_PROPUESTAS
                                                       │
       admin                                       monitor elige
       rechaza ──────────> RECHAZADA <──── admin rechaza
                                │                      │
                                │                      ▼
                                └───────────────> APROBADA (swap ejecutado)
"""
from datetime import time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from asignaciones.models import Asignacion
from cambios.models import OpcionCambio, SolicitudCambio
from cambios.services import (
    aprobar_solicitud,
    crear_solicitud_cambio,
    elegir_opcion,
    proponer_opciones,
    rechazar_solicitud,
)
from horarios.models import Horario
from salas.models import Sala
from semestres.models import Semestre

Usuario = get_user_model()


# ---------------------------------------------------------------------------
# Helpers comunes
# ---------------------------------------------------------------------------

def _make_world():
    """Crea el escenario base: salas, semestre, horarios, monitores y admin.

    Layout:
      - SALA_A LAB-A:  Lun 08-10, Mar 10-12
      - SALA_B LAB-B:  Lun 14-16, Mar 08-10
      - 3 monitores (A, B, C) y 1 admin
      - 1 semestre activo 2025-1
      - Asignaciones:
          monitor_a -> LAB-A Lun 08-10
          monitor_b -> LAB-B Lun 14-16
          monitor_c -> LAB-A Mar 10-12
    """
    sala_a = Sala.objects.create(codigo="LAB-A", nombre="Lab A", capacidad=30)
    sala_b = Sala.objects.create(codigo="LAB-B", nombre="Lab B", capacidad=25)
    semestre = Semestre.objects.create(anio=2025, periodo=1, activo=True)

    h_a_lun_8 = Horario.objects.create(sala=sala_a, dia_semana=1, hora_inicio=time(8, 0),  hora_fin=time(10, 0))
    h_a_mar_10 = Horario.objects.create(sala=sala_a, dia_semana=2, hora_inicio=time(10, 0), hora_fin=time(12, 0))
    h_b_lun_14 = Horario.objects.create(sala=sala_b, dia_semana=1, hora_inicio=time(14, 0), hora_fin=time(16, 0))
    h_b_mar_8 = Horario.objects.create(sala=sala_b, dia_semana=2, hora_inicio=time(8, 0),  hora_fin=time(10, 0))

    monitor_a = Usuario.objects.create_user(
        username="mon_a", email="a@test.com", password="pass1234",
        rol="monitor", cedula="A-001",
    )
    monitor_b = Usuario.objects.create_user(
        username="mon_b", email="b@test.com", password="pass1234",
        rol="monitor", cedula="B-002",
    )
    monitor_c = Usuario.objects.create_user(
        username="mon_c", email="c@test.com", password="pass1234",
        rol="monitor", cedula="C-003",
    )
    admin = Usuario.objects.create_user(
        username="admin1", email="admin@test.com", password="pass1234",
        rol="admin", cedula="ADMIN-1",
    )

    asig_a = Asignacion.objects.create(monitor=monitor_a, horario=h_a_lun_8,  semestre=semestre)
    asig_b = Asignacion.objects.create(monitor=monitor_b, horario=h_b_lun_14, semestre=semestre)
    asig_c = Asignacion.objects.create(monitor=monitor_c, horario=h_a_mar_10, semestre=semestre)

    return {
        "semestre":  semestre,
        "salas":     {"a": sala_a, "b": sala_b},
        "horarios":  {
            "a_lun_8":  h_a_lun_8,
            "a_mar_10": h_a_mar_10,
            "b_lun_14": h_b_lun_14,
            "b_mar_8":  h_b_mar_8,
        },
        "monitor_a": monitor_a,
        "monitor_b": monitor_b,
        "monitor_c": monitor_c,
        "admin":     admin,
        "asig_a":    asig_a,
        "asig_b":    asig_b,
        "asig_c":    asig_c,
    }


def _auth(client, user):
    """Autentica el APIClient con un access JWT para el user dado."""
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")


# ===========================================================================
# 1) Model layer
# ===========================================================================

class SolicitudCambioModelTests(TestCase):
    """Validaciones del modelo SolicitudCambio en el nuevo flujo."""

    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def test_solicitud_se_crea_sin_reemplazo(self):
        """Monitor puede crear solicitud SIN definir reemplazo (lo asigna el admin)."""
        s = SolicitudCambio(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            monitor_reemplazo=None,
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
            motivo="No puedo asistir",
        )
        s.save()
        self.assertEqual(s.estado, SolicitudCambio.PENDIENTE)
        self.assertIsNone(s.monitor_reemplazo)

    def test_solicitante_debe_ser_dueno_de_asignacion(self):
        s = SolicitudCambio(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_b"],  # no es el dueno
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        with self.assertRaises(ValidationError) as ctx:
            s.save()
        self.assertIn("solicitante", ctx.exception.message_dict)

    def test_solo_una_solicitud_pendiente_por_asignacion(self):
        SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        s2 = SolicitudCambio(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        with self.assertRaises(ValidationError) as ctx:
            s2.save()
        self.assertIn("Ya existe una solicitud pendiente", str(ctx.exception))


class OpcionCambioModelTests(TestCase):
    """Validaciones del modelo OpcionCambio."""

    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()
        cls.solicitud = SolicitudCambio.objects.create(
            asignacion=cls.w["asig_a"],
            solicitante=cls.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )

    def test_opcion_no_puede_ser_misma_asignacion(self):
        opcion = OpcionCambio(
            solicitud=self.solicitud,
            asignacion_swap=self.w["asig_a"],  # misma del solicitante
            orden=1,
        )
        with self.assertRaises(ValidationError) as ctx:
            opcion.save()
        self.assertIn("asignacion_swap", ctx.exception.message_dict)

    def test_opcion_debe_ser_de_otro_monitor(self):
        """Si la asignacion_swap pertenece al solicitante, falla."""
        # Crea otra asignacion del solicitante en otro horario sin conflicto
        otra_asig = Asignacion.objects.create(
            monitor=self.w["monitor_a"],
            horario=self.w["horarios"]["b_mar_8"],
            semestre=self.w["semestre"],
        )
        opcion = OpcionCambio(
            solicitud=self.solicitud,
            asignacion_swap=otra_asig,
            orden=1,
        )
        with self.assertRaises(ValidationError) as ctx:
            opcion.save()
        self.assertIn("otro monitor", str(ctx.exception.message_dict.get("asignacion_swap", "")))

    def test_opcion_mismo_semestre(self):
        """Si la asignacion_swap es de otro semestre, falla."""
        otro_semestre = Semestre.objects.create(anio=2026, periodo=1, activo=False)
        asig_otro_sem = Asignacion.objects.create(
            monitor=self.w["monitor_b"],
            horario=self.w["horarios"]["b_lun_14"],
            semestre=otro_semestre,
        )
        opcion = OpcionCambio(
            solicitud=self.solicitud,
            asignacion_swap=asig_otro_sem,
            orden=1,
        )
        with self.assertRaises(ValidationError) as ctx:
            opcion.save()
        self.assertIn("mismo semestre", str(ctx.exception.message_dict.get("asignacion_swap", "")))


# ===========================================================================
# 2) Service layer
# ===========================================================================

class CrearSolicitudCambioServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def test_crear_solicitud_sin_reemplazo(self):
        s = crear_solicitud_cambio(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            monitor_reemplazo=None,
            motivo="Cita medica",
        )
        self.assertEqual(s.estado, SolicitudCambio.PENDIENTE)
        self.assertIsNone(s.monitor_reemplazo)
        self.assertEqual(s.motivo, "Cita medica")


class ProponerOpcionesServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def setUp(self):
        # Solicitud nueva por test para que el estado quede en PENDIENTE
        self.solicitud = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )

    def test_proponer_dos_opciones_cambia_estado(self):
        proponer_opciones(
            solicitud=self.solicitud,
            admin=self.w["admin"],
            asignaciones_swap=[self.w["asig_b"], self.w["asig_c"]],
        )
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, SolicitudCambio.CON_PROPUESTAS)
        self.assertEqual(self.solicitud.opciones.count(), 2)
        self.assertEqual(self.solicitud.respondido_por_id, self.w["admin"].pk)

    def test_proponer_requiere_minimo_2_opciones(self):
        with self.assertRaises(ValidationError) as ctx:
            proponer_opciones(
                solicitud=self.solicitud,
                admin=self.w["admin"],
                asignaciones_swap=[self.w["asig_b"]],
            )
        self.assertIn("al menos 2 opciones", str(ctx.exception))

    def test_proponer_no_duplicadas(self):
        with self.assertRaises(ValidationError) as ctx:
            proponer_opciones(
                solicitud=self.solicitud,
                admin=self.w["admin"],
                asignaciones_swap=[self.w["asig_b"], self.w["asig_b"]],
            )
        self.assertIn("no pueden repetirse", str(ctx.exception))

    def test_no_proponer_si_no_esta_pendiente(self):
        # Lleva la solicitud a CON_PROPUESTAS primero
        proponer_opciones(
            solicitud=self.solicitud,
            admin=self.w["admin"],
            asignaciones_swap=[self.w["asig_b"], self.w["asig_c"]],
        )
        with self.assertRaises(ValidationError) as ctx:
            proponer_opciones(
                solicitud=self.solicitud,
                admin=self.w["admin"],
                asignaciones_swap=[self.w["asig_b"], self.w["asig_c"]],
            )
        self.assertIn("no esta en estado pendiente", str(ctx.exception))


class ElegirOpcionServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def setUp(self):
        self.solicitud = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        proponer_opciones(
            solicitud=self.solicitud,
            admin=self.w["admin"],
            asignaciones_swap=[self.w["asig_b"], self.w["asig_c"]],
        )
        self.solicitud.refresh_from_db()
        self.opciones = list(self.solicitud.opciones.order_by("orden"))

    def test_elegir_ejecuta_swap_atomico(self):
        """El monitor solicitante elige opción 1 (swap con monitor_b).

        Antes:
            asig_a: monitor_a -> LAB-A Lun 8-10
            asig_b: monitor_b -> LAB-B Lun 14-16
        Después:
            asig_a: monitor_b -> LAB-A Lun 8-10
            asig_b: monitor_a -> LAB-B Lun 14-16
        """
        opcion_swap_b = self.opciones[0]  # asig_b
        elegir_opcion(
            solicitud=self.solicitud,
            opcion=opcion_swap_b,
            monitor=self.w["monitor_a"],
        )

        # Verifica swap en BD
        asig_a = Asignacion.objects.get(pk=self.w["asig_a"].pk)
        asig_b = Asignacion.objects.get(pk=self.w["asig_b"].pk)
        self.assertEqual(asig_a.monitor_id, self.w["monitor_b"].pk)
        self.assertEqual(asig_b.monitor_id, self.w["monitor_a"].pk)

        # Verifica estado de la solicitud
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, SolicitudCambio.APROBADA)
        self.assertEqual(self.solicitud.monitor_reemplazo_id, self.w["monitor_b"].pk)
        self.assertIsNotNone(self.solicitud.fecha_respuesta)

        # Opcion elegida queda marcada
        opcion_swap_b.refresh_from_db()
        self.assertTrue(opcion_swap_b.seleccionada)

    def test_solo_solicitante_puede_elegir(self):
        with self.assertRaises(ValidationError) as ctx:
            elegir_opcion(
                solicitud=self.solicitud,
                opcion=self.opciones[0],
                monitor=self.w["monitor_b"],  # no es el solicitante
            )
        self.assertIn("Solo el solicitante", str(ctx.exception))

    def test_no_elegir_si_no_esta_con_propuestas(self):
        # Llevamos la solicitud a APROBADA primero
        elegir_opcion(
            solicitud=self.solicitud,
            opcion=self.opciones[0],
            monitor=self.w["monitor_a"],
        )
        self.solicitud.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            elegir_opcion(
                solicitud=self.solicitud,
                opcion=self.opciones[1],
                monitor=self.w["monitor_a"],
            )
        self.assertIn("no esta esperando eleccion", str(ctx.exception))

    def test_detecta_conflicto_de_horario_en_swap(self):
        """Si el solicitante ya tiene otra asignación en el horario destino, no se hace swap."""
        # monitor_a ya tiene asig_a (Lun 8-10). Le creamos otra Mar 10-12.
        otra_asig_a = Asignacion.objects.create(
            monitor=self.w["monitor_a"],
            horario=self.w["horarios"]["b_mar_8"],
            semestre=self.w["semestre"],
        )
        # opciones[1] es asig_c en Mar 10-12, que NO conflicta con otra_asig_a (Mar 8-10).
        # Forzamos conflicto: creamos asig en mismo dia/hora del swap target.
        # Para test simple: hacemos una solicitud y opciones donde A tendría que tomar
        # un horario que ya tiene.
        # Truco: ya cubrimos elegir correctamente arriba; aquí solo aseguramos
        # que la validación de conflicto se ejecute con datos diseñados.
        # asig_c esta en Mar 10-12; si monitor_a tuviera otra asignacion Mar 11-13
        # haria conflicto. La creamos.
        h_conflict = Horario.objects.create(
            sala=self.w["salas"]["b"], dia_semana=2,
            hora_inicio=time(11, 0), hora_fin=time(13, 0),
        )
        Asignacion.objects.create(
            monitor=self.w["monitor_a"], horario=h_conflict, semestre=self.w["semestre"],
        )

        opcion_swap_c = self.opciones[1]  # asig_c en Mar 10-12 -> conflicto con A Mar 11-13
        with self.assertRaises(ValidationError) as ctx:
            elegir_opcion(
                solicitud=self.solicitud,
                opcion=opcion_swap_c,
                monitor=self.w["monitor_a"],
            )
        self.assertIn("se cruza", str(ctx.exception))

        # Cleanup
        otra_asig_a.delete()


class RechazarSolicitudServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def test_rechazar_pendiente(self):
        s = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        result = rechazar_solicitud(solicitud=s, admin=self.w["admin"], respuesta="No procede")
        self.assertEqual(result.estado, SolicitudCambio.RECHAZADA)
        self.assertEqual(result.respondido_por_id, self.w["admin"].pk)
        self.assertEqual(result.respuesta, "No procede")
        self.assertIsNotNone(result.fecha_respuesta)

    def test_no_rechazar_aprobada(self):
        s = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        proponer_opciones(
            solicitud=s, admin=self.w["admin"],
            asignaciones_swap=[self.w["asig_b"], self.w["asig_c"]],
        )
        s.refresh_from_db()
        elegir_opcion(solicitud=s, opcion=s.opciones.first(), monitor=self.w["monitor_a"])
        s.refresh_from_db()

        with self.assertRaises(ValidationError) as ctx:
            rechazar_solicitud(solicitud=s, admin=self.w["admin"])
        self.assertIn("ya fue respondida", str(ctx.exception))


class AprobarDeshabilitadaTests(TestCase):
    """El servicio antiguo aprobar_solicitud está deshabilitado en el nuevo flujo."""

    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def test_aprobar_solicitud_levanta_validation(self):
        s = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        with self.assertRaises(ValidationError) as ctx:
            aprobar_solicitud(solicitud=s, admin=self.w["admin"])
        self.assertIn("deshabilitada", str(ctx.exception))


# ===========================================================================
# 3) API layer (endpoints REST con JWT)
# ===========================================================================

class CrearSolicitudApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def test_monitor_crea_solicitud_para_su_asignacion(self):
        _auth(self.client, self.w["monitor_a"])
        res = self.client.post(
            "/api/cambios/",
            {"asignacion": self.w["asig_a"].pk, "motivo": "Cita medica"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(SolicitudCambio.objects.filter(asignacion=self.w["asig_a"]).exists())

    def test_monitor_no_puede_crear_para_asignacion_ajena(self):
        _auth(self.client, self.w["monitor_a"])
        res = self.client.post(
            "/api/cambios/",
            {"asignacion": self.w["asig_b"].pk, "motivo": "Quiero"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_no_puede_crear_solicitud(self):
        _auth(self.client, self.w["admin"])
        res = self.client.post(
            "/api/cambios/",
            {"asignacion": self.w["asig_a"].pk, "motivo": "Test"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_sin_auth_es_401(self):
        # Sin credentials
        res = self.client.post("/api/cambios/", {"asignacion": self.w["asig_a"].pk}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class ProponerOpcionesApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def setUp(self):
        self.solicitud = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )

    def test_admin_propone_opciones(self):
        _auth(self.client, self.w["admin"])
        res = self.client.post(
            f"/api/cambios/{self.solicitud.id_cambio}/proponer/",
            {"opciones": [self.w["asig_b"].pk, self.w["asig_c"].pk]},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, SolicitudCambio.CON_PROPUESTAS)

    def test_admin_requiere_minimo_2(self):
        _auth(self.client, self.w["admin"])
        res = self.client.post(
            f"/api/cambios/{self.solicitud.id_cambio}/proponer/",
            {"opciones": [self.w["asig_b"].pk]},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_monitor_no_puede_proponer(self):
        _auth(self.client, self.w["monitor_a"])
        res = self.client.post(
            f"/api/cambios/{self.solicitud.id_cambio}/proponer/",
            {"opciones": [self.w["asig_b"].pk, self.w["asig_c"].pk]},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class CandidatosApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()
        cls.solicitud = SolicitudCambio.objects.create(
            asignacion=cls.w["asig_a"],
            solicitante=cls.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )

    def test_admin_ve_candidatos_excluyendo_solicitante(self):
        _auth(self.client, self.w["admin"])
        res = self.client.get(f"/api/cambios/{self.solicitud.id_cambio}/candidatos/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [c["id_asignacion"] for c in res.json()]
        # Debe incluir asig_b y asig_c, no asig_a (del solicitante)
        self.assertIn(self.w["asig_b"].pk, ids)
        self.assertIn(self.w["asig_c"].pk, ids)
        self.assertNotIn(self.w["asig_a"].pk, ids)

    def test_monitor_no_puede_ver_candidatos(self):
        _auth(self.client, self.w["monitor_a"])
        res = self.client.get(f"/api/cambios/{self.solicitud.id_cambio}/candidatos/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class ElegirOpcionApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def setUp(self):
        self.solicitud = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"],
            solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        proponer_opciones(
            solicitud=self.solicitud, admin=self.w["admin"],
            asignaciones_swap=[self.w["asig_b"], self.w["asig_c"]],
        )
        self.solicitud.refresh_from_db()
        self.opcion_b = self.solicitud.opciones.order_by("orden").first()

    def test_solicitante_elige_y_swap_se_ejecuta(self):
        _auth(self.client, self.w["monitor_a"])
        res = self.client.post(
            f"/api/cambios/{self.solicitud.id_cambio}/elegir/",
            {"opcion": self.opcion_b.id_opcion},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Swap verificado en BD
        asig_a = Asignacion.objects.get(pk=self.w["asig_a"].pk)
        asig_b = Asignacion.objects.get(pk=self.w["asig_b"].pk)
        self.assertEqual(asig_a.monitor_id, self.w["monitor_b"].pk)
        self.assertEqual(asig_b.monitor_id, self.w["monitor_a"].pk)

    def test_otro_monitor_no_puede_elegir(self):
        _auth(self.client, self.w["monitor_b"])
        res = self.client.post(
            f"/api/cambios/{self.solicitud.id_cambio}/elegir/",
            {"opcion": self.opcion_b.id_opcion},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_no_puede_elegir(self):
        _auth(self.client, self.w["admin"])
        res = self.client.post(
            f"/api/cambios/{self.solicitud.id_cambio}/elegir/",
            {"opcion": self.opcion_b.id_opcion},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class RechazarApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()

    def test_admin_rechaza_pendiente(self):
        s = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"], solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        _auth(self.client, self.w["admin"])
        res = self.client.post(
            f"/api/cambios/{s.id_cambio}/rechazar/",
            {"respuesta": "No procede"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        s.refresh_from_db()
        self.assertEqual(s.estado, SolicitudCambio.RECHAZADA)

    def test_no_se_puede_rechazar_aprobada(self):
        """Caso del screenshot: admin intenta rechazar una solicitud que ya fue aprobada/respondida."""
        s = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"], solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        proponer_opciones(
            solicitud=s, admin=self.w["admin"],
            asignaciones_swap=[self.w["asig_b"], self.w["asig_c"]],
        )
        s.refresh_from_db()
        elegir_opcion(solicitud=s, opcion=s.opciones.first(), monitor=self.w["monitor_a"])
        s.refresh_from_db()
        # Ya está APROBADA — intentar rechazar debe retornar 400
        _auth(self.client, self.w["admin"])
        res = self.client.post(
            f"/api/cambios/{s.id_cambio}/rechazar/",
            {"respuesta": "Tarde"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ya fue resuelta", res.json().get("error", ""))

    def test_monitor_no_puede_rechazar(self):
        s = SolicitudCambio.objects.create(
            asignacion=self.w["asig_a"], solicitante=self.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        _auth(self.client, self.w["monitor_a"])
        res = self.client.post(
            f"/api/cambios/{s.id_cambio}/rechazar/", {"respuesta": "Yo"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class ListadoSolicitudesApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = _make_world()
        # 2 solicitudes: una de monitor_a, una de monitor_b
        cls.s_a = SolicitudCambio.objects.create(
            asignacion=cls.w["asig_a"], solicitante=cls.w["monitor_a"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )
        cls.s_b = SolicitudCambio.objects.create(
            asignacion=cls.w["asig_b"], solicitante=cls.w["monitor_b"],
            tipo=SolicitudCambio.TIPO_CAMBIO_TURNO,
        )

    def _list(self, user, params=""):
        _auth(self.client, user)
        return self.client.get(f"/api/cambios/{params}")

    def test_admin_ve_todas(self):
        res = self._list(self.w["admin"])
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [s["id_cambio"] for s in res.json()]
        self.assertIn(self.s_a.id_cambio, ids)
        self.assertIn(self.s_b.id_cambio, ids)

    def test_monitor_solo_ve_las_suyas(self):
        res = self._list(self.w["monitor_a"])
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [s["id_cambio"] for s in res.json()]
        self.assertIn(self.s_a.id_cambio, ids)
        self.assertNotIn(self.s_b.id_cambio, ids)

    def test_filtro_por_estado(self):
        # Rechaza s_a y verifica que filtro estado=pendiente solo trae s_b
        rechazar_solicitud(solicitud=self.s_a, admin=self.w["admin"])
        res = self._list(self.w["admin"], "?estado=pendiente")
        ids = [s["id_cambio"] for s in res.json()]
        self.assertNotIn(self.s_a.id_cambio, ids)
        self.assertIn(self.s_b.id_cambio, ids)
