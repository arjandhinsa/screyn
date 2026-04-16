"""
Focus score — composite 0–100 derived from blink rate, head stability,
and break compliance.

Design principles:
- Both too-low and too-high blink rates are penalised. Hyperfocus (low blink)
  causes strain; high blink rate signals fatigue or distraction.
- Large head movements lower the score. Micro-movements are ignored — small
  adjustments are normal and don't indicate distraction.
- Time since last break adds a growing penalty after ~45 minutes.
- Output is intentionally smoothed over ~2 minutes to avoid jitter.
"""
from collections import deque
from dataclasses import dataclass

from app.config import settings


@dataclass
class FocusInputs:
    blink_rate: float            # blinks/min
    head_movement: float         # normalised 0–1
    seconds_since_break: int     # seconds since the last break
    eye_on_screen: bool


def _blink_component(blink_rate: float) -> float:
    """
    Returns 0–100. Peaks at the centre of the healthy range, falls off on either side.
    """
    lo = settings.healthy_blink_rate_min
    hi = settings.healthy_blink_rate_max
    centre = (lo + hi) / 2
    half_width = (hi - lo) / 2

    if half_width <= 0:
        return 50.0

    # Normalised distance from centre
    distance = abs(blink_rate - centre) / half_width
    # 0 distance = 100, 1.0 distance (edge of healthy) = 80, beyond = tapers sharply
    if distance <= 1.0:
        return 100.0 - 20.0 * distance  # 100 → 80 across healthy band
    # Outside healthy band — sharper penalty
    excess = distance - 1.0
    return max(0.0, 80.0 - 40.0 * excess)


def _head_component(head_movement: float) -> float:
    """
    Small movements fine; large movements indicate distraction.
    0.0 movement → 100. ~0.05 → 70. ~0.15+ → 20.
    """
    if head_movement < 0.01:
        return 100.0
    if head_movement < 0.05:
        return 100.0 - 600 * (head_movement - 0.01)  # 100 → 76
    # Beyond normal fidgeting
    return max(0.0, 76.0 - 500 * (head_movement - 0.05))


def _break_component(seconds_since_break: int) -> float:
    """
    Full score if broken within last 20 min. Falls off after that.
    At 45 min without break → 60. At 90 min → 20.
    """
    ideal = settings.break_interval_seconds  # 20 min = 1200s
    if seconds_since_break <= ideal:
        return 100.0
    overtime = seconds_since_break - ideal
    # Lose 1 point per 30 seconds overtime, floor at 0
    return max(0.0, 100.0 - overtime / 30.0)


def compute_focus_score(inputs: FocusInputs) -> float:
    """
    Weighted combination of the three components. Returns 0–100.
    Weights: 50% blink, 25% head, 25% break.
    """
    if not inputs.eye_on_screen:
        # Not looking at the screen doesn't score focus — it's break time
        return 0.0

    blink = _blink_component(inputs.blink_rate)
    head = _head_component(inputs.head_movement)
    brk = _break_component(inputs.seconds_since_break)

    score = 0.5 * blink + 0.25 * head + 0.25 * brk
    return round(max(0.0, min(100.0, score)), 1)


class FocusSmoother:
    """
    Rolling average over the last N samples to keep the UI stable.
    """
    def __init__(self, window_size: int = 24):
        self._samples: deque[float] = deque(maxlen=window_size)

    def add(self, score: float) -> float:
        self._samples.append(score)
        return self.current()

    def current(self) -> float:
        if not self._samples:
            return 0.0
        return round(sum(self._samples) / len(self._samples), 1)

    def reset(self):
        self._samples.clear()
