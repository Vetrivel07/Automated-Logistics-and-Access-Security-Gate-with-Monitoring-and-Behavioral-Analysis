# Anomaly detection service.
# Two-layer approach:
#   Layer 1 — Rule-based (fast, always runs)
#   Layer 2 — Isolation Forest ML (runs when enough data exists)

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from core.config import settings
from models.access_log import AccessLog
from repositories.access_log_repo import AccessLogRepository


class AnomalyService:

    def __init__(self, db: Session) -> None:
        self._repo = AccessLogRepository(db)

    # PUBLIC: analyse
    # Main entry point — called by AccessService after every log entry.
    # Returns (is_anomaly: bool, reason: str | None)

    def analyse(self, log: AccessLog) -> tuple[bool, Optional[str]]:
        # Layer 1: Rule-based checks (always run, zero cost)
        rule_result, rule_reason = self._run_rule_checks(log)
        if rule_result:
            return True, rule_reason

        # Layer 2: Isolation Forest (only if enough history exists)
        ml_result, ml_reason = self._run_isolation_forest(log)
        if ml_result:
            return True, ml_reason

        return False, None

    # LAYER 1 — Rule-based detection

    def _run_rule_checks(
        self, log: AccessLog
    ) -> tuple[bool, Optional[str]]:
        checks = [
            self._check_off_hours,
            self._check_rapid_scans,
            self._check_denied_streak,
        ]
        for check in checks:
            flagged, reason = check(log)
            if flagged:
                return True, reason
        return False, None

    def _check_off_hours(
        self, log: AccessLog
    ) -> tuple[bool, Optional[str]]:
        hour = log.timestamp.hour
        start = settings.ANOMALY_HOUR_START
        end = settings.ANOMALY_HOUR_END

        if hour < start or hour >= end:
            reason = (
                f"Scan at off-hours: {hour:02d}:xx "
                f"(allowed window {start:02d}:00–{end:02d}:00)"
            )
            return True, reason
        return False, None

    def _check_rapid_scans(
        self, log: AccessLog
    ) -> tuple[bool, Optional[str]]:
        window = settings.ANOMALY_RAPID_SCAN_WINDOW
        limit = settings.ANOMALY_RAPID_SCAN_LIMIT

        recent_scans = self._repo.get_scans_in_window(log.uid, window)

        if len(recent_scans) >= limit:
            reason = (
                f"Rapid scan detected: {len(recent_scans)} scans "
                f"within {window}s (limit: {limit})"
            )
            return True, reason
        return False, None

    def _check_denied_streak(
        self, log: AccessLog
    ) -> tuple[bool, Optional[str]]:
        history = self._repo.get_by_uid(log.uid, limit=5)

        if len(history) < 3:
            return False, None

        # Check last 3 entries (already ordered newest first)
        last_three = history[:3]
        if all(entry.status == "denied" for entry in last_three):
            reason = "Consecutive denied streak: 3+ failed attempts"
            return True, reason

        return False, None

    # LAYER 2 — Isolation Forest (ML)

    def _run_isolation_forest(
        self, log: AccessLog
    ) -> tuple[bool, Optional[str]]:
        history = self._repo.get_all_for_uid_analysis(log.uid)

        # Need minimum data to train a meaningful model
        if len(history) < 10:
            return False, None

        try:
            from sklearn.ensemble import IsolationForest
            import numpy as np

            # Feature: hour of day (0–23) as float
            # Simple but effective for detecting time-based anomalies
            hours = np.array(
                [entry.timestamp.hour for entry in history]
            ).reshape(-1, 1)

            # Train on all history except the current entry
            training_data = hours[:-1]

            model = IsolationForest(
                contamination=0.1,   # expect ~10% anomalies
                random_state=42,
            )
            model.fit(training_data)

            # Predict on current scan's hour
            current_hour = np.array([[log.timestamp.hour]])
            prediction = model.predict(current_hour)

            # IsolationForest: -1 = anomaly, 1 = normal
            if prediction[0] == -1:
                reason = (
                    f"ML anomaly (Isolation Forest): "
                    f"scan at hour {log.timestamp.hour:02d} "
                    f"is unusual for this user's pattern"
                )
                return True, reason

        except ImportError:
            # scikit-learn not installed — skip ML layer silently
            pass
        except Exception:
            # Never crash the main flow due to ML failure
            pass

        return False, None

    # PUBLIC: get_user_behaviour_summary
    # Returns basic analytics dict for a given UID.
    # Used by dashboard behavior analysis endpoint.

    def get_user_behaviour_summary(self, uid: str) -> dict:
        history = self._repo.get_all_for_uid_analysis(uid)

        if not history:
            return {"uid": uid, "total_scans": 0, "message": "No data"}

        # Entry times (hour of day for IN events)
        entry_hours = [
            e.timestamp.hour
            for e in history
            if e.event == "IN"
        ]

        # Average entry hour
        avg_entry_hour = (
            sum(entry_hours) / len(entry_hours) if entry_hours else None
        )

        # Scan frequency per day
        if len(history) > 1:
            first = history[0].timestamp
            last = history[-1].timestamp
            days = max((last - first).days, 1)
            frequency_per_day = round(len(history) / days, 2)
        else:
            frequency_per_day = 1.0

        # Stay durations (time between consecutive IN and OUT pairs)
        stay_durations = self._compute_stay_durations(history)

        return {
            "uid": uid,
            "total_scans": len(history),
            "total_in": len([e for e in history if e.event == "IN"]),
            "total_out": len([e for e in history if e.event == "OUT"]),
            "average_entry_hour": avg_entry_hour,
            "frequency_per_day": frequency_per_day,
            "stay_durations_minutes": stay_durations,
            "anomaly_count": len([e for e in history if e.is_anomaly]),
        }

    def _compute_stay_durations(
        self, history: list[AccessLog]
    ) -> list[float]:
        durations: list[float] = []
        pending_in: Optional[datetime] = None

        # history is ordered oldest-first from get_all_for_uid_analysis
        for entry in history:
            if entry.event == "IN":
                pending_in = entry.timestamp
            elif entry.event == "OUT" and pending_in is not None:
                delta = (entry.timestamp - pending_in).total_seconds()
                durations.append(round(delta / 60, 2))
                pending_in = None

        return durations