from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_session_event_hub, get_session_manager
from api.schemas import (
    CalibrationRequest,
    MarkerRequest,
    OpenCameraRequest,
    OpenVideoRequest,
    PauseRequest,
    PpmRequest,
    SeekRequest,
    SpeedRequest,
)
from core.session_events import SessionEventHub
from core.session_manager import SessionManager

router = APIRouter()


async def _emit_session_state(
    manager: SessionManager,
    hub: SessionEventHub,
    event_type: str,
    **extra: object,
) -> dict:
    snapshot = manager.snapshot()
    await hub.broadcast_snapshot(snapshot, event_type=event_type, extra=extra or None)
    return snapshot


@router.get("")
async def get_session(manager: SessionManager = Depends(get_session_manager)) -> dict:
    return manager.snapshot()


@router.post("/open-video")
async def open_video(
    payload: OpenVideoRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> dict:
    try:
        manager.open_video(payload.path)
        return await _emit_session_state(
            manager,
            hub,
            "session.updated",
            action="open-video",
            source_type="video",
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/open-camera")
async def open_camera(
    payload: OpenCameraRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> dict:
    try:
        manager.open_camera(payload.device_index)
        return await _emit_session_state(
            manager,
            hub,
            "session.updated",
            action="open-camera",
            source_type="camera",
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pause")
async def pause_session(
    payload: PauseRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> dict:
    try:
        manager.pause(payload.paused)
        return await _emit_session_state(manager, hub, "session.updated", action="pause")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/seek")
async def seek_session(
    payload: SeekRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> dict:
    try:
        manager.seek(payload.seconds)
        return await _emit_session_state(manager, hub, "session.updated", action="seek")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/speed")
async def speed_session(
    payload: SpeedRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> dict:
    try:
        manager.set_speed(payload.speed)
        return await _emit_session_state(manager, hub, "session.updated", action="speed")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ppm")
async def ppm_session(
    payload: PpmRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> dict:
    try:
        manager.set_ppm(payload.ppm)
        return await _emit_session_state(manager, hub, "session.updated", action="ppm")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/marker")
async def marker_session(
    payload: MarkerRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> dict:
    try:
        manager.add_marker(payload.label, payload.color)
        return await _emit_session_state(
            manager,
            hub,
            "session.updated",
            action="marker",
            label=payload.label,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/calibrate")
async def calibrate_session(
    payload: CalibrationRequest,
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> dict:
    try:
        manager.calibrate_auto(
            sample_frames=payload.sample_frames,
            start_frame=payload.start_frame,
            frame_step=payload.frame_step,
        )
        return await _emit_session_state(
            manager,
            hub,
            "session.updated",
            action="calibrate",
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reset")
async def reset_session(
    manager: SessionManager = Depends(get_session_manager),
    hub: SessionEventHub = Depends(get_session_event_hub),
) -> dict:
    manager.reset()
    return await _emit_session_state(manager, hub, "session.updated", action="reset")
