from django.contrib import admin
from .models import CategoriaProducto, Producto


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "descripcion")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "categoria", "precio_base", "unidad_venta", "activo")
    list_filter = ("activo", "categoria", "unidad_venta")
    search_fields = ("nombre", "descripcion", "categoria__nombre")
