from django.urls import path

from .views import CambiarEstadoPedidoView, PagosPedidoView, PedidoDetalleView, PedidosView

urlpatterns = [
    path("pedidos/", PedidosView.as_view(), name="pedidos"),
    path("pedidos/<int:pk>/", PedidoDetalleView.as_view(), name="pedido-detalle"),
    path("pedidos/<int:pk>/estado/", CambiarEstadoPedidoView.as_view(), name="pedido-estado"),
    path("pedidos/<int:pk>/pagos/", PagosPedidoView.as_view(), name="pedido-pagos"),
]
