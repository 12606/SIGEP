from decimal import Decimal

from rest_framework import serializers

from .models import Ingrediente, MovimientoInventario
from .permissions import rol_usuario


class IngredienteSerializer(serializers.ModelSerializer):
    stock_actual = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    stock_bajo = serializers.SerializerMethodField()

    class Meta:
        model = Ingrediente
        fields = (
            "id", "nombre", "descripcion", "unidad_medida", "stock_minimo",
            "costo_unitario", "stock_actual", "stock_bajo", "activo", "fecha_registro",
        )
        read_only_fields = ("id", "stock_actual", "stock_bajo", "fecha_registro", "activo")

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and rol_usuario(request.user) == "REPOSTERO":
            fields.pop("costo_unitario", None)
        return fields

    def get_stock_bajo(self, ingrediente):
        return bool(ingrediente.activo and ingrediente.stock_actual <= ingrediente.stock_minimo)

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Indica el nombre del ingrediente.")
        return valor

    def validate(self, attrs):
        ingrediente = self.instance
        if ingrediente and "unidad_medida" in attrs:
            if attrs["unidad_medida"] != ingrediente.unidad_medida and ingrediente.movimientos.exists():
                raise serializers.ValidationError({
                    "unidad_medida": "No puedes cambiar la unidad de un ingrediente con movimientos históricos."
                })
        return attrs


class EstadoIngredienteSerializer(serializers.Serializer):
    activo = serializers.BooleanField()


class MovimientoCrearSerializer(serializers.Serializer):
    ingrediente_id = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(choices=MovimientoInventario.Tipo.choices)
    cantidad = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal("0.001")
    )
    motivo = serializers.CharField(max_length=250, allow_blank=False, trim_whitespace=True)


class MovimientoSerializer(serializers.ModelSerializer):
    ingrediente_nombre = serializers.CharField(source="ingrediente.nombre", read_only=True)
    unidad_medida = serializers.CharField(source="ingrediente.unidad_medida", read_only=True)
    usuario = serializers.CharField(source="registrado_por.username", read_only=True)

    class Meta:
        model = MovimientoInventario
        fields = (
            "id", "ingrediente", "ingrediente_nombre", "unidad_medida", "usuario",
            "tipo", "cantidad", "motivo", "fecha_movimiento",
        )
        read_only_fields = fields
