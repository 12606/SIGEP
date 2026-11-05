from django.core.management.base import BaseCommand
from django.db import transaction
from clientes.models import Cliente
from usuarios.models import Usuario


class Command(BaseCommand):
    help = "Crea fichas Cliente faltantes para cuentas web con rol CLIENTE. Es idempotente."

    def handle(self, *args, **options):
        creados = 0
        vinculados = 0
        omitidos = 0
        cuentas = Usuario.objects.filter(rol__codigo="CLIENTE").order_by("pk")
        with transaction.atomic():
            for usuario in cuentas:
                if Cliente.objects.filter(usuario=usuario).exists():
                    omitidos += 1
                    continue
                # Si ya existía una ficha manual con el mismo correo, no se
                # vincula automáticamente: puede pertenecer a otra persona.
                correo = (usuario.email or "").strip().lower()
                if correo and Cliente.objects.filter(usuario__isnull=True, correo__iexact=correo).exists():
                    omitidos += 1
                    continue
                Cliente.objects.create(
                    usuario=usuario,
                    nombre=usuario.first_name or usuario.username,
                    apellidos=usuario.last_name or "Sin apellidos",
                    correo=correo,
                    telefono=usuario.telefono or "",
                )
                creados += 1
                vinculados += 1
        self.stdout.write(self.style.SUCCESS(
            f"Perfiles creados: {creados}. Ya existentes o pendientes de revisión: {omitidos}."
        ))
