from __future__ import annotations

import asyncio
from base64 import b64encode
from datetime import datetime, timezone
import threading
import time
from typing import Any

import cv2

from api.schemas import FramePayload, FrameUpdateEvent, SessionSnapshot, SessionTelemetry
from core.session_events import SessionEventHub
from core.session_manager import SessionManager
from processing.horse_tracker import HorseTracker


def _format_timecode(position_seconds: float | None) -> str:
    if position_seconds is None:
      return "--:--.--"

    total_ms = max(0, int(position_seconds * 1000))
    minutes = total_ms // 60000
    seconds = (total_ms // 1000) % 60
    millis = (total_ms % 1000) // 10
    return f"{minutes:02d}:{seconds:02d}.{millis:02d}"


class SessionFrameStreamer:
    def __init__(self, manager: SessionManager, hub: SessionEventHub) -> None:
        self._manager = manager
        self._hub = hub
        self._tracker = HorseTracker()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last_session_id: int | None = None
        self._last_calibration_signature: str | None = None
        self._frame_index = 0
        self._last_telemetry: dict[str, Any] = {
            "speed_kmh": 0.0,
            "distance_m": 0.0,
            "timecode": "--:--.--",
            "fps": 0.0,
            "confidence": 0.0,
            "bbox": None,
            "center": None,
            "horse_bbox": None,
        }

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._loop = loop
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="session-frame-streamer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        assert self._loop is not None

        while not self._stop_event.is_set():
            loop_started = time.perf_counter()
            snapshot = self._manager.snapshot()
            session_id = int(snapshot.get("session_id") or 0)

            if self._last_session_id != session_id:
                self._tracker.reset()
                self._last_session_id = session_id
                self._last_calibration_signature = None
                self._frame_index = 0
                self._last_telemetry = {
                    "speed_kmh": 0.0,
                    "distance_m": 0.0,
                    "timecode": "--:--.--",
                    "fps": 0.0,
                    "confidence": 0.0,
                    "bbox": None,
                    "center": None,
                    "horse_bbox": None,
                }

            calibration = snapshot.get("calibration") or None
            calibration_signature = str(calibration) if calibration else None
            if calibration and calibration_signature != self._last_calibration_signature:
                try:
                    self._tracker.setup_homography(calibration)
                    self._last_calibration_signature = calibration_signature
                except Exception as exc:
                    self._manager.last_error = f"Falha ao aplicar calibração: {exc}"

            if not snapshot.get("is_running") or snapshot.get("source_type") == "idle":
                self._sleep(0.05)
                continue

            if snapshot.get("is_paused"):
                self._broadcast_snapshot(snapshot, "session.snapshot")
                self._sleep(0.08)
                continue

            ok, frame, frame_snapshot = self._manager.read_frame()
            if not ok or frame is None:
                self._broadcast_snapshot(frame_snapshot, "session.updated", action="capture-ended")
                self._sleep(0.08)
                continue

            self._frame_index += 1
            fps = float(frame_snapshot.get("capture", {}).get("fps") or 30.0)
            source_type = frame_snapshot.get("source_type")
            analysis_stride = 1 if source_type != "video" else 3
            should_analyze = source_type != "video" or (self._frame_index % analysis_stride == 0)

            if should_analyze:
                processed_frame, telemetry = self._process_frame(frame, frame_snapshot)
                self._last_telemetry = telemetry
                session_snapshot = self._manager.update_telemetry(telemetry)
                frame_to_send = processed_frame
            else:
                session_snapshot = self._manager.snapshot()
                telemetry = dict(session_snapshot.get("telemetry") or self._last_telemetry)
                # Mantém a última box desenhada nos frames intermediários para evitar flicker.
                frame_to_send = self._tracker.draw_tracking(frame, None, None)

            frame_to_send = self._resize_frame(frame_to_send)
            encoded_frame = self._encode_frame(frame_to_send)
            if encoded_frame is None:
                self._sleep(0.02)
                continue

            frame_payload = FramePayload(
                mime_type="image/jpeg",
                width=int(frame_to_send.shape[1]),
                height=int(frame_to_send.shape[0]),
                data=encoded_frame,
            )

            payload = FrameUpdateEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                session=SessionSnapshot.model_validate(session_snapshot),
                frame=frame_payload,
                telemetry=SessionTelemetry.model_validate(telemetry),
            )
            self._broadcast(payload.model_dump(mode="json"))

            speed_factor = max(0.1, float(frame_snapshot.get("speed") or 1.0))
            if source_type == "video":
                target_interval = (1.0 / fps) / speed_factor
                elapsed = time.perf_counter() - loop_started
                if elapsed > target_interval * 1.5:
                    frames_to_skip = int(elapsed / target_interval) - 1
                    if frames_to_skip > 0:
                        skipped_snapshot = self._manager.skip_frames(frames_to_skip)
                        if skipped_snapshot.get("last_error"):
                            self._broadcast_snapshot(skipped_snapshot, "session.updated", action="capture-ended")
                            self._sleep(0.08)
                            continue
                self._sleep(max(0.0, target_interval - elapsed))
            else:
                self._sleep(0.001)

    def _process_frame(self, frame: Any, snapshot: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        fps = float(snapshot.get("capture", {}).get("fps") or 30.0)
        horse_bbox, horse_center, _ = self._tracker.track(frame, fps=fps)
        processed_frame = self._tracker.draw_tracking(frame, horse_bbox, horse_center)

        primary_speed = 0.0
        primary_distance = 0.0
        primary_conf = 0.0
        primary_bbox = None

        with self._tracker.lock:
            if self._tracker.tracked_horses:
                best_tid = max(
                    self._tracker.tracked_horses,
                    key=lambda key: self._tracker.tracked_horses[key].get("conf", 0.0),
                )
                primary = self._tracker.tracked_horses[best_tid]
                primary_speed = float(primary.get("speed", 0.0))
                primary_distance = float(primary.get("dist_total_m", 0.0))
                primary_conf = float(primary.get("conf", 0.0))
                primary_bbox = primary.get("final_bbox")

        timecode = _format_timecode(snapshot.get("capture", {}).get("position_seconds"))
        telemetry = {
            "speed_kmh": round(primary_speed, 2),
            "distance_m": round(primary_distance, 2),
            "timecode": timecode,
            "fps": fps,
            "confidence": round(primary_conf, 3),
            "bbox": primary_bbox,
            "center": horse_center,
            "horse_bbox": horse_bbox,
        }
        return processed_frame, telemetry

    def _encode_frame(self, frame: Any) -> str | None:
        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 72])
        if not ok:
            return None
        return b64encode(buffer.tobytes()).decode("ascii")

    def _resize_frame(self, frame: Any, max_width: int = 720) -> Any:
        height, width = frame.shape[:2]
        if width <= max_width:
            return frame

        scale = max_width / float(width)
        new_width = max(1, int(width * scale))
        new_height = max(1, int(height * scale))
        return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    def _broadcast(self, payload: dict[str, Any]) -> None:
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._hub.broadcast_event(payload), self._loop)

    def _broadcast_snapshot(self, session: dict[str, Any], event_type: str, **extra: Any) -> None:
        payload: dict[str, Any] = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session": SessionSnapshot.model_validate(session).model_dump(mode="json"),
        }
        if extra:
            payload.update(extra)
        self._broadcast(payload)

    def _sleep(self, seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end and not self._stop_event.is_set():
            time.sleep(min(0.02, end - time.time()))
