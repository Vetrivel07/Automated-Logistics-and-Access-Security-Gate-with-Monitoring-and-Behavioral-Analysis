from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.config import settings
from core.database import init_db
from api.routes.access_logs import router as logs_router
from serial_comm.serial_reader import SerialReader


# Serial reader instance (singleton, started at app startup)
serial_reader = SerialReader()


# Lifespan — startup and shutdown events
# Replaces deprecated @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    print(f"[Main] Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # 1. Create DB tables
    init_db()
    print("[Main] Database initialized.")

    # 2. Start serial background thread
    serial_reader.start()
    print(f"[Main] Serial reader started on {settings.SERIAL_PORT}")

    yield  # Application runs here

    # ── SHUTDOWN ──
    serial_reader.stop()
    print("[Main] Serial reader stopped. Shutdown complete.")


# FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Static files — serve dashboard assets
# Mount BEFORE routes so /dashboard/* is served correctly.
app.mount(
    "/dashboard",
    StaticFiles(directory="dashboard", html=True),
    name="dashboard",
)

# API routes
app.include_router(logs_router)


# Root redirect → dashboard
@app.get("/", include_in_schema=False)
def root():
    """Redirect root to the dashboard."""
    return FileResponse("dashboard/index.html")


# Health check
@app.get("/health", tags=["System"])
def health():
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "serial_port": settings.SERIAL_PORT,
    }