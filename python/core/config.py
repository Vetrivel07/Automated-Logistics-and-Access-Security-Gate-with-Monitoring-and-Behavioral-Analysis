# Central configuration — all constants and settings live here.
# Change COM port, baud rate, DB path, and gate settings here.

from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    # Application
    APP_NAME: str = "Security Gate System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Serial (Arduino)
    # Change SERIAL_PORT to match your Arduino COM port.
    SERIAL_PORT: str = "COM3"
    SERIAL_BAUD_RATE: int = 9600
    SERIAL_TIMEOUT: int = 2          # seconds
    SERIAL_RECONNECT_DELAY: int = 5  # seconds before retry on disconnect

    # Serial message markers (must match Arduino code)
    # Arduino sends: <{"uid":"...","status":"...","event":"..."}>
    MSG_START_MARKER: str = "<"
    MSG_END_MARKER: str = ">"

    # Database
    DATABASE_URL: str = "sqlite:///./access_logs.db"

    # Anomaly Detection Rules
    ANOMALY_HOUR_START: int = 10    # scans before 10AM = suspicious
    ANOMALY_HOUR_END: int = 15     # scans after 3PM = suspicious
    ANOMALY_RAPID_SCAN_LIMIT: int = 5    # max scans per window
    ANOMALY_RAPID_SCAN_WINDOW: int = 60  # seconds for rapid scan window

    # Dashboard
    DASHBOARD_RECENT_LOGS_LIMIT: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton instance — import this everywhere
settings = Settings()