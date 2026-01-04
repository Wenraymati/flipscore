from supabase import create_client, Client
from backend.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    if settings.supabase_url and settings.supabase_anon_key:
        supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key
        )
    else:
        supabase = None
        logger.warning("Supabase credentials not found.")
except Exception as e:
    supabase = None
    logger.error(f"Error initializing Supabase: {e}")

def verify_token(token: str) -> dict | None:
    """Verifica JWT de Supabase y retorna user data."""
    if not supabase: return None
    try:
        user = supabase.auth.get_user(token)
        return user.user if user else None
    except Exception:
        return None

def get_user_profile(user_id: str) -> dict | None:
    """Obtiene perfil de usuario con plan y uso."""
    if not supabase: return None
    try:
        result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        return result.data if result.data else None
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return None
