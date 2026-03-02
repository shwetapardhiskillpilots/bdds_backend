from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from database import get_db
from models import (
    Form_data, N_dalam, form_dalam_association, 
    death_person, injured_person, exploded, AuthUser,
    images, s_report, sk_report
)
from auth import get_current_user
from datetime import datetime
import os
import shutil

router = APIRouter()

# ── Helper for file saving ──
def save_upload_file(upload_file: UploadFile, destination: str):
    try:
        if not os.path.exists(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()

def clean_mobile_data(data: dict) -> dict:
    """Robust cleaning for cases where mobile apps send quoted keys/values"""
    clean_data = {}
    for k, v in data.items():
        if isinstance(k, str):
            clean_k = k.strip(' "\'{}:')
        else:
            clean_k = str(k)
            
        val = v[0] if isinstance(v, list) and len(v) > 0 and isinstance(v[0], str) else v
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
    
    fserial_no = data.get('serial_value') or data.get('fserial')
    if not fserial_no:
        raise HTTPException(status_code=400, detail="Serial number required")
        
    existing = await db.execute(select(Form_data).where(Form_data.fserial == fserial_no))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Serial already exists")

    # Helpers
    def parse_int(val):
        try: return int(val) if val else None
        except: return None
        
    def parse_float(val):
        try: return float(val) if val else None
        except: return None
        
    def parse_date(date_str):
        if not date_str: return datetime.now()
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return datetime.now()

    new_form = Form_data(
        user_id=current_user.id,
        fserial=fserial_no,
        d_bomb=data.get('bomb_value') or data.get('d_bomb'),
        fir=data.get('fir_value') or data.get('fir'),
        fdate=parse_date(data.get('date&time') or data.get('fdate')),
        flocation=data.get('location_value') or data.get('flocation'),
        latitude=parse_float(data.get('latitude_value') or data.get('latitude')),
        longitude=parse_float(data.get('longitude_value') or data.get('longitude')),
        flocation_type_id=parse_int(data.get('location_data') or data.get('flocation_type_id')),
        flocation_description=data.get('location_description') or data.get('flocation_description'),
        fjuridiction_id=parse_int(data.get('jurisdiction_data') or data.get('fjuridiction_id')),
        fincident_id=parse_int(data.get('incident_data') or data.get('fincident_id')),
        fweight_data_id=parse_int(data.get('weight_data') or data.get('fweight_data_id')),
        fexplosive_id=parse_int(data.get('explosive_data') or data.get('fexplosive_id')),
        fdetonator=data.get('detonator_data') or data.get('fdetonator'),
        fswitch=data.get('switch_data') or data.get('fswitch'),
        ftarget=data.get('target_data') or data.get('ftarget'),
        fdistruction=data.get('distruction_data') or data.get('fdistruction'),
        fassume=data.get('assume_data') or data.get('fassume'),
        radio_data=data.get('i_data') or data.get('radio_data'),
        fassume_status_new_id=parse_int(data.get('assume_status') or data.get('fassume_status_new_id')),
        flearning=data.get('learning_data') or data.get('flearning'),
        mode_of_detection_id=parse_int(data.get('mode_detection') or data.get('mode_of_detection_id')),
        detected_description=data.get('mode_description') or data.get('detected_description'),
        detected_pname=data.get('detected_name') or data.get('detected_pname'),
        detcted_contact=data.get('detected_contact') or data.get('detcted_contact'),
        detected_dispose_id=parse_int(data.get('detected_despose') or data.get('detected_dispose_id')),
        dispose_name=data.get('despose_name') or data.get('dispose_name'),
        dispose_contact=data.get('despose_contact') or data.get('dispose_contact'),
    )
    
    db.add(new_form)
    await db.flush()

    # Handle Dalam relationship
    dalam_id = parse_int(data.get('dalam_data') or data.get('fdalam'))
    if dalam_id:
        from models import form_dalam_association
        from sqlalchemy import insert
        await db.execute(
            insert(form_dalam_association).values(
                form_data_id=new_form.id,
                n_dalam_id=dalam_id
            )
        )

    if 'death' in data:
        for p in data['death']:
            db.add(death_person(form_id=new_form.id, death_name=p.get('name'), death_contact=p.get('contact')))
            
    if 'injured' in data:
        for p in data['injured']:
            db.add(injured_person(form_id=new_form.id, injured_name=p.get('name'), injured_contact=p.get('contact')))
            
    if 'explode' in data:
        for p in data['explode']:
            db.add(exploded(form_id=new_form.id, exploded_name=p.get('name'), explode_contact=p.get('contact')))
    
    await db.commit()
    return {"message": "Form submitted successfully", "id": new_form.id, "status": 200}

@router.post("/formviewapi")
@router.get("/formviewapi")
async def list_view(request: Request, db: AsyncSession = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
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

    return {"form_data": [form]}

@router.post("/listonly")
@router.get("/listonly")
async def list_only(
    request: Request, 
    db: AsyncSession = Depends(get_db), 
    current_user: AuthUser = Depends(get_current_user)
):
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
        effective_limit = min(int(limit), 25)
        stmt = stmt.offset(offset).limit(effective_limit)
    
    result = await db.execute(stmt)
    forms = result.scalars().all()
    return {"form_data": forms}


# ── Delete Form Data ──
@router.get("/dltfdata")
@router.post("/dltfdata")
async def delete_form_data(
    request: Request,
    f_id: int = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Mirror Django's dlt_subdata: delete form and cascade related media."""
    if f_id is None:
        if request.method == "POST":
            try:
                data = await request.json()
                f_id = data.get('f_id')
            except:
                form_data = await request.form()
                f_id = form_data.get('f_id')

    if not f_id:
        raise HTTPException(status_code=400, detail="f_id required")

    f_id = int(f_id)

    result = await db.execute(select(Form_data).where(Form_data.id == f_id))
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    try:
        await db.execute(delete(images).where(images.form_id == f_id))
        await db.execute(delete(s_report).where(s_report.form_id == f_id))
        await db.execute(delete(sk_report).where(sk_report.form_id == f_id))
        await db.execute(delete(death_person).where(death_person.form_id == f_id))
        await db.execute(delete(injured_person).where(injured_person.form_id == f_id))
        await db.execute(delete(exploded).where(exploded.form_id == f_id))
        await db.execute(delete(form_dalam_association).where(form_dalam_association.c.form_data_id == f_id))
        await db.delete(form)
        await db.commit()
        return {"status": 200, "message": "form successfully deleted"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ── Update Form (First Portion) ──
@router.post("/updfdata/updatefirst/{id}")
async def update_form_first(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Mirror Django's update_form_first: full incident update with casualty sync."""
    try:
        data = await request.json()
    except:
        form_data = await request.form()
        data = dict(form_data)

    result = await db.execute(select(Form_data).where(Form_data.id == id))
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    serial = data.get('serial_uvalue')
    bomb = data.get('bomb_uvalue')
    date_val = data.get('date_uvalue')

    if not serial or not str(serial).strip():
        raise HTTPException(status_code=400, detail="Please enter incidence serial/year")
    if not bomb or not str(bomb).strip():
        raise HTTPException(status_code=400, detail="Please enter CR no. or bomb call")
    if not date_val or not str(date_val).strip() or str(date_val).lower() == "date time":
        raise HTTPException(status_code=400, detail="Please enter date time")

    form.fserial = serial
    form.d_bomb = bomb

    if date_val:
        try:
            if 'T' in str(date_val):
                form.fdate = datetime.strptime(str(date_val), '%Y-%m-%dT%H:%M')
            else:
                form.fdate = date_val
        except:
            form.fdate = date_val

    form.flocation = data.get('loacation_uvalue')
    form.flocation_type_id = data.get('location_ty_uvalue') or None
    form.flocation_description = data.get('location_dy_uvalue')
    form.fjuridiction_id = data.get('juridiction_uvalue') or None
    form.fincident_id = data.get('incident_uvalue') or None
    form.fexplosive_id = data.get('explosive_uvalue') or None
    form.fweight_data_id = data.get('weight_uvalue') or None
    form.fdetonator = data.get('detonator_uvalue')
    form.fswitch = data.get('switch_uvalue')
    form.ftarget = data.get('target_uvalue')
    form.fdistruction = data.get('distruction_uvalue')
    form.fassume = data.get('assused_uvalue')
    form.fassume_status_new_id = data.get('assused_status_uvalue') or None
    form.flearning = data.get('mistake_uvalue')
    form.fir = data.get('fir_uvalue')
    form.latitude = data.get('latitude_uvalue')
    form.longitude = data.get('longitude_uvalue')
    form.radio_data = data.get('i_data')

    form.mode_of_detection_id = data.get('detection_uvalue') or None
    form.detected_description = data.get('detected_description_uvalue')
    form.detected_pname = data.get('detected_pname_uvalue')
    form.detcted_contact = data.get('detected_contact_uvalue')
    form.detected_dispose_id = data.get('dispose_uvalue') or None
    form.dispose_name = data.get('dispose_name_uvalue')
    form.dispose_contact = data.get('dispose_contact_uvalue')

    # Update M2M Dalam
    dalam_ids = data.get('dalam_uvalue', [])
    await db.execute(delete(form_dalam_association).where(form_dalam_association.c.form_data_id == id))
    if dalam_ids and isinstance(dalam_ids, list):
        for did in dalam_ids:
            await db.execute(form_dalam_association.insert().values(form_data_id=id, n_dalam_id=int(did)))

    # Sync Death persons
    death_data = data.get('death', [])
    await db.execute(delete(death_person).where(death_person.form_id == id))
    if isinstance(death_data, list):
        for item in death_data:
            if item.get('death_name') or item.get('death_contact'):
                db.add(death_person(form_id=id, death_name=item.get('death_name'), death_contact=item.get('death_contact')))

    # Sync Injured persons
    injured_data = data.get('injured', [])
    await db.execute(delete(injured_person).where(injured_person.form_id == id))
    if isinstance(injured_data, list):
        for item in injured_data:
            if item.get('injured_name') or item.get('injured_contact'):
                db.add(injured_person(form_id=id, injured_name=item.get('injured_name'), injured_contact=item.get('injured_contact')))

    # Sync Exploded persons
    explode_data = data.get('explode', [])
    await db.execute(delete(exploded).where(exploded.form_id == id))
    if isinstance(explode_data, list):
        for item in explode_data:
            if item.get('exploded_name') or item.get('explode_contact'):
                db.add(exploded(form_id=id, exploded_name=item.get('exploded_name'), explode_contact=item.get('explode_contact')))

    await db.commit()
    return {"msg": "Incident updated successfully", "status": 200}


# ── Attachment Management (Mirroring Django images_api) ──

@router.post("/imageapi")
async def upload_attachments(
    id: int = Form(...),
    im_vi: List[UploadFile] = File(None),
    special_reports: List[UploadFile] = File(None),
    sketch_scences: List[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Handle multi-file uploads for a specific form.
    im_vi: Images/Videos
    special_reports: PDF documents
    sketch_scences: Tactical sketches
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Process Images/Videos
    if im_vi:
        for file in im_vi:
            filename = f"img_{id}_{timestamp}_{file.filename}"
            dest = os.path.join("media", filename)
            save_upload_file(file, dest)
            
            # Determine status (1 for video, 0 for image)
            status = 1 if file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')) else 0
            
            db.add(images(form_id=id, im_vi=filename, status=status))

    # Process Special Reports
    if special_reports:
        for file in special_reports:
            filename = f"rep_{id}_{timestamp}_{file.filename}"
            dest = os.path.join("media", filename)
            save_upload_file(file, dest)
            db.add(s_report(form_id=id, special_report=filename))

    # Process Sketches
    if sketch_scences:
        for file in sketch_scences:
            filename = f"sk_{id}_{timestamp}_{file.filename}"
            dest = os.path.join("media", filename)
            save_upload_file(file, dest)
            db.add(sk_report(form_id=id, sketch_scence=filename))

    await db.commit()
    return {"status": 200, "msg": "all document upload successfully"}


@router.post("/dltimg_api")
async def delete_image_api(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Delete a specific image record and its physical file."""
    try:
        data = await request.json()
    except:
        data = await request.form()
        
    obj_id = data.get('id')
    img_path = data.get('img_path')
    
    if not obj_id:
        raise HTTPException(status_code=400, detail="ID required")

    # Delete record
    await db.execute(delete(images).where(images.id == obj_id))
    
    # Delete file
    if img_path:
        # Strip potential leading /media/ prefix if sent by frontend
        clean_path = img_path.replace('/media/', '').replace('media/', '')
        full_path = os.path.join("media", clean_path)
        if os.path.isfile(full_path):
            os.remove(full_path)
            
    await db.commit()
    return {"msg": "Image deleted successfully", "status": 200}


@router.post("/dltreport_api")
async def delete_report_api(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Delete a specific report record and its physical file."""
    try:
        data = await request.json()
    except:
        data = await request.form()
        
    obj_id = data.get('id')
    report_path = data.get('report_path')
    
    if not obj_id:
        raise HTTPException(status_code=400, detail="ID required")

    # Delete record
    await db.execute(delete(s_report).where(s_report.id == obj_id))
    
    # Delete file
    if report_path:
        clean_path = report_path.replace('/media/', '').replace('media/', '')
        full_path = os.path.join("media", clean_path)
        if os.path.isfile(full_path):
            os.remove(full_path)
            
    await db.commit()
    return {"msg": "Report deleted successfully", "status": 200}


@router.post("/dltsketch_api")
async def delete_sketch_api(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Delete a specific sketch record and its physical file."""
    try:
        data = await request.json()
    except:
        data = await request.form()
        
    obj_id = data.get('id')
    sketch_path = data.get('sketch_path')
    
    if not obj_id:
        raise HTTPException(status_code=400, detail="ID required")

    # Delete record
    await db.execute(delete(sk_report).where(sk_report.id == obj_id))
    
    # Delete file
    if sketch_path:
        clean_path = sketch_path.replace('/media/', '').replace('media/', '')
        full_path = os.path.join("media", clean_path)
        if os.path.isfile(full_path):
            os.remove(full_path)
            
    await db.commit()
    return {"msg": "Sketch deleted successfully", "status": 200}
