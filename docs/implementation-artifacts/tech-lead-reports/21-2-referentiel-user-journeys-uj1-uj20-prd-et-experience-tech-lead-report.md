# Story 21.2 — Référentiel Complet des User Journeys (`UJ-1` à `UJ-20`) dans `prd.md` & `Key Flows` dans `EXPERIENCE.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `21-2-referentiel-user-journeys-uj-1-a-uj-20-prd-experience-et-coherence-auto` (`Epic 21`)
- **Capacité(s)** : `none (référentiel produit & UX)` — classification : `doc` (`GEMINI.md` §5)
- **Auteur / Contexte** : Product Manager (`John`) & UX Designer (`Sally`) — Story 21.2 (`FR-1`..`FR-36`, `UX-DR1`..`UX-DR17`, `AIOPS-INCIDENT-LOOP-01`). Compléter le référentiel des User Journeys (`UJ-1` à `UJ-20`) dans `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md` (§2.3 et §4.10) en annotant `AIOPS-INCIDENT-LOOP-01` sur `UJ-12` et en rédigeant `UJ-13` à `UJ-20`, enrichir `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` (§9 `Key Flows`) pour couvrir `UJ-1` à `UJ-20` sans jargon technique interne (`EXPERIENCE.md` §1.2), et préparer le contrôle automatique par `tests/unit/test_uj_prd_experience_consistency.py` (sous-agent `21.2-test`).
- **Commits associés** : Branche `feat/epic-21-user-journeys-e2e-db-audit` (implémentation documentaire par `21.2-impl` ; validation et Section 3 confiées au sous-agent `21.2-test`).

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problématique** :
  - À l'issue de la Story 21.1, les `62` capacités `kind: feature` de `docs/product/capabilities.yaml` sont rattachées à `UJ-1`..`UJ-20`. Or `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md` s'arrête actuellement à `UJ-12` (§2.3), et `§4.10` (`FR-31`..`FR-36`) référence `Capacités :` sans mentionner `Réalise UJ-...`.
  - De plus, `UJ-12` dans `prd.md` décrit encore l'ancien scénario d'auto-remédiation avec écriture de code et Sandbox TDD applicative alors que `AIOPS-INCIDENT-LOOP-01` (`docs/implementation-artifacts/sprint-status.yaml`) a recadré cette boucle en qualification autonome d'incident sans modification du code source ni écriture Git par ORCIA.
  - Enfin, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` (§9 `Key Flows`) ne contient que les Flows 1 à 3 (`UJ-1`, `UJ-2`, `UJ-3`, `UJ-4`, `UJ-7`, `UJ-9`) : `UJ-5`, `UJ-6`, `UJ-8`, `UJ-10`, `UJ-11`, `UJ-12` et `UJ-13`..`UJ-20` n'y figurent pas encore.
- **Comportement attendu vs actuel** :
  - Actuellement : désalignement documentaire entre `capabilities.yaml` (`UJ-1`..`UJ-20`), `prd.md` (`UJ-1`..`UJ-12`, `FR-31`..`FR-36` sans `Réalise UJ-...`) et `EXPERIENCE.md` (§9 limité à 6 `UJ`).
  - Attendu : alignement à `100 %` entre `capabilities.yaml`, `prd.md` (§2.3 `UJ-1`..`UJ-20` avec `AIOPS-INCIDENT-LOOP-01` sur `UJ-12` et format structuré incluant `- **Persistance PostgreSQL 18 attendue** :` sur `UJ-13`..`UJ-20` ; §4.10 `FR-31`..`FR-36` avec `Réalise UJ-...` aligné sur `capabilities.yaml`) et `EXPERIENCE.md` (§9 `Flows 1..11` couvrant chaque `UJ-1`..`UJ-20` avec écran d'entrée, gestes clés, vérification `F5`, retours d'erreur / RBAC et zéro jargon interne).
- **Contraintes d'architecture** :
  - Ne pas altérer le corps des `UJ-1`..`UJ-11` ni les `FR-1`..`FR-30` existants (tous vérifiés comme portant déjà `Réalise UJ-...`).
  - Respecter les 3 invariants de microcopy de `EXPERIENCE.md` §1.2 : aucun terme d'implémentation interne visible dans les libellés d'écran décrits en §9 (`PG18`, `PostgreSQL 18`, `DBOS`, `pgvector`, `halfvec`, `Argon2id`, `Starlark`, `Wasmtime`, `Outbox`, `Passthrough`, `Service Principal`, `Tie-Break`, `Rubber-stamping`, `What-If`, `Rebase`, `Verrou V1..V5`, `RRF`, `BM25`, `HNSW`, `AD-*`, `RFC 9457`, etc.).
  - Préserver la compatibilité avec `infra/scripts/capabilities_registry.py` (`prd_max_fr()` lit `^#### FR-(\d+) :` dans `prd.md`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - Requête `capabilities_registry validate_registry sync_site_catalog` : `capabilities_registry.py` (`PRD_PATH`, `prd_max_fr()`, `_validate_kind_fields()`) est le point d'entrée de validation CI (`pnpm site:check`) consommé par `infra/scripts/sync_site_catalog.py` et vérifié par `tests/unit/test_capabilities_registry.py` et `tests/unit/test_site_catalog_sync.py`. Aucune dépendance runtime backend/frontend (`orcia_core`, `orcia_api`, `apps/web`) n'est impactée par les modifications documentaires de `prd.md` et `EXPERIENCE.md`.
