from django.urls import path

from .views import DashboardView, ExportarDatosView

urlpatterns = [
    path("reportes/dashboard/", DashboardView.as_view(), name="reportes-dashboard"),
    path("reportes/exportar/", ExportarDatosView.as_view(), name="reportes-exportar"),
]
