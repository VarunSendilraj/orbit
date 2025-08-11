from __future__ import annotations

import os
from typing import Any, Dict

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .steps import bus, stamp
from .executor import execute_command
from .tools import create_files, open_app
from .audit_logger import get_audit_logger

app = FastAPI(title="Orbit Agent", description="Phase 1 Hello World MVP")

# Add CORS middleware for Tauri WebSocket connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost", "https://tauri.localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    command: str
    dry_run: bool = False


async def emit(
    run_id: str, step_id: int, status: str, msg: str, data: Dict[str, Any] | None = None
):
    """Emit a step event to all connected WebSocket clients."""
    payload = {
        "run_id": run_id,
        "step_id": step_id,
        "status": status,  # queued|running|ok|error
        "message": msg,
        "ts": stamp(),
        "data": data or {},
    }
    await bus.broadcast(payload)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time step updates."""
    await bus.register(websocket)
    try:
        while True:
            # Keep connection alive - we don't expect client messages yet
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await bus.unregister(websocket)


@app.post("/run")
async def run_command(req: RunRequest):
    """HTTP endpoint that delegates to the shared executor and streams via the WebSocket bus."""

    async def _emit(
        run_id: str, step_id: int, status: str, msg: str, data: Dict[str, Any] | None = None
    ):
        payload = {
            "run_id": run_id,
            "step_id": step_id,
            "status": status,
            "message": msg,
            "ts": stamp(),
            "data": data or {},
        }
        await bus.broadcast(payload)

    result = await execute_command(req.command, dry_run=req.dry_run, emit=_emit)
    return result


# Keep legacy endpoints for backward compatibility
class CreateFiles(BaseModel):
    dir: str = "~/Documents"
    count: int = 5
    prefix: str = "note"
    ext: str = "md"


@app.post("/tools/create_files")
def create_files_legacy(a: CreateFiles) -> dict[str, list[str]]:
    created = create_files(a.dir, a.count, a.prefix, a.ext)
    return {"created": created}


@app.post("/tools/open_app")
def open_app_legacy(name: str) -> dict[str, str]:
    open_app(name)
    return {"status": "ok"}


# Audit logging endpoints
@app.get("/audit/logs")
async def query_audit_logs(
    run_id: str = None,
    event_type: str = None,
    tool_name: str = None,
    status: str = None,
    limit: int = 100,
):
    """Query audit logs with optional filters."""
    audit_logger = get_audit_logger()

    logs = audit_logger.query_logs(
        run_id=run_id, event_type=event_type, tool_name=tool_name, status=status, limit=limit
    )

    return {"logs": logs, "count": len(logs)}


@app.get("/audit/summary/{run_id}")
async def get_command_summary(run_id: str):
    """Get a detailed summary of a specific command execution."""
    audit_logger = get_audit_logger()

    summary = audit_logger.get_command_summary(run_id)

    if not summary:
        return {"error": f"No logs found for run_id: {run_id}"}, 404

    return {"summary": summary}


@app.get("/debug/env")
async def debug_environment():
    """Debug endpoint to check environment configuration."""
    return {
        "openai_key_present": bool(os.environ.get("OPENAI_API_KEY")),
        "anthropic_key_present": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "orbit_helper_path": os.environ.get("ORBIT_HELPER_PATH"),
        "environment_loaded": True,
    }
