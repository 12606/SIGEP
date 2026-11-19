from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ingrediente, MovimientoInventario
from .permissions import exigir_rol
from .serializers import (
    EstadoIngredienteSerializer, IngredienteSerializer,
    MovimientoCrearSerializer, MovimientoSerializer,
)

ROLES_LECTURA = {"ADMIN", "ALMACEN", "REPOSTERO"}
ROLES_ESCRITURA = {"ADMIN", "ALMACEN"}


def filtrar_ingredientes(request):
    rol = exigir_rol(request.user, ROLES_LECTURA)
    queryset = Ingrediente.objects.all()
    if rol == "REPOSTERO":
        queryset = queryset.filter(activo=True)
    buscar = request.query_params.get("buscar", "").strip()
    if len(buscar) > 100:
        raise ValidationError({"buscar": "La búsqueda es demasiado larga."})
    if buscar:
        queryset = queryset.filter(Q(nombre__icontains=buscar) | Q(descripcion__icontains=buscar))
    activo = request.query_params.get("activo")
    if activo is not None:
        if activo.lower() not in ("true", "false"):
            raise ValidationError({"activo": "Utiliza true o false."})
        queryset = queryset.filter(activo=activo.lower() == "true")
    return queryset


class IngredientesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ingredientes = filtrar_ingredientes(request)[:250]
        return Response(IngredienteSerializer(ingredientes, many=True, context={"request": request}).data)

    def post(self, request):
        exigir_rol(request.user, ROLES_ESCRITURA)
        entrada = IngredienteSerializer(data=request.data, context={"request": request})
        entrada.is_valid(raise_exception=True)
        ingrediente = entrada.save()
        return Response(IngredienteSerializer(ingrediente, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)


class IngredienteDetalleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        ingrediente = get_object_or_404(filtrar_ingredientes(request), pk=pk)
        return Response(IngredienteSerializer(ingrediente, context={"request": request}).data)

    def patch(self, request, pk):
        exigir_rol(request.user, ROLES_ESCRITURA)
        ingrediente = get_object_or_404(Ingrediente, pk=pk)
        entrada = IngredienteSerializer(ingrediente, data=request.data, partial=True,
                                       context={"request": request})
        entrada.is_valid(raise_exception=True)
        entrada.save()
        return Response(entrada.data)


class EstadoIngredienteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        exigir_rol(request.user, {"ADMIN"})
        entrada = EstadoIngredienteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        ingrediente = get_object_or_404(Ingrediente, pk=pk)
        ingrediente.activo = entrada.validated_data["activo"]
        ingrediente.save(update_fields=["activo"])
        return Response(IngredienteSerializer(ingrediente, context={"request": request}).data)


class AlertasInventarioView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        exigir_rol(request.user, ROLES_LECTURA)
        ingredientes = [i for i in Ingrediente.objects.filter(activo=True) if i.stock_actual <= i.stock_minimo]
        return Response(IngredienteSerializer(ingredientes[:250], many=True,
                                              context={"request": request}).data)


class MovimientosInventarioView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        exigir_rol(request.user, ROLES_ESCRITURA)
        qs = MovimientoInventario.objects.select_related("ingrediente", "registrado_por")
        ing = request.query_params.get("ingrediente")
        if ing:
            if not ing.isdecimal() or int(ing) < 1:
                raise ValidationError({"ingrediente": "Indica un ID válido."})
            qs = qs.filter(ingrediente_id=int(ing))
        return Response(MovimientoSerializer(qs[:200], many=True).data)

    @transaction.atomic
    def post(self, request):
        exigir_rol(request.user, ROLES_ESCRITURA)
        entrada = MovimientoCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        ingrediente = get_object_or_404(
            Ingrediente.objects.select_for_update(), pk=datos["ingrediente_id"]
        )
        if not ingrediente.activo:
            raise ValidationError({"ingrediente_id": "El ingrediente está inactivo."})
        cantidad = datos["cantidad"]
        if ingrediente.unidad_medida == Ingrediente.Unidad.PIEZA and cantidad != cantidad.to_integral_value():
            raise ValidationError({"cantidad": "Las piezas deben registrarse en números enteros."})
        if datos["tipo"] != MovimientoInventario.Tipo.ENTRADA and ingrediente.stock_actual < cantidad:
            raise ValidationError({"cantidad": "No hay existencias suficientes para registrar la salida."})
        movimiento = MovimientoInventario.objects.create(
            ingrediente=ingrediente, registrado_por=request.user,
            tipo=datos["tipo"], cantidad=cantidad, motivo=datos["motivo"],
        )
        return Response(MovimientoSerializer(movimiento).data, status=status.HTTP_201_CREATED)
