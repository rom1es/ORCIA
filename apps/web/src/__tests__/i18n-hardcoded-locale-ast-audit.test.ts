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
  it("keeps baseline totalAstViolations synchronized with the sum of astFiles", () => {
    const sum = Object.values(BASELINE.astFiles).reduce((acc, n) => acc + n, 0);
    expect(BASELINE.totalAstViolations).toBe(sum);
  });

  it("rejects any new or increased hardcoded locale conditionals or raw JSX strings beyond the ratchet baseline", () => {
    const files = collectGate1TargetFiles();
    expect(files.length).toBeGreaterThan(50);

    const regressions: string[] = [];
    for (const filePath of files) {
      const rel = path.relative(REPO_ROOT, filePath).replace(/\\/g, "/");
      const src = fs.readFileSync(filePath, "utf8");
      const violations = scanFileForHardcodedLocaleAst(rel, src);
      if (violations.length === 0) continue;

      const allowed = BASELINE.astFiles[rel];
      const first = violations[0];
      const last = violations.at(-1);
      if (allowed === undefined) {
        regressions.push(
          `${rel}: NEW file with ${violations.length} hardcoded i18n violations (sample: L${first?.line ?? 0} ${first?.kind ?? ""} ${first?.detail ?? ""})`,
        );
      } else if (violations.length > allowed) {
        regressions.push(
          `${rel}: violation count increased ${allowed} -> ${violations.length} (latest: L${last?.line ?? 0} ${last?.kind ?? ""})`,
        );
      }
    }

    expect(regressions).toEqual([]);
  });

  it("detects synthetic inline locale ternaries, raw JSX text, and UI attributes while honoring Intl and technical markers", () => {
    const badSnippet = `
      export function SampleView({ locale, isFr }: { locale: "fr" | "en"; isFr: boolean }) {
        const a = locale === "fr" ? "Bonjour" : "Hello";
        const b = isFr ? "Oui" : "Yes";
        const okDate = new Intl.DateTimeFormat(locale === "fr" ? "fr-FR" : "en-US").format(new Date());
        // i18n-non-user-facing
        const okFlag = locale === "fr" ? "fr-FR" : "en-US";
        return (
          <div title="Fermer la fenêtre" aria-label="Action principale">
            Texte codé en dur
            <span>{a}{b}{okDate}{okFlag}</span>
          </div>
        );
      }
    `;
    const found = scanFileForHardcodedLocaleAst("synthetic/SampleView.tsx", badSnippet);
    expect(found.map((v) => v.kind)).toEqual([
      "LOCALE_CONDITIONAL",
      "LOCALE_CONDITIONAL",
      "JSX_ATTR",
      "JSX_ATTR",
      "JSX_TEXT",
    ]);
  });
});
