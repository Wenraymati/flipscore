from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import ImageEvaluateResponse, Evaluacion, RecomendacionDetalle, ImageExtraccion, ImageCalidad
from backend.services.image_processor import ImageProcessor
from backend.services.vision_client import VisionClient
from backend.services.evaluator import EvaluatorService # For reusing reference prices
import logging

router = APIRouter(prefix="/api", tags=["image-evaluate"])
logger = logging.getLogger(__name__)

# Initialize dependencies
processor = ImageProcessor()
vision = VisionClient()
evaluator_service = EvaluatorService() # To access reference_prices

@router.post("/evaluate-image", response_model=ImageEvaluateResponse)
async def evaluate_image(file: UploadFile = File(...)):
    """
    Evalúa una oportunidad desde un screenshot de Marketplace.
    """
    try:
        # 1. Read bytes
        contents = await file.read()
        
        # 2. Validate & Preprocess
        if not processor.validate_marketplace_screenshot(contents):
            raise HTTPException(status_code=400, detail="Imagen no válida o formato incorrecto")
        
        optimized_image = processor.preprocess_image(contents)
        
        # 3. Call Vision API
        # Reusing reference prices from the main evaluator service
        ref_prices = evaluator_service.reference_prices
        
        result_dict = vision.extract_and_evaluate(optimized_image, ref_prices)
        
        # 4. Map to Schema (Simple mapping as the prompt structure matches schema)
        # Add UI displays manually
        
        eval_data = result_dict.get("evaluacion", {})
        rec_data = result_dict.get("recomendacion", {})
        proj_data = result_dict.get("proyeccion", {}) # Might not be in schema, but useful if we add it later
        
        score = eval_data.get("score_total", 0)
        decision = rec_data.get("decision", "PASAR")
        margen = eval_data.get("margen_estimado", 0)
        margen_pct = eval_data.get("margen_porcentaje", 0)
        
        decision_icons = {
            "COMPRAR_YA": "🔥",
            "COMPRAR": "✅",
            "NEGOCIAR": "⚠️",
            "PASAR": "❌",
            "ALERTA_RIESGO": "🚨",
            "ALERTA": "🚨"
        }
        
        response = ImageEvaluateResponse(
            success=True,
            extraccion=ImageExtraccion(**result_dict.get("extraccion", {})),
            evaluacion=Evaluacion(
                score_descuento=0, # These detailed scores might be missing in simplified vision response, default 0
                score_liquidez=0,
                score_condicion=0,
                score_vendedor=0,
                score_margen=0,
                score_total=score
            ),
            recomendacion=RecomendacionDetalle(
                decision=decision,
                confianza=rec_data.get("confianza", 0),
                razonamiento=rec_data.get("razonamiento", ""),
                acciones_sugeridas=rec_data.get("acciones", [])
            ),
            alertas=result_dict.get("alertas", []),
            calidad_imagen=ImageCalidad(**result_dict.get("calidad_imagen", {})),
            
            score_display=f"{score:.1f}/10",
            decision_display=f"{decision_icons.get(decision, '❓')} {decision.replace('_', ' ')}",
            margen_display=f"${margen:,} ({margen_pct*100:.0f}%)"
        )
        
        return response
        
    except ValueError as ve:
         raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail="Error interno procesando la imagen")
