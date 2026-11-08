# 2026-11-08 — TEST-05 : specs Playwright E2E P1 (gates, Mes Espaces, agents)

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-test-05-e2e-p1-specs` (`Ajustement Transverse` — tests, `Epic 13`, ticket `TEST-05`)
- **Capacité(s)** : `none (hygiène/NFR)` — classification `hygiène` ; couvre en `runtime` CAP-050/051 (BU/équipe), CAP-080 (espace), CAP-090 (agents)
- **Branche dédiée** : `test/e2e-coverage-plan`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Suite de `TEST-04` : couvrir les parcours P1 (gates, Mes Espaces/ADN/glossaire, agents/skills/MCP) sur la pile E2E isolée, sans fixture ni simulation.
- Constat à l'exploration (cf. §3) : certains parcours cibles n'ont **pas d'UI montée** ou nécessitent un espace déjà sélectionné ; ils sont tracés plutôt que simulés.

### 1.2 Exploration, Impact GitNexus, Factorisation & Dette
- **GitNexus** : specs Playwright uniquement ; aucun symbole applicatif modifié.
- **Factorisation** : `e2e/support/orgAndWorkspace.ts` (`createBuAndTeamViaUi`, `createWorkspaceViaUi`) réutilisé par les specs 07/08 ; timeout Playwright porté à 90 s (parcours de saisie ≈ 20 s).
- **Piège constaté** : `locator.click()` sans timeout attend jusqu'au timeout du test → toujours borner les sondes.

---

## 2. Plan d'Implémentation
- 2.4 : `06-gates-review-and-anti-rubber-stamping`, `07-spaces-org-and-workspace-persistence`, `08-agents-skills-persistence`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

| Spec | Statut | Capacités / défaut |
| :--- | :--- | :--- |
| `06-gates-review-and-anti-rubber-stamping` | ⏸️ `test.fixme` — **BUG-E2E-05** : `CognitiveReviewBriefingGrid` / `ChunkValidationCard` non montés dans `apps/web` | CAP-032 (non couverte) |
| `07-spaces-org-and-workspace-persistence` | ✅ BU + équipe + espace créés par l'UI → persistés (`platform-setup-state`) et réaffichés après F5 sans localStorage | CAP-050/051, CAP-080 |
| `08-agents-skills-persistence` | ✅ agent créé (POST 2xx) → réaffiché après F5 sans localStorage | CAP-090 |

- **Non couvert** : compilation Starlark / glossaire FIFO (promotion) — la vue `DnaStarlarkCompilerAndGlossaryLifecycleView` n'est pas atteignable sans sélection d'espace (onglet `workspace-tab-GLOSSARY_RULES` absent après création, liste « Tous (0) ») ; banc de test MCP 4 étapes non exercé → à reprendre (`TEST-06`/`TEST-10`).
- Aucun code applicatif modifié.
