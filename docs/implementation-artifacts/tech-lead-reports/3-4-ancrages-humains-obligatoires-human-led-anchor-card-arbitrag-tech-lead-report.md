# Rapport d'Implémentation Tech Lead — Story 3.4 : Ancrages Humains Obligatoires (`human-led-anchor-card`), Arbitrage Humain Systématique (`arbitration-tiebreak-card`) & Politique de Départage (`tie_break_policy`)

- **Clé de Story** : `3-4-ancrages-humains-obligatoires-human-led-anchor-card-arbitrag`
- **Epic** : `Epic 3` — Orchestration Durable, *Blackboard* Immuable, Agent Assistant & Co-Exécution Humain-IA
- **Date** : `2026-10-28`
- **Auteur** : Tech Lead / Dev Senior (`Amelia` & `Winston`)
- **Statut** : `done`
- **Références Architecture & UX** : `FR-4`, `FR-5`, `FR-29`, `AD-3`, `AD-15`, `AD-18`, `AD-19`, `UX-DR3`, `UX-DR6`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique
Dans un système d'ingénierie assistée par IA, deux dérives majeures menacent la souveraineté cognitive de l'équipe :
1. **La délégation aveugle du cadrage critique (*Rubber-Stamping*)** : l'humain laisse l'IA rédiger l'intention d'architecture ou les hypothèses structurantes d'une étape marquée `human_authored_required: true`.
2. **Le choix silencieux par l'agent face à deux options équivalentes** : lorsqu'un Agent Exécuteur identifie $\ge 2$ options d'architecture ou de règles métier ayant chacune des compromis légitimes, un choix implicite enfoui dans un artefact long masque une décision structurante.

