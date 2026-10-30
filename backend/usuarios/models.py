from django.contrib.auth.models import AbstractUser
from django.db import models

class Rol(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=60)
    descripcion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "roles"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name="usuarios", null=True, blank=True)

    class Meta:
        db_table = "usuarios"

    def __str__(self):
        return self.username
