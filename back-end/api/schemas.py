from pydantic import BaseModel, Field


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
