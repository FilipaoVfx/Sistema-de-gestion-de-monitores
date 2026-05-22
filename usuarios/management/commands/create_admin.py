"""Crea (o actualiza la password de) un usuario admin de forma idempotente.

Uso interactivo (CLI):
    python manage.py create_admin --email juan@x.com --password "@Foo" \\
        --first-name Juan --last-name Arias --cedula ADMIN-002

Uso via build/deploy:
    El comando es idempotente. Si el email ya existe, solo actualiza
    los campos y resetea la password si --password fue provista.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Crea o actualiza un usuario admin (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--email",      required=True, help="Email (login)")
        parser.add_argument("--password",   required=True, help="Password en texto plano")
        parser.add_argument("--first-name", default="Admin",  help="Nombre")
        parser.add_argument("--last-name",  default="Sistema", help="Apellido")
        parser.add_argument("--cedula",     default=None, help="Cedula (default: deriva del email)")
        parser.add_argument("--username",   default=None, help="Username (default: deriva del email)")

    def handle(self, *args, **opts):
        Usuario = get_user_model()
        email    = opts["email"].strip().lower()
        password = opts["password"]
        if not email or not password:
            raise CommandError("--email y --password son obligatorios y no pueden ir vacios.")

        username = opts["username"] or email.split("@", 1)[0]
        cedula   = opts["cedula"]   or f"ADMIN-{username[:20]}"

        user, created = Usuario.objects.get_or_create(
            email=email,
            defaults={
                "username":     username,
                "cedula":       cedula,
                "rol":          "admin",
                "first_name":   opts["first_name"],
                "last_name":    opts["last_name"],
                "is_staff":     True,
                "is_superuser": True,
                "is_active":    True,
            },
        )
        if not created:
            # Asegura que el usuario tenga privilegios admin aunque exista
            user.rol          = "admin"
            user.is_staff     = True
            user.is_superuser = True
            user.is_active    = True

        user.set_password(password)
        user.save()

        action = "creado" if created else "actualizado"
        self.stdout.write(self.style.SUCCESS(f"Admin {action}: {email}"))
