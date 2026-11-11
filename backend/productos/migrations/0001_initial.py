from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CategoriaProducto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=90, unique=True)),
                ("descripcion", models.CharField(blank=True, max_length=250)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "categorias_producto",
                "ordering": ("nombre", "id"),
                "verbose_name": "Categoría de producto",
                "verbose_name_plural": "Categorías de productos",
            },
        ),
        migrations.CreateModel(
            name="Producto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120)),
                ("descripcion", models.TextField(blank=True)),
                ("precio_base", models.DecimalField(
                    decimal_places=2, max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                )),
                ("unidad_venta", models.CharField(
                    choices=[("PIEZA", "Pieza"), ("CAJA", "Caja"), ("PORCION", "Porción"), ("KG", "Kilogramo")],
                    default="PIEZA", max_length=10,
                )),
                ("imagen_url", models.URLField(blank=True, max_length=500)),
                ("activo", models.BooleanField(default=True)),
                ("categoria", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="productos", to="productos.categoriaproducto",
                )),
            ],
            options={
                "db_table": "productos", "ordering": ("nombre", "id"),
                "verbose_name": "Producto", "verbose_name_plural": "Productos",
            },
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.UniqueConstraint(
                fields=("categoria", "nombre"), name="uniq_producto_categoria_nombre"
            ),
        ),
    ]
