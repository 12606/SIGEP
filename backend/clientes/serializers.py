from rest_framework import serializers
from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    # La vinculación con Usuario solamente se establece desde el backend.
    usuario = serializers.PrimaryKeyRelatedField(read_only=True)
    cuenta = serializers.SerializerMethodField(read_only=True)

    def get_cuenta(self, obj):
        if not obj.usuario_id:
            return None
        usuario = obj.usuario
        rol = usuario.rol
        return {
            "username": usuario.username,
            "rol_codigo": rol.codigo if rol else None,
            "rol_nombre": rol.nombre if rol else "Sin rol",
            "is_active": usuario.is_active,
        }

    class Meta:
        model = Cliente
        fields = (
            "id", "usuario", "cuenta", "nombre", "apellidos", "telefono", "correo",
            "direccion", "observaciones", "activo", "fecha_registro", "fecha_actualizacion",
        )
        read_only_fields = ("id", "usuario", "cuenta", "activo", "fecha_registro", "fecha_actualizacion")

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        return value

    def validate_apellidos(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Los apellidos no pueden estar vacíos.")
        return value

    def validate_correo(self, value):
        return value.strip().lower()


class EstadoClienteSerializer(serializers.Serializer):
    activo = serializers.BooleanField()
