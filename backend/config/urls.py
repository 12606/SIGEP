from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenRefreshView
from usuarios.views import LoginView, RegistroPublicoView

urlpatterns = [
    # SIGEP web (frontend HTML desde la carpeta hermana frontend/)
    path("", TemplateView.as_view(template_name="index.html"), name="inicio"),
    path("admin/", admin.site.urls),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/register/", RegistroPublicoView.as_view(), name="public-register"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("api/", include("usuarios.urls")),
    path("api/", include("clientes.urls")),
]
