"""Limpieza agresiva de datos de demo para empezar desde cero.

Borra en orden (respetando FKs):
1. OpcionCambio
2. SolicitudCambio
3. Asignacion
4. Horario
5. Sala
6. Usuario con rol=monitor (NO toca admins ni superusers)
7. Semestre

NO borra: usuarios admin (admin@sgmsc.edu.ec, juanariassaavedra@gmail.com,
cualquier user con rol=admin o is_superuser=True). Despues de ejecutarlo,
correr seed_demo crea de nuevo el set minimo de demo limpio.

Uso manual:
    python manage.py wipe_demo
    python manage.py wipe_demo --keep-salas   # no borra salas ni horarios
    python manage.py wipe_demo --dry-run      # solo cuenta, no borra

Uso automatico en deploy:
    Agrega DEMO_WIPE=1 a las env vars de Render. build.sh detecta y
    ejecuta este wipe ANTES del seed_demo.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from asignaciones.models import Asignacion
from cambios.models import OpcionCambio, SolicitudCambio
from horarios.models import Horario
from salas.models import Sala
from semestres.models import Semestre


class Command(BaseCommand):
    help = "Borra datos de demo en cascade (preserva admins). Usar con cuidado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-salas",
            action="store_true",
            help="No borra salas ni horarios (utiles si quieres mantener la estructura fisica).",
        )
        parser.add_argument(
            "--keep-semestres",
            action="store_true",
            help="No borra semestres (utiles si tienes histórico que conservar).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo cuenta lo que borraria, no ejecuta nada.",
        )

    def handle(self, *args, **opts):
        Usuario = get_user_model()
        out = self.stdout.write
        keep_salas = opts["keep_salas"]
        keep_semestres = opts["keep_semestres"]
        dry_run = opts["dry_run"]

        if dry_run:
            out(self.style.WARNING("DRY RUN - no se borra nada, solo se cuenta:"))
        else:
            out(self.style.WARNING("WIPE iniciado - borrando datos de demo..."))

        counts = {
            "opciones":     OpcionCambio.objects.count(),
            "solicitudes":  SolicitudCambio.objects.count(),
            "asignaciones": Asignacion.objects.count(),
            "horarios":     Horario.objects.count() if not keep_salas else 0,
            "salas":        Sala.objects.count() if not keep_salas else 0,
            "monitores":    Usuario.objects.filter(rol="monitor").count(),
            "semestres":    Semestre.objects.count() if not keep_semestres else 0,
        }

        out(f"  Opciones de cambio: {counts['opciones']}")
        out(f"  Solicitudes cambio: {counts['solicitudes']}")
        out(f"  Asignaciones:       {counts['asignaciones']}")
        if not keep_salas:
            out(f"  Horarios:           {counts['horarios']}")
            out(f"  Salas:              {counts['salas']}")
        else:
            out("  Horarios:           (preservados con --keep-salas)")
            out("  Salas:              (preservados con --keep-salas)")
        out(f"  Monitores:          {counts['monitores']}")
        if not keep_semestres:
            out(f"  Semestres:          {counts['semestres']}")
        else:
            out("  Semestres:          (preservados con --keep-semestres)")

        admins_count = Usuario.objects.filter(rol="admin").count()
        out(self.style.SUCCESS(
            f"  Admins preservados: {admins_count} (NO se borran)"
        ))

        if dry_run:
            out(self.style.WARNING("DRY RUN completado. No se modifico nada."))
            return

        try:
            with transaction.atomic():
                # Orden importante por FKs
                OpcionCambio.objects.all().delete()
                SolicitudCambio.objects.all().delete()
                Asignacion.objects.all().delete()
                if not keep_salas:
                    # Horario depende de Sala con CASCADE; borrar horarios primero
                    # es opcional pero mas explicito.
                    Horario.objects.all().delete()
                    Sala.objects.all().delete()
                # Monitor: cascade ya limpio sus FKs, ahora es seguro
                Usuario.objects.filter(rol="monitor").delete()
                if not keep_semestres:
                    Semestre.objects.all().delete()

            out(self.style.SUCCESS("WIPE completado exitosamente."))
            out(self.style.SUCCESS(
                f"BD ahora tiene: {Usuario.objects.count()} usuarios ({admins_count} admins), "
                f"{Sala.objects.count()} salas, "
                f"{Semestre.objects.count()} semestres."
            ))
            out("Para repoblar: python manage.py seed_demo")
        except Exception as exc:
            out(self.style.ERROR(f"WIPE fallo: {exc}"))
            raise
