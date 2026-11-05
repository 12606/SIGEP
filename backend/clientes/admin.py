from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "apellidos", "telefono", "correo", "activo", "usuario")
    list_filter = ("activo",)
    search_fields = ("nombre", "apellidos", "correo", "telefono")
    readonly_fields = ("fecha_registro", "fecha_actualizacion")
