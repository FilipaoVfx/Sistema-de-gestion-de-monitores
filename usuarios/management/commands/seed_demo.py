"""Carga datos de demostracion para SGMSC.

Idempotente: corre las veces que quieras y solo crea lo que falta.
Crea: 1 admin, 3 monitores, 4 salas, 3 semestres, 35 horarios y 6 asignaciones
sobre el semestre activo (2025-1).

Si las asignaciones de demo ya fueron modificadas (por ejemplo via swap de
SolicitudCambio), los conflictos de validacion se atrapan y se loggean como
warning para que el build no falle.

Modo PURGE: si la env var DEMO_PURGE=1 esta seteada en Render, el seed
primero BORRA TODOS los usuarios con rol monitor (cascade borra sus
asignaciones, solicitudes y opciones), y todas las solicitudes huerfanas,
y despues vuelve a crear el set limpio. Util para limpiar BD desordenada
sin tener que tocar Supabase manualmente.
"""
import os
from datetime import time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from asignaciones.models import Asignacion
from cambios.models import OpcionCambio, SolicitudCambio
from horarios.models import Horario
from salas.models import Sala
from semestres.models import Semestre


ADMIN = {
    "username": "admin_sgmsc",
    "email": "admin@sgmsc.edu.ec",
    "cedula": "ADMIN-001",
    "first_name": "Administrador",
    "last_name": "Sistema",
    "telefono": "+593-987654321",
    "password": "Admin@2026",
}

# Set minimo de monitores para un despliegue limpio. Si necesitas mas,
# extiende esta lista (los nombres pueden ser cualquier subconjunto).
MONITORES = [
    ("monitor_juan",   "juan.rodriguez@sgmsc.edu.ec",  "Juan",   "Rodriguez", "1722345678", "+593-999111111"),
    ("monitor_maria",  "maria.garcia@sgmsc.edu.ec",    "Maria",  "Garcia",    "1722345679", "+593-999111112"),
    ("monitor_carlos", "carlos.lopez@sgmsc.edu.ec",    "Carlos", "Lopez",     "1722345680", "+593-999111113"),
]
MONITOR_PASSWORD = "Monitor123"

SALAS = [
    ("LAB-01", "Laboratorio 1 - Planta Baja", 30),
    ("LAB-02", "Laboratorio 2 - Primer Piso", 25),
    ("LAB-03", "Laboratorio 3 - Segundo Piso", 28),
    ("LAB-04", "Sala de Videoconferencia - Tercer Piso", 12),
]

SEMESTRES = [
    (2025, 1, True),
    (2025, 2, False),
    (2026, 1, False),
]

# (codigo_sala, dia_semana, hora_inicio, hora_fin)
HORARIOS = (
    # LAB-01: lunes a viernes, 3 bloques (08-10, 10-12, 14-16) = 15
    [("LAB-01", d, time(8, 0),  time(10, 0)) for d in range(1, 6)]
  + [("LAB-01", d, time(10, 0), time(12, 0)) for d in range(1, 6)]
  + [("LAB-01", d, time(14, 0), time(16, 0)) for d in range(1, 6)]
    # LAB-02: 12 horarios siguiendo el patron del SQL
  + [("LAB-02", 1, time(8, 0),  time(10, 0)),
     ("LAB-02", 1, time(10, 0), time(12, 0)),
     ("LAB-02", 1, time(14, 0), time(16, 0)),
     ("LAB-02", 2, time(8, 0),  time(10, 0)),
     ("LAB-02", 2, time(10, 0), time(12, 0)),
     ("LAB-02", 2, time(14, 0), time(16, 0)),
     ("LAB-02", 3, time(8, 0),  time(10, 0)),
     ("LAB-02", 3, time(10, 0), time(12, 0)),
     ("LAB-02", 3, time(14, 0), time(16, 0)),
     ("LAB-02", 4, time(8, 0),  time(10, 0)),
     ("LAB-02", 4, time(10, 0), time(12, 0)),
     ("LAB-02", 5, time(14, 0), time(16, 0))]
    # LAB-03: 5 horarios variados
  + [("LAB-03", 1, time(8, 0),  time(10, 0)),
     ("LAB-03", 2, time(10, 0), time(12, 0)),
     ("LAB-03", 3, time(14, 0), time(16, 0)),
     ("LAB-03", 4, time(8, 0),  time(10, 0)),
     ("LAB-03", 5, time(10, 0), time(12, 0))]
    # LAB-04: videoconferencia, 3 horarios
  + [("LAB-04", 1, time(9, 0),  time(11, 0)),
     ("LAB-04", 3, time(14, 0), time(16, 0)),
     ("LAB-04", 5, time(9, 0),  time(11, 0))]
)

