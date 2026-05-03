from django.core.exceptions import ValidationError

from .models import Sala


def crear_sala(codigo: str, nombre: str, capacidad: int) -> Sala:
    codigo = codigo.strip().upper()
    nombre = nombre.strip()

    if not codigo:
        raise ValidationError("El código de la sala no puede estar vacío.")

    if not nombre:
        raise ValidationError("El nombre de la sala no puede estar vacío.")

    if capacidad <= 0:
        raise ValidationError("La capacidad debe ser mayor a cero.")

    if Sala.objects.filter(codigo=codigo).exists():
        raise ValidationError(f"Ya existe una sala con el código '{codigo}'.")

    sala = Sala.objects.create(codigo=codigo, nombre=nombre, capacidad=capacidad)
    return sala


def obtener_sala(id_sala: int) -> Sala:
    return Sala.objects.get(pk=id_sala)


def listar_salas() -> list[Sala]:
    return list(Sala.objects.all())


def actualizar_sala(id_sala: int, codigo: str = None, nombre: str = None, capacidad: int = None) -> Sala:
    sala = obtener_sala(id_sala)

    if codigo is not None:
        codigo = codigo.strip().upper()
        if not codigo:
            raise ValidationError("El código no puede estar vacío.")
        if Sala.objects.filter(codigo=codigo).exclude(pk=id_sala).exists():
            raise ValidationError(f"Ya existe otra sala con el código '{codigo}'.")
        sala.codigo = codigo

    if nombre is not None:
        nombre = nombre.strip()
        if not nombre:
            raise ValidationError("El nombre no puede estar vacío.")
        sala.nombre = nombre

    if capacidad is not None:
        if capacidad <= 0:
            raise ValidationError("La capacidad debe ser mayor a cero.")
        sala.capacidad = capacidad

    sala.save()
    return sala


def eliminar_sala(id_sala: int) -> None:
    sala = obtener_sala(id_sala)
    sala.delete()