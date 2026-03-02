from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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
async def get_locations(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_location).order_by(N_location.l_location).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/apijuridiction")
async def get_jurisdictions(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_juridiction).order_by(N_juridiction.l_juridiction).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/apiincident")
async def get_incidents(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_incident).order_by(N_incident.i_incident).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/apiweight")
async def get_weights(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_weight).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/master/dalam")
async def get_dalam(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_dalam).order_by(N_dalam.d_dalam).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/serdesignation")
@router.get("/master/serdesignation")
async def get_designations(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_degignation).order_by(N_degignation.d_designation).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/master/assusedapi")
@router.get("/master/accusedapi")
async def get_assused(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_assused).order_by(N_assused.a_assused).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/master/postapi")
async def get_posts(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_post).order_by(N_post.p_post).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/master/ditectionapi")
@router.get("/master/detectionapi")
async def get_detections(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_ditection).order_by(N_ditection.d_ditection).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/master/despose")
@router.get("/master/dispose")
async def get_disposes(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_dispose).order_by(N_dispose.d_dispose).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/master/apiexplosive")
async def get_explosives(
    skip: int = 0,
    limit: int = Query(default=100, lte=500),
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    result = await db.execute(select(N_explosive).order_by(N_explosive.e_explosive).offset(skip).limit(limit))
    return result.scalars().all()

# --- Location Management ---

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


# ─────────────────────────────────────────────────────────────────
# Generic Master Data CRUD: Add / Update / Delete for all tables
# ─────────────────────────────────────────────────────────────────

# Config: { frontend_key: (Model, field_name) }
_MASTER_CRUD = {
    # (add_url_suffix, upd_url_suffix, dlt_url_suffix): (Model, field, add_form_key, upd_form_key, upd_id_key, dlt_id_key)
    "jurisdiction": (N_juridiction, "l_juridiction", "jurisdiction_value", "jurisdiction_value", "juridiction_id", "j_id"),
    "incident":     (N_incident,    "i_incident",    "incident_value",     "incident_value",     "incident_id",    "i_id"),
    "weight":       (N_weight,      "w_weight",      "weight_value",       "weight_value",       "weight_id",      "w_id"),
    "explosive":    (N_explosive,   "e_explosive",   "explosive_value",    "explosive_value",    "explosive_id",   "e_id"),
    "a_status":     (N_assused,     "a_assused",     "c_status_value",     "status_value",       "status_id",      "s_id"),
    "post":         (N_post,        "p_post",        "post_value",         "post_value",         "post_id",        "p_id"),
    "designation":  (N_degignation, "d_designation", "designation_value",  "designation_value",  "designation_id", "d_id"),
    "detection":    (N_ditection,   "d_ditection",   "detection_value",    "detection_value",    "detection_id",   "di_id"),
    "dispose":      (N_dispose,     "d_dispose",     "dispose_value",      "dispose_value",      "dispose_id",     "ds_id"),
    "dalam":        (N_dalam,       "d_dalam",       "dalam_value",        "dalam_value",        "dalam_id",       "dalam_id"),
}

async def _parse_form_or_json(request):
    try:
        return await request.json()
    except:
        return dict(await request.form())


# ── Add endpoints ──
from fastapi import Request

@router.post("/tlocation")
async def add_location(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("locations_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    item = N_location(l_location=value)
    db.add(item)
    await db.commit()
    return {"status": 200, "message": "successfully location created"}

@router.post("/jurisdiction")
@router.post("/jrusdiction")
async def add_jurisdiction(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("jurisdiction_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_juridiction(l_juridiction=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}

@router.post("/incident")
async def add_incident(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("incident_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_incident(i_incident=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}

@router.post("/weight")
async def add_weight(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("weight_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_weight(w_weight=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}

@router.post("/explosive")
async def add_explosive(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("explosive_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_explosive(e_explosive=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}

@router.post("/a_status")
async def add_accused_status(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("c_status_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_assused(a_assused=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}

@router.post("/post")
async def add_post(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("post_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_post(p_post=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}

@router.post("/designation")
async def add_designation(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("designation_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_degignation(d_designation=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}

@router.post("/detection")
async def add_detection(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("detection_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_ditection(d_ditection=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}

@router.post("/dispose")
async def add_dispose(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("dispose_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_dispose(d_dispose=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}

@router.post("/dalam")
async def add_dalam(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    value = data.get("dalam_value")
    if not value: raise HTTPException(status_code=400, detail="Value required")
    db.add(N_dalam(d_dalam=value))
    await db.commit()
    return {"status": 200, "message": "successfully created"}


# ── Update endpoints ──

@router.post("/updjurisdiction")
@router.post("/updjuridiction")
async def update_jurisdiction(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("juridiction_id")
    value = data.get("jurisdiction_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_juridiction).where(N_juridiction.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.l_juridiction = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}

@router.post("/updincident")
async def update_incident(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("incident_id")
    value = data.get("incident_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_incident).where(N_incident.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.i_incident = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}

@router.post("/updweight")
async def update_weight(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("weight_id")
    value = data.get("weight_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_weight).where(N_weight.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.w_weight = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}

@router.post("/updexplosive")
async def update_explosive(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("explosive_id")
    value = data.get("explosive_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_explosive).where(N_explosive.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.e_explosive = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}

@router.post("/updstatus")
async def update_status(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("status_id")
    value = data.get("status_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_assused).where(N_assused.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.a_assused = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}

@router.post("/updpost")
async def update_post(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("post_id")
    value = data.get("post_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_post).where(N_post.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.p_post = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}

@router.post("/upddesignation")
async def update_designation(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("designation_id")
    value = data.get("designation_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_degignation).where(N_degignation.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.d_designation = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}

@router.post("/upddetection")
async def update_detection(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("detection_id")
    value = data.get("detection_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_ditection).where(N_ditection.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.d_ditection = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}

@router.post("/upddispose")
async def update_dispose(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("dispose_id")
    value = data.get("dispose_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_dispose).where(N_dispose.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.d_dispose = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}

@router.post("/upddalam")
async def update_dalam(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("dalam_id")
    value = data.get("dalam_value")
    if not item_id or not value: raise HTTPException(status_code=400, detail="ID and value required")
    result = await db.execute(select(N_dalam).where(N_dalam.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    item.d_dalam = value
    await db.commit()
    return {"status": 200, "message": "successfully updated"}


# ── Delete endpoints ──

@router.post("/dltjurisdiction")
@router.post("/dltjuridiction")
async def delete_jurisdiction(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("j_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_juridiction).where(N_juridiction.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}

@router.post("/dltincident")
async def delete_incident(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("i_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_incident).where(N_incident.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}

@router.post("/dltweight")
async def delete_weight(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("w_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_weight).where(N_weight.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}

@router.post("/dltexplosive")
async def delete_explosive(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("e_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_explosive).where(N_explosive.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}

@router.post("/dltstatus")
async def delete_status(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("s_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_assused).where(N_assused.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}

@router.post("/dltpost")
async def delete_post(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("p_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_post).where(N_post.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}

@router.post("/dltdesignation")
async def delete_designation(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("d_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_degignation).where(N_degignation.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}

@router.post("/dltdetection")
async def delete_detection(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("di_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_ditection).where(N_ditection.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}

@router.post("/dltdispose")
async def delete_dispose(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("ds_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_dispose).where(N_dispose.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}

@router.post("/dltdalam")
async def delete_dalam(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    data = await _parse_form_or_json(request)
    item_id = data.get("dalam_id")
    if not item_id: raise HTTPException(status_code=400, detail="ID required")
    result = await db.execute(select(N_dalam).where(N_dalam.id == int(item_id)))
    item = result.scalar_one_or_none()
    if not item: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(item)
    await db.commit()
    return {"status": 200, "message": "successfully deleted"}
