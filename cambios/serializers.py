from rest_framework import serializers
from .models import OpcionCambio, SolicitudCambio


class OpcionCambioSerializer(serializers.ModelSerializer):
    """Opcion de swap propuesta — incluye detalle del turno, candidato y estado."""
    asignacion_swap_detalle = serializers.SerializerMethodField()
    monitor_swap_nombre = serializers.SerializerMethodField()
    monitor_swap_email = serializers.SerializerMethodField()
    # Campos del candidato (snapshot tomado al proponer la opcion)
    candidato_id = serializers.IntegerField(source='candidato.pk', read_only=True, allow_null=True)
    candidato_nombre = serializers.SerializerMethodField()
    candidato_email = serializers.SerializerMethodField()

    class Meta:
        model = OpcionCambio
        fields = [
            'id_opcion', 'solicitud', 'asignacion_swap',
            'asignacion_swap_detalle', 'monitor_swap_nombre', 'monitor_swap_email',
            'candidato_id', 'candidato_nombre', 'candidato_email',
            'orden', 'estado_candidato', 'seleccionada',
            'fecha_creacion', 'fecha_decision_candidato',
        ]
        read_only_fields = [
            'id_opcion', 'estado_candidato', 'seleccionada',
            'fecha_creacion', 'fecha_decision_candidato',
        ]

    def get_asignacion_swap_detalle(self, obj):
        a = obj.asignacion_swap
        return {
            'id_asignacion':      a.id_asignacion,
            'sala':               a.horario.sala.nombre,
            'sala_codigo':        a.horario.sala.codigo,
            'dia':                a.horario.get_dia_semana_display(),
            'dia_semana':         a.horario.dia_semana,
            'hora_inicio':        str(a.horario.hora_inicio),
            'hora_fin':           str(a.horario.hora_fin),
            'semestre':           f"{a.semestre.anio}-{a.semestre.periodo}",
        }

    def get_monitor_swap_nombre(self, obj):
        # En el nuevo flujo, mostramos el candidato (snapshot) en lugar del
        # dueno actual de asignacion_swap, porque tras un swap aceptado el
        # dueno cambia y queremos preservar la trazabilidad.
        c = obj.candidato or obj.asignacion_swap.monitor
        return c.get_full_name() or c.email

    def get_monitor_swap_email(self, obj):
        c = obj.candidato or obj.asignacion_swap.monitor
        return c.email

    def get_candidato_nombre(self, obj):
        if not obj.candidato:
            return None
        return obj.candidato.get_full_name() or obj.candidato.email

    def get_candidato_email(self, obj):
        return obj.candidato.email if obj.candidato else None


class SolicitudCambioSerializer(serializers.ModelSerializer):
    solicitante_email = serializers.EmailField(source='solicitante.email', read_only=True)
    solicitante_nombre = serializers.SerializerMethodField()
    monitor_reemplazo_email = serializers.EmailField(source='monitor_reemplazo.email', read_only=True, allow_null=True)
    monitor_reemplazo_nombre = serializers.SerializerMethodField()
    respondido_por_email = serializers.SerializerMethodField()
    asignacion_detalle = serializers.SerializerMethodField()
    opciones = OpcionCambioSerializer(many=True, read_only=True)

    class Meta:
        model = SolicitudCambio
        fields = [
            'id_cambio', 'asignacion', 'asignacion_detalle',
            'solicitante', 'solicitante_email', 'solicitante_nombre',
            'monitor_reemplazo', 'monitor_reemplazo_email', 'monitor_reemplazo_nombre',
            'tipo', 'motivo', 'estado', 'respuesta',
            'respondido_por', 'respondido_por_email',
            'opciones',
            'fecha_creacion', 'fecha_respuesta',
        ]
        read_only_fields = [
            'id_cambio', 'estado', 'respuesta', 'respondido_por',
            'fecha_creacion', 'fecha_respuesta', 'opciones',
        ]

    def get_solicitante_nombre(self, obj):
        return obj.solicitante.get_full_name() or obj.solicitante.email

    def get_monitor_reemplazo_nombre(self, obj):
        # El reemplazo final se setea solo al APROBAR (monitor eligio opcion).
        if not obj.monitor_reemplazo:
            return None
        return obj.monitor_reemplazo.get_full_name() or obj.monitor_reemplazo.email

    def get_respondido_por_email(self, obj):
        return obj.respondido_por.email if obj.respondido_por else None

    def get_asignacion_detalle(self, obj):
        a = obj.asignacion
        return {
            'id_asignacion':      a.id_asignacion,
            'sala':               a.horario.sala.nombre,
            'sala_codigo':        a.horario.sala.codigo,
            'dia':                a.horario.get_dia_semana_display(),
            'dia_semana':         a.horario.dia_semana,
            'hora_inicio':        str(a.horario.hora_inicio),
            'hora_fin':           str(a.horario.hora_fin),
            'semestre':           f"{a.semestre.anio}-{a.semestre.periodo}",
        }


class ProponerOpcionesSerializer(serializers.Serializer):
    """Body para POST /api/cambios/{id}/proponer/  (admin).

    Lista de IDs de asignaciones existentes (de OTROS monitores) que se
    proponen como opcion de swap. Minimo 2.
    """
    opciones = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=2,
        help_text="IDs de Asignacion para swap (al menos 2).",
    )
    respuesta = serializers.CharField(required=False, default='', allow_blank=True)


class ElegirOpcionSerializer(serializers.Serializer):
    """Body para POST /api/cambios/{id}/elegir/  (monitor solicitante)."""
    opcion = serializers.IntegerField(min_value=1, help_text="ID de OpcionCambio elegida.")


class RechazarSolicitudSerializer(serializers.Serializer):
    """Body para POST /api/cambios/{id}/rechazar/  (admin rechaza directamente)."""
    respuesta = serializers.CharField(required=False, default='', allow_blank=True)


class CrearSolicitudSerializer(serializers.ModelSerializer):
    """Body para POST /api/cambios/ (monitor crea solicitud).

    El monitor solo pasa `asignacion` y `motivo`. El admin propone opciones
    de swap, y el monitor elige cual aceptar.
    """
    class Meta:
        model = SolicitudCambio
        fields = ['asignacion', 'motivo']
