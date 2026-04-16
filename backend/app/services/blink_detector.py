"""
Blink detection via Eye Aspect Ratio (EAR).

Reference: Soukupová & Čech (2016) "Real-Time Eye Blink Detection using
Facial Landmarks." The EAR is a simple geometric ratio that falls sharply
when the eye closes, and is robust to head pose and scale.

EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)

MediaPipe Face Mesh gives us 468 landmarks. The 6-point approximation uses:
  Left eye:  [33, 160, 158, 133, 153, 144]
  Right eye: [362, 385, 387, 263, 373, 380]
"""
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.config import settings


# MediaPipe Face Mesh landmark indices for 6-point EAR
LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]


def _euclidean(p1: np.ndarray, p2: np.ndarray) -> float:
    return float(np.linalg.norm(p1 - p2))


def eye_aspect_ratio(eye_points: np.ndarray) -> float:
    """
    Compute EAR from 6 eye landmark points (shape: (6, 2) or (6, 3)).

    Points should be ordered:
      0: outer corner
      1, 2: upper lid
      3: inner corner
      4, 5: lower lid
    """
    v1 = _euclidean(eye_points[1], eye_points[5])
    v2 = _euclidean(eye_points[2], eye_points[4])
    h = _euclidean(eye_points[0], eye_points[3])
    if h == 0:
        return 0.0
    return (v1 + v2) / (2.0 * h)


@dataclass
class BlinkEvent:
    timestamp: float
    duration_ms: float


class BlinkDetector:
    """
    Detects blinks from a stream of per-frame EAR values.

    A blink = EAR drops below threshold for `consec_frames` frames,
    then recovers. Extended closure (>500ms) is treated as "eye closed"
    rather than a blink (counted separately for fatigue tracking).

    Maintains a rolling 60-second window of blink events for rate calculation.
    """

    RATE_WINDOW_SECONDS = 60
    LONG_CLOSURE_MS = 500

    def __init__(
        self,
        ear_threshold: float = None,
        consec_frames: int = None,
    ):
        self.ear_threshold = ear_threshold or settings.ear_threshold
        self.consec_frames = consec_frames or settings.ear_consec_frames

        self._closed_frames = 0
        self._closure_start_time: Optional[float] = None
        self._blink_events: deque[BlinkEvent] = deque()
        self._long_closures: deque[float] = deque()
        self._total_blinks = 0
        self._last_ear: Optional[float] = None

    def process(self, left_ear: float, right_ear: float, timestamp: float = None) -> bool:
        """
        Feed a per-frame EAR measurement. Returns True if a blink just completed.
        """
        if timestamp is None:
            timestamp = time.time()

        ear = (left_ear + right_ear) / 2.0
        self._last_ear = ear
        blink_just_registered = False

        if ear < self.ear_threshold:
            if self._closed_frames == 0:
                self._closure_start_time = timestamp
            self._closed_frames += 1
        else:
            if self._closed_frames >= self.consec_frames and self._closure_start_time:
                duration_ms = (timestamp - self._closure_start_time) * 1000
                if duration_ms < self.LONG_CLOSURE_MS:
                    self._blink_events.append(BlinkEvent(timestamp, duration_ms))
                    self._total_blinks += 1
                    blink_just_registered = True
                else:
                    self._long_closures.append(timestamp)
            self._closed_frames = 0
            self._closure_start_time = None

        self._prune_old_events(timestamp)
        return blink_just_registered

    def _prune_old_events(self, now: float):
        cutoff = now - self.RATE_WINDOW_SECONDS
        while self._blink_events and self._blink_events[0].timestamp < cutoff:
            self._blink_events.popleft()
        while self._long_closures and self._long_closures[0] < cutoff:
            self._long_closures.popleft()

    def get_blink_rate(self, now: float = None) -> float:
        """Blinks per minute, over the rolling 60s window."""
        if now is None:
            now = time.time()
        self._prune_old_events(now)
        return float(len(self._blink_events))  # count/60s == blinks/minute

    def get_total_blinks(self) -> int:
        return self._total_blinks

    def get_last_ear(self) -> Optional[float]:
        return self._last_ear

    def reset(self):
        self._closed_frames = 0
        self._closure_start_time = None
        self._blink_events.clear()
        self._long_closures.clear()
        self._total_blinks = 0
        self._last_ear = None
