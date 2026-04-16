"""
Application configuration — loaded from environment or .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Camera
    camera_index: int = 0
    target_fps: int = 15
    show_preview: bool = False

    # CV / blink detection
    # EAR = Eye Aspect Ratio. Lower = eyes more closed.
    # 0.20 is a reasonable starting point; calibrate per user.
    ear_threshold: float = 0.20
    ear_consec_frames: int = 2

    # Session management
    session_idle_timeout_seconds: int = 120

    # Focus scoring — healthy screen-user blink range
    healthy_blink_rate_min: float = 12.0
    healthy_blink_rate_max: float = 22.0

    # 20-20-20 rule
    break_interval_seconds: int = 20 * 60  # 20 minutes
    break_duration_seconds: int = 20

    # Metric emission — how often to snapshot + broadcast
    metric_interval_seconds: int = 5

    # Database
    database_url: str = "sqlite:///./screyn.db"


settings = Settings()
