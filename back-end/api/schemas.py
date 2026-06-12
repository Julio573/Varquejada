from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OpenVideoRequest(BaseModel):
    path: str = Field(..., description="Caminho local do arquivo de vídeo.")


class OpenCameraRequest(BaseModel):
    device_index: int = Field(0, ge=0, description="Índice da câmera.")


class PauseRequest(BaseModel):
    paused: bool | None = Field(
        default=None,
        description="Se omitido, alterna entre pausado e reproduzindo.",
    )


class SeekRequest(BaseModel):
    seconds: float = Field(..., description="Deslocamento relativo em segundos.")


class SpeedRequest(BaseModel):
    speed: float = Field(..., gt=0, description="Velocidade de reprodução.")


class PpmRequest(BaseModel):
    ppm: float = Field(..., gt=0, description="Pixels por metro.")


class MarkerRequest(BaseModel):
    label: str = Field(..., min_length=1)
    color: str = Field(default="#3B82F6")


class CalibrationRequest(BaseModel):
    sample_frames: int = Field(default=10, ge=1, le=60)
    start_frame: int = Field(default=30, ge=0)
    frame_step: int = Field(default=15, ge=1, le=120)


class ReportItem(BaseModel):
    filename: str
    path: str
    size_bytes: int
    modified_at: str


class CaptureInfo(BaseModel):
    fps: float | None = None
    frame_count: int | None = None
    width: int | None = None
    height: int | None = None
    position_ms: int | None = None
    position_seconds: float | None = None
    duration_ms: int | None = None
    duration_seconds: float | None = None


class SessionTelemetry(BaseModel):
    speed_kmh: float = 0.0
    distance_m: float = 0.0
    timecode: str = "--:--.--"
    fps: float = 0.0
    confidence: float = 0.0
    bbox: list[float] | None = None
    center: list[float] | None = None
    horse_bbox: list[float] | None = None


class SessionSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_type: str
    source_value: str | int | None
    session_id: int = 0
    session_started_at: str | None = None
    session_finished_at: str | None = None
    is_running: bool = False
    is_paused: bool = False
    speed: float = 1.0
    ppm: float | None = None
    verdict: str = "TELEMETRIA"
    markers: list[dict[str, object]] = Field(default_factory=list)
    calibration: dict[str, object] | None = None
    telemetry: SessionTelemetry = Field(default_factory=SessionTelemetry)
    telemetry_history_count: int = 0
    last_report_path: str | None = None
    last_error: str | None = None
    capture: CaptureInfo | None = None


class SessionEventBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: str
    session: SessionSnapshot


class SessionSnapshotEvent(SessionEventBase):
    type: Literal["session.snapshot"] = "session.snapshot"


class SessionUpdatedEvent(SessionEventBase):
    type: Literal["session.updated"] = "session.updated"
    action: str | None = None
    source_type: str | None = None
    label: str | None = None


class SessionPongEvent(SessionEventBase):
    type: Literal["session.pong"] = "session.pong"


class FramePayload(BaseModel):
    mime_type: str
    encoding: Literal["base64"] = "base64"
    width: int
    height: int
    data: str


class FrameUpdateEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["frame.update"] = "frame.update"
    timestamp: str
    session: SessionSnapshot
    frame: FramePayload | None = None
    telemetry: SessionTelemetry


BackendStreamEvent = SessionSnapshotEvent | SessionUpdatedEvent | SessionPongEvent | FrameUpdateEvent
