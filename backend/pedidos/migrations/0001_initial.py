from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("clientes", "0001_initial"),
        ("productos", "0002_producto_imagen"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="Pedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("folio", models.CharField(blank=True, max_length=24, null=True, unique=True)),
                ("fecha_pedido", models.DateTimeField(auto_now_add=True)),
                ("fecha_entrega", models.DateTimeField()),
                ("estado", models.CharField(choices=[("PENDIENTE", "Pendiente de confirmar"), ("CONFIRMADO", "Confirmado"), ("EN_PREPARACION", "En preparación"), ("LISTO", "Listo para entregar"), ("ENTREGADO", "Entregado"), ("CANCELADO", "Cancelado")], default="PENDIENTE", max_length=20)),
                ("subtotal", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("observaciones", models.TextField(blank=True)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="clientes.cliente")),
                ("registrado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pedidos_registrados", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "pedidos", "ordering": ("-fecha_pedido", "-id")},
        ),
        migrations.CreateModel(
            name="DetallePedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre_producto", models.CharField(max_length=120)),
                ("unidad_venta", models.CharField(max_length=10)),
                ("cantidad", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("precio_unitario", models.DecimalField(decimal_places=2, max_digits=12)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=12)),
                ("personalizacion", models.CharField(blank=True, max_length=500)),
                ("pedido", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalles", to="pedidos.pedido")),
                ("producto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="detalles_pedido", to="productos.producto")),
            ],
            options={"db_table": "detalle_pedido", "ordering": ("id",)},
        ),
        migrations.CreateModel(
            name="Pago",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha_pago", models.DateTimeField(auto_now_add=True)),
                ("monto", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("metodo", models.CharField(choices=[("EFECTIVO", "Efectivo"), ("TRANSFERENCIA", "Transferencia"), ("TARJETA", "Tarjeta")], max_length=20)),
                ("referencia", models.CharField(blank=True, max_length=120)),
                ("pedido", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pagos", to="pedidos.pedido")),
                ("registrado_por", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pagos_registrados", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "pagos", "ordering": ("fecha_pago", "id")},
        ),
        migrations.AddIndex(model_name="pedido", index=models.Index(fields=["estado", "fecha_entrega"], name="idx_pedido_estado_ent")),
        migrations.AddIndex(model_name="pedido", index=models.Index(fields=["cliente", "fecha_pedido"], name="idx_pedido_cliente_fecha")),
    ]
