from rest_framework import serializers
from .models import Semestre


class SemestreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semestre
        fields = ['id_semestre', 'anio', 'periodo', 'activo']
        read_only_fields = ['id_semestre']
