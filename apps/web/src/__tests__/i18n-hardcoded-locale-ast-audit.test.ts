import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  collectTsSourceFiles,
  REPO_ROOT,
  scanFileForHardcodedLocaleAst,
} from "./_i18nAuditHelpers";
import baselineData from "./i18n-hardcoded-locale-baseline.json";

interface BaselineSchema {
  readonly version: number;
  readonly totalAstViolations: number;
  readonly astFiles: Record<string, number>;
  readonly totalClientErrorViolations: number;
  readonly clientErrorBaseline: Record<string, number>;
}

const BASELINE = baselineData as BaselineSchema;

function collectGate1TargetFiles(): string[] {
  const webFiles = collectTsSourceFiles(path.join(REPO_ROOT, "apps/web/src")).filter((f) => {
    const rel = path.relative(REPO_ROOT, f).replace(/\\/g, "/");
    return !rel.startsWith("apps/web/src/i18n/locales/");
  });
  const uiFiles = collectTsSourceFiles(path.join(REPO_ROOT, "packages/ui/src"));
  return [...webFiles, ...uiFiles].sort();
}

describe("Gate 1 — TS/JSX Hardcoded Locale & Raw String AST Audit", () => {
  it("locks Gate 1 baseline permanently at zero exemptions", () => {
    expect(BASELINE.totalAstViolations).toBe(0);
    expect(BASELINE.astFiles).toEqual({});
  });

  it("rejects any hardcoded locale conditionals or raw JSX strings with zero baseline exemptions", () => {
    const files = collectGate1TargetFiles();
    expect(files.length).toBeGreaterThan(50);

    const regressions: string[] = [];
    for (const filePath of files) {
      const rel = path.relative(REPO_ROOT, filePath).replace(/\\/g, "/");
      const src = fs.readFileSync(filePath, "utf8");
      const violations = scanFileForHardcodedLocaleAst(rel, src);
      if (violations.length === 0) continue;

      const first = violations[0];
      regressions.push(
        `${rel}: ${violations.length} hardcoded i18n violations (sample: L${first?.line ?? 0} ${first?.kind ?? ""} ${first?.detail ?? ""})`,
      );
    }

    expect(regressions).toEqual([]);
  });

  it("detects synthetic inline locale ternaries, raw JSX text, UI attrs, param defaults, fallbacks, switch defaults, and packages/ui DEFAULT_* constants", () => {
    const badSnippet = `
      const DEFAULT_SAMPLE_LABELS_FR = { close: "Fermer" };
      export function SampleView({ locale, isFr, closeLabel = "Fermer" }: { locale: "fr" | "en"; isFr: boolean; closeLabel?: string }) {
        const a = locale === "fr" ? "Bonjour" : "Hello";
        const b = isFr ? "Oui" : "Yes";
        const fallback = closeLabel ?? "Annuler par défaut";
        const resolveKind = (k: string, labels?: { a?: string }) => {
          switch (k) {
            case "A": return labels?.a ?? "Pause et escalade";
            default: return k;
          }
        };
        const okDate = new Intl.DateTimeFormat(locale === "fr" ? "fr-FR" : "en-US").format(new Date());
        // i18n-non-user-facing
        const okFlag = locale === "fr" ? "fr-FR" : "en-US";
        return (
          <div title="Fermer la fenêtre" aria-label="Action principale">
            Texte codé en dur
            <span>{a}{b}{okDate}{okFlag}{fallback}{resolveKind("A")}{DEFAULT_SAMPLE_LABELS_FR.close}</span>
          </div>
        );
      }
    `;
    const found = scanFileForHardcodedLocaleAst("packages/ui/src/synthetic/SampleView.tsx", badSnippet);
    expect(found.map((v) => v.kind)).toEqual([
      "UI_DEFAULT_CONST",
      "PARAM_DEFAULT",
      "LOCALE_CONDITIONAL",
      "LOCALE_CONDITIONAL",
      "FALLBACK_LITERAL",
      "SWITCH_FALLBACK",
      "JSX_ATTR",
      "JSX_ATTR",
      "JSX_TEXT",
    ]);
  });
});
