import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Gauge, Monitor, RefreshCcw, Settings, Sparkles, TimerReset } from "lucide-react";

import {
  DEFAULT_APP_SETTINGS,
  clearLastSourcePath,
  loadLastSourcePath,
  loadAppSettings,
  resetAppSettings,
  saveAppSettings,
  type AppSettings,
} from "@/lib/app-settings";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "VaqVision Pro — Configurações" },
      {
        name: "description",
        content: "Preferências do player, janela de medições e comportamento da interface.",
      },
    ],
  }),
  component: SettingsPage,
});

function ToggleRow({
  label,
  helper,
  checked,
  onChange,
}: {
  label: string;
  helper: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-2xl border border-border bg-surface/60 p-4 transition hover:bg-surface-2">
      <div className="min-w-0">
        <div className="font-semibold">{label}</div>
        <div className="mt-1 text-sm text-muted-foreground">{helper}</div>
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-1 h-5 w-5 accent-brand"
      />
    </label>
  );
}

function RangeRow({
  label,
  helper,
  value,
  min,
  max,
  step,
  suffix,
  onChange,
  disabled = false,
}: {
  label: string;
  helper: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface/60 p-4 transition hover:bg-surface-2">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="font-semibold">{label}</div>
          <div className="mt-1 text-sm text-muted-foreground">{helper}</div>
        </div>
        <div className="rounded-xl border border-border bg-background px-3 py-2 font-display text-lg font-bold">
          {value}
          {suffix}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-4 h-2 w-full cursor-pointer appearance-none rounded-full bg-surface-2 accent-brand disabled:cursor-not-allowed disabled:opacity-50"
      />
    </div>
  );
}

function SettingCard({
  icon,
  title,
  value,
  helper,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
          {icon}
        </div>
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            {title}
          </div>
          <div className="mt-1 font-display text-xl font-bold">{value}</div>
          <div className="text-xs text-muted-foreground">{helper}</div>
        </div>
      </div>
    </div>
  );
}

