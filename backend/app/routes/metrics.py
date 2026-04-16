"""
Metric endpoints — per-session time-series + recent activity.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models.metric import Metric
from app.models.session import Session
from app.schemas.session import MetricOut

router = APIRouter()


@router.get("/session/{session_id}", response_model=list[MetricOut])
def metrics_for_session(
    session_id: int,
    db: DBSession = Depends(get_db),
):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    metrics = (
        db.query(Metric)
        .filter(Metric.session_id == session_id)
        .order_by(Metric.timestamp.asc())
        .all()
    )
    return metrics


@router.get("/recent", response_model=list[MetricOut])
def recent_metrics(
    limit: int = Query(100, ge=1, le=1000),
    db: DBSession = Depends(get_db),
):
    """Most recent metrics across all sessions, newest first."""
    metrics = (
        db.query(Metric)
        .order_by(Metric.timestamp.desc())
        .limit(limit)
        .all()
    )
    return metrics
