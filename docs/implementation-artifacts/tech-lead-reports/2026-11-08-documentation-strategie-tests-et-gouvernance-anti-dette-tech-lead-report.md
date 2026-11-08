# Rapport d'Analyse & d'Implémentation Tech Lead — `2026-11-08-documentation-strategie-tests-et-gouvernance-anti-dette`

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-documentation-strategie-tests-et-gouvernance-anti-dette` (`Ajustement Transverse` — Documentation Architecture & Qualité, `Epic 13`)
- **Capacité(s)** : `none (hygiène/NFR/UX)` — classification `doc`
- **Objectif Résumé** : Documenter de manière exhaustive, structurée et pérenne dans le dépôt ORCIA la stratégie de tests à 5 couches + Sécurité (`AD-17`) ainsi que les 10 mécanismes automatisés et organisationnels mis en place pour empêcher structurellement l'apparition de dette de tests.
- **Statut** : `done`
- **Auteur** : Agent Tech Lead / Dev Senior ORCIA

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique Métier / Technique
Suite à la mise en place complète de la pyramide des tests (`TEST-01` à `TEST-10`, `TEST-01b`), du registre des capacités vérifié en CI (`CAP-ACT-1` à `CAP-ACT-5` dans [`docs/product/capabilities.yaml`](file:///home/romain/Documents/Projects/ORCIA/docs/product/capabilities.yaml)) et des garde-fous de revue systématique dans [`AGENTS.md`](file:///home/romain/Documents/Projects/ORCIA/AGENTS.md) / [`CLAUDE.md`](file:///home/romain/Documents/Projects/ORCIA/CLAUDE.md), la connaissance de la stratégie de tests et des mécanismes anti-dette de tests était répartie entre `ARCHITECTURE-SPINE.md` (`AD-17`), `AGENTS.md`, plusieurs scripts (`infra/scripts/capabilities_registry.py`, `infra/scripts/e2e/`) et différents rapports Tech Lead.

Il manquait un **document de référence unique, complet et opérationnel** dans `docs/` expliquant :
1. **L'architecture complète de la pyramide des tests ORCIA** (`AD-17` Couches 1 à 5 + Couche Sécurité transverse), son outillage réel, ses cibles et ses commandes d'exécution.
2. **Les 10 mécanismes automatisés et bloquants** qui empêchent toute dette de tests d'apparaître au fil des Epics et des ajustements ad-hoc (contrat `capabilities.yaml` $\leftrightarrow$ `tests:` vérifié par `pnpm site:check`, audit AST des anti-patterns, audit zéro bouton muet / zéro `.catch(() => undefined)`, garde centralisée `isJsdomTestEnv`, survie au `F5`, isolation E2E bi-serveur avec refus de toucher la base de dev, etc.).
3. **Les conventions de nommage fonctionnel des tests** (sans trace d'Epic ni de User Story) et le protocole de revue systématique à chaque changement.

### 1.2 Analyse d'Impact GitNexus & Architecture Hexagonale (`AD-19`)
- **Modules touchés** : Documentation (`docs/testing-strategy.md`, `README.md`, `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md`, `AGENTS.md`, `CLAUDE.md`).
- **Impact code applicatif** : Aucun (`0` symbole Python/TypeScript applicatif modifié).

### 1.3 Exploration & Chiffres Clés
- **Pyramide active dans le monorepo** :
  - **Couche 1 (Unitaires & Composants UI)** : `50` fichiers Python dans `tests/unit/`, `10` fichiers Vitest dans `packages/ui/src/__tests__/`, `1` fichier dans `packages/api-client/src/__tests__/`, `13` fichiers dans `apps/web/src/__tests__/` (couverture $\ge 90\%$ exigée sur `orcia-kernel` et `orcia-core`).
  - **Couche 2 (Intégration Verticale Conteneurisée)** : `17` fichiers dans `tests/integration/*_postgres18*.py` sur PostgreSQL 18 + `pgvector`, Redis 7.4 et SeaweedFS S3 via `testcontainers-python`.
  - **Couche 3 (Contrat OpenAPI 3.1 & Conformité)** : `tests/contract/test_openapi_and_rfc9457_contract.py` + `tests/conformance/test_connector_conformance.py`.
  - **Couche 4 (Évaluations Cognitives & Ontologiques `0 $`)** : `3` suites dans `tests/evals/` + `2` datasets dorés (`tests/evals/golden/citations.jsonl`, `tests/evals/golden/assistant_and_ontology.jsonl`).
  - **Couche 5 (E2E Bi-Serveur Isolé `@playwright/test`)** : `12` specs `apps/web/e2e/00..11-*.spec.ts` sur pile éphémère isolée (`infra/scripts/e2e/`, ports `55433` / `56380` / `18000` / `13100`, workflow CI `.github/workflows/e2e.yml`).
  - **Couche Sécurité & RBAC Transverse** : `tests/security/test_api_security_baseline.py` (`21` tests couvrant SSRF, `READ_ONLY_OBSERVER`, escalade de privilèges RBAC, masquage `CONFIDENTIAL_RESTRICTED`, secrets canaris `DEC-SEC-01`, RFC 9457).

### 1.4 Opportunités de Factorisation & Dette Technique Identifiée
- Centraliser toute la doctrine de test dans [`docs/testing-strategy.md`](file:///home/romain/Documents/Projects/ORCIA/docs/testing-strategy.md) et référencer ce document unique depuis `README.md`, `architecture.md`, `AGENTS.md` et `CLAUDE.md` pour éviter toute duplication ou divergence documentaire.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/`)
- `N/A` (évolution documentaire et de gouvernance).

### 2.2 Noyau Hexagonal, Algorithmes & Workers (`packages/orcia-core/`, `apps/worker/`)
- `N/A`.

### 2.3 Couche Backend FastAPI & Contrats OpenAPI (`apps/api/`, `packages/api-client/`)
- `N/A`.

### 2.4 Documentation de Référence & Gouvernance (`docs/`, `README.md`, `AGENTS.md`, `CLAUDE.md`)
1. Créer [`docs/testing-strategy.md`](file:///home/romain/Documents/Projects/ORCIA/docs/testing-strategy.md) détaillant :
   - La philosophie « Zero Test Debt, Zero Mock Persistence, Zero Dead UI ».
   - Les 5 couches `AD-17` + la couche Sécurité transverse (diagramme Mermaid, périmètre, outillage, SLAs, exemples concrets).
   - Les **10 mécanismes automatisés anti-dette de tests** (avec liens vers chaque test d'audit et script de contrôle CI).
   - Le cycle de vie d'une modification (matrice d'impact pré-codage Section `2.5` $\rightarrow$ TDD `Red-Green-Refactor` $\rightarrow$ validation post-codage Section `3.3` jusqu'au E2E $\rightarrow$ `capabilities.yaml` + `pnpm site:check`).
   - Les règles de nommage fonctionnel des tests (zéro référence d'Epic/Story) et le guide des commandes d'exécution.
2. Mettre à jour [`README.md`](file:///home/romain/Documents/Projects/ORCIA/README.md) (Sections 6 et 7), [`docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md) (Section 7 `AD-17`), [`AGENTS.md`](file:///home/romain/Documents/Projects/ORCIA/AGENTS.md) et [`CLAUDE.md`](file:///home/romain/Documents/Projects/ORCIA/CLAUDE.md) pour pointer vers `docs/testing-strategy.md`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, OBLIGATOIRE)

| Couche `AD-17` | Périmètre & Outils | Fichiers de Tests Impactés (Créés / Modifiés / Exécutés) | Pertinence & Justification |
| :--- | :--- | :--- | :--- |
| **Couche 1 — Unitaires & Composants UI** | `pytest` ($\ge 90\%$) | `tests/unit/test_capabilities_registry.py`, `tests/unit/test_codebase_architectural_anti_patterns_audit.py` | Vérifier que les contrôles documentaires et le registre restent 100 % verts. |
| **Couche 2 — Intégration Verticale Conteneurisée** | `testcontainers` PG18 | Non impactée (aucune modification SQL/API) | Documentée en détail dans `docs/testing-strategy.md`. |
| **Couche 3 — Contrat OpenAPI 3.1 & Conformité** | `tests/contract/` | Non impactée | Documentée dans `docs/testing-strategy.md`. |
| **Couche 4 — Évaluations Cognitives & Ontologiques (`0 $`)** | `tests/evals/` | `tests/evals/test_assistant_and_ontology_evals.py`, `tests/evals/test_citations_golden_dataset.py` | Documentée dans `docs/testing-strategy.md`. |
| **Couche 5 — End-to-End Playwright (`apps/web/e2e/`)** | `@playwright/test` | Non impactée | Architecture bi-serveur isolée documentée dans `docs/testing-strategy.md`. |
| **Transverse — Sécurité & RBAC (`tests/security/`)** | `tests/security/` | `tests/security/test_api_security_baseline.py` | Documentée dans `docs/testing-strategy.md`. |
| **Registre — Traçabilité `capabilities.yaml`** | `pnpm site:check` | `docs/product/capabilities.yaml` | Vérification de cohérence documentaire et synchronisation du catalogue `/showcase` via `pnpm site:sync` + `pnpm site:check`. |



---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés & Modifiés

| Fichier | Nature | Résumé des Modifications |
| :--- | :--- | :--- |
| [`docs/testing-strategy.md`](file:///home/romain/Documents/Projects/ORCIA/docs/testing-strategy.md) | Créé | Référentiel complet de la stratégie de tests `AD-17` (5 couches + Sécurité transverse, diagramme Mermaid, détail opérationnel par couche) et des **10 mécanismes automatisés anti-dette de tests**, du cycle obligatoire en 4 étapes, des conventions de nommage fonctionnel et des commandes d'exécution. |
| [`README.md`](file:///home/romain/Documents/Projects/ORCIA/README.md) | Modifié | Enrichissement de la Section 6 (*Qualité du code et exécution de la pyramide des tests*) avec les commandes des 5 couches + Sécurité + `pnpm site:check` et ajout du lien vers `docs/testing-strategy.md` en Section 7. |
| [`docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md) | Modifié | Mise à jour de la sous-section `7.5` (pile bi-serveur E2E isolée) et ajout de la sous-section `7.6. Couche Transverse Sécurité & 10 Mécanismes Automatisés Anti-Dette de Tests` pointant vers `docs/testing-strategy.md`. |
| [`AGENTS.md`](file:///home/romain/Documents/Projects/ORCIA/AGENTS.md) / [`CLAUDE.md`](file:///home/romain/Documents/Projects/ORCIA/CLAUDE.md) | Modifiés | Référencement de `docs/testing-strategy.md` dans `Where things are` et en en-tête de la Section 6. |
| [`docs/implementation-artifacts/tech-lead-reports/README.md`](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/tech-lead-reports/README.md) | Modifié | Indexation du présent rapport Tech Lead. |

### 3.2 Résultats Chiffrés & Métriques
- **Couches documentées** : `5` couches `AD-17` + `1` couche Sécurité transverse (`93` fichiers de tests actifs).
- **Mécanismes anti-dette documentés et référencés** : `10` verrous automatisés et organisationnels.

### 3.3 Validation des 5 Couches de Tests (`AD-17`) + Sécurité (Jusqu'au E2E Playwright)
- **Couche 1 (Unitaires & Audits)** : `.venv/bin/pytest tests/unit/test_capabilities_registry.py tests/unit/test_codebase_architectural_anti_patterns_audit.py -q` $\rightarrow$ **VERT**.
- **Couche 4 (Evals `0 $`)** : `.venv/bin/pytest tests/evals -q` $\rightarrow$ **16 passed**.
- **Couche Sécurité** : `.venv/bin/pytest tests/security -q` $\rightarrow$ **21 passed**.
- **Synchronisation `/showcase`** : `pnpm site:sync` exécuté avec succès.
