# Rapport d'Implémentation Tech Lead — Story 3.5 : Challenge Amont Inter-Steps avec Simulation d'Impact (*What-If*) & Replay Ciblé à partir du Step $N$ (incluant Replay Intra-Sous-Workflow)

- **Clé de Story** : `3-5-challenge-amont-inter-steps-avec-simulation-d-impact-what-if`
- **Epic** : `Epic 3` — Orchestration Durable, *Blackboard* Immuable, Agent Assistant & Co-Exécution Humain-IA
- **Date** : `2026-10-28`
- **Auteur** : Tech Lead / Dev Senior (`Amelia` & `Winston`)
- **Statut** : `done`
- **Références Architecture & UX** : `FR-7`, `FR-16`, `FR-30`, `AD-2`, `AD-7`, `AD-18`, `AD-19`, `UX-DR7`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique
Lorsqu'un Architecte (`Antoine` au Step 2) ou un Tech Lead (`Yanis` au Step 3) détecte une incohérence dans un artefact amont validé (ex. règle métier du `PRD` au Step 1 incompatible avec l'API partenaire ou portant une alerte `[STALE_WARNING]`), deux écueils doivent être évités :
1. Modifier localement l'artefact aval en créant une divergence silencieuse vis-à-vis du `PRD` amont.
2. Relancer l'intégralité du Workflow Run depuis l'étape 1 en gaspillant les tokens et les validations humaines des étapes amont non impactées.

La `Story 3.5` résout ces deux problèmes :
- **Challenge Amont avec Simulation d'Impact *What-If* (`FR-7`, `AD-7`, `UX-DR7`)** : traverse le graphe des dépendances `input_uris` (`orcia://runs/{run_id}/steps/{step_key}/artifacts/main` / `steps.{step_key}.output.*`) et `ontology_relations` pour lister exactement les *Steps* aval, sections d'artefacts et axiomes d'ontologie invalidés, traduit le challenge technique dans le vocabulaire du profil amont (`PM_BUSINESS` via `ProfileSemanticTranslator`), et publie une notification transactionnelle dans `domain_events_outbox`.
- **Replay Ciblé à partir du Step $N$ & Replay Intra-Sous-Workflow (`FR-16`, `FR-30`, `AD-2`, `AD-18`)** : bifurque l'arbre immuable `blackboard_snapshots` à partir du snapshot validé de l'étape $N-1$ (`0` ré-exécution et `0` token consommé sur $1..N-1$), marque les anciens snapshots $\ge N$ comme `SUPERSEDED`, crée une nouvelle branche `ACTIVE` en conservant le `run-lock.json` (`SHA-256`), et supporte le Replay ciblé d'une étape $k$ à l'intérieur d'un sous-workflow enfant (`SUB_WORKFLOW`) sans recalculer les étapes amont du parent ni les étapes $1..k-1$ de l'enfant.

### 1.2 Analyse d'Impact GitNexus (Pré-Codage)
- **`gitnexus_context({name: "ImpactSimulatorService", repo: "ORCIA"})` & `gitnexus_impact({target: "ImpactSimulatorService", direction: "upstream", repo: "ORCIA"})`** :
  - Risque `LOW` (`1` import direct dans `ontology/__init__.py`, `6` dépendants transitifs).
- **`gitnexus_context({name: "ProfileSemanticTranslator", repo: "ORCIA"})`** :
  - Utilisé dans `ontology/resolver.py` et `ontology/impact_and_promotion.py` pour traduire un concept technique selon les 6 archétypes de Profil Humain.
- **Contrôle de volumétrie & Étape 0 (Pre-Story Refactoring)** :
  - Création d'un module dédié `packages/orcia-core/src/orcia_core/orchestration/challenge_and_replay.py` (`289` lignes) et d'un routeur dédié `apps/api/src/orcia_api/routers/challenge_and_replay.py` (`144` lignes) afin de respecter strictement le seuil de `< 400` lignes par fichier.

### 1.3 Exploration & Chiffres Clés
- **Invariants Append-Only (`AD-2`, `NFR-SEC-3`)** :
  - Aucune ligne existante de `blackboard_snapshots` ne peut être modifiée ni supprimée (protégée par le trigger PostgreSQL `trg_blackboard_snapshots_append_only` et vérifiée par tests `hypothesis` + `testcontainers` PG18).

### 1.4 Opportunités de Factorisation (`DRY`) & Dette Technique
- Réutilisation de `ProfileSemanticTranslator` (`orcia_core.ontology`) pour la traduction inter-profils (`PM_BUSINESS`, `ARCHITECT`, `TECH_LEAD`, `DEVELOPER`, `SECOPS`, `EXECUTIVE`).
- Réutilisation de `HumanArbitrationRequestedEvent` (`orcia_kernel.events`) pour la notification asynchrone Outbox du propriétaire de l'artefact amont.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Création de [`0016_story_3_5_upstream_challenges.py`](file:///home/romain/Documents/Projects/ORCIA/infra/migrations/versions/0016_story_3_5_upstream_challenges.py) (`revision = "0016_story_3_5"`, `down_revision = "0015_story_3_4"`) créant la table `upstream_challenges` avec contraintes `CHECK` et index `ix_upstream_challenges_run_target`.

