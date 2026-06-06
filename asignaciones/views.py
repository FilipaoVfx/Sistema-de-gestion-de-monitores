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
        ).order_by('horario__dia_semana', 'horario__hora_inicio')

        if user.rol == Usuario.MONITOR:
            qs = qs.filter(monitor=user)

        # Filtro automatico por semestre activo. El cliente ya no tiene que
        # pasar ?semestre=X - asumimos siempre el activo.
        # Si el caller necesita ver TODOS los semestres, puede pasar ?all_semesters=1.
        if not self.request.query_params.get('all_semesters'):
            qs = qs.filter(semestre__activo=True)

        # Filtros opcionales que se mantienen
        sala_id = self.request.query_params.get('sala')
        if sala_id:
            qs = qs.filter(horario__sala_id=sala_id)
        monitor_id = self.request.query_params.get('monitor')
        if monitor_id and user.rol == Usuario.ADMIN:
            qs = qs.filter(monitor_id=monitor_id)

        return qs

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk_create(self, request):
        """Crea asignaciones a partir de tokens de horario."""
        # Outer try/except como red de seguridad
        import traceback
        try:
            if request.user.rol != Usuario.ADMIN:
                return Response({
                    'error': 'Solo administradores pueden crear asignaciones.',
                    'detail': {
                        'rol_detectado': getattr(request.user, 'rol', None) or '<sin rol>',
                        'usuario':       getattr(request.user, 'email', None),
                        'is_staff':      getattr(request.user, 'is_staff', False),
                        'is_superuser':  getattr(request.user, 'is_superuser', False),
                        'hint': (
                            "Tu sesion actual no tiene rol admin. Cierra sesion y "
                            "vuelve a entrar con un usuario admin (admin@sgmsc.edu.ec)."
                        ),
                    },
                }, status=403)

            serializer = CrearAsignacionesSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            try:
                monitor = Usuario.objects.get(pk=data['monitor'], rol=Usuario.MONITOR)
            except Usuario.DoesNotExist:
                return Response(
                    {'error': 'Monitor no encontrado.', 'detail': {'monitor_id': data['monitor']}},
                    status=400,
                )
            # El semestre se infiere automaticamente del semestre activo.
            # El campo del serializer se conserva opcional pero se ignora.
            semestre = Semestre.objects.filter(activo=True).first()
            if not semestre:
                return Response(
                    {
                        'error': 'No hay semestre activo configurado.',
                        'detail': {
                            'hint': 'Configura un Semestre con activo=True en la BD antes de crear asignaciones.',
                        },
                    },
                    status=400,
                )

            try:
                creadas = crear_asignaciones(
                    monitor=monitor,
                    semestre=semestre,
                    sala_id=data['sala'],
                    seleccion_tokens=data['horarios'],
                )
            except ValidationError as exc:
                if hasattr(exc, 'message_dict'):
                    return Response(
                        {'error': 'No se pudieron crear las asignaciones.', 'detail': exc.message_dict},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                msgs = exc.messages if hasattr(exc, 'messages') else [str(exc)]
                return Response(
                    {'error': 'No se pudieron crear las asignaciones.', 'detail': msgs},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response({'creadas': creadas}, status=status.HTTP_201_CREATED)

        except Exception as exc:
            # Cualquier excepcion no prevista se reporta con type+msg+traceback
            # corto para diagnostico (en lugar de un 500 HTML opaco).
            return Response(
                {
                    'error': 'Error inesperado al crear asignaciones',
                    'detail': {
                        'type':      type(exc).__name__,
                        'msg':       str(exc),
                        'traceback': traceback.format_exc()[-1500:],
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
