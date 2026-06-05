from rest_framework import serializers
from .models import Horario


class HorarioSerializer(serializers.ModelSerializer):
    dia_semana_display = serializers.CharField(source='get_dia_semana_display', read_only=True)
    # Info de ocupacion en un semestre especifico. Se llena cuando el cliente
    # pasa ?semestre=<id> en el query. Permite mostrar en la UI cuales
    # horarios estan ya tomados y por quien, sin requerir queries extras.
    asignacion_id = serializers.SerializerMethodField()
    monitor_id = serializers.SerializerMethodField()
    monitor_nombre = serializers.SerializerMethodField()
    monitor_email = serializers.SerializerMethodField()
    ocupado = serializers.SerializerMethodField()

    class Meta:
        model = Horario
        fields = [
            'id_horario', 'sala', 'dia_semana', 'dia_semana_display',
            'hora_inicio', 'hora_fin',
            'asignacion_id', 'monitor_id', 'monitor_nombre', 'monitor_email', 'ocupado',
        ]
        read_only_fields = [
            'id_horario',
            'asignacion_id', 'monitor_id', 'monitor_nombre', 'monitor_email', 'ocupado',
        ]

    def _asig(self, obj):
        """Devuelve la Asignacion del horario en el semestre del context, o None."""
        cached = getattr(obj, '_asig_in_semestre', None)
        if cached is not None:
            return cached if cached is not False else None
        return None

    def get_asignacion_id(self, obj):
        a = self._asig(obj)
        return a.id_asignacion if a else None

    def get_monitor_id(self, obj):
        a = self._asig(obj)
        return a.monitor_id if a else None

    def get_monitor_nombre(self, obj):
        a = self._asig(obj)
        if not a:
            return None
        m = a.monitor
        return m.get_full_name() or m.email

    def get_monitor_email(self, obj):
        a = self._asig(obj)
        return a.monitor.email if a else None

    def get_ocupado(self, obj):
        return self._asig(obj) is not None
