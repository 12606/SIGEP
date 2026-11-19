from django.contrib import admin

from .models import Ingrediente, MovimientoInventario


@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "unidad_medida", "stock_minimo", "activo")
    search_fields = ("nombre",)
    list_filter = ("unidad_medida", "activo")
    readonly_fields = ("fecha_registro",)


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ("id", "ingrediente", "tipo", "cantidad", "fecha_movimiento", "registrado_por")
    list_filter = ("tipo", "fecha_movimiento")
    search_fields = ("ingrediente__nombre", "motivo")
    readonly_fields = ("ingrediente", "tipo", "cantidad", "motivo", "registrado_por", "fecha_movimiento")

    def has_add_permission(self, request):
        # Los movimientos se crean exclusivamente por API para respetar validaciones de stock.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
