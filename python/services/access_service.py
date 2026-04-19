# services/access_service.py
# Core business logic for processing RFID scan events.
# Called by SerialReader (background thread).
# Calls Repository to save data and AnomalyService to analyse.

from sqlalchemy.orm import Session

from core.database import SessionLocal
from schemas.access_log import AccessLogCreate
from repositories.access_log_repo import AccessLogRepository
from services.anomaly_service import AnomalyService
from pydantic import ValidationError


class AccessService:
    # process_scan
    # Main public method — called once per RFID scan event.

    def process_scan(self, uid: str, status: str, event: str) -> None:
        db: Session = SessionLocal()
        try:
            self._run_pipeline(db, uid, status, event)
        except Exception as e:
            print(f"[AccessService] Error processing scan: {e}")
            db.rollback()
        finally:
            db.close()

    def _run_pipeline(
        self, db: Session, uid: str, status: str, event: str
    ) -> None:
        repo = AccessLogRepository(db)
        anomaly_svc = AnomalyService(db)

        # Step 1: Validate via Pydantic schema

        try:
            # log_data = AccessLogCreate(uid=uid, status=status, event=event)
            last = repo.get_last_event_for_uid(uid)

            if status == "allowed":
                if last and last.event == "IN":
                    event = "OUT"
                else:
                    event = "IN"
            else:
                event = "NONE"

            log_data = AccessLogCreate(uid=uid, status=status, event=event)
        except ValidationError as e:
            print(f"[AccessService] Invalid scan data: {e}")
            return

        # Step 2: Persist to DB
        log_entry = repo.create(log_data)
        print(
            f"[AccessService] Saved → id={log_entry.id} "
            f"uid={log_entry.uid} status={log_entry.status} "
            f"event={log_entry.event}"
        )

        # Step 3: Run anomaly detection
        is_anomaly, reason = anomaly_svc.analyse(log_entry)

        # Step 4: Update DB with anomaly result
        if is_anomaly:
            repo.update_anomaly(log_entry.id, True, reason)
            print(f"[AccessService] ⚠ Anomaly flagged: {reason}")

        # Step 5: Confirmation
        print(
            f"[AccessService] ✓ Pipeline complete → "
            f"anomaly={is_anomaly}"
        )