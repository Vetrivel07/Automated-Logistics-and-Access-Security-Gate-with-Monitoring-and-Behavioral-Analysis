from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models.access_log import AccessLog
from schemas.access_log import AccessLogCreate


class AccessLogRepository:

    def __init__(self, db: Session) -> None:
        self._db = db

    # CREATE
    def create(self, data: AccessLogCreate) -> AccessLog:
        log = AccessLog(
            uid=data.uid,
            status=data.status,
            event=data.event,
            timestamp=datetime.now(),  
        )
        self._db.add(log)
        self._db.commit()
        self._db.refresh(log)
        return log

    def update_anomaly(
        self,
        log_id: int,
        is_anomaly: bool,
        reason: Optional[str] = None,
    ) -> Optional[AccessLog]:
        log = self._db.get(AccessLog, log_id)
        if log is None:
            return None
        log.is_anomaly = is_anomaly
        log.anomaly_reason = reason
        self._db.commit()
        self._db.refresh(log)
        return log

    # READ — single record

    def get_by_id(self, log_id: int) -> Optional[AccessLog]:
        return self._db.get(AccessLog, log_id)

    def get_last_event_for_uid(self, uid: str) -> Optional[AccessLog]:
        return (
            self._db.query(AccessLog)
            .filter(AccessLog.uid == uid)
            .order_by(desc(AccessLog.timestamp))
            .first()
        )

    # READ — collections

    def get_recent(self, limit: int = 50) -> list[AccessLog]:
        return (
            self._db.query(AccessLog)
            .order_by(desc(AccessLog.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_uid(self, uid: str, limit: int = 100) -> list[AccessLog]:
        return (
            self._db.query(AccessLog)
            .filter(AccessLog.uid == uid)
            .order_by(desc(AccessLog.timestamp))
            .limit(limit)
            .all()
        )

    def get_anomalies(self, limit: int = 50) -> list[AccessLog]:
        return (
            self._db.query(AccessLog)
            .filter(AccessLog.is_anomaly == True)  # noqa: E712
            .order_by(desc(AccessLog.timestamp))
            .limit(limit)
            .all()
        )

    def get_scans_in_window(
        self, uid: str, window_seconds: int
    ) -> list[AccessLog]:
        cutoff = datetime.now() - timedelta(seconds=window_seconds)  # ← local time
        return (
            self._db.query(AccessLog)
            .filter(
                AccessLog.uid == uid,
                AccessLog.timestamp >= cutoff,
            )
            .order_by(desc(AccessLog.timestamp))
            .all()
        )

    def get_all_for_uid_analysis(self, uid: str) -> list[AccessLog]:
        return (
            self._db.query(AccessLog)
            .filter(AccessLog.uid == uid)
            .order_by(AccessLog.timestamp)
            .all()
        )

    # AGGREGATES

    def count_total(self) -> int:
        return self._db.query(func.count(AccessLog.id)).scalar() or 0

    def count_by_status(self, status: str) -> int:
        return (
            self._db.query(func.count(AccessLog.id))
            .filter(AccessLog.status == status)
            .scalar() or 0
        )

    def count_anomalies(self) -> int:
        return (
            self._db.query(func.count(AccessLog.id))
            .filter(AccessLog.is_anomaly == True)  # noqa: E712
            .scalar() or 0
        )

    def count_unique_users(self) -> int:
        return (
            self._db.query(func.count(func.distinct(AccessLog.uid)))
            .scalar() or 0
        )