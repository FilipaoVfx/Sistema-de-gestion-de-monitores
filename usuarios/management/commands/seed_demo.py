"""Carga datos de demostracion para SGMSC.

Idempotente: corre las veces que quieras y solo crea lo que falta.
Crea: 1 admin, 8 monitores, 4 salas, 3 semestres, 35 horarios y 15 asignaciones
sobre el semestre activo (2025-1).

Si las asignaciones de demo ya fueron modificadas (por ejemplo via swap de
SolicitudCambio), los conflictos de validacion se atrapan y se loggean como
warning para que el build no falle.
"""
from datetime import time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from asignaciones.models import Asignacion
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

MONITORES = [
    ("monitor_juan",   "juan.rodriguez@sgmsc.edu.ec",  "Juan",   "Rodriguez", "1722345678", "+593-999111111"),
    ("monitor_maria",  "maria.garcia@sgmsc.edu.ec",    "Maria",  "Garcia",    "1722345679", "+593-999111112"),
    ("monitor_carlos", "carlos.lopez@sgmsc.edu.ec",    "Carlos", "Lopez",     "1722345680", "+593-999111113"),
    ("monitor_ana",    "ana.torres@sgmsc.edu.ec",      "Ana",    "Torres",    "1722345681", "+593-999111114"),
    ("monitor_luis",   "luis.morales@sgmsc.edu.ec",    "Luis",   "Morales",   "1722345682", "+593-999111115"),
    ("monitor_sofia",  "sofia.diaz@sgmsc.edu.ec",      "Sofia",  "Diaz",      "1722345683", "+593-999111116"),
    ("monitor_diego",  "diego.ramirez@sgmsc.edu.ec",   "Diego",  "Ramirez",   "1722345684", "+593-999111117"),
    ("monitor_lucia",  "lucia.sanchez@sgmsc.edu.ec",   "Lucia",  "Sanchez",   "1722345685", "+593-999111118"),
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
# Asignaciones para el semestre activo (2025-1).
ASIGNACIONES = [
    ("monitor_juan",   "LAB-01", 1, time(8, 0),  time(10, 0)),
    ("monitor_juan",   "LAB-01", 1, time(10, 0), time(12, 0)),
    ("monitor_maria",  "LAB-01", 1, time(14, 0), time(16, 0)),
    ("monitor_maria",  "LAB-01", 2, time(8, 0),  time(10, 0)),
    ("monitor_carlos", "LAB-02", 1, time(10, 0), time(12, 0)),
    ("monitor_carlos", "LAB-02", 1, time(14, 0), time(16, 0)),
    ("monitor_ana",    "LAB-02", 2, time(8, 0),  time(10, 0)),
    ("monitor_ana",    "LAB-02", 2, time(10, 0), time(12, 0)),
    ("monitor_luis",   "LAB-03", 1, time(8, 0),  time(10, 0)),
    ("monitor_luis",   "LAB-03", 2, time(10, 0), time(12, 0)),
    ("monitor_sofia",  "LAB-03", 3, time(14, 0), time(16, 0)),
    ("monitor_sofia",  "LAB-03", 4, time(8, 0),  time(10, 0)),
    ("monitor_diego",  "LAB-04", 1, time(9, 0),  time(11, 0)),
    ("monitor_diego",  "LAB-04", 3, time(14, 0), time(16, 0)),
    ("monitor_lucia",  "LAB-04", 5, time(9, 0),  time(11, 0)),
]


class Command(BaseCommand):
    help = "Crea datos de demostracion idempotentes (admin, monitores, salas, horarios, asignaciones)."

    @transaction.atomic
    def handle(self, *args, **opts):
        Usuario = get_user_model()
        out = self.stdout.write

        # 1) Admin
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

        # 2) Monitores
        for username, email, first, last, cedula, telefono in MONITORES:
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
                out(self.style.SUCCESS(f"Monitor creado: {email}"))
            else:
                out(f"Monitor ya existe: {email}")

        # 3) Salas
        for codigo, nombre, capacidad in SALAS:
            sala, created = Sala.objects.get_or_create(
                codigo=codigo,
                defaults={"nombre": nombre, "capacidad": capacidad},
            )
            out(self.style.SUCCESS(f"Sala creada: {codigo}") if created else f"Sala ya existe: {codigo}")

        # 4) Semestres
        for anio, periodo, activo in SEMESTRES:
            sem, created = Semestre.objects.get_or_create(
                anio=anio, periodo=periodo,
                defaults={"activo": activo},
            )
            out(self.style.SUCCESS(f"Semestre creado: {anio}-{periodo}") if created else f"Semestre ya existe: {anio}-{periodo}")

        # 5) Horarios
        salas_by_codigo = {s.codigo: s for s in Sala.objects.all()}
        horarios_creados = 0
        for codigo, dia, h_ini, h_fin in HORARIOS:
            _, created = Horario.objects.get_or_create(
                sala=salas_by_codigo[codigo],
                dia_semana=dia,
                hora_inicio=h_ini,
                hora_fin=h_fin,
            )
            horarios_creados += int(created)
        out(self.style.SUCCESS(f"Horarios creados/existentes: {horarios_creados} nuevos / {len(HORARIOS)} totales"))

        # 6) Asignaciones (sobre el semestre activo 2025-1)
        # Si las asignaciones originales fueron modificadas (por swap o
        # delete admin), saltamos las que ya no aplican en vez de romper el
        # seed. Esto permite que el deploy sea seguro post-modificaciones.
        semestre_activo = Semestre.objects.get(anio=2025, periodo=1)
        usuarios_by_username = {u.username: u for u in Usuario.objects.filter(rol="monitor")}
        asignaciones_creadas = 0
        asignaciones_saltadas = 0
        for username, codigo, dia, h_ini, h_fin in ASIGNACIONES:
            horario = Horario.objects.get(
                sala=salas_by_codigo[codigo],
                dia_semana=dia,
                hora_inicio=h_ini,
                hora_fin=h_fin,
            )
            monitor = usuarios_by_username[username]

            # Si la asignacion exacta (monitor + horario + semestre) ya existe, OK.
            if Asignacion.objects.filter(
                monitor=monitor, horario=horario, semestre=semestre_activo,
            ).exists():
                continue

            # Si el horario YA ESTA ocupado por otro monitor en este semestre
            # (swap previo), no intentamos sobrescribirlo — respetamos el
            # estado actual del sistema.
            if Asignacion.objects.filter(
                horario=horario, semestre=semestre_activo,
            ).exclude(monitor=monitor).exists():
                asignaciones_saltadas += 1
                out(f"Asignacion saltada (horario ya tomado por otro monitor): {username} -> {codigo} {dia} {h_ini}-{h_fin}")
                continue

            # Crea — pero si hay conflicto de horario del monitor (otro turno
            # se cruza), atrapamos y saltamos.
            try:
                with transaction.atomic():
                    Asignacion.objects.create(
                        monitor=monitor,
                        horario=horario,
                        semestre=semestre_activo,
                    )
                asignaciones_creadas += 1
            except ValidationError as exc:
                asignaciones_saltadas += 1
                msg = '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
                out(f"Asignacion saltada por conflicto: {username} -> {codigo} {dia} {h_ini}-{h_fin} ({msg})")
        out(self.style.SUCCESS(
            f"Asignaciones: {asignaciones_creadas} creadas, {asignaciones_saltadas} saltadas / {len(ASIGNACIONES)} totales"
        ))

        out(self.style.SUCCESS("\nSeed completado."))
        out("Login admin:   admin@sgmsc.edu.ec / Admin@2026")
        out("Login monitor: <email>@sgmsc.edu.ec / Monitor123")
