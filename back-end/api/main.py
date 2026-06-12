import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.health import router as health_router
from api.routers.media import router as media_router
from api.routers.session import router as session_router
from api.routers.session_ws import router as session_ws_router
from core.frame_streamer import SessionFrameStreamer
from core.session_events import SessionEventHub
from core.config import settings
from core.session_manager import SessionManager


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API do backend do Varquejada System para integração com Electron.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.session_manager = SessionManager()
    app.state.session_event_hub = SessionEventHub()
    app.state.session_streamer = None

    app.include_router(health_router)
    app.include_router(media_router, prefix="/media", tags=["media"])
    app.include_router(session_router, prefix="/session", tags=["session"])
    app.include_router(session_ws_router, prefix="/ws", tags=["session-ws"])

    @app.on_event("startup")
    async def start_streamer() -> None:
        streamer = SessionFrameStreamer(app.state.session_manager, app.state.session_event_hub)
        streamer.start(asyncio.get_running_loop())
        app.state.session_streamer = streamer

    @app.on_event("shutdown")
    async def stop_streamer() -> None:
        streamer = app.state.session_streamer
        if streamer is not None:
            streamer.stop()

    return app


app = create_app()
