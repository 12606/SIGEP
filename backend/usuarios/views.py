from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Rol, Usuario
from .permissions import EsAdministradorSIGEP
from .serializers import EstadoUsuarioSerializer, RolSerializer, UsuarioEscrituraSerializer, UsuarioSerializer


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return Response({"status": "ok", "servicio": "SIGEP API", "base_de_datos": "conectada"})


class MiPerfilView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer

    def get_object(self):
        return self.request.user


class RolesView(generics.ListAPIView):
    permission_classes = [EsAdministradorSIGEP]
    queryset = Rol.objects.all().order_by("id")
    serializer_class = RolSerializer
    pagination_class = None


class UsuariosView(generics.ListCreateAPIView):
    permission_classes = [EsAdministradorSIGEP]
    queryset = Usuario.objects.select_related("rol").all().order_by("id")

    def get_serializer_class(self):
        return UsuarioEscrituraSerializer if self.request.method == "POST" else UsuarioSerializer


class UsuarioDetalleView(generics.RetrieveUpdateAPIView):
    permission_classes = [EsAdministradorSIGEP]
    queryset = Usuario.objects.select_related("rol").all()
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        return UsuarioEscrituraSerializer if self.request.method == "PATCH" else UsuarioSerializer


class EstadoUsuarioView(APIView):
    permission_classes = [EsAdministradorSIGEP]

    def patch(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        serializer = EstadoUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activo = serializer.validated_data["activo"]
        if usuario.pk == request.user.pk and not activo:
            raise serializers.ValidationError({"activo": "No puedes desactivar tu propia cuenta."})
        if usuario.is_superuser and not activo:
            raise serializers.ValidationError({"activo": "No se puede desactivar un superusuario desde esta API."})
        usuario.is_active = activo
        usuario.save(update_fields=["is_active"])
        return Response(UsuarioSerializer(usuario).data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        valor = request.data.get("refresh")
        if not isinstance(valor, str) or not valor.strip():
            raise serializers.ValidationError({"refresh": "Debes enviar el refresh token."})
        try:
            token = RefreshToken(valor)
            if str(token["user_id"]) != str(request.user.pk):
                return Response({"detail": "El token no pertenece al usuario."}, status=status.HTTP_403_FORBIDDEN)
            token.blacklist()
        except (TokenError, KeyError):
            raise serializers.ValidationError({"refresh": "Token inválido o ya revocado."})
        # JWT stateless: el access existente dura hasta su caducidad (15 minutos).
        return Response(status=status.HTTP_205_RESET_CONTENT)
