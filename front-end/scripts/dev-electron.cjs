const { spawn } = require("node:child_process");
const path = require("node:path");

const electronPath = require("electron");
const mainPath = path.join(__dirname, "..", "electron", "main.cjs");

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

const child = spawn(electronPath, [mainPath], {
  stdio: "inherit",
  env,
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});
