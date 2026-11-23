import { describe, expect, it } from "vitest";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";

const ALLOW_EMPTY_KEYS = new Set<string>(["shell.brandSubtitle"]);

const UX_RULE_31_FORBIDDEN_TERMS: readonly string[] = [
  "DBOS",
  "PostgreSQL 18",
  "PG18",
  "pgvector",
  "halfvec",
  "domain_events_outbox",
  "Wasmtime",
  "Starlark",
  "Argon2id",
  "OIDC PKCE",
  "Service Principal",
  "Rubber-stamping",
  "Verrou V1",
  "Verrou V2",
  "Verrou V3",
  "Verrou V4",
  "Verrou V5",
  "RFC 9457",
  "human_authored_required",
  "WAITING_FOR_HUMAN_ARBITRATION",
  "CONTRIBUTOR_ACTION_REQUIRED",
  "READ_ONLY_OBSERVER",
  "ORCIA_BOOTSTRAP_TOKEN",
  "Outbox",
  "BM25",
  "HNSW",
  "RRF",
  "CTE",
  "AD-10",
  "AD-15",
  "Passthrough",
  "Tie-Break",
  "What-If",
  "Rebase",
];

function collectLeafEntries(
  obj: unknown,
  prefix = "",
): Map<string, string> {
  const entries = new Map<string, string>();
  if (obj === null || obj === undefined) return entries;
  if (typeof obj === "string") {
    entries.set(prefix, obj);
    return entries;
  }
  if (Array.isArray(obj)) {
    obj.forEach((item, idx) => {
      for (const [k, v] of collectLeafEntries(item, `${prefix}[${idx}]`)) {
        entries.set(k, v);
      }
    });
    return entries;
  }
  if (typeof obj === "object") {
    for (const [key, val] of Object.entries(obj as Record<string, unknown>)) {
      const nextKey = prefix ? `${prefix}.${key}` : key;
      for (const [k, v] of collectLeafEntries(val, nextKey)) {
        entries.set(k, v);
      }
    }
  }
  return entries;
}

function extractInterpolationParams(text: string): string[] {
  if (text.trim().startsWith("{") && text.includes('"$schema"')) {
    return [];
  }
  const matches = text.match(/\{[a-zA-Z0-9_]+\}/g) ?? [];
  return Array.from(new Set(matches)).sort();
}

describe("Gate 2 — FR/EN Dictionary Parity, Placeholders & UX Rule 3.1 Zero-Jargon", () => {
  it("enforces recursive key parity, non-empty values, and matching {param} placeholders", () => {
    const frLeaves = collectLeafEntries(frDictionary);
    const enLeaves = collectLeafEntries(enDictionary);

    const missingInEn = [...frLeaves.keys()].filter((k) => !enLeaves.has(k));
    const missingInFr = [...enLeaves.keys()].filter((k) => !frLeaves.has(k));
    expect(missingInEn, "Keys present in FR but missing in EN").toEqual([]);
    expect(missingInFr, "Keys present in EN but missing in FR").toEqual([]);

    const emptyViolations: string[] = [];
    const placeholderMismatches: string[] = [];

    for (const [key, frVal] of frLeaves.entries()) {
      const enVal = enLeaves.get(key) ?? "";
      if (!ALLOW_EMPTY_KEYS.has(key)) {
        if (frVal.trim().length === 0) emptyViolations.push(`fr:${key}`);
        if (enVal.trim().length === 0) emptyViolations.push(`en:${key}`);
      }
      const frParams = extractInterpolationParams(frVal);
      const enParams = extractInterpolationParams(enVal);
      if (JSON.stringify(frParams) !== JSON.stringify(enParams)) {
        placeholderMismatches.push(
          `${key}: FR=${JSON.stringify(frParams)} vs EN=${JSON.stringify(enParams)}`,
        );
      }
    }

    expect(emptyViolations, "Empty dictionary leaf values").toEqual([]);
    expect(placeholderMismatches, "Mismatched {param} placeholders").toEqual([]);
  });

  it("forbids UX Rule 3.1 internal plumbing jargon across frDictionary and enDictionary", () => {
    const violations: string[] = [];
    for (const [localeName, dict] of [
      ["fr", frDictionary],
      ["en", enDictionary],
    ] as const) {
      const leaves = collectLeafEntries(dict);
      for (const [key, val] of leaves.entries()) {
        for (const term of UX_RULE_31_FORBIDDEN_TERMS) {
          if (val.includes(term)) {
            violations.push(`${localeName}:${key} contains forbidden term [${term}]`);
          }
        }
      }
    }
    expect(violations).toEqual([]);
  });
});
