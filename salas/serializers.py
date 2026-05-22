from rest_framework import serializers
from .models import Sala


class SalaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sala
        fields = ['id_sala', 'codigo', 'nombre', 'capacidad']
        read_only_fields = ['id_sala']
