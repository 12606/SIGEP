from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView
from usuarios.views import LoginView, RegistroPublicoView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/register/", RegistroPublicoView.as_view(), name="public-register"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("api/", include("usuarios.urls")),
]
