from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import (
    AuthUser, N_location, N_juridiction, N_incident, N_weight, 
    N_explosive, N_assused, N_dalam, N_ditection, N_dispose,
    N_degignation, N_post
)
from auth import get_current_user
from schemas import LocationUpdate, LocationDelete

router = APIRouter()

@router.get("/apilocation")
async def get_locations(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_location))
    return result.scalars().all()

@router.get("/apijuridiction")
async def get_jurisdictions(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_juridiction))
    return result.scalars().all()

@router.get("/apiincident")
async def get_incidents(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_incident))
    return result.scalars().all()

@router.get("/apiweight")
async def get_weights(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_weight))
    return result.scalars().all()

@router.get("/master/dalam")
async def get_dalam(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_dalam))
    return result.scalars().all()

@router.get("/serdesignation")
@router.get("/master/serdesignation")
async def get_designations(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_degignation))
    return result.scalars().all()

@router.get("/master/assusedapi")
@router.get("/master/accusedapi")
async def get_assused(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_assused))
    return result.scalars().all()

@router.get("/master/postapi")
async def get_posts(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_post))
    return result.scalars().all()

@router.get("/master/ditectionapi")
@router.get("/master/detectionapi")
async def get_detections(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_ditection))
    return result.scalars().all()

@router.get("/master/despose")
@router.get("/master/dispose")
async def get_disposes(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_dispose))
    return result.scalars().all()

@router.get("/master/apiexplosive")
async def get_explosives(db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    result = await db.execute(select(N_explosive))
    return result.scalars().all()

# --- Location Management ---

@router.post("/api_proxy/updlocation")
@router.post("/updlocation")
async def update_location(
    data: LocationUpdate, 
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    """Update an existing location name."""
    stmt = select(N_location).where(N_location.id == data.location_id)
    result = await db.execute(stmt)
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    location.l_location = data.locations_value
    await db.commit()
    return {"status": 200, "message": "Location updated successfully"}

@router.post("/api_proxy/dlocation")
@router.post("/dlocation")
async def delete_location(
    data: LocationDelete, 
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    """Delete a location from the database."""
    stmt = select(N_location).where(N_location.id == data.location_id)
    result = await db.execute(stmt)
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    await db.delete(location)
    await db.commit()
    return {"status": 200, "message": "Location deleted successfully"}
