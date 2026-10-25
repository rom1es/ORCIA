import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const rootEnvPath = path.resolve(__dirname, "../../.env");
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

const webHost = process.env.ORCIA_WEB_HOST ?? "127.0.0.1";
const webPort = process.env.ORCIA_WEB_PORT ?? process.env.PORT ?? "3100";
const webBaseUrl = process.env.ORCIA_WEB_URL ?? `http://${webHost}:${webPort}`;

const cachedChromePath = path.join(
  os.homedir(),
  ".cache/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell",
);
const executablePath = fs.existsSync(cachedChromePath) ? cachedChromePath : undefined;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
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
  webServer: {
    command: `pnpm next dev --hostname ${webHost} --port ${webPort}`,
    url: webBaseUrl,
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
});
