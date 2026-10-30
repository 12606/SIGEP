from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Rol, Usuario

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ("id", "codigo", "nombre")

class UsuarioSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = ("id", "username", "email", "first_name", "last_name", "telefono", "rol", "is_active")

class UsuarioCrearSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    rol_id = serializers.PrimaryKeyRelatedField(source="rol", queryset=Rol.objects.filter(activo=True), required=True, write_only=True)

    class Meta:
        model = Usuario
        fields = ("id", "username", "email", "first_name", "last_name", "telefono", "password", "rol_id")
        read_only_fields = ("id",)

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(password=password, **validated_data)
