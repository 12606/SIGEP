from rest_framework.permissions import BasePermission


class EsAdministradorOVentas(BasePermission):
    message = "Solo ADMIN o VENTAS pueden administrar clientes."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        rol = getattr(user, "rol", None)
        return bool(rol and rol.activo and rol.codigo in ("ADMIN", "VENTAS"))
