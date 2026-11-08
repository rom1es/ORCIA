/**
 * Détection centralisée de l'environnement de test jsdom (Vitest).
 *
 * Source UNIQUE de la garde « pas de réseau sous jsdom » : toute autre occurrence inline de
 * `/jsdom/i.test(navigator.userAgent)` est interdite (audit `runtime-env-guard-audit.test.ts`).
 * L'angle mort Vitest ↔ FastAPI que cette garde crée est couvert par les specs Playwright
 * (`apps/web/e2e`, TEST-04…TEST-08) ; la suppression complète de la garde reste à faire (TEST-03).
 */
export function isJsdomRuntime(): boolean {
  return typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
}
