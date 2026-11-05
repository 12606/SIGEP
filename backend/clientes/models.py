from django.conf import settings
from django.db import models


class Cliente(models.Model):
    """Cliente de la pastelería, con o sin cuenta web.

    Se distingue de Usuario: Usuario controla acceso, Cliente contiene
    información comercial. El vínculo es opcional para ventas de mostrador.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfil_cliente",
    )
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    direccion = models.CharField(max_length=250, blank=True)
    observaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clientes"
        ordering = ["apellidos", "nombre", "id"]
        indexes = [models.Index(fields=["activo", "apellidos"], name="idx_cliente_activo_ap")]

    def __str__(self):
        return f"{self.nombre} {self.apellidos}".strip()
