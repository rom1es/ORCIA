import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect } from "@playwright/test";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../../..");
const pythonBin = path.join(repoRoot, ".venv/bin/python");
const queryDbScript = path.join(repoRoot, "infra/scripts/e2e/query_db.py");

interface QueryDbOutput<T extends Record<string, unknown>> {
  rows: T[];
  row_count: number;
}

function formatParams(params?: Record<string, unknown>): string {
  return JSON.stringify(params ?? {});
}

/**
 * Exécute une requête `SELECT` / `WITH` en lecture seule stricte sur la base PostgreSQL 18
 * éphémère de la pile E2E (`orcia_e2e`) via `infra/scripts/e2e/query_db.py`.
 */
export function queryDbRows<T extends Record<string, unknown> = Record<string, unknown>>(
  sql: string,
  params?: Record<string, unknown>,
): T[] {
  let stdout = "";
  try {
    stdout = execFileSync(
      pythonBin,
      [queryDbScript, "--sql", sql, "--params", formatParams(params)],
      {
        cwd: repoRoot,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
  } catch (err: unknown) {
    const execErr = err as { stderr?: string | Buffer; message?: string };
    const stderr =
      typeof execErr.stderr === "string"
        ? execErr.stderr.trim()
        : Buffer.isBuffer(execErr.stderr)
          ? execErr.stderr.toString("utf8").trim()
          : "";
    throw new Error(
      `Échec requête PostgreSQL 18 E2E (${stderr || execErr.message || "erreur inconnue"}) — SQL: ${sql}`,
    );
  }

  const parsed = JSON.parse(stdout) as QueryDbOutput<T>;
  if (!Array.isArray(parsed.rows)) {
    throw new Error(`Réponse JSON invalide depuis query_db.py : ${stdout}`);
  }
  return parsed.rows;
}

/**
 * Vérifie qu'au moins une ligne existe dans PostgreSQL 18 (`orcia_e2e`) et retourne la première.
 */
export function expectDbRowExists(
  sql: string,
  params?: Record<string, unknown>,
  contextMessage?: string,
): Record<string, unknown> {
  const rows = queryDbRows<Record<string, unknown>>(sql, params);
  const label = contextMessage ? `${contextMessage} — ` : "";
  expect(
    rows.length,
    `${label}Aucune ligne persistée trouvée en base PostgreSQL 18 (orcia_e2e). SQL: ${sql} | params: ${formatParams(params)}`,
  ).toBeGreaterThanOrEqual(1);
  return rows[0] ?? {};
}

/**
 * Vérifie que la requête retourne (ou agrège via `COUNT(*)`) au moins `minCount` lignes en PG18.
 */
export function expectDbRowCount(
  sql: string,
  params: Record<string, unknown> | undefined,
  minCount: number,
  contextMessage?: string,
): number {
  const rows = queryDbRows<Record<string, unknown>>(sql, params);
  const firstRow = rows[0];
  const singleCount =
    rows.length === 1 &&
    firstRow !== undefined &&
    Object.keys(firstRow).length === 1 &&
    typeof firstRow.count === "number"
      ? firstRow.count
      : rows.length;
  const label = contextMessage ? `${contextMessage} — ` : "";
  expect(
    singleCount,
    `${label}Nombre de lignes persistées insuffisant en base PostgreSQL 18 (${singleCount} < ${minCount}). SQL: ${sql} | params: ${formatParams(params)}`,
  ).toBeGreaterThanOrEqual(minCount);
  return singleCount;
}
