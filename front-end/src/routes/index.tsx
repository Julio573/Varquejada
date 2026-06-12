import { createFileRoute, useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import {
  Home,
  LineChart,
  Calendar,
  Settings,
  Video,
  Crosshair,
  FileText,
  Clock,
  Ruler,
  Radio,
  Upload,
  Camera,
  Target,
  Flag,
  FileQuestion,
  ArrowRight,
  Play,
  Pause,
  FolderOpen,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Maximize2,
} from "lucide-react";

import {
  API_BASE_URL,
  addBackendMarker,
  calibrateBackendSession,
  createBackendSessionSocket,
  createBackendMediaUrl,
  fetchBackendHealth,
  fetchBackendSession,
  openBackendCamera,
  openBackendVideo,
  resetBackendSession,
  seekBackendSession,
  setBackendSpeed,
  toggleBackendPause,
  type BackendHealth,
  type BackendCapture,
  type BackendFrameEvent,
  type BackendSession,
} from "@/lib/backend";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "VeloVaquejo Pro — Sistema de Medição de Velocidade" },
      {
        name: "description",
        content:
          "Painel profissional para análise e medição de velocidade em eventos de vaquejada.",
      },
    ],
    links: [
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap",
      },
    ],
  }),
  component: Dashboard,
});

function useClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

async function loadBackendSnapshot(
  setBackendHealth: React.Dispatch<React.SetStateAction<BackendHealth | null>>,
  setBackendSession: React.Dispatch<React.SetStateAction<BackendSession | null>>,
  setBackendError: React.Dispatch<React.SetStateAction<string | null>>,
  signal?: AbortSignal,
) {
  try {
    const [health, session] = await Promise.all([
      fetchBackendHealth(signal),
      fetchBackendSession(signal),
    ]);
    setBackendHealth(health);
    setBackendSession(session);
    setBackendError(null);
  } catch (error) {
    setBackendHealth(null);
    setBackendSession(null);
    setBackendError(error instanceof Error ? error.message : "Falha ao conectar ao backend");
  }
}

function formatClock(seconds: number | null | undefined) {
  if (seconds == null || Number.isNaN(seconds)) {
    return "--:--.--";
  }

  const totalMs = Math.max(0, Math.floor(seconds * 1000));
  const minutes = Math.floor(totalMs / 60000);
  const remainingSeconds = Math.floor((totalMs % 60000) / 1000);
  const millis = totalMs % 1000;
  return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}.${String(Math.floor(millis / 10)).padStart(2, "0")}`;
}

function formatSourceLabel(session: BackendSession | null) {
  if (!session) {
    return "Aguardando fonte";
  }

  if (session.source_type === "video" && typeof session.source_value === "string") {
    return session.source_value.split(/[\\/]/).pop() || session.source_value;
  }

  if (session.source_type === "camera") {
    return `Câmera ${session.source_value ?? 0}`;
  }

  return "Fonte não definida";
}

function formatCaptureInfo(capture: BackendCapture | null) {
  if (!capture) {
    return {
      resolution: "--",
      fps: "--",
      position: "--",
      duration: "--",
    };
  }

  return {
    resolution: capture.width && capture.height ? `${capture.width} × ${capture.height}` : "--",
    fps: capture.fps ? capture.fps.toFixed(1) : "--",
    position: formatClock(capture.position_seconds),
    duration: formatClock(capture.duration_seconds),
  };
}

function hasRenderableBox(telemetry: BackendFrameEvent["telemetry"] | null) {
  const rawBox = telemetry?.horse_bbox ?? telemetry?.bbox;
  return Array.isArray(rawBox) && rawBox.length >= 4;
}

function drawTrackingOverlay(
  canvas: HTMLCanvasElement,
  sourceWidth: number,
  sourceHeight: number,
  telemetry: BackendFrameEvent["telemetry"] | null,
) {
  const context = canvas.getContext("2d");
  if (!context) return;

  const rect = canvas.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0 || sourceWidth <= 0 || sourceHeight <= 0) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    return;
  }

  const dpr = window.devicePixelRatio || 1;
  const nextWidth = Math.max(1, Math.floor(rect.width * dpr));
  const nextHeight = Math.max(1, Math.floor(rect.height * dpr));
  if (canvas.width !== nextWidth || canvas.height !== nextHeight) {
    canvas.width = nextWidth;
    canvas.height = nextHeight;
  }

  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, rect.width, rect.height);

  const rawBox = telemetry?.horse_bbox ?? telemetry?.bbox;
  if (!rawBox || rawBox.length < 4) {
    return;
  }

  const [rawX, rawY, rawW, rawH] = rawBox;
  const scale = Math.min(rect.width / sourceWidth, rect.height / sourceHeight);
  const drawnWidth = sourceWidth * scale;
  const drawnHeight = sourceHeight * scale;
  const offsetX = (rect.width - drawnWidth) / 2;
  const offsetY = (rect.height - drawnHeight) / 2;

  const x = offsetX + rawX * scale;
  const y = offsetY + rawY * scale;
  const w = rawW * scale;
  const h = rawH * scale;
  const centerX = x + w / 2;

  const speed = telemetry?.speed_kmh ?? 0;
  const confidence = Math.round((telemetry?.confidence ?? 0) * 100);
  const badgeText = `${speed.toFixed(1)} KM/H  •  ${confidence}%`;

  const accent = "#F0903A";
  const accentSoft = "rgba(240, 144, 58, 0.14)";
  const border = "rgba(255, 255, 255, 0.85)";
  const panel = "rgba(10, 12, 18, 0.82)";

  context.font = "600 13px Rajdhani, Inter, sans-serif";
  const textWidth = context.measureText(badgeText).width;
  const badgeWidth = Math.max(138, Math.ceil(textWidth + 32));
  const badgeHeight = 34;
  const badgeX = Math.max(8, Math.min(rect.width - badgeWidth - 8, centerX - badgeWidth / 2));
  const badgeY = Math.max(8, y - badgeHeight - 16);

  const drawRoundedRect = (x0: number, y0: number, width: number, height: number, radius: number) => {
    const x1 = x0 + width;
    const y1 = y0 + height;
    const r = Math.min(radius, width / 2, height / 2);
    context.beginPath();
    context.moveTo(x0 + r, y0);
    context.lineTo(x1 - r, y0);
    context.quadraticCurveTo(x1, y0, x1, y0 + r);
    context.lineTo(x1, y1 - r);
    context.quadraticCurveTo(x1, y1, x1 - r, y1);
    context.lineTo(x0 + r, y1);
    context.quadraticCurveTo(x0, y1, x0, y1 - r);
    context.lineTo(x0, y0 + r);
    context.quadraticCurveTo(x0, y0, x0 + r, y0);
    context.closePath();
  };

  context.lineWidth = 2;
  context.strokeStyle = accent;
  context.fillStyle = accentSoft;
  drawRoundedRect(x, y, w, h, 12);
  context.fill();
  context.stroke();

  context.fillStyle = panel;
  context.strokeStyle = "rgba(255, 255, 255, 0.14)";
  drawRoundedRect(badgeX, badgeY, badgeWidth, badgeHeight, 14);
  context.fill();
  context.stroke();

  context.fillStyle = accent;
  drawRoundedRect(badgeX, badgeY, 5, badgeHeight, 14);
  context.fill();

  context.strokeStyle = accent;
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(centerX, badgeY + badgeHeight);
  context.lineTo(centerX, Math.max(badgeY + badgeHeight + 10, y - 3));
  context.stroke();

  context.fillStyle = border;
  context.textBaseline = "middle";
  context.fillText(badgeText, badgeX + 15, badgeY + badgeHeight / 2 + 0.5);
}

function formatFileUrl(filePath: string) {
  if (typeof window !== "undefined" && window.electronAPI?.pathToFileUrl) {
    return window.electronAPI.pathToFileUrl(filePath);
  }

  return `file://${encodeURI(filePath)}`;
}