# (username_monitor, codigo_sala, dia_semana, hora_inicio, hora_fin)
# Asignaciones para el semestre activo (2025-1) usando solo los 3 monitores.
ASIGNACIONES = [
    ("monitor_juan",   "LAB-01", 1, time(8, 0),  time(10, 0)),
    ("monitor_juan",   "LAB-01", 1, time(10, 0), time(12, 0)),
    ("monitor_maria",  "LAB-01", 1, time(14, 0), time(16, 0)),
    ("monitor_maria",  "LAB-01", 2, time(8, 0),  time(10, 0)),
    ("monitor_carlos", "LAB-02", 1, time(10, 0), time(12, 0)),
    ("monitor_carlos", "LAB-02", 1, time(14, 0), time(16, 0)),
]


class Command(BaseCommand):
    help = "Crea datos de demostracion idempotentes (admin, monitores, salas, horarios, asignaciones)."

    # IMPORTANTE: NO usamos @transaction.atomic global. Cada seccion tiene su
    # propio try/except con sub-transaction para que si UNA seccion falla
    # (por ejemplo asignaciones con conflict por swap previo), las demas se
    # mantengan. Antes el seed era todo-o-nada y un fallo en asignaciones
    # borraba incluso los monitores recien creados.

    def handle(self, *args, **opts):
        Usuario = get_user_model()
        out = self.stdout.write

        # 0) PURGE opcional - solo si DEMO_PURGE=1
        # Borra solicitudes/opciones/asignaciones huerfanas y luego TODOS los
        # usuarios con rol monitor. Cascade del modelo limpia los hijos.
        # NO toca admins, salas, horarios ni semestres.
        if os.environ.get("DEMO_PURGE") == "1":
            out(self.style.WARNING("DEMO_PURGE=1 detectado: limpiando datos previos..."))
            try:
                with transaction.atomic():
                    # Solicitudes y opciones primero (por si alguna ya esta huerfana)
                    n_opciones = OpcionCambio.objects.all().delete()[0]
                    n_solicitudes = SolicitudCambio.objects.all().delete()[0]
                    # Asignaciones (cascade tambien al borrar monitores)
                    n_asignaciones = Asignacion.objects.all().delete()[0]
                    # Monitores
                    n_monitores = Usuario.objects.filter(rol="monitor").delete()[0]
                    out(self.style.WARNING(
                        f"  Purgados: {n_monitores} monitores, "
                        f"{n_asignaciones} asignaciones, "
                        f"{n_solicitudes} solicitudes, "
                        f"{n_opciones} opciones"
                    ))
            except Exception as exc:
                out(self.style.WARNING(f"Purge fallo: {exc}"))

        # 1) Admin
        try:
            with transaction.atomic():
                admin, created = Usuario.objects.get_or_create(
                    email=ADMIN["email"],
                    defaults={
                        "username":    ADMIN["username"],
                        "cedula":      ADMIN["cedula"],
                        "rol":         "admin",
                        "first_name":  ADMIN["first_name"],
                        "last_name":   ADMIN["last_name"],
                        "telefono":    ADMIN["telefono"],
                        "is_staff":    True,
                        "is_superuser": True,
                        "is_active":   True,
                    },
                )
                if created:
                    admin.set_password(ADMIN["password"])
                    admin.save()
                    out(self.style.SUCCESS(f"Admin creado: {admin.email}"))
                else:
                    out(f"Admin ya existe: {admin.email}")
        except Exception as exc:
            out(self.style.WARNING(f"Admin saltado por error: {exc}"))

        # 2) Monitores - cada uno en su propia sub-transaction para que si
        # UNO falla por unique constraint o cualquier otra cosa, los demas
        # se sigan creando.
        monitores_creados = 0
        monitores_existentes = 0
        monitores_saltados = 0
        for username, email, first, last, cedula, telefono in MONITORES:
            try:
                with transaction.atomic():
                    user, created = Usuario.objects.get_or_create(
                        email=email,
                        defaults={
                            "username":   username,
                            "cedula":     cedula,
                            "rol":        "monitor",
                            "first_name": first,
                            "last_name":  last,
                            "telefono":   telefono,
                            "is_active":  True,
                        },
                    )
                    if created:
                        user.set_password(MONITOR_PASSWORD)
                        user.save()
                        monitores_creados += 1
                        out(self.style.SUCCESS(f"Monitor creado: {email}"))
                    else:
                        monitores_existentes += 1
                        out(f"Monitor ya existe: {email}")
            except Exception as exc:
                monitores_saltados += 1
                out(self.style.WARNING(f"Monitor saltado ({email}): {exc}"))
        out(self.style.SUCCESS(
            f"Monitores: {monitores_creados} nuevos, "
            f"{monitores_existentes} ya existian, {monitores_saltados} saltados"
        ))

        # 3) Salas
        try:
            with transaction.atomic():
                for codigo, nombre, capacidad in SALAS:
                    sala, created = Sala.objects.get_or_create(
                        codigo=codigo,
                        defaults={"nombre": nombre, "capacidad": capacidad},
                    )
                    out(self.style.SUCCESS(f"Sala creada: {codigo}") if created else f"Sala ya existe: {codigo}")
        except Exception as exc:
            out(self.style.WARNING(f"Salas saltadas por error: {exc}"))

        # 4) Semestres
        try:
            with transaction.atomic():
                for anio, periodo, activo in SEMESTRES:
                    sem, created = Semestre.objects.get_or_create(
                        anio=anio, periodo=periodo,
                        defaults={"activo": activo},
                    )
                    out(self.style.SUCCESS(f"Semestre creado: {anio}-{periodo}") if created else f"Semestre ya existe: {anio}-{periodo}")
        except Exception as exc:
            out(self.style.WARNING(f"Semestres saltados por error: {exc}"))

        # 5) Horarios — cada uno en su propia sub-transaction
        try:
            salas_by_codigo = {s.codigo: s for s in Sala.objects.all()}
        except Exception as exc:
            out(self.style.WARNING(f"No se pudo cargar salas para horarios: {exc}"))
            salas_by_codigo = {}

        horarios_creados = 0
        horarios_saltados = 0
        for codigo, dia, h_ini, h_fin in HORARIOS:
            if codigo not in salas_by_codigo:
                horarios_saltados += 1
                continue
            try:
                with transaction.atomic():
                    _, created = Horario.objects.get_or_create(
                        sala=salas_by_codigo[codigo],
                        dia_semana=dia,
                        hora_inicio=h_ini,
                        hora_fin=h_fin,
                    )
                    horarios_creados += int(created)
            except Exception as exc:
                horarios_saltados += 1
                out(self.style.WARNING(
                    f"Horario saltado ({codigo} dia={dia} {h_ini}-{h_fin}): {exc}"
                ))
        out(self.style.SUCCESS(
            f"Horarios: {horarios_creados} nuevos, {horarios_saltados} saltados / {len(HORARIOS)} totales"
        ))

        # 6) Asignaciones (sobre el semestre activo 2025-1)
        # Si las asignaciones originales fueron modificadas (por swap o
        # delete admin), saltamos las que ya no aplican en vez de romper el
        # seed.
        try:
            semestre_activo = Semestre.objects.get(anio=2025, periodo=1)
        except Semestre.DoesNotExist:
            out(self.style.WARNING("No hay semestre 2025-1, saltamos asignaciones"))
            self._print_login_info(out)
            return

        usuarios_by_username = {u.username: u for u in Usuario.objects.filter(rol="monitor")}
        asignaciones_creadas = 0
        asignaciones_saltadas = 0
        for username, codigo, dia, h_ini, h_fin in ASIGNACIONES:
            if username not in usuarios_by_username:
                asignaciones_saltadas += 1
                out(f"Asignacion saltada (monitor {username} no existe)")
                continue
            if codigo not in salas_by_codigo:
                asignaciones_saltadas += 1
                continue
            try:
                horario = Horario.objects.get(
                    sala=salas_by_codigo[codigo],
                    dia_semana=dia,
                    hora_inicio=h_ini,
                    hora_fin=h_fin,
                )
            except Horario.DoesNotExist:
                asignaciones_saltadas += 1
                continue

            monitor = usuarios_by_username[username]

            if Asignacion.objects.filter(
                monitor=monitor, horario=horario, semestre=semestre_activo,
            ).exists():
                continue

            if Asignacion.objects.filter(
                horario=horario, semestre=semestre_activo,
            ).exclude(monitor=monitor).exists():
                asignaciones_saltadas += 1
                out(f"Asignacion saltada (horario ya tomado): {username} -> {codigo} {dia} {h_ini}-{h_fin}")
                continue

            try:
                with transaction.atomic():
                    Asignacion.objects.create(
                        monitor=monitor,
                        horario=horario,
                        semestre=semestre_activo,
                    )
                asignaciones_creadas += 1
            except Exception as exc:
                asignaciones_saltadas += 1
                msg = '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
                out(f"Asignacion saltada por conflicto: {username} -> {codigo} {dia} {h_ini}-{h_fin} ({msg})")
        out(self.style.SUCCESS(
            f"Asignaciones: {asignaciones_creadas} nuevas, {asignaciones_saltadas} saltadas / {len(ASIGNACIONES)} totales"
        ))

        self._print_login_info(out)

    def _print_login_info(self, out):
        out(self.style.SUCCESS("\nSeed completado."))
        out("Login admin:   admin@sgmsc.edu.ec / Admin@2026")
        out("Login monitor: <email>@sgmsc.edu.ec / Monitor123")
