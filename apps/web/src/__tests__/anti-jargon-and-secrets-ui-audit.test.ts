import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");

const FORBIDDEN_UI_TERMS: readonly string[] = [
  "SYNTHESIS_READY",
  "OAUTH2_PASSTHROUGH",
  "PAUSE_AND_ESCALATE",
  "OPT_A_SPOT_15M",
  "OPT_B_LOCK_48H",
  "DeclarativePackLoader",
  "orcia-connectors",
  "WritePreviewCard",
  "Tier cognitif",
  "Anti-Prompt Injection",
  "1024-dim RAG",
  "AES-256-GCM",
  "LOCK TABLE users IN EXCLUSIVE MODE",
  "Chef1",
  "aqwZSX",
  "[LAYER_5_",
  "[STALE_WARNING]",
  "ORCIA_BOOTSTRAP_TOKEN",
];

function collectFiles(dir: string, extensions: readonly string[]): string[] {
  if (!fs.existsSync(dir)) return [];
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (
      entry.name === "node_modules" ||
      entry.name === "dist" ||
      entry.name === "__tests__" ||
      entry.name === "generated"
    ) {
      continue;
    }
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectFiles(full, extensions));
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

function isTechnicalTypeOrSanitizerLine(line: string, term: string): boolean {
  const trimmed = line.trim();
  if (trimmed.startsWith("import ") || trimmed.startsWith("export type ")) return true;
  if (trimmed.startsWith("//") || trimmed.startsWith("*")) return true;
  // TypeScript union members or type annotations
  if (new RegExp(`^\\|\\s*["']${escapeRegExp(term)}["']`).test(trimmed)) return true;
  if (new RegExp(`[:<]\\s*["']${escapeRegExp(term)}["']`).test(trimmed)) return true;
  // Sanitization .replace(...) patterns that explicitly strip internal enums
  if (trimmed.includes(".replace(") && trimmed.includes(term)) return true;
  // HTML option values or equality comparisons on internal enum codes
  if (new RegExp(`value\\s*=\\s*["']${escapeRegExp(term)}["']`).test(trimmed)) return true;
  if (new RegExp(`(?:===|!==|case)\\s*["']${escapeRegExp(term)}["']`).test(trimmed)) return true;
  // Internal TypeScript component/interface identifier (e.g. TraceWritePreviewCardProps)
  if (term === "WritePreviewCard" && /\bTraceWritePreviewCard(?:Props)?\b/.test(trimmed)) {
    return true;
  }
  return false;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

describe("CI Guardrail — Zero Technical Jargon, Internal Enums, or Secrets in Visible UI & Help", () => {
  it("forbids all banned jargon and secret tokens across i18n dictionaries, contextual help, and markdown help docs", () => {
    const targetFiles: string[] = [
      ...collectFiles(path.join(REPO_ROOT, "apps/web/src/i18n/locales"), [".ts"]),
      path.join(REPO_ROOT, "apps/web/src/components/_contextualHelpSections.ts"),
      path.join(REPO_ROOT, "apps/web/src/components/_contextualHelpSectionsEn.ts"),
      ...collectFiles(path.join(REPO_ROOT, "docs/help"), [".md"]),
      ...collectFiles(path.join(REPO_ROOT, "packs"), [".md"]).filter((p) =>
        p.includes(`${path.sep}help${path.sep}`),
      ),
    ];

    expect(targetFiles.length).toBeGreaterThan(5);

    const violations: string[] = [];
    for (const filePath of targetFiles) {
      const content = fs.readFileSync(filePath, "utf8");
      const lines = content.split("\n");
      const rel = path.relative(REPO_ROOT, filePath);
      lines.forEach((line, idx) => {
        for (const term of FORBIDDEN_UI_TERMS) {
          if (line.includes(term)) {
            violations.push(`${rel}:${idx + 1} [${term}] -> ${line.trim()}`);
          }
        }
      });
    }

    expect(violations).toEqual([]);
  });

  it("forbids visible UI leaks of banned jargon and secret tokens in packages/ui/src primitives and components", () => {
    const uiFiles = collectFiles(path.join(REPO_ROOT, "packages/ui/src"), [".ts", ".tsx"]).filter(
      (filePath) => path.basename(filePath) !== "OrciaProductShowcaseSiteView.tsx",
    );

    expect(uiFiles.length).toBeGreaterThan(10);

    const violations: string[] = [];
    for (const filePath of uiFiles) {
      const content = fs.readFileSync(filePath, "utf8");
      const lines = content.split("\n");
      const rel = path.relative(REPO_ROOT, filePath);
      lines.forEach((line, idx) => {
        for (const term of FORBIDDEN_UI_TERMS) {
          if (line.includes(term) && !isTechnicalTypeOrSanitizerLine(line, term)) {
            violations.push(`${rel}:${idx + 1} [${term}] -> ${line.trim()}`);
          }
        }
      });
    }

    expect(violations).toEqual([]);
  });
});
