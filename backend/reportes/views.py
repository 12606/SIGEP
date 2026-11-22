"""Indicadores y exportaciones de SIGEP.

Todos los reportes son exclusivamente ADMIN: no deben incluir datos
financieros en endpoints accesibles para ventas, clientes o producción.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from clientes.models import Cliente
from inventario.models import Ingrediente, MovimientoInventario
from pedidos.models import DetallePedido, Pago, Pedido

CERO = Decimal("0.00")
MAX_DIAS = 366
MAX_FILAS_EXPORTACION = 5000


def _autorizado(usuario):
    """Valida la sesión y el rol en el servidor; nunca confía en la interfaz."""
    if not usuario or not usuario.is_authenticated or not usuario.is_active:
        raise PermissionDenied("No tienes acceso a reportes administrativos.")
    if usuario.is_superuser:
        return
    rol = getattr(usuario, "rol", None)
    if not rol or not rol.activo or rol.codigo != "ADMIN":
        raise PermissionDenied("Solo ADMIN puede consultar reportes y cifras financieras.")


def _fecha(valor, nombre):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ValidationError({nombre: "Utiliza una fecha válida con formato AAAA-MM-DD."})


def _rango(request):
    """Fecha local inclusiva; límite superior exclusivo para incluir todo el día."""
    hoy = timezone.localdate()
    desde = _fecha(request.query_params.get("desde", (hoy - timedelta(days=29)).isoformat()), "desde")
    hasta = _fecha(request.query_params.get("hasta", hoy.isoformat()), "hasta")
    if desde > hasta:
        raise ValidationError({"hasta": "La fecha final no puede ser anterior a la inicial."})
    if (hasta - desde).days >= MAX_DIAS:
        raise ValidationError({"hasta": "Consulta un máximo de 366 días por reporte."})
    tz = timezone.get_current_timezone()
    inicial = timezone.make_aware(datetime.combine(desde, time.min), tz)
    final = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), tz)
    return desde, hasta, inicial, final


def _dinero(valor):
    return str((valor if valor is not None else CERO).quantize(Decimal("0.01")))


def _stock_inventario():
    """Agrega los movimientos una sola vez, evitando consultas por ingrediente."""
    ingredientes = list(Ingrediente.objects.filter(activo=True).only(
        "id", "nombre", "unidad_medida", "stock_minimo", "costo_unitario"
    ))
    acumulados = defaultdict(lambda: Decimal("0.000"))
    for fila in (MovimientoInventario.objects.filter(ingrediente__activo=True)
                 .values("ingrediente_id", "tipo").annotate(total=Sum("cantidad"))):
        signo = 1 if fila["tipo"] == MovimientoInventario.Tipo.ENTRADA else -1
        acumulados[fila["ingrediente_id"]] += signo * fila["total"]

    alertas = []
    valor_estimado = CERO
    for ing in ingredientes:
        stock = acumulados[ing.pk]
        valor_estimado += stock * ing.costo_unitario
        if stock <= ing.stock_minimo:
            alertas.append({
                "id": ing.pk, "nombre": ing.nombre,
                "existencia": str(stock.quantize(Decimal("0.001"))),
                "minimo": str(ing.stock_minimo), "unidad": ing.unidad_medida,
            })
    alertas.sort(key=lambda x: (x["nombre"].casefold(), x["id"]))
    return {
        "ingredientes_activos": len(ingredientes),
        "ingredientes_bajo_minimo": len(alertas),
        "valor_estimado": _dinero(valor_estimado),
        "alertas": alertas[:12],
    }


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        _autorizado(request.user)
        desde, hasta, inicio, fin = _rango(request)
        pedidos = Pedido.objects.filter(fecha_pedido__gte=inicio, fecha_pedido__lt=fin)
        vigentes = pedidos.exclude(estado=Pedido.Estado.CANCELADO)
        cobros = Pago.objects.filter(fecha_pago__gte=inicio, fecha_pago__lt=fin)

        importe = vigentes.aggregate(x=Sum("total"))["x"] or CERO
        ingresado = cobros.aggregate(x=Sum("monto"))["x"] or CERO
        pagado_en_pedidos = (Pago.objects.filter(pedido__in=vigentes)
                             .aggregate(x=Sum("monto"))["x"] or CERO)
        saldo = max(CERO, importe - pagado_en_pedidos)
        cantidad_vigentes = vigentes.count()
        estados = {codigo: 0 for codigo, _ in Pedido.Estado.choices}
        for fila in pedidos.values("estado").annotate(cantidad=Count("id")):
            estados[fila["estado"]] = fila["cantidad"]

        # Serie por fecha LOCAL. Se evita depender de tablas TZ de MySQL/MariaDB.
        fechas = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
        serie = {f: {"pedidos": 0, "cobros": CERO} for f in fechas}
        for creado in (pedidos.values_list("fecha_pedido", flat=True)
                       .iterator(chunk_size=1000)):
            fecha = timezone.localtime(creado).date()
            if fecha in serie:
                serie[fecha]["pedidos"] += 1
        for creado, monto in (cobros.values_list("fecha_pago", "monto")
                               .iterator(chunk_size=1000)):
            fecha = timezone.localtime(creado).date()
            if fecha in serie:
                serie[fecha]["cobros"] += monto

        top = (DetallePedido.objects.filter(pedido__in=vigentes)
               .values("nombre_producto").annotate(
                   unidades=Sum("cantidad"), importe=Sum("subtotal"))
               .order_by("-unidades", "nombre_producto")[:8])

        respuesta = {
            "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
            "indicadores": {
                "pedidos_registrados": pedidos.count(),
                "pedidos_no_cancelados": cantidad_vigentes,
                "pedidos_cancelados": estados[Pedido.Estado.CANCELADO],
                "importe_pedidos": _dinero(importe),
                "cobros_registrados": _dinero(ingresado),
                "saldo_pedidos": _dinero(saldo),
                "ticket_promedio": _dinero(importe / cantidad_vigentes if cantidad_vigentes else CERO),
                "clientes_nuevos": Cliente.objects.filter(
                    fecha_registro__gte=inicio, fecha_registro__lt=fin).count(),
            },
            "estados": [
                {"codigo": codigo, "nombre": nombre, "cantidad": estados[codigo]}
                for codigo, nombre in Pedido.Estado.choices
            ],
            "serie": [
                {"fecha": f.isoformat(), "pedidos": serie[f]["pedidos"],
                 "cobros": _dinero(serie[f]["cobros"])} for f in fechas
            ],
            "productos": [
                {"nombre": fila["nombre_producto"], "unidades": fila["unidades"],
                 "importe": _dinero(fila["importe"])} for fila in top
            ],
            "inventario": _stock_inventario(),
            "nota": (
                "Importe de pedidos: pedidos no cancelados creados en el período. "
                "Cobros: pagos recibidos en el período, incluso si corresponden a pedidos anteriores. "
                "Saldo: importe pendiente de los pedidos no cancelados creados en el período, "
                "considerando todos sus pagos registrados. No representa utilidad."
            ),
        }
        respuesta_http = Response(respuesta)
        respuesta_http["Cache-Control"] = "no-store"
        return respuesta_http


class ExportarDatosView(APIView):
    """Entrega filas JSON para generar CSV con sesión JWT existente en el navegador."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        _autorizado(request.user)
        tipo = request.query_params.get("tipo", "").strip()
        if tipo not in {"pedidos", "pagos"}:
            raise ValidationError({"tipo": "Elige 'pedidos' o 'pagos'."})
        desde, hasta, inicio, fin = _rango(request)

        if tipo == "pedidos":
            qs = (Pedido.objects.filter(fecha_pedido__gte=inicio, fecha_pedido__lt=fin)
                  .select_related("cliente").prefetch_related("pagos")
                  .order_by("fecha_pedido", "id"))
            cantidad = qs.count()
            if cantidad > MAX_FILAS_EXPORTACION:
                raise ValidationError({"detail": "Hay más de 5000 pedidos. Reduce el rango de fechas."})
            columnas = ["Folio", "Fecha pedido", "Fecha entrega", "Cliente", "Estado",
                        "Importe MXN", "Cobrado MXN", "Saldo MXN"]
            filas = []
            for p in qs:
                abonado = sum((pago.monto for pago in p.pagos.all()), CERO)
                filas.append([
                    p.folio or f"#{p.pk}",
                    timezone.localtime(p.fecha_pedido).strftime("%Y-%m-%d %H:%M"),
                    timezone.localtime(p.fecha_entrega).strftime("%Y-%m-%d %H:%M"),
                    str(p.cliente), p.get_estado_display(),
                    _dinero(p.total), _dinero(abonado), _dinero(p.total - abonado),
                ])
        else:
            qs = (Pago.objects.filter(fecha_pago__gte=inicio, fecha_pago__lt=fin)
                  .select_related("pedido", "pedido__cliente")
                  .order_by("fecha_pago", "id"))
            cantidad = qs.count()
            if cantidad > MAX_FILAS_EXPORTACION:
                raise ValidationError({"detail": "Hay más de 5000 pagos. Reduce el rango de fechas."})
            columnas = ["Fecha pago", "Pedido", "Cliente", "Método", "Monto MXN", "Referencia"]
            filas = [
                [timezone.localtime(p.fecha_pago).strftime("%Y-%m-%d %H:%M"),
                 p.pedido.folio or f"#{p.pedido_id}", str(p.pedido.cliente),
                 p.get_metodo_display(), _dinero(p.monto), p.referencia]
                for p in qs
            ]

        response = Response({
            "tipo": tipo,
            "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
            "columnas": columnas, "filas": filas, "total": cantidad,
        })
        response["Cache-Control"] = "no-store"
        return response
