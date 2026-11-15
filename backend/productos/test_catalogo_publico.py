"""Pruebas de API pública sin modificar usuarios ni migraciones."""
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APITestCase
from .models import CategoriaProducto, Producto


class CatalogoPublicoTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.categoria = CategoriaProducto.objects.create(nombre="Pasteles", activo=True)
        cls.oculta = CategoriaProducto.objects.create(nombre="Oculta", activo=False)
        cls.visible = Producto.objects.create(
            categoria=cls.categoria, nombre="Pastel de fresa", descripcion="Con fresas",
            precio_base=Decimal("390.00"), activo=True,
        )
        cls.inactivo = Producto.objects.create(
            categoria=cls.categoria, nombre="Producto desactivado",
            precio_base=Decimal("200.00"), activo=False,
        )
        cls.en_categoria_oculta = Producto.objects.create(
            categoria=cls.oculta, nombre="Producto secreto",
            precio_base=Decimal("250.00"), activo=True,
        )

    def test_visitante_ve_solo_categorias_activas(self):
        response = self.client.get(reverse("catalogo-categorias"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nombre"], "Pasteles")

    def test_visitante_ve_solo_productos_publicados(self):
        response = self.client.get(reverse("catalogo-productos"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.visible.pk)
        self.assertEqual(response.data[0]["precio_base"], "390.00")
        self.assertNotIn("activo", response.data[0])

    def test_busqueda_y_filtro_categoria(self):
        response = self.client.get(reverse("catalogo-productos"), {
            "buscar": "fresa", "categoria": str(self.categoria.pk),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nombre"], "Pastel de fresa")

    def test_filtro_invalido(self):
        response = self.client.get(reverse("catalogo-productos"), {"categoria": "abc"})
        self.assertEqual(response.status_code, 400)

    def test_no_muestra_detalle_inactivo(self):
        response = self.client.get(reverse("catalogo-producto-detalle", args=(self.inactivo.pk,)))
        self.assertEqual(response.status_code, 404)

    def test_no_muestra_producto_de_categoria_inactiva(self):
        response = self.client.get(reverse("catalogo-producto-detalle", args=(self.en_categoria_oculta.pk,)))
        self.assertEqual(response.status_code, 404)

    def test_detalle_del_producto_publicado(self):
        response = self.client.get(reverse("catalogo-producto-detalle", args=(self.visible.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["categoria_nombre"], "Pasteles")

    def test_visitante_no_puede_crear_producto(self):
        response = self.client.post(reverse("catalogo-productos"), {
            "nombre": "Falso", "precio_base": "99.00",
        }, format="json")
        self.assertEqual(response.status_code, 405)
        self.assertFalse(Producto.objects.filter(nombre="Falso").exists())

    def test_visitante_no_puede_modificar_producto(self):
        response = self.client.patch(reverse("catalogo-producto-detalle", args=(self.visible.pk,)), {
            "precio_base": "1.00",
        }, format="json")
        self.assertEqual(response.status_code, 405)

    def test_endpoint_administrativo_sigue_protegido(self):
        response = self.client.get(reverse("productos"))
        self.assertEqual(response.status_code, 401)
