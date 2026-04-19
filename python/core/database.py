# SQLAlchemy engine and session management.
# Singleton pattern — one engine, one session factory shared
# across the entire application (serial thread + API thread).

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from core.config import settings


# Base class for all ORM models
# All models in models/ inherit from this.
class Base(DeclarativeBase):
    pass


# Singleton Engine
# connect_args check_same_thread=False is required for SQLite
# when used across multiple threads (serial + FastAPI).
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Session Factory
# Each thread/request creates a session from this factory.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# init_db()
# Creates all tables defined in ORM models.
# Called once at startup from main.py.
def init_db() -> None:
    """
    Import all models before calling create_all so SQLAlchemy
    can discover them via the Base metadata.
    """
    from models import access_log  # noqa: F401 — registers model
    Base.metadata.create_all(bind=engine)


# get_db()
# Dependency for FastAPI routes.
# Yields a session and guarantees it is closed after each request.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()