- **Exploration & Chiffres Clés (`docs/product/capabilities.yaml` & `prd.md`)** :
  - Inventaire réel extrait de `docs/product/capabilities.yaml` (`65` capacités : `3` `foundation`, `62` `feature`) :
    - `UJ-1` : `CAP-020`, `CAP-022`, `CAP-072`
    - `UJ-2` : `CAP-024`
    - `UJ-3` : `CAP-011`, `CAP-024`, `CAP-033`
    - `UJ-4` : `CAP-021`, `CAP-040`, `CAP-041`, `CAP-043`
    - `UJ-5` : `CAP-010`, `CAP-021`, `CAP-023`, `CAP-081`
    - `UJ-6` : `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`
    - `UJ-7` : `CAP-003`, `CAP-024`
    - `UJ-8` : `CAP-041`, `CAP-065`, `CAP-200`
    - `UJ-9` : `CAP-002`, `CAP-080`, `CAP-082`, `CAP-090`
    - `UJ-10` : `CAP-020`, `CAP-021`, `CAP-083`, `CAP-140`, `CAP-160`
    - `UJ-11` : `CAP-201`
    - `UJ-12` : `CAP-201` (recadré `AIOPS-INCIDENT-LOOP-01`)
    - `UJ-13` : `CAP-001`, `CAP-004`, `CAP-005`, `CAP-058`, `CAP-061`
    - `UJ-14` : `CAP-043`, `CAP-050`, `CAP-051`, `CAP-058`, `CAP-065`, `CAP-067`, `CAP-203`
    - `UJ-15` : `CAP-052`, `CAP-053`, `CAP-054`, `CAP-190`
    - `UJ-16` : `CAP-003`, `CAP-063`, `CAP-069`
    - `UJ-17` : `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-073`, `CAP-074`, `CAP-075`, `CAP-076`, `CAP-160`
    - `UJ-18` : `CAP-010`, `CAP-011`, `CAP-080`, `CAP-081`, `CAP-084`, `CAP-180`
    - `UJ-19` : `CAP-002`, `CAP-055`, `CAP-056`, `CAP-057`, `CAP-082`, `CAP-083`, `CAP-090`, `CAP-091`, `CAP-092`, `CAP-140`, `CAP-150`
    - `UJ-20` : `CAP-042`, `CAP-060`, `CAP-062`, `CAP-064`, `CAP-066`, `CAP-068`
  - Mapping exact `FR-31`..`FR-36` $\rightarrow$ `UJ-*` dérivé de `capabilities.yaml` :
    - `FR-31` : `UJ-13`, `UJ-14`, `UJ-15`, `UJ-19`
    - `FR-32` : `UJ-8`, `UJ-13`, `UJ-14`, `UJ-16`, `UJ-20`
    - `FR-33` : `UJ-1`, `UJ-10`, `UJ-15`, `UJ-17`
    - `FR-34` : `UJ-5`, `UJ-9`, `UJ-14`, `UJ-18`, `UJ-19`
    - `FR-35` : `UJ-9`, `UJ-10`, `UJ-18`, `UJ-19`
    - `FR-36` : `UJ-9`, `UJ-10`, `UJ-17`, `UJ-19`
  - Audit `FR-1`..`FR-30` dans `prd.md` : les `30` sections portent déjà `Réalise UJ-...` dans leur texte.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Consolidation unique de la traçabilité `CAP ↔ UJ ↔ FR` entre `capabilities.yaml`, `prd.md` et `EXPERIENCE.md`, préparant le verrou CI `pnpm site:check` de la Story 21.3. Aucune dette technique créée.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Non applicable : aucune table ni migration PostgreSQL modifiée en Story 21.2.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Non applicable : aucun code Python applicatif modifié en Story 21.2.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`) & Référentiel PRD (`prd.md`)
- Mise à jour de `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md` :
  - Mettre à jour les mentions d'en-tête globales (`§2.3 Key User Journeys (UJ-1 à UJ-20)`, `§4`, `§6.1`) tout en laissant intacts les corps de `UJ-1`..`UJ-11` et `FR-1`..`FR-30`.
  - Annoter `#### UJ-12.` avec le cadrage `AIOPS-INCIDENT-LOOP-01` : qualification autonome d'incident depuis `LogSinkQueryPort`, déduplication `error_fingerprint_sha256`, création/qualification du ticket Jira d'incident et du paquet de contexte MCP, et vérification post-résolution en boucle fermée (`POST_ACTION_VERIFICATION`), sans modification du code source ni écriture Git par ORCIA.
  - Ajouter `#### UJ-13.` à `#### UJ-20.` au format complet (`- **Persona + contexte** :`, `- **Entry state** :`, `- **Path** :`, `- **Climax** :`, `- **Resolution** :`, `- **Edge case** :`, `- **Persistance PostgreSQL 18 attendue** :`) couvrant les capacités exactes attribuées dans `capabilities.yaml` (et leurs `db_tables` / `read_only_surface`).
  - Compléter `§4.10` (`FR-31` à `FR-36`) avec la mention explicite `Réalise UJ-...` alignée sur `capabilities.yaml`.

