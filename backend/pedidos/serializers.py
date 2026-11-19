from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import DetallePedido, Pago, Pedido


class DetalleEntradaSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1, max_value=100)
    personalizacion = serializers.CharField(required=False, allow_blank=True, max_length=500)


class PedidoCrearSerializer(serializers.Serializer):
    cliente_id = serializers.IntegerField(required=False, min_value=1)
    fecha_entrega = serializers.DateTimeField()
    observaciones = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    detalles = DetalleEntradaSerializer(many=True)

    def validate_fecha_entrega(self, value):
        ahora = timezone.now()
        if value <= ahora:
            raise serializers.ValidationError("La entrega debe programarse para una fecha futura.")
        if value > ahora + timedelta(days=365):
            raise serializers.ValidationError("La fecha de entrega no puede superar un año.")
        return value

    def validate_detalles(self, value):
        if not 1 <= len(value) <= 20:
            raise serializers.ValidationError("Agrega entre 1 y 20 líneas de productos.")
        return value


class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = DetallePedido
        fields = ("id", "producto_id", "nombre_producto", "unidad_venta", "cantidad", "precio_unitario", "subtotal", "personalizacion")


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ("id", "fecha_pago", "monto", "metodo", "referencia")


class PedidoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.SerializerMethodField()
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    pagos = PagoSerializer(many=True, read_only=True)
    pagado = serializers.SerializerMethodField()
    saldo = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = (
            "id", "folio", "cliente", "cliente_nombre", "registrado_por", "fecha_pedido",
            "fecha_entrega", "estado", "subtotal", "total", "pagado", "saldo",
            "observaciones", "detalles", "pagos",
        )
        read_only_fields = fields

    def get_cliente_nombre(self, obj):
        return str(obj.cliente)

    def _pagado(self, obj):
        # Prefetch de pagos, utilizado en los listados para evitar una consulta por pedido.
        if "pagos" in getattr(obj, "_prefetched_objects_cache", {}):
            return sum((p.monto for p in obj.pagos.all()), Decimal("0.00"))
        return obj.pagado

    def get_pagado(self, obj):
        return self._pagado(obj)

    def get_saldo(self, obj):
        return obj.total - self._pagado(obj)


class PedidoProduccionSerializer(serializers.ModelSerializer):
    """Vista del repostero: no expone importes, pagos ni referencias de cobro."""
    cliente_nombre = serializers.SerializerMethodField()
    detalles = DetallePedidoSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = (
            "id", "folio", "cliente_nombre", "fecha_entrega",
            "estado", "observaciones", "detalles",
        )
        read_only_fields = fields

    def get_cliente_nombre(self, obj):
        return str(obj.cliente)


class CambioEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=Pedido.Estado.choices)


class RegistrarPagoSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    metodo = serializers.ChoiceField(choices=Pago.Metodo.choices)
    referencia = serializers.CharField(required=False, allow_blank=True, max_length=120)
