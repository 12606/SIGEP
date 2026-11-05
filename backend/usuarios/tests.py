from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Rol

Usuario = get_user_model()


class UsuariosAPITests(APITestCase):
    def setUp(self):
        self.admin_rol = Rol.objects.create(codigo="ADMIN", nombre="Administrador")
        self.ventas_rol = Rol.objects.create(codigo="VENTAS", nombre="Vendedor")
        self.admin = Usuario.objects.create_superuser(
            username="admin", email="admin@example.com", password="ClaveAdmin!2026", rol=self.admin_rol
        )
        self.ventas = Usuario.objects.create_user(
            username="vendedor", email="ventas@example.com", password="ClaveVentas!2026", rol=self.ventas_rol
        )

    def acceso(self, username, password):
        response = self.client.post(reverse("login"), {"username": username, "password": password}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def autorizar(self, username="admin", password="ClaveAdmin!2026"):
        tokens = self.acceso(username, password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return tokens

    def test_login_y_perfil(self):
        self.autorizar("vendedor", "ClaveVentas!2026")
        resp = self.client.get(reverse("mi-perfil"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["rol"]["codigo"], "VENTAS")
        self.assertNotIn("password", resp.data)

    def test_credenciales_incorrectas(self):
        resp = self.client.post(reverse("login"), {"username": "vendedor", "password": "incorrecta"}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_endpoints_privados_requieren_token(self):
        for url in [reverse("mi-perfil"), reverse("usuarios"), reverse("roles")]:
            self.assertEqual(self.client.get(url).status_code, 401)

    def test_ventas_no_puede_administrar(self):
        self.autorizar("vendedor", "ClaveVentas!2026")
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 403)
        self.assertEqual(self.client.get(reverse("roles")).status_code, 403)
        resp = self.client.post(reverse("usuarios"), {"username": "nuevo"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.client.patch(reverse("usuario-estado", args=[self.admin.id]), {"activo": False}, format="json").status_code, 403)

    def test_admin_lista_roles_y_usuarios(self):
        self.autorizar()
        self.assertEqual(self.client.get(reverse("roles")).status_code, 200)
        response = self.client.get(reverse("usuarios"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_admin_crea_y_edita_usuario(self):
        self.autorizar()
        data = {"username": "nuevo", "email": "nuevo@example.com", "first_name": "Ana", "password": "NuevaClave!2026", "rol_codigo": "VENTAS"}
        response = self.client.post(reverse("usuarios"), data, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["rol"]["codigo"], "VENTAS")
        self.assertNotIn("password", response.data)
        usuario = Usuario.objects.get(username="nuevo")
        self.assertTrue(usuario.check_password("NuevaClave!2026"))
        detalle = self.client.get(reverse("usuario-detalle", args=[usuario.id]))
        self.assertEqual(detalle.status_code, 200)
        modif = self.client.patch(reverse("usuario-detalle", args=[usuario.id]), {"first_name": "Ana María", "password": "OtraClave!2026"}, format="json")
        self.assertEqual(modif.status_code, 200, modif.data)
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, "Ana María")
        self.assertTrue(usuario.check_password("OtraClave!2026"))
        self.assertFalse(usuario.check_password("NuevaClave!2026"))

    def test_admin_desactiva_y_reactiva(self):
        self.autorizar()
        url = reverse("usuario-estado", args=[self.ventas.id])
        self.assertEqual(self.client.patch(url, {"activo": False}, format="json").status_code, 200)
        self.ventas.refresh_from_db()
        self.assertFalse(self.ventas.is_active)
        self.client.credentials()
        self.assertEqual(self.client.post(reverse("login"), {"username": "vendedor", "password": "ClaveVentas!2026"}, format="json").status_code, 401)
        self.autorizar()
        self.assertEqual(self.client.patch(url, {"activo": True}, format="json").status_code, 200)
        self.ventas.refresh_from_db()
        self.assertTrue(self.ventas.is_active)

    def test_no_se_permite_autodesactivacion(self):
        self.autorizar()
        resp = self.client.patch(reverse("usuario-estado", args=[self.admin.id]), {"activo": False}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_datos_invalidos_rechazados(self):
        self.autorizar()
        data = {"username": "vendedor", "email": "ventas@example.com", "password": "123", "rol_codigo": "VENTAS"}
        self.assertEqual(self.client.post(reverse("usuarios"), data, format="json").status_code, 400)
        data = {"username": "nuevo", "email": "nuevo@example.com", "password": "NuevaClave!2026", "rol_codigo": "INEXISTENTE"}
        self.assertEqual(self.client.post(reverse("usuarios"), data, format="json").status_code, 400)

    def test_logout_revoca_refresh(self):
        tokens = self.autorizar("vendedor", "ClaveVentas!2026")
        logout = self.client.post(reverse("logout"), {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(logout.status_code, 205, logout.data)
        self.assertEqual(self.client.post(reverse("refresh"), {"refresh": tokens["refresh"]}, format="json").status_code, 401)

    def test_rol_admin_puede_administrar_sin_ser_staff(self):
        jefe = Usuario.objects.create_user(username="jefe", email="jefe@example.com", password="ClaveJefe!2026", rol=self.admin_rol)
        self.assertFalse(jefe.is_staff)
        self.autorizar("jefe", "ClaveJefe!2026")
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 200)

    def test_staff_sin_rol_admin_no_puede_administrar(self):
        self.ventas.is_staff = True
        self.ventas.save(update_fields=["is_staff"])
        self.autorizar("vendedor", "ClaveVentas!2026")
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 403)

    def test_password_inseguro_se_rechaza(self):
        self.autorizar()
        response = self.client.post(reverse("usuarios"), {
            "username": "inseguro", "email": "inseguro@example.com", "password": "123", "rol_codigo": "VENTAS"
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("password", response.data)

    def test_logout_no_acepta_refresh_de_otro_usuario(self):
        tokens = self.acceso("vendedor", "ClaveVentas!2026")
        self.autorizar()
        logout = self.client.post(reverse("logout"), {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(logout.status_code, 403)

    def test_refresh_token_gira_y_el_viejo_es_revocado(self):
        tokens = self.acceso("vendedor", "ClaveVentas!2026")
        response = self.client.post(reverse("refresh"), {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(self.client.post(reverse("refresh"), {"refresh": tokens["refresh"]}, format="json").status_code, 401)


class RegistroPublicoTests(APITestCase):
    def setUp(self):
        self.cliente = Rol.objects.create(codigo="CLIENTE", nombre="Cliente", activo=True)
        Rol.objects.create(codigo="ADMIN", nombre="Administrador", activo=True)
        self.payload = {
            "username": "ana_cliente", "email": "ana@example.com",
            "first_name": "Ana", "last_name": "Pérez",
            "password": "Segura#Vainilla2026", "password_confirm": "Segura#Vainilla2026",
        }

    def test_registro_publico_crea_cliente_no_admin(self):
        payload = {**self.payload, "rol_codigo": "ADMIN", "is_superuser": True, "is_staff": True}
        response = self.client.post(reverse("public-register"), payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        usuario = Usuario.objects.get(username="ana_cliente")
        self.assertEqual(usuario.rol.codigo, "CLIENTE")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertTrue(usuario.check_password(self.payload["password"]))
        self.assertNotIn("password", response.data["usuario"])

    def test_login_con_email_y_usuario(self):
        response = self.client.post(reverse("public-register"), self.payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        for value in ["ana_cliente", "ana@example.com"]:
            login = self.client.post(reverse("login"), {"username": value, "password": self.payload["password"]}, format="json")
            self.assertEqual(login.status_code, 200, login.data)
            self.assertIn("access", login.data)

    def test_no_se_permite_correo_repetido(self):
        self.client.post(reverse("public-register"), self.payload, format="json")
        payload = {**self.payload, "username": "otro", "email": "ANA@EXAMPLE.COM"}
        response = self.client.post(reverse("public-register"), payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_rechaza_confirmacion_incorrecta(self):
        payload = {**self.payload, "password_confirm": "Distinta#2026"}
        response = self.client.post(reverse("public-register"), payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Usuario.objects.filter(username="ana_cliente").exists())

    def test_rechaza_contrasena_debil(self):
        payload = {**self.payload, "password": "1234", "password_confirm": "1234"}
        response = self.client.post(reverse("public-register"), payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_cliente_no_puede_administrar_usuarios(self):
        self.client.post(reverse("public-register"), self.payload, format="json")
        login = self.client.post(reverse("login"), {"username": "ana_cliente", "password": self.payload["password"]}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 403)
        self.assertEqual(self.client.get(reverse("mi-perfil")).status_code, 200)
