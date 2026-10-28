import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const UI_SRC_DIR = path.resolve(__dirname, "..");

function walkFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__") {
        files.push(...walkFiles(fullPath));
      }
    } else if (entry.isFile() && /\.(ts|tsx|css)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

describe("@orcia/ui Design System architectural isolation & Direction C token discipline", () => {
  const allSrcFiles = walkFiles(UI_SRC_DIR);
  const tsFiles = allSrcFiles.filter((f) => /\.(ts|tsx)$/.test(f));

  it("never imports @tanstack/react-router, next/*, zustand, or @orcia/api-client inside packages/ui", () => {
    for (const filePath of tsFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      expect(content).not.toMatch(/from\s+["']@tanstack\/react-router(\/|["'])/);
      expect(content).not.toMatch(/from\s+["']next(\/|["'])/);
      expect(content).not.toMatch(/from\s+["']zustand(\/|["'])/);
      expect(content).not.toMatch(/from\s+["']@orcia\/api-client(\/|["'])/);
    }
  });

  it("never uses raw hex colors outside packages/ui/src/styles/tokens.css", () => {
    const hexColorRegex = /#[0-9a-fA-F]{3,8}\b/;
    for (const filePath of tsFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      expect(
        hexColorRegex.test(content),
        `Found forbidden hex color in ${path.relative(UI_SRC_DIR, filePath)}`,
      ).toBe(false);
    }
  });

  it("reserves --color-human-led-violet exclusively for HumanLedAnchorCard.tsx and tokens.css", () => {
    for (const filePath of tsFiles) {
      const baseName = path.basename(filePath);
      const content = fs.readFileSync(filePath, "utf-8");
      if (baseName === "HumanLedAnchorCard.tsx") {
        expect(content).toContain("--color-human-led-violet");
      } else {
        expect(content).not.toContain("--color-human-led-violet");
      }
    }
  });
});
