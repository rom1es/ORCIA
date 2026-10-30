# Rapport d'Implémentation Tech Lead — Story 4.3 : Gates Humaines Adaptatives, Briefing de Revue 4 Blocs (`review-briefing-grid`), Validation par Découpage (`chunk-validation-card`) & Garde-fou Anti-Rubber-Stamping (`< 15 s`)

- **Clé de Story** : `4-3-gates-humaines-adaptatives-briefing-de-revue-4-blocs-review`
- **Epic** : `Epic 4` — Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution (Actions Jira, Sandbox & MCP IDE)
- **Date** : `2026-10-30`
- **Auteur** : Tech Lead / Dev Senior (`Amelia`, `Sally` & `Sophie`)
- **Statut** : `done`
- **Références Architecture & UX** : `FR-6`, `FR-19`, `AD-11`, `AD-19`, `UX-DR4`, `UX-DR5`, `UX-DR10`, `SM-C1`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique
Après l'exécution de la Gate Déterministe (`Stories 4.1 / 4.1a`) et de la Gate Agentique à 5 lentilles (`Story 4.2`), l'artefact atteint la **Gate Humaine Adaptative (`AD-11`, `FR-6`, `FR-19`)**. Deux écueils opposés menacent la gouvernance humaine des workflows assistés par IA :
1. **La fatigue d'approbation par sollicitation excessive** : soumettre systématiquement chaque étape triviale et conforme à une validation humaine complète ralentit le flux et banalise l'acte de revue.
2. **Le *Rubber-Stamping* (tamponnage aveugle, `SM-C1`)** : face à un artefact long ($> 1\,000$ ou $> 1\,500$ mots), un valideur pressé clique sur « Approuver » en quelques secondes sans lire les hypothèses retenues par l'IA ni inspecter chaque section critique.