function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(() => loadAppSettings());
  const [savedAt, setSavedAt] = useState<string>("Salvo automaticamente");
  const [lastSourcePath, setLastSourcePath] = useState<string | null>(() => loadLastSourcePath());

  useEffect(() => {
    saveAppSettings(settings);
    setSavedAt(`Salvo automaticamente às ${new Date().toLocaleTimeString("pt-BR", { hour12: false })}`);
  }, [settings]);

  const analysisModeLabel = settings.openAnalysisInWindow ? "Janela separada" : "Na mesma tela";
  const controlsLabel = settings.autoHideControls ? "Auto-hide ativo" : "Controles fixos";

  const restoredDefaults = useMemo(() => DEFAULT_APP_SETTINGS, []);

  const updateSetting = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((current) => ({
      ...current,
      [key]: value,
    }));
  };

  const handleResetDefaults = () => {
    resetAppSettings();
    clearLastSourcePath();
    setLastSourcePath(null);
    setSettings(restoredDefaults);
    setSavedAt("Padrões restaurados");
  };

  return (
    <div className="dark flex h-screen overflow-hidden bg-background text-foreground">
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-surface/60 backdrop-blur">
        <div className="flex items-center gap-3 border-b border-border px-5 py-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand/15 text-brand">
            <Settings className="h-6 w-6" />
          </div>
          <div>
            <div className="font-display text-xl font-bold tracking-wider">
              VAQ<span className="text-brand">VISION</span>
            </div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Configurações
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
            Preferências locais
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            Salvas no dispositivo e aplicadas automaticamente no painel.
          </p>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <header className="flex items-center justify-between gap-4 border-b border-border px-8 py-4">
          <div>
            <h1 className="font-display text-2xl font-bold tracking-wider">CONFIGURAÇÕES</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Ajustes de comportamento do player, janela de medições e atualização da telemetria.
            </p>
          </div>
          <div className="rounded-full border border-border bg-surface/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            {savedAt}
          </div>
        </header>

        <div className="grid h-[calc(100vh-5.5rem)] grid-cols-12 gap-4 px-6 py-4 xl:px-8 xl:py-4">
          <div className="col-span-12 flex min-h-0 flex-col gap-4 xl:col-span-8">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <SettingCard
                icon={<Monitor className="h-5 w-5" />}
                title="Modo de medições"
                value={analysisModeLabel}
                helper="Define se a aba de medições abre em uma janela separada."
              />
              <SettingCard
                icon={<TimerReset className="h-5 w-5" />}
                title="Controles do player"
                value={controlsLabel}
                helper="Determina se os controles somem sozinhos após alguns segundos."
              />
            </div>

            <section className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
                  <Monitor className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-xl font-bold tracking-wider">Experiência do player</h2>
                  <p className="text-sm text-muted-foreground">
                    Ajustes que mudam o comportamento do painel principal e da janela de medições.
                  </p>
                </div>
              </div>

              <div className="mt-4 grid gap-3">
                <ToggleRow
                  label="Abrir medições em janela separada"
                  helper="Quando ativo, o botão de medições abre uma segunda janela do Electron para uso em segundo monitor."
                  checked={settings.openAnalysisInWindow}
                  onChange={(value) => updateSetting("openAnalysisInWindow", value)}
                />
                <ToggleRow
                  label="Auto-hide dos controles"
                  helper="Esconde os controles do player depois de alguns segundos sem interação."
                  checked={settings.autoHideControls}
                  onChange={(value) => updateSetting("autoHideControls", value)}
                />
                <ToggleRow
                  label="Restaurar feed ao voltar"
                  helper="Ao retornar para o painel principal, tenta reconstruir automaticamente a visualização do vídeo."
                  checked={settings.restoreFeedOnReturn}
                  onChange={(value) => updateSetting("restoreFeedOnReturn", value)}
                />
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
                  <Gauge className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-xl font-bold tracking-wider">Performance e atualização</h2>
                  <p className="text-sm text-muted-foreground">
                    Controla a frequência de atualização da telemetria e a persistência dos controles.
                  </p>
                </div>
              </div>

              <div className="mt-4 grid gap-3">
                <RangeRow
                  label="Intervalo da telemetria"
                  helper="Intervalo usado para agrupar as atualizações do backend antes de renderizar na interface."
                  value={settings.telemetryFlushMs}
                  min={40}
                  max={500}
                  step={10}
                  suffix=" ms"
                  onChange={(value) => updateSetting("telemetryFlushMs", value)}
                />
                <RangeRow
                  label="Tempo do auto-hide"
                  helper="Se os controles estiverem ativos, define quanto tempo eles permanecem visíveis sem interação."
                  value={settings.controlsHideDelayMs}
                  min={800}
                  max={6000}
                  step={100}
                  suffix=" ms"
                  disabled={!settings.autoHideControls}
                  onChange={(value) => updateSetting("controlsHideDelayMs", value)}
                />
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
                  <h2 className="font-display text-xl font-bold tracking-wider">Memória da interface</h2>
                  <p className="text-sm text-muted-foreground">
                    Preferências simples para deixar a operação mais confortável.
                  </p>
                </div>
              </div>

              <div className="mt-4 grid gap-3">
                <ToggleRow
                  label="Lembrar última origem"
                  helper="Guarda a última fonte usada para facilitar o próximo carregamento."
                  checked={settings.rememberLastSource}
                  onChange={(value) => {
                    updateSetting("rememberLastSource", value);
                    if (!value) {
                      clearLastSourcePath();
                      setLastSourcePath(null);
                    }
                  }}
                />

                <div className="rounded-2xl border border-dashed border-border/80 bg-background/60 p-4 text-sm text-muted-foreground">
                  Algumas preferências alteram a navegação imediatamente, como a abertura das medições em janela separada.
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-border bg-surface/60 p-4 backdrop-blur">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
                  <RefreshCcw className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-display text-xl font-bold tracking-wider">Ações rápidas</h2>
                  <p className="text-sm text-muted-foreground">
                    Use para voltar aos padrões quando quiser simplificar a operação.
                  </p>
                </div>
              </div>

              <div className="mt-4 grid gap-3">
                <button
                  onClick={handleResetDefaults}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-brand/30 bg-brand/15 px-4 py-3 text-sm font-semibold text-brand transition hover:bg-brand/20"
                >
                  <RefreshCcw className="h-4 w-4" />
                  Restaurar padrões
                </button>
                <div className="rounded-2xl border border-border bg-background/60 p-4">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Estado atual
                  </div>
                  <div className="mt-2 text-sm text-muted-foreground">
                    <div>Janela de medições: {analysisModeLabel}</div>
                    <div>Controles: {controlsLabel}</div>
                    <div>Telemetria: {settings.telemetryFlushMs} ms</div>
                    <div>Auto-hide: {settings.autoHideControls ? `${settings.controlsHideDelayMs} ms` : "desligado"}</div>
                  </div>
                </div>
                <div className="rounded-2xl border border-border bg-background/60 p-4">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Última origem
                  </div>
                  <div className="mt-2 break-all text-sm text-muted-foreground">
                    {lastSourcePath || "Nenhum vídeo lembrado ainda."}
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
