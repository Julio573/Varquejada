const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { app, BrowserWindow, dialog, ipcMain, screen, session, shell } = require("electron");

app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");
app.on("browser-window-created", (_, window) => {
  window.setMenuBarVisibility(false);
  window.setAutoHideMenuBar(true);
});

let analysisWindow = null;
let mainWindow = null;

function getAppUrl(route = "/") {
  const isDev = !app.isPackaged;
  const baseUrl = process.env.ELECTRON_START_URL
    ? process.env.ELECTRON_START_URL
    : isDev
      ? "http://127.0.0.1:5173"
      : pathToFileURL(path.join(app.getAppPath(), "dist", "index.html")).href;
  const url = new URL(baseUrl);
  url.searchParams.set("route", route);
  return url.href;
}

function getPreferredDisplay() {
  const displays = screen.getAllDisplays();
  if (displays.length < 2) {
    return screen.getPrimaryDisplay();
  }

  const primaryDisplay = screen.getPrimaryDisplay();
  return displays.find((display) => display.id !== primaryDisplay.id) ?? primaryDisplay;
}

function createAppWindow({
  title,
  route = "/",
  display,
  width = 1600,
  height = 980,
} = {}) {
  const bounds = display?.workArea ?? null;
  const win = new BrowserWindow({
    width: bounds?.width ?? width,
    height: bounds?.height ?? height,
    x: bounds?.x ?? undefined,
    y: bounds?.y ?? undefined,
    minWidth: 1280,
    minHeight: 820,
    maximizable: true,
    backgroundColor: "#0b0d14",
    show: false,
    title,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      backgroundThrottling: false,
    },
  });

  win.once("ready-to-show", () => {
    win.maximize();
    win.show();
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  win.loadURL(getAppUrl(route));

  return win;
}

ipcMain.handle("select-video-file", async () => {
  const result = await dialog.showOpenDialog({
    title: "Selecionar vídeo",
    properties: ["openFile"],
    filters: [
      { name: "Vídeos", extensions: ["mp4", "avi", "mkv", "mov", "webm"] },
      { name: "Todos os arquivos", extensions: ["*"] },
    ],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  return result.filePaths[0];
});

ipcMain.handle("open-analysis-window", async () => {
  if (analysisWindow && !analysisWindow.isDestroyed()) {
    if (analysisWindow.isMinimized()) {
      analysisWindow.restore();
    }
    analysisWindow.focus();
    return true;
  }

  analysisWindow = createAppWindow({
    title: "VeloVaquejo Pro — Medições",
    route: "/analysis",
    display: getPreferredDisplay(),
  });

  analysisWindow.on("closed", () => {
    analysisWindow = null;
  });

  const isDev = !app.isPackaged;
  if (isDev && process.env.ELECTRON_OPEN_DEVTOOLS === "1") {
    analysisWindow.webContents.openDevTools({ mode: "detach" });
  }

  return true;
});

ipcMain.handle("close-analysis-window", async () => {
  if (analysisWindow && !analysisWindow.isDestroyed()) {
    analysisWindow.close();
    analysisWindow = null;
  }

  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    mainWindow.focus();
  }

  return true;
});

function createWindow() {
  mainWindow = createAppWindow({
    title: "VeloVaquejo Pro",
    route: "/",
    display: screen.getPrimaryDisplay(),
  });

  const isDev = !app.isPackaged;
  if (isDev && process.env.ELECTRON_OPEN_DEVTOOLS === "1") {
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }

  return mainWindow;
}

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const url = webContents.getURL();
    const isTrustedOrigin =
      url.startsWith("http://127.0.0.1:5173") ||
      url.startsWith("http://localhost:5173") ||
      url.startsWith("file://");
    if (isTrustedOrigin && permission === "media") {
      callback(true);
      return;
    }

    callback(false);
  });

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
