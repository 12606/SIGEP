from django.db import migrations, models
import productos.models


class Migration(migrations.Migration):
    dependencies = [("productos", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="imagen",
            field=models.ImageField(
                upload_to=productos.models.ruta_imagen_producto,
                blank=True,
                null=True,
            ),
        ),
    ]
