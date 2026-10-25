# Rapport d'Implémentation Tech Lead — Story 1.4 : Exécution Passthrough / Service Principal & Permission Broker IA connecté à Jira

- **Story Key** : `1-4-exécution-passthrough-service-principal-permission-broker-ia`
- **Epic** : `Epic 1 — Amorçage Gouverné de l'Organisation, Onboarding Autonome d'Équipe (TEAM_LEAD), Catalogue Fédéré & Permission Broker connecté à Jira`
- **Date** : `2026-10-25`
- **Auteur** : `Tech Lead / Senior Dev Agent (Antigravity)`
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1. Contexte & Problématique Métier / Technique
Dans une plateforme d'orchestration d'agents connectée aux sources d'entreprise (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`, MCP), deux risques majeurs menacent la sécurité et la fluidité opérationnelle :
1. **L'élévation de privilèges par *Confused Deputy*** : si un agent exécute ses appels externes via un compte de service global omnipotent (`service_principal` non gouverné), un utilisateur peut contourner les habilitations natives de Git, Confluence ou Jira.
2. **L'impasse opérationnelle sur refus d'accès (`HTTP 401/403`)** : lorsqu'une étape de workflow échoue faute de droit sur un dépôt Git privé, une page Confluence restreinte ou une transition de projet Jira, l'utilisateur se retrouve bloqué devant une erreur technique opaque sans savoir quel rôle demander, à quelle équipe approbatrice s'adresser, ni comment débloquer et rejouer son étape (`Replay Step N`).

La **Story 1.4** (`FR-22`, `AD-6`, `UX-DR11`) résout ces deux problèmes en imposant l'exécution `passthrough` par défaut (identité déléguée chiffrée `AES-256-GCM`, avec garde-fou strict sur `service_principal` réservé aux ressources explicitement approuvées par un administrateur) et en introduisant le **`PermissionBrokerService`** adossé à une Base de Connaissances d'Habilitations (fichiers Markdown à frontmatter YAML `uri_pattern`, `required_role`, `approver_team`, `request_url_template`, `sla_hours`), restituant une enveloppe **RFC 9457** enrichie de `permission_broker_hint` et ouvrant automatiquement le **Dock Agent Assistant & Permission Broker** sur une carte ambre (`#D97706`, `UX-DR11`) munie du lien Jira pré-rempli et du bouton *Mettre en pause / Rejouer l'étape*.

### 1.2. Analyse d'Impact GitNexus (Obligatoire)
- **Requêtes exécutées (`repo: "ORCIA"`)** :
  - `gitnexus_query({repo: "ORCIA", search_query: "permission broker passthrough service principal assistant dock"})`
  - `gitnexus_impact({repo: "ORCIA", target: "AssistantDock", direction: "upstream"})` $\rightarrow$ **`risk: LOW`** (`impactedCount: 3` : `AppShell.tsx` d=1, `ShellContainer.tsx` d=2, `RootLayout` d=3).
  - `gitnexus_impact({repo: "ORCIA", target: "ProblemDetails", direction: "upstream"})` $\rightarrow$ **`risk: LOW`** (`impactedCount: 2` : `schemas/__init__.py` d=1, `OrciaProblemError.constructor` dans `packages/api-client/src/index.ts` d=1).
  - `gitnexus_impact({repo: "ORCIA", target: "AuthAndOrganizationService", direction: "upstream"})` $\rightarrow$ **`risk: LOW`** (`impactedCount: 2` : `permissions/__init__.py` d=1, `catalog/__init__.py` d=2).
  - `gitnexus_impact({repo: "ORCIA", target: "PassthroughVaultCipher", direction: "upstream"})` $\rightarrow$ **`risk: LOW`** (`impactedCount: 3` : `permissions/service.py` d=1, `permissions/__init__.py` d=1).
  - `gitnexus_impact({repo: "ORCIA", target: "MatrixPermissionEvaluator", direction: "upstream"})` $\rightarrow$ **`risk: LOW`** (`impactedCount: 4` : `catalog/service.py` d=1, `permissions/service.py` d=1, `permissions/__init__.py` d=1).
