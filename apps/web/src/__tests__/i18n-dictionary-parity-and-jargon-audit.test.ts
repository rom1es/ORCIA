import { describe, expect, it } from "vitest";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import { SHOWCASE_ARCHITECTURE_LABELS_BY_LOCALE } from "../routes/showcaseArchitectureCatalog";

const ALLOW_EMPTY_KEYS = new Set<string>(["shell.brandSubtitle"]);
const ALLOW_FRENCH_BRAND_OR_NATIVE_KEYS = new Set<string>([
  "locale",
  "userAccountAndSettings.localeFrLabel",
]);
const FRENCH_ACCENT_RE = /[àâäçéèêëîïôöùûüÿœæÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ]/;
const FRENCH_PROSE_RE =
  /(?:\b(?:l'|d'|qu'|n'|s'|c')|\b(?:pour|avec|sans|dans|sous|tous|toutes|aucun|aucune|veuillez|introuvable|requis|requise|indisponible|données|paramètres|utilisateur|utilisateurs|espace|espaces|équipe|équipes|étape|étapes|erreur|erreurs|vérifier|enregistrement|supprimer|modifier|ajouter|créer|valider|fermer|annuler|modèle|fournisseur|clôture|retour|accéder|brouillon|brouillons|votre|vos|notre|nos|cette|depuis|après|avant|rapide|lecture|seule|consommation|factures|livrable|livrables|cadrage|synthèse|répertoire|compétences|connaissances|glossaire|métiers|périmètre|coûts|plafond)\b)/i;

const UX_RULE_31_FORBIDDEN_TERMS: readonly string[] = [
  "DBOS", "PostgreSQL 18", "PG18", "pgvector", "halfvec", "domain_events_outbox",
  "Wasmtime", "Starlark", "Argon2id", "OIDC PKCE", "Service Principal", "Rubber-stamping",
  "Verrou V1", "Verrou V2", "Verrou V3", "Verrou V4", "Verrou V5", "RFC 9457",
  "human_authored_required", "WAITING_FOR_HUMAN_ARBITRATION", "CONTRIBUTOR_ACTION_REQUIRED",
  "READ_ONLY_OBSERVER", "ORCIA_BOOTSTRAP_TOKEN", "Outbox", "BM25", "HNSW", "RRF", "CTE",
  "AD-10", "AD-15", "Passthrough", "Tie-Break", "What-If", "Rebase",
];

function collectLeafEntries(obj: unknown, prefix = ""): Map<string, string> {
  const entries = new Map<string, string>();
  if (obj === null || obj === undefined) return entries;
  if (typeof obj === "string") {
    entries.set(prefix, obj);
    return entries;
  }
  if (Array.isArray(obj)) {
    obj.forEach((item, idx) => {
      for (const [k, v] of collectLeafEntries(item, `${prefix}[${idx}]`)) entries.set(k, v);
    });
    return entries;
  }
  if (typeof obj === "object") {
    for (const [key, val] of Object.entries(obj as Record<string, unknown>)) {
      const nextKey = prefix ? `${prefix}.${key}` : key;
      for (const [k, v] of collectLeafEntries(val, nextKey)) entries.set(k, v);
    }
  }
  return entries;
}

function extractInterpolationParams(text: string): string[] {
  if (text.trim().startsWith("{") && text.includes('"$schema"')) return [];
  const matches = text.match(/\{[a-zA-Z0-9_]+\}/g) ?? [];
  return Array.from(new Set(matches)).sort();
}

export function detectFrenchInEnglishLeaf(key: string, text: string): string | null {
  if (ALLOW_FRENCH_BRAND_OR_NATIVE_KEYS.has(key)) return null;
  // Strip canonical @Agent-Handle proper identifiers before scanning prose.
  const withoutHandles = text.replace(/@[A-Za-zÀ-ÿ0-9_-]+/g, "");
  if (FRENCH_ACCENT_RE.test(withoutHandles)) {
    return `${key}: French accented text in EN (${JSON.stringify(text.slice(0, 80))})`;
  }
  const wordMatch = FRENCH_PROSE_RE.exec(withoutHandles);
  if (wordMatch) {
    return `${key}: French token "${wordMatch[0]}" in EN (${JSON.stringify(text.slice(0, 80))})`;
  }
  return null;
}

function assertBilingualPairParity(
  frObj: unknown,
  enObj: unknown,
  namespace: string,
): void {
  const frLeaves = collectLeafEntries(frObj);
  const enLeaves = collectLeafEntries(enObj);
  const missingInEn = [...frLeaves.keys()].filter((k) => !enLeaves.has(k));
  const missingInFr = [...enLeaves.keys()].filter((k) => !frLeaves.has(k));
  expect(missingInEn, `${namespace} keys in FR missing in EN`).toEqual([]);
  expect(missingInFr, `${namespace} keys in EN missing in FR`).toEqual([]);

  const emptyViolations: string[] = [];
  const placeholderMismatches: string[] = [];
  const frInEnViolations: string[] = [];

  for (const [key, frVal] of frLeaves.entries()) {
    const enVal = enLeaves.get(key) ?? "";
    if (!ALLOW_EMPTY_KEYS.has(key)) {
      if (frVal.trim().length === 0) emptyViolations.push(`fr:${namespace}:${key}`);
      if (enVal.trim().length === 0) emptyViolations.push(`en:${namespace}:${key}`);
    }
    const frParams = extractInterpolationParams(frVal);
    const enParams = extractInterpolationParams(enVal);
    if (JSON.stringify(frParams) !== JSON.stringify(enParams)) {
      placeholderMismatches.push(`${namespace}:${key}: FR=${JSON.stringify(frParams)} vs EN=${JSON.stringify(enParams)}`);
    }
    const frInEn = detectFrenchInEnglishLeaf(key, enVal);
    if (frInEn) frInEnViolations.push(`${namespace}:${frInEn}`);
  }

  expect(emptyViolations, `Empty leaf values in ${namespace}`).toEqual([]);
  expect(placeholderMismatches, `Mismatched {param} placeholders in ${namespace}`).toEqual([]);
  expect(frInEnViolations, `Untranslated French text in EN ${namespace}`).toEqual([]);
}

describe("Gate 2 — FR/EN Dictionary Parity, Placeholders, Zero FR-in-EN & UX Rule 3.1 Zero-Jargon", () => {
  it("enforces recursive key parity, non-empty values, matching {param} placeholders, and zero FR-in-EN across dictionaries & showcase catalog", () => {
    assertBilingualPairParity(frDictionary, enDictionary, "dict");
    assertBilingualPairParity(
      SHOWCASE_ARCHITECTURE_LABELS_BY_LOCALE.fr,
      SHOWCASE_ARCHITECTURE_LABELS_BY_LOCALE.en,
      "showcaseArchitectureCatalog",
    );
    expect(detectFrenchInEnglishLeaf("test.sample", "Enabling analysis requires an admin role.")).toBeNull();
    expect(detectFrenchInEnglishLeaf("test.bad", "L'activation de l'analyse requiert un rôle.")).not.toBeNull();
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
          if (val.includes(term)) violations.push(`${localeName}:${key} contains forbidden term [${term}]`);
        }
      }
    }
    expect(violations).toEqual([]);
  });
});
