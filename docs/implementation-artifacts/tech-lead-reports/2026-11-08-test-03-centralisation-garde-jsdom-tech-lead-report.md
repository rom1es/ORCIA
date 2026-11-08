# 2026-11-08 — TEST-03 (étape 1) : centralisation de la garde jsdom d'`apps/web`

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-test-03-centralisation-garde-jsdom` (`Ajustement Transverse` — tests/refactoring, `Epic 13`, ticket `TEST-03`)
- **Capacité(s)** : `none (hygiène/NFR)` — classification `hygiène`
- **Branche dédiée** : `test/e2e-coverage-plan`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)
- 44 usages de `isJsdom` (11 fichiers d'`apps/web/src`) court-circuitent `@orcia/api-client` sous Vitest : les tests « survie au F5 » ne prouvaient que `localStorage` (garde-fou n°3 de `AGENTS.md`).
- **Décision d'ingénierie** : supprimer la garde d'un coup casserait les 42 tests Vitest sans filet. Les specs Playwright (`TEST-04…08`) prouvent désormais les allers-retours réels `UI → API → PostgreSQL` ; la garde peut donc être retirée **par étapes**. Étape 1 (ce rapport) : source unique + audit anti-régression. Impact GitNexus : refactoring mécanique, comportement identique.

## 2. Plan d'Implémentation
- Créer `apps/web/src/lib/runtimeEnv.ts` (`isJsdomRuntime`) et remplacer les 9 définitions inline (`ShellContainer`, `platformSetupStore` ×4, `features/{inbox,catalog,gates,workspaces}`, `useManagedAgentsAndSkills`, `SettingsAiModelsSection`, `SettingsPacksSection`).
- Audit Vitest `runtime-env-guard-audit.test.ts` : échoue si une détection `/jsdom/i.test(` réapparaît hors helper.

## 3. Bilan des Modifications & Résultats (Post-Implémentation)
- `tsc --noEmit` et `check-feature-boundaries.mjs` : OK ; Vitest `apps/web` : 6 fichiers / 42 tests verts (dont l'audit, 2 tests).
- **Reste à faire (ticket `TEST-03` maintenu `in-progress`)** : retirer réellement les branches `if (isJsdomRuntime())` en injectant un transport `@orcia/api-client` (fetch simulé au niveau transport), dont la branche qui **fabrique une réponse d'assistant** (`jsdomReply` dans `useAssistantStreamingTurn.ts`) — code de test dans le chemin de production.
