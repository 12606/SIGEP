from django.urls import path
from .views import EstadoUsuarioView, LogoutView, MiPerfilView, RolesView, UsuarioDetalleView, UsuariosView, health

urlpatterns = [
    path("health/", health, name="health"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("roles/", RolesView.as_view(), name="roles"),
    path("usuarios/me/", MiPerfilView.as_view(), name="mi-perfil"),
    path("usuarios/", UsuariosView.as_view(), name="usuarios"),
    path("usuarios/<int:pk>/", UsuarioDetalleView.as_view(), name="usuario-detalle"),
    path("usuarios/<int:pk>/estado/", EstadoUsuarioView.as_view(), name="usuario-estado"),
]
