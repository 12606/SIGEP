from rest_framework.permissions import BasePermission


class EsAdministradorSIGEP(BasePermission):
    """No confundir is_staff de Django con el rol ADMIN de SIGEP."""
    message = "Solo un administrador de SIGEP puede realizar esta operación."

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario or not usuario.is_authenticated or not usuario.is_active:
            return False
        if usuario.is_superuser:
            return True
        return bool(usuario.rol_id and usuario.rol.activo and usuario.rol.codigo == "ADMIN")
