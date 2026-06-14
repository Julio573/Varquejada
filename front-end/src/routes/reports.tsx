import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  Download,
  FileText,
  FolderDown,
  RotateCcw,
  Sparkles,
  TimerReset,
} from "lucide-react";

import {
  API_BASE_URL,
  createBackendMediaUrl,
  createBackendReportUrl,
  finishBackendSession,
  downloadLatestBackendReport,
  fetchBackendHealth,
  fetchBackendReports,
  fetchBackendSession,
  type BackendReportItem,
  type BackendHealth,
  type BackendSession,
} from "@/lib/backend";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "TrackJada Pro — Relatórios" },
      {
        name: "description",
        content:
          "Painel de relatórios automáticos com resumo das corridas, PDF gerado e histórico da última sessão.",
      },
    ],
  }),
  component: ReportsPage,
});

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

function ReportsPage() {
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [backendSession, setBackendSession] = useState<BackendSession | null>(null);
  const [reports, setReports] = useState<BackendReportItem[]>([]);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [downloadStatus, setDownloadStatus] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    const sync = async () => {
      if (cancelled) return;
      try {
        const [health, session, reportList] = await Promise.all([
          fetchBackendHealth(controller.signal),
          fetchBackendSession(controller.signal),
          fetchBackendReports(controller.signal),
        ]);
        setBackendHealth(health);
        setBackendSession(session);
        setReports(reportList);
        setBackendError(null);
      } catch (error) {
        setBackendHealth(null);
        setBackendSession(null);
        setReports([]);
        setBackendError(error instanceof Error ? error.message : "Falha ao conectar ao backend");
      }
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

  const reportUrl = createBackendReportUrl();
  const reportName = useMemo(() => {
    if (backendSession?.last_report_path) {
      return backendSession.last_report_path.split(/[\\/]/).pop() || "relatorio-ultima-corrida.pdf";
    }
    return "relatorio-ultima-corrida.pdf";
  }, [backendSession?.last_report_path]);

  const hasReport = Boolean(backendSession?.last_report_path);
  const markerCount = backendSession?.markers?.length ?? 0;
  const sampleCount = backendSession?.telemetry_history_count ?? 0;
  const lastUpdated = backendSession?.session_finished_at || backendSession?.session_started_at || null;
  const sourceLabel = formatSourceLabel(backendSession);
  const lastUpdatedLabel = lastUpdated ? new Date(lastUpdated).toLocaleString("pt-BR") : null;

  const handleDownload = async () => {
    setDownloadError(null);
    setDownloadStatus("Gerando download do relatório...");
    try {
      await downloadLatestBackendReport(reportName);
      setDownloadStatus("Relatório baixado com sucesso.");
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "Falha ao baixar o relatório");
    } finally {
      window.setTimeout(() => setDownloadStatus(null), 2200);
    }
  };

  const handleFinishMeasurement = async () => {
    setDownloadError(null);
    setDownloadStatus("Encerrando medição e gerando PDF...");
    try {
      await finishBackendSession();
      setDownloadStatus("Medição encerrada com sucesso.");
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "Falha ao encerrar a medição");
    } finally {
      window.setTimeout(() => setDownloadStatus(null), 2200);
    }
  };

  return (
    <div className="dark flex h-screen overflow-hidden bg-background text-foreground">
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-surface/60 backdrop-blur">
        <div className="flex items-center gap-3 border-b border-border px-5 py-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand/15 text-brand">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <div className="font-display text-xl font-bold tracking-wider">
              TRACK<span className="text-brand">JADA</span>
            </div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Relatórios automáticos
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
              : backendError || `Esperando ${API_BASE_URL}`}
          </p>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <header className="flex items-center justify-between gap-4 border-b border-border px-8 py-4">
          <div>
            <h1 className="font-display text-2xl font-bold tracking-wider">RELATÓRIOS</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              PDFs gerados automaticamente ao final de cada corrida.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => void handleDownload()}
              className="inline-flex items-center gap-2 rounded-xl border border-brand/30 bg-brand/15 px-4 py-2.5 text-sm font-semibold text-brand transition hover:bg-brand/20"
              disabled={!hasReport}
            >
              <Download className="h-4 w-4" />
              Baixar PDF
            </button>
          </div>
        </header>

        {(downloadStatus || downloadError) && (
          <div
            className={[
              "mx-8 mt-3 rounded-xl border px-4 py-3 text-sm",
              downloadError
                ? "border-destructive/40 bg-destructive/10 text-destructive"
                : "border-brand/30 bg-brand/10 text-brand",
            ].join(" ")}
          >
            {downloadError || downloadStatus}
          </div>
        )}

        <div className="grid h-[calc(100vh-5.5rem)] grid-cols-12 gap-4 px-6 py-4 xl:px-8 xl:py-4">
          <div className="col-span-12 flex min-h-0 flex-col gap-4 xl:col-span-8">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <StatCard
                icon={<BadgeCheck className="h-5 w-5" />}
                label="Status do relatório"
                value={hasReport ? "Gerado" : "Aguardando"}
                helper={hasReport ? reportName : "Finalize uma corrida para criar o PDF."}
              />
              <StatCard
                icon={<TimerReset className="h-5 w-5" />}
                label="Última atualização"
                value={lastUpdated ? new Date(lastUpdated).toLocaleTimeString("pt-BR", { hour12: false }) : "--:--:--"}
                helper={lastUpdatedLabel ?? "Sem sessão concluída"}
              />
              <StatCard
                icon={<Sparkles className="h-5 w-5" />}
                label="Amostras / marcadores"
                value={`${sampleCount} / ${markerCount}`}
                helper="Dados acumulados na última sessão"
              />
            </div>

            <section className="rounded-2xl border border-border bg-surface/60 p-5 backdrop-blur">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-display text-2xl font-bold tracking-wide">
                    Último relatório da corrida
                  </h2>
                  <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                    Este painel mostra o relatório mais recente criado pelo backend. Ao resetar a
                    corrida, um novo PDF substitui o contexto anterior e deixa a próxima análise
                    pronta para começar do zero.
                  </p>
                </div>
                <div className="rounded-full border border-success/30 bg-success/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-success">
                  {hasReport ? "Pronto" : "Sem PDF"}
                </div>
              </div>

              <div className="mt-6 grid gap-4 lg:grid-cols-2">
                <div className="rounded-2xl border border-border bg-background/60 p-4">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Detalhes da sessão
                  </div>
                  <div className="mt-4 space-y-3 text-sm">
                    <Row label="Fonte" value={sourceLabel} />
                    <Row label="Session ID" value={String(backendSession?.session_id ?? "—")} />
                    <Row
                      label="Início"
                      value={backendSession?.session_started_at ? new Date(backendSession.session_started_at).toLocaleString("pt-BR") : "—"}
                    />
                    <Row
                      label="Encerramento"
                      value={backendSession?.session_finished_at ? new Date(backendSession.session_finished_at).toLocaleString("pt-BR") : "—"}
                    />
                    <Row
                      label="Arquivo PDF"
                      value={backendSession?.last_report_path ? reportName : "Nenhum arquivo ainda"}
                    />
                  </div>
                </div>

                <div className="rounded-2xl border border-border bg-background/60 p-4">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Ações rápidas
                  </div>
                  <div className="mt-4 space-y-3">
                    <button
                      onClick={() => void handleDownload()}
                      disabled={!hasReport}
                      className="flex w-full items-center justify-between rounded-xl border border-border bg-surface/60 px-4 py-3 text-left transition hover:border-brand/50 hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <div>
                        <div className="font-semibold">Baixar relatório</div>
                        <div className="text-xs text-muted-foreground">
                          Faz download do último PDF gerado.
                        </div>
                      </div>
                      <FolderDown className="h-4 w-4 text-brand" />
                    </button>
                    <button
                      onClick={() => void handleFinishMeasurement()}
                      className="flex w-full items-center justify-between rounded-xl border border-success/30 bg-success/10 px-4 py-3 text-left transition hover:border-success/50 hover:bg-success/15"
                    >
                      <div>
                        <div className="font-semibold">Encerrar medição</div>
                        <div className="text-xs text-muted-foreground">
                          Fecha o arquivo atual e gera o PDF final.
                        </div>
                      </div>
                      <TimerReset className="h-4 w-4 text-success" />
                    </button>
                    <a
                      href={hasReport ? reportUrl : undefined}
                      target={hasReport ? "_blank" : undefined}
                      rel={hasReport ? "noreferrer" : undefined}
                      aria-disabled={!hasReport}
                      onClick={(event) => {
                        if (!hasReport) {
                          event.preventDefault();
                        }
                      }}
                      className={[
                        "flex items-center justify-between rounded-xl border border-border bg-surface/60 px-4 py-3 text-left transition hover:border-brand/50 hover:bg-surface-2",
                        hasReport ? "" : "pointer-events-none opacity-50",
                      ].join(" ")}
                    >
                      <div>
                        <div className="font-semibold">Abrir PDF no navegador</div>
                        <div className="text-xs text-muted-foreground">
                          Abre o arquivo direto do backend.
                        </div>
                      </div>
                      <FileText className="h-4 w-4 text-brand" />
                    </a>
                    <Link
                      to="/analysis"
                      className="flex items-center justify-between rounded-xl border border-border bg-surface/60 px-4 py-3 text-left transition hover:border-brand/50 hover:bg-surface-2"
                    >
                      <div>
                        <div className="font-semibold">Ir para medições</div>
                        <div className="text-xs text-muted-foreground">
                          Retorna à análise de velocidade.
                        </div>
                      </div>
                      <RotateCcw className="h-4 w-4 text-brand" />
                    </Link>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div className="col-span-12 min-h-0 xl:col-span-4">
            <section className="flex h-full flex-col rounded-2xl border border-border bg-surface/60 p-5 backdrop-blur">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                <Sparkles className="h-4 w-4 text-brand" />
                Conteúdo do relatório
              </div>
              <div className="mt-5 space-y-4 overflow-auto pr-1">
                <InfoBlock
                  title="Resumo automático"
                  text="O backend salva o PDF no fim da sessão com métricas de velocidade, consistência, marcadores e amostras."
                />
                <InfoBlock
                  title="Novo ciclo"
                  text="Ao resetar a corrida, a medição atual entra no mesmo relatório em andamento. O PDF final só é gerado ao encerrar a medição."
                />
                <InfoBlock
                  title="Arquivo atual"
                  text={backendSession?.last_report_path || "Nenhum relatório foi gerado nesta máquina ainda."}
                  mono
                />
                <div className="rounded-2xl border border-border bg-background/60 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Histórico de PDFs
                  </div>
                  <div className="mt-3 space-y-3">
                    {reports.length ? (
                      reports.map((report) => (
                        <a
                          key={report.path}
                          href={createBackendMediaUrl(report.path)}
                          target="_blank"
                          rel="noreferrer"
                          className="block rounded-xl border border-border bg-surface/60 p-3 transition hover:border-brand/50 hover:bg-surface-2"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <div className="truncate font-semibold">{report.filename}</div>
                              <p className="mt-1 text-xs text-muted-foreground">
                                {new Date(report.modified_at).toLocaleString("pt-BR")}
                              </p>
                            </div>
                            <span className="rounded-full border border-brand/30 bg-brand/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-brand">
                              {(report.size_bytes / 1024).toFixed(0)} KB
                            </span>
                          </div>
                        </a>
                      ))
                    ) : (
                      <div className="rounded-xl border border-dashed border-border bg-surface/40 p-3 text-sm text-muted-foreground">
                        Nenhum PDF histórico encontrado.
                      </div>
                    )}
                  </div>
                </div>

                {backendSession?.markers?.length ? (
                  <div className="rounded-2xl border border-border bg-background/60 p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                      Marcadores recentes
                    </div>
                    <div className="mt-3 space-y-3">
                      {backendSession.markers.slice(-5).reverse().map((marker, index) => (
                        <div
                          key={`${String(marker.label)}-${index}`}
                          className="rounded-xl border border-border bg-surface/60 p-3"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="font-semibold">{String(marker.label ?? "Evento")}</div>
                            <span
                              className="inline-flex h-2.5 w-2.5 rounded-full"
                              style={{ backgroundColor: String(marker.color ?? "#3B82F6") }}
                            />
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {typeof marker.position_ms === "number"
                              ? formatClock(marker.position_ms / 1000)
                              : "Sem posição"}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-border bg-background/60 p-4 text-sm text-muted-foreground">
                    Nenhum marcador disponível para compor o PDF.
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/60 pb-2 last:border-b-0 last:pb-0">
      <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </span>
      <span className="max-w-[65%] text-right text-sm font-medium text-foreground">{value}</span>
    </div>
  );
}

function InfoBlock({ title, text, mono = false }: { title: string; text: string; mono?: boolean }) {
  return (
    <div className="rounded-2xl border border-border bg-background/60 p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {title}
      </div>
      <p className={["mt-2 text-sm", mono ? "font-mono text-xs leading-5" : "text-muted-foreground"].join(" ")}>
        {text}
      </p>
    </div>
  );
}
