from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Rol, Usuario


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ("id", "codigo", "nombre", "descripcion", "activo")


class UsuarioSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id", "username", "email", "first_name", "last_name",
            "telefono", "rol", "is_active", "date_joined", "last_login",
        )
        read_only_fields = fields


class UsuarioEscrituraSerializer(serializers.ModelSerializer):
    # API permite el codigo legible (VENTAS, ADMIN...) y el id del rol por compatibilidad.
    rol_codigo = serializers.SlugRelatedField(
        source="rol", slug_field="codigo", queryset=Rol.objects.filter(activo=True),
        required=False, write_only=True,
    )
    rol_id = serializers.PrimaryKeyRelatedField(
        source="rol", queryset=Rol.objects.filter(activo=True),
        required=False, write_only=True,
    )
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False, style={"input_type": "password"})

    class Meta:
        model = Usuario
        fields = (
            "id", "username", "email", "first_name", "last_name", "telefono",
            "rol_codigo", "rol_id", "password",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        # Un solo campo para el rol por peticion; ambos se asignan al mismo atributo.
        if "rol_codigo" in self.initial_data and "rol_id" in self.initial_data:
            raise serializers.ValidationError({"rol": "Utiliza rol_codigo o rol_id, no los dos."})
        if self.instance is None:
            if "password" not in attrs:
                raise serializers.ValidationError({"password": "La contraseña es obligatoria."})
            if "rol" not in attrs:
                raise serializers.ValidationError({"rol_codigo": "Debes seleccionar un rol."})
        if "password" in attrs:
            # Django verifica longitud, contraseñas comunes y similitud con el usuario.
            user = Usuario(**{k: v for k, v in attrs.items() if k in ("username", "email", "first_name", "last_name")})
            if self.instance:
                user = self.instance
            try:
                validate_password(attrs["password"], user=user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

    def to_representation(self, instance):
        # Respuesta uniforme, nunca muestra contraseñas ni hashes.
        return UsuarioSerializer(instance).data


class EstadoUsuarioSerializer(serializers.Serializer):
    activo = serializers.BooleanField()
