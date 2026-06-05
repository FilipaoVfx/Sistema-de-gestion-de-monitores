from django.core.exceptions import ValidationError
from django.db.models import Q
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
    aceptar_como_candidato,
    crear_solicitud_cambio,
    elegir_opcion,
    proponer_opciones,
    rechazar_como_candidato,
    rechazar_solicitud,
)


def _format_validation_error(exc: ValidationError, msg: str = "Operacion fallida") -> Response:
    """Convierte un ValidationError de Django en Response 400 con detail rico."""
    if hasattr(exc, 'message_dict'):
        return Response(
            {'error': msg, 'detail': exc.message_dict},
            status=status.HTTP_400_BAD_REQUEST,
        )
    msgs = exc.messages if hasattr(exc, 'messages') else [str(exc)]
    return Response(
        {'error': msg, 'detail': msgs},
        status=status.HTTP_400_BAD_REQUEST,
    )


class SolicitudCambioViewSet(viewsets.ModelViewSet):
    """
    list                GET  /api/cambios/                   admin todas, monitor: solicitante o candidato
    create              POST /api/cambios/                   monitor crea (asignacion + motivo)
    retrieve            GET  /api/cambios/{id}/              detalle con opciones
    proponer            POST /api/cambios/{id}/proponer/     admin propone 2+ opciones
    elegir              POST /api/cambios/{id}/elegir/       solicitante elige opcion
    aceptar_candidato   POST /api/cambios/{id}/aceptar/      candidato confirma swap
    rechazar_candidato  POST /api/cambios/{id}/rechazar-candidato/  candidato declina
    rechazar            POST /api/cambios/{id}/rechazar/     admin rechaza
    candidatos          GET  /api/cambios/{id}/candidatos/   admin: asignaciones elegibles
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
            'opciones__candidato',
        ).order_by('-fecha_creacion')

        # Monitor ve: sus propias solicitudes O solicitudes donde es candidato
        # de una opcion ELEGIDA (esperando su confirmacion).
        if user.rol == Usuario.MONITOR:
            qs = qs.filter(
                Q(solicitante=user)
                | Q(opciones__candidato=user, opciones__estado_candidato=OpcionCambio.EST_ELEGIDA)
            ).distinct()

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
                solicitud=solicitud, admin=request.user,
                asignaciones_swap=asignaciones, respuesta=respuesta,
            )
        except ValidationError as exc:
            return _format_validation_error(exc, "No se pudo proponer las opciones.")

        return Response(SolicitudCambioSerializer(resultado).data)

    @action(detail=True, methods=['post'], url_path='elegir')
    def elegir(self, request, id_cambio=None):
        """Solicitante elige una opcion. El swap aun no se ejecuta; el candidato debe confirmar."""
        if request.user.rol != Usuario.MONITOR:
            return Response({'error': 'Solo el monitor solicitante puede elegir.'}, status=403)

        solicitud = self.get_object()
        if solicitud.solicitante_id != request.user.pk:
            return Response({'error': 'Solo el solicitante puede elegir.'}, status=403)

        serializer = ElegirOpcionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opcion_id = serializer.validated_data['opcion']

        try:
            opcion = OpcionCambio.objects.select_related('asignacion_swap').get(pk=opcion_id)
        except OpcionCambio.DoesNotExist:
            return Response({'error': 'Opcion no existe.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resultado = elegir_opcion(solicitud=solicitud, opcion=opcion, monitor=request.user)
        except ValidationError as exc:
            return _format_validation_error(exc, "No se pudo registrar tu eleccion.")

        return Response(SolicitudCambioSerializer(resultado).data)

    @action(detail=True, methods=['post'], url_path='aceptar')
    def aceptar(self, request, id_cambio=None):
        """Candidato confirma el swap. Solo el monitor candidato de la opcion elegida."""
        if request.user.rol != Usuario.MONITOR:
            return Response({'error': 'Solo el monitor candidato puede aceptar.'}, status=403)

        solicitud = self.get_object()
        try:
            resultado = aceptar_como_candidato(solicitud=solicitud, candidato=request.user)
        except ValidationError as exc:
            return _format_validation_error(exc, "No se pudo confirmar el swap.")

        return Response(SolicitudCambioSerializer(resultado).data)

    @action(detail=True, methods=['post'], url_path='rechazar-candidato')
    def rechazar_candidato_action(self, request, id_cambio=None):
        """Candidato declina el swap. La opcion queda rechazada y el solicitante puede elegir otra."""
        if request.user.rol != Usuario.MONITOR:
            return Response({'error': 'Solo el monitor candidato puede rechazar.'}, status=403)

        solicitud = self.get_object()
        motivo = request.data.get('motivo', '') if hasattr(request, 'data') else ''

        try:
            resultado = rechazar_como_candidato(
                solicitud=solicitud, candidato=request.user, motivo=motivo or '',
            )
        except ValidationError as exc:
            return _format_validation_error(exc, "No se pudo rechazar.")

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
                solicitud=solicitud, admin=request.user, respuesta=respuesta,
            )
        except ValidationError as exc:
            return _format_validation_error(exc, "No se pudo rechazar.")

        return Response(SolicitudCambioSerializer(resultado).data)
