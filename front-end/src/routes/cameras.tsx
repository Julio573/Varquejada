import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Camera,
  CheckCircle2,
  RefreshCcw,
  ScreenShare,
  Settings,
  Sparkles,
  Video,
} from "lucide-react";

import { fetchBackendHealth, fetchBackendSession, openBackendCamera, type BackendHealth, type BackendSession } from "@/lib/backend";
import { loadAppSettings, savePreferredCameraSelection, type AppSettings } from "@/lib/app-settings";
import { listCameraDevices, type CameraDeviceInfo } from "@/lib/camera-devices";

export const Route = createFileRoute("/cameras")({
  head: () => ({
    meta: [
      { title: "VeloVaquejo Pro — Câmeras" },
      {
        name: "description",
        content: "Selecione o dispositivo de câmera conectado que será usado pelo backend.",
      },
    ],
  }),
  component: CamerasPage,
});

function StatCard({
  icon,
  label,
  value,
  helper,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/15 text-brand">
          {icon}
        </div>
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            {label}
          </div>
          <div className="mt-1 font-display text-xl font-bold">{value}</div>
          <div className="text-xs text-muted-foreground">{helper}</div>
        </div>
      </div>
    </div>
  );
}

function CameraCard({
  device,
  isSelected,
  isActive,
  onSelect,
  onUseNow,
}: {
  device: CameraDeviceInfo;
  isSelected: boolean;
  isActive: boolean;
  onSelect: (device: CameraDeviceInfo) => void;
  onUseNow: (device: CameraDeviceInfo) => void;
}) {
  return (
    <div
      className={[
        "rounded-2xl border p-4 transition",
        isSelected || isActive
          ? "border-brand/40 bg-brand/10 shadow-[0_0_0_1px_rgba(251,146,60,0.12)]"
          : "border-border bg-surface/60 hover:bg-surface-2",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-4">
        <button onClick={() => onSelect(device)} className="min-w-0 text-left">
          <div className="flex items-center gap-2">
            <Camera className="h-4 w-4 text-brand" />
            <div className="font-display text-lg font-bold tracking-wide">{device.label}</div>
          </div>
          <div className="mt-2 text-xs text-muted-foreground">ID interno: {device.deviceId}</div>
          <div className="mt-1 text-xs text-muted-foreground">Grupo: {device.groupId || "—"}</div>
        </button>

        <div className="flex flex-col items-end gap-2">
          {isActive ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-success/30 bg-success/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-success">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Ativa
            </span>
          ) : null}
          {isSelected ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-brand/30 bg-brand/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-brand">
              <Sparkles className="h-3.5 w-3.5" />
              Preferida
            </span>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={() => onUseNow(device)}
          className="inline-flex items-center gap-2 rounded-xl border border-brand/30 bg-brand/15 px-3 py-2 text-sm font-semibold text-brand transition hover:bg-brand/20"
        >
          <Video className="h-4 w-4" />
          Usar esta câmera
        </button>
        <button
          onClick={() => onSelect(device)}
          className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-sm font-semibold text-muted-foreground transition hover:text-foreground"
        >
          <Settings className="h-4 w-4" />
          Definir padrão
        </button>
      </div>
    </div>
  );
}

function CamerasPage() {
  const [settings, setSettings] = useState<AppSettings>(() => loadAppSettings());
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [backendSession, setBackendSession] = useState<BackendSession | null>(null);
  const [devices, setDevices] = useState<CameraDeviceInfo[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(
    () => loadAppSettings().preferredCameraIndex,
  );
  const [selectedLabel, setSelectedLabel] = useState<string | null>(
    () => loadAppSettings().preferredCameraLabel,
  );
  const [backendError, setBackendError] = useState<string | null>(null);
  const [deviceError, setDeviceError] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<string | null>(null);

  const activeCameraIndex = useMemo(() => {
    if (backendSession?.source_type === "camera" && typeof backendSession.source_value === "number") {
      return backendSession.source_value;
    }
    return null;
  }, [backendSession?.source_type, backendSession?.source_value]);

  const syncBackend = async (signal?: AbortSignal) => {
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
  };

  const refreshDevices = async () => {
    setDeviceError(null);
    setActionStatus("Detectando câmeras...");
    try {
      const nextDevices = await listCameraDevices();
      setDevices(nextDevices);
      if (nextDevices.length > 0 && selectedIndex == null) {
        const first = nextDevices[0];
        setSelectedIndex(first.index);
        setSelectedLabel(first.label);
        savePreferredCameraSelection(first.index, first.label);
        setSettings(loadAppSettings());
      }
      setActionStatus(`Encontradas ${nextDevices.length} câmera(s).`);
    } catch (error) {
      setDevices([]);
      setDeviceError(error instanceof Error ? error.message : "Falha ao listar câmeras");
    } finally {
      window.setTimeout(() => setActionStatus(null), 2000);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    const sync = async () => {
      if (cancelled) return;
      await syncBackend(controller.signal);
    };

    void sync();
    void refreshDevices();

    const intervalId = window.setInterval(() => {
      void sync();
    }, 5000);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, []);

  const handleSelectDevice = (device: CameraDeviceInfo) => {
    setSelectedIndex(device.index);
    setSelectedLabel(device.label);
    savePreferredCameraSelection(device.index, device.label);
    setSettings(loadAppSettings());
    setActionStatus(`Câmera padrão definida: ${device.label}`);
    window.setTimeout(() => setActionStatus(null), 2000);
  };

  const handleUseCamera = async (device: CameraDeviceInfo) => {
    setSelectedIndex(device.index);
    setSelectedLabel(device.label);
    savePreferredCameraSelection(device.index, device.label);
    setSettings(loadAppSettings());
    setActionStatus(`Abrindo ${device.label}...`);
    try {
      const session = await openBackendCamera(device.index);
      setBackendSession(session);
      setActionStatus(`Câmera ativa: ${device.label}`);
    } catch (error) {
      setActionStatus(null);
      setBackendError(error instanceof Error ? error.message : "Falha ao abrir a câmera");
    } finally {
      window.setTimeout(() => setActionStatus(null), 2200);
    }
  };

  const handleOpenPreferred = () => {
    const preferred = devices.find((device) => device.index === selectedIndex) ?? devices[0];
    if (preferred) {
      void handleUseCamera(preferred);
    }
  };

  return (
    <div className="dark flex h-screen overflow-hidden bg-background text-foreground">
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-surface/60 backdrop-blur">
        <div className="flex items-center gap-3 border-b border-border px-5 py-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand/15 text-brand">
            <Camera className="h-6 w-6" />
          </div>
          <div>
            <div className="font-display text-xl font-bold tracking-wider">
              VELO<span className="text-brand">VAQUEJO</span>
            </div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Seleção de câmera
            </div>
          </div>
        </div>

        <div className="flex-1 px-4 py-4">
          <Link
            to="/"
            className="flex items-center gap-3 rounded-xl border border-border bg-surface/60 px-3 py-3 text-sm transition hover:bg-surface-2"
          >
            <ArrowLeft className="h-4 w-4 text-brand" />
            <div>
              <div className="font-semibold">Voltar ao painel</div>
              <div className="text-[11px] text-muted-foreground">Player principal e medições</div>
            </div>
          </Link>
        </div>

        <div className="m-3 rounded-lg border border-success/30 bg-success/5 p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-success">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
            </span>
            {backendHealth ? "BACKEND ONLINE" : "BACKEND INDISPONÍVEL"}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            {backendHealth
              ? `${backendHealth.app} · ${backendHealth.version}`
              : backendError || "Aguardando conexão com o backend."}
          </p>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <header className="flex items-center justify-between gap-4 border-b border-border px-8 py-4">
          <div>
            <h1 className="font-display text-2xl font-bold tracking-wider">CÂMERAS</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Selecione o dispositivo conectado que será usado pelo sistema.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => void refreshDevices()}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface/70 px-4 py-2.5 text-sm font-semibold text-muted-foreground transition hover:text-foreground"
            >
              <RefreshCcw className="h-4 w-4" />
              Atualizar lista
            </button>
            <button
              onClick={handleOpenPreferred}
              className="inline-flex items-center gap-2 rounded-xl border border-brand/30 bg-brand/15 px-4 py-2.5 text-sm font-semibold text-brand transition hover:bg-brand/20"
              disabled={devices.length === 0}
            >
              <ScreenShare className="h-4 w-4" />
              Abrir preferida
            </button>
          </div>
        </header>

        {(actionStatus || deviceError) && (
          <div
            className={[
              "mx-8 mt-3 rounded-xl border px-4 py-3 text-sm",
              deviceError
                ? "border-destructive/40 bg-destructive/10 text-destructive"
                : "border-brand/30 bg-brand/10 text-brand",
            ].join(" ")}
          >
            {deviceError || actionStatus}
          </div>
        )}

        <div className="grid h-[calc(100vh-5.5rem)] grid-cols-12 gap-4 px-6 py-4 xl:px-8 xl:py-4">
          <div className="col-span-12 flex min-h-0 flex-col gap-4 xl:col-span-8">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <StatCard
                icon={<Camera className="h-5 w-5" />}
                label="Dispositivos"
                value={`${devices.length}`}
                helper="Câmeras de vídeo detectadas"
              />
              <StatCard
                icon={<Sparkles className="h-5 w-5" />}
                label="Preferida"
                value={selectedLabel || "—"}
                helper="Câmera que o painel principal usa ao abrir"
              />
              <StatCard
                icon={<CheckCircle2 className="h-5 w-5" />}
                label="Ativa"
                value={activeCameraIndex != null ? `#${activeCameraIndex}` : "—"}
                helper="Câmera atualmente aberta no backend"
              />
            </div>

            <section className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
                  <Camera className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-xl font-bold tracking-wider">Dispositivos conectados</h2>
                  <p className="text-sm text-muted-foreground">
                    Clique em uma câmera para defini-la como padrão ou abri-la imediatamente.
                  </p>
                </div>
              </div>

              <div className="mt-4 grid gap-3">
                {devices.length > 0 ? (
                  devices.map((device) => (
                    <CameraCard
                      key={device.deviceId}
                      device={device}
                      isSelected={device.index === selectedIndex}
                      isActive={device.index === activeCameraIndex}
                      onSelect={handleSelectDevice}
                      onUseNow={handleUseCamera}
                    />
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-border/80 bg-background/60 p-6 text-sm text-muted-foreground">
                    Nenhuma câmera foi listada ainda. Clique em atualizar ou libere a permissão de câmera para ver os nomes dos dispositivos.
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="col-span-12 flex min-h-0 flex-col gap-4 xl:col-span-4">
            <section className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-xl font-bold tracking-wider">Dica</h2>
                  <p className="text-sm text-muted-foreground">
                    A lista mostra o nome do dispositivo detectado pelo sistema operacional.
                  </p>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-border bg-background/60 p-4 text-sm text-muted-foreground">
                Se o nome vier como genérico, abra a câmera uma vez para o sistema liberar as permissões e exibir o rótulo completo.
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Seleção atual
              </div>
              <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                <div>Preferida: {selectedLabel || "Nenhuma"}</div>
                <div>Índice: {selectedIndex ?? "—"}</div>
                <div>Ativa no backend: {activeCameraIndex ?? "—"}</div>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
