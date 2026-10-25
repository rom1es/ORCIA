import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const rootEnvPath = path.resolve(scriptDir, "../../../.env");

if (fs.existsSync(rootEnvPath)) {
  const lines = fs.readFileSync(rootEnvPath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx <= 0) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
    if (process.env[key] === undefined) {
      process.env[key] = val;
    }
  }
}

const mode = process.argv[2] === "start" ? "start" : "dev";
const extraArgs = process.argv.slice(3);
const hasPortArg = extraArgs.some(
  (arg) => arg === "-p" || arg === "--port" || arg.startsWith("--port=")
);
const hasHostArg = extraArgs.some(
  (arg) => arg === "-H" || arg === "--hostname" || arg.startsWith("--hostname=")
);

const host = process.env.ORCIA_WEB_HOST ?? "127.0.0.1";
const port = process.env.ORCIA_WEB_PORT ?? process.env.PORT ?? "3100";

const nextArgs = [mode];
if (!hasHostArg) {
  nextArgs.push("--hostname", host);
}
if (!hasPortArg) {
  nextArgs.push("--port", port);
}
nextArgs.push(...extraArgs);

const nextBin = path.resolve(scriptDir, "../node_modules/.bin/next");
const child = spawn(nextBin, nextArgs, {
  stdio: "inherit",
  env: { ...process.env, PORT: port, ORCIA_WEB_PORT: port, ORCIA_WEB_HOST: host },
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.exit(1);
  }
  process.exit(code ?? 0);
});
