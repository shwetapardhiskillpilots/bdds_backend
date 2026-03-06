from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from database import get_db
from models import (
    AuthUser, Nlogines_creations, N_location, N_juridiction, N_incident, 
    N_weight, N_explosive, N_assused, N_post, N_degignation, N_ditection, 
    N_dispose, N_dalam
)
from auth import get_current_user, pwd_context
from schemas import UserProfileResponse, MasterItemResponse, MasterItemBase, UserPasswordReset

router = APIRouter(prefix="/dashboard", tags=["admin"])

# Mapping of table names to their SQLAlchemy models
MASTER_MODELS = {
    "location": N_location,
    "jurisdiction": N_juridiction,
    "incident": N_incident,
    "weight": N_weight,
    "explosive": N_explosive,
    "accused": N_assused,
    "post": N_post,
    "designation": N_degignation,
    "detection": N_ditection,
    "dispose": N_dispose,
    "dalam": N_dalam
}

# --- Common Helper for Master CRUD ---
def get_model_attr(model, attr_name):
    # Map 'name' to the specific column name used in the model
    mapping = {
        N_location: "l_location",
        N_juridiction: "l_juridiction",
        N_incident: "i_incident",
        N_weight: "w_weight",
        N_explosive: "e_explosive",
        N_assused: "a_assused",
        N_post: "p_post",
        N_degignation: "d_designation",
        N_ditection: "d_ditection",
        N_dispose: "d_dispose",
        N_dalam: "d_dalam"
    }
    return mapping.get(model, "name")

# --- Master Data CRUD ---

@router.get("/master/{table}", response_model=List[Dict[str, Any]])
async def list_master_data(
    table: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    if table not in MASTER_MODELS:
        raise HTTPException(status_code=404, detail="Table not found")
    
    model = MASTER_MODELS[table]
    result = await db.execute(select(model))
    items = result.scalars().all()
    attr = get_model_attr(model, "name")
    
    return [{"id": item.id, "name": getattr(item, attr)} for item in items]

@router.post("/master/{table}", status_code=status.HTTP_201_CREATED)
async def create_master_data(
    table: str,
    item: MasterItemBase,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    if table not in MASTER_MODELS:
        raise HTTPException(status_code=404, detail="Table not found")
    
    model = MASTER_MODELS[table]
    attr = get_model_attr(model, "name")
    new_item = model(**{attr: item.name})
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    return {"id": new_item.id, "name": getattr(new_item, attr)}

@router.delete("/master/{table}/{id}")
async def delete_master_data(
    table: str,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    if table not in MASTER_MODELS:
        raise HTTPException(status_code=404, detail="Table not found")
    
    model = MASTER_MODELS[table]
    result = await db.execute(select(model).filter(model.id == id))
    db_item = result.scalar_one_or_none()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.delete(db_item)
    await db.commit()
    return {"message": "Deleted successfully"}

# --- User Management ---

@router.get("/users", response_model=List[UserProfileResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.execute(select(AuthUser))
    users = result.scalars().all()
    res = []
    for user in users:
        # Try to find associated login_creation data
        lc_result = await db.execute(select(Nlogines_creations).filter(Nlogines_creations.user_id == user.id))
        lc = lc_result.scalar_one_or_none()
        res.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "is_active": bool(user.is_active),
            "is_superuser": bool(user.is_superuser),
            "designation": lc.l_designation if lc else "N/A",
            "post": "N/A" # Simplified for now
        })
    return res

@router.patch("/users/{id}/toggle-active")
async def toggle_user_active(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.execute(select(AuthUser).filter(AuthUser.id == id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = 0 if user.is_active else 1
    await db.commit()
    return {"id": user.id, "is_active": bool(user.is_active)}

@router.post("/users/{id}/reset-password")
async def reset_user_password(
    id: int,
    data: UserPasswordReset,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.execute(select(AuthUser).filter(AuthUser.id == id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Bug-web-05: Hash the password for secure login
    user.password = pwd_context.hash(data.new_password)
    await db.commit()
    return {"message": "Password reset successfully"}
