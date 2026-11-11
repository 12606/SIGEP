from django.urls import path
from .views import (
    CategoriaDetalleView, CategoriaEstadoView, CategoriasView,
    ProductoDetalleView, ProductoEstadoView, ProductosView,
)

urlpatterns = [
    path("categorias/", CategoriasView.as_view(), name="categorias-producto"),
    path("categorias/<int:pk>/", CategoriaDetalleView.as_view(), name="categoria-producto-detalle"),
    path("categorias/<int:pk>/estado/", CategoriaEstadoView.as_view(), name="categoria-producto-estado"),
    path("productos/", ProductosView.as_view(), name="productos"),
    path("productos/<int:pk>/", ProductoDetalleView.as_view(), name="producto-detalle"),
    path("productos/<int:pk>/estado/", ProductoEstadoView.as_view(), name="producto-estado"),
]
