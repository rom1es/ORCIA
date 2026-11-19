import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const E2E_DIR = path.join(REPO_ROOT, "apps/web/e2e");
const PLAYWRIGHT_CONFIG_PATH = path.join(REPO_ROOT, "apps/web/playwright.config.ts");

function collectTsFiles(dir: string): string[] {
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectTsFiles(full));
    } else if (entry.isFile() && entry.name.endsWith(".ts")) {
      results.push(full);
    }
  }
  return results;
}

describe("Anti-False-Positive Lock 2 — Typed OpenAPI Helper Only & Zero E2E Seed Fixtures", () => {
  it("forbids untyped raw page.request/request HTTP calls outside typedApiRequest.ts and purges ORCIA_E2E_SEED_FIXTURES", () => {
    const rawRequestRegex = /\b(?:page\.)?request\.(?:get|post|put|patch|delete)\s*\(/;
    const rawRequestViolations: string[] = [];
    const fixtureViolations: string[] = [];

    for (const filePath of collectTsFiles(E2E_DIR)) {
      const rel = path.relative(REPO_ROOT, filePath);
      const content = fs.readFileSync(filePath, "utf8");
      const lines = content.split("\n");

      lines.forEach((line, idx) => {
        if (!rel.endsWith("support/typedApiRequest.ts") && rawRequestRegex.test(line)) {
          rawRequestViolations.push(`${rel}:${idx + 1} -> ${line.trim()}`);
        }
        if (line.includes("ORCIA_E2E_SEED_FIXTURES")) {
          fixtureViolations.push(`${rel}:${idx + 1} -> ${line.trim()}`);
        }
      });
    }

    const pwConfig = fs.readFileSync(PLAYWRIGHT_CONFIG_PATH, "utf8");
    if (pwConfig.includes("ORCIA_E2E_SEED_FIXTURES")) {
      fixtureViolations.push("apps/web/playwright.config.ts references ORCIA_E2E_SEED_FIXTURES");
    }

    const helperContent = fs.readFileSync(path.join(E2E_DIR, "support/typedApiRequest.ts"), "utf8");
    expect(helperContent).toContain('from "@orcia/api-client"');
    expect(helperContent).toContain("reloadColdFromPg");
    expect(rawRequestViolations).toEqual([]);
    expect(fixtureViolations).toEqual([]);
  });
});
