# Story 22.1 — Socle Identité UUIDv7 Workspaces, Permissions `PLATFORM_ADMIN` & Fin du Mode Dégradé `marc` / Bypass PG

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-1-socle-identite-uuid-workspaces-permissions-admin-et-fin-bypass-pg` (`Epic 22` — Vague 0)
- **Capacité(s)** : `CAP-011`, `CAP-022`, `CAP-050`, `CAP-067`, `CAP-072`, `CAP-076`, `CAP-080`, `CAP-180` (ancrages principaux `failed_e2e`) ; impact transverse sur `CAP-001`, `CAP-004`, `CAP-020`, `CAP-021`, `CAP-023`, `CAP-030`..`CAP-033`, `CAP-061`, `CAP-081` — classification : `feature`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-01`**, **`REM-02`** et **`REM-07`** (`synthese-remediation-sally-winston-epic-21.md`). Couvre `FR-3`, `FR-14`, `FR-21`, `FR-23`, `FR-28`, `FR-33`, `FR-34`, `AD-1`, `AD-6`, `AD-19`, `AD-21`, `UJ-1`, `UJ-5`, `UJ-6`, `UJ-9`, `UJ-10`, `UJ-13`, `UJ-14`, `UJ-17`, `UJ-18`.
- **Commits associés** : `En attente d'implémentation (initialisé sur 575cf4a)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Schisme identitaire `"ws-1"` vs `UUIDv7` & perte de `slug` (`REM-01`, `7` échecs directs en cascade)** :
  - Dans `apps/web/src/components/platformSetupStore.tsx:839-888`, `createWorkspace` génère côté navigateur un identifiant synthétique `"ws-${workspaces.length + 1}"` (`"ws-1"`) et construit l'item d'état local **sans transmettre `slug: input.slug`**.
  - Côté serveur, `sql_platform_setup_relational_sync.py:259-260` recalcule le slug à partir du nom (`'Espace E2E Comptabilité'` $\rightarrow$ `'espace-e2e-comptabilit'` au lieu de `'espace-e2e-compta'`), tandis que la synchro UI avale les rejets avec `.catch(() => undefined)`.
  - Ensuite, `WorkspaceSourcesRagTab.tsx:42,161` et `features/workspaces/index.tsx:321-356` envoient `"ws-1"` vers `/api/v1/workspaces/ws-1/datasources` et `/api/v1/workspaces/ws-1/dna/*`, qui exigent un `UUID` strict (`ResourceNotFoundError` **HTTP 404** sur `POST` et **HTTP 422** sur `dna_and_glossary.py:65`, et `GET` retourne silencieusement `[]`).
- **Faux rejets `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` d'un `PLATFORM_ADMIN` (`REM-02`, `4` échecs)** :
  - Lors de la création d'une BU/Équipe/Espace après l'initialisation Jour 0, `_bootstrap_evaluator_sync.py:95-125` n'enregistre de `WorkspaceMembershipEntity` explicite que sur `"ws-1"` et `sync_evaluator_topology_from_pg` (`_finops_scope_guards.py:114-129`) insère l'entité `WorkspaceEntity(id=ws.pgWorkspaceId)` sans membership.
  - Dans `MatrixPermissionEvaluator.resolve_workspace_access` (`evaluator.py:184-211`), tout `PLATFORM_ADMIN` sans membership direct reçoit `role="OBSERVER"`, `access_mode="READ_ONLY_OBSERVER"`, `access_origin="GLOBAL_ADMIN"`. Les routeurs `gates.py:118` et `executions_trace.py:97-100` appliquent cette résolution et rejettent les actions d'un `PLATFORM_ADMIN` en **`HTTP 403`** !
- **Résidus `AUTH-01` / identité `"marc"` / drapeau `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` (`REM-07`)** :
  - `CockpitHumanLedGovernanceSection.tsx:54,112,157,177,208,243` et `features/cockpit/index.tsx:155` transmettent encore le persona `"marc"` en dur au lieu de l'identité JWT issue de `useAuthSessionStore`.
  - `get_accostage_service` (`dependencies/portal_and_assistant.py:59-70`) code `orcia_env="local"` et `expected_bootstrap_token="orcia-day0-bootstrap-token"` en dur au lieu de lire la configuration applicative injectée.
  - `_auth_session_routes.py:46-47`, `enterprise_connectors.py:86-87` et `autonomy_contracts.py:261` exposent encore `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`, permettant une dégradation silencieuse vers la RAM.
- **Échecs E2E associés & captures PNG archivées (`7` échecs E2E directs)** :
  - `07-spaces-org-and-workspace-persistence.spec.ts` (`desktop-cockpit`, fail) : `workspaces` = `0` ligne pour `slug = 'espace-e2e-compta'` — [PNG](../e2e-campaign-epic-21/screenshots/07-spaces-org-and-workspace-persistence/desktop-cockpit--bu-equipe-espace-crees-par-l-ui-sont-persistes-cote-api-et-survivent-a-un-f5--failed.png)
  - `17-workspace-sources-codegraph-dna-and-ontology.spec.ts` #1 (`desktop-cockpit` & `mobile-companion`, 2 fails) : `workspace_datasources` = `0` ligne (`404` sur `"ws-1"`) — [Desktop PNG](../e2e-campaign-epic-21/screenshots/17-workspace-sources-codegraph-dna-and-ontology/desktop-cockpit--rattachement-source-code-fraicheur-sha-256-webhook-outils-codegraph-lecture-seule-et-sur--failed.png) · [Mobile PNG](../e2e-campaign-epic-21/screenshots/17-workspace-sources-codegraph-dna-and-ontology/mobile-companion--rattachement-source-code-fraicheur-sha-256-webhook-outils-codegraph-lecture-seule-et-sur--failed.png)
  - `19-orchestration-whatif-replay-and-gates.spec.ts` #2 (`desktop-cockpit` & `mobile-companion`, 2 fails) : `POST /api/v1/gates/deterministic/evaluate` -> `403` — [Desktop PNG](../e2e-campaign-epic-21/screenshots/19-orchestration-whatif-replay-and-gates/desktop-cockpit--validation-deterministe-sandbox-validation-agentique-orthogonale-revue-humaine-par-decou--failed.png) · [Mobile PNG](../e2e-campaign-epic-21/screenshots/19-orchestration-whatif-replay-and-gates/mobile-companion--validation-deterministe-sandbox-validation-agentique-orthogonale-revue-humaine-par-decou--failed.png)
  - `21-assistant-citations-v5-audit-help-showcase.spec.ts` #1 (`desktop-cockpit` & `mobile-companion`, 2 fails) : `POST /api/v1/executions/reflexive` -> `403` — [Desktop PNG](../e2e-campaign-epic-21/screenshots/21-assistant-citations-v5-audit-help-showcase/desktop-cockpit--creation-de-dossier-reponse-avec-citations-verifiees-verrouillage-d-ecriture-directe-et---failed.png) · [Mobile PNG](../e2e-campaign-epic-21/screenshots/21-assistant-citations-v5-audit-help-showcase/mobile-companion--creation-de-dossier-reponse-avec-citations-verifiees-verrouillage-d-ecriture-directe-et---failed.png)

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `MatrixPermissionEvaluator` (`packages/orcia-core/src/orcia_core/permissions/evaluator.py:51-361`) : **`impactedCount: 18`**, risque **`MEDIUM`** (`direct: 9` — `catalog/{__init__,service}.py`, `orchestration/{control_center,run_lock_service,seeds}.py`, `permissions/{__init__,_default_service,broker,service}.py` ; `d=2: 5`, `d=3: 4`).
  - `resolve_workspace_access` (`packages/orcia-core/src/orcia_core/permissions/evaluator.py`) : **`impactedCount: 287`**, risque **`CRITICAL`** (`direct: 122`, `d=2: 124`, `d=3: 41`, `processes_affected: 33`, `modules_affected: 18` dont `Orchestration`, `Routers`, `Permissions`, `Bootstrap`, `Gates`).
  - `createWorkspace` (`apps/web/src/components/platformSetupStore.tsx:839-888`) : **`impactedCount: 358`**, risque **`CRITICAL`** (`direct: 182`, `d=2: 135`, `d=3: 41`, `processes_affected: 51`, `modules_affected: 20`).
- **Tables PostgreSQL 18 concernées** : `workspaces`, `org_units`, `workspace_memberships`, `workspace_datasources`, `gate_evaluations`, `reflexive_execution_sessions`, `users`.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Supprimer la double logique `"ws-N"` vs `UUIDv5` (`resolve_workspace_uuid_or_setup_key` / contournements `ws-\d+`) au profit d'un unique identifiant `UUIDv7` attribué par l'API à la création d'un Workspace.
  - Unifier la vérification d'accès `PLATFORM_ADMIN` sur les espaces `STANDARD` vs `CONFIDENTIAL_RESTRICTED` au sein de `MatrixPermissionEvaluator.resolve_workspace_access` (plutôt que des contournements dispersés dans `_finops_auth_guards.py` vs `gates.py`).
  - Scinder `platformSetupStore.tsx` si son volume dépasse `400` lignes après suppression de la plomberie `"ws-N"`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Les tables `workspaces`, `org_units`, `workspace_memberships` et `workspace_datasources` existent déjà dans les migrations `0002`..`20261114_1801`.
- Aucune migration destructive requise ; vérifier l'unicité et l'indexation de `workspaces.slug` et l'absence de contrainte bloquante lorsque `POST /api/v1/workspaces` insère un `UUIDv7` + `slug` exact fourni par l'utilisateur (migration additive uniquement si une contrainte d'unicité par `org_unit_id, slug` manquait).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/permissions/evaluator.py` (`MatrixPermissionEvaluator.resolve_workspace_access`) :
  - Un `PLATFORM_ADMIN` agissant sur un espace `STANDARD` (sans header explicite `X-Orcia-Access-Mode: READ_ONLY_OBSERVER`) conserve un accès contributeur/admin gouverné ; il ne bascule en `READ_ONLY_OBSERVER` que sur un espace `CONFIDENTIAL_RESTRICTED` sans délégation ou sur demande explicite du mode observateur.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py` & `_bootstrap_evaluator_sync.py` :
  - Préserver exactement `ws.slug` (si non vide et validé `^[a-z0-9-]+$`) sans le ré-écraser par une translittération tronquée du nom.
  - Enregistrer un `WorkspaceMembershipEntity` propriétaire pour le créateur/admin sur l'UUID réel PG18 dès la création de l'espace.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/` (`org_and_workspaces.py` / `workspace_datasources.py` / `dna_and_glossary.py` / `gates.py` / `executions_trace.py`) :
  - Faire retourner immédiatement par `POST /api/v1/workspaces` l'entité complète avec son `id` (`UUIDv7`) et son `slug` exact persistés en PG18.
  - Supprimer tout contournement `ws-\d+` dans les routeurs et exiger un `UUID` valide (retournant un RFC 9457 explicite en `404`/`422`).
- `apps/api/src/orcia_api/dependencies/portal_and_assistant.py` :
  - Dans `get_accostage_service`, injecter `orcia_env` et `bootstrap_token` depuis les settings centralisés (`ORCIA_ENV` / `ORCIA_BOOTSTRAP_TOKEN`) avec refus strict d'un secret par défaut hors `local`.
- Purger intégralement `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` de `_auth_session_routes.py`, `enterprise_connectors.py` et `autonomy_contracts.py` (fail-fast `HTTP 503` si le moteur PG18 n'est pas initialisé au Composition Root).
- Régénérer `@orcia/api-client` (`0-diff`) si le contrat de réponse de création d'espace évolue.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `apps/web/src/components/platformSetupStore.tsx` :
  - Supprimer la génération `"ws-${workspaces.length + 1}"` dans `createWorkspace` (`L846`) ; attendre la réponse synchrone de `POST /api/v1/workspaces`, propager `slug: input.slug` et stocker l'UUIDv7 serveur retourné partout (`WorkspaceSourcesRagTab.tsx`, sélecteur de contexte, navigation `/workspaces/$wsId/sources`).
  - Supprimer les `.catch(() => undefined)` sur création/mise à jour d'espace et remonter toute erreur RFC 9457 à l'UI.
- `apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx` & `apps/web/src/features/cockpit/index.tsx` :
  - Remplacer toutes les occurrences codées en dur de `"marc"` (`L54,112,157,177,208,243` et `L155`) par l'utilisateur authentifié courant issu de `useAuthSessionStore` (zéro fallback persona hors tests unitaires).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Python) & Couche 1b (TS/Vitest)** : tests unitaires sur `MatrixPermissionEvaluator` (`PLATFORM_ADMIN` sur `STANDARD` vs `CONFIDENTIAL_RESTRICTED` vs header `READ_ONLY_OBSERVER`), conservation exacte de `slug`, suppression de `"ws-1"` et `"marc"` dans `platformSetupStore` et `cockpit`.
- **Couche 2 (`HTTP FastAPI ➔ PG18`)** : `POST /api/v1/workspaces` $\rightarrow$ `SELECT id, slug FROM workspaces` + `workspace_memberships` ; `POST /api/v1/workspaces/{uuid}/datasources` ; `POST /api/v1/gates/deterministic/evaluate` & `POST /api/v1/executions/reflexive` sous `PLATFORM_ADMIN` sans faux `403`.
- **Couche 3 (`OpenAPI 3.1 0-diff`, `Schemathesis`, `lint-imports`)** : validation `0-diff` SDK et `5 contracts kept, 0 broken`.
- **Couche Sécurité / Red-Team (`tests/security/`)** : vérifier que `READ_ONLY_OBSERVER` (header explicite ou observateur réel) reste bloqué en `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`, qu'aucun `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` ne contourne PG18 et que `CONFIDENTIAL_RESTRICTED` sans délégation reste isolé.
- **Couche 5 (Playwright E2E)** : passage au vert visé pour `07-spaces-org-and-workspace-persistence.spec.ts`, `17-workspace` #1, `19-orchestration` #2 et `21-assistant` #1 (avec `F5` et `SELECT` PG18).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[En attente d'implémentation de la Story 22.1]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/permissions/evaluator.py` | Modification | *[À compléter après implémentation]* |
| `apps/api/src/orcia_api/...` | Modification | *[À compléter après implémentation]* |
| `apps/web/src/components/platformSetupStore.tsx` | Modification | *[À compléter après implémentation]* |
| `apps/web/src/features/cockpit/...` | Modification | *[À compléter après implémentation]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[$\ge 90\%$ requis à mesurer après implémentation]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `pnpm typecheck`, `lint-imports`, `lint_spine.py`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après exécution des 5 couches `AD-17`, test `F5` et `pnpm db:reset`]*
