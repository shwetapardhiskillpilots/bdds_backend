from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text
from database import get_db
from models import (
    Form_data, AuthUser, death_person, injured_person, exploded,
    images, s_report, sk_report, CriminalDossier, CriminalLink,
    N_ditection, N_dispose, N_location, N_juridiction, N_incident,
    N_explosive, N_weight
)
from auth import get_current_user
from schemas import DashboardStats
import time


# ── Simple TTL Cache (avoids repeated remote DB calls) ──
_stats_cache: dict = {}  # key: user_id or "admin" -> {"data": ..., "ts": time.time()}
CACHE_TTL = 2  # seconds

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def _build_stats_sql(is_admin: bool) -> str:
    """
    Build ONE single SQL statement that returns all dashboard data.
    This minimizes round-trips to the remote database server for maximum speed.
    """
    if is_admin:
        user_filter = ""
        death_filter = ""
        injured_filter = ""
    else:
        user_filter = "WHERE fd.user_id = :uid"
        death_filter = "JOIN bdds_dashboard_form_data fd2 ON dp.form_id = fd2.id WHERE fd2.user_id = :uid"
        injured_filter = "JOIN bdds_dashboard_form_data fd3 ON ip.form_id = fd3.id WHERE fd3.user_id = :uid"

    return f"""
    SELECT
        -- Form counts (all in one pass)
        COUNT(fd.id) AS total_case,
        SUM(CASE WHEN fd.radio_data = 'Exploded' THEN 1 ELSE 0 END) AS total_exposed,
        SUM(CASE WHEN fd.radio_data = 'Detected' OR fd.radio_data = 'Incident Logged' OR fd.radio_data IS NULL THEN 1 ELSE 0 END) AS total_detected,
        -- Death/Injured (subqueries)
        (SELECT COUNT(*) FROM bdds_dashboard_death_person dp {death_filter}) AS total_death,
        (SELECT COUNT(*) FROM bdds_dashboard_injured_person ip {injured_filter}) AS total_injured,
        -- Global master counts
        (SELECT COUNT(*) FROM bdds_dashboard_n_incident) AS total_incident,
        (SELECT COUNT(*) FROM bdds_dashboard_n_location) AS total_location,
        (SELECT COUNT(*) FROM bdds_dashboard_n_dalam) AS total_dalam
    FROM bdds_dashboard_form_data fd
    {user_filter}
    """


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Ultra-optimized: ALL counts in 1 query + 60s in-memory cache.
    First call: ~3s (network). Subsequent calls: <50ms (cached).
    """
    is_admin = bool(current_user.is_superuser)
    uid = current_user.id
    cache_key = "admin" if is_admin else f"user_{uid}"

    # Return cached response if fresh
    cached = _stats_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL:
        return cached["data"]

    # ── SINGLE QUERY for all counts ──
    counts_sql = text(_build_stats_sql(is_admin))
    counts = (await db.execute(counts_sql, {"uid": uid})).one()

    # ── Jurisdiction Top 5 ──
    if is_admin:
        jur_sql = text("""
            SELECT j.l_juridiction, COUNT(fd.id) AS cnt
            FROM bdds_dashboard_n_juridiction j
            JOIN bdds_dashboard_form_data fd ON fd.fjuridiction_id = j.id
            GROUP BY j.l_juridiction ORDER BY cnt DESC LIMIT 5
        """)
        jur_results = (await db.execute(jur_sql)).all()
        
        loc_sql = text("""
            SELECT l.l_location, COUNT(fd.id) AS cnt
            FROM bdds_dashboard_n_location l
            JOIN bdds_dashboard_form_data fd ON fd.flocation_type_id = l.id
            GROUP BY l.l_location ORDER BY cnt DESC LIMIT 5
        """)
        loc_results = (await db.execute(loc_sql)).all()
    else:
        jur_sql = text("""
            SELECT j.l_juridiction, COUNT(fd.id) AS cnt
            FROM bdds_dashboard_n_juridiction j
            JOIN bdds_dashboard_form_data fd ON fd.fjuridiction_id = j.id
            WHERE fd.user_id = :uid
            GROUP BY j.l_juridiction ORDER BY cnt DESC LIMIT 5
        """)
        jur_results = (await db.execute(jur_sql, {"uid": uid})).all()

        loc_sql = text("""
            SELECT l.l_location, COUNT(fd.id) AS cnt
            FROM bdds_dashboard_n_location l
            JOIN bdds_dashboard_form_data fd ON fd.flocation_type_id = l.id
            WHERE fd.user_id = :uid
            GROUP BY l.l_location ORDER BY cnt DESC LIMIT 5
        """)
        loc_results = (await db.execute(loc_sql, {"uid": uid})).all()

    # ── Monthly Timeline ──
    if is_admin:
        month_sql = text("""
            SELECT DATE_FORMAT(fdate, '%b %Y') AS m, COUNT(id) AS total
            FROM bdds_dashboard_form_data
            GROUP BY m ORDER BY MIN(fdate)
        """)
        month_results = (await db.execute(month_sql)).all()
        
        week_sql = text("""
            SELECT DATE_FORMAT(fdate, '%x-W%v') AS w, COUNT(id) AS total
            FROM bdds_dashboard_form_data
            GROUP BY w ORDER BY MIN(fdate)
        """)
        week_results = (await db.execute(week_sql)).all()
    else:
        month_sql = text("""
            SELECT DATE_FORMAT(fdate, '%b %Y') AS m, COUNT(id) AS total
            FROM bdds_dashboard_form_data
            WHERE user_id = :uid
            GROUP BY m ORDER BY MIN(fdate)
        """)
        month_results = (await db.execute(month_sql, {"uid": uid})).all()

        week_sql = text("""
            SELECT DATE_FORMAT(fdate, '%x-W%v') AS w, COUNT(id) AS total
            FROM bdds_dashboard_form_data
            WHERE user_id = :uid
            GROUP BY w ORDER BY MIN(fdate)
        """)
        week_results = (await db.execute(week_sql, {"uid": uid})).all()

    result = {
        "total_case": counts.total_case or 0,
        "total_exposed": int(counts.total_exposed or 0),
        "total_detected": int(counts.total_detected or 0),
        "total_death": counts.total_death or 0,
        "total_injured": counts.total_injured or 0,
        "total_incident": counts.total_incident or 0,
        "total_location": counts.total_location or 0,
        "total_dalam": counts.total_dalam or 0,
        "jur_labels": [r[0] for r in jur_results],
        "jur_counts": [r[1] for r in jur_results],
        "loc_labels": [r[0] for r in loc_results],
        "loc_counts": [r[1] for r in loc_results],
        "month_labels": [r[0] for r in month_results],
        "month_counts": [r[1] for r in month_results],
        "week_labels": [r[0] for r in week_results],
        "week_counts": [r[1] for r in week_results]
    }

    # Cache the result
    _stats_cache[cache_key] = {"data": result, "ts": time.time()}
    return result


from sqlalchemy.orm import joinedload

@router.get("/forms")
async def list_dashboard_forms(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    # Enforce maximum limit of 100
    limit = min(limit, 100)
    
    # Base query for total count
    count_stmt = select(Form_data)
    if not current_user.is_superuser:
        count_stmt = count_stmt.filter(Form_data.user_id == current_user.id)
    
    # Base query for items
    stmt = select(Form_data).options(
        joinedload(Form_data.flocation_type),
        joinedload(Form_data.fjuridiction),
        joinedload(Form_data.fincident)
    )
    
    if not current_user.is_superuser:
        stmt = stmt.filter(Form_data.user_id == current_user.id)
        
    if status and status != 'all':
        count_stmt = count_stmt.filter(Form_data.radio_data == status)
        stmt = stmt.filter(Form_data.radio_data == status)

    if search:
        search_filter = f"%{search}%"
        search_cond = (
            (Form_data.fserial.ilike(search_filter)) |
            (Form_data.flocation.ilike(search_filter)) |
            (Form_data.d_bomb.ilike(search_filter))
        )
        count_stmt = count_stmt.filter(search_cond)
        stmt = stmt.filter(search_cond)
        
    stmt = stmt.order_by(Form_data.id.desc()).offset(skip).limit(limit)
    
    # Execute count
    total_result = await db.execute(select(func.count()).select_from(count_stmt.subquery()))
    total = total_result.scalar() or 0

    # Execute items
    result = await db.execute(stmt)
    forms = result.scalars().unique().all()
    
    return {
        "total": total,
        "form_data": [{
            "id": f.id,
            "fserial": f.fserial,
            "d_bomb": f.d_bomb,
            "fdate": f.fdate.strftime("%Y-%m-%d %H:%M:%S") if f.fdate else None,
            "flocation": f.flocation,
            "flocation_description": f.flocation, # For mobile fallback
            "radio_data": f.radio_data,
            "i_data": f.radio_data, # For web fallback
            "user_id": f.user_id,
            "edit_request": f.edit_request,
            "delete_request": f.delete_request,
            "flocation_type": {
                "id": f.flocation_type.id if f.flocation_type else None,
                "name": f.flocation_type.l_location if f.flocation_type else None,
                "l_location": f.flocation_type.l_location if f.flocation_type else None
            } if f.flocation_type else None,
            "fjuridiction": {
                "id": f.fjuridiction.id if f.fjuridiction else None,
                "name": f.fjuridiction.l_juridiction if f.fjuridiction else None,
                "l_juridiction": f.fjuridiction.l_juridiction if f.fjuridiction else None
            } if f.fjuridiction else None,
            "fincident": {
                "id": f.fincident.id if f.fincident else None,
                "name": f.fincident.i_incident if f.fincident else None,
                "i_incident": f.fincident.i_incident if f.fincident else None
            } if f.fincident else None
        } for f in forms]
    }


@router.get("/forms/{id}")
async def get_form_details(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(Form_data).filter(Form_data.id == id)
    result = await db.execute(stmt)
    form = result.scalar_one_or_none()
    
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    if not current_user.is_superuser and form.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Fetch all related data
    img_res = await db.execute(select(images).filter(images.form_id == id))
    rep_res = await db.execute(select(s_report).filter(s_report.form_id == id))
    sk_res = await db.execute(select(sk_report).filter(sk_report.form_id == id))
    death_res = await db.execute(select(death_person).filter(death_person.form_id == id))
    inj_res = await db.execute(select(injured_person).filter(injured_person.form_id == id))
    exp_res = await db.execute(select(exploded).filter(exploded.form_id == id))
    
    # Fetch linked criminals
    crim_stmt = select(CriminalDossier, CriminalLink.role).join(
        CriminalLink, CriminalLink.criminal_id == CriminalDossier.id
    ).filter(CriminalLink.form_id == id)
    crim_res = await db.execute(crim_stmt)
    criminals = [{"id": c.id, "name": c.name, "alias": c.alias, "role": role} for c, role in crim_res.all()]
    
    # Fetch Detection/Dispose/Location names
    detection_name = "N/A"
    dispose_name = "N/A"
    loc_name_resolved = form.flocation
    juridiction_name = "N/A"
    incident_name = "N/A"
    explosive_name = "N/A"
    weight_name = None
    user_display_name = "System"

    if form.flocation_type_id:
        loc_res = await db.execute(select(N_location).where(N_location.id == form.flocation_type_id))
        loc_obj = loc_res.scalar_one_or_none()
        if loc_obj:
            loc_name_resolved = loc_obj.l_location

    if form.fjuridiction_id:
        jur_res = await db.execute(select(N_juridiction).where(N_juridiction.id == form.fjuridiction_id))
        jur_obj = jur_res.scalar_one_or_none()
        if jur_obj:
            juridiction_name = jur_obj.l_juridiction

    if form.fincident_id:
        inc_res = await db.execute(select(N_incident).where(N_incident.id == form.fincident_id))
        inc_obj = inc_res.scalar_one_or_none()
        if inc_obj:
            incident_name = inc_obj.i_incident

    if form.fexplosive_id:
        exp_ent_res = await db.execute(select(N_explosive).where(N_explosive.id == form.fexplosive_id))
        exp_ent_obj = exp_ent_res.scalar_one_or_none()
        if exp_ent_obj:
            explosive_name = exp_ent_obj.e_explosive

    if form.fweight_data_id:
        w_res = await db.execute(select(N_weight).where(N_weight.id == form.fweight_data_id))
        w_obj = w_res.scalar_one_or_none()
        if w_obj:
            weight_name = w_obj.w_weight

    if form.user_id:
        u_res = await db.execute(select(AuthUser).where(AuthUser.id == form.user_id))
        u_obj = u_res.scalar_one_or_none()
        if u_obj:
            user_display_name = u_obj.first_name or u_obj.username

    if getattr(form, 'mode_of_detection_id', None):
        det_res = await db.execute(select(N_ditection).where(N_ditection.id == form.mode_of_detection_id))
        det_obj = det_res.scalar_one_or_none()
        if det_obj:
            detection_name = det_obj.d_ditection
            
    if getattr(form, 'detected_dispose_id', None):
        disp_res = await db.execute(select(N_dispose).where(N_dispose.id == form.detected_dispose_id))
        disp_obj = disp_res.scalar_one_or_none()
        if disp_obj:
            dispose_name = disp_obj.d_dispose

    # Convert model to dict to add extra fields
    form_dict = {col.name: getattr(form, col.name) for col in form.__table__.columns}
    # Do NOT pop flocation_type_id as the frontend might need it
    form_dict['flocation'] = form.flocation # Raw coordinates/data
    form_dict['fdate'] = form.fdate.strftime("%Y-%m-%d %H:%M:%S") if form.fdate else None
    
    # Standardize Master Objects for Frontend
    form_dict['flocation_type'] = {
        "id": loc_obj.id if (loc_obj := (await db.get(N_location, form.flocation_type_id))) else None,
        "l_location": loc_obj.l_location if loc_obj else None,
    } if form.flocation_type_id else None

    form_dict['fjuridiction'] = {
        "id": jur_obj.id if (jur_obj := (await db.get(N_juridiction, form.fjuridiction_id))) else None,
        "l_juridiction": jur_obj.l_juridiction if jur_obj else None,
    } if form.fjuridiction_id else None

    form_dict['fincident'] = {
        "id": inc_obj.id if (inc_obj := (await db.get(N_incident, form.fincident_id))) else None,
        "i_incident": inc_obj.i_incident if inc_obj else None,
    } if form.fincident_id else None

    form_dict['fexplosive'] = {
        "id": exp_ent_obj.id if (exp_ent_obj := (await db.get(N_explosive, form.fexplosive_id))) else None,
        "e_explosive": exp_ent_obj.e_explosive if exp_ent_obj else None,
    } if form.fexplosive_id else None

    form_dict['fweight_data'] = {
        "id": w_obj.id if (w_obj := (await db.get(N_weight, form.fweight_data_id))) else None,
        "w_weight": w_obj.w_weight if w_obj else None,
    } if form.fweight_data_id else None

    form_dict['mode_of_detection'] = {
        "id": det_obj.id if (det_obj := (await db.get(N_ditection, getattr(form, 'mode_of_detection_id', None)))) else None,
        "d_ditection": det_obj.d_ditection if det_obj else None,
    } if getattr(form, 'mode_of_detection_id', None) else None

    form_dict['detected_dispose'] = {
        "id": disp_obj.id if (disp_obj := (await db.get(N_dispose, getattr(form, 'detected_dispose_id', None)))) else None,
        "d_dispose": disp_obj.d_dispose if disp_obj else None,
    } if getattr(form, 'detected_dispose_id', None) else None

    form_dict['mode_of_detection_name'] = detection_name
    form_dict['detected_dispose_name'] = dispose_name
    form_dict['fjuridiction_name'] = juridiction_name
    form_dict['fincident_name'] = incident_name
    form_dict['fexplosive_name'] = explosive_name
    form_dict['fweight_data_name'] = weight_name
    form_dict['user_name'] = user_display_name
    
    return {
        "form_data": [form_dict],
        "image_data": img_res.scalars().all(),
        "reports_data": rep_res.scalars().all(),
        "sketch_data": sk_res.scalars().all(),
        "death_data": death_res.scalars().all(), 
        "injured_data": inj_res.scalars().all(), 
        "explode_data": exp_res.scalars().all(), 
        "criminals": criminals
    }
