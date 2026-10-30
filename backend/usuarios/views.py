from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import connection
from .models import Usuario
from .serializers import UsuarioCrearSerializer, UsuarioSerializer

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health(request):
    # Comprueba que la API realmente puede conectarse a MariaDB.
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return Response({"status": "ok", "servicio": "SIGEP API", "base_de_datos": "conectada"})

class MiPerfilView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer

    def get_object(self):
        return self.request.user

class UsuariosView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Usuario.objects.select_related("rol").all().order_by("id")

    def get_serializer_class(self):
        return UsuarioCrearSerializer if self.request.method == "POST" else UsuarioSerializer
