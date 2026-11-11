from decimal import Decimal
from io import BytesIO
import tempfile
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import Rol, Usuario
from .models import CategoriaProducto, Producto


class CatalogoAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        admin = Rol.objects.create(codigo="ADMIN", nombre="Administrador")
        ventas = Rol.objects.create(codigo="VENTAS", nombre="Ventas")
        cliente = Rol.objects.create(codigo="CLIENTE", nombre="Cliente")
        cls.administrador = Usuario.objects.create_user(
            username="adminp", email="adminp@example.com", password="ClaveSegura123!", rol=admin
        )
        cls.vendedor = Usuario.objects.create_user(
            username="vendp", email="vendp@example.com", password="ClaveSegura123!", rol=ventas
        )
        cls.cliente = Usuario.objects.create_user(
            username="clientep", email="clientep@example.com", password="ClaveSegura123!", rol=cliente
        )
        cls.categoria = CategoriaProducto.objects.create(nombre="Pasteles")
        cls.inactiva = CategoriaProducto.objects.create(nombre="Oculta", activo=False)
        cls.producto = Producto.objects.create(
            categoria=cls.categoria, nombre="Pastel de chocolate", precio_base=Decimal("350.00")
        )
        cls.producto_inactivo = Producto.objects.create(
            categoria=cls.categoria, nombre="Pastel antiguo", precio_base=Decimal("200.00"), activo=False
        )

    def auth(self, usuario):
        self.client.force_authenticate(user=usuario)

    def test_anonimo_no_puede_listar(self):
        self.assertEqual(self.client.get(reverse("productos")).status_code, 401)
        self.assertEqual(self.client.get(reverse("categorias-producto")).status_code, 401)

    def test_administrador_ve_todos_y_crea_categoria(self):
        self.auth(self.administrador)
        respuesta = self.client.get(reverse("categorias-producto"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data), 2)
        crear = self.client.post(reverse("categorias-producto"), {
            "nombre": "Cupcakes", "descripcion": "Individuales"
        }, format="json")
        self.assertEqual(crear.status_code, 201, crear.data)

    def test_vendedor_ve_solo_categorias_activas(self):
        self.auth(self.vendedor)
        respuesta = self.client.get(reverse("categorias-producto"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data), 1)

    def test_vendedor_no_crea_categorias(self):
        self.auth(self.vendedor)
        respuesta = self.client.post(reverse("categorias-producto"), {"nombre": "Galletas"}, format="json")
        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_crea_producto(self):
        self.auth(self.administrador)
        respuesta = self.client.post(reverse("productos"), {
            "categoria_id": self.categoria.pk, "nombre": "Caja de cupcakes",
            "precio_base": "280.50", "unidad_venta": "CAJA",
            "descripcion": "Doce cupcakes", "imagen_url": "https://example.com/cupcakes.jpg"
        }, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        nuevo = Producto.objects.get(pk=respuesta.data["id"])
        self.assertEqual(nuevo.precio_base, Decimal("280.50"))

    def test_precio_invalido_rechazado(self):
        self.auth(self.administrador)
        respuesta = self.client.post(reverse("productos"), {
            "categoria_id": self.categoria.pk, "nombre": "Pastel sin precio", "precio_base": "0"
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_categoria_inactiva_no_admite_productos(self):
        self.auth(self.administrador)
        respuesta = self.client.post(reverse("productos"), {
            "categoria_id": self.inactiva.pk, "nombre": "Prueba", "precio_base": "100.00"
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_rechazar_duplicados_por_categoria(self):
        self.auth(self.administrador)
        respuesta = self.client.post(reverse("productos"), {
            "categoria_id": self.categoria.pk, "nombre": "PASTEL DE CHOCOLATE", "precio_base": "500.00"
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_ventas_ve_solo_productos_activos(self):
        self.auth(self.vendedor)
        respuesta = self.client.get(reverse("productos"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data), 1)
        self.assertEqual(respuesta.data[0]["nombre"], "Pastel de chocolate")

    def test_cliente_solo_consulta_activos(self):
        self.auth(self.cliente)
        self.assertEqual(len(self.client.get(reverse("productos")).data), 1)
        self.assertEqual(self.client.get(reverse("producto-detalle"), args=(self.producto_inactivo.pk,)).status_code, 404)

    def test_ventas_no_modifica_producto(self):
        self.auth(self.vendedor)
        respuesta = self.client.patch(reverse("producto-detalle", args=(self.producto.pk,)), {
            "precio_base": "15.00"
        }, format="json")
        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_edita_producto(self):
        self.auth(self.administrador)
        respuesta = self.client.patch(reverse("producto-detalle", args=(self.producto.pk,)), {
            "precio_base": "425.00"
        }, format="json")
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio_base, Decimal("425.00"))

    def test_filtro_por_categoria_y_busqueda(self):
        self.auth(self.administrador)
        respuesta = self.client.get(reverse("productos"), {"buscar": "chocolate", "categoria": self.categoria.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data), 1)

    def test_estado_producto(self):
        self.auth(self.administrador)
        respuesta = self.client.patch(reverse("producto-estado", args=(self.producto.pk,)), {
            "activo": False
        }, format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)

    def test_no_desactivar_categoria_con_productos_activos(self):
        self.auth(self.administrador)
        respuesta = self.client.patch(reverse("categoria-producto-estado", args=(self.categoria.pk,)), {
            "activo": False
        }, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_no_permitir_eliminar_productos(self):
        self.auth(self.administrador)
        self.assertEqual(self.client.delete(reverse("producto-detalle", args=(self.producto.pk,))).status_code, 405)

    def test_filtro_activo_invalido(self):
        self.auth(self.administrador)
        respuesta = self.client.get(reverse("productos"), {"activo": "quizas"})
        self.assertEqual(respuesta.status_code, 400)

    def crear_archivo_imagen(self, nombre="pastel.png", formato="PNG", dimensiones=(240, 240)):
        salida = BytesIO()
        Image.new("RGB", dimensiones, color=(238, 160, 175)).save(salida, format=formato)
        return SimpleUploadedFile(nombre, salida.getvalue(), content_type="image/png")

    def test_admin_sube_imagen_al_crear_producto(self):
        self.auth(self.administrador)
        with tempfile.TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            respuesta = self.client.post(reverse("productos"), {
                "nombre": "Pastel de fresa", "categoria_id": self.categoria.pk,
                "precio_base": "300.00", "unidad_venta": "PIEZA",
                "imagen": self.crear_archivo_imagen(),
            }, format="multipart")
            self.assertEqual(respuesta.status_code, 201, respuesta.data)
            producto = Producto.objects.get(id=respuesta.data["id"])
            self.assertTrue(producto.imagen.name.startswith("productos/"))
            self.assertIn("/media/productos/", respuesta.data["imagen_url"])
            self.assertTrue(producto.imagen.storage.exists(producto.imagen.name))

    def test_admin_reemplaza_imagen_con_patch(self):
        self.auth(self.administrador)
        with tempfile.TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            respuesta = self.client.patch(reverse("producto-detalle", args=(self.producto.pk,)), {
                "imagen": self.crear_archivo_imagen(),
            }, format="multipart")
            self.assertEqual(respuesta.status_code, 200, respuesta.data)
            self.producto.refresh_from_db()
            self.assertTrue(self.producto.imagen.name.endswith(".png"))

    def test_rechaza_archivo_mayor_a_3mb(self):
        from .serializers import ProductoSerializer
        from rest_framework.exceptions import ValidationError
        archivo = SimpleUploadedFile(
            "pastel.png", b"x" * (3 * 1024 * 1024 + 1), content_type="image/png"
        )
        with self.assertRaisesMessage(ValidationError, "3 MB"):
            ProductoSerializer().validate_imagen(archivo)

    def test_rechaza_imagen_falsa(self):
        self.auth(self.administrador)
        archivo = SimpleUploadedFile("pastel.png", b"no es una imagen", content_type="image/png")
        respuesta = self.client.post(reverse("productos"), {
            "nombre": "Archivo falso", "categoria_id": self.categoria.pk,
            "precio_base": "90.00", "imagen": archivo,
        }, format="multipart")
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(Producto.objects.filter(nombre="Archivo falso").exists())

    def test_rechaza_imagen_con_extension_incorrecta(self):
        self.auth(self.administrador)
        respuesta = self.client.post(reverse("productos"), {
            "nombre": "Archivo incorrecto", "categoria_id": self.categoria.pk,
            "precio_base": "90.00", "imagen": self.crear_archivo_imagen(nombre="pastel.gif"),
        }, format="multipart")
        self.assertEqual(respuesta.status_code, 400)

    def test_rechaza_imagen_demasiado_pequena(self):
        self.auth(self.administrador)
        respuesta = self.client.post(reverse("productos"), {
            "nombre": "Miniatura invalida", "categoria_id": self.categoria.pk,
            "precio_base": "90.00", "imagen": self.crear_archivo_imagen(dimensiones=(40, 40)),
        }, format="multipart")
        self.assertEqual(respuesta.status_code, 400)

    def test_ventas_no_puede_subir_imagen(self):
        self.auth(self.vendedor)
        respuesta = self.client.patch(reverse("producto-detalle", args=(self.producto.pk,)), {
            "imagen": self.crear_archivo_imagen(),
        }, format="multipart")
        self.assertEqual(respuesta.status_code, 403)