### 1.2 Analyse d'Impact GitNexus (Pré-Codage)
- **`gitnexus_impact({target: "DeterministicGateService", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`4` importateurs directs : `bootstrap/engine.py`, `gates/__init__.py`, `orchestration/step_executors.py`, `apps/api/src/orcia_api/routers/gates.py`).
- **`gitnexus_impact({target: "AgenticGateService", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`2` importateurs directs : `gates/__init__.py`, `gates/deterministic.py`).

### 1.3 Exploration & Chiffres Clés
- **Base de données** : la table `gate_evaluations` (`0017_story_4_1`) possède déjà les colonnes `briefing_4blocks_jsonb`, `review_duration_ms` et `fast_approval_warning`. La révision Alembic `0018_story_4_3_chunk_approvals.py` ajoute la table `chunk_approvals` (`UUIDv7` PK) liée à `gate_evaluations(id) ON DELETE CASCADE` et `human_anchor_signatures(id) ON DELETE SET NULL`.
- **Contrôle de volumétrie (`< 300-400` lignes)** :
  - Création de `apps/api/src/orcia_api/routers/human_gates.py` (`199` lignes) et `apps/api/src/orcia_api/schemas/human_gates.py` (`121` lignes) afin de ne pas alourdir `routers/gates.py` (`391` lignes).
  - Côté `@orcia/ui` (`packages/ui/src/primitives/`), création de `CognitiveReviewBriefingGrid.tsx` (`226` lignes, `UX-DR4`) et `ChunkValidationCard.tsx` (`365` lignes, `UX-DR5` + `UX-DR10`).

### 1.4 Opportunités de Factorisation (`DRY`) & Dette Technique
- Réutilisation de `GateEvaluated.create(...)` (`orcia_kernel.events`) et `OutboxRelayPort` pour publier l'événement `GateEvaluated` (`gate_type="HUMAN"`) dans `domain_events_outbox`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migration Alembic (`infra/migrations/versions/0018_story_4_3_chunk_approvals.py`)
- Création de la table `chunk_approvals` en SQL pur (`op.execute(sa.text(...))`) avec `id UUID PRIMARY KEY`, `gate_evaluation_id UUID NOT NULL REFERENCES gate_evaluations(id) ON DELETE CASCADE`, `workspace_id UUID NOT NULL`, `run_id UUID NOT NULL`, `step_execution_id UUID NOT NULL`, `chunk_key VARCHAR(128) NOT NULL`, `section_title VARCHAR(255) NOT NULL`, `section_index INTEGER NOT NULL`, `content_markdown TEXT NOT NULL`, `word_count INTEGER NOT NULL`, `human_authored_required BOOLEAN NOT NULL DEFAULT FALSE`, `status VARCHAR(32) NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'CO_EDITED', 'CHALLENGED'))`, `reviewer_user_id VARCHAR(128) NULL`, `human_anchor_signature_id UUID NULL REFERENCES human_anchor_signatures(id) ON DELETE SET NULL`, `challenge_reason TEXT NULL`, `reviewed_at TIMESTAMPTZ NULL`, et contrainte `UNIQUE (gate_evaluation_id, chunk_key)`.

### 2.2 Noyau Hexagonal : `AdaptiveHumanGateService` (`packages/orcia-core/src/orcia_core/gates/human.py`)
- Évaluation des 3 politiques (`mandatory_full`, `risk_or_exception_based`, `sampling` `20 %` déterministe par hash SHA-256).
- Découpage automatique ou structuré de l'artefact en `ChunkApprovalRecord` et gestion des 3 actions par section (`APPROVE`, `CO_EDIT` avec signature `SHA-256`, `CHALLENGE`).
- Vérification d'approbation finale :
  - Blocage (`UnapprovedChunksRemainingError` -> `HTTP 422 ERR_UNAPPROVED_CHUNKS_REMAINING`) tant qu'une section requise est `PENDING` ou `CHALLENGED` ou que le bloc 4 (`hypotheses_retained`) du briefing n'a pas été inspecté.
  - Garde-fou Anti-Rubber-Stamping (`RubberStampingGuardTriggeredError` -> `HTTP 422 ERR_RUBBER_STAMPING_GUARD_TRIGGERED`) si `total_word_count > 1000` et `review_duration_ms < 15000` sans `explicit_hypotheses_confirmation=True`, et marquage `fast_approval_warning = True` dès confirmation.

### 2.3 Couche Backend FastAPI & Contrats OpenAPI (`apps/api/`, `packages/api-client/`)
- Endpoints dans `apps/api/src/orcia_api/routers/human_gates.py` :
  - `POST /api/v1/gates/human/evaluate` : initialise ou auto-valide une Gate Humaine selon sa politique (`mandatory_full`, `risk_or_exception_based`, `sampling`).
  - `POST /api/v1/gates/human/{gate_evaluation_id}/inspect-hypotheses` : marque le Bloc 4 (*Hypothèses Retenues*) comme inspecté.
  - `POST /api/v1/gates/human/{gate_evaluation_id}/chunks/{chunk_key}/decide` : valide (`APPROVE`), co-édite (`CO_EDIT`) ou challenge (`CHALLENGE`) une section.
  - `POST /api/v1/gates/human/{gate_evaluation_id}/finalize` : soumet l'approbation finale de la Gate Humaine avec vérification des chunks, inspection du bloc 4 et garde-fou `< 15 s`.

### 2.4 Design System `@orcia/ui`, `i18n` (`fr`/`en`) & Module `features/gates` (`packages/ui/`, `apps/web/`)
- Création de `packages/ui/src/primitives/CognitiveReviewBriefingGrid.tsx` (`UX-DR4` : grille $2 \times 2$ avec encadrement ambre `--color-arbitration-amber` sur le bloc 4 *Hypothèses Retenues* jusqu'à son inspection).
- Création de `packages/ui/src/primitives/ChunkValidationCard.tsx` (`UX-DR5` + `UX-DR10` : cartes de validation par découpage navigables via `Alt + ↑ / ↓`, 3 actions par section, absence de bouton « Tout Approuver en 1 clic » tant que des sections restent `PENDING`, et modale `AntiRubberStampingGuardModal` si `< 15 s` sur $> 1\,000$ mots).
- Enrichissement de `apps/web/src/i18n/locales/{fr,en}.ts` et intégration dans `apps/web/src/features/gates/index.tsx`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés & Modifiés
| Fichier | Action | Lignes | Rôle |
| :--- | :--- | :---: | :--- |
| `infra/migrations/versions/0018_story_4_3_chunk_approvals.py` | Créé | `77` | Migration Alembic (`chunk_approvals` UUIDv7 PK, index & `UNIQUE (gate_evaluation_id, chunk_key)`). |
| `packages/orcia-core/src/orcia_core/gates/human.py` | Créé | `428` | `AdaptiveHumanGateService` (3 politiques, découpage, `APPROVE`/`CO_EDIT`/`CHALLENGE`, garde-fou `< 15 s`). |
| `packages/orcia-core/src/orcia_core/gates/errors.py` | Modifié | `116` | Erreurs `UnapprovedChunksRemainingError`, `RubberStampingGuardTriggeredError`, `HumanGateNotFoundError`. |
| `apps/api/src/orcia_api/schemas/human_gates.py` | Créé | `121` | Schémas HTTP Pydantic v2 pour les Gates Humaines. |
| `apps/api/src/orcia_api/routers/human_gates.py` | Créé | `199` | Endpoints REST `/api/v1/gates/human/*` + garde `READ_ONLY_OBSERVER`. |
| `packages/ui/src/primitives/CognitiveReviewBriefingGrid.tsx` | Créé | `226` | Grille $2 \times 2$ `review-briefing-grid` (`UX-DR4`) avec encadrement ambre sur Bloc 4. |
| `packages/ui/src/primitives/ChunkValidationCard.tsx` | Créé | `365` | Cartes `chunk-validation-card` (`UX-DR5`), navigation `Alt + ↑/↓` et modale `< 15 s` (`UX-DR10`). |
| `packages/ui/src/__tests__/human-gates.test.tsx` | Créé | `141` | Tests Vitest sur l'encadrement ambre du Bloc 4, la navigation clavier et la modale `< 15 s`. |
| `tests/unit/test_story_4_3_adaptive_human_gates.py` | Créé | `257` | Tests unitaires, contrat API et vérification de la révision Alembic `0018`. |

### 3.2 Métriques & Couverture de Tests (`AD-17`)
- **Tests unitaires Python (`pytest`)** : `100 passed` en `38.27 s`, couverture globale **`91.37 %`** (`>= 90 %` requis).
- **Qualité statique & Frontières (`AD-19`)** :
  - `ruff check .` & `ruff format --check .` : `0` erreur.
  - `mypy --strict` : `0` erreur (`154` fichiers).
  - `lint-imports` : **`5 contracts kept, 0 broken`**.
- **Tests TypeScript & SDK OpenAPI 3.1 (`0-diff`)** : `pnpm turbo run lint typecheck test` (`9/9` tâches vertes, `18` tests `@orcia/ui` + `9` tests `@orcia/web`).
