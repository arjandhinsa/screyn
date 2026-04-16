"""
Camera capture — runs OpenCV VideoCapture in a background thread.

Pushes frames into an asyncio.Queue so the async CV worker can consume them
without blocking the event loop. Kept intentionally simple — no buffering,
just "latest frame wins".
"""
import asyncio
import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class CameraCapture:
    """
    Owns the OpenCV VideoCapture.

    Runs a background thread that grabs frames at TARGET_FPS and stashes
    the most recent one. `get_latest_frame()` returns it async-safely.
    """

    def __init__(self, camera_index: int = None, target_fps: int = None):
        self.camera_index = camera_index if camera_index is not None else settings.camera_index
        self.target_fps = target_fps or settings.target_fps
        self.frame_interval = 1.0 / self.target_fps

        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> bool:
        """Open the camera and begin capture. Returns True on success."""
        if self._is_running:
            return True

        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            logger.error(f"Could not open camera at index {self.camera_index}")
            self._cap = None
            return False

        # Reasonable defaults — actual resolution depends on hardware
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        self._is_running = True
        logger.info(f"Camera started on index {self.camera_index}")
        return True

    def stop(self):
        """Stop capture and release the camera."""
        if not self._is_running:
            return

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()
        self._cap = None
        self._thread = None
        self._is_running = False
        logger.info("Camera stopped")

    def _capture_loop(self):
        """Background thread: grab frames at target_fps. Blocking — keep off event loop."""
        next_frame_time = time.time()
        while not self._stop_event.is_set():
            now = time.time()
            if now < next_frame_time:
                time.sleep(max(0, next_frame_time - now))

            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Failed to read frame; retrying")
                time.sleep(0.1)
                continue

            with self._frame_lock:
                self._latest_frame = frame

            if settings.show_preview:
                # Useful for development — disable on Pi
                cv2.imshow("Screyn Preview", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self._stop_event.set()
                    break

            next_frame_time += self.frame_interval

        if settings.show_preview:
            cv2.destroyAllWindows()

    async def get_latest_frame(self) -> Optional[np.ndarray]:
        """Return the most recent frame (copy), or None if none available."""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()


# Module-level singleton — owned by session_manager
camera = CameraCapture()
