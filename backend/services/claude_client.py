import anthropic
import json
import logging
from typing import Optional, Dict
from backend.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres un experto evaluador de oportunidades de reventa de productos usados en Chile.
Tu trabajo es analizar posibles compras y proporcionar una evaluación objetiva y estructurada.

## CONTEXTO DE MERCADO CHILENO
- Moneda: Pesos chilenos (CLP)
- Temporada actual: {temporada}
- Fecha: {fecha_actual}

## BASE DE PRECIOS DE REFERENCIA
{precios_referencia}

## CRITERIOS DE EVALUACIÓN (ponderación)

### 1. DESCUENTO REAL (30%)
- Comparar precio publicado vs precio de referencia
- < 40% descuento → score bajo (1-4)
- 40-50% → score medio (5-6)
- 50-60% → score alto (7-8)
- > 60% → score muy alto (9-10), verificar no sea estafa

### 2. LIQUIDEZ DE CATEGORÍA (25%)
- Alta (Celulares, Consolas): score 8-10
- Media (Herramientas, Computación): score 5-7
- Baja (Fitness, Muebles): score 3-5

### 3. CONDICIÓN DEL PRODUCTO (20%)
- Evaluar descripción del vendedor
- Nuevo/Sellado: 10
- Excelente: 8
- Bueno: 6
- Regular: 4

### 4. SEÑALES DEL VENDEDOR (15%)
Positivas (+score):
- Urgencia legítima (mudanza, viaje, deuda)
- Fotos propias detalladas
- Incluye accesorios originales
- Factura disponible

Negativas (-score):
- Sin fotos reales
- Precio muy bajo (posible estafa)
- Múltiples unidades iguales
- "Funciona perfecto" sin detalles

### 5. MARGEN POTENCIAL (10%)
- Margen < 15%: score 1-3
- Margen 15-25%: score 4-6
- Margen 25-40%: score 7-8
- Margen > 40%: score 9-10

## REGLAS ABSOLUTAS
1. Si detectas señales claras de estafa → decision: "ALERTA_RIESGO"
2. Nunca recomendar COMPRAR si descuento < 35%
3. Ser conservador en estimaciones de venta

## FORMATO DE RESPUESTA
Responde ÚNICAMENTE con JSON válido (sin markdown, sin texto adicional):
{{
  "clasificacion": {{
    "categoria": "string (Celulares|Consolas|Herramientas|Computación|Fitness|Bicicletas|Otro)",
    "producto_identificado": "string",
    "condicion_inferida": "string (Nuevo|Excelente|Bueno|Regular|Malo)",
    "confianza": float
  }},
  "analisis_precio": {{
    "precio_publicado": int,
    "precio_referencia_nuevo": int,
    "precio_referencia_usado": int,
    "descuento_vs_nuevo": float,
    "descuento_vs_usado": float,
    "precio_max_compra": int
  }},
  "evaluacion": {{
    "score_descuento": float,
    "score_liquidez": float,
    "score_condicion": float,
    "score_vendedor": float,
    "score_margen": float,
    "score_total": float
  }},
  "proyeccion": {{
    "precio_venta_esperado": int,
    "margen_bruto": int,
    "margen_porcentaje": float,
    "tiempo_venta_dias": "string",
    "liquidez": "string"
  }},
  "senales_positivas": ["string"],
  "senales_negativas": ["string"],
  "alertas": ["string"],
  "recomendacion": {{
    "decision": "string (COMPRAR_YA|COMPRAR|NEGOCIAR|PASAR|ALERTA_RIESGO)",
    "confianza": float,
    "razonamiento": "string",
    "acciones_sugeridas": ["string"]
  }}
}}
"""

class ClaudeClient:
    """Cliente para interactuar con Claude API."""
    
    def __init__(self):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens
    
    def evaluate_deal(
        self,
        producto: str,
        precio: int,
        descripcion: Optional[str],
        precios_referencia: Dict
    ) -> Dict:
        """
        Evalúa una oportunidad de compra.
        
        Args:
            producto: Texto del producto
            precio: Precio publicado en CLP
            descripcion: Descripción del vendedor
            precios_referencia: Dict con precios de referencia
            
        Returns:
            Dict con evaluación estructurada
        """
        from datetime import datetime
        
        # Construir prompts
        system = SYSTEM_PROMPT.format(
            temporada=self._get_temporada(),
            fecha_actual=datetime.now().strftime("%Y-%m-%d"),
            precios_referencia=json.dumps(precios_referencia, indent=2, ensure_ascii=False)
        )
        
        user_prompt = f"""
Evalúa esta oportunidad de compra para reventa:

**Producto:** {producto}
**Precio publicado:** ${precio:,} CLP
**Descripción:** {descripcion or "No proporcionada"}

Proporciona tu evaluación en formato JSON.
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": user_prompt}],
                system=system
            )
            
            # Extraer y parsear JSON
            content = response.content[0].text
            result = self._parse_json(content)
            
            return result
            
        except anthropic.APIError as e:
            logger.error(f"Error de API Claude: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta: {e}")
            raise ValueError(f"Respuesta de IA inválida: {e}")
    
    def _parse_json(self, text: str) -> dict:
        """Extrae JSON de la respuesta."""
        # Limpiar posibles markers de código
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        # Buscar JSON
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start == -1 or end == 0:
            raise json.JSONDecodeError("No JSON found", text, 0)
        
        return json.loads(text[start:end])
    
    def _get_temporada(self) -> str:
        """Determina temporada actual para Chile."""
        from datetime import datetime
        month = datetime.now().month
        
        if month in [12, 1, 2]:
            return "Verano - Alta oportunidad (deudas post-navidad, propósitos abandonados)"
        elif month in [3, 4, 5]:
            return "Otoño - Temporada regular"
        elif month in [6, 7, 8]:
            return "Invierno - Temporada regular"
        else:
            return "Primavera - Pre-cybers (cautela con precios inflados)"
