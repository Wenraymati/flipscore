import google.generativeai as genai
import json
import logging
import typing_extensions as typing
from typing import Dict, Optional, Any
from backend.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres un experto evaluador de oportunidades de reventa en Chile.
Tu misión es analizar productos y predecir su rentabilidad y liquidez.
Usa los precios de referencia proporcionados para calcular márgenes.

Contexto actual:
- Temporada: {temporada}
- Fecha: {fecha_actual}
- Precios Referencia: {precios_referencia}

Salida requerida: JSON válido estrictamente.
"""

class GeminiClient:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    def _get_temporada(self) -> str:
        from datetime import datetime
        mes = datetime.now().month
        if mes in [12, 1, 2]: return "Verano (Alta demanda productos aire libre/vacaciones)"
        if mes in [3, 4, 5]: return "Otoño (Vuelta a clases/trabajo)"
        if mes in [6, 7, 8]: return "Invierno (Alta demanda calefacción/indoor)"
        return "Primavera (Prep. aire libre)"

    def evaluate_deal(
        self,
        producto: str,
        precio: int,
        descripcion: Optional[str],
        precios_referencia: Dict
    ) -> Dict:
        """
        Evalúa una oportunidad de compra usando Gemini.
        """
        if not self.model:
            logger.warning("Gemini Client no inicializado")
            return self._get_mock_response(producto, precio)

        from datetime import datetime
        
        system_content = SYSTEM_PROMPT.format(
            temporada=self._get_temporada(),
            fecha_actual=datetime.now().strftime("%Y-%m-%d"),
            precios_referencia=json.dumps(precios_referencia, indent=2, ensure_ascii=False)
        )
        
        user_prompt = f"""
{system_content}

Evalúa esta oportunidad de compra para reventa:

**Producto:** {producto}
**Precio publicado:** ${precio:,} CLP
**Descripción:** {descripcion or "No proporcionada"}

Proporciona tu evaluación en formato JSON con la siguiente estructura:
{{
  "clasificacion": {{ "categoria": "", "producto_identificado": "", "condicion_inferida": "", "confianza": 0.0 }},
  "analisis_precio": {{ "precio_publicado": 0, "precio_referencia_nuevo": 0, "precio_referencia_usado": 0, "descuento_vs_nuevo": 0.0, "descuento_vs_usado": 0.0, "precio_max_compra": 0 }},
  "evaluacion": {{ "score_descuento": 0.0, "score_liquidez": 0.0, "score_condicion": 0.0, "score_vendedor": 0.0, "score_margen": 0.0, "score_total": 0.0 }},
  "proyeccion": {{ "precio_venta_esperado": 0, "margen_bruto": 0, "margen_porcentaje": 0.0, "tiempo_venta_dias": "", "liquidez": "" }},
  "senales_positivas": [],
  "senales_negativas": [],
  "alertas": [],
  "recomendacion": {{ "decision": "", "confianza": 0.0, "razonamiento": "", "acciones_sugeridas": [] }}
}}
"""
        
        try:
            # Gemini supports JSON response via generation config
            response = self.model.generate_content(
                user_prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            logger.error(f"Error de API Gemini: {e}")
            raise ValueError(f"Error llamando a Gemini: {e}")

    def _get_mock_response(self, producto: str, precio: int) -> dict:
        return {
            "recomendacion": {
                "decision": "ERROR_CONFIG",
                "razonamiento": "No se pudo conectar con Gemini API.",
                "acciones_sugeridas": ["Verificar API Key"]
            },
            "evaluacion": {"score_total": 0},
            "analisis_precio": {"precio_publicado": precio},
            "proyeccion": {},
            "alertas": ["Error de configuración API"]
        }
