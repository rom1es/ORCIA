import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../../..");

/**
 * Remet la base PostgreSQL 18 **éphémère** de la pile E2E à l'état Jour 0 (0 utilisateur).
 * Le script Python refuse de s'exécuter si la base n'est pas la base E2E isolée.
 */
export function resetDay0(): void {
  execFileSync(
    path.join(repoRoot, ".venv/bin/python"),
    [path.join(repoRoot, "infra/scripts/e2e/reset_day0.py")],
    { cwd: repoRoot, stdio: "pipe" },
  );
}
