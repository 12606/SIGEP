# Migración inicial del inventario de SIGEP.
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Ingrediente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120, unique=True)),
                ("descripcion", models.CharField(blank=True, max_length=250)),
                ("unidad_medida", models.CharField(choices=[("KG", "Kilogramo"), ("G", "Gramo"), ("L", "Litro"), ("ML", "Mililitro"), ("PIEZA", "Pieza")], max_length=10)),
                ("stock_minimo", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.000"))])),
                ("costo_unitario", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("activo", models.BooleanField(default=True)),
                ("fecha_registro", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ingredientes", "ordering": ("nombre", "id"), "verbose_name": "Ingrediente", "verbose_name_plural": "Ingredientes"},
        ),
        migrations.CreateModel(
            name="MovimientoInventario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("ENTRADA", "Entrada"), ("SALIDA", "Salida"), ("MERMA", "Merma")], max_length=10)),
                ("cantidad", models.DecimalField(decimal_places=3, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.001"))])),
                ("motivo", models.CharField(max_length=250)),
                ("fecha_movimiento", models.DateTimeField(auto_now_add=True)),
                ("ingrediente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movimientos", to="inventario.ingrediente")),
                ("registrado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movimientos_inventario", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "movimientos_inventario", "ordering": ("-fecha_movimiento", "-id")},
        ),
        migrations.AddIndex(
            model_name="movimientoinventario",
            index=models.Index(fields=["ingrediente", "fecha_movimiento"], name="idx_mov_ing_fecha"),
        ),
    ]
