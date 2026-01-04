from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Procesador de imágenes local para optimizar antes de enviar a API."""
    
    MAX_SIZE = (1200, 1200)
    QUALITY = 85
    MIN_DIMENSION = 400
    
    @staticmethod
    def preprocess_image(image_bytes: bytes) -> bytes:
        """
        Redimensiona, verifica y comprime la imagen.
        Retorna bytes de imagen optimizada (JPEG).
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # 1. Validar dimensiones mínimas (evitar iconos o errores)
            if img.width < ImageProcessor.MIN_DIMENSION and img.height < ImageProcessor.MIN_DIMENSION:
                # Si es muy pequeña, tal vez no es legible, pero intentamos igual
                logger.warning(f"Imagen pequeña detectada: {img.size}")
            
            # 2. Convertir a RGB si es necesario (ej: PNG transparente)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # 3. Redimensionar si excede MAX_SIZE (manteniendo aspect ratio)
            img.thumbnail(ImageProcessor.MAX_SIZE, Image.Resampling.LANCZOS)
            
            # 4. Comprimir a buffer
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=ImageProcessor.QUALITY, optimize=True)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error procesando imagen: {e}")
            raise ValueError("No se pudo procesar la imagen. Asegúrate que sea un formato válido.")

    @staticmethod
    def validate_marketplace_screenshot(image_bytes: bytes) -> bool:
        """Check simple de validez."""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # Simples chequeos
            if img.format not in ['JPEG', 'PNG', 'WEBP']:
                return False
            if img.width < 100 or img.height < 100:
                return False
            return True
        except:
            return False
