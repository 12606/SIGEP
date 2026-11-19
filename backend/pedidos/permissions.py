from rest_framework.exceptions import PermissionDenied


def codigo_rol(usuario):
    if not usuario or not usuario.is_authenticated or not usuario.is_active:
        return None
    if usuario.is_superuser:
        return "ADMIN"
    rol = getattr(usuario, "rol", None)
    if rol and rol.activo:
        return rol.codigo
    return None


def exigir_rol(usuario, permitidos):
    rol = codigo_rol(usuario)
    if rol not in permitidos:
        raise PermissionDenied("No tienes permisos para esta operación.")
    return rol
