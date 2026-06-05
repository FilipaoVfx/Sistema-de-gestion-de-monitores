from rest_framework import viewsets, permissions
from rest_framework.response import Response

from asignaciones.models import Asignacion
from .models import Horario
from .serializers import HorarioSerializer


class HorarioViewSet(viewsets.ModelViewSet):
    """Endpoints de Horario.

    Query params soportados:
      ?sala=<id>      filtra por sala
      ?semestre=<id>  anota cada horario con la Asignacion existente en ese
                      semestre (campos asignacion_id, monitor_id,
                      monitor_nombre, monitor_email, ocupado). Util para que
                      el frontend muestre cuales horarios estan tomados al
                      asignar un nuevo monitor.
    """
    serializer_class = HorarioSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id_horario'

    def get_queryset(self):
        qs = Horario.objects.select_related('sala').order_by(
            'sala', 'dia_semana', 'hora_inicio',
        )
        sala_id = self.request.query_params.get('sala')
        if sala_id:
            qs = qs.filter(sala_id=sala_id)
        return qs

    def _anotar_ocupacion(self, horarios, semestre_id):
        """Cachea la Asignacion de cada horario para el semestre dado."""
        if not semestre_id:
            return
        asigs = Asignacion.objects.select_related('monitor').filter(
            semestre_id=semestre_id,
            horario_id__in=[h.pk for h in horarios],
        )
        asig_by_horario = {a.horario_id: a for a in asigs}
        for h in horarios:
            # False como sentinel "ya verificamos, no hay asignacion"
            h._asig_in_semestre = asig_by_horario.get(h.pk, False)

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        semestre_id = request.query_params.get('semestre')
        horarios = list(qs)
        self._anotar_ocupacion(horarios, semestre_id)

        page = self.paginate_queryset(horarios)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(horarios, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        semestre_id = request.query_params.get('semestre')
        if semestre_id:
            asig = Asignacion.objects.select_related('monitor').filter(
                semestre_id=semestre_id, horario=instance,
            ).first()
            instance._asig_in_semestre = asig if asig else False
        return Response(self.get_serializer(instance).data)
