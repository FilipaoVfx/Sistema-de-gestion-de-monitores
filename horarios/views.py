from rest_framework import viewsets, permissions
from .models import Horario
from .serializers import HorarioSerializer


class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all().select_related('sala').order_by('sala', 'dia_semana', 'hora_inicio')
    serializer_class = HorarioSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id_horario'

    def get_queryset(self):
        qs = super().get_queryset()
        sala_id = self.request.query_params.get('sala')
        if sala_id:
            qs = qs.filter(sala_id=sala_id)
        return qs