const navItems = [
  { icon: Home, label: "Painel Principal", to: "/" },
  {
    icon: LineChart,
    label: "Medições",
    to: "/analysis",
    action: "open-analysis-window",
  },
  { icon: Calendar, label: "Histórico" },
  { icon: Settings, label: "Configurações" },
  { icon: Video, label: "Câmeras" },
  { icon: Crosshair, label: "Calibração" },
  { icon: FileText, label: "Relatórios", to: "/reports" },
];

function HorseLogo({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 54 C 14 38, 22 30, 30 28 L 26 20 L 32 22 L 36 14 L 40 22 C 48 24, 54 32, 54 42 L 48 42 L 46 36 L 42 38 L 40 54" />
      <circle cx="42" cy="24" r="1.2" fill="currentColor" />
    </svg>
  );
}

function Dashboard() {
  const now = useClock();
  const location = useLocation();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const playerShellRef = useRef<HTMLDivElement | null>(null);
  const controlsTimerRef = useRef<number | null>(null);
  const frameFlushTimerRef = useRef<number | null>(null);
  const pendingTelemetryRef = useRef<BackendFrameEvent["telemetry"] | null>(null);
  const lastOverlayTelemetryRef = useRef<BackendFrameEvent["telemetry"] | null>(null);
  const selectedVideoPathRef = useRef<string | null>(null);
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [backendSession, setBackendSession] = useState<BackendSession | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [commandStatus, setCommandStatus] = useState<string | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [frameSrc, setFrameSrc] = useState<string | null>(null);
  const [liveTelemetry, setLiveTelemetry] = useState<BackendFrameEvent["telemetry"] | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [playerDuration, setPlayerDuration] = useState(0);
  const [playerCurrentTime, setPlayerCurrentTime] = useState(0);
  const [playerVolume, setPlayerVolume] = useState(0.85);
  const [isMuted, setIsMuted] = useState(false);
  const [isPlayerControlsVisible, setIsPlayerControlsVisible] = useState(false);
  const [isSeeking, setIsSeeking] = useState(false);
  const [videoLoadError, setVideoLoadError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    const sync = async () => {
      if (cancelled) return;
      await loadBackendSnapshot(
        setBackendHealth,
        setBackendSession,
        setBackendError,
        controller.signal,
      );
    };

    void sync();
    const intervalId = window.setInterval(() => {
      void sync();
    }, 5000);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    const flushFrame = () => {
      frameFlushTimerRef.current = null;
      setLiveTelemetry(pendingTelemetryRef.current);
    };

    const scheduleFrameFlush = () => {
      if (frameFlushTimerRef.current !== null) {
        return;
      }

      frameFlushTimerRef.current = window.setTimeout(flushFrame, 80);
    };

    return createBackendSessionSocket((event) => {
      setBackendError(null);

      if (event.type === "frame.update") {
        setBackendSession(event.session);
        pendingTelemetryRef.current = event.telemetry;
        if (event.frame) {
          setFrameSrc(`data:${event.frame.mime_type};base64,${event.frame.data}`);
        }
        if (hasRenderableBox(event.telemetry)) {
          lastOverlayTelemetryRef.current = event.telemetry;
        }
        scheduleFrameFlush();
        return;
      }

      setBackendSession(event.session);
      const sessionTelemetry = (event.session.telemetry ?? null) as BackendFrameEvent["telemetry"] | null;
      if (hasRenderableBox(sessionTelemetry)) {
        lastOverlayTelemetryRef.current = sessionTelemetry;
      }
    });
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || backendSession?.source_type !== "video") {
      return;
    }

    video.playbackRate = backendSession.speed || 1;
    video.muted = isMuted;
    video.volume = isMuted ? 0 : playerVolume;

    if (backendSession.is_paused) {
      if (!video.paused) {
        video.pause();
      }
    }
  }, [backendSession?.is_paused, backendSession?.speed, backendSession?.source_type, videoUrl, isMuted, playerVolume]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.volume = isMuted ? 0 : playerVolume;
    video.muted = isMuted;
  }, [isMuted, playerVolume]);

  useEffect(() => {
    return () => {
      if (controlsTimerRef.current) {
        window.clearTimeout(controlsTimerRef.current);
      }
      if (frameFlushTimerRef.current) {
        window.clearTimeout(frameFlushTimerRef.current);
      }
    };
  }, []);

  const executeCommand = async (label: string, action: () => Promise<BackendSession>) => {
    setCommandStatus(label);
    setCommandError(null);
    try {
      const nextSession = await action();
      setBackendSession(nextSession);
      setCommandStatus(`${label} concluído`);
    } catch (error) {
      setCommandError(error instanceof Error ? error.message : "Falha ao executar comando");
    } finally {
      window.setTimeout(() => setCommandStatus(null), 1800);
    }
  };

  const handleOpenVideoPicker = () => {
    void (async () => {
      setCommandError(null);
      setFrameSrc(null);
      setLiveTelemetry(null);
      pendingTelemetryRef.current = null;
      setIsPlayerControlsVisible(true);
      setVideoLoadError(null);

      const selectedPath = await window.electronAPI?.selectVideoFile?.();
      if (selectedPath) {
        selectedVideoPathRef.current = selectedPath;
        setVideoUrl(createBackendMediaUrl(selectedPath));
        setPlayerCurrentTime(0);
        setPlayerDuration(0);
        setIsMuted(false);
        await executeCommand("Abrindo vídeo", () => openBackendVideo(selectedPath));
        return;
      }

      if (window.electronAPI?.selectVideoFile) {
        setCommandError("Seleção de vídeo cancelada.");
        return;
      }

      fileInputRef.current?.click();
    })();
  };

  const handleVideoSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const filePath = (file as File & { path?: string }).path;
    event.target.value = "";

    if (!filePath) {
      setCommandError(
        "Não foi possível obter o caminho local do vídeo. Use o diálogo nativo do Electron.",
      );
      return;
    }

    setFrameSrc(null);
    setLiveTelemetry(null);
    pendingTelemetryRef.current = null;
    selectedVideoPathRef.current = filePath;
    setVideoUrl(createBackendMediaUrl(filePath));
    setPlayerCurrentTime(0);
    setPlayerDuration(0);
    setIsMuted(false);
    setIsPlayerControlsVisible(true);
    setVideoLoadError(null);
    await executeCommand("Abrindo vídeo", () => openBackendVideo(filePath));
  };

  const handleOpenCamera = async () => {
    setVideoUrl(null);
    setFrameSrc(null);
    setIsPlayerControlsVisible(false);
    setVideoLoadError(null);
    pendingTelemetryRef.current = null;
    selectedVideoPathRef.current = null;
    await executeCommand("Abrindo câmera", () => openBackendCamera(0));
  };

  const handlePauseToggle = async () => {
    const nextPaused = !(backendSession?.is_paused ?? false);
    if (backendSession?.source_type === "video") {
      const video = videoRef.current;
      if (!video) return;

      if (nextPaused) {
        video.pause();
      } else {
        try {
          await video.play();
        } catch {
          setCommandError("O navegador bloqueou a reprodução automática. Pressione play no player.");
        }
      }
    }
    void executeCommand("Alternando pausa", () => toggleBackendPause(nextPaused));
  };

  const handleSeek = async (direction: number) => {
    const video = videoRef.current;
    const sourceSeconds = video?.currentTime ?? capture?.position_seconds ?? 0;
    const targetSeconds = Math.max(0, sourceSeconds + direction * 5);
    if (video) {
      video.currentTime = targetSeconds;
      setPlayerCurrentTime(targetSeconds);
    }
    await executeCommand("Buscando", () => seekBackendSession(targetSeconds - sourceSeconds));
  };

  const handleSpeedCycle = async () => {
    const steps = [0.5, 1, 1.5, 2];
    const currentSpeed = backendSession?.speed ?? 1;
    const currentIndex = steps.findIndex((step) => Math.abs(step - currentSpeed) < 0.05);
    const nextSpeed = steps[(currentIndex + 1) % steps.length];
    await executeCommand("Ajustando velocidade", () => setBackendSpeed(nextSpeed));
    if (videoRef.current) {
      videoRef.current.playbackRate = nextSpeed;
    }
  };

  const handleCalibrate = async () => {
    await executeCommand("Calibrando", () => calibrateBackendSession());
  };

  const handleMarker = async (label: string, color?: string) => {
    await executeCommand(`Marcando ${label}`, () => addBackendMarker(label, color));
  };

  const handleReset = async () => {
    setVideoUrl(null);
    setFrameSrc(null);
    setPlayerCurrentTime(0);
    setPlayerDuration(0);
    setIsMuted(false);
    setIsPlayerControlsVisible(false);
    setVideoLoadError(null);
    pendingTelemetryRef.current = null;
    await executeCommand("Resetando sessão", () => resetBackendSession());
  };

  const showPlayerControls = () => {
    setIsPlayerControlsVisible(true);
    if (controlsTimerRef.current) {
      window.clearTimeout(controlsTimerRef.current);
    }
    controlsTimerRef.current = window.setTimeout(() => {
      if (!backendSession?.is_paused) {
        setIsPlayerControlsVisible(false);
      }
    }, 2200);
  };

  const handlePlayerMouseEnter = () => {
    showPlayerControls();
  };

  const handlePlayerMouseMove = () => {
    showPlayerControls();
  };

  const handlePlayerMouseLeave = () => {
    if (controlsTimerRef.current) {
      window.clearTimeout(controlsTimerRef.current);
    }
    controlsTimerRef.current = window.setTimeout(() => {
      if (!backendSession?.is_paused) {
        setIsPlayerControlsVisible(false);
      }
    }, 250);
  };

  const handleVideoLoadedMetadata = () => {
    const video = videoRef.current;
    if (!video) return;

    setPlayerDuration(Number.isFinite(video.duration) ? video.duration : 0);
    setPlayerCurrentTime(video.currentTime || 0);
    setPlayerVolume(video.volume || 0.85);
    setIsMuted(video.muted);
    setIsPlayerControlsVisible(true);
    setVideoLoadError(null);
    if (backendSession?.source_type === "video" && !backendSession.is_paused) {
      void video.play().catch(() => {
        setVideoLoadError("O navegador bloqueou a reprodução automática. Use o botão play.");
      });
    }
  };

  const handleVideoError = () => {
    const video = videoRef.current;
    if (!video) return;

    const errorCode = video.error?.code;
    const errorMessage =
      errorCode === 4
        ? "O formato do vídeo não é suportado pelo player do Electron."
        : errorCode === 3
          ? "Não foi possível decodificar o vídeo selecionado."
          : "Falha ao carregar o vídeo.";
    setVideoLoadError(errorMessage);
  };

  const handleVideoTimeUpdate = () => {
    const video = videoRef.current;
    if (!video || isSeeking) return;
    setPlayerCurrentTime(video.currentTime || 0);
    setPlayerDuration(Number.isFinite(video.duration) ? video.duration : 0);
  };

  const handleVideoVolumeUpdate = () => {
    const video = videoRef.current;
    if (!video) return;

    setPlayerVolume(video.volume);
    setIsMuted(video.muted);
  };

  const handlePlayerSeekStart = () => {
    setIsSeeking(true);
  };

  const handlePlayerSeekChange = (value: number) => {
    const video = videoRef.current;
    if (!video) return;

    setPlayerCurrentTime(value);
    video.currentTime = value;
  };

  const handlePlayerSeekEnd = async () => {
    setIsSeeking(false);
    const video = videoRef.current;
    if (!video) return;

    const targetSeconds = playerCurrentTime;
    const sourceSeconds = capture?.position_seconds ?? targetSeconds;
    await executeCommand("Buscando", () => seekBackendSession(targetSeconds - sourceSeconds));
  };

  const handleToggleMute = () => {
    const video = videoRef.current;
    if (!video) return;

    const nextMuted = !isMuted;
    video.muted = nextMuted;
    setIsMuted(nextMuted);
    if (!nextMuted && video.volume === 0) {
      video.volume = playerVolume || 0.85;
    }
  };

  const handlePlayerVolumeChange = (value: number) => {
    const video = videoRef.current;
    if (!video) return;

    const nextVolume = Math.max(0, Math.min(1, value));
    video.volume = nextVolume;
    video.muted = nextVolume === 0;
    setPlayerVolume(nextVolume);
    setIsMuted(nextVolume === 0);
  };

  const handleTogglePlayerFullscreen = async () => {
    const element = playerShellRef.current;
    if (!element) return;

    if (document.fullscreenElement) {
      await document.exitFullscreen().catch(() => {});
      return;
    }

    await element.requestFullscreen?.().catch(() => {});
  };

  const dateStr = now
    ? now
        .toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" })
        .toUpperCase()
    : "—";
  const timeStr = now ? now.toLocaleTimeString("pt-BR", { hour12: false }) : "--:--:--";
  const backendLabel = backendHealth ? "ONLINE" : backendError ? "OFFLINE" : "CONECTANDO...";
  const capture = backendSession?.capture ?? null;
  const captureInfo = formatCaptureInfo(capture);
  const sourceLabel = formatSourceLabel(backendSession);
  const sessionTelemetry = (backendSession?.telemetry ?? null) as
    | BackendFrameEvent["telemetry"]
    | null;
  const currentTelemetry = liveTelemetry ?? sessionTelemetry;
  const currentSpeed = currentTelemetry?.speed_kmh ?? 0;
  const isVideoSource = backendSession?.source_type === "video" && Boolean(videoUrl);
  const playbackState = backendSession
    ? backendSession.is_running
      ? backendSession.is_paused
        ? "PAUSADO"
        : "EM EXECUÇÃO"
      : "PRONTO"
    : "AGUARDANDO API";
  const markers = backendSession?.markers ?? [];
  const playerPositionSeconds = isVideoSource ? playerCurrentTime : capture?.position_seconds ?? 0;
  const playerDurationSeconds = isVideoSource ? playerDuration : capture?.duration_seconds ?? 0;
  const playerProgress =
    playerDurationSeconds > 0 ? Math.min(100, (playerPositionSeconds / playerDurationSeconds) * 100) : 0;
  const playerTimeLabel = `${formatClock(playerPositionSeconds)} / ${formatClock(playerDurationSeconds)}`;
  const playerSpeedLabel = `${(backendSession?.speed ?? 1).toFixed(1)}x`;
  const navActivePath = location.pathname;
  const sidebarNavItems = navItems.map((item) => ({
    ...item,
    isActive: item.to ? navActivePath === item.to : false,
  }));

  useEffect(() => {
    if (hasRenderableBox(liveTelemetry)) {
      lastOverlayTelemetryRef.current = liveTelemetry;
    }
  }, [liveTelemetry]);

  useEffect(() => {
    if (hasRenderableBox(sessionTelemetry)) {
      lastOverlayTelemetryRef.current = sessionTelemetry;
    }
  }, [sessionTelemetry]);

  useEffect(() => {
    const canvas = overlayCanvasRef.current;
    const shell = playerShellRef.current;
    if (!canvas || !shell || !isVideoSource) {
      return;
    }

    const redraw = () => {
      const sourceWidth = backendSession?.capture?.width ?? videoRef.current?.videoWidth ?? 0;
      const sourceHeight = backendSession?.capture?.height ?? videoRef.current?.videoHeight ?? 0;
      drawTrackingOverlay(
        canvas,
        sourceWidth,
        sourceHeight,
        liveTelemetry ?? sessionTelemetry ?? lastOverlayTelemetryRef.current,
      );
    };

    redraw();

    const ResizeObserverCtor = window.ResizeObserver;
    let observer: ResizeObserver | null = null;
    if (ResizeObserverCtor) {
      observer = new ResizeObserverCtor(() => redraw());
      observer.observe(shell);
    }

    const video = videoRef.current;
    const handleLoadedMetadata = () => redraw();
    video?.addEventListener("loadedmetadata", handleLoadedMetadata);

    return () => {
      observer?.disconnect();
      video?.removeEventListener("loadedmetadata", handleLoadedMetadata);
    };
  }, [
    backendSession?.capture?.height,
    backendSession?.capture?.width,
    isVideoSource,
    liveTelemetry,
    sessionTelemetry,
    videoUrl,
  ]);

  const handleSidebarAction = async (to?: string, action?: string) => {
    if (action === "open-analysis-window") {
      if (window.electronAPI?.openAnalysisWindow) {
        await window.electronAPI.openAnalysisWindow();
        return;
      }
      void navigate({ to: "/analysis" });
      return;
    }

    if (to) {
      void navigate({ to: to as "/" | "/analysis" | "/reports" });
    }
  };

  return (
    <div className="dark flex h-screen overflow-hidden bg-background text-foreground">
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={handleVideoSelected}
      />

      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-surface/60 backdrop-blur">
        <div className="flex items-center gap-3 border-b border-border px-5 py-5">
          <HorseLogo className="h-12 w-12 text-brand drop-shadow-[0_0_8px_oklch(0.72_0.18_55/0.6)]" />
          <div>
            <div className="font-display text-xl font-bold tracking-wider">
              VELO<span className="text-brand">VAQUEJO</span>
            </div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Sistema de medição de velocidade
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {sidebarNavItems.map(({ icon: Icon, label, to, isActive, action }) => (
            <button
              key={label}
              onClick={() => void handleSidebarAction(to, action)}
              className={[
                "group relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                isActive
                  ? "bg-brand/10 text-brand"
                  : "text-muted-foreground hover:bg-surface-2 hover:text-foreground",
              ].join(" ")}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r bg-brand" />
              )}
              <Icon className="h-4 w-4" />
              <span className="font-medium">{label}</span>
            </button>
          ))}
        </nav>

        <div className="m-3 rounded-lg border border-success/30 bg-success/5 p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-success">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
            </span>
            {backendLabel === "ONLINE" ? "BACKEND ONLINE" : "BACKEND INDISPONÍVEL"}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            {backendHealth
              ? `${backendHealth.app} · ${backendHealth.version} · ${playbackState}`
              : backendError || `Esperando ${API_BASE_URL}`}
          </p>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <header className="flex items-center justify-between gap-4 border-b border-border px-8 py-4">
          <div className="flex items-center gap-4">
            <h1 className="font-display text-2xl font-bold tracking-wider">VELOVAQUEJO PRO</h1>
            <span className="inline-flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-success">
              <span className="h-1.5 w-1.5 rounded-full bg-success" />
              {backendLabel}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <InfoPill icon={<Calendar className="h-4 w-4" />} label="Data atual" value={dateStr} />
            <InfoPill icon={<Clock className="h-4 w-4" />} label="Hora local" value={timeStr} />
            <InfoPill icon={<Radio className="h-4 w-4" />} label="Backend" value={backendLabel} />
            <button className="rounded-lg border border-border bg-surface p-2.5 text-muted-foreground transition hover:text-foreground">
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </header>

        {(commandStatus || commandError) && (
          <div
            className={[
              "mx-8 mt-3 rounded-xl border px-4 py-3 text-sm",
              commandError
                ? "border-destructive/40 bg-destructive/10 text-destructive"
                : "border-brand/30 bg-brand/10 text-brand",
            ].join(" ")}
          >
            {commandError || commandStatus}
          </div>
        )}

        <div className="grid h-[calc(100vh-5.5rem)] grid-cols-12 gap-4 px-6 py-4 xl:px-8 xl:py-4">
          <div className="col-span-12 flex min-h-0 flex-col gap-3 xl:col-span-9">
            <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
              <KpiCard
                icon={<Clock className="h-5 w-5" />}
                tint="purple"
                label="Tempo percorrido"
                value={captureInfo.position}
                unit="posição atual"
              />
              <KpiCard
                icon={<Ruler className="h-5 w-5" />}
                tint="success"
                label="Resolução"
                value={captureInfo.resolution}
                unit="arquivo/fonte atual"
              />
              <KpiCard
                icon={<Radio className="h-5 w-5" />}
                tint="info"
                label="Status do sistema"
                value={playbackState}
                unit={sourceLabel}
              />
            </div>

            <section className="rounded-2xl border border-border bg-surface/60 p-3 backdrop-blur">
              <div
                ref={playerShellRef}
                className="relative -mt-1 min-h-[560px] overflow-hidden rounded-2xl border border-border bg-black/90 xl:min-h-[680px]"
                onMouseEnter={handlePlayerMouseEnter}
                onMouseMove={handlePlayerMouseMove}
                onMouseLeave={handlePlayerMouseLeave}
              >
                {isVideoSource && videoUrl ? (
                  <div className="relative h-full min-h-[560px] w-full xl:min-h-[680px]">
                    <video
                      ref={videoRef}
                      src={videoUrl}
                      key={videoUrl}
                      className="absolute left-0 top-0 h-px w-px opacity-0 pointer-events-none"
                      playsInline
                      preload="auto"
                      onLoadedMetadata={handleVideoLoadedMetadata}
                      onError={handleVideoError}
                      onTimeUpdate={handleVideoTimeUpdate}
                      onVolumeChange={handleVideoVolumeUpdate}
                      onPlay={showPlayerControls}
                      onPause={() => setIsPlayerControlsVisible(true)}
                    />
                    {frameSrc ? (
                      <img
                        src={frameSrc}
                        alt="Quadro processado pelo backend"
                        className="absolute inset-0 h-full w-full object-contain bg-black"
                      />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center bg-black">
                        <div className="text-center">
                          <div className="mx-auto h-14 w-14 rounded-full border-2 border-brand/60 border-t-transparent animate-spin" />
                          <p className="mt-4 text-sm text-muted-foreground">
                            {videoLoadError || "Aguardando o primeiro frame processado..."}
                          </p>
                        </div>
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/70" />

                    <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full border border-white/10 bg-black/55 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/90 backdrop-blur-xl">
                      <span className="h-2 w-2 rounded-full bg-success shadow-[0_0_12px_rgba(34,197,94,0.85)]" />
                      Ao vivo
                    </div>

                    <div className="absolute right-4 top-4 rounded-full border border-white/10 bg-black/55 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/80 backdrop-blur-xl">
                      {backendSession?.is_paused ? "Pausado" : "Reproduzindo"}
                    </div>

                    {videoLoadError && (
                      <div className="absolute left-1/2 top-20 w-[min(92%,560px)] -translate-x-1/2 rounded-2xl border border-destructive/30 bg-black/75 px-4 py-3 text-center text-sm text-destructive backdrop-blur-xl">
                        {videoLoadError}
                      </div>
                    )}

                    <div
                      className={[
                        "absolute inset-x-0 bottom-0 p-4 transition-opacity duration-200",
                        backendSession?.is_paused || isPlayerControlsVisible ? "opacity-100" : "opacity-0",
                      ].join(" ")}
                    >
                      <div className="rounded-2xl border border-white/10 bg-black/60 backdrop-blur-xl">
                        <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
                          <button
                            onClick={handleOpenVideoPicker}
                            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white transition hover:bg-white/10"
                            aria-label="Carregar vídeo"
                          >
                            <FolderOpen className="h-4 w-4" />
                          </button>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/60">
                              <span className="truncate">{sourceLabel}</span>
                              <span>{playerTimeLabel}</span>
                            </div>
                            <input
                              type="range"
                              min={0}
                              max={Math.max(playerDurationSeconds, 0.001)}
                              step="0.001"
                              value={Math.min(playerCurrentTime, playerDurationSeconds || playerCurrentTime)}
                              onPointerDown={handlePlayerSeekStart}
                              onPointerUp={() => {
                                void handlePlayerSeekEnd();
                              }}
                              onChange={(event) =>
                                handlePlayerSeekChange(Number.parseFloat(event.target.value) || 0)
                              }
                              className="mt-2 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-white/10 accent-[var(--brand)]"
                            />
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <button
                              onClick={() => void handleSeek(-1)}
                              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white transition hover:bg-white/10"
                              aria-label="Voltar"
                            >
                              <SkipBack className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => void handlePauseToggle()}
                              className="inline-flex h-11 items-center gap-2 rounded-xl border border-brand/30 bg-brand/15 px-4 text-sm font-semibold text-brand transition hover:bg-brand/20"
                            >
                              {backendSession?.is_paused ? (
                                <Play className="h-4 w-4" />
                              ) : (
                                <Pause className="h-4 w-4" />
                              )}
                              {backendSession?.is_paused ? "Retomar" : "Pausar"}
                            </button>
                            <button
                              onClick={() => void handleSeek(1)}
                              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white transition hover:bg-white/10"
                              aria-label="Avançar"
                            >
                              <SkipForward className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => void handleSpeedCycle()}
                              className="inline-flex h-10 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 text-xs font-semibold uppercase tracking-wider text-white transition hover:bg-white/10"
                            >
                              {playerSpeedLabel}
                            </button>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={handleToggleMute}
                              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white transition hover:bg-white/10"
                              aria-label={isMuted ? "Ativar som" : "Silenciar"}
                            >
                              {isMuted || playerVolume === 0 ? (
                                <VolumeX className="h-4 w-4" />
                              ) : (
                                <Volume2 className="h-4 w-4" />
                              )}
                            </button>
                            <input
                              type="range"
                              min={0}
                              max={1}
                              step="0.01"
                              value={isMuted ? 0 : playerVolume}
                              onChange={(event) =>
                                handlePlayerVolumeChange(Number.parseFloat(event.target.value) || 0)
                              }
                              className="h-1.5 w-24 cursor-pointer appearance-none rounded-full bg-white/10 accent-[var(--brand)]"
                            />
                            <button
                              onClick={() => void handleTogglePlayerFullscreen()}
                              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white transition hover:bg-white/10"
                              aria-label="Tela cheia"
                            >
                              <Maximize2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : frameSrc ? (
                  <div className="relative h-full min-h-[560px] w-full xl:min-h-[680px]">
                    <img
                      src={frameSrc}
                      alt="Quadro processado pelo backend"
                      className="absolute inset-0 h-full w-full object-contain bg-black"
                    />
                    <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/70" />

                    <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full border border-white/10 bg-black/55 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/90 backdrop-blur-xl">
                      <span className="h-2 w-2 rounded-full bg-success shadow-[0_0_12px_rgba(34,197,94,0.85)]" />
                      Ao vivo
                    </div>

                    <div className="absolute right-4 top-4 rounded-full border border-white/10 bg-black/55 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/80 backdrop-blur-xl">
                      {backendSession?.is_paused ? "Pausado" : "Reproduzindo"}
                    </div>
                  </div>
                ) : (
                  <div className="flex h-full min-h-[560px] flex-col items-center justify-center px-8 text-center xl:min-h-[680px]">
                    <div className="flex h-48 w-48 items-center justify-center rounded-full border-2 border-dashed border-brand/60 bg-brand/5">
                      <Upload className="h-12 w-12 text-brand" strokeWidth={1.5} />
                    </div>
                    <h3 className="mt-7 font-display text-2xl font-bold tracking-wider">
                      {backendSession?.is_running ? "SESSÃO ATIVA" : "AGUARDANDO VÍDEO"}
                    </h3>
                    <p className="mt-3 max-w-md text-sm text-muted-foreground">
                      {backendSession
                        ? "O vídeo já pode ser manipulado pelos controles sobrepostos."
                        : "Conecte a câmera ou carregue um vídeo para iniciar a análise."}
                    </p>
                    <button
                      onClick={handleOpenVideoPicker}
                      className="mt-6 inline-flex items-center gap-2 rounded-xl border border-brand/30 bg-brand/10 px-5 py-3 text-sm font-semibold text-brand transition hover:bg-brand/15"
                    >
                      <FolderOpen className="h-4 w-4" />
                      Carregar vídeo
                    </button>
                  </div>
                )}
              </div>

            </section>
          </div>

          <div className="col-span-12 space-y-4 xl:col-span-3">
            <Speedometer speed={currentSpeed} />
            <ToolsCard
              onOpenVideo={handleOpenVideoPicker}
              onOpenCamera={handleOpenCamera}
              onCalibrate={handleCalibrate}
              onTogglePause={handlePauseToggle}
              onAddStartMarker={() => handleMarker("Início", "#22c55e")}
              onAddEndMarker={() => handleMarker("Fim", "#0ea5e9")}
              isPaused={backendSession?.is_paused ?? false}
            />
            <RecentHistory markers={markers} />
          </div>
        </div>

      </main>
    </div>
  );
}

