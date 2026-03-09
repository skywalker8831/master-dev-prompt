#!/usr/bin/env python3
"""
dj_server.py — FastAPI HTTP server for the AI-DJ system.

Exposes the TrackLibrary and DJBrain over a REST API so any client
(web app, mobile app, hardware controller) can interact with the AI-DJ
system over HTTP.

Endpoints:
    GET  /health              — liveness check
    GET  /tracks              — list all tracks
    POST /tracks              — add a new track
    DELETE /tracks/{title}    — remove a track by title
    GET  /tracks/search       — filter tracks by genre, BPM range, energy, key
    POST /playlist            — generate an AI-ordered playlist

Run:
    uvicorn dj_server:app --reload --port 8001

Environment variables:
    ANTHROPIC_API_KEY  — required for playlist generation
    DJ_TRACKS_DB       — path to the track JSON database (default: tracks.json)
    DJ_API_KEY         — optional: protect endpoints with this bearer token
"""

import os
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from dj_brain import DJBrain
from track_library import TrackLibrary, VALID_GENRES, _validate_track

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI-DJ Server",
    description="REST API for the AI-DJ track library and playlist generator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_security = HTTPBearer(auto_error=False)


def _get_library() -> TrackLibrary:
    db_path = os.getenv("DJ_TRACKS_DB", "tracks.json")
    return TrackLibrary(db_path)


def verify_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)],
) -> None:
    expected = os.getenv("DJ_API_KEY")
    if not expected:
        return  # No key configured — open access
    token = credentials.credentials if credentials else None
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


Auth = Annotated[None, Depends(verify_api_key)]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TrackIn(BaseModel):
    title: str = Field(..., min_length=1)
    artist: str = Field(..., min_length=1)
    bpm: float = Field(..., ge=40, le=300)
    key: str = Field(..., min_length=1)
    genre: str
    energy: float = Field(..., ge=1, le=10)


class PlaylistRequest(BaseModel):
    mood: str = Field(..., min_length=1, description="Desired vibe or energy arc")
    duration_minutes: int = Field(60, ge=1, le=480)
    genre: str | None = None
    min_bpm: float | None = None
    max_bpm: float | None = None
    min_energy: float | None = None
    max_energy: float | None = None
    key: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tracks", dependencies=[Depends(verify_api_key)])
def list_tracks() -> list[dict[str, Any]]:
    return _get_library().all_tracks()


@app.post("/tracks", status_code=201, dependencies=[Depends(verify_api_key)])
def add_track(track: TrackIn) -> dict[str, str]:
    lib = _get_library()
    raw = track.model_dump()
    try:
        _validate_track(raw)
        lib.add(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"message": f"Track '{track.title}' by '{track.artist}' added."}


@app.delete("/tracks/{title}", dependencies=[Depends(verify_api_key)])
def remove_track(title: str) -> dict[str, str]:
    lib = _get_library()
    if not lib.remove(title):
        raise HTTPException(status_code=404, detail=f"Track '{title}' not found.")
    return {"message": f"Track '{title}' removed."}


@app.get("/tracks/search", dependencies=[Depends(verify_api_key)])
def search_tracks(
    genre: str | None = Query(default=None),
    min_bpm: float | None = Query(default=None, ge=40, le=300),
    max_bpm: float | None = Query(default=None, ge=40, le=300),
    min_energy: float | None = Query(default=None, ge=1, le=10),
    max_energy: float | None = Query(default=None, ge=1, le=10),
    key: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    return _get_library().search(
        genre=genre,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
        min_energy=min_energy,
        max_energy=max_energy,
        key=key,
    )


@app.post("/playlist", dependencies=[Depends(verify_api_key)])
def generate_playlist(req: PlaylistRequest) -> dict[str, Any]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not configured on the server.",
        )

    lib = _get_library()
    candidates = lib.search(
        genre=req.genre,
        min_bpm=req.min_bpm,
        max_bpm=req.max_bpm,
        min_energy=req.min_energy,
        max_energy=req.max_energy,
        key=req.key,
    )

    if not candidates:
        raise HTTPException(
            status_code=422,
            detail=(
                "No tracks matched the supplied filters. "
                "Relax your filter criteria or add more tracks."
            ),
        )

    try:
        brain = DJBrain(api_key=api_key)
        plan = brain.generate_plan(
            tracks=candidates,
            mood=req.mood,
            duration_minutes=req.duration_minutes,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return plan


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "dj_server:app",
        host="0.0.0.0",
        port=int(os.getenv("DJ_PORT", "8001")),
        reload=False,
    )
