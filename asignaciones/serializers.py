from rest_framework import serializers
from .models import Asignacion


class AsignacionSerializer(serializers.ModelSerializer):
    monitor_email = serializers.EmailField(source='monitor.email', read_only=True)
    monitor_nombre = serializers.SerializerMethodField()
    semestre_label = serializers.SerializerMethodField()
    sala_codigo = serializers.CharField(source='horario.sala.codigo', read_only=True)
    sala_nombre = serializers.CharField(source='horario.sala.nombre', read_only=True)
    id_sala = serializers.IntegerField(source='horario.sala.id_sala', read_only=True)
    dia_semana = serializers.IntegerField(source='horario.dia_semana', read_only=True)
    dia_semana_display = serializers.CharField(source='horario.get_dia_semana_display', read_only=True)
    hora_inicio = serializers.TimeField(source='horario.hora_inicio', read_only=True)
    hora_fin = serializers.TimeField(source='horario.hora_fin', read_only=True)

    class Meta:
        model = Asignacion
        fields = [
            'id_asignacion', 'monitor', 'monitor_email', 'monitor_nombre',
            'horario', 'semestre', 'semestre_label', 'fecha_creacion',
            'sala_codigo', 'sala_nombre', 'id_sala',
            'dia_semana', 'dia_semana_display', 'hora_inicio', 'hora_fin',
        ]
        read_only_fields = ['id_asignacion', 'fecha_creacion']

    def get_monitor_nombre(self, obj):
        return obj.monitor.get_full_name() or obj.monitor.email

    def get_semestre_label(self, obj):
        return f"{obj.semestre.anio}-{obj.semestre.periodo}"


class CrearAsignacionesSerializer(serializers.Serializer):
    """Serializer para la acción de creación masiva vía tokens de horario."""
    monitor = serializers.IntegerField(help_text="PK del monitor (Usuario)")
    semestre = serializers.IntegerField(help_text="PK del semestre")
    sala = serializers.IntegerField(help_text="PK de la sala")
    horarios = serializers.ListField(
        child=serializers.CharField(),
        help_text="Lista de tokens: 'h:<id>' para horarios existentes, 'n:<dia>|<HH:MM>|<HH:MM>' para nuevos",
    )
