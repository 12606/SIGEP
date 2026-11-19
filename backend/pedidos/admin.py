from django.contrib import admin

from .models import DetallePedido, Pago, Pedido


class DetalleInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    can_delete = False
    readonly_fields = ("producto", "nombre_producto", "unidad_venta", "cantidad", "precio_unitario", "subtotal", "personalizacion")

    def has_add_permission(self, request, obj=None):
        return False


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    can_delete = False
    readonly_fields = ("fecha_pago", "monto", "metodo", "referencia", "registrado_por")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("folio", "cliente", "estado", "fecha_pedido", "fecha_entrega", "total")
    list_filter = ("estado", "fecha_entrega")
    search_fields = ("folio", "cliente__nombre", "cliente__apellidos")
    inlines = (DetalleInline, PagoInline)
    readonly_fields = ("folio", "cliente", "registrado_por", "fecha_pedido", "fecha_entrega", "estado", "subtotal", "total", "observaciones")

    def has_add_permission(self, request):
        return False  # Crear pedidos por la API para conservar totales y precios históricos.

    def has_delete_permission(self, request, obj=None):
        return False
