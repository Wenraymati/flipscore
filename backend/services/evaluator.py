import json
import logging
from pathlib import Path
from typing import Optional

from typing import Optional
from backend.services.price_client import PriceClient
from backend.config import get_settings
from backend.services.gemini_client import GeminiClient
from backend.services.groq_client import GroqClient
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
        settings = get_settings()
        if settings.ai_provider == "groq":
            self.client = GroqClient()
            logger.info("Using AI Provider: Groq (Llama 3.3)")
        else:
            self.client = GeminiClient()
            logger.info("Using AI Provider: Gemini")
            
        self.price_client = PriceClient()
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
        # 1. Obtener datos de mercado en tiempo real (si es posible)
        market_data = await self.price_client.fetch_market_data(request.producto)
        
        # 2. Llamar a IA con contexto enriquecido
        ai_result = self.client.evaluate_deal(
            producto=request.producto,
            precio=request.precio_publicado,
            descripcion=request.descripcion,
            precios_referencia=self.reference_prices,
            market_data=market_data
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
        
        try:
            # Intenta conversión directa o fuzzy
            try:
                decision_enum = Recomendacion(decision)
            except ValueError:
                decision_enum = Recomendacion.from_fuzzy(decision)
                logger.info(f"Fuzzy mapped '{decision}' to {decision_enum}")

        except Exception as e:
            logger.warning(f"Error mapeando decisión '{decision}': {e}. Fallback NEGOCIAR.")
            decision_enum = Recomendacion.NEGOCIAR

        return EvaluateResponse(
            clasificacion=Clasificacion(
                categoria=clasif.get("categoria") or "Otro",
                producto_identificado=clasif.get("producto_identificado") or "",
                condicion_inferida=clasif.get("condicion_inferida") or "Bueno",
                confianza=clasif.get("confianza") or 0.5
            ),
            analisis_precio=AnalisisPrecio(
                precio_publicado=precio.get("precio_publicado") or 0,
                precio_referencia_nuevo=precio.get("precio_referencia_nuevo") or 0,
                precio_referencia_usado=precio.get("precio_referencia_usado") or 0,
                descuento_vs_nuevo=precio.get("descuento_vs_nuevo") or 0.0,
                descuento_vs_usado=precio.get("descuento_vs_usado") or 0.0,
                precio_max_compra=precio.get("precio_max_compra") or 0
            ),
            evaluacion=Evaluacion(
                score_descuento=eval_data.get("score_descuento") or 0.0,
                score_liquidez=eval_data.get("score_liquidez") or 0.0,
                score_condicion=eval_data.get("score_condicion") or 0.0,
                score_vendedor=eval_data.get("score_vendedor") or 0.0,
                score_margen=eval_data.get("score_margen") or 0.0,
                score_total=score
            ),
            proyeccion=Proyeccion(
                precio_venta_esperado=proy.get("precio_venta_esperado") or 0,
                margen_bruto=margen,
                margen_porcentaje=margen_pct,
                tiempo_venta_dias=proy.get("tiempo_venta_dias") or "N/A",
                liquidez=proy.get("liquidez") or "media"
            ),
            senales_positivas=ai_result.get("senales_positivas", []),
            senales_negativas=ai_result.get("senales_negativas", []),
            alertas=ai_result.get("alertas", []),
            recomendacion=RecomendacionDetalle(
                decision=decision_enum,
                confianza=rec.get("confianza") or 0.5,
                razonamiento=rec.get("razonamiento") or "",
                acciones_sugeridas=rec.get("acciones_sugeridas") or []
            ),
            # Displays para UI
            score_display=f"{score:.1f}/10",
            decision_display=f"{decision_icons.get(decision, '❓')} {decision.replace('_', ' ')}",
            margen_display=f"${margen:,} ({margen_pct*100:.0f}%)"
        )
