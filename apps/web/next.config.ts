import fs from "node:fs";
import path from "node:path";
import type { NextConfig } from "next";

const rootEnvPath = path.resolve(process.cwd(), "../../.env");
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

const nextConfig: NextConfig = {
  transpilePackages: ["@orcia/ui", "@orcia/api-client"],
  reactStrictMode: true,
  devIndicators: false,
};

export default nextConfig;
