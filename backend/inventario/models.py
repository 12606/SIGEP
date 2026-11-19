"""Inventario por movimientos. La existencia no se edita directamente."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum


class Ingrediente(models.Model):
    class Unidad(models.TextChoices):
        KG = "KG", "Kilogramo"
        G = "G", "Gramo"
        L = "L", "Litro"
        ML = "ML", "Mililitro"
        PIEZA = "PIEZA", "Pieza"

    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=250, blank=True)
    unidad_medida = models.CharField(max_length=10, choices=Unidad.choices)
    stock_minimo = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
    )
    costo_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ingredientes"
        ordering = ("nombre", "id")
        verbose_name = "Ingrediente"
        verbose_name_plural = "Ingredientes"

    @property
    def stock_actual(self):
        """Stock calculado; nunca se almacena una segunda cifra de existencia."""
        if hasattr(self, "_stock_calculado"):
            return self._stock_calculado
        acumulados = self.movimientos.aggregate(
            entradas=Sum("cantidad", filter=Q(tipo=MovimientoInventario.Tipo.ENTRADA)),
            salidas=Sum("cantidad", filter=Q(tipo__in=(
                MovimientoInventario.Tipo.SALIDA, MovimientoInventario.Tipo.MERMA
            ))),
        )
        return (acumulados["entradas"] or Decimal("0.000")) - (
            acumulados["salidas"] or Decimal("0.000")
        )

    def __str__(self):
        return self.nombre


class MovimientoInventario(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"
        MERMA = "MERMA", "Merma"

    ingrediente = models.ForeignKey(
        Ingrediente, on_delete=models.PROTECT, related_name="movimientos"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="movimientos_inventario",
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    motivo = models.CharField(max_length=250)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "movimientos_inventario"
        ordering = ("-fecha_movimiento", "-id")
        indexes = [
            models.Index(fields=["ingrediente", "fecha_movimiento"], name="idx_mov_ing_fecha"),
        ]

    def __str__(self):
        return f"{self.tipo} {self.cantidad} {self.ingrediente.nombre}"
