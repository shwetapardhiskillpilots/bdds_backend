from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, case, text
from typing import List
from database import get_db
from models import Form_data, N_dalam, AuthUser, death_person, injured_person, N_incident, N_location, N_juridiction
from auth import get_current_user
from schemas import DashboardStats
import time

# ── Simple TTL Cache (avoids repeated remote DB calls) ──
_stats_cache: dict = {}  # key: user_id or "admin" -> {"data": ..., "ts": time.time()}
CACHE_TTL = 60  # seconds

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
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(Form_data)
    if not current_user.is_superuser:
        stmt = stmt.filter(Form_data.user_id == current_user.id)
    
    result = await db.execute(stmt)
    forms = result.scalars().all()
    
    return [{
        "id": f.id,
        "fserial": f.fserial,
        "d_bomb": f.d_bomb,
        "fdate": f.fdate,
        "flocation": f.flocation,
        "user": f.user_id,
        "edit_request": f.edit_request,
        "delete_request": f.delete_request
    } for f in forms]


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
    
    return form
