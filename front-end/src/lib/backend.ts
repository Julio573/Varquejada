export type BackendHealth = {
  status: string;
  app: string;
  version: string;
  timestamp: string;
};

export type BackendSession = {
  source_type: string;
  source_value: string | number | null;
  session_id?: number;
  session_started_at?: string | null;
  session_finished_at?: string | null;
  is_running: boolean;
  is_paused: boolean;
  speed: number;
  ppm: number | null;
  verdict: string;
  markers: Array<Record<string, unknown>>;
  calibration: Record<string, unknown> | null;
  telemetry?: Record<string, unknown>;
  telemetry_history_count?: number;
  last_report_path?: string | null;
  last_error: string | null;
  capture: BackendCapture | null;
};

export type BackendSessionEvent = {
  type: string;
  timestamp: string;
  session: BackendSession;
  action?: string;
  source_type?: string;
  label?: string;
};

export type BackendFrameEvent = {
  type: "frame.update";
  timestamp: string;
  session: BackendSession;
  frame?: {
    mime_type: string;
    encoding: "base64";
    width: number;
    height: number;
    data: string;
  };
  telemetry: {
    speed_kmh: number;
    distance_m: number;
    timecode: string;
    fps: number;
    confidence: number;
    bbox: number[] | null;
    center: [number, number] | null;
    horse_bbox: number[] | null;
  };
};

export type BackendStreamEvent = BackendSessionEvent | BackendFrameEvent;

export type BackendCapture = {
  fps: number | null;
  frame_count: number | null;
  width: number | null;
  height: number | null;
  position_ms: number | null;
  position_seconds: number | null;
  duration_ms: number | null;
  duration_seconds: number | null;
};

export type BackendReportItem = {
  filename: string;
  path: string;
  size_bytes: number;
  modified_at: string;
};

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;

function toWebSocketUrl(path: string) {
  const url = new URL(path, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function createBackendMediaUrl(path: string) {
  const url = new URL("/media/file", API_BASE_URL);
  url.searchParams.set("path", path);
  return url.toString();
}

export function createBackendReportUrl() {
  return new URL("/reports/latest", API_BASE_URL).toString();
}

async function requestJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });
  if (!response.ok) {
    throw new Error(`API error ${response.status} on ${path}`);
  }
  return (await response.json()) as T;
}

async function postJson<T>(
  path: string,
  body: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    let detail = `API error ${response.status} on ${path}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // Mantém a mensagem genérica quando o corpo não for JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function fetchBackendHealth(signal?: AbortSignal) {
  return requestJson<BackendHealth>("/health", signal);
}

export function fetchBackendSession(signal?: AbortSignal) {
  return requestJson<BackendSession>("/session", signal);
}

export function fetchBackendReports(signal?: AbortSignal) {
  return requestJson<BackendReportItem[]>("/reports", signal);
}

export function openBackendVideo(path: string) {
  return postJson<BackendSession>("/session/open-video", { path });
}

export function openBackendCamera(deviceIndex = 0) {
  return postJson<BackendSession>("/session/open-camera", { device_index: deviceIndex });
}

export function toggleBackendPause(paused?: boolean) {
  return postJson<BackendSession>("/session/pause", { paused: paused ?? null });
}

export function seekBackendSession(seconds: number) {
  return postJson<BackendSession>("/session/seek", { seconds });
}

export function setBackendSpeed(speed: number) {
  return postJson<BackendSession>("/session/speed", { speed });
}

export function setBackendPpm(ppm: number) {
  return postJson<BackendSession>("/session/ppm", { ppm });
}

export function addBackendMarker(label: string, color = "#3B82F6") {
  return postJson<BackendSession>("/session/marker", { label, color });
}

export function calibrateBackendSession(sampleFrames = 10, startFrame = 30, frameStep = 15) {
  return postJson<BackendSession>("/session/calibrate", {
    sample_frames: sampleFrames,
    start_frame: startFrame,
    frame_step: frameStep,
  });
}

export function resetBackendSession() {
  return postJson<BackendSession>("/session/reset", {});
}

export async function downloadLatestBackendReport(filename = "relatorio-ultima-corrida.pdf") {
  const response = await fetch(createBackendReportUrl());
  if (!response.ok) {
    let detail = `API error ${response.status} on /reports/latest`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // fallback para mensagem genérica
    }
    throw new Error(detail);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.rel = "noreferrer";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  }
}

export function createBackendSessionSocket(
  onEvent: (event: BackendStreamEvent) => void,
  onStatus?: (message: string) => void,
) {
  if (typeof window === "undefined") {
    return () => {};
  }

  let closed = false;
  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;

  const connect = () => {
    if (closed) return;

    socket = new WebSocket(toWebSocketUrl("/ws/session"));

    socket.addEventListener("open", () => {
      onStatus?.("WebSocket conectado");
    });

    socket.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(String(event.data)) as BackendStreamEvent;
        if (payload && typeof payload === "object" && "session" in payload) {
          onEvent(payload);
          if (payload.type === "session.updated" && "action" in payload && payload.action) {
            onStatus?.(`Atualizado: ${payload.action}`);
          } else if (payload.type === "frame.update" && "frame" in payload && payload.frame) {
            onStatus?.("Frame atualizado");
          } else if (payload.type === "frame.update") {
            onStatus?.("Telemetria atualizada");
          }
        }
      } catch {
        // Ignora mensagens fora do protocolo esperado.
      }
    });

    socket.addEventListener("close", () => {
      onStatus?.("WebSocket desconectado");
      if (closed) return;
      reconnectTimer = window.setTimeout(connect, 2000);
    });

    socket.addEventListener("error", () => {
      socket?.close();
    });
  };

  connect();

  return () => {
    closed = true;
    if (reconnectTimer) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    socket?.close();
  };
}
