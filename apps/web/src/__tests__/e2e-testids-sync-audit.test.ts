import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const E2E_DIR = path.join(REPO_ROOT, "apps/web/e2e");
const WEB_SRC_DIR = path.join(REPO_ROOT, "apps/web/src");
const UI_SRC_DIR = path.join(REPO_ROOT, "packages/ui/src");

function collectFiles(dir: string, extensions: readonly string[], skipDirs: ReadonlySet<string>): string[] {
  if (!fs.existsSync(dir)) return [];
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (skipDirs.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectFiles(full, extensions, skipDirs));
    } else if (
      entry.isFile() &&
      !entry.name.includes(".test.") &&
      extensions.some((ext) => entry.name.endsWith(ext))
    ) {
      results.push(full);
    }
  }
  return results;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

describe("Anti-False-Positive Lock 1 — 100% E2E data-testid Selectors Synced With UI Sources", () => {
  it("verifies every getByTestId(...) and [data-testid=...] selector in apps/web/e2e/ resolves to UI source code", () => {
    const uiFiles = [
      ...collectFiles(WEB_SRC_DIR, [".ts", ".tsx"], new Set(["node_modules", "__tests__", "generated", "dist"])),
      ...collectFiles(UI_SRC_DIR, [".ts", ".tsx"], new Set(["node_modules", "__tests__", "generated", "dist"])),
    ];
    const uiCorpus = uiFiles.map((f) => fs.readFileSync(f, "utf8")).join("\n");

    const dynamicMatchers: RegExp[] = [];
    const tplRegex = /(?:data-testid|testId|dataTestId|testIdPrefix)\s*[=:]\s*\{?`([^`]+)`\}?/g;
    let tplMatch: RegExpExecArray | null = tplRegex.exec(uiCorpus);
    while (tplMatch !== null) {
      const rawTpl = tplMatch[1] ?? "";
      const parts = rawTpl.split(/\$\{[^}]+\}/g).map(escapeRegExp);
      dynamicMatchers.push(new RegExp(`^${parts.join(".*")}$`));
      tplMatch = tplRegex.exec(uiCorpus);
    }

    const prefixTplRegex = /`([a-z0-9-]+-\$\{[^`]+)`/g;
    let prefixMatch: RegExpExecArray | null = prefixTplRegex.exec(uiCorpus);
    while (prefixMatch !== null) {
      const rawTpl = prefixMatch[1] ?? "";
      const parts = rawTpl.split(/\$\{[^}]+\}/g).map(escapeRegExp);
      dynamicMatchers.push(new RegExp(`^${parts.join(".*")}$`));
      prefixMatch = prefixTplRegex.exec(uiCorpus);
    }

    const e2eFiles = collectFiles(E2E_DIR, [".ts"], new Set(["node_modules"]));
    expect(e2eFiles.length).toBeGreaterThanOrEqual(24);

    const missingSelectors: string[] = [];
    const getByTestIdRegex = /getByTestId\(\s*["']([^"']+)["']\s*\)/g;
    const attrSelectorRegex = /\[data-testid=["']([^"']+)["']\]/g;

    for (const filePath of e2eFiles) {
      const content = fs.readFileSync(filePath, "utf8");
      const rel = path.relative(REPO_ROOT, filePath);

      for (const regex of [getByTestIdRegex, attrSelectorRegex]) {
        regex.lastIndex = 0;
        let match: RegExpExecArray | null = regex.exec(content);
        while (match !== null) {
          const testId = match[1] ?? "";
          const foundExact = uiCorpus.includes(testId);
          const foundDynamic = dynamicMatchers.some((rx) => rx.test(testId));
          if (!foundExact && !foundDynamic) {
            missingSelectors.push(`${rel} -> ${testId}`);
          }
          match = regex.exec(content);
        }
      }
    }

    expect(missingSelectors).toEqual([]);
  });
});
