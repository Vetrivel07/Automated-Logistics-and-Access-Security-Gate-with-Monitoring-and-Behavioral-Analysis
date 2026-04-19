from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class AccessLog(Base):
    """
    ORM model representing one RFID scan event.

    Table: access_logs
    ----------------------------------------------------------
    id             | Auto-increment primary key
    uid            | RFID card UID (e.g. "A3 B4 C1 D9")
    status         | "allowed" or "denied"
    event          | "IN", "OUT", or "NONE" (denied = NONE)
    timestamp      | LOCAL datetime of the scan
    is_anomaly     | True if flagged by anomaly detection
    anomaly_reason | Text description of why it was flagged
    ----------------------------------------------------------
    Note: datetime.now() used (local time) — NOT utcnow()
    """

    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    uid: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    event: Mapped[str] = mapped_column(
        String(4), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now  # local time
    )
    is_anomaly: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    anomaly_reason: Mapped[str] = mapped_column(
        String(200), nullable=True, default=None
    )

    def __repr__(self) -> str:
        return (
            f"<AccessLog id={self.id} uid={self.uid} "
            f"status={self.status} event={self.event} "
            f"timestamp={self.timestamp}>"
        )