from django.urls import path
from .views import ClientesView, ClienteDetalleView, EstadoClienteView, MiFichaClienteView

urlpatterns = [
    path("clientes/me/", MiFichaClienteView.as_view(), name="cliente-me"),
    path("clientes/", ClientesView.as_view(), name="clientes"),
    path("clientes/<int:pk>/", ClienteDetalleView.as_view(), name="cliente-detalle"),
    path("clientes/<int:pk>/estado/", EstadoClienteView.as_view(), name="cliente-estado"),
]
