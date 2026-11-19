from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from clientes.models import Cliente
from productos.models import CategoriaProducto, Producto
from usuarios.models import Rol, Usuario
from .models import DetallePedido, Pago, Pedido


class PedidosAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        roles = {
            codigo: Rol.objects.create(codigo=codigo, nombre=codigo)
            for codigo in ("ADMIN", "VENTAS", "REPOSTERO", "ALMACEN", "CLIENTE")
        }
        cls.admin = Usuario.objects.create_user(
            username="adminped", email="adminped@example.com", password="ClaveSegura123!", rol=roles["ADMIN"]
        )
        cls.ventas = Usuario.objects.create_user(
            username="ventasped", email="ventasped@example.com", password="ClaveSegura123!", rol=roles["VENTAS"]
        )
        cls.repostero = Usuario.objects.create_user(
            username="reposteroped", email="reposteroped@example.com", password="ClaveSegura123!", rol=roles["REPOSTERO"]
        )
        cls.almacen = Usuario.objects.create_user(
            username="almacenped", email="almacenped@example.com", password="ClaveSegura123!", rol=roles["ALMACEN"]
        )
        cls.cliente_usuario = Usuario.objects.create_user(
            username="cliente01ped", email="cliente01ped@example.com", password="ClaveSegura123!", rol=roles["CLIENTE"]
        )
        cls.otro_usuario = Usuario.objects.create_user(
            username="cliente02ped", email="cliente02ped@example.com", password="ClaveSegura123!", rol=roles["CLIENTE"]
        )
        cls.cliente = Cliente.objects.create(usuario=cls.cliente_usuario, nombre="Mariana", apellidos="López")
        cls.otro_cliente = Cliente.objects.create(usuario=cls.otro_usuario, nombre="Jorge", apellidos="Pérez")
        cls.categoria = CategoriaProducto.objects.create(nombre="Pasteles")
        cls.producto = Producto.objects.create(
            categoria=cls.categoria, nombre="Pastel de chocolate", precio_base=Decimal("450.00")
        )
        cls.otro_producto = Producto.objects.create(
            categoria=cls.categoria, nombre="Caja cupcakes", precio_base=Decimal("160.00")
        )
        cls.inactivo = Producto.objects.create(
            categoria=cls.categoria, nombre="Descatalogado", precio_base=Decimal("100.00"), activo=False
        )

    def autenticar(self, usuario):
        self.client.force_authenticate(user=usuario)

    def datos(self, **overrides):
        data = {
            "fecha_entrega": (timezone.now() + timedelta(days=2)).isoformat(),
            "detalles": [
                {"producto_id": self.producto.pk, "cantidad": 2, "personalizacion": "Sin nueces"},
                {"producto_id": self.otro_producto.pk, "cantidad": 1},
            ],
            "observaciones": "Llamar antes de entregar",
        }
        data.update(overrides)
        return data

    def crear(self, cliente=False):
        self.autenticar(self.cliente_usuario if cliente else self.admin)
        data = self.datos() if cliente else self.datos(cliente_id=self.cliente.pk)
        result = self.client.post(reverse("pedidos"), data, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        return result.data

    def test_anonimo_no_ve_pedidos(self):
        self.assertEqual(self.client.get(reverse("pedidos")).status_code, 401)

    def test_cliente_crea_propio_pedido_y_precio_se_calcula_en_servidor(self):
        self.autenticar(self.cliente_usuario)
        data = self.datos(total="0.01", estado="ENTREGADO", registrado_por=self.admin.pk)
        result = self.client.post(reverse("pedidos"), data, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(Decimal(result.data["total"]), Decimal("1060.00"))
        self.assertEqual(result.data["estado"], "PENDIENTE")
        self.assertEqual(result.data["cliente"], self.cliente.pk)
        self.assertTrue(result.data["folio"].startswith("PED-"))
        self.assertEqual(DetallePedido.objects.filter(pedido_id=result.data["id"]).count(), 2)

    def test_cliente_no_elije_cliente_ajeno(self):
        self.autenticar(self.cliente_usuario)
        result = self.client.post(reverse("pedidos"), self.datos(cliente_id=self.otro_cliente.pk), format="json")
        self.assertEqual(result.status_code, 400)
        self.assertFalse(Pedido.objects.exists())

    def test_clientes_solo_ven_sus_pedidos(self):
        data = self.crear()
        self.autenticar(self.otro_usuario)
        result = self.client.get(reverse("pedidos"))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, [])
        self.assertEqual(self.client.get(reverse("pedido-detalle", args=[data["id"]])).status_code, 404)

    def test_no_admite_productos_inactivos(self):
        self.autenticar(self.cliente_usuario)
        result = self.client.post(reverse("pedidos"), self.datos(detalles=[{
            "producto_id": self.inactivo.pk, "cantidad": 1,
        }]), format="json")
        self.assertEqual(result.status_code, 400)
        self.assertFalse(Pedido.objects.exists())

    def test_no_admite_fecha_pasada(self):
        self.autenticar(self.cliente_usuario)
        result = self.client.post(reverse("pedidos"), self.datos(
            fecha_entrega=(timezone.now() - timedelta(days=1)).isoformat()
        ), format="json")
        self.assertEqual(result.status_code, 400)

    def test_no_admite_cantidad_cero(self):
        self.autenticar(self.cliente_usuario)
        result = self.client.post(reverse("pedidos"), self.datos(detalles=[{
            "producto_id": self.producto.pk, "cantidad": 0,
        }]), format="json")
        self.assertEqual(result.status_code, 400)

    def test_no_admite_ficha_cliente_inactiva(self):
        self.cliente.activo = False
        self.cliente.save(update_fields=["activo"])
        self.autenticar(self.cliente_usuario)
        result = self.client.post(reverse("pedidos"), self.datos(), format="json")
        self.assertEqual(result.status_code, 400)

    def test_ventas_crea_pedido_para_cliente(self):
        self.autenticar(self.ventas)
        result = self.client.post(reverse("pedidos"), self.datos(cliente_id=self.otro_cliente.pk), format="json")
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data["cliente"], self.otro_cliente.pk)

    def test_repostero_no_registra_pedidos_ni_pagos(self):
        pedido = self.crear()
        self.autenticar(self.repostero)
        self.assertEqual(self.client.post(reverse("pedidos"), self.datos(), format="json").status_code, 403)
        self.assertEqual(self.client.post(reverse("pedido-pagos", args=[pedido["id"]]), {
            "monto": "10.00", "metodo": "EFECTIVO",
        }, format="json").status_code, 403)

    def test_almacen_no_accede_al_modulo(self):
        self.autenticar(self.almacen)
        self.assertEqual(self.client.get(reverse("pedidos")).status_code, 403)

    def test_ventas_registra_pago_y_saldo_disminuye(self):
        pedido = self.crear()
        self.autenticar(self.ventas)
        response = self.client.post(reverse("pedido-pagos", args=[pedido["id"]]), {
            "monto": "300.00", "metodo": "TRANSFERENCIA", "referencia": "TR-001",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        result = self.client.get(reverse("pedido-detalle", args=[pedido["id"]]))
        self.assertEqual(Decimal(result.data["pagado"]), Decimal("300.00"))
        self.assertEqual(Decimal(result.data["saldo"]), Decimal("760.00"))
        self.assertEqual(Pago.objects.count(), 1)

    def test_no_admite_pago_mayor_al_saldo(self):
        pedido = self.crear()
        self.autenticar(self.admin)
        resp = self.client.post(reverse("pedido-pagos", args=[pedido["id"]]), {
            "monto": "1060.01", "metodo": "EFECTIVO",
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Pago.objects.count(), 0)

    def test_cliente_no_puede_registrar_pago(self):
        pedido = self.crear(cliente=True)
        resp = self.client.post(reverse("pedido-pagos", args=[pedido["id"]]), {
            "monto": "100.00", "metodo": "EFECTIVO",
        }, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_flujo_estados_separado_por_roles(self):
        pedido = self.crear()
        pk = pedido["id"]
        self.autenticar(self.ventas)
        self.assertEqual(self.client.patch(reverse("pedido-estado", args=[pk]), {
            "estado": "CONFIRMADO",
        }, format="json").status_code, 200)
        self.assertEqual(self.client.patch(reverse("pedido-estado", args=[pk]), {
            "estado": "LISTO",
        }, format="json").status_code, 400)
        self.autenticar(self.repostero)
        self.assertEqual(self.client.patch(reverse("pedido-estado", args=[pk]), {
            "estado": "EN_PREPARACION",
        }, format="json").status_code, 200)
        self.assertEqual(self.client.patch(reverse("pedido-estado", args=[pk]), {
            "estado": "LISTO",
        }, format="json").status_code, 200)
        self.autenticar(self.ventas)
        self.assertEqual(self.client.patch(reverse("pedido-estado", args=[pk]), {
            "estado": "ENTREGADO",
        }, format="json").status_code, 200)

    def test_cancelacion_bloqueada_si_hay_pago(self):
        pedido = self.crear()
        pk = pedido["id"]
        self.autenticar(self.ventas)
        self.client.post(reverse("pedido-pagos", args=[pk]), {
            "monto": "50.00", "metodo": "EFECTIVO",
        }, format="json")
        resp = self.client.patch(reverse("pedido-estado", args=[pk]), {
            "estado": "CANCELADO",
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Pedido.objects.get(pk=pk).estado, Pedido.Estado.PENDIENTE)

    def test_repostero_solo_ve_confirmados_y_en_preparacion(self):
        pedido = self.crear()
        self.autenticar(self.repostero)
        self.assertEqual(self.client.get(reverse("pedidos")).data, [])
        self.autenticar(self.admin)
        self.client.patch(reverse("pedido-estado", args=[pedido["id"]]), {
            "estado": "CONFIRMADO",
        }, format="json")
        self.autenticar(self.repostero)
        resp = self.client.get(reverse("pedidos"))
        self.assertEqual(len(resp.data), 1)

    def test_repostero_no_ve_informacion_de_pagos(self):
        pedido = self.crear()
        self.autenticar(self.admin)
        self.client.patch(reverse("pedido-estado", args=[pedido["id"]]), {
            "estado": "CONFIRMADO",
        }, format="json")
        self.client.post(reverse("pedido-pagos", args=[pedido["id"]]), {
            "monto": "60.00", "metodo": "TRANSFERENCIA", "referencia": "REFERENCIA-PRIVADA",
        }, format="json")
        self.autenticar(self.repostero)
        result = self.client.get(reverse("pedido-detalle", args=[pedido["id"]]))
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("pagos", result.data)
        self.assertNotIn("saldo", result.data)
        self.assertNotIn("total", result.data)
        self.assertEqual(self.client.get(reverse("pedido-pagos", args=[pedido["id"]])).status_code, 403)

    def test_el_precio_historico_no_cambia_al_editar_catalogo(self):
        pedido = self.crear()
        self.producto.precio_base = Decimal("999.00")
        self.producto.save(update_fields=["precio_base"])
        self.autenticar(self.admin)
        result = self.client.get(reverse("pedido-detalle", args=[pedido["id"]]))
        self.assertEqual(Decimal(result.data["total"]), Decimal("1060.00"))
        self.assertEqual(Decimal(result.data["detalles"][0]["precio_unitario"]), Decimal("450.00"))