- **Évaluation du risque et rayon d'impact** : Risque **LOW** sur l'ensemble des symboles existants. Le champ `permission_broker_hint: str | None` existe déjà dans `ProblemDetails` (`schemas/problem_details.py`) et `OrciaDomainError` (`domain/exceptions.py`), ce qui garantit une compatibilité ascendante totale des gestionnaires d'erreurs RFC 9457 existants.

### 1.3. Exploration & Chiffres Clés (Base de Données, Codebase, Volumétrie)
- **Tables existantes (Alembic `0001` à `0003`)** : 12 tables (`org_units`, `workspaces`, `workspace_datasources`, `users`, `transverse_groups`, `user_transverse_group_memberships`, `workspace_memberships`, `workspace_invitations`, `user_passthrough_credentials`, `catalog_acl_entries`, `catalog_items`, `workflow_definitions`, `workspace_customization_overrides`).
- **Nouvelles tables introduites en Story 1.4 (`0004_story_1_4_permission_broker_and_step_denials.py`)** :
  - `permission_broker_policies` (clés `UUIDv7`, `uri_pattern`, `connector_scheme`, `required_role`, `approver_team`, `request_url_template`, `sla_hours`, `procedure_markdown`, `service_principal_allowed`, `approved_by_admin_id`).
  - `permission_broker_tickets` (clés `UUIDv7`, suivi des blocages `WAITING_FOR_PERMISSION`, `PAUSED`, `REPLAYED`, `GRANTED` par étape/source).
- **Contrôle de volumétrie des fichiers existants** :
  - `packages/orcia-core/src/orcia_core/permissions/service.py` : `290` lignes $\rightarrow$ conserver intact et créer un module dédié `packages/orcia-core/src/orcia_core/permissions/broker.py` (`< 260` lignes) pour éviter tout dépassement du seuil des `300` lignes.
  - `packages/orcia-core/src/orcia_core/domain/exceptions.py` : `302` lignes $\rightarrow$ conserver sous le seuil en ajoutant uniquement les 2 entrées compactes `ERR_PERMISSION_BROKER_INTERCEPTED` et `ERR_CONFUSED_DEPUTY_BLOCKED`.
  - `packages/ui/src/shell/AssistantDock.tsx` : `185` lignes $\rightarrow$ extraire la carte ambre dans un composant dédié `packages/ui/src/shell/PermissionBrokerCard.tsx` (`< 180` lignes).

### 1.4. Opportunités de Factorisation & Dette Technique Identifiée
- **Factorisation retenue (`Étape 0 / DRY`)** :
  - Réutiliser le coffre `PassthroughVaultCipher` (`AES-256-GCM`) et `MatrixPermissionEvaluator` livrés en Story 1.2 au sein de `PermissionBrokerService` afin qu'un seul moteur vérifie à la fois les 5 permissions du Catalogue (`EXECUTE`), la présence du jeton délégué `passthrough` et l'approbation `service_principal`.
  - Réutiliser le parseur de frontmatter YAML sans dépendance externe pour charger les fiches Markdown de la KB d'Habilitations (`uri_pattern`, `required_role`, `approver_team`, `request_url_template`, `sla_hours`) et préparer dès maintenant les champs de signature d'Ancre Humaine requis par `init-datasource` en Story 1.5.
- **Tickets de dette technique / refactoring créés** : Aucun ticket de dette différé n'est nécessaire ; le découpage modulaire (`permissions/broker.py`, `PermissionBrokerCard.tsx`) maintient tous les fichiers sous `290` lignes.

---

## 2. Plan d'Implémentation

### 2.1. Schéma de Données & Migrations Alembic (`infra/migrations/`)
- Créer `infra/migrations/versions/0004_story_1_4_permission_broker_and_step_denials.py` (`down_revision = "0003_story_1_3"`) en SQL brut (`op.execute(sa.text(...))`) créant `permission_broker_policies` et `permission_broker_tickets` avec clés primaires `UUIDv7` et contraintes `CHECK` sur les schémas (`git`, `jira`, `confluence`, `db`, `nexus`, `mcp`) et statuts (`WAITING_FOR_PERMISSION`, `PAUSED`, `REPLAYED`, `GRANTED`).
- Ajouter les semences idempotentes dans `packages/orcia-core/src/orcia_core/bootstrap/permission_broker_seeds.py` et `seeder.py`, ainsi que le script `infra/scripts/maintenance/03_backfill_permission_broker.py` (`--dry-run` par défaut, `--apply` pour commiter).

