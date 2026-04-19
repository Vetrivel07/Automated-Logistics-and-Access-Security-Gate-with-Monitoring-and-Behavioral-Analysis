# Pydantic schemas for request validation and API responses.
# Separates API data shapes from ORM models (clean architecture).

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


# AccessLogCreate
# Schema for creating a new log entry.
# Used by AccessService when processing a serial message.
class AccessLogCreate(BaseModel):
    uid: str
    status: str
    event: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"allowed", "denied"}
        if v.lower() not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v.lower()

    @field_validator("event")
    @classmethod
    def validate_event(cls, v: str) -> str:
        allowed = {"IN", "OUT", "NONE"}
        if v.upper() not in allowed:
            raise ValueError(f"event must be one of {allowed}")
        return v.upper()

    @field_validator("uid")
    @classmethod
    def validate_uid(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("uid cannot be empty")
        return v


# AccessLogResponse
# Schema returned by API endpoints.
# Maps ORM model fields to JSON response shape.
class AccessLogResponse(BaseModel):
    id: int
    uid: str
    status: str
    event: str
    timestamp: datetime
    is_anomaly: bool
    anomaly_reason: Optional[str]

    model_config = {"from_attributes": True}


# AccessLogSummary
# Lightweight schema for dashboard recent-logs list.
class AccessLogSummary(BaseModel):
    id: int
    uid: str
    status: str
    event: str
    timestamp: datetime
    is_anomaly: bool

    model_config = {"from_attributes": True}


# DashboardStats
# Aggregated stats returned for the dashboard overview panel.
class DashboardStats(BaseModel):
    total_scans: int
    total_allowed: int
    total_denied: int
    total_anomalies: int
    unique_users: int