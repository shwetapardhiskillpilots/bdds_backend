from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_db
from models import AuthToken
import time

API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# ── Token Cache (avoids DB round-trip on every request) ──
_token_cache: dict = {}  # token_key -> {"user": AuthUser, "ts": time.time()}
TOKEN_CACHE_TTL = 300  # 5 minutes

async def get_current_user(token: str = Depends(api_key_header), db: AsyncSession = Depends(get_db)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )
    
    if token.startswith("Token "):
        token_key = token[6:]
    elif token.startswith("Bearer "):
        token_key = token[7:]
    else:
        token_key = token

    # Check cache first
    cached = _token_cache.get(token_key)
    if cached and (time.time() - cached["ts"]) < TOKEN_CACHE_TTL:
        return cached["user"]

    # Cache miss - hit DB
    result = await db.execute(select(AuthToken).options(selectinload(AuthToken.user)).where(AuthToken.key == token_key))
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    user = db_token.user
    # Cache the result
    _token_cache[token_key] = {"user": user, "ts": time.time()}
    return user
