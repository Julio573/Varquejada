from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from api.dependencies import get_session_event_hub, get_session_manager
from core.session_events import SessionEventHub
from core.session_manager import SessionManager

router = APIRouter()


@router.websocket("/session")
async def session_stream(
    websocket: WebSocket,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> None:
    await hub.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "session.snapshot",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session": manager.snapshot(),
            }
        )

        while True:
            message = await websocket.receive_text()
            normalized = message.strip().lower()

            if normalized in {"ping", "pong"}:
                await websocket.send_json(
                    {
                        "type": "session.pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "session": manager.snapshot(),
                    }
                )
            elif normalized == "snapshot":
                await websocket.send_json(
                    {
                        "type": "session.snapshot",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "session": manager.snapshot(),
                    }
                )
    except WebSocketDisconnect:
        return
    finally:
        await hub.disconnect(websocket)
