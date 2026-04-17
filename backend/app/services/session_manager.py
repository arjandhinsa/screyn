"""
Session manager — the orchestrator.

Break model: after 20 minutes of session time, break_due becomes true and the
frontend shows a prompt. When the user clicks Done on the prompt, the frontend
POSTs to /sessions/take-break which resets the break timer.
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Set

from fastapi import WebSocket

from app.config import settings
from app.database import SessionLocal
from app.models.metric import Metric
from app.models.session import Session as SessionModel
from app.schemas.session import LiveFrame
from app.services.blink_detector import BlinkDetector
from app.services.camera import camera
from app.services.cv_pipeline import CVPipeline
from app.services.focus_scorer import FocusInputs, FocusSmoother, compute_focus_score
from app.services.calibration import calibrator

logger = logging.getLogger(__name__)


class SessionManager:
    """Central CV + session loop. Singleton."""

    def __init__(self):
        self._pipeline: Optional[CVPipeline] = None
        self._blink_detector = BlinkDetector()
        self._focus_smoother = FocusSmoother()

        self._current_session_id: Optional[int] = None
        self._session_started_at: Optional[float] = None
        self._last_face_time: Optional[float] = None
        self._last_break_time: Optional[float] = None

        self._break_count: int = 0
        self._total_break_seconds: int = 0
        self._active_seconds: float = 0.0

        self._metric_buffer: list[dict] = []

        self._cv_task: Optional[asyncio.Task] = None
        self._metric_task: Optional[asyncio.Task] = None
        self._running = False

        self._subscribers: Set[WebSocket] = set()
        self._latest_live_frame: Optional[LiveFrame] = None

    @property
    def camera_active(self) -> bool:
        return camera.is_running

    @property
    def current_session_id(self) -> Optional[int]:
        return self._current_session_id

    async def start(self):
        if self._running:
            return
        if not camera.start():
            logger.error("SessionManager could not start camera")
            return
        self._pipeline = CVPipeline()
        # Auto-calibrate on first launch if no existing calibration
        existing = calibrator.load_existing()
        if existing:
            settings.ear_threshold = existing.threshold
            self._blink_detector.ear_threshold = existing.threshold
            logger.info(f"Loaded calibration: threshold={existing.threshold}")
        else:
            calibrator.start()
            logger.info("No calibration found — starting auto-calibration")
        self._last_break_time = time.time()
        self._running = True
        self._cv_task = asyncio.create_task(self._cv_loop())
        self._metric_task = asyncio.create_task(self._metric_loop())
        logger.info("SessionManager started")

    async def stop(self):
        self._running = False
        if self._cv_task:
            self._cv_task.cancel()
        if self._metric_task:
            self._metric_task.cancel()
        await self._close_current_session()
        camera.stop()
        if self._pipeline:
            self._pipeline.close()
        logger.info("SessionManager stopped")

    async def subscribe(self, ws: WebSocket):
        await ws.accept()
        self._subscribers.add(ws)
        if self._latest_live_frame:
            await self._safe_send(ws, self._latest_live_frame)

    def unsubscribe(self, ws: WebSocket):
        self._subscribers.discard(ws)

    def acknowledge_break(self) -> dict:
        """Called when user clicks Done on the break prompt."""
        if self._current_session_id is None:
            return {"status": "no_active_session"}
        self._break_count += 1
        self._total_break_seconds += 20
        self._last_break_time = time.time()
        logger.info(f"Break acknowledged (total: {self._break_count})")
        return {
            "status": "ok",
            "break_count": self._break_count,
            "total_break_seconds": self._total_break_seconds,
        }

    async def _cv_loop(self):
        try:
            while self._running:
                frame = await camera.get_latest_frame()
                if frame is None:
                    await asyncio.sleep(0.05)
                    continue

                features = self._pipeline.process_frame(frame)
                now = time.time()

                if features.face_detected:
                    self._last_face_time = now

                    if self._current_session_id is None:
                        await self._open_session()

                    # Active seconds = time since session start
                    if self._session_started_at:
                        self._active_seconds = now - self._session_started_at


                    # Feed calibrator if running
                    if calibrator.is_running:
                        avg_ear = (features.left_ear + features.right_ear) / 2.0
                        calibrator.feed(avg_ear)
                    elif calibrator.is_complete and calibrator.result:
                        # Apply calibrated threshold once
                        new_thresh = calibrator.result.threshold
                        if self._blink_detector.ear_threshold != new_thresh:
                            self._blink_detector.ear_threshold = new_thresh
                            settings.ear_threshold = new_thresh
                            logger.info(f"Applied calibrated threshold: {new_thresh}")

                    self._blink_detector.process(features.left_ear, features.right_ear, now)

                    self._metric_buffer.append({
                        "timestamp": now,
                        "blink_rate": self._blink_detector.get_blink_rate(now),
                        "head_movement": features.head_movement,
                        "screen_distance_cm": features.screen_distance_cm,
                        "eye_on_screen": features.eye_on_screen,
                    })
                else:
                    # No face — close session if absent too long
                    if (
                        self._current_session_id is not None
                        and self._last_face_time is not None
                        and (now - self._last_face_time) > settings.session_idle_timeout_seconds
                    ):
                        await self._close_current_session()

                await asyncio.sleep(1.0 / settings.target_fps)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("CV loop crashed")

    async def _metric_loop(self):
        try:
            while self._running:
                await asyncio.sleep(settings.metric_interval_seconds)
                await self._emit_metric()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Metric loop crashed")

    async def _emit_metric(self):
        now = time.time()
        face_detected = bool(self._metric_buffer)

        if face_detected:
            avg_blink_rate = sum(s["blink_rate"] for s in self._metric_buffer) / len(self._metric_buffer)
            avg_head_movement = sum(s["head_movement"] for s in self._metric_buffer) / len(self._metric_buffer)
            distances = [s["screen_distance_cm"] for s in self._metric_buffer if s["screen_distance_cm"]]
            avg_distance = sum(distances) / len(distances) if distances else None
            eye_on_screen = self._metric_buffer[-1]["eye_on_screen"]
        else:
            avg_blink_rate = 0.0
            avg_head_movement = 0.0
            avg_distance = None
            eye_on_screen = False

        seconds_since_break = int(now - (self._last_break_time or now))
        break_due = seconds_since_break >= settings.break_interval_seconds

        raw_focus = compute_focus_score(FocusInputs(
            blink_rate=avg_blink_rate,
            head_movement=avg_head_movement,
            seconds_since_break=seconds_since_break,
            eye_on_screen=eye_on_screen,
        ))
        smoothed_focus = self._focus_smoother.add(raw_focus)
        head_stability = max(0.0, min(1.0, 1.0 - avg_head_movement * 10))

        if self._current_session_id is not None and face_detected:
            with SessionLocal() as db:
                metric = Metric(
                    session_id=self._current_session_id,
                    timestamp=datetime.utcnow(),
                    blink_rate=avg_blink_rate,
                    focus_score=smoothed_focus,
                    head_stability=head_stability,
                    screen_distance_cm=avg_distance,
                    eye_on_screen=eye_on_screen,
                )
                db.add(metric)
                db.commit()

        live = LiveFrame(
            timestamp=datetime.utcnow(),
            session_id=self._current_session_id,
            face_detected=face_detected,
            blink_rate=round(avg_blink_rate, 1),
            focus_score=smoothed_focus,
            head_stability=round(head_stability, 2),
            screen_distance_cm=round(avg_distance, 1) if avg_distance else None,
            seconds_since_break=seconds_since_break,
            total_blinks_this_session=self._blink_detector.get_total_blinks(),
            active_seconds=int(self._active_seconds),
            break_due=break_due,
            calibrating=calibrator.is_running,
            calibration_progress=round(calibrator.progress, 2),
        )
        self._latest_live_frame = live
        await self._broadcast(live)

        self._metric_buffer.clear()

    async def _broadcast(self, frame: LiveFrame):
        dead = set()
        for ws in list(self._subscribers):
            try:
                await self._safe_send(ws, frame)
            except Exception:
                dead.add(ws)
        self._subscribers -= dead

    async def _safe_send(self, ws: WebSocket, frame: LiveFrame):
        await ws.send_json(frame.model_dump(mode="json"))

    async def _open_session(self):
        with SessionLocal() as db:
            new_session = SessionModel(start_time=datetime.utcnow())
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            self._current_session_id = new_session.id
            self._session_started_at = time.time()
            self._blink_detector.reset()
            self._focus_smoother.reset()
            self._active_seconds = 0.0
            self._break_count = 0
            self._total_break_seconds = 0
            self._last_break_time = time.time()
            logger.info(f"Opened session {new_session.id}")

    async def _close_current_session(self):
        if self._current_session_id is None:
            return
        end_time = datetime.utcnow()
        with SessionLocal() as db:
            session = db.get(SessionModel, self._current_session_id)
            if session:
                session.end_time = end_time
                if session.start_time:
                    session.duration_seconds = int(
                        (end_time - session.start_time).total_seconds()
                    )
                session.break_count = self._break_count
                session.total_break_seconds = self._total_break_seconds
                metrics = db.query(Metric).filter(
                    Metric.session_id == self._current_session_id
                ).all()
                if metrics:
                    session.avg_blink_rate = sum(m.blink_rate for m in metrics) / len(metrics)
                    session.avg_focus_score = sum(m.focus_score for m in metrics) / len(metrics)
                db.commit()
                logger.info(f"Closed session {self._current_session_id}")
        self._current_session_id = None
        self._session_started_at = None


session_manager = SessionManager()