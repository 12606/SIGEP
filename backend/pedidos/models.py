from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de confirmar"
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        EN_PREPARACION = "EN_PREPARACION", "En preparación"
        LISTO = "LISTO", "Listo para entregar"
        ENTREGADO = "ENTREGADO", "Entregado"
        CANCELADO = "CANCELADO", "Cancelado"

    folio = models.CharField(max_length=24, unique=True, null=True, blank=True)
    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="pedidos"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="pedidos_registrados"
    )
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField()
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "pedidos"
        ordering = ("-fecha_pedido", "-id")
        indexes = [
            models.Index(fields=["estado", "fecha_entrega"], name="idx_pedido_estado_ent"),
            models.Index(fields=["cliente", "fecha_pedido"], name="idx_pedido_cliente_fecha"),
        ]

    @property
    def pagado(self):
        return self.pagos.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    @property
    def saldo(self):
        return self.total - self.pagado

    def __str__(self):
        return self.folio or f"Pedido #{self.pk}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT, related_name="detalles_pedido")
    nombre_producto = models.CharField(max_length=120)
    unidad_venta = models.CharField(max_length=10)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    personalizacion = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "detalle_pedido"
        ordering = ("id",)


class Pago(models.Model):
    class Metodo(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        TARJETA = "TARJETA", "Tarjeta"

    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="pagos")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="pagos_registrados"
    )
    fecha_pago = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    metodo = models.CharField(max_length=20, choices=Metodo.choices)
    referencia = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "pagos"
        ordering = ("fecha_pago", "id")

    def __str__(self):
        return f"{self.pedido.folio}: {self.monto}"
