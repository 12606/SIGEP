"""Reglas de permisos del inventario, verificadas en la API."""
from rest_framework.exceptions import PermissionDenied


def rol_usuario(usuario):
    if not usuario or not usuario.is_authenticated or not usuario.is_active:
        return None
    if usuario.is_superuser:
        return "ADMIN"
    rol = getattr(usuario, "rol", None)
    return rol.codigo if rol and rol.activo else None


def exigir_rol(usuario, permitidos):
    rol = rol_usuario(usuario)
    if rol not in permitidos:
        raise PermissionDenied("No tienes permiso para esta operación de inventario.")
    return rol
