"""
Session — a continuous screen-use period.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Aggregate metrics (computed at session close)
    avg_blink_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_focus_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    break_count: Mapped[int] = mapped_column(Integer, default=0)
    total_break_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Where was this session recorded — laptop, Pi sentinel, etc.
    device_id: Mapped[str] = mapped_column(String, default="laptop")

    metrics = relationship("Metric", back_populates="session", cascade="all, delete-orphan")
