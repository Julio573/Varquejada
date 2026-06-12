import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  BarChart3,
  Gauge,
  LineChart,
  Pause,
  Play,
  Rocket,
  RotateCcw,
  TrendingUp,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart as RechartsLineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  API_BASE_URL,
  createBackendSessionSocket,
  fetchBackendHealth,
  fetchBackendSession,
  resetBackendSession,
  toggleBackendPause,
  type BackendFrameEvent,
  type BackendHealth,
  type BackendSession,
} from "@/lib/backend";

export const Route = createFileRoute("/analysis")({
  head: () => ({
    meta: [
      { title: "VeloVaquejo Pro — Análise de Velocidade" },
      {
        name: "description",
        content: "Painel de análise com velocidade por tempo, consistência e tendências da corrida.",
      },
    ],
  }),
  component: AnalysisPage,
});

type Sample = {
  t: number;
  speed: number;
};

function formatClock(seconds: number | null | undefined) {
  if (seconds == null || Number.isNaN(seconds)) return "--:--.--";
  const totalMs = Math.max(0, Math.floor(seconds * 1000));
  const minutes = Math.floor(totalMs / 60000);
  const remainingSeconds = Math.floor((totalMs % 60000) / 1000);
  const millis = totalMs % 1000;
  return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}.${String(
    Math.floor(millis / 10),
  ).padStart(2, "0")}`;
}

function formatSourceLabel(session: BackendSession | null) {
  if (!session) return "Aguardando fonte";
  if (session.source_type === "video" && typeof session.source_value === "string") {
    return session.source_value.split(/[\\/]/).pop() || session.source_value;
  }
  if (session.source_type === "camera") return `Câmera ${session.source_value ?? 0}`;
  return "Fonte não definida";
}

function safeMean(values: number[]) {
  return values.length ? values.reduce((acc, value) => acc + value, 0) / values.length : 0;
}

function safeStdDev(values: number[]) {
  if (values.length < 2) return 0;
  const mean = safeMean(values);
  const variance = safeMean(values.map((value) => (value - mean) ** 2));
  return Math.sqrt(variance);
}

function StatsCard({
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
          <div className="mt-1 font-display text-2xl font-bold">{value}</div>
          <div className="text-xs text-muted-foreground">{helper}</div>
        </div>
      </div>
    </div>
  );
}

function AnalysisPage() {
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [backendSession, setBackendSession] = useState<BackendSession | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [currentTelemetry, setCurrentTelemetry] = useState<BackendFrameEvent["telemetry"] | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [sessionActionStatus, setSessionActionStatus] = useState<string | null>(null);
  const [sessionActionError, setSessionActionError] = useState<string | null>(null);
  const sessionIdRef = useRef<number | null>(null);
  const lastTelemetryCountRef = useRef<number | null>(null);
  const lastSamplePositionRef = useRef<number | null>(null);
  const samplesRef = useRef<Sample[]>([]);

  const syncSamplesFromSession = (session: BackendSession) => {
    const nextSessionId = session.session_id ?? null;
    if (nextSessionId !== sessionIdRef.current) {
      sessionIdRef.current = nextSessionId;
      lastTelemetryCountRef.current = null;
      lastSamplePositionRef.current = null;
      samplesRef.current = [];
      setSamples([]);
    }

    const telemetry = (session.telemetry ?? null) as BackendFrameEvent["telemetry"] | null;
    if (!telemetry) {
      return;
    }

    setCurrentTelemetry(telemetry);

    const telemetryCount = session.telemetry_history_count ?? null;
    const positionSeconds = session.capture?.position_seconds ?? lastSamplePositionRef.current ?? 0;
    const speed = Number(telemetry.speed_kmh ?? 0);
    const shouldAppend =
      telemetryCount !== null
        ? telemetryCount !== lastTelemetryCountRef.current
        : samplesRef.current.length === 0 ||
          Math.abs((samplesRef.current.at(-1)?.t ?? 0) - positionSeconds) > 0.05;

    if (!shouldAppend) {
      return;
    }

    const nextSample = { t: positionSeconds, speed };
    const nextSamples = [...samplesRef.current, nextSample].slice(-240);
    samplesRef.current = nextSamples;
    setSamples(nextSamples);
    lastTelemetryCountRef.current = telemetryCount;
    lastSamplePositionRef.current = positionSeconds;
    setCurrentTelemetry(telemetry);
  };

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    const sync = async () => {
      if (cancelled) return;
      try {
        const [health, session] = await Promise.all([
          fetchBackendHealth(controller.signal),
          fetchBackendSession(controller.signal),
        ]);
        setBackendHealth(health);
        setBackendSession(session);
        setBackendError(null);
        syncSamplesFromSession(session);
      } catch (error) {
        setBackendHealth(null);
        setBackendSession(null);
        setBackendError(error instanceof Error ? error.message : "Falha ao conectar ao backend");
      }
    };

    void sync();
    const intervalId = window.setInterval(() => {
      void sync();
    }, 1500);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    return createBackendSessionSocket((event) => {
      setBackendSession(event.session);
      setBackendError(null);
      syncSamplesFromSession(event.session);

      if (event.type === "frame.update") {
        setCurrentTelemetry(event.telemetry);
      }
    });
  }, []);

  const speeds = samples.map((sample) => sample.speed);
  const maxSpeed = speeds.length ? Math.max(...speeds) : 0;
  const avgSpeed = safeMean(speeds);
  const minSpeed = speeds.length ? Math.min(...speeds) : 0;
  const stdDev = safeStdDev(speeds);
  const consistency = maxSpeed > 0 ? Math.max(0, 100 - (stdDev / maxSpeed) * 100) : 0;
  const accelPeak =
    samples.length > 1
      ? samples.slice(1).reduce((peak, sample, index) => {
          const prev = samples[index];
          const deltaT = Math.max(0.001, sample.t - prev.t);
          const accel = (sample.speed - prev.speed) / deltaT;
          return accel > peak ? accel : peak;
        }, 0)
      : 0;
  const timeAbove40 = samples.reduce((acc, sample, index) => {
    const prev = samples[index - 1];
    if (!prev) return acc;
    const deltaT = Math.max(0, sample.t - prev.t);
    if (prev.speed >= 40 || sample.speed >= 40) {
      return acc + deltaT;
    }
    return acc;
  }, 0);

  const segments = useMemo(() => {
    if (!samples.length) {
      return [
        { label: "Início", value: 0 },
        { label: "Meio", value: 0 },
        { label: "Final", value: 0 },
      ];
    }

    const start = samples.slice(0, Math.max(1, Math.floor(samples.length * 0.25)));
    const middle = samples.slice(
      Math.max(0, Math.floor(samples.length * 0.25)),
      Math.max(1, Math.floor(samples.length * 0.75)),
    );
    const end = samples.slice(Math.max(1, Math.floor(samples.length * 0.75)));

    return [
      { label: "Início", value: safeMean(start.map((sample) => sample.speed)) },
      { label: "Meio", value: safeMean(middle.map((sample) => sample.speed)) },
      { label: "Final", value: safeMean(end.map((sample) => sample.speed)) },
    ];
  }, [samples]);

  const currentTelemetryFromSession = (backendSession?.telemetry ?? currentTelemetry ?? null) as
    | BackendFrameEvent["telemetry"]
    | null;
  const trend = samples.length > 1 ? samples.at(-1)!.speed - samples[0]!.speed : 0;
  const sourceLabel = formatSourceLabel(backendSession);
  const capturePosition = formatClock(backendSession?.capture?.position_seconds);
  const markerSummary = backendSession?.markers?.slice(-5) ?? [];
  const isPaused = backendSession?.is_paused ?? false;

  const executeSessionAction = async (label: string, action: () => Promise<BackendSession>) => {
    setSessionActionStatus(label);
    setSessionActionError(null);
    try {
      const nextSession = await action();
      setBackendSession(nextSession);
      setSessionActionStatus(`${label} concluído`);
    } catch (error) {
      setSessionActionError(error instanceof Error ? error.message : "Falha ao executar ação");
    } finally {
      window.setTimeout(() => setSessionActionStatus(null), 1800);
    }
  };

  return (
    <div className="dark flex h-screen overflow-hidden bg-background text-foreground">
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-surface/60 backdrop-blur">
        <div className="flex items-center gap-3 border-b border-border px-5 py-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand/15 text-brand">
            <LineChart className="h-6 w-6" />
          </div>
          <div>
            <div className="font-display text-xl font-bold tracking-wider">
              VELO<span className="text-brand">VAQUEJO</span>
            </div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Análise de desempenho
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
              <div className="text-[11px] text-muted-foreground">Player principal e controles</div>
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
              : backendError || `Esperando ${API_BASE_URL}`}
          </p>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <header className="flex items-center justify-between gap-4 border-b border-border px-8 py-4">
          <div>
            <h1 className="font-display text-2xl font-bold tracking-wider">ANÁLISE DE VELOCIDADE</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Velocidade, tendência e consistência da corrida em tempo real.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full border border-border bg-surface px-4 py-2 text-sm font-semibold">
              {backendSession?.is_running ? (isPaused ? "PAUSADO" : "EM EXECUÇÃO") : "AGUARDANDO"}
            </div>
            <button
              onClick={() =>
                void executeSessionAction(isPaused ? "Retomando" : "Pausando", () =>
                  toggleBackendPause(!isPaused),
                )
              }
              disabled={!backendSession?.is_running}
              className="inline-flex items-center gap-2 rounded-xl border border-brand/30 bg-brand/15 px-4 py-2.5 text-sm font-semibold text-brand transition hover:bg-brand/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
              {isPaused ? "Retomar" : "Pausar"}
            </button>
            <button
              onClick={() => void executeSessionAction("Resetando", () => resetBackendSession())}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-semibold text-foreground transition hover:bg-surface-2"
            >
              <RotateCcw className="h-4 w-4" />
              Resetar
            </button>
          </div>
        </header>

        {(sessionActionStatus || sessionActionError) && (
          <div
            className={[
              "mx-8 mt-3 rounded-xl border px-4 py-3 text-sm",
              sessionActionError
                ? "border-destructive/40 bg-destructive/10 text-destructive"
                : "border-brand/30 bg-brand/10 text-brand",
            ].join(" ")}
          >
            {sessionActionError || sessionActionStatus}
          </div>
        )}

        <div className="grid h-[calc(100vh-5.5rem)] grid-cols-12 gap-4 px-6 py-4 xl:px-8 xl:py-4">
          <div className="col-span-12 flex min-h-0 flex-col gap-4 xl:col-span-8">
            <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
              <StatsCard icon={<Gauge className="h-4 w-4" />} label="Velocidade máx." value={`${maxSpeed.toFixed(1)} km/h`} helper="Maior pico da sessão" />
              <StatsCard icon={<TrendingUp className="h-4 w-4" />} label="Velocidade média" value={`${avgSpeed.toFixed(1)} km/h`} helper="Média do histórico atual" />
              <StatsCard icon={<BarChart3 className="h-4 w-4" />} label="Consistência" value={`${consistency.toFixed(0)}%`} helper="Estabilidade da velocidade" />
              <StatsCard icon={<Rocket className="h-4 w-4" />} label="Aceleração pico" value={`${accelPeak.toFixed(1)}`} helper="km/h por segundo" />
            </div>

            <section className="min-h-0 flex-1 rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Curva de velocidade
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">{sourceLabel}</p>
                </div>
                <div className="text-right">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Tempo atual</div>
                  <div className="font-display text-lg font-semibold">{capturePosition}</div>
                </div>
              </div>

              <div className="mt-4 h-[clamp(260px,50vh,420px)] rounded-2xl border border-border bg-black/30 p-4">
                {samples.length > 1 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsLineChart data={samples}>
                      <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                      <XAxis
                        dataKey="t"
                        tickFormatter={(value) => formatClock(Number(value))}
                        stroke="rgba(255,255,255,0.45)"
                        fontSize={11}
                      />
                      <YAxis
                        stroke="rgba(255,255,255,0.45)"
                        fontSize={11}
                        width={42}
                        tickFormatter={(value) => `${Number(value).toFixed(0)}`}
                      />
                      <Tooltip
                        labelFormatter={(value) => `Tempo: ${formatClock(Number(value))}`}
                        formatter={(value) => [`${Number(value).toFixed(1)} km/h`, "Velocidade"]}
                        contentStyle={{
                          background: "rgba(10, 12, 18, 0.96)",
                          border: "1px solid rgba(255,255,255,0.08)",
                          borderRadius: "14px",
                          color: "#fff",
                        }}
                      />
                      <ReferenceLine y={40} stroke="rgba(34,197,94,0.45)" strokeDasharray="4 4" />
                      <Line
                        type="monotone"
                        dataKey="speed"
                        stroke="#F0903A"
                        strokeWidth={3}
                        dot={false}
                        activeDot={{ r: 5, strokeWidth: 0 }}
                      />
                    </RechartsLineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-center">
                    <div>
                      <Play className="mx-auto h-10 w-10 text-brand" />
                      <p className="mt-4 text-sm text-muted-foreground">
                        Carregue um vídeo ou câmera para começar a gerar a curva de velocidade.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </section>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {segments.map((segment) => (
                <div key={segment.label} className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    {segment.label}
                  </div>
                  <div className="mt-1 font-display text-2xl font-bold">{segment.value.toFixed(1)} km/h</div>
                  <div className="text-xs text-muted-foreground">Velocidade média no trecho</div>
                </div>
              ))}
            </div>
          </div>

          <div className="col-span-12 flex min-h-0 flex-col gap-4 xl:col-span-4">
            <section className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Leitura útil
              </h2>
              <div className="mt-4 space-y-3">
                <InsightRow label="Pico atual" value={`${maxSpeed.toFixed(1)} km/h`} />
                <InsightRow label="Tendência" value={trend >= 0 ? `Subindo +${trend.toFixed(1)}` : `Caindo ${trend.toFixed(1)}`} />
                <InsightRow label="Tempo acima de 40" value={`${timeAbove40.toFixed(1)} s`} />
                <InsightRow label="Desvio padrão" value={`${stdDev.toFixed(1)}`} />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Marcadores
              </h2>
              <div className="mt-4 space-y-3">
                {markerSummary.length ? (
                  markerSummary.map((marker, index) => (
                    <div key={`${String(marker.label)}-${index}`} className="rounded-xl border border-border bg-background/40 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-semibold">{String(marker.label)}</div>
                        <div className="text-xs text-muted-foreground">
                          {formatClock(Number(marker.position_ms ?? 0) / 1000)}
                        </div>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">Ponto marcado na corrida</div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">Sem marcadores nesta sessão ainda.</p>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                Visão rápida
              </h2>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <MiniStat
                  label="Atual"
                  value={`${currentTelemetryFromSession?.speed_kmh?.toFixed(1) ?? "0.0"} km/h`}
                />
                <MiniStat label="Média" value={`${avgSpeed.toFixed(1)} km/h`} />
                <MiniStat label="Máx." value={`${maxSpeed.toFixed(1)} km/h`} />
                <MiniStat label="Mín." value={`${minSpeed.toFixed(1)} km/h`} />
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

function InsightRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-border bg-background/40 px-4 py-3">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-display text-lg font-semibold">{value}</span>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-background/40 px-3 py-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 font-display text-lg font-semibold">{value}</div>
    </div>
  );
}
