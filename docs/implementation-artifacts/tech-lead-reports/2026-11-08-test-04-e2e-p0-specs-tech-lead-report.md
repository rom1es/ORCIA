# 2026-11-08 — TEST-04 : specs Playwright E2E P0 (Jour 0 / F5, Mon Assistant, Human-Led, multi-acteurs, mobile)

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-test-04-e2e-p0-specs` (`Ajustement Transverse` — tests, `Epic 13`, ticket `TEST-04`)
- **Capacité(s)** : `none (hygiène/NFR)` — classification `hygiène` ; promeut en `runtime` les capacités couvertes (voir §3)
- **Branche dédiée** : `test/e2e-coverage-plan`
- **Livraison incrémentale** : un commit par spec réussie (04a…04e).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Garde-fou n°3 de `AGENTS.md` (survie au F5) non réellement prouvé : les tests Vitest sont coupés du réseau (`isJsdom`). Un vrai navigateur sur la pile E2E (TEST-01) prouve l'aller-retour `UI → api-client → FastAPI → PostgreSQL 18`.
- Les écrans réels sont pilotés par des données créées via l'UI (premier administrateur, etc.) : les specs créent leurs données par l'UI, sans fixture ni simulation.

### 1.2 Exploration, Impact GitNexus, Factorisation & Dette
- **GitNexus** : specs Playwright uniquement ; si une spec révèle un défaut produit, il est consigné (ticket) — pas de correctif silencieux dans ce lot.
- **Factorisation** : helpers `e2e/support/day0.ts` (reset) et `e2e/support/firstAdmin.ts` (création du premier admin par l'UI).
- **Constat produit** : la création du premier admin est « fire-and-forget » côté UI (`platformSetupStore.createPlatformAdmin`, `.catch(() => undefined)` sur le repli) ; la persistance est asynchrone → les specs attendent (`expect.poll`) l'état `accostage-status`.

---

## 2. Plan d'Implémentation
- 2.4 : `e2e/01-day0-boot-and-f5-persistence.spec.ts`, `02-assistant-streaming-and-folders.spec.ts`, `03-human-led-…`, `04-multi-actor-…`, `05-mobile-companion-…` ; exécution sur la pile isolée, 2 viewports.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

*Mis à jour spec par spec.*

| Spec | Statut | Capacités couvertes |
| :--- | :--- | :--- |
| `01-day0-boot-and-f5-persistence` | ✅ 4/4 (2 viewports) | CAP-004, CAP-005, CAP-061 |