### 2.4 Interface Utilisateur & Expérience (`EXPERIENCE.md`)
- Mise à jour de `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` (`## 9. Key Flows`) :
  - Mettre à jour le titre de section `## 9. Key Flows (Ancrés sur les User Journeys UJ-1 à UJ-20)`.
  - Conserver les Flows 1 à 3 et ajouter les **Flows 4 à 11** afin que chaque identifiant `UJ-1` à `UJ-20` apparaisse explicitement dans §9 (`UJ-5`, `UJ-6`, `UJ-8`, `UJ-10`, `UJ-11`, `UJ-12` et `UJ-13`..`UJ-20`).
  - Chaque Flow documente : écran d'entrée, gestes clés, vérification après rechargement (`F5`), retours d'erreur / RBAC, avec un vocabulaire strictement métier et **zéro jargon technique interne** (`EXPERIENCE.md` §1.2).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Unitaires Python `tests/unit/`)** : `tests/unit/test_uj_prd_experience_consistency.py` (rédigé et exécuté par le sous-agent `21.2-test`) vérifiant la présence et la continuité `UJ-1`..`UJ-20` dans `prd.md` §2.3, la présence de `Réalise UJ-...` sur `FR-1`..`FR-36`, la couverture `UJ-1`..`UJ-20` dans `EXPERIENCE.md` §9 (et l'absence de jargon interdit en §9), et la cohérence 100 % avec `docs/product/capabilities.yaml`.
- **Couche 2 (Intégration Verticale)** : Non applicable.
- **Couche 3 (Contrats & Gouvernance Registre)** : `pnpm site:check` / `capabilities_registry.py`.
- **Couche 4 & Sécurité** : Non applicable directement.
- **Couche 5 (E2E Playwright)** : Référentiel socle utilisé par les Stories 21.4..21.8.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification) | Description synthétique |
| :--- | :--- | :--- |
| `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md` | Modification (`769` lignes) | Recadrage de `UJ-12` selon `AIOPS-INCIDENT-LOOP-01` (qualification autonome depuis `LogSinkQueryPort`, paquet de contexte MCP, vérification post-résolution, zéro écriture code/Git), ajout des parcours structurés `UJ-13`..`UJ-20` en §2.3, mise à jour des en-têtes globaux (`UJ-1`..`UJ-20`) et ajout de `Réalise UJ-...` sur `FR-31`..`FR-36` (§4.10) aligné sur `docs/product/capabilities.yaml`. |
| `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` | Modification (`258` lignes) | Mise à jour du titre `## 9. Key Flows (Ancrés sur les User Journeys UJ-1 à UJ-20)` et ajout des `Flows 4..11` couvrant intégralement `UJ-1`..`UJ-20` (écrans d'entrée, gestes clés, vérification `F5`, retours d'erreur/RBAC) sans jargon technique interne. |
| `tests/unit/test_uj_prd_experience_consistency.py` | Création (`139` lignes) | Suite de `4` tests unitaires de cohérence croisée vérifiant la continuité `#### UJ-1.`..`#### UJ-20.` dans `prd.md`, le référencement `UJ-*` sur `FR-1`..`FR-36`, la couverture `UJ-1`..`UJ-20` dans les corps `### Flow` de `EXPERIENCE.md` §9, et l'alignement à `100 %` avec `docs/product/capabilities.yaml` (noms conformes à `docs/testing-strategy.md` §6). |
| `docs/implementation-artifacts/tech-lead-reports/21-2-referentiel-user-journeys-uj1-uj20-prd-et-experience-tech-lead-report.md` | Création | Rapport Tech Lead complet (Sections 1, 2 et 3). |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Enregistrement de l'entrée `Story 21.2` dans l'index des rapports Tech Lead. |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Passage de `21-2-referentiel-user-journeys-uj-1-a-uj-20-prd-experience-et-coherence-auto` à `done` et actualisation de `last_updated` (`11-18-2026 09:04`). |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `dist/orcia-site/index.html` | Modification (générés) | Artefacts du catalogue synchronisés par `pnpm site:sync` (`165` rapports). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture documentaire & alignement registre** :
  - `20/20` titres continus `#### UJ-1.`..`#### UJ-20.` présents dans `prd.md` §2.3 (`0` trou de numérotation).
  - `36/36` exigences `FR-1`..`FR-36` dans `prd.md` référencent explicitement au moins un `UJ-*` valide (`0` exigence orpheline).
  - `20/20` parcours `UJ-1`..`UJ-20` couverts dans les corps `### Flow 1`..`### Flow 11` de `EXPERIENCE.md` §9.
  - `62/62` capacités `kind: feature` (sur `65` capacités `live`) alignées à `100 %` entre `capabilities.yaml`, `prd.md` et `EXPERIENCE.md`.
