from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from clientes.models import Cliente
from usuarios.models import Rol

Usuario = get_user_model()


class PermisosYPerfilTests(APITestCase):
    def setUp(self):
        self.adminrol = Rol.objects.create(codigo="ADMIN", nombre="Administrador")
        self.ventasrol = Rol.objects.create(codigo="VENTAS", nombre="Ventas")
        self.clierterol = Rol.objects.create(codigo="CLIENTE", nombre="Cliente")
        self.reposterorol = Rol.objects.create(codigo="REPOSTERO", nombre="Repostero")
        self.admin = Usuario.objects.create_user(username="root_test", email="admin@example.com", password="ClaveTest123!", rol=self.adminrol)
        self.ventas = Usuario.objects.create_user(username="venta_test", email="venta@example.com", password="ClaveTest123!", rol=self.ventasrol)
        self.repostero = Usuario.objects.create_user(username="repostero_test", email="rep@example.com", password="ClaveTest123!", rol=self.reposterorol)
        self.cliente = Usuario.objects.create_user(username="cliente_test", email="cliente@example.com", password="ClaveTest123!", rol=self.clierterol)
        self.ficha = Cliente.objects.create(usuario=self.cliente, nombre="Rosa", apellidos="Torres", correo="cliente@example.com")
        self.manual = Cliente.objects.create(nombre="Persona", apellidos="Mostrador", telefono="3312345678")
        self.perfil_empleado = Cliente.objects.create(usuario=self.repostero, nombre="Repostero", apellidos="Prueba", correo="rep@example.com")

    def test_ventas_no_puede_desactivar_ficha(self):
        self.client.force_authenticate(user=self.ventas)
        respuesta = self.client.patch(reverse("cliente-estado", args=[self.manual.id]), {"activo": False}, format="json")
        self.assertEqual(respuesta.status_code, 403)
        self.manual.refresh_from_db()
        self.assertTrue(self.manual.activo)

    def test_ventas_puede_editar_ficha_de_mostrador(self):
        self.client.force_authenticate(user=self.ventas)
        respuesta = self.client.patch(reverse("cliente-detalle", args=[self.manual.id]), {"direccion": "Centro"}, format="json")
        self.assertEqual(respuesta.status_code, 200, respuesta.data)

    def test_ventas_no_puede_modificar_correo_de_acceso(self):
        self.client.force_authenticate(user=self.ventas)
        response = self.client.patch(reverse("cliente-detalle", args=[self.ficha.id]), {
            "correo": "intruso@example.com",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.email, "cliente@example.com")

    def test_admin_edita_ficha_y_sincroniza_cuenta(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(reverse("cliente-detalle", args=[self.ficha.id]), {
            "telefono": "3399988877", "correo": "cambiado@example.com",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.email, "cambiado@example.com")
        self.assertEqual(self.cliente.telefono, "3399988877")

    def test_ventas_no_ve_rol_o_id_de_cuenta(self):
        self.client.force_authenticate(user=self.ventas)
        respuesta = self.client.get(reverse("clientes"))
        self.assertEqual(respuesta.status_code, 200)
        cliente = next(item for item in respuesta.data if item["id"] == self.ficha.id)
        self.assertNotIn("usuario", cliente)
        self.assertNotIn("cuenta", cliente)
        self.assertNotIn(self.perfil_empleado.id, [item["id"] for item in respuesta.data])

    def test_ventas_no_puede_consultar_ficha_de_empleado_por_id(self):
        self.client.force_authenticate(user=self.ventas)
        self.assertEqual(self.client.get(reverse("cliente-detalle", args=[self.perfil_empleado.id])).status_code, 404)

    def test_admin_puede_cambiar_estado_y_ver_cuentas(self):
        self.client.force_authenticate(user=self.admin)
        respuesta = self.client.patch(reverse("cliente-estado", args=[self.manual.id]), {"activo": False}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Cliente.objects.get(id=self.manual.id).activo)
        lista = self.client.get(reverse("clientes"))
        self.assertTrue(any(item["id"] == self.perfil_empleado.id for item in lista.data))

    def test_cliente_edita_su_ficha_y_sincroniza_usuario(self):
        self.client.force_authenticate(user=self.cliente)
        respuesta = self.client.patch(reverse("cliente-me"), {
            "nombre": "Rosalía", "telefono": "3311122233", "direccion": "Colonia Centro",
            "correo": "nuevo@example.com",
        }, format="json")
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.cliente.refresh_from_db()
        self.ficha.refresh_from_db()
        self.assertEqual(self.cliente.first_name, "Rosalía")
        self.assertEqual(self.cliente.telefono, "3311122233")
        self.assertEqual(self.cliente.email, "nuevo@example.com")
        self.assertEqual(self.ficha.direccion, "Colonia Centro")

    def test_cliente_no_puede_cambiar_roles_desde_su_perfil(self):
        self.client.force_authenticate(user=self.cliente)
        response = self.client.patch(reverse("cliente-me"), {"rol_codigo": "ADMIN", "activo": False}, format="json")
        self.assertEqual(response.status_code, 400)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.rol.codigo, "CLIENTE")
        self.assertTrue(self.ficha.activo)

    def test_cliente_no_puede_usar_directorio(self):
        self.client.force_authenticate(user=self.cliente)
        self.assertEqual(self.client.get(reverse("clientes")).status_code, 403)

    def test_empleado_edita_su_perfil_sin_elevar_privilegios(self):
        self.client.force_authenticate(user=self.ventas)
        url = reverse("mi-perfil")
        res = self.client.patch(url, {"telefono": "3311112222", "email": "ventanueva@example.com"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.ventas.refresh_from_db()
        self.assertEqual(self.ventas.email, "ventanueva@example.com")
        denied = self.client.patch(url, {"rol_codigo": "ADMIN", "is_superuser": True}, format="json")
        self.assertEqual(denied.status_code, 400)
        self.ventas.refresh_from_db()
        self.assertEqual(self.ventas.rol.codigo, "VENTAS")
        self.assertFalse(self.ventas.is_superuser)

    def test_no_permiso_editar_ficha_propia_de_cliente_si_es_repostero(self):
        self.client.force_authenticate(user=self.repostero)
        self.assertEqual(self.client.patch(reverse("cliente-me"), {"nombre": "Nuevo"}, format="json").status_code, 403)
        self.assertEqual(self.client.get(reverse("mi-perfil")).status_code, 200)

    def test_no_autenticado_no_puede_ver_perfil(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(reverse("mi-perfil")).status_code, 401)

    def test_email_duplicado_rechazado(self):
        self.client.force_authenticate(user=self.cliente)
        response = self.client.patch(reverse("cliente-me"), {"correo": "VENTA@example.com"}, format="json")
        self.assertEqual(response.status_code, 400)
