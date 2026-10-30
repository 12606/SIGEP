from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

class LoginTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="demo", email="demo@example.com", password="ClavePrueba!123"
        )

    def test_login_correcto_y_perfil(self):
        respuesta = self.client.post(reverse("login"), {"username": "demo", "password": "ClavePrueba!123"}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn("access", respuesta.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
        perfil = self.client.get(reverse("mi-perfil"))
        self.assertEqual(perfil.status_code, status.HTTP_200_OK)
        self.assertEqual(perfil.data["username"], "demo")

    def test_login_incorrecto(self):
        respuesta = self.client.post(reverse("login"), {"username": "demo", "password": "incorrecta"}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_perfil_requiere_token(self):
        respuesta = self.client.get(reverse("mi-perfil"))
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_normal_no_puede_crear_cuentas(self):
        self.client.force_authenticate(self.user)
        respuesta = self.client.post(reverse("usuarios"), {"username": "otro"}, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
