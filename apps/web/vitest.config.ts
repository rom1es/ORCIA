import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@orcia/ui": path.resolve(__dirname, "../../packages/ui/src/index.ts"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/__tests__/vitest.setup.ts"],
    include: ["src/__tests__/**/*.test.{ts,tsx}"],
  },
});
