from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .orchestrator import Orchestrator
from .store import EventStore


store = EventStore(settings.database_path)
orchestrator = Orchestrator(store, settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_start:
        orchestrator.start()
    yield
    orchestrator.shutdown()


app = FastAPI(title="InternFly API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class Command(BaseModel):
    action: Literal["pause", "resume", "sleep-now", "emergency-stop"]


class Approval(BaseModel):
    decision: Literal["approved", "rejected"]
    content_hash: str
    reason: str | None = None


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def ready() -> dict[str, object]:
    return {"status": "ready", "mode": settings.mode, "stopped": orchestrator.snapshot.stopped}


@app.get("/api/state")
def state() -> dict[str, object]:
    if not settings.auto_start:
        orchestrator.pulse()
    return orchestrator.public_state()


@app.get("/api/events")
def events(limit: int = 80, after: int = 0) -> list[dict[str, object]]:
    return store.events(min(max(limit, 1), 500), after)


@app.get("/api/metrics")
def metrics() -> dict[str, object]:
    return projected_metrics()


def projected_metrics() -> dict[str, object]:
    counts = store.counts()
    state = orchestrator.snapshot
    quality = 100 if counts["drafts_approved"] else 70 if counts["drafts_created"] else 0
    uptime = 100 if not state.stopped else 0
    counts["ten_x_drosophila_score"] = round(min(1000, 4 * counts["dsa_success_rate"] + 2 * quality + uptime), 1)
    counts["estimated_flies_per_engineer"] = max(1, round(40 / max(0.1, counts["dsa_solved"] + counts["drafts_created"])))
    return counts


@app.get("/api/jobs")
def jobs() -> list[dict[str, object]]:
    return orchestrator.jobs.list_jobs()


@app.get("/api/connectome/map")
def connectome_map() -> dict[str, object]:
    return orchestrator.public_connectome_map()


@app.get("/api/drafts")
def drafts() -> list[dict[str, object]]:
    return orchestrator.jobs.list_drafts()


@app.post("/api/commands")
def command(body: Command) -> dict[str, object]:
    try:
        return orchestrator.command(body.action).to_dict()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/drafts/{draft_id}/decision")
def decide(draft_id: str, body: Approval) -> dict[str, object]:
    try:
        return orchestrator.jobs.decide(draft_id, body.decision, body.content_hash, body.reason)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    await websocket.accept()
    sequence = 0
    try:
        while True:
            if not settings.auto_start:
                orchestrator.pulse()
            batch = store.events(limit=50, after=sequence)
            if batch:
                sequence = max(int(item["sequence"]) for item in batch)
            await websocket.send_json({
                "sequence": sequence,
                "state": orchestrator.public_state(),
                "metrics": projected_metrics(),
                "events": batch,
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


# Vercel's FastAPI builder runs the dashboard build before packaging this app.
# Mount it last so API, health, docs, and WebSocket routes retain precedence.
dashboard_directory = Path(__file__).resolve().parents[1] / "public"
if dashboard_directory.is_dir():
    app.mount("/", StaticFiles(directory=dashboard_directory, html=True), name="dashboard")
