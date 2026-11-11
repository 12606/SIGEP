from rest_framework.permissions import BasePermission, SAFE_METHODS


ROLES_CONSULTA = {"ADMIN", "VENTAS", "REPOSTERO", "ALMACEN", "CLIENTE"}


def es_admin(usuario):
    if not usuario or not usuario.is_authenticated or not usuario.is_active:
        return False
    if usuario.is_superuser:
        return True
    rol = getattr(usuario, "rol", None)
    return bool(rol and rol.activo and rol.codigo == "ADMIN")


class PuedeGestionarCatalogo(BasePermission):
    """Lectura para roles válidos; escritura exclusiva del administrador."""
    message = "No tienes permisos para administrar el catálogo."

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario or not usuario.is_authenticated or not usuario.is_active:
            return False
        if es_admin(usuario):
            return True
        if request.method not in SAFE_METHODS:
            return False
        rol = getattr(usuario, "rol", None)
        return bool(rol and rol.activo and rol.codigo in ROLES_CONSULTA)
