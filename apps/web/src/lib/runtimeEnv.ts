/**
 * Détection centralisée de l'environnement de test jsdom (Vitest).
 *
 * TEST-03 : aucun composant, hook, store ou route de production dans `apps/web/src/` ne doit
 * importer ou appeler `isJsdomRuntime()` pour court-circuiter `@orcia/api-client` (vérifié par
 * `runtime-env-guard-audit.test.ts`). Le transport HTTP/SSE Vitest est injecté au niveau `fetch`
 * dans `src/__tests__/vitest.setup.ts`.
 */
export function isJsdomRuntime(): boolean {
  return typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
}
