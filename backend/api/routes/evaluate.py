from fastapi import APIRouter, HTTPException
from backend.models.schemas import EvaluateRequest, EvaluateResponse
from backend.services.evaluator import EvaluatorService

router = APIRouter(prefix="/api", tags=["evaluate"])

evaluator = EvaluatorService()

@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_deal(request: EvaluateRequest):
    """
    Evalúa una oportunidad de compra para reventa.
    
    - **producto**: Nombre/descripción del producto
    - **precio_publicado**: Precio en CLP
    - **descripcion**: Descripción del vendedor (opcional)
    - **categoria**: Categoría del producto (auto-detecta si vacío)
    """
    try:
        result = await evaluator.evaluate(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "resale-evaluator"}
