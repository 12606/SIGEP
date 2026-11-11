from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CategoriaProducto, Producto
from .permissions import PuedeGestionarCatalogo, es_admin
from .serializers import (
    CategoriaProductoSerializer, EstadoSerializer, ProductoSerializer
)


def validar_activo(request):
    valor = request.query_params.get("activo")
    if valor is None or valor == "":
        return None
    if valor.lower() not in ("true", "false"):
        raise serializers.ValidationError({"activo": "Usa true o false."})
    return valor.lower() == "true"


class CategoriasView(generics.ListCreateAPIView):
    permission_classes = (PuedeGestionarCatalogo,)
    serializer_class = CategoriaProductoSerializer
    pagination_class = None
    queryset = CategoriaProducto.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if not es_admin(self.request.user):
            queryset = queryset.filter(activo=True)
        activo = validar_activo(self.request)
        if activo is not None:
            queryset = queryset.filter(activo=activo)
        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar) | Q(descripcion__icontains=buscar)
            )
        return queryset


class CategoriaDetalleView(generics.RetrieveUpdateAPIView):
    permission_classes = (PuedeGestionarCatalogo,)
    serializer_class = CategoriaProductoSerializer
    queryset = CategoriaProducto.objects.all()
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        if not es_admin(self.request.user):
            queryset = queryset.filter(activo=True)
        return queryset


class CategoriaEstadoView(APIView):
    permission_classes = (PuedeGestionarCatalogo,)

    def patch(self, request, pk):
        categoria = get_object_or_404(CategoriaProducto, pk=pk)
        entrada = EstadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        activo = entrada.validated_data["activo"]
        if not activo and categoria.productos.filter(activo=True).exists():
            raise serializers.ValidationError({
                "activo": "Desactiva o reasigna los productos activos antes de desactivar esta categoría."
            })
        categoria.activo = activo
        categoria.save(update_fields=("activo",))
        return Response(CategoriaProductoSerializer(categoria).data)


class ProductosView(generics.ListCreateAPIView):
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = (PuedeGestionarCatalogo,)
    serializer_class = ProductoSerializer
    pagination_class = None
    queryset = Producto.objects.select_related("categoria").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if not es_admin(self.request.user):
            queryset = queryset.filter(activo=True, categoria__activo=True)
        activo = validar_activo(self.request)
        if activo is not None:
            queryset = queryset.filter(activo=activo)
        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(descripcion__icontains=buscar)
                | Q(categoria__nombre__icontains=buscar)
            )
        categoria_id = self.request.query_params.get("categoria")
        if categoria_id:
            if not categoria_id.isdecimal() or int(categoria_id) < 1:
                raise serializers.ValidationError({"categoria": "Indica un ID de categoría válido."})
            queryset = queryset.filter(categoria_id=int(categoria_id))
        return queryset


class ProductoDetalleView(generics.RetrieveUpdateAPIView):
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = (PuedeGestionarCatalogo,)
    serializer_class = ProductoSerializer
    queryset = Producto.objects.select_related("categoria").all()
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        if not es_admin(self.request.user):
            queryset = queryset.filter(activo=True, categoria__activo=True)
        return queryset


class ProductoEstadoView(APIView):
    permission_classes = (PuedeGestionarCatalogo,)

    def patch(self, request, pk):
        producto = get_object_or_404(
            Producto.objects.select_related("categoria"), pk=pk
        )
        entrada = EstadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        activo = entrada.validated_data["activo"]
        if activo and not producto.categoria.activo:
            raise serializers.ValidationError({
                "activo": "Activa primero la categoría del producto."
            })
        producto.activo = activo
        producto.save(update_fields=("activo",))
        return Response(ProductoSerializer(producto).data)
