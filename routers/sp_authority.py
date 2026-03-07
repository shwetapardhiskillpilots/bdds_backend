from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from database import get_db
from models import Nsp_authourity, AuthUser
from datetime import datetime
from auth import get_current_user, pwd_context
from schemas import SPAuthorityCreate, SPAuthorityResponse

router = APIRouter(prefix="/sp-authority", tags=["sp-authority"])

@router.get("/", response_model=List[SPAuthorityResponse])
async def list_sp_authorities(
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """List all registered SP authorities."""
    result = await db.execute(select(Nsp_authourity))
    authorities = result.scalars().all()
    return authorities

@router.post("/", response_model=SPAuthorityResponse, status_code=status.HTTP_201_CREATED)
async def create_sp_authority(
    data: SPAuthorityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Create a new SP authority (Credential)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can create SP authority credentials")
    
    # Check if email already exists
    existing = await db.execute(select(Nsp_authourity).where(Nsp_authourity.s_email == data.s_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Authority with this email already exists")

    # Create the central AuthUser first so login works properly
    hashed_pwd = pwd_context.hash(data.s_password)
    new_auth_user = AuthUser(
        username=data.s_numbers, # Map mobile to username
        email=data.s_email,
        first_name=data.s_name,
        last_name=data.s_designation,
        password=hashed_pwd,
        is_active=1,
        is_staff=1,     # SP Authority gets staff
        is_superuser=1, # SP Authority gets superuser
        date_joined=datetime.utcnow()
    )
    
    db.add(new_auth_user)
    await db.flush() # get ID

    new_authority = Nsp_authourity(
        s_name=data.s_name,
        s_numbers=data.s_numbers,
        s_designation=data.s_designation,
        s_email=data.s_email,
        s_password=hashed_pwd
    )
    
    db.add(new_authority)
    await db.commit()
    await db.refresh(new_authority)
    return new_authority
