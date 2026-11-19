from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cliente
from .permissions import EsAdministradorOVentas, EsAdministradorClientes, EsClientePropio, codigo_rol
from .serializers import ClienteSerializer, EstadoClienteSerializer, MiFichaClienteSerializer


class ClientesView(generics.ListCreateAPIView):
    """Lista y alta manual. Sin DELETE para conservar el historial comercial."""
    permission_classes = [EsAdministradorOVentas]
    serializer_class = ClienteSerializer
    queryset = Cliente.objects.select_related("usuario__rol").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if codigo_rol(self.request.user) == "VENTAS":
            # No mostrar perfiles de empleados en el directorio comercial.
            queryset = queryset.filter(Q(usuario__isnull=True) | Q(usuario__rol__codigo="CLIENTE"))
        buscar = self.request.query_params.get("buscar", "").strip()
        activo = self.request.query_params.get("activo")
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(apellidos__icontains=buscar)
                | Q(telefono__icontains=buscar)
                | Q(correo__icontains=buscar)
            )
        if activo is not None:
            if activo.lower() not in ("true", "false"):
                raise serializers.ValidationError({"activo": "Usa true o false."})
            queryset = queryset.filter(activo=(activo.lower() == "true"))
        return queryset


class ClienteDetalleView(generics.RetrieveUpdateAPIView):
    permission_classes = [EsAdministradorOVentas]
    serializer_class = ClienteSerializer
    queryset = Cliente.objects.select_related("usuario__rol").all()
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        qs = super().get_queryset()
        if codigo_rol(self.request.user) == "VENTAS":
            return qs.filter(Q(usuario__isnull=True) | Q(usuario__rol__codigo="CLIENTE"))
        return qs


class EstadoClienteView(APIView):
    permission_classes = [EsAdministradorClientes]

    def patch(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        entrada = EstadoClienteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cliente.activo = entrada.validated_data["activo"]
        cliente.save(update_fields=["activo", "fecha_actualizacion"])
        return Response(ClienteSerializer(cliente).data)


class MiFichaClienteView(generics.RetrieveUpdateAPIView):
    """Un CLIENTE puede ver y editar solo su ficha, no sus privilegios."""
    permission_classes = [EsClientePropio]
    serializer_class = MiFichaClienteSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return get_object_or_404(Cliente, usuario=self.request.user, activo=True)
