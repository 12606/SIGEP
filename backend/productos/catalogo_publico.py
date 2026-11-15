"""Catálogo público de lectura. No reutiliza los endpoints administrativos.

Solo se exponen productos activos en categorías activas, también para usuarios anónimos.
La administración del catálogo sigue protegida en /api/productos/ y /api/categorias/.
"""
from django.db.models import Q
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny

from .models import CategoriaProducto, Producto


class CategoriaPublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaProducto
        fields = ("id", "nombre", "descripcion")
        read_only_fields = fields


class ProductoPublicoSerializer(serializers.ModelSerializer):
    categoria = serializers.IntegerField(source="categoria_id", read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = (
            "id", "categoria", "categoria_nombre", "nombre", "descripcion",
            "precio_base", "unidad_venta", "imagen_url",
        )
        read_only_fields = fields

    def get_imagen_url(self, producto):
        if producto.imagen:
            ruta = producto.imagen.url
            request = self.context.get("request")
            return request.build_absolute_uri(ruta) if request else ruta
        return producto.imagen_url or ""


class CatalogoCategoriasView(generics.ListAPIView):
    """GET /api/catalogo/categorias/ — categorías activas."""
    permission_classes = (AllowAny,)
    authentication_classes = ()
    serializer_class = CategoriaPublicaSerializer
    pagination_class = None
    queryset = CategoriaProducto.objects.filter(activo=True).order_by("nombre", "id")


class CatalogoProductosView(generics.ListAPIView):
    """GET /api/catalogo/productos/?buscar=texto&categoria=ID"""
    permission_classes = (AllowAny,)
    authentication_classes = ()
    serializer_class = ProductoPublicoSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").filter(
            activo=True, categoria__activo=True
        ).order_by("nombre", "id")
        buscar = self.request.query_params.get("buscar", "").strip()
        if len(buscar) > 120:
            raise serializers.ValidationError({"buscar": "La búsqueda es demasiado larga."})
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(descripcion__icontains=buscar)
                | Q(categoria__nombre__icontains=buscar)
            )
        categoria = self.request.query_params.get("categoria", "").strip()
        if categoria:
            if not categoria.isdecimal() or int(categoria) < 1:
                raise serializers.ValidationError({"categoria": "Indica un ID de categoría válido."})
            queryset = queryset.filter(categoria_id=int(categoria))
        return queryset


class CatalogoProductoDetalleView(generics.RetrieveAPIView):
    """GET /api/catalogo/productos/<id>/ — detalles, solo si está publicado."""
    permission_classes = (AllowAny,)
    authentication_classes = ()
    serializer_class = ProductoPublicoSerializer
    queryset = Producto.objects.select_related("categoria").filter(
        activo=True, categoria__activo=True
    )
