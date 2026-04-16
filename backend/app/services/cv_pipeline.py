"""
CV pipeline — wraps MediaPipe Tasks FaceLandmarker and produces per-frame features.

Uses the modern MediaPipe Tasks API. On first run, downloads the face_landmarker.task
model (~10MB) to backend/models/.
"""
import logging
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from app.services.blink_detector import LEFT_EYE_IDX, RIGHT_EYE_IDX, eye_aspect_ratio

logger = logging.getLogger(__name__)

# Model — downloaded on first run
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_PATH = MODEL_DIR / "face_landmarker.task"

# Average adult interpupillary distance (mm)
AVG_IPD_MM = 63.0
DEFAULT_FOCAL_PX = 600.0


def _ensure_model() -> None:
    """Download the FaceLandmarker model if not present."""
    if MODEL_PATH.exists():
        return
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading MediaPipe face landmarker model (~10MB) to {MODEL_PATH}")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    logger.info("Model downloaded")


@dataclass
class FrameFeatures:
    face_detected: bool
    left_ear: float = 0.0
    right_ear: float = 0.0
    head_yaw: float = 0.0
    head_pitch: float = 0.0
    head_roll: float = 0.0
    head_movement: float = 0.0
    screen_distance_cm: Optional[float] = None
    eye_on_screen: bool = True


class CVPipeline:
    """Runs MediaPipe FaceLandmarker and extracts per-frame features."""

    def __init__(self):
        _ensure_model()
        base_options = mp_python.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        self._prev_nose: Optional[np.ndarray] = None

    def process_frame(self, frame: np.ndarray) -> FrameFeatures:
        """Analyse one BGR frame. Returns features."""
        if frame is None:
            return FrameFeatures(face_detected=False)

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)

        if not result.face_landmarks:
            self._prev_nose = None
            return FrameFeatures(face_detected=False)

        landmarks = result.face_landmarks[0]
        points = np.array(
            [[lm.x * w, lm.y * h, lm.z * w] for lm in landmarks],
            dtype=np.float32,
        )

        # EAR
        left_eye_pts = points[LEFT_EYE_IDX][:, :2]
        right_eye_pts = points[RIGHT_EYE_IDX][:, :2]
        left_ear = eye_aspect_ratio(left_eye_pts)
        right_ear = eye_aspect_ratio(right_eye_pts)

        # Head pose
        yaw, pitch, roll = self._estimate_head_pose(points, w, h)

        # Head movement
        nose_tip = points[1][:2]
        head_movement = 0.0
        if self._prev_nose is not None:
            head_movement = float(np.linalg.norm(nose_tip - self._prev_nose) / max(w, h))
        self._prev_nose = nose_tip

        # Screen distance
        screen_distance_cm = self._estimate_distance(points, w)

        # Eye-on-screen heuristic
        eye_on_screen = abs(yaw) < 25.0 and abs(pitch) < 20.0

        return FrameFeatures(
            face_detected=True,
            left_ear=left_ear,
            right_ear=right_ear,
            head_yaw=yaw,
            head_pitch=pitch,
            head_roll=roll,
            head_movement=head_movement,
            screen_distance_cm=screen_distance_cm,
            eye_on_screen=eye_on_screen,
        )

    def _estimate_head_pose(
        self, points: np.ndarray, w: int, h: int
    ) -> tuple[float, float, float]:
        """Rough head pose via solvePnP with a canonical 3D face model."""
        image_points = np.array([
            points[1][:2],      # nose tip
            points[152][:2],    # chin
            points[33][:2],     # left eye outer
            points[263][:2],    # right eye outer
            points[61][:2],     # left mouth corner
            points[291][:2],    # right mouth corner
        ], dtype=np.float64)

        model_points = np.array([
            (0.0, 0.0, 0.0),
            (0.0, -63.6, -12.5),
            (-43.3, 32.7, -26.0),
            (43.3, 32.7, -26.0),
            (-28.9, -28.9, -24.1),
            (28.9, -28.9, -24.1),
        ], dtype=np.float64)

        focal_length = w
        camera_matrix = np.array([
            [focal_length, 0, w / 2],
            [0, focal_length, h / 2],
            [0, 0, 1],
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1))

        try:
            ok, rvec, _ = cv2.solvePnP(
                model_points, image_points, camera_matrix, dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
            if not ok:
                return 0.0, 0.0, 0.0

            rot_mat, _ = cv2.Rodrigues(rvec)
            proj_mat = np.hstack((rot_mat, np.zeros((3, 1))))
            _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(proj_mat)
            pitch, yaw, roll = [float(a) for a in euler.flatten()]

            if pitch > 90:
                pitch -= 180
            elif pitch < -90:
                pitch += 180

            return yaw, pitch, roll
        except cv2.error:
            return 0.0, 0.0, 0.0

    def _estimate_distance(self, points: np.ndarray, frame_width: int) -> Optional[float]:
        """Rough distance estimate from outer-eye-corner pixel distance."""
        left_outer = points[33][:2]
        right_outer = points[263][:2]
        pixel_distance = float(np.linalg.norm(right_outer - left_outer))
        if pixel_distance < 1.0:
            return None
        focal_px = DEFAULT_FOCAL_PX * (frame_width / 640.0)
        distance_mm = (AVG_IPD_MM * focal_px) / pixel_distance
        return distance_mm / 10.0

    def close(self):
        self._landmarker.close()