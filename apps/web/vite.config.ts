import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const webHost = process.env.ORCIA_WEB_HOST ?? "127.0.0.1";
const webPort = Number(process.env.ORCIA_WEB_PORT ?? process.env.PORT ?? "3100");
const apiHost = process.env.ORCIA_API_HOST ?? "127.0.0.1";
const apiPort = process.env.ORCIA_API_PORT ?? "8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: webHost,
    port: webPort,
    strictPort: true,
    proxy: {
      "/api": {
        target: `http://${apiHost}:${apiPort}`,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: webHost,
    port: webPort,
  },
});
