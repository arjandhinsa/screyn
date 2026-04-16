"""
Screyn backend — FastAPI entry point.

Owns the camera + CV pipeline lifecycle via startup/shutdown events.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes import sessions, metrics, websocket
from app.services.session_manager import session_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    await session_manager.start()
    yield
    # Shutdown
    await session_manager.stop()


app = FastAPI(
    title="Screyn API",
    description="Screen health optimiser — local-first backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — only allow local frontend during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(websocket.router, tags=["live"])


@app.get("/")
def root():
    return {
        "name": "Screyn",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "camera_active": session_manager.camera_active,
        "current_session_id": session_manager.current_session_id,
    }
