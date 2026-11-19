from django.urls import path

from .views import (
    AlertasInventarioView, EstadoIngredienteView, IngredienteDetalleView,
    IngredientesView, MovimientosInventarioView,
)

urlpatterns = [
    path("inventario/ingredientes/", IngredientesView.as_view(), name="inventario-ingredientes"),
    path("inventario/ingredientes/<int:pk>/", IngredienteDetalleView.as_view(), name="inventario-ingrediente-detalle"),
    path("inventario/ingredientes/<int:pk>/estado/", EstadoIngredienteView.as_view(), name="inventario-ingrediente-estado"),
    path("inventario/movimientos/", MovimientosInventarioView.as_view(), name="inventario-movimientos"),
    path("inventario/alertas/", AlertasInventarioView.as_view(), name="inventario-alertas"),
]
