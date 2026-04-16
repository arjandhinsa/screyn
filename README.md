# Screyn — Screen Health Optimiser

Your screen time, optimised for focus.

Screyn uses computer vision to monitor your eyes, posture, and attention during screen sessions. It helps you understand when your focus and mood are strongest, and when to step away — because eye health and cognitive performance are deeply connected.

## The Connection

- **Blink rate** drops ~60% when staring at screens — a strong predictor of dry eye, fatigue, and waning focus
- **Accumulated eye strain** directly correlates with reduced cognitive performance and low mood
- **Screen distance and posture** affect vergence and neck tension, both of which compound through a session

Screyn surfaces these signals in real-time so you can build better screen habits — and know when you're genuinely in flow versus when you're pushing past useful effort.

## Architecture

- **Backend**: Python + FastAPI + MediaPipe + OpenCV
- **Frontend**: React + Vite dashboard
- **Database**: Local SQLite (all data stays on your machine)
- **CV**: MediaPipe Face Mesh for eye/head tracking, EAR-based blink detection

## Development Approach

Build and test on laptop webcam first. Once the pipeline is solid, deploy to a Raspberry Pi + camera module on your desk as a dedicated "Sentinel" device. Pi streams data to the desktop dashboard over your local network.

## Running Locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs on `http://localhost:8000` (API docs at `/docs`)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

## Privacy

Screyn is local-first by design. No video ever leaves your device. All metrics are stored in a local SQLite database. There is no cloud, no account, no telemetry. So full privacy as to be expected.

## Status

Scaffold complete. wire up the CV pipeline end-to-end, test on webcam and pi.

See `ROADMAP.md` for the full plan and `ARCHITECTURE.md` for technical details.

## Part of the SEYN Ecosystem

- [Seynse](https://seynse.seyn.co.uk) — Social confidence coach
- [Seynario](https://seynario.seyn.co.uk) — Dress for the scenario
- **Screyn** — Screen health optimiser *(in development)*
- Seync — Find your tribe *(coming soon)*
- Be Seyn — Identity marketing platform *(coming soon)*
