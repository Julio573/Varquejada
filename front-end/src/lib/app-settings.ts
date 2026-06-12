const STORAGE_KEY = "velovaquejo.app.settings";
const LAST_SOURCE_KEY = "velovaquejo.app.last-source";

export type AppSettings = {
  openAnalysisInWindow: boolean;
  autoHideControls: boolean;
  controlsHideDelayMs: number;
  telemetryFlushMs: number;
  rememberLastSource: boolean;
  restoreFeedOnReturn: boolean;
  preferredCameraIndex: number | null;
  preferredCameraLabel: string | null;
};

export const DEFAULT_APP_SETTINGS: AppSettings = {
  openAnalysisInWindow: true,
  autoHideControls: true,
  controlsHideDelayMs: 2200,
  telemetryFlushMs: 80,
  rememberLastSource: true,
  restoreFeedOnReturn: true,
  preferredCameraIndex: null,
  preferredCameraLabel: null,
};

function coerceBoolean(value: unknown, fallback: boolean) {
  return typeof value === "boolean" ? value : fallback;
}

function coerceNumber(value: unknown, fallback: number, min: number, max: number) {
  const next = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(next)) return fallback;
  return Math.min(max, Math.max(min, next));
}

function coerceNullableInteger(value: unknown) {
  if (value == null) return null;
  const next = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(next)) return null;
  return Math.max(0, Math.trunc(next));
}

export function loadAppSettings(): AppSettings {
  if (typeof window === "undefined") {
    return DEFAULT_APP_SETTINGS;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return DEFAULT_APP_SETTINGS;
    }

    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    return {
      openAnalysisInWindow: coerceBoolean(
        parsed.openAnalysisInWindow,
        DEFAULT_APP_SETTINGS.openAnalysisInWindow,
      ),
      autoHideControls: coerceBoolean(parsed.autoHideControls, DEFAULT_APP_SETTINGS.autoHideControls),
      controlsHideDelayMs: coerceNumber(
        parsed.controlsHideDelayMs,
        DEFAULT_APP_SETTINGS.controlsHideDelayMs,
        800,
        6000,
      ),
      telemetryFlushMs: coerceNumber(
        parsed.telemetryFlushMs,
        DEFAULT_APP_SETTINGS.telemetryFlushMs,
        40,
        500,
      ),
      rememberLastSource: coerceBoolean(
        parsed.rememberLastSource,
        DEFAULT_APP_SETTINGS.rememberLastSource,
      ),
      restoreFeedOnReturn: coerceBoolean(
        parsed.restoreFeedOnReturn,
        DEFAULT_APP_SETTINGS.restoreFeedOnReturn,
      ),
      preferredCameraIndex: coerceNullableInteger(parsed.preferredCameraIndex),
      preferredCameraLabel:
        typeof parsed.preferredCameraLabel === "string" && parsed.preferredCameraLabel.trim()
          ? parsed.preferredCameraLabel.trim()
          : null,
    };
  } catch {
    return DEFAULT_APP_SETTINGS;
  }
}

export function saveAppSettings(settings: AppSettings) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function resetAppSettings() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(STORAGE_KEY);
}

export function loadLastSourcePath() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(LAST_SOURCE_KEY);
}

export function saveLastSourcePath(path: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(LAST_SOURCE_KEY, path);
}

export function clearLastSourcePath() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(LAST_SOURCE_KEY);
}

export function savePreferredCameraSelection(index: number | null, label: string | null) {
  if (typeof window === "undefined") {
    return;
  }

  const current = loadAppSettings();
  const next = {
    ...current,
    preferredCameraIndex: index,
    preferredCameraLabel: label,
  };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}
