from rest_framework import serializers
from .models import SolicitudCambio


class SolicitudCambioSerializer(serializers.ModelSerializer):
    solicitante_email = serializers.EmailField(source='solicitante.email', read_only=True)
    solicitante_nombre = serializers.SerializerMethodField()
    monitor_reemplazo_email = serializers.EmailField(source='monitor_reemplazo.email', read_only=True)
    monitor_reemplazo_nombre = serializers.SerializerMethodField()
    respondido_por_email = serializers.SerializerMethodField()
    asignacion_detalle = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudCambio
        fields = [
            'id_cambio', 'asignacion', 'asignacion_detalle',
            'solicitante', 'solicitante_email', 'solicitante_nombre',
            'monitor_reemplazo', 'monitor_reemplazo_email', 'monitor_reemplazo_nombre',
            'tipo', 'motivo', 'estado', 'respuesta',
            'respondido_por', 'respondido_por_email',
            'fecha_creacion', 'fecha_respuesta',
        ]
        read_only_fields = [
            'id_cambio', 'estado', 'respuesta', 'respondido_por',
            'fecha_creacion', 'fecha_respuesta',
        ]

    def get_solicitante_nombre(self, obj):
        return obj.solicitante.get_full_name() or obj.solicitante.email

    def get_monitor_reemplazo_nombre(self, obj):
        return obj.monitor_reemplazo.get_full_name() or obj.monitor_reemplazo.email

    def get_respondido_por_email(self, obj):
        return obj.respondido_por.email if obj.respondido_por else None

    def get_asignacion_detalle(self, obj):
        a = obj.asignacion
        return {
            'id_asignacion': a.id_asignacion,
            'sala': a.horario.sala.nombre,
            'dia': a.horario.get_dia_semana_display(),
            'hora_inicio': str(a.horario.hora_inicio),
            'hora_fin': str(a.horario.hora_fin),
            'semestre': f"{a.semestre.anio}-{a.semestre.periodo}",
        }


class ResponderSolicitudSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=[SolicitudCambio.APROBADA, SolicitudCambio.RECHAZADA])
    respuesta = serializers.CharField(required=False, default='', allow_blank=True)


class CrearSolicitudSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitudCambio
        fields = ['asignacion', 'monitor_reemplazo', 'motivo']
