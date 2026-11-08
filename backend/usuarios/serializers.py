from django.contrib.auth.password_validation import validate_password
from django.db import transaction
import re
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
            "telefono", "rol", "is_active", "is_superuser", "date_joined", "last_login",
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
        if self.instance is not None and "rol" in attrs:
            nuevo_rol = attrs["rol"]
            if nuevo_rol.pk != self.instance.rol_id:
                request = self.context.get("request")
                if self.instance.is_superuser:
                    raise serializers.ValidationError({"rol_codigo": "El rol de un superusuario está protegido."})
                if request and request.user.pk == self.instance.pk:
                    raise serializers.ValidationError({"rol_codigo": "No puedes cambiar tu propio rol."})
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

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        usuario = Usuario.objects.create_user(password=password, **validated_data)
        if usuario.rol and usuario.rol.codigo == "CLIENTE":
            from clientes.models import Cliente
            Cliente.objects.create(
                usuario=usuario,
                nombre=usuario.first_name or usuario.username,
                apellidos=usuario.last_name or "Sin apellidos",
                correo=usuario.email,
                telefono=usuario.telefono,
            )
        return usuario

    @transaction.atomic
    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password is not None:
            instance.set_password(password)
        instance.save()
        # Si el administrador convierte una cuenta en CLIENTE, crear su ficha si no
        # existe. No vincular automáticamente fichas manuales por correo.
        if instance.rol and instance.rol.codigo == "CLIENTE":
            from clientes.models import Cliente
            Cliente.objects.get_or_create(
                usuario=instance,
                defaults={
                    "nombre": instance.first_name or instance.username,
                    "apellidos": instance.last_name or "Sin apellidos",
                    "telefono": instance.telefono,
                    "correo": instance.email,
                },
            )
        return instance

    def to_representation(self, instance):
        # Respuesta uniforme, nunca muestra contraseñas ni hashes.
        return UsuarioSerializer(instance).data


class EstadoUsuarioSerializer(serializers.Serializer):
    activo = serializers.BooleanField()


class RegistroPublicoSerializer(serializers.ModelSerializer):
    """Registro para clientes: el rol NUNCA se acepta desde el navegador."""

    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    # No existe direccion en Usuario: se almacena exclusivamente en la ficha Cliente.
    direccion = serializers.CharField(max_length=250, write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Usuario
        fields = (
            "id", "username", "email", "first_name", "last_name",
            "telefono", "direccion", "password", "password_confirm",
        )
        read_only_fields = ("id",)
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
            "telefono": {"required": True, "allow_blank": False},
        }

    def validate_telefono(self, value):
        telefono = value.strip()
        digitos = re.sub(r"\D", "", telefono)
        if not (10 <= len(digitos) <= 15):
            raise serializers.ValidationError("Ingresa un teléfono válido de 10 a 15 dígitos.")
        return telefono

    def validate_email(self, value):
        value = value.strip().lower()
        if Usuario.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este correo ya está registrado.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Las contraseñas no coinciden."})
        ejemplo = Usuario(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=ejemplo)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        from clientes.models import Cliente

        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        direccion = validated_data.pop("direccion", "").strip()
        rol_cliente = Rol.objects.get(codigo="CLIENTE", activo=True)
        # Ambas operaciones son una transacción: no se crea un usuario sin ficha.
        with transaction.atomic():
            usuario = Usuario.objects.create_user(
                password=password, rol=rol_cliente,
                is_staff=False, is_superuser=False, **validated_data,
            )
            Cliente.objects.create(
                usuario=usuario,
                nombre=usuario.first_name,
                apellidos=usuario.last_name,
                correo=usuario.email,
                telefono=usuario.telefono,
                direccion=direccion,
            )
        return usuario
