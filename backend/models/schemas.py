from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class Categoria(str, Enum):
    CELULARES = "Celulares"
    CONSOLAS = "Consolas"
    HERRAMIENTAS = "Herramientas"
    COMPUTACION = "Computación"
    FITNESS = "Fitness"
    BICICLETAS = "Bicicletas"
    MOTOCICLETAS = "Motocicletas"
    OTRO = "Otro"

class Recomendacion(str, Enum):
    COMPRAR_YA = "COMPRAR_YA"
    COMPRAR = "COMPRAR"
    NEGOCIAR = "NEGOCIAR"
    PASAR = "PASAR"
    ALERTA_RIESGO = "ALERTA_RIESGO"

# Request
class EvaluateRequest(BaseModel):
    """Input del usuario para evaluar un deal."""
    producto: str = Field(..., min_length=3, max_length=200, 
                          description="Nombre/descripción del producto")
    precio_publicado: int = Field(..., gt=0, le=50000000,
                                   description="Precio en CLP")
    descripcion: Optional[str] = Field(None, max_length=1000,
                                        description="Descripción del vendedor")
    categoria: Optional[Categoria] = Field(None,
                                            description="Categoría (auto-detecta si vacío)")
    url: Optional[str] = Field(None, description="URL de la publicación")

# Response
class Clasificacion(BaseModel):
    categoria: Categoria
    producto_identificado: str
    condicion_inferida: str
    confianza: float = Field(ge=0, le=1)

class AnalisisPrecio(BaseModel):
    precio_publicado: int
    precio_referencia_nuevo: int
    precio_referencia_usado: int
    descuento_vs_nuevo: float
    descuento_vs_usado: float
    precio_max_compra: int

class Evaluacion(BaseModel):
    score_descuento: float = Field(ge=0, le=10)
    score_liquidez: float = Field(ge=0, le=10)
    score_condicion: float = Field(ge=0, le=10)
    score_vendedor: float = Field(ge=0, le=10)
    score_margen: float = Field(ge=0, le=10)
    score_total: float = Field(ge=0, le=10)

class Proyeccion(BaseModel):
    precio_venta_esperado: int
    margen_bruto: int
    margen_porcentaje: float
    tiempo_venta_dias: str
    liquidez: str

class RecomendacionDetalle(BaseModel):
    decision: Recomendacion
    confianza: float = Field(ge=0, le=1)
    razonamiento: str
    acciones_sugeridas: List[str]

class EvaluateResponse(BaseModel):
    """Respuesta completa de evaluación."""
    clasificacion: Clasificacion
    analisis_precio: AnalisisPrecio
    evaluacion: Evaluacion
    proyeccion: Proyeccion
    senales_positivas: List[str]
    senales_negativas: List[str]
    alertas: List[str]
    recomendacion: RecomendacionDetalle
    
    # Resumen para UI
    score_display: str  # "8.2/10"
    decision_display: str  # "✅ COMPRAR YA"
    margen_display: str  # "$95,000 (34%)"

# --- Image Evaluation Schemas ---

class ImageExtraccion(BaseModel):
    producto: str
    precio: int
    descripcion: Optional[str] = None
    ubicacion: Optional[str] = None
    estado: Optional[str] = None
    senales_detectadas: List[str] = []

class ImageCalidad(BaseModel):
    texto_legible: bool
    info_completa: bool
    confianza_extraccion: float

class ImageEvaluateResponse(BaseModel):
    success: bool
    extraccion: ImageExtraccion
    evaluacion: Evaluacion
    recomendacion: RecomendacionDetalle
    alertas: List[str] = []
    calidad_imagen: ImageCalidad
    
    # UI Displays
    score_display: str
    decision_display: str
    margen_display: str

