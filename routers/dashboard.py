from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text
from database import get_db
from models import (
    Form_data, AuthUser, death_person, injured_person, exploded,
    images, s_report, sk_report, CriminalDossier, CriminalLink,
    N_ditection, N_dispose
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
        SUM(CASE WHEN fd.radio_data = 'Detected' THEN 1 ELSE 0 END) AS total_detected,
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
    else:
        jur_sql = text("""
            SELECT j.l_juridiction, COUNT(fd.id) AS cnt
            FROM bdds_dashboard_n_juridiction j
            JOIN bdds_dashboard_form_data fd ON fd.fjuridiction_id = j.id
            WHERE fd.user_id = :uid
            GROUP BY j.l_juridiction ORDER BY cnt DESC LIMIT 5
        """)
        jur_results = (await db.execute(jur_sql, {"uid": uid})).all()

    # ── Monthly Timeline ──
    if is_admin:
        month_sql = text("""
            SELECT DATE_FORMAT(fdate, '%b %Y') AS m, COUNT(id) AS total
            FROM bdds_dashboard_form_data
            GROUP BY m ORDER BY MIN(fdate)
        """)
        month_results = (await db.execute(month_sql)).all()
    else:
        month_sql = text("""
            SELECT DATE_FORMAT(fdate, '%b %Y') AS m, COUNT(id) AS total
            FROM bdds_dashboard_form_data
            WHERE user_id = :uid
            GROUP BY m ORDER BY MIN(fdate)
        """)
        month_results = (await db.execute(month_sql, {"uid": uid})).all()

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
        "month_labels": [r[0] for r in month_results],
        "month_counts": [r[1] for r in month_results]
    }

    # Cache the result
    _stats_cache[cache_key] = {"data": result, "ts": time.time()}
    return result


@router.get("/forms")
async def list_dashboard_forms(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    # Enforce maximum limit of 25
    limit = min(limit, 25)
    
    # ── 1. Get Total Count (for pagination) ──
    count_stmt = select(func.count()).select_from(Form_data)
    if not current_user.is_superuser:
        count_stmt = count_stmt.filter(Form_data.user_id == current_user.id)
    
    total_count = (await db.execute(count_stmt)).scalar() or 0
    
    # ── 2. Get Paginated Data ──
    stmt = select(Form_data)
    if not current_user.is_superuser:
        stmt = stmt.filter(Form_data.user_id == current_user.id)
    
    # Sorting by date desc to show newest first
    stmt = stmt.order_by(Form_data.fdate.desc()).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    forms = result.scalars().all()
    
    return {
        "items": [{
            "id": f.id,
            "fserial": f.fserial,
            "d_bomb": f.d_bomb,
            "fdate": f.fdate,
            "flocation": f.flocation,
            "radio_data": f.radio_data, # Added for frontend status display
            "user": f.user_id,
            "edit_request": f.edit_request,
            "delete_request": f.delete_request
        } for f in forms],
        "total": total_count
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
    
    # Fetch Detection names
    detection_name = "N/A"
    dispose_name = "N/A"
    
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
    form_dict['mode_of_detection_name'] = detection_name
    form_dict['detected_dispose_name'] = dispose_name
    
    return {
        "form_data": [form_dict], # list for frontend compat
        "image_data": img_res.scalars().all(),
        "reports_data": rep_res.scalars().all(),
        "sketch_data": sk_res.scalars().all(),
        "death_data": death_res.scalars().all(),
        "injured_data": inj_res.scalars().all(),
        "explode_data": exp_res.scalars().all(),
        "criminals": criminals
    }
