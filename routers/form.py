from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.orm import selectinload
from typing import List
from database import get_db
from models import (
    Form_data, N_dalam, form_dalam_association, 
    death_person, injured_person, exploded, AuthUser,
    images, s_report, sk_report,
    N_location, N_juridiction, N_incident, N_weight, 
    N_explosive, N_assused, N_ditection, N_dispose
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
    import json
    """Robust cleaning for cases where mobile apps send quoted keys/values"""
    clean_data = {}
    for k, v in data.items():
        clean_k = k.strip(' "\'{}:')
        val = v[0] if isinstance(v, list) and len(v) > 0 else v
        if isinstance(val, str):
            val = val.strip(' "\',}:')
            # Try to parse as JSON if it looks like a list or object
            if (val.startswith('[') and val.endswith(']')) or (val.startswith('{') and val.endswith('}')):
                try:
                    val = json.loads(val)
                except:
                    pass
        if clean_k:
            clean_data[clean_k] = val
    return clean_data

def safe_get_list(data, key):
    """Ensure we get a list of dicts, even if double-stringified"""
    import json
    val = data.get(key, [])
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except:
            return []
    if isinstance(val, list):
        parsed_list = []
        for item in val:
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except:
                    continue
            if isinstance(item, dict):
                parsed_list.append(item)
        return parsed_list
    return []

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
        flocation_type_id=parse_int(data.get('location_data') or data.get('flocation_type') or data.get('flocation_type_id')),
        flocation_description=data.get('location_description') or data.get('flocation_description'),
        fjuridiction_id=parse_int(data.get('jurisdiction_data') or data.get('fjuridiction') or data.get('fjuridiction_id')),
        fincident_id=parse_int(data.get('incident_data') or data.get('fincident') or data.get('fincident_id')),
        fweight_data_id=parse_int(data.get('weight_data') or data.get('fweight_data') or data.get('fweight_data_id')),
        fexplosive_id=parse_int(data.get('explosive_data') or data.get('fexplosive') or data.get('fexplosive_id')),
        fdetonator=data.get('detonator_data') or data.get('fdetonator'),
        fswitch=data.get('switch_data') or data.get('fswitch'),
        ftarget=data.get('target_data') or data.get('ftarget'),
        fdistruction=data.get('distruction_data') or data.get('fdistruction'),
        fassume=data.get('assume_data') or data.get('fassume'),
        radio_data=data.get('i_data') or data.get('radio_data'),
        fassume_status_new_id=parse_int(data.get('assume_status') or data.get('fassume_status_new') or data.get('fassume_status_new_id')),
        flearning=data.get('learning_data') or data.get('flearning'),
        mode_of_detection_id=parse_int(data.get('mode_detection') or data.get('mode_of_detection') or data.get('mode_of_detection_id')),
        detected_description=data.get('mode_description') or data.get('detected_description'),
        detected_pname=data.get('detected_name') or data.get('detected_pname'),
        detcted_contact=data.get('detected_contact') or data.get('detcted_contact'),
        detected_dispose_id=parse_int(data.get('detected_despose') or data.get('detected_dispose') or data.get('detected_dispose_id')),
        dispose_name=data.get('despose_name') or data.get('dispose_name'),
        dispose_contact=data.get('despose_contact') or data.get('dispose_contact'),
    )
    
    db.add(new_form)
    await db.flush()

    # Auto-parse coordinates if flocation contains "lat,long" and lat/long are missing
    if new_form.flocation and not new_form.latitude and not new_form.longitude:
        try:
            parts = str(new_form.flocation).split(',')
            if len(parts) == 2:
                new_form.latitude = parse_float(parts[0].strip())
                new_form.longitude = parse_float(parts[1].strip())
        except:
            pass

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

    for p in safe_get_list(data, 'death'):
        db.add(death_person(form_id=new_form.id, death_name=p.get('name') or p.get('death_name'), death_contact=p.get('contact') or p.get('death_contact')))
            
    for p in safe_get_list(data, 'injured'):
        db.add(injured_person(form_id=new_form.id, injured_name=p.get('name') or p.get('injured_name'), injured_contact=p.get('contact') or p.get('injured_contact')))
            
    for p in safe_get_list(data, 'explode'):
        db.add(exploded(form_id=new_form.id, exploded_name=p.get('name') or p.get('exploded_name'), explode_contact=p.get('contact') or p.get('explode_contact')))
    
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

    async def get_full_form_dict(form_id, form_obj=None):
        if not form_obj:
            res = await db.execute(select(Form_data).options(selectinload(Form_data.fdalam)).where(Form_data.id == form_id))
            form_obj = res.scalar_one_or_none()
        if not form_obj: return None

        # Fetch all master data objects for nesting
        loc = await db.execute(select(N_location).where(N_location.id == form_obj.flocation_type_id))
        jur = await db.execute(select(N_juridiction).where(N_juridiction.id == form_obj.fjuridiction_id))
        inc = await db.execute(select(N_incident).where(N_incident.id == form_obj.fincident_id))
        wei = await db.execute(select(N_weight).where(N_weight.id == form_obj.fweight_data_id))
        exp = await db.execute(select(N_explosive).where(N_explosive.id == form_obj.fexplosive_id))
        ass = await db.execute(select(N_assused).where(N_assused.id == form_obj.fassume_status_new_id))
        det = await db.execute(select(N_ditection).where(N_ditection.id == form_obj.mode_of_detection_id))
        dis = await db.execute(select(N_dispose).where(N_dispose.id == form_obj.detected_dispose_id))
        
        loc_o = loc.scalar_one_or_none()
        jur_o = jur.scalar_one_or_none()
        inc_o = inc.scalar_one_or_none()
        wei_o = wei.scalar_one_or_none()
        exp_o = exp.scalar_one_or_none()
        ass_o = ass.scalar_one_or_none()
        det_o = det.scalar_one_or_none()
        dis_o = dis.scalar_one_or_none()

        # Handle M2M fdalam (take first as per user example structure)
        fdalam_obj = None
        if form_obj.fdalam:
            d_obj = form_obj.fdalam[0]
            fdalam_obj = {"id": d_obj.id, "d_dalam": d_obj.d_dalam}

        form_dict = {
            "id": form_obj.id,
            "fserial": form_obj.fserial,
            "d_bomb": form_obj.d_bomb,
            "fdate": str(form_obj.fdate.date()) if form_obj.fdate else None,
            "flocation": form_obj.flocation,
            "flocation_type": {"id": loc_o.id, "l_location": loc_o.l_location} if loc_o else None,
            "flocation_description": form_obj.flocation_description,
            "fjuridiction": {"id": jur_o.id, "j_name": jur_o.l_juridiction} if jur_o else None,
            "fincident": {"id": inc_o.id, "incident_name": inc_o.i_incident} if inc_o else None,
            "fweight_data": {"id": wei_o.id, "weight": wei_o.w_weight} if wei_o else None,
            "fexplosive": {"id": exp_o.id, "explosive_name": exp_o.e_explosive} if exp_o else None,
            "fdetonator": form_obj.fdetonator,
            "fswitch": form_obj.fswitch,
            "ftarget": form_obj.ftarget,
            "fdistruction": form_obj.fdistruction,
            "fassume": form_obj.fassume,
            "radio_data": form_obj.radio_data,
            "fdalam": fdalam_obj,
            "flearning": form_obj.flearning,
            "fassume_status_new": {"id": ass_o.id, "a_assused": ass_o.a_assused} if ass_o else None,
            "mode_of_detection": {"id": det_o.id, "detection_name": det_o.d_ditection} if det_o else None,
            "detected_description": form_obj.detected_description,
            "detected_pname": form_obj.detected_pname,
            "detcted_contact": form_obj.detcted_contact,
            "detected_dispose": {"id": dis_o.id, "dispose_type": dis_o.d_dispose} if dis_o else None,
            "dispose_name": form_obj.dispose_name,
            "dispose_contact": form_obj.dispose_contact,
            "edit_request": str(form_obj.edit_request),
            "delete_request": str(form_obj.delete_request)
        }
        return form_dict

    if not id:
        # Return whole list for current user if no ID specified
        stmt = select(Form_data).options(selectinload(Form_data.fdalam)).where(Form_data.user_id == current_user.id).order_by(Form_data.fdate.desc())
        result = await db.execute(stmt)
        forms = result.scalars().all()
        
        form_list = []
        for f in forms:
            f_dict = await get_full_form_dict(f.id, f)
            form_list.append(f_dict)
            
        return {"form_data": form_list}

    # Single form detail
    form_dict = await get_full_form_dict(id)
    if not form_dict:
        raise HTTPException(status_code=404, detail="Form not found")

    # Fetch related data (rename keys to _data as requested)
    death_res = await db.execute(select(death_person).filter(death_person.form_id == id))
    inj_res = await db.execute(select(injured_person).filter(injured_person.form_id == id))
    exp_res = await db.execute(select(exploded).filter(exploded.form_id == id))
    img_res = await db.execute(select(images).filter(images.form_id == id))
    rep_res = await db.execute(select(s_report).filter(s_report.form_id == id))
    sk_res = await db.execute(select(sk_report).filter(sk_report.form_id == id))
    
    return {
        "form_data": [form_dict],
        "death_data": death_res.scalars().all(),
        "injured_data": inj_res.scalars().all(),
        "explode_data": exp_res.scalars().all(),
        "image_data": img_res.scalars().all(),
        "reports_data": rep_res.scalars().all(),
        "sketch_data": sk_res.scalars().all()
    }

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

    from models import N_location
    stmt = select(Form_data, N_location).outerjoin(N_location, Form_data.flocation_type_id == N_location.id).where(Form_data.user_id == current_user.id)
    
    if limit is not None:
        effective_limit = min(int(limit), 25)
        stmt = stmt.offset(offset).limit(effective_limit)
    
    result = await db.execute(stmt)
    rows = result.all()
    
    form_list = []
    for form, loc_obj in rows:
        # Return only the specific fields requested for the list view
        form_list.append({
            "id": form.id,
            "fserial": form.fserial,
            "d_bomb": form.d_bomb,
            "fdate": str(form.fdate.date()) if isinstance(form.fdate, datetime) else str(form.fdate),
            "flocation": form.flocation, # Raw coordinates as requested
            "flocation_type": {
                "id": loc_obj.id if loc_obj else None,
                "l_location": loc_obj.l_location if loc_obj else None,
                "l_datetime": loc_obj.l_datetime.isoformat() if loc_obj and loc_obj.l_datetime else None
            } if loc_obj else None,
            "flocation_type_id": str(form.flocation_type_id) if form.flocation_type_id else None
        })
        
    return {"form_data": form_list}


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

    serial = data.get('fserial') or data.get('serial_uvalue')
    bomb = data.get('d_bomb') or data.get('bomb_uvalue')
    date_val = data.get('fdate') or data.get('date_uvalue')

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

    form.flocation = data.get('flocation') or data.get('loacation_uvalue')
    form.flocation_type_id = data.get('flocation_type') or data.get('location_ty_uvalue') or None
    form.flocation_description = data.get('flocation_description') or data.get('location_dy_uvalue')
    form.fjuridiction_id = data.get('fjuridiction') or data.get('juridiction_uvalue') or None
    form.fincident_id = data.get('fincident') or data.get('incident_uvalue') or None
    form.fexplosive_id = data.get('fexplosive') or data.get('explosive_uvalue') or None
    form.fweight_data_id = data.get('fweight_data') or data.get('weight_uvalue') or None
    form.fdetonator = data.get('fdetonator') or data.get('detonator_uvalue')
    form.fswitch = data.get('fswitch') or data.get('switch_uvalue')
    form.ftarget = data.get('ftarget') or data.get('target_uvalue')
    form.fdistruction = data.get('fdistruction') or data.get('distruction_uvalue')
    form.fassume = data.get('fassume') or data.get('assused_uvalue')
    form.fassume_status_new_id = data.get('fassume_status_new') or data.get('assused_status_uvalue') or None
    form.flearning = data.get('flearning') or data.get('mistake_uvalue')
    form.fir = data.get('fir') or data.get('fir_uvalue')
    form.latitude = data.get('latitude') or data.get('latitude_uvalue')
    form.longitude = data.get('longitude') or data.get('longitude_uvalue')
    form.radio_data = data.get('radio_data') or data.get('i_data')

    form.mode_of_detection_id = data.get('mode_of_detection') or data.get('detection_uvalue') or None
    form.detected_description = data.get('detected_description') or data.get('detected_description_uvalue')
    form.detected_pname = data.get('detected_pname') or data.get('detected_pname_uvalue')
    form.detcted_contact = data.get('detcted_contact') or data.get('detected_contact_uvalue')
    form.detected_dispose_id = data.get('detected_dispose') or data.get('dispose_uvalue') or None
    form.dispose_name = data.get('dispose_name') or data.get('dispose_name_uvalue')
    form.dispose_contact = data.get('dispose_contact') or data.get('dispose_contact_uvalue')

    # Update M2M Dalam
    dalam_ids = data.get('fdalam') or data.get('dalam_uvalue', [])
    await db.execute(delete(form_dalam_association).where(form_dalam_association.c.form_data_id == id))
    if dalam_ids and isinstance(dalam_ids, list):
        for did in dalam_ids:
            await db.execute(form_dalam_association.insert().values(form_data_id=id, n_dalam_id=int(did)))

    # Sync Death persons
    await db.execute(delete(death_person).where(death_person.form_id == id))
    for item in safe_get_list(data, 'death'):
        db.add(death_person(form_id=id, death_name=item.get('death_name') or item.get('name'), death_contact=item.get('death_contact') or item.get('contact')))

    # Sync Injured persons
    await db.execute(delete(injured_person).where(injured_person.form_id == id))
    for item in safe_get_list(data, 'injured'):
        db.add(injured_person(form_id=id, injured_name=item.get('injured_name') or item.get('name'), injured_contact=item.get('injured_contact') or item.get('contact')))

    # Sync Exploded persons
    await db.execute(delete(exploded).where(exploded.form_id == id))
    for item in safe_get_list(data, 'explode'):
        db.add(exploded(form_id=id, exploded_name=item.get('exploded_name') or item.get('name'), explode_contact=item.get('explode_contact') or item.get('contact')))

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
