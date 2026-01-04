import json
import logging
from pathlib import Path
from typing import Optional

from backend.config import get_settings
from backend.services.gemini_client import GeminiClient
from backend.models.schemas import (
    EvaluateRequest, 
    EvaluateResponse,
    Clasificacion,
    AnalisisPrecio,
    Evaluacion,
    Proyeccion,
    RecomendacionDetalle,
    Recomendacion
)

logger = logging.getLogger(__name__)

class EvaluatorService:
    """Servicio principal de evaluación de deals."""
    
    def __init__(self):
        self.client = GeminiClient()
        self.reference_prices = self._load_reference_prices()
    
    def _load_reference_prices(self) -> dict:
        """Carga precios de referencia desde JSON."""
        settings = get_settings()
        # Ensure path is relative to the root project or absolute
        path = Path(settings.reference_prices_path)
        
        # Try to find the file relative to where main.py runs or the shared workspace
        if not path.exists():
            # Fallback to absolute path check if needed or different relative path
            # Assuming running from 'resale-evaluator' root
            path = Path("resale-evaluator") / settings.reference_prices_path
            if not path.exists():
                 # Last resort: try checking in current dir
                 path = Path(settings.reference_prices_path)

        if not path.exists():
            logger.warning(f"Archivo de precios no encontrado: {path}")
            return {"categorias": {}}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando precios de referencia: {e}")
            return {"categorias": {}}
    
    async def evaluate(self, request: EvaluateRequest) -> EvaluateResponse:
        """
        Evalúa una oportunidad de compra.
        
        Args:
            request: Datos del deal a evaluar
            
        Returns:
            EvaluateResponse con evaluación completa
        """
        # Llamar a Claude para evaluación
        ai_result = self.client.evaluate_deal(
            producto=request.producto,
            precio=request.precio_publicado,
            descripcion=request.descripcion,
            precios_referencia=self.reference_prices
        )
        
        # Transformar a response estructurado
        return self._build_response(ai_result)
    
    def _build_response(self, ai_result: dict) -> EvaluateResponse:
        """Construye EvaluateResponse desde resultado de IA."""
        
        # Extraer secciones
        clasif = ai_result.get("clasificacion", {})
        precio = ai_result.get("analisis_precio", {})
        eval_data = ai_result.get("evaluacion", {})
        proy = ai_result.get("proyeccion", {})
        rec = ai_result.get("recomendacion", {})
        
        # Construir displays para UI
        score = eval_data.get("score_total", 0)
        decision = rec.get("decision", "PASAR")
        margen = proy.get("margen_bruto", 0)
        margen_pct = proy.get("margen_porcentaje", 0)
        
        decision_icons = {
            "COMPRAR_YA": "🔥",
            "COMPRAR": "✅",
            "NEGOCIAR": "⚠️",
            "PASAR": "❌",
            "ALERTA_RIESGO": "🚨"
        }
        
        return EvaluateResponse(
            clasificacion=Clasificacion(
                categoria=clasif.get("categoria", "Otro"),
                producto_identificado=clasif.get("producto_identificado", ""),
                condicion_inferida=clasif.get("condicion_inferida", "Bueno"),
                confianza=clasif.get("confianza", 0.5)
            ),
            analisis_precio=AnalisisPrecio(
                precio_publicado=precio.get("precio_publicado", 0),
                precio_referencia_nuevo=precio.get("precio_referencia_nuevo", 0),
                precio_referencia_usado=precio.get("precio_referencia_usado", 0),
                descuento_vs_nuevo=precio.get("descuento_vs_nuevo", 0),
                descuento_vs_usado=precio.get("descuento_vs_usado", 0),
                precio_max_compra=precio.get("precio_max_compra", 0)
            ),
            evaluacion=Evaluacion(
                score_descuento=eval_data.get("score_descuento", 0),
                score_liquidez=eval_data.get("score_liquidez", 0),
                score_condicion=eval_data.get("score_condicion", 0),
                score_vendedor=eval_data.get("score_vendedor", 0),
                score_margen=eval_data.get("score_margen", 0),
                score_total=score
            ),
            proyeccion=Proyeccion(
                precio_venta_esperado=proy.get("precio_venta_esperado", 0),
                margen_bruto=margen,
                margen_porcentaje=margen_pct,
                tiempo_venta_dias=proy.get("tiempo_venta_dias", "N/A"),
                liquidez=proy.get("liquidez", "media")
            ),
            senales_positivas=ai_result.get("senales_positivas", []),
            senales_negativas=ai_result.get("senales_negativas", []),
            alertas=ai_result.get("alertas", []),
            recomendacion=RecomendacionDetalle(
                decision=Recomendacion(decision),
                confianza=rec.get("confianza", 0.5),
                razonamiento=rec.get("razonamiento", ""),
                acciones_sugeridas=rec.get("acciones_sugeridas", [])
            ),
            # Displays para UI
            score_display=f"{score:.1f}/10",
            decision_display=f"{decision_icons.get(decision, '❓')} {decision.replace('_', ' ')}",
            margen_display=f"${margen:,} ({margen_pct*100:.0f}%)"
        )
