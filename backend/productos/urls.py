from django.urls import path
from .catalogo_publico import (
    CatalogoCategoriasView, CatalogoProductosView, CatalogoProductoDetalleView,
)
from .views import (
    CategoriaDetalleView, CategoriaEstadoView, CategoriasView,
    ProductoDetalleView, ProductoEstadoView, ProductosView,
)

urlpatterns = [
    # Solo lectura, disponible para clientes y visitantes; NO modifica las rutas de administración.
    path("catalogo/categorias/", CatalogoCategoriasView.as_view(), name="catalogo-categorias"),
    path("catalogo/productos/", CatalogoProductosView.as_view(), name="catalogo-productos"),
    path("catalogo/productos/<int:pk>/", CatalogoProductoDetalleView.as_view(), name="catalogo-producto-detalle"),
    path("categorias/", CategoriasView.as_view(), name="categorias-producto"),
    path("categorias/<int:pk>/", CategoriaDetalleView.as_view(), name="categoria-producto-detalle"),
    path("categorias/<int:pk>/estado/", CategoriaEstadoView.as_view(), name="categoria-producto-estado"),
    path("productos/", ProductosView.as_view(), name="productos"),
    path("productos/<int:pk>/", ProductoDetalleView.as_view(), name="producto-detalle"),
    path("productos/<int:pk>/estado/", ProductoEstadoView.as_view(), name="producto-estado"),
]
