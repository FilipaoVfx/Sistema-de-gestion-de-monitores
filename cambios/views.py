from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from asignaciones.models import Asignacion
from asignaciones.serializers import AsignacionSerializer
from usuarios.models import Usuario

from .models import OpcionCambio, SolicitudCambio
from .serializers import (
    SolicitudCambioSerializer,
    CrearSolicitudSerializer,
    ProponerOpcionesSerializer,
    ElegirOpcionSerializer,
    RechazarSolicitudSerializer,
)
from .services import (
    crear_solicitud_cambio,
    proponer_opciones,
    elegir_opcion,
    rechazar_solicitud,
)


class SolicitudCambioViewSet(viewsets.ModelViewSet):
    """
    list      GET  /api/cambios/                   → todos (admin) o solo los propios (monitor)
    create    POST /api/cambios/                   → monitor crea solicitud (asignacion + motivo)
    retrieve  GET  /api/cambios/{id}/              → detalle con opciones
    proponer  POST /api/cambios/{id}/proponer/     → admin propone 2+ opciones de swap
    elegir    POST /api/cambios/{id}/elegir/       → monitor solicitante elige opcion
    rechazar  POST /api/cambios/{id}/rechazar/     → admin rechaza solicitud sin proponer
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
        ).prefetch_related(
            'opciones__asignacion_swap__horario__sala',
            'opciones__asignacion_swap__monitor',
            'opciones__asignacion_swap__semestre',
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
            raise PermissionDenied("Solo monitores pueden crear solicitudes de cambio.")

        asignacion = serializer.validated_data['asignacion']
        if asignacion.monitor != user:
            raise PermissionDenied("Solo puedes solicitar cambios de tus propios turnos.")

        crear_solicitud_cambio(
            asignacion=asignacion,
            solicitante=user,
            monitor_reemplazo=None,
            motivo=serializer.validated_data.get('motivo', ''),
        )

    @action(detail=True, methods=['post'], url_path='proponer')
    def proponer(self, request, id_cambio=None):
        """Admin propone 2+ opciones de swap para la solicitud."""
        if request.user.rol != Usuario.ADMIN:
            return Response({'error': 'Solo administradores pueden proponer opciones.'}, status=403)

        solicitud = self.get_object()
        if solicitud.estado != SolicitudCambio.PENDIENTE:
            return Response(
                {'error': 'La solicitud no esta en estado pendiente.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProponerOpcionesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opcion_ids = serializer.validated_data['opciones']
        respuesta = serializer.validated_data.get('respuesta', '')

        # Resolver las Asignaciones por ID
        asignaciones = list(
            Asignacion.objects.select_related('monitor', 'horario', 'semestre').filter(pk__in=opcion_ids)
        )
        if len(asignaciones) != len(opcion_ids):
            return Response(
                {'error': 'Una o mas asignaciones no existen.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            resultado = proponer_opciones(
                solicitud=solicitud,
                admin=request.user,
                asignaciones_swap=asignaciones,
                respuesta=respuesta,
            )
        except ValidationError as exc:
            msgs = exc.messages if hasattr(exc, 'messages') else [str(exc)]
            return Response({'error': ' '.join(msgs)}, status=400)

        return Response(SolicitudCambioSerializer(resultado).data)

    @action(detail=True, methods=['post'], url_path='elegir')
    def elegir(self, request, id_cambio=None):
        """Monitor solicitante elige una opcion de swap; se ejecuta el cambio."""
        if request.user.rol != Usuario.MONITOR:
            return Response({'error': 'Solo el monitor solicitante puede elegir.'}, status=403)

        solicitud = self.get_object()
        if solicitud.solicitante_id != request.user.pk:
            return Response({'error': 'Solo el solicitante puede elegir.'}, status=403)

        if solicitud.estado != SolicitudCambio.CON_PROPUESTAS:
            return Response(
                {'error': 'La solicitud no esta esperando eleccion.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ElegirOpcionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opcion_id = serializer.validated_data['opcion']

        try:
            opcion = OpcionCambio.objects.select_related('asignacion_swap').get(pk=opcion_id)
        except OpcionCambio.DoesNotExist:
            return Response({'error': 'Opcion no existe.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resultado = elegir_opcion(
                solicitud=solicitud,
                opcion=opcion,
                monitor=request.user,
            )
        except ValidationError as exc:
            msgs = exc.messages if hasattr(exc, 'messages') else [str(exc)]
            return Response({'error': ' '.join(msgs)}, status=400)

        return Response(SolicitudCambioSerializer(resultado).data)

    @action(detail=True, methods=['get'], url_path='candidatos')
    def candidatos(self, request, id_cambio=None):
        """Admin: lista asignaciones elegibles para swap.

        Retorna asignaciones del mismo semestre que la solicitud, de OTROS
        monitores (no el solicitante), excluyendo turnos que ya esten en
        solicitudes pendientes/con_propuestas.
        """
        if request.user.rol != Usuario.ADMIN:
            return Response({'error': 'Solo administradores pueden ver candidatos.'}, status=403)

        solicitud = self.get_object()
        # IDs de asignaciones que ya estan en solicitudes activas (no aprobadas/rechazadas)
        bloqueadas = SolicitudCambio.objects.filter(
            estado__in=[SolicitudCambio.PENDIENTE, SolicitudCambio.CON_PROPUESTAS]
        ).values_list('asignacion_id', flat=True)

        qs = Asignacion.objects.select_related(
            'monitor', 'horario__sala', 'semestre'
        ).filter(
            semestre=solicitud.asignacion.semestre,
        ).exclude(
            monitor=solicitud.solicitante,
        ).exclude(
            pk__in=list(bloqueadas),
        ).order_by('horario__dia_semana', 'horario__hora_inicio', 'horario__sala__codigo')

        return Response(AsignacionSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='rechazar')
    def rechazar(self, request, id_cambio=None):
        """Admin rechaza la solicitud (sin proponer opciones)."""
        if request.user.rol != Usuario.ADMIN:
            return Response({'error': 'Solo administradores pueden rechazar.'}, status=403)

        solicitud = self.get_object()
        if solicitud.estado in (SolicitudCambio.APROBADA, SolicitudCambio.RECHAZADA):
            return Response(
                {'error': 'La solicitud ya fue resuelta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RechazarSolicitudSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        respuesta = serializer.validated_data.get('respuesta', '')

        try:
            resultado = rechazar_solicitud(
                solicitud=solicitud,
                admin=request.user,
                respuesta=respuesta,
            )
        except ValidationError as exc:
            msgs = exc.messages if hasattr(exc, 'messages') else [str(exc)]
            return Response({'error': ' '.join(msgs)}, status=400)

        return Response(SolicitudCambioSerializer(resultado).data)