function InfoPill({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-2">
      <span className="text-muted-foreground">{icon}</span>
      <div className="leading-tight">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </div>
        <div className="font-display text-sm font-semibold">{value}</div>
      </div>
    </div>
  );
}

const tintMap: Record<string, string> = {
  purple: "bg-purple/15 text-purple",
  success: "bg-success/15 text-success",
  info: "bg-info/15 text-info",
  brand: "bg-brand/15 text-brand",
  warning: "bg-warning/15 text-warning",
  pink: "bg-pink/15 text-pink",
};

function KpiCard({
  icon,
  tint,
  label,
  value,
  unit,
}: {
  icon: React.ReactNode;
  tint: keyof typeof tintMap | string;
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
      <div className="flex items-start gap-3">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${tintMap[tint as string] ?? tintMap.brand}`}
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            {label}
          </div>
          <div className="mt-1 font-display text-2xl font-bold">{value}</div>
          <div className="text-xs text-muted-foreground">{unit}</div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  tint,
  label,
  value,
  unit,
}: {
  icon: React.ReactNode;
  tint: string;
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
      <div className="flex items-center gap-3">
        <div
          className={`flex h-9 w-9 items-center justify-center rounded-lg ${tintMap[tint] ?? tintMap.brand}`}
        >
          {icon}
        </div>
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            {label}
          </div>
          <div className="font-display text-xl font-bold leading-tight">{value}</div>
          <div className="text-[11px] text-muted-foreground">{unit}</div>
        </div>
      </div>
    </div>
  );
}

function Speedometer({ speed }: { speed: number }) {
  // Half-circle gauge using SVG
  const radius = 90;
  const cx = 110;
  const cy = 110;
  const startAngle = 180;
  const endAngle = 360;
  const polar = (a: number, r = radius) => {
    const rad = (a * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };
  const arc = (a1: number, a2: number, r = radius) => {
    const p1 = polar(a1, r);
    const p2 = polar(a2, r);
    const large = a2 - a1 > 180 ? 1 : 0;
    return `M ${p1.x} ${p1.y} A ${r} ${r} 0 ${large} 1 ${p2.x} ${p2.y}`;
  };
  // Ticks
  const ticks = Array.from(
    { length: 21 },
    (_, i) => startAngle + ((endAngle - startAngle) * i) / 20,
  );

  return (
    <section className="rounded-2xl border border-border bg-surface/60 p-5 backdrop-blur">
      <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        Velocidade atual
      </h3>
      <div className="mt-3 flex justify-center">
        <svg width="220" height="140" viewBox="0 0 220 140">
          <defs>
            <linearGradient id="gauge" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="oklch(0.78 0.17 150)" />
              <stop offset="50%" stopColor="oklch(0.82 0.16 85)" />
              <stop offset="100%" stopColor="oklch(0.65 0.22 25)" />
            </linearGradient>
          </defs>
          <path
            d={arc(startAngle, endAngle)}
            stroke="oklch(0.3 0.018 250)"
            strokeWidth="14"
            fill="none"
            strokeLinecap="round"
          />
          <path
            d={arc(startAngle, endAngle)}
            stroke="url(#gauge)"
            strokeWidth="10"
            fill="none"
            strokeLinecap="round"
          />
          {ticks.map((a, i) => {
            const p1 = polar(a, radius - 14);
            const p2 = polar(a, radius - 6);
            return (
              <line
                key={i}
                x1={p1.x}
                y1={p1.y}
                x2={p2.x}
                y2={p2.y}
                stroke="oklch(0.97 0.005 250 / 0.4)"
                strokeWidth={i % 5 === 0 ? 2 : 1}
              />
            );
          })}
        </svg>
      </div>
      <div className="-mt-12 text-center">
        <div className="font-display text-5xl font-bold">{speed.toFixed(1)}</div>
        <div className="text-xs font-semibold tracking-[0.2em] text-muted-foreground">KM/H</div>
        <div className="mt-2 flex justify-between px-3 text-[10px] text-muted-foreground">
          <span>0</span>
          <span>200</span>
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between rounded-lg border border-border bg-background/60 px-3 py-2">
        <span className="text-xs text-muted-foreground">Status</span>
        <span className="rounded-full bg-success/15 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-success">
          {speed > 0 ? "Em uso" : "Aguardando"}
        </span>
      </div>
    </section>
  );
}

function ToolsCard({
  onOpenVideo,
  onOpenCamera,
  onCalibrate,
  onTogglePause,
  onAddStartMarker,
  onAddEndMarker,
  isPaused,
}: {
  onOpenVideo: () => void;
  onOpenCamera: () => void;
  onCalibrate: () => void;
  onTogglePause: () => void;
  onAddStartMarker: () => void;
  onAddEndMarker: () => void;
  isPaused: boolean;
}) {
  const tools = [
    { icon: Upload, label: "Carregar", tint: "brand", action: onOpenVideo },
    { icon: Camera, label: "Câmera", tint: "info", action: onOpenCamera },
    { icon: Target, label: "Calibrar", tint: "success", action: onCalibrate },
    {
      icon: isPaused ? Play : Pause,
      label: isPaused ? "Retomar" : "Pausar",
      tint: "warning",
      action: onTogglePause,
    },
    { icon: Flag, label: "Início", tint: "success", action: onAddStartMarker },
    { icon: Flag, label: "Fim", tint: "brand", action: onAddEndMarker },
  ];
  return (
    <section className="rounded-2xl border border-border bg-surface/60 p-5 backdrop-blur">
      <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        Ferramentas de precisão
      </h3>
      <div className="mt-4 grid grid-cols-3 gap-2">
        {tools.map(({ icon: Icon, label, tint, action }) => (
          <button
            key={label}
            onClick={action}
            className="group flex flex-col items-center gap-1.5 rounded-xl border border-border bg-background/60 p-3 transition hover:border-brand/50 hover:bg-surface-2"
          >
            <span
              className={`flex h-9 w-9 items-center justify-center rounded-lg ${tintMap[tint]}`}
            >
              <Icon className="h-4 w-4" />
            </span>
            <span className="text-xs font-medium">{label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function RecentHistory({ markers }: { markers: Array<Record<string, unknown>> }) {
  const recentMarkers = markers.slice(-3).reverse();
  return (
    <section className="rounded-2xl border border-border bg-surface/60 p-5 backdrop-blur">
      <h3 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        Histórico recente
      </h3>
      {recentMarkers.length > 0 ? (
        <div className="mt-4 space-y-3">
          {recentMarkers.map((marker, index) => (
            <div
              key={`${String(marker.label ?? "marcador")}-${index}`}
              className="flex items-start gap-3 rounded-xl border border-border bg-background/40 p-4"
            >
              <div
                className="flex h-10 w-10 items-center justify-center rounded-lg text-xs font-bold text-background"
                style={{ backgroundColor: String(marker.color ?? "#3B82F6") }}
              >
                {String(marker.label ?? "?")
                  .slice(0, 1)
                  .toUpperCase()}
              </div>
              <div>
                <div className="text-sm font-semibold">{String(marker.label ?? "Evento")}</div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {typeof marker.position_ms === "number"
                    ? formatClock(marker.position_ms / 1000)
                    : "Sem posição"}
                </p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-4 flex items-start gap-3 rounded-xl border border-dashed border-border bg-background/40 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground">
            <FileQuestion className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold">Nenhuma medição realizada</div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              As medições aparecerão aqui após serem concluídas.
            </p>
          </div>
        </div>
      )}
      <button className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-background/60 px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground transition hover:border-brand/50 hover:text-foreground">
        Ver todas as medições
        <ArrowRight className="h-3.5 w-3.5" />
      </button>
    </section>
  );
}
