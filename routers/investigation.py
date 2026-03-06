from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from database import get_db
from models import CriminalDossier, CriminalLink, Form_data, AuthUser
from auth import get_current_user
from datetime import datetime
from typing import Optional

router = APIRouter()

@router.get("/search")
async def search_criminals(query: str = Query(...), db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """Search for criminals by name or alias."""
    stmt = select(CriminalDossier).where(
        or_(
            CriminalDossier.name.ilike(f"%{query}%"),
            CriminalDossier.alias.ilike(f"%{query}%")
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/detail/{id}")
async def get_criminal_detail(id: int, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """Get full dossier and incident history for a criminal."""
    result = await db.execute(select(CriminalDossier).where(CriminalDossier.id == id))
    criminal = result.scalar_one_or_none()
    if not criminal:
        raise HTTPException(status_code=404, detail="Criminal not found")
    
    # Fetch incident history via links
    stmt = (
        select(CriminalLink, Form_data)
        .join(Form_data, CriminalLink.form_id == Form_data.id)
        .where(CriminalLink.criminal_id == id)
        .order_by(Form_data.fdate.desc())
    )
    links_result = await db.execute(stmt)
    
    from models import N_location
    history = []
    for link, form in links_result:
        loc_obj = None
        if form.flocation_type_id:
            loc_res = await db.execute(select(N_location).where(N_location.id == form.flocation_type_id))
            loc_obj = loc_res.scalar_one_or_none()

        history.append({
            "incident_id": form.id,
            "serial": form.fserial,
            "date": form.fdate.strftime("%Y-%m-%d %H:%M:%S") if form.fdate else None,
            "location": form.flocation, # Raw coordinates/data
            "d_bomb": form.d_bomb, # Match Android entity @SerializedName
            "flocation_type": {
                "id": loc_obj.id if loc_obj else None,
                "l_location": loc_obj.l_location if loc_obj else None,
                "l_datetime": loc_obj.l_datetime.isoformat() if loc_obj and loc_obj.l_datetime else None
            } if loc_obj else None, # Object for Android
            "role": link.role
        })
    
    return {
        "criminal": criminal,
        "history": history
    }

@router.post("/create")
async def create_criminal(
    name: str = Body(...),
    alias: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    photo_path: Optional[str] = Body(None),
    status: str = Body("Active"),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    """Create a new criminal dossier entry."""
    new_criminal = CriminalDossier(
        name=name,
        alias=alias,
        description=description,
        photo_path=photo_path,
        status=status,
        created_at=datetime.utcnow()
    )
    db.add(new_criminal)
    await db.commit()
    await db.refresh(new_criminal)
    return new_criminal

@router.post("/link")
async def link_criminal_to_incident(
    form_id: int = Body(...),
    criminal_id: int = Body(...),
    role: str = Body("Accused"),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    """Link a criminal dossier to an incident report."""
    # Check if already linked
    existing = await db.execute(
        select(CriminalLink).where(
            CriminalLink.form_id == form_id,
            CriminalLink.criminal_id == criminal_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Criminal already linked to this incident")

    new_link = CriminalLink(
        form_id=form_id,
        criminal_id=criminal_id,
        role=role,
        created_at=datetime.utcnow()
    )
    db.add(new_link)
    await db.commit()
    return {"message": "Dossier linked successfully", "status": 200}
