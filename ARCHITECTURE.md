# Screyn Architecture

## Overview

Screyn is a **local-first desktop application** that monitors your screen-session health and productivity. A Python/FastAPI backend owns the webcam, runs a CV pipeline on each frame, writes metrics to a local SQLite database, and streams live data to a React dashboard over WebSocket.

```
┌────────────────────────────────────────────────────────┐
│  Your Machine (or Raspberry Pi in Sentinel mode)       │
│                                                         │
│  ┌──────────┐   ┌───────────────┐   ┌──────────────┐   │
│  │  Camera  │──▶│  CV Pipeline  │──▶│   Metrics    │   │
│  │  (cv2)   │   │  (MediaPipe)  │   │   Buffer     │   │
│  └──────────┘   └───────────────┘   └──────┬───────┘   │
│                                              │          │
│                         ┌────────────────────┴───┐     │
│                         ▼                        ▼     │
│                    ┌─────────┐            ┌──────────┐ │
│                    │ SQLite  │            │ WebSocket│ │
│                    │   DB    │            │ Broadcast│ │
│                    └─────────┘            └─────┬────┘ │
└──────────────────────────────────────────────────┼─────┘
                                                    │
                           ┌────────────────────────┘
                           ▼
                    ┌───────────────┐
                    │ React Dash-   │
                    │ board (Vite)  │
                    └───────────────┘
```

## Core Concepts

### Session

A continuous period where the user is at their screen. Starts when the camera first detects a face, ends after a configurable period of no face detected (default 2 minutes). Each session records aggregate metrics and references to a time-series of per-window samples.

### Focus Score

A composite 0–100 score derived from:

- **Blink rate** — deviation from healthy baseline (15–20 blinks/min). Both abnormally low (hyperfocus/strain) and abnormally high (fatigue/distraction) lower the score.
- **Head stability** — controlled stillness suggests engagement. Micro-movements are normal; large head turns suggest distraction.
- **Break compliance** — penalty grows over time since last proper break (20-20-20 rule).

The focus score is intentionally noisy on short windows and smooths over ~2 minutes for display.

### Break

A 20+ second window where the user either (a) looks away from the screen (gaze off-axis) or (b) leaves the frame entirely. Follows the 20-20-20 rule used in occupational ophthalmology.

## Backend

### Structure

```
backend/
├── main.py                  # FastAPI app entry + CV worker lifecycle
├── requirements.txt
├── .env.example
└── app/
    ├── config.py            # Pydantic settings
    ├── database.py          # SQLAlchemy engine + session
    ├── models/              # SQLAlchemy ORM models
    │   ├── session.py
    │   └── metric.py
    ├── schemas/             # Pydantic request/response schemas
    │   └── session.py
    ├── routes/              # FastAPI routers
    │   ├── sessions.py      # GET /sessions, GET /sessions/{id}
    │   ├── metrics.py       # GET /metrics/{session_id}
    │   └── websocket.py     # WS /ws/live
    └── services/
        ├── camera.py        # OpenCV capture loop (background thread)
        ├── cv_pipeline.py   # MediaPipe face mesh + metric extraction
        ├── blink_detector.py # EAR-based blink detection
        ├── focus_scorer.py  # Focus score calculation
        └── session_manager.py # In-memory session state + broadcast
```

### CV Pipeline

1. **Capture** — OpenCV reads frames from default camera at ~15 FPS (enough for reliable blink detection; faster wastes cycles).
2. **Face Mesh** — MediaPipe extracts 468 facial landmarks from each frame. Returns `None` if no face detected.
3. **Eye Aspect Ratio (EAR)** — Computed from 6 landmarks per eye. A blink is registered when EAR drops below `0.20` for 1–3 frames and then recovers.
4. **Head Pose** — Yaw/pitch/roll estimated from nose bridge and eye corners via solvePnP.
5. **Screen Distance** — Rough estimate from inter-pupillary pixel distance (calibrated to a known ~63mm average IPD).
6. **Metrics Emission** — Every 5 seconds, the pipeline emits a metric record: `{blink_rate, head_stability, focus_score, distance, timestamp}`.

### Data Flow

- **High-frequency path (30ms)**: camera → pipeline → in-memory ring buffer
- **Medium-frequency path (5s)**: ring buffer → metric record → SQLite + WebSocket broadcast
- **Low-frequency path (session end)**: session summary computed from metrics and written to SQLite

### Threading

- **Main thread**: FastAPI event loop (async)
- **Camera thread**: blocking OpenCV capture; pushes frames to `asyncio.Queue`
- **CV worker**: consumes frames, runs MediaPipe (CPU-bound, kept single-threaded to avoid GIL contention)
- **Broadcast**: async, from FastAPI event loop

### Database

SQLite for simplicity and full local-first story. Two tables:

- `sessions` — one row per session. `id, start_time, end_time, duration_seconds, avg_blink_rate, avg_focus_score, break_count, device_id`
- `metrics` — many rows per session (one per 5s window). `id, session_id, timestamp, blink_rate, focus_score, head_stability, screen_distance_cm, eye_on_screen`

No migrations framework yet — on first run, tables are created via `Base.metadata.create_all`. Add Alembic if schema churn becomes painful.

## Frontend

### Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx
    ├── App.jsx              # Router
    ├── index.css            # Globals + SEYN design tokens
    ├── pages/
    │   ├── Dashboard.jsx    # Live view — main screen
    │   ├── History.jsx      # Past sessions + trends
    │   └── Settings.jsx     # Thresholds, break config
    ├── components/
    │   ├── MetricCard.jsx
    │   ├── FocusGauge.jsx
    │   ├── SessionTimer.jsx
    │   └── BreakReminder.jsx
    └── hooks/
        └── useWebSocket.js  # Live-metric subscription
```

### Design

Matches the SEYN brand ecosystem (dark, refined, Space Mono for numerics + DM Sans for body). Layout is HUD-like — dense live metrics without being cluttered.

### Real-time Updates

The dashboard opens a WebSocket to `/ws/live` on mount and receives a metric payload every 5 seconds. No polling.

## Raspberry Pi "Sentinel" Mode

The same backend code runs on the Pi. Differences:

- Uses `picamera2` instead of `cv2.VideoCapture` for the Pi Camera Module
- Runs headless — no frontend bundled. Exposes the API over the local network.
- Desktop frontend connects to `http://screyn.local:8000` via mDNS (or manually-configured IP)

See `pi-deployment/README.md` for setup.

## Future (post-MVP)

- Mood inference from micro-expressions (MediaPipe face blendshapes)
- Ambient lux tracking (BH1750 sensor on Pi I²C)
- Humidity/temperature (DHT22)
- Correlation view: "your focus drops 40% after 90 min without a break"
- Optional ambient LED output (status glow strip)
- Export to CSV/JSON for personal data analysis
