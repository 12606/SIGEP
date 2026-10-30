from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Rol, Usuario

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    search_fields = ("codigo", "nombre")

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "rol", "is_active", "is_staff")
    list_filter = ("rol", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("SIGEP", {"fields": ("telefono", "rol")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("SIGEP", {"fields": ("email", "telefono", "rol")}),)
