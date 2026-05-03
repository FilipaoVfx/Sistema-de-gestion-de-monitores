import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import services


def _sala_a_dict(sala) -> dict:
    return {
        "id_sala": sala.id_sala,
        "codigo": sala.codigo,
        "nombre": sala.nombre,
        "capacidad": sala.capacidad,
    }


@require_http_methods(["GET"])
def listar_salas(request):
    salas = services.listar_salas()
    return JsonResponse({"salas": [_sala_a_dict(s) for s in salas]})


@csrf_exempt
@require_http_methods(["POST"])
def crear_sala(request):
    try:
        datos = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "El cuerpo de la solicitud no es JSON válido."}, status=400)

    try:
        sala = services.crear_sala(
            codigo=datos.get("codigo", ""),
            nombre=datos.get("nombre", ""),
            capacidad=datos.get("capacidad", 0),
        )
        return JsonResponse(_sala_a_dict(sala), status=201)
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=400)


@require_http_methods(["GET"])
def obtener_sala(request, id_sala):
    try:
        sala = services.obtener_sala(id_sala)
        return JsonResponse(_sala_a_dict(sala))
    except Exception:
        return JsonResponse({"error": "Sala no encontrada."}, status=404)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def salas(request):
    if request.method == "GET":
        salas = services.listar_salas()
        return JsonResponse({"salas": [_sala_a_dict(s) for s in salas]})

    datos = json.loads(request.body)
    try:
        sala = services.crear_sala(
            codigo=datos.get("codigo", ""),
            nombre=datos.get("nombre", ""),
            capacidad=datos.get("capacidad", 0),
        )
        return JsonResponse(_sala_a_dict(sala), status=201)
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def sala_detalle(request, id_sala):
    if request.method == "GET":
        try:
            sala = services.obtener_sala(id_sala)
            return JsonResponse(_sala_a_dict(sala))
        except Exception:
            return JsonResponse({"error": "Sala no encontrada."}, status=404)

    if request.method == "PATCH":
        try:
            datos = json.loads(request.body)
            sala = services.actualizar_sala(
                id_sala=id_sala,
                codigo=datos.get("codigo"),
                nombre=datos.get("nombre"),
                capacidad=datos.get("capacidad"),
            )
            return JsonResponse(_sala_a_dict(sala))
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    if request.method == "DELETE":
        try:
            services.eliminar_sala(id_sala)
            return JsonResponse({"mensaje": "Sala eliminada correctamente."})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)