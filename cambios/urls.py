from django.urls import path

from .views import (
    crear_solicitud_view,
    detalle_solicitud_view,
    lista_solicitudes_view,
    mis_asignaciones_view,
    mis_solicitudes_view,
    responder_solicitud_view,
)

urlpatterns = [
    # Monitores
    path("solicitud/crear/", crear_solicitud_view, name="crear_solicitud"),
    path("solicitudes/", mis_solicitudes_view, name="mis_solicitudes"),
    path("asignaciones/", mis_asignaciones_view, name="mis_asignaciones"),

    # Administradores
    path("admin/solicitudes/", lista_solicitudes_view, name="lista_solicitudes"),
    path("admin/solicitud/<int:id_cambio>/detalle/", detalle_solicitud_view, name="detalle_solicitud"),
    path("admin/solicitud/<int:id_cambio>/responder/", responder_solicitud_view, name="responder_solicitud"),
]
