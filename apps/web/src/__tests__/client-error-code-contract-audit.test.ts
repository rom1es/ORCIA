import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import { CLIENT_ERROR_CODES, resolveClientErrorMessage } from "../lib/clientErrorCodes";
import {
  collectClientErrorAuditTargets,
  scanFileForClientErrorViolations,
} from "./_clientErrorAuditHelper";
import { REPO_ROOT } from "./_i18nAuditHelpers";
import baselineData from "./i18n-hardcoded-locale-baseline.json";

interface BaselineSchema {
  readonly totalClientErrorViolations: number;
  readonly clientErrorBaseline: Record<string, number>;
}

const BASELINE = baselineData as BaselineSchema;

describe("Gate 3 — Client Error Code Contract & Ratchet Audit", () => {
  it("requires complete fr/en ClientErrorCode resolution without raw placeholders", () => {
    for (const code of CLIENT_ERROR_CODES) {
      const fr = resolveClientErrorMessage(code, frDictionary.clientErrors, {
        seconds: 16,
        detail: "détail",
      });
      const en = resolveClientErrorMessage(code, enDictionary.clientErrors, {
        seconds: 16,
        detail: "detail",
      });
      expect(fr.trim().length).toBeGreaterThan(10);
      expect(en.trim().length).toBeGreaterThan(10);
      expect(fr).not.toMatch(/\{[a-zA-Z0-9_]+\}/);
      expect(en).not.toMatch(/\{[a-zA-Z0-9_]+\}/);
    }
  });

  it("keeps totalClientErrorViolations synchronized with the sum of clientErrorBaseline", () => {
    const sum = Object.values(BASELINE.clientErrorBaseline).reduce((acc, n) => acc + n, 0);
    expect(BASELINE.totalClientErrorViolations).toBe(sum);
  });

  it("rejects any new or increased hardcoded client error prose or locale ternaries across bridges, stores, and controllers", () => {
    const targets = collectClientErrorAuditTargets();
    expect(targets.length).toBeGreaterThan(20);

    const regressions: string[] = [];
    for (const filePath of targets) {
      const rel = path.relative(REPO_ROOT, filePath).replace(/\\/g, "/");
      const src = fs.readFileSync(filePath, "utf8");
      const violations = scanFileForClientErrorViolations(rel, src);
      if (violations.length === 0) continue;

      const allowed = BASELINE.clientErrorBaseline[rel];
      const first = violations[0];
      const last = violations.at(-1);
      if (allowed === undefined) {
        regressions.push(
          `${rel}: NEW file with ${violations.length} client error violations (sample: L${first?.line ?? 0} ${first?.kind ?? ""} ${first?.detail ?? ""})`,
        );
      } else if (violations.length > allowed) {
        regressions.push(
          `${rel}: client error violations increased ${allowed} -> ${violations.length} (latest: L${last?.line ?? 0})`,
        );
      }
    }

    expect(regressions).toEqual([]);
  });

  it("flags synthetic locale ternaries and hardcoded English/French error throws", () => {
    const badBridge = `
      export function callApi(locale: "fr" | "en", failed: boolean) {
        if (failed) {
          throw new Error(locale === "fr" ? "Erreur réseau critique" : "Critical network error");
        }
        return {
          title: "Connection failed",
          message: "Unable to reach the server right now",
        };
      }
    `;
    const found = scanFileForClientErrorViolations("synthetic/badApiBridge.ts", badBridge);
    expect(found.some((v) => v.kind === "LOCALE_TERNARY")).toBe(true);
    expect(found.some((v) => v.kind === "HARDCODED_ERROR_STRING")).toBe(true);
  });
});