### 2.2. Noyau Hexagonal, Algorithmes & Workers (`packages/orcia-core/` & `apps/worker/`)
- Créer `packages/orcia-core/src/orcia_core/permissions/broker.py` :
  - `PermissionBrokerPolicy` & parseur `parse_permission_kb_markdown(markdown_text)` lisant le frontmatter YAML (`uri_pattern`, `required_role`, `approver_team`, `request_url_template`, `sla_hours`, `service_principal_allowed`, `approved_by_admin_id`) et le corps Markdown de procédure.
  - `PermissionBrokerTicket` (`WAITING_FOR_PERMISSION`, `PAUSED`, `REPLAYED`, `GRANTED`) et `PermissionBrokerResolution` (incluant `jira_request_url` pré-rempli et `formatted_hint` injecté dans `permission_broker_hint` de l'enveloppe RFC 9457).
  - `PermissionBrokerService` :
    1. Vérifie le mode d'identité d'exécution (`execution_identity: passthrough | service_principal`) : bloque immédiatement toute exécution `service_principal` non explicitement approuvée par un administrateur (`ConfusedDeputyBlockedError`, `HTTP 403 ERR_CONFUSED_DEPUTY_BLOCKED`).
    2. En mode `passthrough` (défaut), vérifie que l'utilisateur détient la permission `EXECUTE` et le rôle/jeton délégué requis sur la cible (`git://`, `confluence://`, `jira://`, `db://`, `nexus://`).
    3. En cas de refus (`HTTP 401/403` amont ou rôle manquant), intercepte l'erreur, résout le motif `uri_pattern` correspondant dans la KB, génère le lien Jira pré-rempli (`https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?...`), crée un ticket `WAITING_FOR_PERMISSION` (`step_state="PERMISSION_DENIED_STEP"`) et lève `PermissionBrokerDeniedError` (`HTTP 403 ERR_PERMISSION_BROKER_INTERCEPTED`) avec `permission_broker_hint`.
    4. Permet de mettre en pause (`pause_blocked_step`) ou de débloquer et rejouer l'étape (`replay_blocked_step`, `FR-22`).

### 2.3. Couche Backend FastAPI & Contrats OpenAPI (`apps/api/` & `packages/api-client/`)
- Créer `packages/orcia-core/src/orcia_core/schemas/permission_broker.py` et `apps/api/src/orcia_api/routers/permission_broker.py` :
  - `GET /api/v1/permissions/broker/state` : état consolidé des politiques KB et des tickets `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION` pour le Workspace et le persona actifs.
  - `POST /api/v1/permissions/broker/policies/import-markdown` : import d'une fiche Markdown à frontmatter YAML dans la KB d'Habilitations (protégé contre `READ_ONLY_OBSERVER`).
  - `POST /api/v1/permissions/broker/check-access` : exécution gouvernée d'un accès connecteur (`passthrough` ou `service_principal`) avec mode `raise_on_denied: bool` permettant à la fois de tester l'enveloppe d'erreur RFC 9457 (`HTTP 403` + `permission_broker_hint`) et d'inspecter le ticket `WAITING_FOR_PERMISSION`.
  - `POST /api/v1/permissions/broker/tickets/{ticket_id}/action` : action `PAUSE` ou `REPLAY` (*Mettre en pause / Rejouer l'étape*) sur une étape bloquée (`FR-22`).
- Régénérer `packages/api-client` (`openapi.json` + `src/generated/schema.ts`) avec `0-diff`.

### 2.4. Design System (`packages/ui`) & Interface Next.js Direction C (`apps/web/`)
- Créer dans `@orcia/ui` (`packages/ui/src/shell/PermissionBrokerCard.tsx`) la carte ambre (`#D97706`, `UX-DR11`) affichant :
  1. L'URI exacte de la source (`git://`, `confluence://`, `jira://`, `db://`, `nexus://`), le mode d'identité (`passthrough` vs `service_principal`) et le rôle manquant (`required_role`),
  2. L'équipe approbatrice (`approver_team`), le SLA (`sla_hours`) et la procédure Markdown de la KB,
  3. Le bouton/lien ouvrant la demande d'accès pré-remplie dans **Atlassian Jira**,
  4. Les boutons *Mettre en pause* et *Rejouer l'étape (Replay Step N)* (`FR-22`).
- Mettre à jour `AssistantDock.tsx` et `AppShell.tsx` pour que la réception ou la sélection d'un état `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION` **ouvre automatiquement le Dock Agent Assistant & Permission Broker à droite** (`dockCollapsed -> false`) et affiche la `PermissionBrokerCard`.
- Intégrer le simulateur et le tableau de bord du Permission Broker dans **🛡️ 5. Gates & Habilitations** (`ModuleWorkspaceView.tsx`) ainsi que dans le Cockpit/Catalogue, avec dictionnaires `i18n` `fr`/`en` complets.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1. Fichiers Développés et Modifiés
| Fichier | Action | Rôle & Responsabilité | Lignes |
| :--- | :--- | :--- | :---: |
| `infra/migrations/versions/0004_story_1_4_permission_broker_and_step_denials.py` | Créé | Migration Alembic `0004` (`permission_broker_policies`, `permission_broker_tickets` avec `procedure_markdown`, `UUIDv7`). | 104 |
| `packages/orcia-core/src/orcia_core/bootstrap/permission_broker_seeds.py` | Créé | Semences de la KB d'Habilitations (`git://`, `confluence://`, `jira://`, `db://`, `nexus://`) et ticket initial `PERMISSION_DENIED_STEP`. | 222 |
| `packages/orcia-core/src/orcia_core/bootstrap/seeder.py` | Modifié | Spécifications `UpsertSpec` idempotentes (`PERMISSION_BROKER_POLICIES_UPSERT_SPEC`, `PERMISSION_BROKER_TICKETS_UPSERT_SPEC`). | 288 |
| `infra/scripts/maintenance/03_backfill_permission_broker.py` | Créé | Script de maintenance idempotent (`--dry-run` / `--apply`) pour les politiques et tickets du Permission Broker. | 261 |
| `packages/orcia-core/src/orcia_core/permissions/broker_models.py` | Créé | Entités `PermissionBrokerPolicy`, `PermissionBrokerTicket`, `PermissionCheckOutcome`, parseur Markdown+YAML borné et constructeurs d'URL Jira. | 259 |
| `packages/orcia-core/src/orcia_core/permissions/broker.py` | Créé | `PermissionBrokerService` (garde-fou anti-*Confused Deputy*, vérification ACL Catalogue + `PassthroughVaultCipher`, interception `401/403`, transitions `PAUSED`/`REPLAYED`/`GRANTED`). | 276 |
| `packages/orcia-core/src/orcia_core/permissions/evaluator.py` | Modifié | Résolution d'ACL Catalogue par URI (`get_catalog_acl_by_uri`) et contrôle de périmètre Workspace. | 294 |
| `packages/orcia-core/src/orcia_core/domain/exceptions.py` | Modifié | Exceptions `PermissionBrokerDeniedError` et `ConfusedDeputyBlockedError` dans le catalogue RFC 9457 (`fr`/`en`). | 280 |
| `packages/orcia-core/src/orcia_core/schemas/permission_broker.py` | Créé | Schémas Pydantic v2 (`extra="forbid"`) pour `/api/v1/permissions/broker/*`. | 150 |
| `apps/api/src/orcia_api/routers/permission_broker.py` | Créé | Routeur FastAPI `/api/v1/permissions/broker/*` branché sur `MatrixPermissionEvaluator` et `PassthroughVaultCipher`. | 209 |
| `packages/api-client/src/index.ts` | Modifié | Client typé `getPermissionBrokerState(personaKey?, workspaceId?)` et méthodes Permission Broker (`0-diff` OpenAPI). | 270 |
| `packages/ui/src/shell/PermissionBrokerCard.tsx` | Créé | Composant pur `@orcia/ui` (`UX-DR11`) affichant la carte ambre `#D97706`, le rôle manquant, l'approbateur, le SLA, `procedureMarkdown`, le lien Jira pré-rempli et *Pause / Replay Step N*. | 265 |
| `packages/ui/src/shell/AssistantDock.tsx` & `AppShell.tsx` | Modifié | Ouverture automatique du Dock à droite sur état `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION` et intégration de `PermissionBrokerCard`. | 208 / 225 |
| `apps/web/src/components/ModuleWorkspaceView.tsx` & `workspaceFixtures.ts` | Modifié | Panneau simulateur `PERMISSION_DENIED_STEP` (ciblé sur `cockpit`, `catalog`, `gates`) et fixtures `procedureMarkdown` (`fr`/`en`). | 217 / 284 |
| `tests/unit/test_permission_broker.py` & `tests/integration/test_real_containers.py` | Créé / Modifié | Tests unitaires (`pytest` + `hypothesis`, 27 tests) et tests d'intégration `testcontainers` (migration `0004` + backfill `03`). | 350 |

### 3.2. Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests Python (`pytest --cov=packages/orcia-core --cov-fail-under=90`)** : **`97.61 %`** global sur `packages/orcia-core` (`29 passed`), dont **`98 %`** sur `broker_models.py`, **`95 %`** sur `broker.py`, **`100 %`** sur `permission_broker_seeds.py`, **`100 %`** sur `seeder.py` et **`100 %`** sur `schemas/permission_broker.py`.
- **Couverture & tests TypeScript (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches Turborepo réussies** (`@orcia/api-client`: `5 passed`, `@orcia/ui`: `8 passed`, `@orcia/web`: `4 passed`).
- **Tests E2E Playwright (`pnpm --filter @orcia/web test:e2e`)** : **`2 passed`** (`desktop-cockpit` `1600x1000` & `mobile-companion` `390x844`).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : `0 erreur` (`137 files already formatted`)
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : `0 erreur` (`Success: no issues found in 53 source files`)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : `{"ok": true, "total_findings": 0}`
  - `gitnexus_detect_changes({repo: "ORCIA", scope: "all"})` : graphe d'impact vérifié sans régression.

### 3.3. Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** : Validation de l'exécution `passthrough` par défaut (jeton chiffré `PassthroughVaultCipher` ou rôle accordé), du blocage anti-*Confused Deputy* sur `service_principal` non approuvé et à l'import Markdown par un non-administrateur, des bornes YAML du parseur KB (`sla_hours`, `freshness_ttl_days`, longueurs), de l'isolation de périmètre Workspace et du garde-fou `OBSERVER`/`BU_DIRECTOR`, du cycle `WAITING_FOR_PERMISSION -> PAUSED -> REPLAYED / GRANTED` et du composant `@orcia/ui` `PermissionBrokerCard` (incluant `procedureMarkdown`).
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** : Vérification du cycle complet `alembic upgrade head -> downgrade 0003_story_1_3 -> downgrade base -> upgrade head` et de l'idempotence de `03_backfill_permission_broker.py` (`--dry-run` rollback puis `--apply` commit).
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff + `Schemathesis`)** : `0 diff` sur `packages/api-client` et conformité OpenAPI 3.1 + RFC 9457 validée par `Schemathesis`.
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** : Validation déterministe sans appel LLM externe (`0 $`).
- **Couche 5 — Tests E2E & Accessibilité (`@playwright/test` Desktop `1600x1000` & Mobile `390x844`)** : Vérification de l'ouverture automatique du Dock Permission Broker sur `PERMISSION_DENIED_STEP`, de l'affichage de la carte ambre `#D97706` (source, rôle manquant, équipe approbatrice, SLA, procédure Markdown, lien Jira pré-rempli, bouton *Rejouer l'étape*) et `0` violation WCAG 2.1 AA (`@axe-core/playwright`).
