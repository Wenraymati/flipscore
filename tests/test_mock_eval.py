import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.evaluator import EvaluatorService
from backend.models.schemas import EvaluateRequest, Categoria

# Mock Response from Claude
MOCK_CLAUDE_RESPONSE = {
  "clasificacion": {
    "categoria": "Celulares",
    "producto_identificado": "iPhone 13 128GB",
    "condicion_inferida": "Excelente",
    "confianza": 0.95
  },
  "analisis_precio": {
    "precio_publicado": 350000,
    "precio_referencia_nuevo": 650000,
    "precio_referencia_usado": 425000,
    "descuento_vs_nuevo": 0.46,
    "descuento_vs_usado": 0.17,
    "precio_max_compra": 325000
  },
  "evaluacion": {
    "score_descuento": 6.0,
    "score_liquidez": 9.0,
    "score_condicion": 8.0,
    "score_vendedor": 7.0,
    "score_margen": 8.0,
    "score_total": 7.8
  },
  "proyeccion": {
    "precio_venta_esperado": 450000,
    "margen_bruto": 100000,
    "margen_porcentaje": 0.28,
    "tiempo_venta_dias": "2-5 días",
    "liquidez": "alta"
  },
  "senales_positivas": ["Precio competitivo", "Producto alta liquidez"],
  "senales_negativas": [],
  "alertas": [],
  "recomendacion": {
    "decision": "COMPRAR",
    "confianza": 0.9,
    "razonamiento": "Buen margen y alta rotación.",
    "acciones_sugeridas": ["Ofertar 320.000", "Revisar batería"]
  }
}

@pytest.mark.asyncio
async def test_evaluate_deal_mock():
    # Setup Mocks
    mock_claude_client = MagicMock()
    mock_claude_client.evaluate_deal.return_value = MOCK_CLAUDE_RESPONSE
    
    with patch('backend.services.evaluator.ClaudeClient', return_value=mock_claude_client):
        service = EvaluatorService()
        
        # Test Input
        request = EvaluateRequest(
            producto="iPhone 13 128GB",
            precio_publicado=350000,
            descripcion="Como nuevo, batería 90%",
            categoria=Categoria.CELULARES
        )
        
        # Execute
        response = await service.evaluate(request)
        
        # Verify
        assert response.score_display == "7.8/10"
        assert "COMPRAR" in response.decision_display
        assert response.clasificacion.categoria == Categoria.CELULARES
        assert response.analisis_precio.precio_publicado == 350000
        
        print("\n✅ Test Passed: Evaluator logic handles Claude response correctly.")
