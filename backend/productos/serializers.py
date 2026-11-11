from pathlib import Path
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from .models import CategoriaProducto, Producto


class CategoriaProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaProducto
        fields = ("id", "nombre", "descripcion", "activo")
        read_only_fields = ("id", "activo")

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Indica un nombre para la categoría.")
        queryset = CategoriaProducto.objects.filter(nombre__iexact=value)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe una categoría con ese nombre.")
        return value


class ProductoSerializer(serializers.ModelSerializer):
    # "imagen" solo recibe archivos. "imagen_url" expone la ruta para la tabla.
    imagen = serializers.ImageField(write_only=True, required=False, allow_empty_file=False)
    imagen_url = serializers.SerializerMethodField()
    categoria = serializers.PrimaryKeyRelatedField(read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    categoria_id = serializers.PrimaryKeyRelatedField(
        source="categoria",
        queryset=CategoriaProducto.objects.filter(activo=True),
        write_only=True,
    )

    class Meta:
        model = Producto
        fields = (
            "id", "categoria", "categoria_nombre", "categoria_id",
            "nombre", "descripcion", "precio_base", "unidad_venta",
            "imagen", "imagen_url", "activo",
        )
        read_only_fields = ("id", "activo", "categoria", "categoria_nombre")

    def get_imagen_url(self, producto):
        if producto.imagen:
            ruta = producto.imagen.url
            peticion = self.context.get("request")
            return peticion.build_absolute_uri(ruta) if peticion else ruta
        # Se conservan enlaces previos mientras se migran las fotos existentes.
        return producto.imagen_url or ""

    def validate_imagen(self, archivo):
        """Comprueba tamaño, extensión, contenido real y dimensiones."""
        limite = 3 * 1024 * 1024  # 3 MiB
        if archivo.size > limite:
            raise serializers.ValidationError("La imagen no debe superar 3 MB.")

        extension = Path(archivo.name).suffix.lower()
        formatos = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
        if extension not in formatos:
            raise serializers.ValidationError("Solo se permiten JPG, PNG o WebP.")

        try:
            archivo.seek(0)
            with Image.open(archivo) as foto:
                formato_real = foto.format
                ancho, alto = foto.size
                cuadros = getattr(foto, "n_frames", 1)
                foto.verify()  # verifica contenido; no basta con la extensión
            if formato_real != formatos[extension]:
                raise serializers.ValidationError("La extensión no coincide con el formato real.")
            if cuadros != 1:
                raise serializers.ValidationError("No se permiten imágenes animadas.")
            if not (100 <= ancho <= 4096 and 100 <= alto <= 4096):
                raise serializers.ValidationError("La imagen debe medir entre 100 y 4096 píxeles por lado.")
            # Verifica además que Pillow pueda decodificar la imagen completa.
            archivo.seek(0)
            with Image.open(archivo) as foto:
                foto.load()
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            raise serializers.ValidationError("El archivo está dañado o no es una imagen válida.")
        finally:
            archivo.seek(0)
        return archivo

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre del producto es obligatorio.")
        return value

    def validate(self, attrs):
        categoria = attrs.get("categoria", getattr(self.instance, "categoria", None))
        nombre = attrs.get("nombre", getattr(self.instance, "nombre", None))
        if categoria is not None and nombre is not None:
            duplicados = Producto.objects.filter(
                categoria=categoria, nombre__iexact=nombre
            )
            if self.instance is not None:
                duplicados = duplicados.exclude(pk=self.instance.pk)
            if duplicados.exists():
                raise serializers.ValidationError({
                    "nombre": "Ya existe un producto con ese nombre en la categoría."
                })
        return attrs


class EstadoSerializer(serializers.Serializer):
    activo = serializers.BooleanField(required=True)