- **Tests unitaires Python (`pytest`)** :
  - `.venv/bin/pytest tests/unit/test_uj_prd_experience_consistency.py tests/unit/test_capabilities_registry.py tests/unit/test_site_catalog_sync.py` : `21 passed` (`4` tests dans `test_uj_prd_experience_consistency.py`, `14` dans `test_capabilities_registry.py`, `3` dans `test_site_catalog_sync.py`).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check tests/unit/test_uj_prd_experience_consistency.py` : `All checks passed!`
  - `.venv/bin/ruff format --check tests/unit/test_uj_prd_experience_consistency.py` : `1 file already formatted`
  - `pnpm site:sync && pnpm site:check` : OK (`65/65` capacités `live`, `165` rapports, `28` routes, `133` primitives UI, `0` erreur).
  - MCP `gitnexus:detect_changes` (`repo: "/home/romain/Documents/Projects/ORCIA"`, `scope: "all"`) : `risk_level: "low"`, `changed_count: 0`, `affected_count: 0`, `changed_files: 4`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a — Tests Unitaires Python (`pytest`)** : `21 passed` (`test_uj_prd_experience_consistency.py`, `test_capabilities_registry.py`, `test_site_catalog_sync.py`), garantissant l'alignement structurel permanent entre `prd.md`, `EXPERIENCE.md` et `capabilities.yaml`.
- **Couche 2 — Intégration Verticale `HTTP ➔ PostgreSQL 18`** : Non applicable (évolution purement documentaire et outillage de cohérence statique).
- **Couche 3 — Contrats, Schémas & Gouvernance Statique** : `ruff check`, `ruff format --check` et `pnpm site:sync && pnpm site:check` passés à `0` erreur.
- **Couche 4 — Orchestration IA & Evals Golden Dataset** : Non applicable.
- **Couche Sécurité / Red-Team** : Non applicable.
- **Couche 5 — E2E Navigateur Playwright** : Non applicable directement en Story 21.2 (`UJ-1`..`UJ-20` et `EXPERIENCE.md` §9 servent de référentiel aux campagnes E2E des Stories 21.4..21.8).
