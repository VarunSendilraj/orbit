"""
WebSocket step broadcasting system for real-time step updates.
Manages WebSocket connections and broadcasts step events to all connected clients.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, Set

from fastapi import WebSocket


class StepBus:
    """
    Manages WebSocket connections and broadcasts step events.
    Handles client registration, unregistration, and message broadcasting.
    """

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register(self, ws: WebSocket) -> None:
        """Register a new WebSocket client and accept the connection."""
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def unregister(self, ws: WebSocket) -> None:
        """Unregister a WebSocket client."""
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.
        Automatically handles dead connections by removing them.
        """
        if not self._clients:
            return

        dead_clients = []
        for ws in list(self._clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead_clients.append(ws)

        # Clean up dead connections
        for ws in dead_clients:
            await self.unregister(ws)


# Global step bus instance
bus = StepBus()


def new_run_id() -> str:
    """Generate a new unique run ID."""
    return uuid.uuid4().hex


def stamp() -> float:
    """Get current timestamp."""
    return time.time()
