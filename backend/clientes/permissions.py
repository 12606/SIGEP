from rest_framework.permissions import BasePermission


def codigo_rol(user):
    if not user or not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return "ADMIN"
    rol = getattr(user, "rol", None)
    return rol.codigo if rol and rol.activo else None


class EsAdministradorOVentas(BasePermission):
    """Directorio y edición de clientes, pero no desactivación de fichas."""
    message = "Solo ADMIN y VENTAS pueden consultar y editar clientes."

    def has_permission(self, request, view):
        return codigo_rol(request.user) in ("ADMIN", "VENTAS")


class EsAdministradorClientes(BasePermission):
    """Único rol que puede activar/desactivar fichas comerciales."""
    message = "Solo ADMIN puede activar o desactivar fichas de clientes."

    def has_permission(self, request, view):
        return codigo_rol(request.user) == "ADMIN"


class EsClientePropio(BasePermission):
    """La ficha propia es exclusiva del rol CLIENTE."""
    message = "Esta ficha solo está disponible para cuentas de cliente."

    def has_permission(self, request, view):
        return codigo_rol(request.user) == "CLIENTE"
