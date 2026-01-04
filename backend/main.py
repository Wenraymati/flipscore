from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import evaluate, image_evaluate
from backend.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API para evaluar oportunidades de reventa con IA",
    version="0.1.0"
)

# CORS para Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(evaluate.router)
app.include_router(image_evaluate.router)


@app.get("/")
async def root():
    return {
        "message": "Resale Evaluator API",
        "docs": "/docs",
        "health": "/api/health"
    }
