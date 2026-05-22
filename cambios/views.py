from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from usuarios.models import Usuario

from .models import SolicitudCambio
from .serializers import (
    SolicitudCambioSerializer,
    ResponderSolicitudSerializer,
    CrearSolicitudSerializer,
)
from .services import aprobar_solicitud, rechazar_solicitud, crear_solicitud_cambio


class SolicitudCambioViewSet(viewsets.ModelViewSet):
    """
    list      GET  /api/cambios/                    → todos (admin) o solo los propios (monitor)
    create    POST /api/cambios/                    → monitor crea solicitud
    retrieve  GET  /api/cambios/{id}/
    responder POST /api/cambios/{id}/responder/     → admin aprueba o rechaza
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id_cambio'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return CrearSolicitudSerializer
        return SolicitudCambioSerializer

    def get_queryset(self):
        user = self.request.user
        qs = SolicitudCambio.objects.select_related(
            'asignacion__horario__sala', 'asignacion__semestre',
            'solicitante', 'monitor_reemplazo', 'respondido_por',
        ).order_by('-fecha_creacion')

        if user.rol == Usuario.MONITOR:
            qs = qs.filter(solicitante=user)

        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.rol != Usuario.MONITOR:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo monitores pueden crear solicitudes de cambio.")

        asignacion = serializer.validated_data['asignacion']
        if asignacion.monitor != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo puedes solicitar cambios de tus propios turnos.")

        # En el nuevo flujo el monitor NO elige reemplazo (no tiene visibilidad
        # de otros usuarios). El admin lo asigna al aprobar.
        crear_solicitud_cambio(
            asignacion=asignacion,
            solicitante=user,
            monitor_reemplazo=None,
            motivo=serializer.validated_data.get('motivo', ''),
        )

    @action(detail=True, methods=['post'], url_path='responder')
    def responder(self, request, id_cambio=None):
        if request.user.rol != Usuario.ADMIN:
            return Response({'error': 'Solo administradores pueden responder solicitudes.'}, status=403)

        solicitud = self.get_object()
        if solicitud.estado != SolicitudCambio.PENDIENTE:
            return Response({'error': 'Esta solicitud ya fue respondida.'}, status=400)

        serializer = ResponderSolicitudSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estado = serializer.validated_data['estado']
        respuesta = serializer.validated_data.get('respuesta', '')
        reemplazo_id = serializer.validated_data.get('monitor_reemplazo')

        # Resolver el monitor reemplazo (admin lo elige al aprobar)
        reemplazo = None
        if reemplazo_id:
            try:
                reemplazo = Usuario.objects.get(pk=reemplazo_id)
            except Usuario.DoesNotExist:
                return Response(
                    {'error': 'Monitor reemplazo no existe.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            if estado == SolicitudCambio.APROBADA:
                resultado = aprobar_solicitud(
                    solicitud=solicitud,
                    admin=request.user,
                    monitor_reemplazo=reemplazo,
                    respuesta=respuesta,
                )
            else:
                resultado = rechazar_solicitud(
                    solicitud=solicitud,
                    admin=request.user,
                    respuesta=respuesta,
                )
        except ValidationError as exc:
            msgs = exc.messages if hasattr(exc, 'messages') else [str(exc)]
            return Response({'error': ' '.join(msgs)}, status=400)

        return Response(SolicitudCambioSerializer(resultado).data)
