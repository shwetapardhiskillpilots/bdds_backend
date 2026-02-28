from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from database import get_db
from models import (
    Form_data, N_dalam, form_dalam_association, 
    death_person, injured_person, exploded, AuthUser
)
from auth import get_current_user
from datetime import datetime
import json

router = APIRouter()

def clean_mobile_data(data: dict) -> dict:
    """Robust cleaning for cases where mobile apps send quoted keys/values"""
    clean_data = {}
    for k, v in data.items():
        clean_k = k.strip(' "\'{}:')
        val = v[0] if isinstance(v, list) and len(v) > 0 else v
        if isinstance(val, str):
            val = val.strip(' "\',}:')
        if clean_k:
            clean_data[clean_k] = val
    return clean_data

@router.post("/formapi")
async def create_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    try:
        raw_data = await request.json()
    except:
        form_data = await request.form()
        raw_data = dict(form_data)
        
    data = clean_mobile_data(raw_data)
    
    fserial_no = data.get('fserial')
    if not fserial_no:
        raise HTTPException(status_code=400, detail="Serial number required")
        
    existing = await db.execute(select(Form_data).where(Form_data.fserial == fserial_no))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Serial already exists")

    # Create form data object
    # Simplified mapping for brevity in this POC, in reality, use all fields
    new_form = Form_data(
        fserial=fserial_no,
        d_bomb=data.get('d_bomb'),
        fdate=datetime.now(), # Simplified date handling
        flocation=data.get('flocation'),
        user_id=current_user.id
    )
    
    db.add(new_form)
    await db.flush()

    # Handle persons
    if 'death' in data:
        for p in data['death']:
            db.add(death_person(form_id=new_form.id, death_name=p.get('death_name'), death_contact=p.get('death_contact')))
    
    await db.commit()
    return {"message": "Form submitted successfully", "id": new_form.id, "status": 200}

@router.post("/formviewapi")
@router.get("/formviewapi")
async def list_view(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    # Handle both GET (for browser/testing) and POST (mobile app requirement)
    if request.method == "POST":
        try:
            data = await request.json()
            id = data.get('id')
        except:
            id = (await request.form()).get('id')
    else:
        id = request.query_params.get('id')

    if not id:
        return {"form_data": []}

    result = await db.execute(select(Form_data).where(Form_data.id == id))
    form = result.scalar_one_or_none()
    
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    return {
        "form_data": [form],
        # Add other related data if needed
    }

@router.post("/listonly")
@router.get("/listonly")
async def list_only(
    request: Request, 
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
    # Extract pagination parameters from query params (GET) or body (POST)
    # We maintain the signature to "not change the base code"
    params = request.query_params
    if request.method == "POST":
        try:
            body = await request.json()
            params = {**params, **body}
        except:
            pass

    offset = int(params.get("offset", 0))
    limit = params.get("limit")

    stmt = select(Form_data).where(Form_data.user_id == current_user.id)
    
    if limit is not None:
        # Cap limit at 25 if provided
        effective_limit = min(int(limit), 25)
        stmt = stmt.offset(offset).limit(effective_limit)
    
    result = await db.execute(stmt)
    forms = result.scalars().all()
    # Mirror Django's exact JSON shape wrapper for lists
    return {"form_data": forms}
