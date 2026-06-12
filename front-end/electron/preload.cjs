const { contextBridge } = require("electron");
const { ipcRenderer } = require("electron");
const { pathToFileURL } = require("node:url");

const backendBaseUrl = process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

contextBridge.exposeInMainWorld("electronAPI", {
  backendBaseUrl,
  platform: process.platform,
  versions: process.versions,
  selectVideoFile: () => ipcRenderer.invoke("select-video-file"),
  pathToFileUrl: (filePath) => pathToFileURL(filePath).href,
});
