from rest_framework import serializers
from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    # La vinculación con Usuario solamente se establece desde el backend.
    usuario = serializers.PrimaryKeyRelatedField(read_only=True)
    cuenta = serializers.SerializerMethodField(read_only=True)

    def get_cuenta(self, obj):
        request = self.context.get("request")
        if request is not None:
            from .permissions import codigo_rol
            if codigo_rol(request.user) != "ADMIN":
                return None
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
        from usuarios.models import Usuario
        correo = value.strip().lower()
        if self.instance and self.instance.usuario_id:
            if not correo:
                raise serializers.ValidationError("El correo de una cuenta vinculada no puede estar vacío.")
            # Una ficha enlazada usa el correo como credencial de login.
            if Usuario.objects.filter(email__iexact=correo).exclude(pk=self.instance.usuario_id).exists():
                raise serializers.ValidationError("Ese correo ya está registrado en otra cuenta.")
        return correo

    def validate(self, attrs):
        request = self.context.get("request")
        if request and self.instance and self.instance.usuario_id:
            from .permissions import codigo_rol
            if codigo_rol(request.user) == "VENTAS":
                # VENTAS modifica fichas comerciales, no correos de acceso.
                nuevo = attrs.get("correo", self.instance.correo)
                if nuevo != self.instance.correo:
                    raise serializers.ValidationError({"correo": "Solo ADMIN o el dueño pueden cambiar el correo de la cuenta."})
        return attrs

    def update(self, instance, validated_data):
        from django.db import transaction
        with transaction.atomic():
            for campo, valor in validated_data.items():
                setattr(instance, campo, valor)
            instance.save()
            if instance.usuario_id:
                usuario = instance.usuario
                mapeo = {"nombre": "first_name", "apellidos": "last_name", "telefono": "telefono", "correo": "email"}
                modificados = []
                for campo, campo_usuario in mapeo.items():
                    if campo in validated_data:
                        setattr(usuario, campo_usuario, getattr(instance, campo))
                        modificados.append(campo_usuario)
                if modificados:
                    usuario.save(update_fields=modificados)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None:
            from .permissions import codigo_rol
            if codigo_rol(request.user) != "ADMIN":
                # VENTAS necesita datos comerciales, no datos de la cuenta ni el rol.
                data.pop("usuario", None)
                data.pop("cuenta", None)
        return data


class EstadoClienteSerializer(serializers.Serializer):
    activo = serializers.BooleanField()


class MiFichaClienteSerializer(serializers.ModelSerializer):
    """Edición limitada de la ficha propia; sincroniza la información con el login."""

    class Meta:
        model = Cliente
        fields = ("id", "nombre", "apellidos", "telefono", "correo", "direccion")
        read_only_fields = ("id",)
        extra_kwargs = {
            "nombre": {"required": True, "allow_blank": False},
            "apellidos": {"required": True, "allow_blank": False},
        }

    def validate(self, attrs):
        extras = set(self.initial_data.keys()) - {"nombre", "apellidos", "telefono", "correo", "direccion"}
        if extras:
            raise serializers.ValidationError({"campos": "No puedes modificar: " + ", ".join(sorted(extras))})
        return attrs

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Escribe tu nombre.")
        return value

    def validate_apellidos(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Escribe tus apellidos.")
        return value

    def validate_telefono(self, value):
        import re
        numero = value.strip()
        if numero and not 10 <= len(re.sub(r"\D", "", numero)) <= 15:
            raise serializers.ValidationError("Introduce un teléfono de 10 a 15 dígitos.")
        return numero

    def validate_correo(self, value):
        from usuarios.models import Usuario
        correo = value.strip().lower()
        if not correo:
            raise serializers.ValidationError("El correo es obligatorio.")
        usuario_id = self.instance.usuario_id if self.instance else None
        if Usuario.objects.filter(email__iexact=correo).exclude(pk=usuario_id).exists():
            raise serializers.ValidationError("Ese correo ya está registrado.")
        return correo

    @staticmethod
    def _sincronizar_usuario(cliente):
        if not cliente.usuario_id:
            return
        usuario = cliente.usuario
        usuario.first_name = cliente.nombre
        usuario.last_name = cliente.apellidos
        usuario.telefono = cliente.telefono
        usuario.email = cliente.correo
        usuario.save(update_fields=["first_name", "last_name", "telefono", "email"])

    def update(self, instance, validated_data):
        from django.db import transaction
        with transaction.atomic():
            for nombre, valor in validated_data.items():
                setattr(instance, nombre, valor)
            instance.save()
            self._sincronizar_usuario(instance)
        return instance