La `Story 3.4` répond à ces deux risques par :
- Le verrouillage cryptographique (`SHA-256`) et fonctionnel (`>= 30` caractères rédigés par `author_type="HUMAN"`, rejet strict `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED` de toute écriture agentique et refus socratique Layer 1 de l'Agent Assistant) des sections d'Ancrage Humain Obligatoire (`HumanLedAnchorCard`, `UX-DR3`, Violet exclusif `#6D28D9`).
- L'outil `request_human_arbitration(options_matrix)` évaluant `tie_break_policy` (`PAUSE_AND_ESCALATE` avec publication transactionnelle `HumanArbitrationRequested` dans `domain_events_outbox` et attente durable `DBOS.recv`, `ONTOLOGY_AXIOM_FIRST` par départage ontologique L1/L2, ou `DEFER_AND_CONTINUE_WITH_ASSUMPTION` réservé aux sous-workflows non-critiques avec marqueur `[ASSUMPTION]` dans `step_memlog_jsonb`), couplé au composant `ArbitrationTieBreakCard` (`UX-DR6`, Ambre `#D97706`).

### 1.2 Analyse d'Impact GitNexus (Pré-Codage)
- **`gitnexus_query({query: "HumanLedAnchorCard arbitration tie_break_policy HumanArbitrationRequested", repo: "ORCIA"})`** :
  - Identification de `HumanLedAnchorCard.tsx` (`packages/ui/src/primitives/HumanLedAnchorCard.tsx`), `TieBreakPolicy` (`packages/orcia-kernel/src/orcia_kernel/enums.py`), `HumanArbitrationRequestedEvent` (`packages/orcia-kernel/src/orcia_kernel/events.py`), `HumanAnchorRequiredError` / `InvalidTieBreakPolicyError` (`packages/orcia-core/src/orcia_core/orchestration/errors.py`), et `DurableOrchestrationEngine` (`packages/orcia-core/src/orcia_core/orchestration/engine.py`).
- **`gitnexus_impact({target: "DurableOrchestrationEngine", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `HIGH` (`13` appelants directs à `d=1`, incluant `apps/api/src/orcia_api/dependencies.py`, `apps/api/src/orcia_api/routers/blackboard_and_engine.py`, `packages/orcia-core/src/orcia_core/assistant/service.py`).
  - Décision d'architecture : extraire la logique métier d'ancrage humain et d'arbitrage dans un module dédié `packages/orcia-core/src/orcia_core/orchestration/human_anchors_and_arbitration.py` (`272` lignes $< 300$ lignes) composé dans `DurableOrchestrationEngine` sans casser la signature existante de `execute_step` (`require_human_anchor: bool = False` optionnel rétrocompatible).

### 1.3 Exploration & Chiffres Clés
- **Volumétrie des fichiers** :
  - `packages/orcia-core/src/orcia_core/orchestration/human_anchors_and_arbitration.py` : `272` lignes (sous le seuil de `300` lignes).
  - `packages/ui/src/primitives/ArbitrationTieBreakCard.tsx` : `241` lignes (sous le seuil de `300` lignes).
  - `packages/ui/src/primitives/HumanLedAnchorCard.tsx` : `172` lignes.
- **Isolation CSS Design System** :
  - Le test `packages/ui/src/__tests__/ui-isolation.test.ts` garantit que `--color-human-led-violet` (`#6D28D9`) n'apparaît que dans `HumanLedAnchorCard.tsx` et `tokens.css`, tandis que `ArbitrationTieBreakCard.tsx` utilise exclusivement `--color-arbitration-amber` (`#D97706`) et `--color-arbitration-bg`.

### 1.4 Opportunités de Factorisation (`DRY`) & Dette Technique
- Réutilisation directe de `HumanArbitrationRequestedEvent` (`orcia_kernel.events`) et `OutboxEventBus` (`orcia_core.events.outbox`) livrés en `Story 3.2c`.
- Réutilisation du mécanisme `pause_step_for_human` / `resume_human_task` (`StepMemlogEntry` `DECISION` / `ASSUMPTION` et checkpoint immuable `BlackboardSnapshotEntity`) de `DurableOrchestrationEngine`.
- Aucune dette technique résiduelle créée par cette story.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Création de `infra/migrations/versions/0015_story_3_4_human_anchors_and_arbitration.py` (`revision = "0015_story_3_4"`, `down_revision = "0014_story_3_2e"`) :
  - Table `human_anchor_signatures` (`id UUID PRIMARY KEY`, `run_id`, `workspace_id`, `step_key`, `section_key`, `author_user_id`, `author_type CHECK ('HUMAN')`, `signature_text`, `content_text CHECK (char_length(btrim(content_text)) >= 30)`, `content_sha256`, `char_length CHECK (>= 30)`, `signed_at`).
  - Table `human_arbitration_requests` (`id UUID PRIMARY KEY`, `run_id`, `workspace_id`, `step_key`, `question_title`, `context_summary`, `tie_break_policy`, `status`, `options_matrix_jsonb`, `selected_option_key`, `custom_option_text`, `resolved_by_user_id`, `resolved_by_axiom_key`, `assumption_note`, `created_at`, `resolved_at`).

### 2.2 Noyau Hexagonal, Algorithmes & Workers (`packages/orcia-core/`)
- Création de [`human_anchors_and_arbitration.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/human_anchors_and_arbitration.py) :
  - `validate_human_anchor_submission` : rejette `author_type != "HUMAN"` ou `len(content_text.strip()) < 30` ou signature vide avec `HumanAnchorRequiredError` (`ERR_HUMAN_ANCHOR_REQUIRED`).
  - `HumanAnchorAndArbitrationService.sign_human_anchor` & `enforce_step_anchor_if_required` : persiste la signature SHA-256, consigne un marqueur `[DECISION]` dans `step_memlog_jsonb`, et déverrouille l'exécution de l'étape.
  - `HumanAnchorAndArbitrationService.request_human_arbitration` : supporte les 3 politiques `PAUSE_AND_ESCALATE` (pause du step en `WAITING_HUMAN_ARBITRATION` + émission de `HumanArbitrationRequestedEvent` dans `domain_events_outbox`), `ONTOLOGY_AXIOM_FIRST` (évaluation des axiomes L1/L2 et résolution automatique `RESOLVED_BY_AXIOM` si 1 seule option survit, sinon escalade humaine), et `DEFER_AND_CONTINUE_WITH_ASSUMPTION` (rejeté sur le chemin critique avec `InvalidTieBreakPolicyError` `ERR_INVALID_TIE_BREAK_POLICY`, autorisé sur sous-workflow non-critique avec marqueur `[ASSUMPTION]`).
  - `HumanAnchorAndArbitrationService.resolve_human_arbitration` : enregistre le choix `Option A` / `Option B` ou `Option C` personnalisée (`CUSTOM_OPTION_C`), reprend immédiatement l'étape via `engine.resume_human_task` et crée un checkpoint immuable `BlackboardSnapshotEntity`.

### 2.3 Couche Backend FastAPI & Contrats OpenAPI (`apps/api/`, `packages/api-client/`)
- Ajout des schémas Pydantic v2 dans [`blackboard.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/schemas/blackboard.py) : `HumanAnchorSignRequest`, `HumanAnchorSignatureSchema`, `HumanAnchorSignResponse`, `ArbitrationOptionSchema`, `ArbitrationRequestCreatePayload`, `ArbitrationResolvePayload`, `HumanArbitrationSchema`, `HumanArbitrationActionResponse`.
- Ajout des routes dans [`blackboard_and_engine.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/blackboard_and_engine.py) :
  - `POST /api/v1/orchestration/runs/anchors/sign`
  - `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/arbitration`
  - `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/arbitration/resolve`
- Régénération du SDK OpenAPI 3.1 (`openapi.json` et `packages/api-client/src/generated/`).

### 2.4 Design System (`@orcia/ui`), `i18n` (`fr`/`en`) & Interface SPA (`apps/web/`)
- Enrichissement de [`HumanLedAnchorCard.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/HumanLedAnchorCard.tsx) : compteur de caractères temps réel (`>= 30`), verrouillage du bouton de soumission tant que le seuil ou la signature n'est pas atteint, attributs d'audit `data-ai-generation-forbidden="true"` et `data-anchor-locked`.
- Création de [`ArbitrationTieBreakCard.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/ArbitrationTieBreakCard.tsx) : carte Ambre `--color-arbitration-amber` (`#D97706`) affichant la matrice comparative (Avantages, Inconvénients, Impact SI, Impact FinOps) côte-à-côte, sélection 1-clic (`Option A` / `Option B`) et formulaire `Option C` personnalisée.
- Parité `i18n` complète `fr`/`en` (`apps/web/src/i18n/types.ts`, `fr.ts`, `en.ts`) et intégration dans [`apps/web/src/features/cockpit/index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/cockpit/index.tsx).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés et Modifiés

| Fichier | Action | Lignes | Rôle |
| :--- | :--- | :---: | :--- |
| `infra/migrations/versions/0015_story_3_4_human_anchors_and_arbitration.py` | Créé | `124` | Migration Alembic `0015_story_3_4` (`human_anchor_signatures`, `human_arbitration_requests`) |
| `packages/orcia-core/src/orcia_core/orchestration/human_anchors_and_arbitration.py` | Créé | `272` | Service d'ancrage humain obligatoire (`SHA-256`, `>= 30` car.) et d'arbitrage (`tie_break_policy`) |
| `packages/orcia-core/src/orcia_core/orchestration/engine.py` | Modifié | `348` | Câblage de `HumanAnchorAndArbitrationService` et garde `enforce_step_anchor_if_required` |
| `apps/api/src/orcia_api/schemas/blackboard.py` | Modifié | `258` | Schémas OpenAPI 3.1 pour signatures d'ancrage et demandes/résolutions d'arbitrage |
| `apps/api/src/orcia_api/routers/blackboard_and_engine.py` | Modifié | `308` | Endpoints `/runs/anchors/sign`, `/arbitration` et `/arbitration/resolve` |
| `packages/ui/src/primitives/HumanLedAnchorCard.tsx` | Modifié | `172` | Verrouillage `< 30` car., `data-ai-generation-forbidden="true"`, Violet `#6D28D9` exclusif |
| `packages/ui/src/primitives/ArbitrationTieBreakCard.tsx` | Créé | `241` | Carte d'arbitrage côte-à-côte (`Option A/B` 1-clic + `Option C` libre, Ambre `#D97706`) |
| `packages/ui/src/__tests__/arbitration-and-anchor.test.tsx` | Créé | `135` | Tests unitaires Vitest/RTL pour `HumanLedAnchorCard` et `ArbitrationTieBreakCard` |
| `tests/unit/test_story_3_4_human_anchors_and_arbitration.py` | Créé | `364` | Tests PostgreSQL 18 (`testcontainers`) + API bout-en-bout (`FR-4`, `FR-5`, `FR-29`, `AD-3`) |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Qualité
- **L1 (Analyse statique & frontières)** :
  - `.venv/bin/ruff check .` : `0` erreur.
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `0` erreur (`133` fichiers sources).
  - `.venv/bin/lint-imports` : `4 kept, 0 broken`.
  - `pnpm turbo run lint typecheck test` : `9/9` tâches réussies (`@orcia/ui` `6/6` fichiers de tests dont `ui-isolation.test.ts` et `arbitration-and-anchor.test.tsx`, `@orcia/web` `9/9` tests, `@orcia/api-client` `7/7` tests).
- **L2 & L3 (Tests Unitaires, Intégration PostgreSQL 18 `testcontainers` & Contrats OpenAPI)** :
  - `.venv/bin/pytest tests/unit/test_story_3_4_human_anchors_and_arbitration.py -q` : `4 passed` (incluant migration `0015_story_3_4` upgrade/downgrade/upgrade sur `pgvector/pgvector:pg18`).
  - Couverture globale `orcia-kernel` + `orcia-core` $\ge 90\%$.
- **GitNexus (`gitnexus_detect_changes`)** :
  - Index rafraîchi (`7,417 nodes | 12,875 edges | 142 clusters | 552 flows`), `13` fichiers modifiés, `4` fichiers ajoutés, `0` cycle inter-domaine.
