"""
Pydantic schemas for API responses.
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    timestamp: datetime
    blink_rate: float
    focus_score: float
    head_stability: float
    screen_distance_cm: float | None
    eye_on_screen: bool


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_time: datetime
    end_time: datetime | None
    duration_seconds: int | None
    avg_blink_rate: float | None
    avg_focus_score: float | None
    break_count: int
    total_break_seconds: int
    device_id: str


class LiveFrame(BaseModel):
    """Payload broadcast over WebSocket every N seconds."""
    timestamp: datetime
    session_id: int | None
    face_detected: bool
    blink_rate: float
    focus_score: float
    head_stability: float
    screen_distance_cm: float | None
    seconds_since_break: int
    total_blinks_this_session: int
    active_seconds: int      # session elapsed time
    break_due: bool          # 20+ minutes since last break
    calibrating: bool = False          # currently running auto-calibration
    calibration_progress: float = 1.0  # 0.0 to 1.0 during calibration