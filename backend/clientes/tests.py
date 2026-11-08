from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Cliente
from usuarios.models import Rol

Usuario = get_user_model()


class ClientesAPITests(APITestCase):
    def setUp(self):
        self.rol_admin = Rol.objects.create(codigo="ADMIN", nombre="Administrador")
        self.rol_ventas = Rol.objects.create(codigo="VENTAS", nombre="Ventas")
        self.rol_cliente = Rol.objects.create(codigo="CLIENTE", nombre="Cliente")
        self.rol_repostero = Rol.objects.create(codigo="REPOSTERO", nombre="Repostero")
        self.admin = Usuario.objects.create_user(
            username="gerente", email="gerente@example.com", password="ClaveSegura2026!", rol=self.rol_admin,
        )
        self.vendedor = Usuario.objects.create_user(
            username="ventas", email="ventas@example.com", password="ClaveSegura2026!", rol=self.rol_ventas,
        )
        self.repostero = Usuario.objects.create_user(
            username="repostero", email="repostero@example.com", password="ClaveSegura2026!", rol=self.rol_repostero,
        )
        self.cliente_web = Usuario.objects.create_user(
            username="clientews", email="web@example.com", password="ClaveSegura2026!", rol=self.rol_cliente,
        )
        self.ficha = Cliente.objects.create(
            nombre="Mariana", apellidos="López", telefono="3312345678", correo="mariana@example.com",
        )

    def autorizar(self, usuario):
        self.client.force_authenticate(user=usuario)

    def test_sin_token_no_hay_acceso(self):
        self.assertEqual(self.client.get(reverse("clientes")).status_code, 401)

    def test_admin_puede_crear_y_consultar(self):
        self.autorizar(self.admin)
        response = self.client.post(reverse("clientes"), {
            "nombre": "Carlos", "apellidos": "Pérez", "telefono": "3311112222",
            "correo": "CARLOS@EXAMPLE.COM", "direccion": "Centro",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["correo"], "carlos@example.com")
        self.assertTrue(Cliente.objects.filter(nombre="Carlos").exists())
        lista = self.client.get(reverse("clientes"))
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(len(lista.data), 2)

    def test_ventas_puede_editar(self):
        self.autorizar(self.vendedor)
        response = self.client.patch(reverse("cliente-detalle", args=[self.ficha.pk]), {
            "telefono": "3399998888",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.ficha.refresh_from_db()
        self.assertEqual(self.ficha.telefono, "3399998888")

    def test_filtros_y_busqueda(self):
        Cliente.objects.create(nombre="Luis", apellidos="Soto", activo=False)
        self.autorizar(self.vendedor)
        listado = self.client.get(reverse("clientes"), {"buscar": "mariana", "activo": "true"})
        self.assertEqual(listado.status_code, 200)
        self.assertEqual(len(listado.data), 1)
        inactivos = self.client.get(reverse("clientes"), {"activo": "false"})
        self.assertEqual(len(inactivos.data), 1)
        self.assertEqual(self.client.get(reverse("clientes"), {"activo": "incorrecto"}).status_code, 400)

    def test_desactivar_y_reactivar(self):
        self.autorizar(self.admin)
        url = reverse("cliente-estado", args=[self.ficha.pk])
        self.assertEqual(self.client.patch(url, {"activo": False}, format="json").status_code, 200)
        self.ficha.refresh_from_db()
        self.assertFalse(self.ficha.activo)
        self.assertEqual(self.client.patch(url, {"activo": True}, format="json").status_code, 200)
        self.ficha.refresh_from_db()
        self.assertTrue(self.ficha.activo)

    def test_no_se_permite_borrado(self):
        self.autorizar(self.admin)
        self.assertEqual(self.client.delete(reverse("cliente-detalle", args=[self.ficha.pk])).status_code, 405)
        self.assertTrue(Cliente.objects.filter(pk=self.ficha.pk).exists())

    def test_usuario_vinculado_no_es_editable_desde_api(self):
        self.autorizar(self.admin)
        response = self.client.patch(reverse("cliente-detalle", args=[self.ficha.pk]), {
            "usuario": self.vendedor.pk,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.ficha.refresh_from_db()
        self.assertIsNone(self.ficha.usuario)

    def test_repostero_no_puede_administrar(self):
        self.autorizar(self.repostero)
        self.assertEqual(self.client.get(reverse("clientes")).status_code, 403)
        self.assertEqual(self.client.post(reverse("clientes"), {"nombre": "X"}, format="json").status_code, 403)

    def test_cliente_no_puede_consultar_lista(self):
        self.autorizar(self.cliente_web)
        self.assertEqual(self.client.get(reverse("clientes")).status_code, 403)

    def test_cliente_puede_consultar_solo_su_ficha(self):
        ficha_web = Cliente.objects.create(
            usuario=self.cliente_web, nombre="Ana", apellidos="Torres", correo="web@example.com",
        )
        self.autorizar(self.cliente_web)
        resp = self.client.get(reverse("cliente-me"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], ficha_web.pk)
        self.assertNotEqual(resp.data["id"], self.ficha.pk)

    def test_cliente_sin_ficha_devuelve_404(self):
        self.autorizar(self.cliente_web)
        self.assertEqual(self.client.get(reverse("cliente-me")).status_code, 404)

    def test_registro_publico_crea_usuario_y_ficha(self):
        self.client.force_authenticate(user=None)
        datos = {
            "username": "nuevo_clientew", "email": "nuevo@example.com",
            "first_name": "Rosa", "last_name": "Mendoza", "telefono": "3312345678",
            "password": "ClaveFuerte!2026", "password_confirm": "ClaveFuerte!2026",
        }
        response = self.client.post(reverse("public-register"), datos, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        cuenta = Usuario.objects.get(username="nuevo_clientew")
        self.assertEqual(cuenta.rol.codigo, "CLIENTE")
        self.assertEqual(Cliente.objects.get(usuario=cuenta).nombre, "Rosa")

    def test_registro_no_admite_rol_admin(self):
        self.client.force_authenticate(user=None)
        datos = {
            "username": "nueva_cliente", "email": "nueva@example.com",
            "first_name": "Rosa", "last_name": "Mendoza", "telefono": "3312345678",
            "password": "ClaveFuerte!2026", "password_confirm": "ClaveFuerte!2026",
            "rol_codigo": "ADMIN", "is_superuser": True,
        }
        response = self.client.post(reverse("public-register"), datos, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        cuenta = Usuario.objects.get(username="nueva_cliente")
        self.assertEqual(cuenta.rol.codigo, "CLIENTE")
        self.assertFalse(cuenta.is_superuser)

    def test_validacion_de_nombres(self):
        self.autorizar(self.admin)
        resp = self.client.post(reverse("clientes"), {"nombre": " ", "apellidos": "Pérez"}, format="json")
        self.assertEqual(resp.status_code, 400)
