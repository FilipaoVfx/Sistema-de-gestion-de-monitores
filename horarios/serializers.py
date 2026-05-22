from rest_framework import serializers
from .models import Horario


class HorarioSerializer(serializers.ModelSerializer):
    dia_semana_display = serializers.CharField(source='get_dia_semana_display', read_only=True)

    class Meta:
        model = Horario
        fields = [
            'id_horario', 'sala', 'dia_semana', 'dia_semana_display',
            'hora_inicio', 'hora_fin',
        ]
        read_only_fields = ['id_horario']
