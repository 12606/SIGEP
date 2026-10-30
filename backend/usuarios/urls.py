from django.urls import path
from .views import health, MiPerfilView, UsuariosView

urlpatterns = [
    path("health/", health, name="health"),
    path("usuarios/me/", MiPerfilView.as_view(), name="mi-perfil"),
    path("usuarios/", UsuariosView.as_view(), name="usuarios"),
]
