from groq import Groq
import json
import logging
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
- Fecha: {fecha_actual}
- Precios Referencia (DB Interna): {precios_referencia}
- Datos Mercado En Vivo (MercadoLibre): {market_data}


Salida requerida: JSON válido estrictamente.
IMPORTANTE: El campo "decision" DEBE ser uno de estos valores exactos:
["COMPRAR_YA", "COMPRAR", "NEGOCIAR", "PASAR", "ALERTA_RIESGO"]
"""

class GroqClient:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.groq_api_key
        self.model = settings.groq_text_model
        self.client = None
        if self.api_key:
            self.client = Groq(api_key=self.api_key)

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
        precios_referencia: Dict,
        market_data: Optional[Dict] = None
    ) -> Dict:
        """
        Evalúa una oportunidad de compra usando Groq.
        """
        settings = get_settings()
        
        # Fallback Mock si no hay cliente (aunque user puso key)
        if not self.client:
            logger.warning("Groq Client no inicializado (falta key?)")
            return self._get_mock_response(producto, precio)

        from datetime import datetime
        
        system_content = SYSTEM_PROMPT.format(
            temporada=self._get_temporada(),
            fecha_actual=datetime.now().strftime("%Y-%m-%d"),
            precios_referencia=json.dumps(precios_referencia, indent=2, ensure_ascii=False),
            market_data=json.dumps(market_data or {}, indent=2, ensure_ascii=False)
        )
        
        user_prompt = f"""
Evalúa esta oportunidad de compra para reventa:

**Producto:** {producto}
**Precio publicado:** ${precio:,} CLP
**Descripción:** {descripcion or "No proporcionada"}

Proporciona tu evaluación en formato JSON con la siguiente estructura (la misma que usaba Claude):
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
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1, # Más determinista para JSON
                response_format={"type": "json_object"}, # Groq soporta json mode en Llama3, probemos con openai/gpt-oss
                stream=False
            )
            
            content = completion.choices[0].message.content
            return self._parse_json(content)
            
        except Exception as e:
            logger.error(f"Error de API Groq: {e}")
            # Fallback error response
            raise ValueError(f"Error llamando a Groq: {e}")

    def _parse_json(self, text: str) -> dict:
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = text[start:end]
                return json.loads(json_str)
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            raise ValueError("Respuesta no es JSON válido")

    def _get_mock_response(self, producto: str, precio: int) -> dict:
        return {
            "recomendacion": {
                "decision": "ERROR_CONFIG",
                "razonamiento": "No se pudo conectar con Groq API.",
                "acciones_sugeridas": ["Verificar API Key"]
            },
            "evaluacion": {"score_total": 0},
            "analisis_precio": {"precio_publicado": precio},
            "proyeccion": {},
            "alertas": ["Error de configuración API"]
        }
