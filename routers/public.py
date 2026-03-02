from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Form_data
from datetime import datetime
from typing import Optional

router = APIRouter()

@router.post("/report")
async def public_report(
    description: str = Body(...),
    location: str = Body(...),
    latitude: Optional[float] = Body(None),
    longitude: Optional[float] = Body(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Unauthenticated endpoint for public reports.
    Markers as is_public = 1.
    """
    if not location or not description:
        raise HTTPException(status_code=400, detail="Location and description are mandatory for reporting.")
    
    # Create public report entry
    # Serial prefix PUB- facilitates easy filtering for admins
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_report = Form_data(
        fserial=f"PUB-{timestamp}",
        d_bomb=description,
        fdate=datetime.now(),
        flocation=location,
        latitude=latitude,
        longitude=longitude,
        is_public=1 # Flag for public report
    )
    
    try:
        db.add(new_report)
        await db.commit()
        await db.refresh(new_report)
        return {
            "status": 200,
            "message": "Intelligence received. Our team will investigate. Thank you for your alertness.",
            "reference_id": new_report.fserial
        }
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to submit intelligence report.")
