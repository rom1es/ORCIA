import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const configDir = path.dirname(fileURLToPath(import.meta.url));
const rootEnvPath = path.resolve(configDir, "../../.env");
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

// Ports dédiés E2E : jamais ceux de l'environnement de développement (API 8000, web 3100).
const webHost = process.env.ORCIA_E2E_WEB_HOST ?? "127.0.0.1";
const webPort = process.env.ORCIA_E2E_WEB_PORT ?? "3101";
const apiPort = process.env.ORCIA_E2E_API_PORT ?? "8100";
const webBaseUrl = `http://${webHost}:${webPort}`;
const apiBaseUrl = `http://127.0.0.1:${apiPort}`;
const repoRoot = path.resolve(configDir, "../..");
const pythonBin = path.join(repoRoot, ".venv/bin/python");

const cachedChromePath = path.join(
  os.homedir(),
  ".cache/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell",
);
const executablePath = fs.existsSync(cachedChromePath) ? cachedChromePath : undefined;

export default defineConfig({
  testDir: "./e2e",
  // Base PostgreSQL partagée et remise à zéro (Jour 0) entre specs : exécution séquentielle.
  fullyParallel: false,
  workers: 1,
  // Les parcours de saisie réels (admin + BU + équipe + espace) dépassent 30 s.
  timeout: 90000,
  retries: 0,
  use: {
    baseURL: webBaseUrl,
    trace: "on-first-retry",
    launchOptions: {
      executablePath,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    },
  },
  projects: [
    {
      name: "desktop-cockpit",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "mobile-companion",
      use: {
        ...devices["Pixel 7"],
        viewport: { width: 390, height: 844 },
      },
    },
  ],
  webServer: [
    {
      // Pile isolée : PostgreSQL 18 + Redis 7.4 éphémères, migrations, FastAPI (cassette LLM, 0 $).
      command: `${pythonBin} infra/scripts/e2e/e2e_stack.py --api-port ${apiPort}`,
      cwd: repoRoot,
      url: `${apiBaseUrl}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 180000,
      // SIGTERM (et non SIGKILL par défaut) : laisse e2e_stack.py supprimer les conteneurs.
      gracefulShutdown: { signal: "SIGTERM", timeout: 30000 },
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      // SPA Vite dont le proxy `/api` vise l'API E2E (et non l'API de développement).
      command: `node scripts/run-next.mjs dev --host ${webHost} --port ${webPort}`,
      url: webBaseUrl,
      reuseExistingServer: false,
      timeout: 60000,
      env: {
        ORCIA_WEB_HOST: webHost,
        ORCIA_WEB_PORT: webPort,
        PORT: webPort,
        ORCIA_API_HOST: "127.0.0.1",
        ORCIA_API_PORT: apiPort,
      },
    },
  ],
});