### 2.2 Noyau Hexagonal, Algorithmes & Workers (`packages/orcia-core/`)
- Création de [`challenge_and_replay.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/challenge_and_replay.py) :
  - `UpstreamChallengeImpactPreview`, `UpstreamChallengeEntity`, `StepReplayResult`.
  - `UpstreamChallengeAndReplayService.preview_upstream_challenge` : traversée DAG des `input_uris` et des relations ontologiques, calcul des steps/sections/axiomes invalidés et des steps amont préservés, traduction sémantique pour le profil amont (`PM_BUSINESS`, `ARCHITECT`, `TECH_LEAD`, `DEVELOPER`, `SECOPS`, `EXECUTIVE`).
  - `UpstreamChallengeAndReplayService.submit_upstream_challenge` : enregistre le challenge, met optionnellement à jour le brouillon amont (`v1.1`), et publie l'événement de notification dans `domain_events_outbox`.
  - `UpstreamChallengeAndReplayService.replay_from_step` : supporte le Replay à partir du Step $N$ ainsi que le Replay intra-sous-workflow (`sub_workflow_step_key`), marque les snapshots $\ge N$ comme `SUPERSEDED` (append-only), réutilise les snapshots $1..N-1$ (`0` ré-exécution, `0` token consommé) et vérifie l'intégrité `SHA-256` de `run-lock.json`.

### 2.3 Couche Backend FastAPI & Contrats OpenAPI (`apps/api/`, `packages/api-client/`)
- Ajout des schémas dans [`apps/api/src/orcia_api/schemas/challenge_and_replay.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/schemas/challenge_and_replay.py) et des routes dans [`apps/api/src/orcia_api/routers/challenge_and_replay.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/challenge_and_replay.py) :
  - `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/challenge/preview`
  - `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/challenge`
  - `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/replay` (et alias `/api/v1/runs/{run_id}/steps/{step_key}/replay`).
- Régénération du SDK OpenAPI 3.1 (`0-diff`).

### 2.4 Design System (`@orcia/ui`), `i18n` (`fr`/`en`) & Interface SPA (`apps/web/`)
- Création de [`UpstreamChallengeRewindModal.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/UpstreamChallengeRewindModal.tsx) (`UX-DR7`) : modale avec aperçu d'impact *What-If* (steps invalidés, sections d'artefacts, axiomes d'ontologie, steps amont préservés à `0` token), traduction pour le profil amont, soumission du challenge et déclenchement du *Replay Step N*.
- Parité `i18n` `fr`/`en` et intégration dans [`apps/web/src/features/cockpit/index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/cockpit/index.tsx).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés / Modifiés

| Fichier | Action | Lignes | Rôle |
| :--- | :--- | :---: | :--- |
| `infra/migrations/versions/0016_story_3_5_upstream_challenges.py` | Créé | `88` | Migration Alembic `0016_story_3_5` (`upstream_challenges` + index). |
| `packages/orcia-core/src/orcia_core/orchestration/challenge_and_replay.py` | Créé | `289` | `UpstreamChallengeAndReplayService` (What-If preview, challenge amont, Replay Step $N$ & intra-sous-workflow). |
| `packages/orcia-core/src/orcia_core/blackboard/store.py` | Modifié | `164` | Support du statut effectif `SUPERSEDED` (append-only sans muter les snapshots existants) et ré-exécution de branche sur Replay. |
| `apps/api/src/orcia_api/schemas/challenge_and_replay.py` | Créé | `95` | Schémas HTTP/OpenAPI 3.1 de challenge amont et de replay ciblé. |
| `apps/api/src/orcia_api/routers/challenge_and_replay.py` | Créé | `144` | Endpoints REST `/challenge/preview`, `/challenge` et `/replay` avec `RunAccessGuard`. |
| `packages/ui/src/primitives/UpstreamChallengeRewindModal.tsx` | Créé | `222` | Composant Design System `@orcia/ui` `UX-DR7` (`role="dialog"`, `aria-modal="true"`, fermeture `Escape`). |
| `packages/ui/src/__tests__/upstream-challenge-modal.test.tsx` | Créé | `61` | Tests Vitest / Testing Library de `UpstreamChallengeRewindModal`. |
| `tests/unit/test_story_3_5_challenge_and_replay.py` | Créé | `289` | Suite de tests Story 3.5 (migration PG18 `0016`, What-If, Replay Step $N$ & intra-sous-workflow, `hypothesis` append-only). |

### 3.2 Métriques, Couverture & Validation des 5 Couches (`AD-17`)
- **Couverture unitaire Python (`packages/orcia-kernel` + `packages/orcia-core`)** : **`91.91 %`** (`>= 90 %` requis).
- **Couche 1 (Statique & Contrats)** :
  - `ruff check .` & `ruff format --check .` : `0` erreur.
  - `mypy --strict` : `Success: no issues found in 136 source files`.
  - `lint-imports` : `4 kept, 0 broken`.
  - `pnpm turbo run lint typecheck test` : `9/9 successful`.
  - `lint_spine.py` : `0 findings`.
- **Couche 2 (Unitaires & Property-Based `hypothesis`)** : `5 passed` dans `test_story_3_5_challenge_and_replay.py` (incluant la preuve `hypothesis` d'immuabilité des snapshots `1..N-1` et de `0` token consommé en amont).
- **Couche 3 (Intégration Conteneurs Réels)** : Migration Alembic `0001 -> 0016 -> 0015 -> 0016` validée sur conteneur réel `pgvector/pgvector:pg18`.
- **Couche 4 (Composants `@orcia/ui` & `apps/web`)** : `7/7` fichiers Vitest verts dans `@orcia/ui` et `9/9` dans `@orcia/web`.
- **Analyse GitNexus post-implémentation** : index rafraîchi et `gitnexus_detect_changes()` exécuté avant commit.
