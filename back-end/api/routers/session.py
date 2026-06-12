from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_session_event_hub, get_session_manager
from api.schemas import (
    CalibrationRequest,
    MarkerRequest,
    OpenCameraRequest,
    OpenVideoRequest,
    PauseRequest,
    PpmRequest,
    SessionSnapshot,
    SessionUpdatedEvent,
    SeekRequest,
    SpeedRequest,
)
from core.session_events import SessionEventHub
from core.session_manager import SessionManager

router = APIRouter()


async def _emit_session_state(
    manager: SessionManager,
    hub: SessionEventHub,
    *,
    action: str,
    source_type: str | None = None,
    label: str | None = None,
) -> SessionSnapshot:
    snapshot = SessionSnapshot.model_validate(manager.snapshot())
    event = SessionUpdatedEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        session=snapshot,
        action=action,
        source_type=source_type,
        label=label,
    )
    await hub.broadcast_event(event.model_dump(mode="json"))
    return snapshot


@router.get("", response_model=SessionSnapshot)
async def get_session(manager: SessionManager = Depends(get_session_manager)) -> SessionSnapshot:
    return SessionSnapshot.model_validate(manager.snapshot())


@router.post("/open-video", response_model=SessionSnapshot)
async def open_video(
    payload: OpenVideoRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> SessionSnapshot:
    try:
        manager.open_video(payload.path)
        return await _emit_session_state(
            manager,
            hub,
            action="open-video",
            source_type="video",
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/open-camera", response_model=SessionSnapshot)
async def open_camera(
    payload: OpenCameraRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> SessionSnapshot:
    try:
        manager.open_camera(payload.device_index)
        return await _emit_session_state(
            manager,
            hub,
            action="open-camera",
            source_type="camera",
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pause", response_model=SessionSnapshot)
async def pause_session(
    payload: PauseRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> SessionSnapshot:
    try:
        manager.pause(payload.paused)
        return await _emit_session_state(manager, hub, action="pause")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/seek", response_model=SessionSnapshot)
async def seek_session(
    payload: SeekRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> SessionSnapshot:
    try:
        manager.seek(payload.seconds)
        return await _emit_session_state(manager, hub, action="seek")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/speed", response_model=SessionSnapshot)
async def speed_session(
    payload: SpeedRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> SessionSnapshot:
    try:
        manager.set_speed(payload.speed)
        return await _emit_session_state(manager, hub, action="speed")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ppm", response_model=SessionSnapshot)
async def ppm_session(
    payload: PpmRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> SessionSnapshot:
    try:
        manager.set_ppm(payload.ppm)
        return await _emit_session_state(manager, hub, action="ppm")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/marker", response_model=SessionSnapshot)
async def marker_session(
    payload: MarkerRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> SessionSnapshot:
    try:
        manager.add_marker(payload.label, payload.color)
        return await _emit_session_state(
            manager,
            hub,
            action="marker",
            label=payload.label,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/calibrate", response_model=SessionSnapshot)
async def calibrate_session(
    payload: CalibrationRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> SessionSnapshot:
    try:
        manager.calibrate_auto(
            sample_frames=payload.sample_frames,
            start_frame=payload.start_frame,
            frame_step=payload.frame_step,
        )
        return await _emit_session_state(
            manager,
            hub,
            action="calibrate",
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reset", response_model=SessionSnapshot)
async def reset_session(
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> SessionSnapshot:
    manager.reset()
    return await _emit_session_state(manager, hub, action="reset")
