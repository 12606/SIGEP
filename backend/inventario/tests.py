from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from usuarios.models import Rol, Usuario
from .models import Ingrediente, MovimientoInventario


class InventarioAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        roles = {c: Rol.objects.create(codigo=c, nombre=c) for c in (
            "ADMIN", "ALMACEN", "REPOSTERO", "VENTAS", "CLIENTE"
        )}
        cls.usuarios = {
            c: Usuario.objects.create_user(
                username="inv_" + c.lower(), email=f"inv_{c.lower()}@example.com",
                password="ClaveSegura123!", rol=roles[c],
            ) for c in roles
        }
        cls.harina = Ingrediente.objects.create(
            nombre="Harina", unidad_medida="KG", stock_minimo=Decimal("2.000"),
            costo_unitario=Decimal("25.50"),
        )

    def login(self, codigo):
        self.client.force_authenticate(user=self.usuarios[codigo])

    def movimiento(self, tipo, cantidad, ingrediente=None, motivo="Prueba de inventario"):
        return self.client.post(reverse("inventario-movimientos"), {
            "ingrediente_id": ingrediente or self.harina.pk,
            "tipo": tipo, "cantidad": cantidad, "motivo": motivo,
        }, format="json")

    def test_sin_sesion_no_puede_ver_ingredientes(self):
        self.assertEqual(self.client.get(reverse("inventario-ingredientes")).status_code, 401)

    def test_admin_puede_registrar_ingrediente_sin_stock(self):
        self.login("ADMIN")
        resp = self.client.post(reverse("inventario-ingredientes"), {
            "nombre": "Azúcar", "unidad_medida": "KG", "stock_minimo": "3.000",
            "costo_unitario": "22.50", "stock_actual": "999", "activo": False,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Decimal(resp.data["stock_actual"]), Decimal("0"))
        self.assertTrue(resp.data["activo"])

    def test_almacen_puede_crear_y_editar_ingrediente(self):
        self.login("ALMACEN")
        respuesta = self.client.patch(reverse("inventario-ingrediente-detalle", args=[self.harina.pk]), {
            "stock_minimo": "5.000", "costo_unitario": "26.00"
        }, format="json")
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(self.harina.stock_minimo, Decimal("2"))  # instancia sin refresh
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.stock_minimo, Decimal("5"))

    def test_entrada_salida_y_merma_calculan_stock(self):
        self.login("ALMACEN")
        self.assertEqual(self.movimiento("ENTRADA", "10.000").status_code, 201)
        self.assertEqual(self.movimiento("SALIDA", "3.500").status_code, 201)
        self.assertEqual(self.movimiento("MERMA", "0.250").status_code, 201)
        detalle = self.client.get(reverse("inventario-ingrediente-detalle", args=[self.harina.pk]))
        self.assertEqual(Decimal(detalle.data["stock_actual"]), Decimal("6.250"))
        self.assertEqual(MovimientoInventario.objects.count(), 3)

    def test_rechaza_salida_superior_a_existencia_y_no_registra_movimiento(self):
        self.login("ADMIN")
        self.movimiento("ENTRADA", "2.000")
        resp = self.movimiento("SALIDA", "2.001")
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertEqual(MovimientoInventario.objects.count(), 1)
        self.assertEqual(self.harina.stock_actual, Decimal("2.000"))

    def test_rechaza_cantidad_cero_y_negativa(self):
        self.login("ALMACEN")
        self.assertEqual(self.movimiento("ENTRADA", "0.000").status_code, 400)
        self.assertEqual(self.movimiento("ENTRADA", "-1.000").status_code, 400)
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_rechaza_tipo_desconocido(self):
        self.login("ALMACEN")
        self.assertEqual(self.movimiento("REGALO", "5.000").status_code, 400)

    def test_movimientos_no_se_pueden_editar_o_borrar(self):
        self.login("ADMIN")
        creado = self.movimiento("ENTRADA", "3.000")
        self.assertEqual(creado.status_code, 201)
        url = reverse("inventario-movimientos")
        self.assertEqual(self.client.patch(url, {"cantidad": "999"}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_inactivo_no_recibe_movimientos(self):
        self.login("ADMIN")
        url = reverse("inventario-ingrediente-estado", args=[self.harina.pk])
        self.assertEqual(self.client.patch(url, {"activo": False}, format="json").status_code, 200)
        self.assertEqual(self.movimiento("ENTRADA", "1.000").status_code, 400)

    def test_solo_admin_desactiva_ingrediente(self):
        url = reverse("inventario-ingrediente-estado", args=[self.harina.pk])
        self.login("ALMACEN")
        self.assertEqual(self.client.patch(url, {"activo": False}, format="json").status_code, 403)
        self.login("ADMIN")
        self.assertEqual(self.client.patch(url, {"activo": False}, format="json").status_code, 200)

    def test_repostero_ve_stock_sin_costos(self):
        self.login("REPOSTERO")
        resp = self.client.get(reverse("inventario-ingredientes"))
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertNotIn("costo_unitario", resp.data[0])
        self.assertIn("stock_actual", resp.data[0])
        self.assertEqual(self.movimiento("ENTRADA", "2.000").status_code, 403)

    def test_repostero_no_ve_ingredientes_inactivos(self):
        self.login("ADMIN")
        self.client.patch(reverse("inventario-ingrediente-estado", args=[self.harina.pk]), {
            "activo": False,
        }, format="json")
        self.login("REPOSTERO")
        resp = self.client.get(reverse("inventario-ingredientes"))
        self.assertEqual(resp.data, [])
        self.assertEqual(self.client.get(reverse("inventario-ingrediente-detalle", args=[self.harina.pk])).status_code, 404)

    def test_ventas_y_cliente_no_acceden_a_inventario(self):
        for codigo in ("VENTAS", "CLIENTE"):
            with self.subTest(codigo=codigo):
                self.login(codigo)
                self.assertEqual(self.client.get(reverse("inventario-ingredientes")).status_code, 403)
                self.assertEqual(self.client.get(reverse("inventario-alertas")).status_code, 403)
                self.assertEqual(self.client.get(reverse("inventario-movimientos")).status_code, 403)

    def test_alertas_se_actualizan_con_movimientos(self):
        self.login("ADMIN")
        url = reverse("inventario-alertas")
        self.assertEqual(len(self.client.get(url).data), 1)  # stock cero
        self.movimiento("ENTRADA", "10.000")
        self.assertEqual(len(self.client.get(url).data), 0)
        self.movimiento("SALIDA", "9.000")
        self.assertEqual(len(self.client.get(url).data), 1)

    def test_busqueda_y_filtro_activos(self):
        Ingrediente.objects.create(nombre="Azúcar", unidad_medida="KG", activo=False)
        self.login("ADMIN")
        resp = self.client.get(reverse("inventario-ingredientes"), {"buscar": "Har", "activo": "true"})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual([x["nombre"] for x in resp.data], ["Harina"])
        resp = self.client.get(reverse("inventario-ingredientes"), {"activo": "false"})
        self.assertEqual(len(resp.data), 1)

    def test_no_cambia_unidad_si_ya_hay_movimientos(self):
        self.login("ADMIN")
        self.movimiento("ENTRADA", "1.000")
        resp = self.client.patch(reverse("inventario-ingrediente-detalle", args=[self.harina.pk]), {
            "unidad_medida": "G",
        }, format="json")
        self.assertEqual(resp.status_code, 400, resp.data)

    def test_piezas_no_admiten_fracciones(self):
        self.login("ALMACEN")
        huevo = Ingrediente.objects.create(nombre="Huevos", unidad_medida="PIEZA")
        self.assertEqual(self.movimiento("ENTRADA", "2.500", huevo.pk).status_code, 400)
        self.assertEqual(self.movimiento("ENTRADA", "3.000", huevo.pk).status_code, 201)

    def test_lista_movimientos_solo_admin_y_almacen(self):
        self.login("ADMIN")
        self.movimiento("ENTRADA", "3.000")
        response = self.client.get(reverse("inventario-movimientos"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["usuario"], self.usuarios["ADMIN"].username)
        self.login("REPOSTERO")
        self.assertEqual(self.client.get(reverse("inventario-movimientos")).status_code, 403)
