"""
Metric — a 5-second aggregated snapshot within a session.
"""
from datetime import datetime
from sqlalchemy import Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Eye / focus
    blink_rate: Mapped[float] = mapped_column(Float)  # blinks/min, windowed
    focus_score: Mapped[float] = mapped_column(Float)  # 0–100
    head_stability: Mapped[float] = mapped_column(Float)  # 0–1
    screen_distance_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    eye_on_screen: Mapped[bool] = mapped_column(Boolean, default=True)

    session = relationship("Session", back_populates="metrics")
