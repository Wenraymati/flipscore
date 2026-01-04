import google.generativeai as genai
import json
import logging
from typing import Dict, Any
import io
from PIL import Image
from backend.config import get_settings

logger = logging.getLogger(__name__)

VISION_USER_PROMPT_TEMPLATE = """
Analiza este screenshot de Facebook Marketplace Chile.

EXTRAE estos campos del texto visible:
- producto: nombre/modelo del producto
- precio: número en CLP (solo dígitos)
- descripcion: texto descriptivo del vendedor
- ubicacion: comuna/ciudad si aparece
- estado: nuevo/usado/como nuevo
- señales: cualquier detalle relevante (batería, fallas, motivo venta)

LUEGO EVALÚA usando estos precios de referencia:
{reference_prices}

RESPONDE SOLO JSON con esta estructura:
{{
  "extraccion": {{ "producto": "", "precio": 0, "descripcion": "", "ubicacion": "", "estado": "", "senales_detectadas": [] }},
  "evaluacion": {{ "categoria": "", "score_total": 0.0, "precio_referencia_nuevo": 0, "precio_referencia_usado": 0, "descuento_porcentaje": 0.0, "margen_estimado": 0, "margen_porcentaje": 0.0, "tiempo_venta": "", "liquidez": "" }},
  "recomendacion": {{ "decision": "COMPRAR/PASAR/NEGOCIAR", "confianza": 0.0, "razonamiento": "", "precio_max_oferta": 0, "acciones": [] }},
  "alertas": [],
  "calidad_imagen": {{ "texto_legible": true, "info_completa": true, "confianza_extraccion": 0.0 }}
}}
"""

class VisionClient:
    """Invoca a Gemini Vision para analizar imágenes."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    def extract_and_evaluate(self, image_bytes: bytes, reference_prices: Dict) -> Dict[str, Any]:
        """
        Envía imagen a Gemini para extracción y evaluación simultánea.
        """
        # MOCK MODE check removed (handled by env var globally mostly but good to implement fallback if client is None)
        if not self.model:
             return self._get_mock_vision_response()

        # Convert bytes to PIL Image for Gemini
        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.error(f"Error opening image for Gemini: {e}")
            raise ValueError("Invalid image format")

        # Construir Prompt
        user_text = VISION_USER_PROMPT_TEMPLATE.format(
            reference_prices=json.dumps(reference_prices, indent=2, ensure_ascii=False)
        )

        try:
            response = self.model.generate_content(
                [user_text, image],
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            
            return json.loads(response.text)

        except Exception as e:
            logger.error(f"Error en Vision API (Gemini): {e}")
            # FALLBACK AUTOMÁTICO PARA DEMO
            mock_response = self._get_mock_vision_response()
            # Detectar si es error de cuota
            msg = "⚠️ DEMO MODE: API Rate Limited (Quota Exceeded). Mostrando resultado simulación." if "429" in str(e) else f"⚠️ DEMO MODE: {str(e)[:40]}..."
            mock_response["alertas"].append(msg)
            return mock_response

    def _get_mock_vision_response(self) -> Dict:
        """Respuesta simulada para Vision (Fallback - Tuned for Demo)."""
        return {
            "extraccion": {
                "producto": "iPhone 13 128GB",
                "precio": 380000,
                "descripcion": "En venta por renovación. Face ID funcionando impecable. Batería 88%.",
                "ubicacion": "Providencia, RM",
                "estado": "usado - buen estado",
                "senales_detectadas": ["Pantalla sin rayas", "Batería 88%", "Incluye caja"]
            },
            "evaluacion": {
                "categoria": "Celulares",
                "score_total": 8.8,
                "precio_referencia_nuevo": 590000,
                "precio_referencia_usado": 420000,
                "descuento_porcentaje": 0.09,
                "margen_estimado": 90000,
                "margen_porcentaje": 0.23,
                "tiempo_venta": "Muy Rápido (<2 días)",
                "liquidez": "alta"
            },
            "recomendacion": {
                "decision": "COMPRAR",
                "confianza": 0.92,
                "razonamiento": "Precio excelente para reventa. El iPhone 13 tiene altísima rotación. Margen proyectado superior al 20%.",
                "precio_max_oferta": 360000,
                "acciones": ["Ofertar $350.000 efectivo", "Pedir video de condición de batería"]
            },
            "alertas": [], # Se llena dinámicamente si es fallback
            "calidad_imagen": {"texto_legible": True, "info_completa": True, "confianza_extraccion": 0.98}
        }
