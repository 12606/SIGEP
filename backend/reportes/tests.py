"""Fase 6: agregados financieros, filtros y autorización del dashboard."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from clientes.models import Cliente
from inventario.models import Ingrediente, MovimientoInventario
from pedidos.models import DetallePedido, Pago, Pedido
from productos.models import CategoriaProducto, Producto
from usuarios.models import Rol

Usuario = get_user_model()


class ReportesAPITests(APITestCase):
    def setUp(self):
        self.admin_rol = Rol.objects.create(codigo="ADMIN", nombre="Administrador")
        self.ventas_rol = Rol.objects.create(codigo="VENTAS", nombre="Ventas")
        self.cliente_rol = Rol.objects.create(codigo="CLIENTE", nombre="Cliente")
        self.almacen_rol = Rol.objects.create(codigo="ALMACEN", nombre="Almacén")
        self.repostero_rol = Rol.objects.create(codigo="REPOSTERO", nombre="Repostero")
        self.admin = Usuario.objects.create_user(username="admin6", email="admin6@test.local", password="ClaveSegura2026!", rol=self.admin_rol)
        self.ventas = Usuario.objects.create_user(username="ventas6", email="ventas6@test.local", password="ClaveSegura2026!", rol=self.ventas_rol)
        self.cliente_user = Usuario.objects.create_user(username="cliente6", email="cliente6@test.local", password="ClaveSegura2026!", rol=self.cliente_rol)
        self.almacen = Usuario.objects.create_user(username="almacen6", email="almacen6@test.local", password="ClaveSegura2026!", rol=self.almacen_rol)
        self.repostero = Usuario.objects.create_user(username="repostero6", email="repostero6@test.local", password="ClaveSegura2026!", rol=self.repostero_rol)
        self.cliente = Cliente.objects.create(nombre="Eva", apellidos="Lopez", usuario=self.cliente_user)
        categoria = CategoriaProducto.objects.create(nombre="Tortas")
        self.producto = Producto.objects.create(categoria=categoria, nombre="Torta vainilla", precio_base=Decimal("200.00"))
        self.pedido = Pedido.objects.create(
            folio="SIGEP-T001", cliente=self.cliente, registrado_por=self.ventas,
            fecha_entrega=timezone.now() + timedelta(days=2),
            estado=Pedido.Estado.CONFIRMADO, subtotal=Decimal("200.00"), total=Decimal("200.00"),
        )
        DetallePedido.objects.create(
            pedido=self.pedido, producto=self.producto, nombre_producto="Torta vainilla",
            unidad_venta="PIEZA", cantidad=2, precio_unitario=Decimal("100.00"), subtotal=Decimal("200.00"),
        )
        self.pago = Pago.objects.create(
            pedido=self.pedido, registrado_por=self.ventas,
            metodo=Pago.Metodo.EFECTIVO, monto=Decimal("80.00"), referencia="MOSTRADOR",
        )
        self.ingrediente = Ingrediente.objects.create(
            nombre="Harina", unidad_medida="KG", stock_minimo=Decimal("3.000"),
            costo_unitario=Decimal("20.00"),
        )
        MovimientoInventario.objects.create(
            ingrediente=self.ingrediente, registrado_por=self.admin,
            tipo=MovimientoInventario.Tipo.ENTRADA, cantidad=Decimal("2.000"), motivo="Compra",
        )

    def login_admin(self):
        self.client.force_authenticate(user=self.admin)

    def test_admin_consulta_cifras_correctas(self):
        self.login_admin()
        res = self.client.get(reverse("reportes-dashboard"))
        self.assertEqual(res.status_code, 200, res.data)
        kpis = res.data["indicadores"]
        self.assertEqual(kpis["pedidos_registrados"], 1)
        self.assertEqual(kpis["importe_pedidos"], "200.00")
        self.assertEqual(kpis["cobros_registrados"], "80.00")
        self.assertEqual(kpis["saldo_pedidos"], "120.00")
        self.assertEqual(kpis["ticket_promedio"], "200.00")
        self.assertEqual(res.data["inventario"]["ingredientes_bajo_minimo"], 1)
        self.assertEqual(res.data["inventario"]["valor_estimado"], "40.00")
        self.assertEqual(res.data["productos"][0]["unidades"], 2)
        self.assertEqual(res["Cache-Control"], "no-store")

    def test_serie_incluye_pedidos_y_cobros(self):
        self.login_admin()
        res = self.client.get(reverse("reportes-dashboard"))
        hoy = timezone.localdate().isoformat()
        fila = next(f for f in res.data["serie"] if f["fecha"] == hoy)
        self.assertEqual(fila["pedidos"], 1)
        self.assertEqual(fila["cobros"], "80.00")

    def test_cancelados_no_suman_al_importe_ni_al_top(self):
        self.pedido.estado = Pedido.Estado.CANCELADO
        self.pedido.save(update_fields=["estado"])
        self.login_admin()
        res = self.client.get(reverse("reportes-dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["indicadores"]["pedidos_cancelados"], 1)
        self.assertEqual(res.data["indicadores"]["importe_pedidos"], "0.00")
        self.assertEqual(res.data["productos"], [])
        # El cobro ya ocurrió, incluso si el pedido luego fue cancelado.
        self.assertEqual(res.data["indicadores"]["cobros_registrados"], "80.00")

    def test_ventas_no_puede_consultar_cifras_ni_exportar(self):
        self.client.force_authenticate(user=self.ventas)
        self.assertEqual(self.client.get(reverse("reportes-dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("reportes-exportar"), {"tipo": "pagos"}).status_code, 403)

    def test_otros_roles_sin_permiso(self):
        for usuario in (self.cliente_user, self.almacen, self.repostero):
            with self.subTest(rol=usuario.rol.codigo):
                self.client.force_authenticate(user=usuario)
                self.assertEqual(self.client.get(reverse("reportes-dashboard")).status_code, 403)

    def test_anonimo_requiere_autenticacion(self):
        self.assertIn(self.client.get(reverse("reportes-dashboard")).status_code, (401, 403))

    def test_rango_invalido_rechazado(self):
        self.login_admin()
        fecha = timezone.localdate()
        datos = {"desde": fecha.isoformat(), "hasta": (fecha - timedelta(days=1)).isoformat()}
        self.assertEqual(self.client.get(reverse("reportes-dashboard"), datos).status_code, 400)

    def test_fecha_invalida_rechazada(self):
        self.login_admin()
        self.assertEqual(self.client.get(reverse("reportes-dashboard"), {"desde": "2026-99-99"}).status_code, 400)

    def test_rango_superior_al_maximo_rechazado(self):
        self.login_admin()
        self.assertEqual(self.client.get(reverse("reportes-dashboard"), {
            "desde": "2025-01-01", "hasta": "2026-07-01",
        }).status_code, 400)

    def test_exportacion_pedidos(self):
        self.login_admin()
        res = self.client.get(reverse("reportes-exportar"), {"tipo": "pedidos"})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["total"], 1)
        self.assertEqual(res.data["filas"][0][0], "SIGEP-T001")
        self.assertEqual(res.data["filas"][0][-1], "120.00")

    def test_exportacion_pagos(self):
        self.login_admin()
        res = self.client.get(reverse("reportes-exportar"), {"tipo": "pagos"})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["total"], 1)
        self.assertEqual(res.data["filas"][0][-1], "MOSTRADOR")

    def test_exportacion_tipo_invalido(self):
        self.login_admin()
        res = self.client.get(reverse("reportes-exportar"), {"tipo": "usuarios"})
        self.assertEqual(res.status_code, 400)

    def test_periodo_futuro_no_tiene_cobros(self):
        self.login_admin()
        fecha = timezone.localdate() + timedelta(days=15)
        res = self.client.get(reverse("reportes-dashboard"), {
            "desde": fecha.isoformat(), "hasta": fecha.isoformat(),
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["indicadores"]["pedidos_registrados"], 0)
        self.assertEqual(res.data["indicadores"]["cobros_registrados"], "0.00")
        self.assertEqual(len(res.data["serie"]), 1)

    def test_permisos_denegados_a_admin_inactivo(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        self.login_admin()
        self.assertEqual(self.client.get(reverse("reportes-dashboard")).status_code, 403)
