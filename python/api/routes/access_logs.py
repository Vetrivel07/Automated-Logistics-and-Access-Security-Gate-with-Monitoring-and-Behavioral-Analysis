from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, time
from typing import Optional
from sqlalchemy import cast, String

from core.database import get_db
from core.config import settings
from core.user_map import USER_MAP
from repositories.access_log_repo import AccessLogRepository
from services.anomaly_service import AnomalyService
from models.access_log import AccessLog
from schemas.access_log import (
    AccessLogResponse,
    AccessLogSummary,
    DashboardStats,
)

router = APIRouter(prefix="/api", tags=["Access Logs"])


# GET /api/latest
@router.get("/latest", response_model=AccessLogResponse)
def get_latest(db: Session = Depends(get_db)):
    repo = AccessLogRepository(db)
    logs = repo.get_recent(limit=1)
    if not logs:
        raise HTTPException(status_code=404, detail="No logs yet")
    return logs[0]


# GET /api/logs
@router.get("/logs", response_model=list[AccessLogSummary])
def get_recent_logs(
    limit: int = settings.DASHBOARD_RECENT_LOGS_LIMIT,
    db: Session = Depends(get_db),
):
    repo = AccessLogRepository(db)
    return repo.get_recent(limit=limit)


# GET /api/logs/filter
# Filter logs by date and optional time range
@router.get("/logs/filter", response_model=list[AccessLogSummary])
def filter_logs(
    date_from: str = Query(..., description="Start date YYYY-MM-DD"),
    date_to: str   = Query(..., description="End date YYYY-MM-DD"),
    time_from: Optional[str] = Query(None, description="Start time HH:MM"),
    time_to:   Optional[str] = Query(None, description="End time HH:MM"),
    db: Session = Depends(get_db),
):
    try:
        # Parse dates
        d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        d_to   = datetime.strptime(date_to,   "%Y-%m-%d").date()

        # Build datetime range
        if time_from:
            t_from = datetime.strptime(time_from, "%H:%M").time()
        else:
            t_from = time(0, 0, 0)

        if time_to:
            t_to = datetime.strptime(time_to, "%H:%M").time()
        else:
            t_to = time(23, 59, 59)

        dt_from = datetime.combine(d_from, t_from)
        dt_to   = datetime.combine(d_to,   t_to)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date/time format: {e}")

    # Fetch by date range first
    dt_from = datetime.combine(d_from, time(0, 0, 0))
    dt_to   = datetime.combine(d_to,   time(23, 59, 59))

    logs = (
        db.query(AccessLog)
        .filter(
            AccessLog.timestamp >= dt_from,
            AccessLog.timestamp <= dt_to,
        )
        .order_by(AccessLog.timestamp.desc())
        .limit(200)
        .all()
    )

    # Apply time filter in Python (SQLite doesn't support time comparison well)
    if time_from or time_to:
        t_from = datetime.strptime(time_from, "%H:%M").time() if time_from else time(0, 0, 0)
        t_to   = datetime.strptime(time_to,   "%H:%M").time() if time_to   else time(23, 59, 59)
        logs   = [l for l in logs if t_from <= l.timestamp.time() <= t_to]

    return logs


# GET /api/logs/{log_id}
@router.get("/logs/{log_id}", response_model=AccessLogResponse)
def get_log_by_id(log_id: int, db: Session = Depends(get_db)):
    repo = AccessLogRepository(db)
    log = repo.get_by_id(log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return log


# GET /api/logs/user/{uid}
@router.get("/logs/user/{uid}", response_model=list[AccessLogSummary])
def get_logs_by_uid(uid: str, db: Session = Depends(get_db)):
    repo = AccessLogRepository(db)
    return repo.get_by_uid(uid.upper())


# GET /api/anomalies
@router.get("/anomalies", response_model=list[AccessLogResponse])
def get_anomalies(db: Session = Depends(get_db)):
    repo = AccessLogRepository(db)
    return repo.get_anomalies()


# GET /api/stats — all time
@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    repo = AccessLogRepository(db)
    return DashboardStats(
        total_scans=repo.count_total(),
        total_allowed=repo.count_by_status("allowed"),
        total_denied=repo.count_by_status("denied"),
        total_anomalies=repo.count_anomalies(),
        unique_users=repo.count_unique_users(),
    )


# GET /api/stats/today — today only (resets at midnight)
@router.get("/stats/today")
def get_stats_today(db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), time(0, 0, 0))
    today_end   = datetime.now()

    total   = db.query(func.count(AccessLog.id)).filter(
        AccessLog.timestamp >= today_start,
        AccessLog.timestamp <= today_end,
    ).scalar() or 0

    allowed = db.query(func.count(AccessLog.id)).filter(
        AccessLog.timestamp >= today_start,
        AccessLog.timestamp <= today_end,
        AccessLog.status == "allowed",
    ).scalar() or 0

    denied = db.query(func.count(AccessLog.id)).filter(
        AccessLog.timestamp >= today_start,
        AccessLog.timestamp <= today_end,
        AccessLog.status == "denied",
    ).scalar() or 0

    anomalies = db.query(func.count(AccessLog.id)).filter(
        AccessLog.timestamp >= today_start,
        AccessLog.timestamp <= today_end,
        AccessLog.is_anomaly == True,  # noqa: E712
    ).scalar() or 0

    unique = db.query(func.count(func.distinct(AccessLog.uid))).filter(
        AccessLog.timestamp >= today_start,
        AccessLog.timestamp <= today_end,
    ).scalar() or 0

    return {
        "date":           date.today().isoformat(),
        "total_scans":    total,
        "total_allowed":  allowed,
        "total_denied":   denied,
        "total_anomalies": anomalies,
        "unique_users":   unique,
    }


# GET /api/users
@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    rows = db.query(AccessLog.uid).distinct().all()
    users = []
    for (uid,) in rows:
        logs    = db.query(AccessLog).filter(AccessLog.uid == uid).all()
        allowed = sum(1 for l in logs if l.status == "allowed")
        denied  = sum(1 for l in logs if l.status == "denied")
        last    = max((l.timestamp for l in logs), default=None)
        users.append({
            "uid":       uid,
            "name":      USER_MAP.get(uid, uid),
            "total":     len(logs),
            "allowed":   allowed,
            "denied":    denied,
            "last_seen": last.isoformat() if last else None,
        })
    users.sort(key=lambda u: u["total"], reverse=True)
    return users


# GET /api/behaviour/{uid}
@router.get("/behaviour/{uid}")
def get_behaviour(uid: str, db: Session = Depends(get_db)):
    svc    = AnomalyService(db)
    result = svc.get_user_behaviour_summary(uid.upper())
    result["name"] = USER_MAP.get(uid.upper(), uid.upper())
    return result