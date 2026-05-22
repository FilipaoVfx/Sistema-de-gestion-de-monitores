"""
Crea un superusuario admin desde variables de entorno.

Idempotente: si ya existe un usuario con ese email, no hace nada.
Pensado para correr automaticamente en el build de Render (build.sh).

Variables de entorno:
    DJANGO_ADMIN_EMAIL     (obligatoria)
    DJANGO_ADMIN_PASSWORD  (obligatoria)
    DJANGO_ADMIN_CEDULA    (opcional, default: '0000000000')
    DJANGO_ADMIN_USERNAME  (opcional, default: 'admin')
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Crea un superusuario admin desde variables de entorno (idempotente)."

    def handle(self, *args, **opts):
        email    = os.environ.get('DJANGO_ADMIN_EMAIL')
        password = os.environ.get('DJANGO_ADMIN_PASSWORD')
        cedula   = os.environ.get('DJANGO_ADMIN_CEDULA',   '0000000000')
        username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin')

        if not email or not password:
            self.stdout.write(self.style.WARNING(
                "Saltando: DJANGO_ADMIN_EMAIL o DJANGO_ADMIN_PASSWORD no configurados."
            ))
            return

        Usuario = get_user_model()

        if Usuario.objects.filter(email=email).exists():
            self.stdout.write(self.style.SUCCESS(
                f"Admin '{email}' ya existe — nada que hacer."
            ))
            return

        user = Usuario.objects.create_superuser(
            email=email,
            password=password,
            username=username,
            cedula=cedula,
            rol='admin',
        )
        self.stdout.write(self.style.SUCCESS(
            f"Superusuario '{user.email}' creado correctamente."
        ))
