from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100)),
                ("apellidos", models.CharField(max_length=150)),
                ("telefono", models.CharField(blank=True, max_length=20)),
                ("correo", models.EmailField(blank=True, max_length=254)),
                ("direccion", models.CharField(blank=True, max_length=250)),
                ("observaciones", models.TextField(blank=True)),
                ("activo", models.BooleanField(default=True)),
                ("fecha_registro", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                ("usuario", models.OneToOneField(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="perfil_cliente", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "clientes", "ordering": ["apellidos", "nombre", "id"]},
        ),
        migrations.AddIndex(
            model_name="cliente",
            index=models.Index(fields=["activo", "apellidos"], name="idx_cliente_activo_ap"),
        ),
    ]
