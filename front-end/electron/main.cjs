const path = require("node:path");
const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");

app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");
app.on("browser-window-created", (_, window) => {
  window.setMenuBarVisibility(false);
  window.setAutoHideMenuBar(true);
});

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

function createWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 980,
    minWidth: 1280,
    minHeight: 820,
    maximizable: true,
    backgroundColor: "#0b0d14",
    show: false,
    title: "VeloVaquejo Pro",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
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

  const isDev = !app.isPackaged;
  const targetUrl = process.env.ELECTRON_START_URL
    ? process.env.ELECTRON_START_URL
    : isDev
      ? "http://127.0.0.1:5173"
      : `file://${path.join(app.getAppPath(), "dist", "index.html")}`;
  win.loadURL(targetUrl);

  if (isDev && process.env.ELECTRON_OPEN_DEVTOOLS === "1") {
    win.webContents.openDevTools({ mode: "detach" });
  }
}

app.whenReady().then(() => {
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
