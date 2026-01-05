from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    """Configuración de la aplicación."""
    
    # API Keys
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
    # Models
    claude_model: str = "claude-sonnet-4-20250514"
    groq_text_model: str = "openai/gpt-oss-120b"
    groq_vision_model: str = "llama-3.2-11b-vision-preview"
    gemini_model: str = "models/gemini-flash-latest"
    
    # Supabase
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    
    claude_max_tokens: int = 2000
    
    # App Config
    app_name: str = "Resale Evaluator"
    debug: bool = False
    mock_mode: bool = False
    
    # Precios
    reference_prices_path: str = "backend/data/reference_prices.json"
    ai_provider: str = "groq" # Options: gemini, groq
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()
