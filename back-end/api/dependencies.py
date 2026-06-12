from starlette.requests import HTTPConnection

from core.session_events import SessionEventHub
from core.session_manager import SessionManager
from core.frame_streamer import SessionFrameStreamer


def get_session_manager(connection: HTTPConnection) -> SessionManager:
    return connection.app.state.session_manager


def get_session_event_hub(connection: HTTPConnection) -> SessionEventHub:
    return connection.app.state.session_event_hub


def get_session_streamer(connection: HTTPConnection) -> SessionFrameStreamer:
    return connection.app.state.session_streamer
