from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ADMIN = 'admin'
    MONITOR = 'monitor'
    OPCIONES_ROL = [
        (ADMIN, 'Administrador'),
        (MONITOR, 'Monitor'),
    ]

    cedula = models.CharField("Cédula", max_length=20, unique=True)
    rol = models.CharField("Rol", max_length=15, choices=OPCIONES_ROL, default=MONITOR)
    telefono = models.CharField("Telefono", max_length=20, blank=True)
    email = models.EmailField("Correo institucional", unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'cedula', 'rol']

    def __str__(self):
        return f"{self.get_full_name()} ({self.rol})"

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'