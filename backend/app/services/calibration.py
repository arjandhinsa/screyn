"""
Auto-calibration — silently measures baseline EAR for 60 seconds on first launch.

Collects open-eye and blink EAR values, then computes an optimal threshold
that sits between the two distributions. Stores the result in the DB so it
only runs once per user/device.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

CALIBRATION_DURATION = 60  # seconds
CALIBRATION_FILE = Path(__file__).parent.parent.parent / "calibration.json"


@dataclass
class CalibrationResult:
    baseline_ear: float          # median EAR when eyes are open
    blink_ear: float             # median EAR during detected dips
    threshold: float             # computed optimal threshold
    samples_collected: int
    blinks_detected: int
    calibrated_at: float = field(default_factory=time.time)


class Calibrator:
    """
    Collects raw EAR samples for CALIBRATION_DURATION seconds.

    After collection, splits samples into "open" (above median) and
    "closed" (bottom 10th percentile dips) and picks a threshold
    halfway between the two clusters.
    """

    def __init__(self):
        self._samples: list[float] = []
        self._start_time: float | None = None
        self._is_running = False
        self._is_complete = False
        self._result: CalibrationResult | None = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @property
    def result(self) -> CalibrationResult | None:
        return self._result

    @property
    def progress(self) -> float:
        """0.0 to 1.0"""
        if not self._is_running or not self._start_time:
            return 1.0 if self._is_complete else 0.0
        elapsed = time.time() - self._start_time
        return min(1.0, elapsed / CALIBRATION_DURATION)

    def start(self):
        self._samples = []
        self._start_time = time.time()
        self._is_running = True
        self._is_complete = False
        logger.info("Calibration started — collecting EAR samples for 60s")

    def feed(self, ear: float):
        """Feed a per-frame average EAR value."""
        if not self._is_running:
            return
        self._samples.append(ear)

        # Check if time's up
        if time.time() - self._start_time >= CALIBRATION_DURATION:
            self._finish()

    def _finish(self):
        self._is_running = False
        self._is_complete = True

        if len(self._samples) < 50:
            logger.warning("Not enough samples for calibration, using defaults")
            self._result = CalibrationResult(
                baseline_ear=0.28,
                blink_ear=0.15,
                threshold=settings.ear_threshold,
                samples_collected=len(self._samples),
                blinks_detected=0,
            )
            return

        arr = np.array(self._samples)
        median_ear = float(np.median(arr))

        # Bottom 10th percentile = blink territory
        p10 = float(np.percentile(arr, 10))

        # Threshold = midpoint between blink dips and open baseline
        # Weighted slightly toward the blink side to avoid false positives
        threshold = p10 + 0.4 * (median_ear - p10)

        # Clamp to reasonable range
        threshold = max(0.12, min(0.28, threshold))

        # Count how many "dip events" we saw (rough blink count)
        below_thresh = arr < threshold
        dip_starts = np.diff(below_thresh.astype(int)) == 1
        blinks_detected = int(np.sum(dip_starts))

        self._result = CalibrationResult(
            baseline_ear=round(median_ear, 4),
            blink_ear=round(p10, 4),
            threshold=round(threshold, 4),
            samples_collected=len(self._samples),
            blinks_detected=blinks_detected,
        )

        logger.info(
            f"Calibration complete: baseline={median_ear:.3f}, "
            f"blink_p10={p10:.3f}, threshold={threshold:.3f}, "
            f"samples={len(self._samples)}, blinks={blinks_detected}"
        )

        self._save()

    def _save(self):
        """Persist calibration to a JSON file."""
        import json
        if not self._result:
            return
        data = {
            "baseline_ear": self._result.baseline_ear,
            "blink_ear": self._result.blink_ear,
            "threshold": self._result.threshold,
            "samples_collected": self._result.samples_collected,
            "blinks_detected": self._result.blinks_detected,
            "calibrated_at": self._result.calibrated_at,
        }
        CALIBRATION_FILE.write_text(json.dumps(data, indent=2))
        logger.info(f"Calibration saved to {CALIBRATION_FILE}")

    @staticmethod
    def load_existing() -> CalibrationResult | None:
        """Load a previous calibration from disk, or None if not calibrated."""
        import json
        if not CALIBRATION_FILE.exists():
            return None
        try:
            data = json.loads(CALIBRATION_FILE.read_text())
            return CalibrationResult(**data)
        except Exception:
            return None


calibrator = Calibrator()