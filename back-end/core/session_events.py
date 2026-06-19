from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket


@dataclass(slots=True)
class _ClientConnection:
    websocket: WebSocket
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=lambda: asyncio.Queue(maxsize=2))
    sender_task: asyncio.Task[None] | None = None


class SessionEventHub:
    def __init__(self) -> None:
        self._clients: dict[WebSocket, _ClientConnection] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        connection = _ClientConnection(websocket=websocket)
        connection.sender_task = asyncio.create_task(self._client_sender(connection))
        async with self._lock:
            self._clients[websocket] = connection

    async def disconnect(self, websocket: WebSocket) -> None:
        connection: _ClientConnection | None = None
        async with self._lock:
            connection = self._clients.pop(websocket, None)

        if connection and connection.sender_task:
            connection.sender_task.cancel()
            try:
                await connection.sender_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

    async def broadcast_event(self, payload: dict[str, Any]) -> None:
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()

        async with self._lock:
            clients = list(self._clients.values())

        for connection in clients:
            self._enqueue_latest(connection, dict(payload))

    async def broadcast_snapshot(
        self,
        session: dict[str, Any],
        event_type: str = "session.snapshot",
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session": session,
        }
        if extra:
            payload.update(extra)

        await self.broadcast_event(payload)

    def _enqueue_latest(self, connection: _ClientConnection, payload: dict[str, Any]) -> None:
        queue = connection.queue
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # Se o cliente estiver muito lento, preservamos apenas o evento mais recente.
                pass

    async def _client_sender(self, connection: _ClientConnection) -> None:
        websocket = connection.websocket
        queue = connection.queue

        try:
            while True:
                payload = await queue.get()
                await websocket.send_json(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Cliente desconectado ou fora de sincronia.
            pass
