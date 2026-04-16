"""
Basic sanity test for the blink detector.

Run with:  python -m pytest backend/tests/
(Requires pytest; skip for now if you haven't added it)
"""
import time

from app.services.blink_detector import BlinkDetector, eye_aspect_ratio
import numpy as np


def test_ear_open_eye():
    """A wide-open eye should have EAR > 0.3."""
    points = np.array([
        [0, 0],       # outer corner
        [2, -1.5],    # upper 1
        [4, -1.5],    # upper 2
        [6, 0],       # inner corner
        [4, 1.5],     # lower 2
        [2, 1.5],     # lower 1
    ])
    assert eye_aspect_ratio(points) > 0.3


def test_ear_closed_eye():
    """A closed eye should have EAR close to 0."""
    points = np.array([
        [0, 0],
        [2, -0.1],
        [4, -0.1],
        [6, 0],
        [4, 0.1],
        [2, 0.1],
    ])
    assert eye_aspect_ratio(points) < 0.1


def test_blink_registers():
    """Simulated blink sequence should register exactly one blink."""
    detector = BlinkDetector(ear_threshold=0.2, consec_frames=2)
    now = time.time()

    # 10 open frames
    for i in range(10):
        detector.process(0.3, 0.3, now + i * 0.05)

    # 3 closed frames (blink)
    for i in range(3):
        detector.process(0.1, 0.1, now + (10 + i) * 0.05)

    # 10 open frames (eye reopens)
    for i in range(10):
        detector.process(0.3, 0.3, now + (13 + i) * 0.05)

    assert detector.get_total_blinks() == 1
