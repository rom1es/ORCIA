# 2026-11-08 — TEST-03 : suppression de l'angle mort `isJsdom` et transport HTTP/SSE injectable sous Vitest

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-test-03-centralisation-garde-jsdom` (`Ajustement Transverse` — tests/refactoring, `Epic 13`, ticket `TEST-03`)
- **Capacité(s)** : `none (hygiène/NFR)` — classification `hygiène`
- **Branche dédiée** : `test/e2e-coverage-plan`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)
- 44 usages de `isJsdom` (11 fichiers d'`apps/web/src`) court-circuitaient `@orcia/api-client` sous Vitest : les tests « survie au F5 » ne prouvaient que `localStorage` (garde-fou n°3 de `AGENTS.md`), et `useAssistantStreamingTurn.ts` fabriquait une réponse factice (`jsdomReply`) directement dans le code de production.
- **Décision d'ingénierie en 2 étapes** :
  - **Étape 1** : centraliser les 9 détections inline dans `apps/web/src/lib/runtimeEnv.ts` et poser l'audit `runtime-env-guard-audit.test.ts`.
  - **Étape 2 (clôture `TEST-03`)** : supprimer tous les court-circuits `if (isJsdom)` / `if (!isJsdom)` des 10 fichiers de production d'`apps/web/src/` (`ShellContainer.tsx`, `platformSetupStore.tsx`, `features/inbox/index.tsx`, `features/inbox/useAssistantStreamingTurn.ts`, `features/catalog/index.tsx`, `features/catalog/useManagedAgentsAndSkills.ts`, `features/gates/index.tsx`, `features/gates/OrciaDocumentationProcessCard.tsx`, `features/workspaces/index.tsx`, `routes/SettingsPacksSection.tsx`, `routes/SettingsAiModelsSection.tsx`) et installer un transport HTTP/SSE simulé au niveau `fetch` dans `apps/web/src/__tests__/vitest.setup.ts` (`vitest.config.ts`).

## 2. Plan d'Implémentation
- Créer `apps/web/src/__tests__/vitest.setup.ts` interceptant `globalThis.fetch` pour les endpoints `/api/v1/*` (y compris le flux `ReadableStream` SSE `POST /api/v1/assistant/three-speed/stream` et l'état persisté `PUT/GET /api/v1/bootstrap/platform-setup-state`, `GET/POST /api/v1/agents-and-skills`, etc.).
- Retirer toutes les branches `isJsdom` / `jsdomReply` des 10 fichiers de production d'`apps/web/src/`.
- Durcir `runtime-env-guard-audit.test.ts` : vérifier (1) qu'aucun fichier hors `__tests__/` et `lib/runtimeEnv.ts` n'importe ou n'utilise `isJsdomRuntime` / `/jsdom/i`, et (2) qu'un cycle `mutation -> unmount -> localStorage.clear() -> render` réhydrate bien l'état via `GET /api/v1/bootstrap/platform-setup-state` et que l'envoi d'un tour à Mon Assistant traverse `POST /api/v1/assistant/three-speed/stream`.

## 3. Bilan des Modifications & Résultats (Post-Implémentation)
- **Zéro court-circuit `isJsdom` en production** : suppression de toutes les branches `isJsdom` / `isJsdomRuntime()` et de `jsdomReply` dans `ShellContainer.tsx`, `platformSetupStore.tsx`, `features/inbox/index.tsx`, `features/inbox/useAssistantStreamingTurn.ts`, `features/catalog/index.tsx`, `features/catalog/useManagedAgentsAndSkills.ts`, `features/gates/index.tsx`, `features/gates/OrciaDocumentationProcessCard.tsx`, `features/workspaces/index.tsx`, `routes/SettingsPacksSection.tsx` et `routes/SettingsAiModelsSection.tsx`.
- **Transport HTTP/SSE Vitest (`src/__tests__/vitest.setup.ts`)** : interception déterministe de `globalThis.fetch` pour `/api/v1/*`, incluant le flux `ReadableStream` SSE `POST /api/v1/assistant/three-speed/stream` et l'état de configuration (`GET/PUT /api/v1/bootstrap/platform-setup-state`, `GET/POST /api/v1/agents-and-skills`).
- **Validation** : `tsc --noEmit` et `check-feature-boundaries.mjs` : OK ; Vitest `apps/web` : **6 fichiers / 43 tests verts** (dont 3 dans `runtime-env-guard-audit.test.ts` prouvant l'absence de `isJsdomRuntime` en production et la réhydratation HTTP après vidage du cache local).
