from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from semestres.models import Semestre
from usuarios.models import Usuario

from .models import Asignacion
from .serializers import AsignacionSerializer, CrearAsignacionesSerializer
from .services import crear_asignaciones


class AsignacionViewSet(viewsets.ModelViewSet):
    """
    list   GET  /api/asignaciones/           → todos (admin) o solo las propias (monitor)
    create POST /api/asignaciones/            → no usado directamente (usa /bulk/)
    bulk   POST /api/asignaciones/bulk/       → creación masiva por tokens de horario
    """
    serializer_class = AsignacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id_asignacion'
    http_method_names = ['get', 'delete', 'head', 'options', 'post']

    def get_queryset(self):
        user = self.request.user
        qs = Asignacion.objects.select_related(
            'monitor', 'horario__sala', 'semestre'
        ).order_by('semestre__anio', 'semestre__periodo', 'horario__dia_semana', 'horario__hora_inicio')

        if user.rol == Usuario.MONITOR:
            qs = qs.filter(monitor=user)

        # Filtros opcionales
        semestre_id = self.request.query_params.get('semestre')
        if semestre_id:
            qs = qs.filter(semestre_id=semestre_id)
        sala_id = self.request.query_params.get('sala')
        if sala_id:
            qs = qs.filter(horario__sala_id=sala_id)
        monitor_id = self.request.query_params.get('monitor')
        if monitor_id and user.rol == Usuario.ADMIN:
            qs = qs.filter(monitor_id=monitor_id)

        return qs

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk_create(self, request):
        """Crea asignaciones a partir de tokens de horario (misma lógica que el formulario HTMX)."""
        if request.user.rol != Usuario.ADMIN:
            return Response({'error': 'Solo administradores pueden crear asignaciones.'}, status=403)

        serializer = CrearAsignacionesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            monitor = Usuario.objects.get(pk=data['monitor'], rol=Usuario.MONITOR)
        except Usuario.DoesNotExist:
            return Response({'error': 'Monitor no encontrado.'}, status=400)
        try:
            semestre = Semestre.objects.get(pk=data['semestre'])
        except Semestre.DoesNotExist:
            return Response({'error': 'Semestre no encontrado.'}, status=400)

        try:
            creadas = crear_asignaciones(
                monitor=monitor,
                semestre=semestre,
                sala_id=data['sala'],
                seleccion_tokens=data['horarios'],
            )
        except ValidationError as exc:
            msgs = exc.messages if hasattr(exc, 'messages') else [str(exc)]
            return Response({'error': ' '.join(msgs)}, status=400)

        return Response({'creadas': creadas}, status=status.HTTP_201_CREATED)
