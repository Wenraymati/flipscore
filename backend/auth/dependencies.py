from fastapi import Depends, HTTPException, Header
from backend.auth.supabase_client import verify_token, get_user_profile

async def get_current_user(authorization: str = Header(None)):
    """Dependency para obtener usuario autenticado."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token inválido o ausente")
    
    token = authorization.replace("Bearer ", "")
    user = verify_token(token)
    
    if not user:
        raise HTTPException(401, "No autenticado o sesión expirada")
    
    profile = get_user_profile(user.id)
    # Return dict merging user auth data and profile data
    return {**user.__dict__, "profile": profile or {}}

async def check_evaluation_limit(user = Depends(get_current_user)):
    """Verifica que usuario no haya excedido límite de plan."""
    profile = user.get("profile", {})
    plan = profile.get("plan", "free")
    evaluations_this_month = profile.get("evaluations_this_month", 0)
    
    limits = {"free": 10, "starter": 100, "pro": 500, "business": 99999}
    limit = limits.get(plan, 10) # Default to free limit
    
    if evaluations_this_month >= limit:
        raise HTTPException(
            403, 
            f"Límite de evaluaciones alcanzado ({limit}/mes). Upgrade tu plan."
        )
    
    return user
