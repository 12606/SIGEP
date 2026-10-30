from django.core.management.base import BaseCommand
from usuarios.models import Rol, Usuario

ROLES = [
    ("ADMIN", "Administrador", "Acceso administrativo"),
    ("VENTAS", "Vendedor", "Atiende clientes y registra pedidos"),
    ("REPOSTERO", "Repostero", "Consulta y prepara pedidos"),
    ("ALMACEN", "Almacén", "Gestiona el inventario"),
]

class Command(BaseCommand):
    help = "Crea los roles de SIGEP y asigna ADMIN a superusuarios sin rol."

    def handle(self, *args, **options):
        for codigo, nombre, descripcion in ROLES:
            Rol.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre, "descripcion": descripcion, "activo": True})
        admin = Rol.objects.get(codigo="ADMIN")
        Usuario.objects.filter(is_superuser=True, rol__isnull=True).update(rol=admin)
        self.stdout.write(self.style.SUCCESS("Roles preparados: ADMIN, VENTAS, REPOSTERO, ALMACEN"))
