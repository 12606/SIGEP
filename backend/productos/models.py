from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from django.core.validators import MinValueValidator
from django.db import models


def ruta_imagen_producto(instance, nombre_archivo):
    """El nombre original no se usa para guardar el archivo en el servidor."""
    extension = Path(nombre_archivo).suffix.lower()
    return f"productos/{uuid4().hex}{extension}"


class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=90, unique=True)
    descripcion = models.CharField(max_length=250, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "categorias_producto"
        ordering = ("nombre", "id")
        verbose_name = "Categoría de producto"
        verbose_name_plural = "Categorías de productos"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    class UnidadVenta(models.TextChoices):
        PIEZA = "PIEZA", "Pieza"
        CAJA = "CAJA", "Caja"
        PORCION = "PORCION", "Porción"
        KG = "KG", "Kilogramo"

    categoria = models.ForeignKey(
        CategoriaProducto, on_delete=models.PROTECT, related_name="productos"
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    precio_base = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    unidad_venta = models.CharField(
        max_length=10, choices=UnidadVenta.choices, default=UnidadVenta.PIEZA
    )
    # Compatibilidad: se conserva el enlace de productos creados antes de la carga.
    imagen_url = models.URLField(max_length=500, blank=True)
    imagen = models.ImageField(upload_to=ruta_imagen_producto, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "productos"
        ordering = ("nombre", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("categoria", "nombre"),
                name="uniq_producto_categoria_nombre"
            )
        ]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"
