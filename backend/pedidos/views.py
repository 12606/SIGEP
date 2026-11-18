from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from clientes.models import Cliente
from productos.models import Producto
from .models import DetallePedido, Pago, Pedido
from .permissions import codigo_rol, exigir_rol
from .serializers import (
    CambioEstadoSerializer, PedidoCrearSerializer, PedidoProduccionSerializer, PedidoSerializer,
    PagoSerializer, RegistrarPagoSerializer,
)


ROLES_LECTURA = {"ADMIN", "VENTAS", "REPOSTERO", "CLIENTE"}
ROLES_ALTA = {"ADMIN", "VENTAS", "CLIENTE"}
ROLES_COBRO = {"ADMIN", "VENTAS"}


def pedidos_visibles(usuario):
    rol = exigir_rol(usuario, ROLES_LECTURA)
    qs = (Pedido.objects.select_related("cliente", "registrado_por")
          .prefetch_related("detalles", "pagos"))
    if rol == "CLIENTE":
        return qs.filter(cliente__usuario=usuario)
    if rol == "REPOSTERO":
        return qs.filter(estado__in=[
            Pedido.Estado.CONFIRMADO, Pedido.Estado.EN_PREPARACION,
            Pedido.Estado.LISTO,
        ])
    return qs


def presentar(usuario, instancia, many=False):
    serializer = PedidoProduccionSerializer if codigo_rol(usuario) == "REPOSTERO" else PedidoSerializer
    return serializer(instancia, many=many).data


class PedidosView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = pedidos_visibles(request.user)
        estado = request.query_params.get("estado", "").strip()
        if estado:
            if estado not in Pedido.Estado.values:
                raise ValidationError({"estado": "El estado solicitado no existe."})
            qs = qs.filter(estado=estado)
        buscar = request.query_params.get("buscar", "").strip()
        if buscar:
            if len(buscar) > 100:
                raise ValidationError({"buscar": "Búsqueda demasiado larga."})
            if codigo_rol(request.user) in {"ADMIN", "VENTAS"}:
                qs = qs.filter(Q(folio__icontains=buscar) | Q(cliente__nombre__icontains=buscar) | Q(cliente__apellidos__icontains=buscar))
            else:
                qs = qs.filter(folio__icontains=buscar)
        return Response(presentar(request.user, qs[:200], many=True))

    @transaction.atomic
    def post(self, request):
        rol = exigir_rol(request.user, ROLES_ALTA)
        entrada = PedidoCrearSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        if rol == "CLIENTE":
            if "cliente_id" in datos:
                raise ValidationError({"cliente_id": "No puedes elegir otra ficha de cliente."})
            cliente = Cliente.objects.filter(usuario=request.user, activo=True).first()
            if cliente is None:
                raise ValidationError({"cliente": "Tu cuenta no tiene una ficha activa. Contacta al administrador."})
        else:
            cliente_id = datos.get("cliente_id")
            if cliente_id is None:
                raise ValidationError({"cliente_id": "Selecciona un cliente."})
            cliente = get_object_or_404(Cliente, pk=cliente_id, activo=True)

        ids = [linea["producto_id"] for linea in datos["detalles"]]
        productos = {
            p.pk: p for p in Producto.objects.select_related("categoria")
            .select_for_update().filter(pk__in=ids)
        }
        total = Decimal("0.00")
        lineas = []
        for item in datos["detalles"]:
            producto = productos.get(item["producto_id"])
            if not producto or not producto.activo or not producto.categoria.activo:
                raise ValidationError({"detalles": "Hay productos inexistentes o inactivos."})
            cantidad = item["cantidad"]
            precio = producto.precio_base
            subtotal = precio * cantidad
            total += subtotal
            lineas.append((producto, cantidad, precio, subtotal, item.get("personalizacion", "")))

        if total > Decimal("9999999999.99"):
            raise ValidationError({"detalles": "El total supera el máximo permitido."})

        pedido = Pedido.objects.create(
            cliente=cliente, registrado_por=request.user,
            fecha_entrega=datos["fecha_entrega"], observaciones=datos.get("observaciones", ""),
            subtotal=total, total=total,
        )
        pedido.folio = f"PED-{pedido.pk:06d}"
        pedido.save(update_fields=["folio"])
        DetallePedido.objects.bulk_create([
            DetallePedido(
                pedido=pedido, producto=p, nombre_producto=p.nombre,
                unidad_venta=p.unidad_venta, cantidad=cantidad,
                precio_unitario=precio, subtotal=subtotal, personalizacion=nota,
            )
            for p, cantidad, precio, subtotal, nota in lineas
        ])
        pedido = pedidos_visibles(request.user).get(pk=pedido.pk)
        return Response(presentar(request.user, pedido), status=status.HTTP_201_CREATED)


class PedidoDetalleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        pedido = get_object_or_404(pedidos_visibles(request.user), pk=pk)
        return Response(presentar(request.user, pedido))


TRANSICIONES = {
    Pedido.Estado.PENDIENTE: {Pedido.Estado.CONFIRMADO: {"ADMIN", "VENTAS"}, Pedido.Estado.CANCELADO: {"ADMIN", "VENTAS"}},
    Pedido.Estado.CONFIRMADO: {Pedido.Estado.EN_PREPARACION: {"ADMIN", "REPOSTERO"}, Pedido.Estado.CANCELADO: {"ADMIN", "VENTAS"}},
    Pedido.Estado.EN_PREPARACION: {Pedido.Estado.LISTO: {"ADMIN", "REPOSTERO"}},
    Pedido.Estado.LISTO: {Pedido.Estado.ENTREGADO: {"ADMIN", "VENTAS"}},
}


class CambiarEstadoPedidoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        rol = exigir_rol(request.user, {"ADMIN", "VENTAS", "REPOSTERO"})
        entrada = CambioEstadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pk)
        nuevo = entrada.validated_data["estado"]
        autorizados = TRANSICIONES.get(pedido.estado, {}).get(nuevo, set())
        if rol not in autorizados:
            raise ValidationError({"estado": "Transición no permitida para el estado actual o tu rol."})
        if nuevo == Pedido.Estado.CANCELADO and pedido.pagos.exists():
            raise ValidationError({"estado": "Un pedido con pagos requiere un proceso de devolución; no se puede cancelar aquí."})
        pedido.estado = nuevo
        pedido.save(update_fields=["estado"])
        return Response(presentar(request.user, pedidos_visibles(request.user).get(pk=pk)))


class PagosPedidoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        pedido = get_object_or_404(pedidos_visibles(request.user), pk=pk)
        if codigo_rol(request.user) == "REPOSTERO":
            raise PermissionDenied("La consulta de pagos está reservada a ventas, administración y el cliente.")
        return Response(PagoSerializer(pedido.pagos.all(), many=True).data)

    @transaction.atomic
    def post(self, request, pk):
        exigir_rol(request.user, ROLES_COBRO)
        entrada = RegistrarPagoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pk)
        if pedido.estado == Pedido.Estado.CANCELADO:
            raise ValidationError({"pedido": "No se pueden registrar pagos en pedidos cancelados."})
        pagado = pedido.pagos.aggregate(suma=Sum("monto"))["suma"] or Decimal("0.00")
        saldo = pedido.total - pagado
        monto = entrada.validated_data["monto"]
        if monto > saldo:
            raise ValidationError({"monto": f"El pago supera el saldo disponible de {saldo}."})
        pago = Pago.objects.create(
            pedido=pedido, registrado_por=request.user,
            monto=monto, metodo=entrada.validated_data["metodo"],
            referencia=entrada.validated_data.get("referencia", ""),
        )
        return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)
