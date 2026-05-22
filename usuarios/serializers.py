from rest_framework import serializers
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'email', 'first_name', 'last_name', 'cedula', 'telefono', 'rol']
        read_only_fields = ['id', 'email']


class CrearMonitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['email', 'first_name', 'last_name', 'cedula', 'telefono']

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")
        return value

    def validate_cedula(self, value):
        if Usuario.objects.filter(cedula=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con esta cédula.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
