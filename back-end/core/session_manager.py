from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import threading
import sys

import cv2

from processing.auto_calibration import AutoCalibrator


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


@dataclass
class SessionManager:
    source_type: str = "idle"
    source_value: str | int | None = None
    session_id: int = 0
    is_running: bool = False
    is_paused: bool = False
    speed: float = 1.0
    ppm: float | None = None
    verdict: str = "TELEMETRIA"
    markers: list[dict[str, Any]] = field(default_factory=list)
    calibration: dict[str, Any] | None = None
    telemetry: dict[str, Any] = field(default_factory=dict)
    last_error: str | None = None

    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _capture: cv2.VideoCapture | None = field(default=None, init=False, repr=False)
    _calibrator: AutoCalibrator = field(default_factory=AutoCalibrator, init=False, repr=False)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            capture_info = self._capture_info_locked()
            return {
                "source_type": self.source_type,
                "source_value": self.source_value,
                "session_id": self.session_id,
                "is_running": self.is_running,
                "is_paused": self.is_paused,
                "speed": self.speed,
                "ppm": self.ppm,
                "verdict": self.verdict,
                "markers": [dict(marker) for marker in self.markers],
                "calibration": dict(self.calibration) if self.calibration else None,
                "telemetry": dict(self.telemetry),
                "last_error": self.last_error,
                "capture": capture_info,
            }

    def open_video(self, path: str) -> dict[str, Any]:
        video_path = Path(path).expanduser().resolve()
        if not video_path.exists():
            raise ValueError(f"Arquivo de vídeo não encontrado: {video_path}")

        return self._open_capture("video", str(video_path))

    def open_camera(self, device_index: int = 0) -> dict[str, Any]:
        return self._open_capture("camera", int(device_index))

    def pause(self, paused: bool | None = None) -> dict[str, Any]:
        with self._lock:
            self._ensure_capture_locked()
            self.is_paused = (not self.is_paused) if paused is None else bool(paused)
            self.last_error = None
            return self.snapshot()

    def seek(self, seconds: float) -> dict[str, Any]:
        with self._lock:
            self._ensure_capture_locked()
            if self.source_type != "video":
                raise ValueError("Seek só está disponível para fontes de vídeo.")

            current_ms = float(self._capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
            target_ms = max(0.0, current_ms + (float(seconds) * 1000.0))
            duration_ms = self._duration_ms_locked()
            if duration_ms is not None:
                target_ms = min(target_ms, duration_ms)

            self._capture.set(cv2.CAP_PROP_POS_MSEC, target_ms)
            self.last_error = None
            return self.snapshot()

    def set_speed(self, speed: float) -> dict[str, Any]:
        with self._lock:
            self._ensure_capture_locked()
            self.speed = _clamp(float(speed), 0.1, 5.0)
            self.last_error = None
            return self.snapshot()

    def set_ppm(self, ppm: float) -> dict[str, Any]:
        with self._lock:
            value = float(ppm)
            if value <= 0:
                raise ValueError("ppm deve ser maior que zero.")
            self.ppm = value
            self.calibration = self.calibration or {}
            self.calibration["ppm"] = value
            self.last_error = None
            return self.snapshot()

    def add_marker(self, label: str, color: str = "#3B82F6") -> dict[str, Any]:
        with self._lock:
            marker = {
                "label": label,
                "color": color,
                "position_ms": self._position_ms_locked(),
            }
            self.markers.append(marker)
            self.last_error = None
            return self.snapshot()

    def calibrate_auto(
        self,
        sample_frames: int = 10,
        start_frame: int = 30,
        frame_step: int = 15,
    ) -> dict[str, Any]:
        with self._lock:
            self._ensure_capture_locked()
            if self.source_type != "video" or not isinstance(self.source_value, str):
                raise ValueError("Calibração automática só está disponível para arquivos de vídeo.")

            temp_cap = cv2.VideoCapture(self.source_value)
            if not temp_cap.isOpened():
                raise RuntimeError("Não foi possível abrir o vídeo para calibração.")

            try:
                temp_cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(start_frame)))

                for _ in range(max(1, int(sample_frames))):
                    ret, frame = temp_cap.read()
                    if not ret or frame is None:
                        break

                    calib_data = self._calibrator.calibrate(frame)
                    if calib_data:
                        self.ppm = float(calib_data["ppm"])
                        self.calibration = dict(calib_data)
                        self.last_error = None
                        return self.snapshot()

                    current_frame = temp_cap.get(cv2.CAP_PROP_POS_FRAMES) or 0
                    temp_cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame + max(1, int(frame_step)))

                raise RuntimeError("Não foi possível calibrar automaticamente a partir do vídeo.")
            finally:
                temp_cap.release()

    def reset(self) -> None:
        with self._lock:
            self._release_capture_locked()
            self.source_type = "idle"
            self.source_value = None
            self.session_id += 1
            self.is_running = False
            self.is_paused = False
            self.speed = 1.0
            self.ppm = None
            self.verdict = "TELEMETRIA"
            self.markers.clear()
            self.calibration = None
            self.telemetry.clear()
            self.last_error = None

    def read_frame(self) -> tuple[bool, Any | None, dict[str, Any]]:
        with self._lock:
            self._ensure_capture_locked()

            if self.is_paused:
                return False, None, self.snapshot()

            ret, frame = self._capture.read()
            if not ret or frame is None:
                self.is_running = False
                self.last_error = "Fim da captura."
                return False, None, self.snapshot()

            self.last_error = None
            return True, frame, self.snapshot()

    def skip_frames(self, count: int) -> dict[str, Any]:
        with self._lock:
            self._ensure_capture_locked()
            skips = max(0, int(count))
            for _ in range(skips):
                ret = self._capture.grab()
                if not ret:
                    self.is_running = False
                    self.last_error = "Fim da captura."
                    break

            return self.snapshot()

    def update_telemetry(self, telemetry: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.telemetry = dict(telemetry)
            if "speed" in telemetry:
                try:
                    self.verdict = telemetry.get("verdict", self.verdict)
                except Exception:
                    pass
            return self.snapshot()

    def _open_capture(self, source_type: str, source_value: str | int) -> dict[str, Any]:
        with self._lock:
            self._release_capture_locked()

            if source_type == "video":
                capture = cv2.VideoCapture(source_value)
            elif source_type == "camera":
                if sys.platform.startswith("linux"):
                    capture = cv2.VideoCapture(source_value, cv2.CAP_V4L2)
                else:
                    capture = cv2.VideoCapture(source_value)
            else:
                raise ValueError(f"Tipo de fonte inválido: {source_type}")

            if not capture.isOpened():
                capture.release()
                self.last_error = f"Falha ao abrir a fonte: {source_value}"
                raise RuntimeError(self.last_error)

            if source_type == "camera":
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            self._capture = capture
            self.source_type = source_type
            self.source_value = source_value
            self.session_id += 1
            self.is_running = True
            self.is_paused = False
            self.speed = 1.0
            self.verdict = "TELEMETRIA"
            self.markers.clear()
            self.calibration = None
            self.telemetry.clear()
            self.ppm = None
            self.last_error = None
            return self.snapshot()

    def _ensure_capture_locked(self) -> None:
        if self._capture is None or not self._capture.isOpened():
            self.is_running = False
            raise RuntimeError("Não há captura ativa.")

    def _release_capture_locked(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def _capture_info_locked(self) -> dict[str, Any] | None:
        if self._capture is None or not self._capture.isOpened():
            return None

        fps = float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        position_ms = self._position_ms_locked()
        duration_ms = self._duration_ms_locked()

        return {
            "fps": fps or None,
            "frame_count": frame_count or None,
            "width": width or None,
            "height": height or None,
            "position_ms": position_ms,
            "position_seconds": round(position_ms / 1000.0, 3) if position_ms is not None else None,
            "duration_ms": duration_ms,
            "duration_seconds": round(duration_ms / 1000.0, 3) if duration_ms is not None else None,
        }

    def _position_ms_locked(self) -> int | None:
        if self._capture is None or not self._capture.isOpened():
            return None

        position_ms = float(self._capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
        if position_ms > 0:
            return int(position_ms)

        frame_index = float(self._capture.get(cv2.CAP_PROP_POS_FRAMES) or 0.0)
        fps = float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0)
        if frame_index > 0 and fps > 0:
            return int((frame_index / fps) * 1000.0)

        return 0

    def _duration_ms_locked(self) -> int | None:
        if self._capture is None or not self._capture.isOpened():
            return None

        frame_count = float(self._capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
        fps = float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0)
        if frame_count > 0 and fps > 0:
            return int((frame_count / fps) * 1000.0)

        return None
