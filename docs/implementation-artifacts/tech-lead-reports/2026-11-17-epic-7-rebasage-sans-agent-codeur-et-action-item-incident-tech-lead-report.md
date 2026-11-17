# 2026-11-17 — Cadrage & Rebasage de l'Epic 7 (Retrait `Story 7.3` Agent Codeur & Création `ACTION_ITEM AIOPS-INCIDENT-LOOP-01`)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification documentaire ou applicative)** :
> `docs/implementation-artifacts/tech-lead-reports/2026-11-17-epic-7-rebasage-sans-agent-codeur-et-action-item-incident-tech-lead-report.md`

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `2026-11-17-epic-7-rebasage-sans-agent-codeur-et-action-item-incident` (`Cadrage & Rebasage Epic 7` / `Amendement AD-3, AD-6 & AD-18` / `ACTION_ITEM AIOPS-INCIDENT-LOOP-01`)
- **Capacité(s)** : `CAP-201`, `CAP-202` (`status: planned` dans `docs/product/capabilities.yaml`) — classification : `doc`
- **Auteur / Contexte** : Tech Lead & Architecte Système ORCIA (`Winston`, `Sally`, `Karim`). Étude critique préalable à l'implémentation de l'Epic 7 (`7.0a`–`7.4`, `FR-5`, `FR-19`, `FR-22`, `FR-24`, `FR-26`, `FR-27`, `FR-29`, `NFR-OBS-1`, `NFR-SEC-4`, `AD-3`, `AD-6`, `AD-18`, `AD-23`, `UX-DR17`). Résolution des 6 fractures architecturales, SQL et UX identifiées entre les spécifications initiales d'octobre 2026 et l'état réel du codebase post-Epics 6, 14, 15, 17, 18 et 19, retrait de la `Story 7.3` (vestige « agent codeur / écriture Git / Sandbox TDD / CI-CD externe » contraire au positionnement d'ORCIA), et ouverture du ticket structuré `AIOPS-INCIDENT-LOOP-01`.
- **Commits associés** : `doc/epic-7-rebase-and-aiops-action-item`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Contexte** : L'Epic 7 (`CAP-201` autonomie sous contrat, déclencheurs idempotents, supervision post-hoc + `CAP-202` socle d'observabilité 12-factor / OpenShift `AD-23`) est le dernier Epic fonctionnel en statut `backlog`, alors que les Epics `1..6`, `8..12`, `14..15` et `17..19` sont `done`. Un audit complet du codebase réel (`bmad-scout` + `gitnexus` `repo: "ORCIA"`) mené le 2026-11-17 a révélé **6 fractures critiques** entre le texte historique de l'Epic 7 et l'architecture actuelle d'ORCIA :
  1. **Fracture n°1 — Incohérence fondamentale de la `Story 7.3` (`UJ-12` agent codeur / Git / Sandbox TDD / déploiement)** :
     - La `Story 7.3` postulait qu'ORCIA clone les dépôts applicatifs, rédige et exécute des tests TDD `Red -> Green` en conteneur Palier 2, pousse du code, valide en staging et déploie en production avec rollback automatique.
     - Or, les **Epics 14 et 18** ont formellement établi qu'**ORCIA ne gère ni le code source ni le déploiement des applications représentées dans ses Espaces** : le développement reste externe dans l'IDE du développeur (`wf-08-dev-external-gate.yaml`), les connecteurs SDLC dans `packages/orcia-connectors` sont simulés en mémoire sans écriture Git ni connecteur CI/CD, `codegraph-mcp` / `gitnexus-mcp` est strictement en lecture seule (`PermissionError` sur toute écriture), et `ContainerSandboxRunner` (`packages/orcia-core/src/orcia_core/gates/tier2_sandbox.py:L178-L187`) lance en pratique `sys.executable -I` localement (aucun Podman-in-Pod compatible OpenShift `SCC restricted`).
     - **Décision** : Retirer `Story 7.3` du périmètre actif de l'Epic 7 et créer le ticket `ACTION_ITEM AIOPS-INCIDENT-LOOP-01` dans `sprint-status.yaml` pour traiter ultérieurement une **boucle fermée de Gouvernance d'Incident sans modification de code ni écriture Git** (Diagnostic contextuel lecture seule → Dossier d'Intention + Paquet MCP IDE `/api/v1/mcp` + Ticket Jira HTTP réel → Pause `DBOS.recv` jusqu'à résolution webhook Jira ou clic manuel 1-clic dans `/processes` → `POST_ACTION_VERIFICATION` via `LogSinkQueryPort` → Clôture auto ou Réouverture/Escalade du ticket).
  2. **Fracture n°2 — Impasse SQL sur `human_anchor_signatures` & goulot `SECOPS` (`Story 7.1`, `AD-3`, `AD-6`, `AD-18`)** :
     - La migration `0015_story_3_4_human_anchors_and_arbitration.py:L31-L65` impose `run_id NOT NULL` et `step_execution_id NOT NULL` sur `human_anchor_signatures`, rendant impossible la signature d'un Contrat d'Autonomie en amont de tout `WorkflowRun`.
     - Par ailleurs, l'exigence de co-signature systématique `SECOPS` dès l'usage d'un `SERVICE_PRINCIPAL` est devenue redondante depuis la `Story 17.3` (`20261111_1703`) et `IAM-ORG-DELEGATION-01`, où seuls `PLATFORM_ADMIN` et `SECOPS` provisionnent et habilitent les Comptes de service dans `iam_accounts` / `role_permission_grants`.
     - **Décision** : Créer une table dédiée **`autonomy_contracts`**, supprimer la co-signature `SECOPS` au profit d'une signature unique `TEAM_LEAD` ou `BU_LEAD` protégée par double garde noyau (`SERVICE_PRINCIPAL` déjà actif et habilité sur l'Espace dans `iam_accounts` + confinement `Actions autorisées ⊆ Droits(Signataire) ∩ Droits(SERVICE_PRINCIPAL)` + trace immuable `audit_ledger`), et amender `AD-3`, `AD-6` et `AD-18` dans `ARCHITECTURE-SPINE.md`.
  3. **Fracture n°3 — Dualité Studio V1 vs Process Studio V2 & `SignedApprovalToken` autonome (`Epics 14 & 15`)** :
     - `packages/orcia-kernel`, `orcia-pack-sdlc` et `orcia-pack-builder` ont été supprimés en Epic 15 au profit de `packs/<domaine>/` déclaratifs et `OrciaConnectorProtocol` (`SignedApprovalToken` requis avant `execute_write()`).
     - Côté UI, `WorkflowTopGovernanceBar.tsx` (hérité Story 8.5, portant le bouton `Déclencheurs`) est du code mort orphelin (`incoming: {}` sous GitNexus) ; le Studio actif est `WorkflowFiveBlocksCanvas.tsx` (`/processes/studio/$workflowId`), dépourvu d'UI Contrats et Déclencheurs.
     - **Décision** : Unifier les modales `OrciaDialog` **« Contrat d'autonomie »** et **« Déclencheurs »** dans `WorkflowFiveBlocksCanvas.tsx`, supprimer `WorkflowTopGovernanceBar.tsx` lors de la `Story 7.1`/`7.2`, et permettre au `PermissionBroker` d'émettre automatiquement un `SignedApprovalToken` scopé au contrat valide lorsque 100 % des Gates déterministes et agentiques passent.
  4. **Fracture n°4 — Risque de duplication Webhook avec l'Epic 18 & déclenchement d'aide (`Story 7.2`)** :
     - `apps/api/src/orcia_api/routers/datasource_webhooks.py` (`Story 18.2`) implémente déjà la validation HMAC temps-constant et la déduplication SQL (`datasource_webhook_deliveries`).
     - `workflow_triggers.trigger_type` (`0010_story_3_1`) omet `OUTBOX_EVENT`, et `workflow_runs.status` omet `PAUSED_AUTONOMOUS_ESCALATION` et `COMMITTED_AUTONOMOUS`.
     - **Décision** : Factoriser la vérification HMAC / anti-rejeu avec `Story 18.2`, activer réellement le démon `trigger-dispatcher` dans `apps/worker/src/orcia_worker/roles.py`, et rendre la génération automatique d'aide à la publication (`generate-and-attach-help` via `OUTBOX_EVENT`) **strictement Opt-in par Espace/Processus** (désactivée au Jour 0).
  5. **Fracture n°5 — Périmètre `7.0b` (Loki vs OpenSearch) et cible OpenShift `7.0c`** :
     - **Décision** : `Story 7.0b` livre `LogSinkQueryPort`, `ElasticsearchLogSinkAdapter` (OpenSearch/Elasticsearch sous `testcontainers`) et l'export OTel OTLP, tandis que `LokiLogSinkAdapter` reste en P2 dans `OBS-LOGSINK-LOKI-01`. `Story 7.0c` fixe le format **Kustomize** (`infra/k8s/base` + `overlays/openshift`), `Dockerfile` multi-rôles + `Dockerfile.web` non-root (`SCC restricted`, `readOnlyRootFilesystem: true`, `/ready`), contrat `ClusterLogForwarder`, et `sandbox-runner` en sidecar/pod isolé HTTP/MCP sans réseau sortant (zéro conteneur imbriqué).
  6. **Fracture n°6 — Obsolescence UX & Loi anti-jargon (`Story 7.4` vs Epics 6, 9 & 17)** :
     - `/inbox` et `/settings?tab=workflows` n'existent plus ; `/finops` possède déjà 4 onglets et `/activity` héberge `audit_ledger`. Les termes `Kill-Switch`, `Rollback`, `Tie-Break`, `Service Principal`, `CIRCUIT_OPEN`, `SM-A1..A3` violent la règle anti-jargon de `GEMINI.md` / `DESIGN.md`.
     - **Décision** : Intégrer `SM-A1..A3` dans l'onglet existant **« Maîtrise humaine & Qualité »** de `/finops` (**0 nouvel onglet**, masqué si `0` run autonome), afficher le badge Cyan/Cobalt `#0284C7` et les sorties de secours dans `/processes`, le tiroir `Notifications` et `ShellContextualHelpColumn.tsx`, avec une microcopy 100 % métier FR (*« Automatisé sous contrat »*, *« Arrêt d'urgence »*, *« Annuler et rétablir la version précédente »*, *« Compte de service »*, *« Contrôle qualité par échantillonnage »*).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "ORCIA"`) & Inspection Codebase** :
  - `WorkflowTopGovernanceBar` (`packages/ui/src/primitives/WorkflowTopGovernanceBar.tsx`) : `incoming: {}` (composant orphelin à supprimer lors de la `Story 7.1`).
  - `packages/orcia-core/src/orcia_core/observability/logging.py:L228-L248` (`configure_structlog`), `scripts/manage.py:L314-L375` (logs `.orcia-run/*.log`), `apps/web/package.json:L22` (`pino` non utilisé), `apps/api/src/orcia_api/routers/health.py:L15-L31` (`GET /api/v1/health`).
  - `infra/migrations/versions/0010_story_3_1_workflow_runs_triggers_and_run_lock.py`, `0015_story_3_4_human_anchors_and_arbitration.py`, `20261116_0601_story_6_1_audit_ledger_append_only.py`, `20261116_0602_story_6_2_finops_budgets_baselines_and_pauses.py`.
  - `apps/worker/src/orcia_worker/roles.py:L17-L29` & `outbox_relay.py:L34-L240`.
  - `apps/api/src/orcia_api/routers/datasource_webhooks.py:L83-L219`, `pack_builder.py:L291-L391`, `apps/web/src/features/processes/studio/WorkflowFiveBlocksCanvas.tsx:L461-L781`, `apps/web/src/features/help/ShellContextualHelpColumn.tsx:L30`.
  - Impact immédiat du présent cadrage : **0 modification de code exécutable** (documentation, Spine, backlog et registre des capacités uniquement).
- **Opportunités de Factorisation & Résorption de Dette Technique** :
  - Mutualisation du socle HMAC temps-constant et anti-rejeu entre `datasource_webhooks.py` (`Story 18.2`) et les webhooks de triggers (`Story 7.2`).
  - Suppression programmée de `WorkflowTopGovernanceBar.tsx` (dette UI Story 8.5) et de `pino` (`Story 7.0a` / `OBS-FRONT-ERRORS-01`).
  - Réutilisation de l'onglet « Maîtrise humaine & Qualité » (`/finops`, `Story 6.3`) pour `SM-A1..A3` sans ajouter de 5ᵉ onglet.
- **Tickets de dette technique / backlog mis à jour** :
  - Retrait de `7-3-boucle-fermée-d-auto-remédiation-uj-12-diagnostic-0-90-repro` du scope actif de `epic-7`.
  - Création de **`AIOPS-INCIDENT-LOOP-01`** (`P2`, `status: open`, `epic: epic-7`) dans `docs/implementation-artifacts/sprint-status.yaml`.

---

## 2. Plan d'Implémentation (Feuille de Route Rebasée Epic 7 & Modifications Documentaires Immédiates)

### 2.1 Schéma de Données & Migrations Alembic (Stories futures `7.1` & `7.2`)
- **Story `7.1`** : Nouvelle migration Alembic créant la table `autonomy_contracts` (`UUIDv7`, `workspace_id`, `workflow_def_id`, `workflow_version_sha256`, `service_principal_id` FK `iam_accounts`, `allowed_actions_jsonb`, `allowed_sources_jsonb`, `max_cost_per_run_usd`, `tie_break_policy`, `signed_by_user_id`, `signed_at`, `revoked_at`) + index partiel sur contrats actifs + extension `workflow_runs.status` (`PAUSED_AUTONOMOUS_ESCALATION`, `COMMITTED_AUTONOMOUS`) + `domain_events_outbox.event_type` (`AutonomousContractSigned`, `AutonomousEscalated`).
- **Story `7.2`** : Nouvelle migration Alembic ajoutant `'OUTBOX_EVENT'` dans le `CHECK` de `workflow_triggers.trigger_type`, reliant `workflow_triggers.contract_id` à `autonomy_contracts(id)`, ajoutant l'opt-in `auto_help_on_publish` (défaut `FALSE`) et les événements Outbox (`TriggerFired`, `SelfTriggerBlocked`, `TriggerCircuitOpened`).
- **Story `7.4`** : Ajout de `post_hoc_audit_status` / file `POST_HOC_AUDIT_SAMPLE` + événements (`PostHocSampleSelected`, `KillSwitchActivated`, `AutonomousArtifactRolledBack`).

### 2.2 Noyau Métier Hexagonal, Observabilité & Workers (`packages/orcia-core/`, `apps/worker/`)
- **Story `7.0a`** : Unification `structlog.stdlib.ProcessorFormatter` JSON 1 ligne sur `stdout`, schéma ECS (`ctx` imbriqué), `LOG_LEVEL`, masquage des secrets (`NFR-SEC-4` secret témoin), configuration des workers et rotation `.orcia-run/*.log` (50 Mo max) dans `scripts/manage.py`, retrait de `pino`.
- **Story `7.0b`** : Port `LogSinkQueryPort` dans `orcia_core`, adaptateur `ElasticsearchLogSinkAdapter` + `LogSinkContractTestKit` sous `testcontainers`, traces OpenTelemetry OTLP (`opentelemetry-sdk`, `opentelemetry-exporter-otlp`, instrumentations `fastapi`/`sqlalchemy`/`httpx`, 0 exportateur OTel Logs) et profils Compose (`logs-elastic`, `logs-loki`).
- **Story `7.0c`** : `Dockerfile` multi-rôles Python + `Dockerfile.web` non-root (`SCC restricted`, `readOnlyRootFilesystem: true`, `/tmp` `tmpfs`), manifestes Kustomize (`infra/k8s/base/` + `overlays/openshift/`), contrat `ClusterLogForwarder`, et `sandbox-runner` isolé en sidecar/pod HTTP interne sans réseau sortant (zéro conteneur imbriqué).
- **Story `7.1`** : Service domaine `AutonomyContractService` (blocage `422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`, signature unique `TEAM_LEAD`/`BU_LEAD` sans `SECOPS`, garde `Actions ⊆ Droits(Signataire) ∩ Droits(SERVICE_PRINCIPAL)`, scellement `audit_ledger`), émission automatique du `SignedApprovalToken` par `PermissionBroker` sous contrat valide et exécution de bout en bout `AUTONOMOUS_CONTRACT` dans le moteur DBOS (`COMMITTED_AUTONOMOUS` / `PAUSED_AUTONOMOUS_ESCALATION`).
- **Story `7.2`** : `SqlWorkflowTriggerRepository`, démon réel `trigger-dispatcher` dans `apps/worker/src/orcia_worker/roles.py` (scrutation `LogSinkQueryPort` avec `error_fingerprint_sha256` et cooldown, `@DBOS.scheduled` pour `CRON`, relais `OUTBOX_EVENT`, verrou Redis `NX EX 86400` + `DBOS SetWorkflowID`), `Self-Trigger Guard` (`x-orcia-origin-run-id` / `service_principal`), et raccordement opt-in de `generate-and-attach-help` (`packs/orcia-docs/`).
- **Story `7.4`** : Échantillonnage `POST_HOC_AUDIT_SAMPLE` (`10–20 %`), arrêt d'urgence à frontière de `@DBOS.step` (`AD-21.5`), restauration instantanée `@v(N-1)` + invalidation Redis `< 10 ms` des fiches `HELP_ARTICLE`, calcul `SM-A1..A3` séparé de `SM-C1/C2`.
- **Action Item différé (`AIOPS-INCIDENT-LOOP-01`)** : Connecteurs HTTP `httpx.AsyncClient` réels pour Jira et Confluence (sans écriture Git), workflow déclaratif d'incident (diagnostic lecture seule, dossier d'intention, paquet MCP `/api/v1/mcp`, ticket Jira, pause `DBOS.recv` + réveil webhook Jira ou clic manuel 1-clic en dev local, puis `POST_ACTION_VERIFICATION` dans `LogSinkQueryPort` avec clôture auto ou réouverture/escalade).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **Stories `7.0a/7.0c`** : Filtrage accès `/api/v1/health` et nouvelle sonde `/ready` (`< 100 ms`, sans SQL lourd).
- **Story `7.1`** : Endpoints `/api/v1/workflows/{id}/autonomy-contracts` (signature, lecture, révocation avec garde `READ_ONLY_OBSERVER` `403`, anti-escalade `403`, `HIGH_CRITICAL` `422`), régénération OpenAPI 3.1 `0-diff`.
- **Story `7.2`** : Endpoints CRUD triggers, webhook entrant mutualisé HMAC (`/api/v1/webhooks/triggers/{trigger_id}`), endpoint `/api/v1/triggers/alerts` (`AD-23.5`) et déclenchement manuel `MANUAL_AUTONOMOUS`.
- **Story `7.4`** : Endpoints d'arrêt d'urgence, rétablissement `@v(N-1)`, revue d'échantillon post-hoc et agrégats `SM-A1..A3` sur `/api/v1/finops/cognitive-impact` (ou endpoint dédié rattaché).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- **Stories `7.1` & `7.2`** : Ajout des modales `OrciaDialog` **« Contrat d'autonomie »** et **« Déclencheurs »** dans l'en-tête de `WorkflowFiveBlocksCanvas.tsx` (`/processes/studio/$workflowId`) avec opt-in explicite pour l'aide automatique à la publication, et suppression de `WorkflowTopGovernanceBar.tsx`.
- **Story `7.4`** : Composant `AutonomousExecutionBadge` (`@orcia/ui`, Cyan/Cobalt `--color-cobalt` `#0284C7` / fond `#F0F9FF` dans `tokens.css`, jamais de Violet `#6D28D9`), regroupement par déclencheur dans le tiroir `Notifications`, commandes d'arrêt d'urgence et de rétablissement dans `/processes` et `ShellContextualHelpColumn.tsx`, métriques `SM-A1..A3` dans l'onglet existant « Maîtrise humaine & Qualité » de `/finops` (masqué à vide), zéro jargon technique banni.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Portes immédiates de ce cadrage documentaire** :
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` (`ok: true`, `0 findings`).
  - `pnpm site:sync` puis `pnpm site:check` (`[site:check OK]` vérifiant le manifeste, les 146 rapports Tech Lead, `capabilities.yaml` et `sprint-status.yaml`).
  - Aucune ligne de code applicatif modifiée (`packages/`, `apps/api/`, `apps/worker/`, `infra/migrations/` intacts).
- **Exigences posées pour les futures Stories `7.0a..7.4` (`AD-17`)** :
  - **Couche 1a (`tests/unit/`, `>= 90 %`)** : masquage secret témoin, `LogSinkContractTestKit`, garde de confinement `AutonomyContractService`, `Self-Trigger Guard`, `SM-A1..A3` `Decimal`, audits statiques anti-patterns.
  - **Couche 1b (`Vitest`, sans `isJsdom`)** : modales Studio V2 (`Contrat`, `Déclencheurs`), `AutonomousExecutionBadge`, survie au `F5` (`unmount`/`render`), zéro bouton muet ni `.catch(() => undefined)`.
  - **Couche 2 (`testcontainers` PG18 + Redis + OpenSearch)** : intégration verticale `HTTP ➔ PG18` des contrats, idempotence concurrente triggers (`UNIQUE` + Redis + DBOS), `ElasticsearchLogSinkAdapter`.
  - **Couche 3 (`OpenAPI 0-diff`, `Schemathesis`, `lint-imports`)** : `5 contracts kept, 0 broken`.
  - **Couche 4 (`tests/evals/` `DeterministicCassetteLLM`)** : exécution autonome `UJ-11` avec `tie_break_policy` et `generate-and-attach-help`.
  - **Couche Sécurité (`tests/security/`)** : blocage `403 READ_ONLY_OBSERVER`, rejet `HIGH_CRITICAL` `422`, anti-escalade `SERVICE_PRINCIPAL`, validation HMAC constant-time, zéro secret en clair dans logs/DBOS/Outbox/ledger.
  - **Couche 5 (`Playwright` Desktop + Mobile)** : création contrat/déclencheur dans Studio V2, arrêt d'urgence et rétablissement `@v(N-1)` dans `/processes` et aide contextuelle.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification) | Description synthétique |
| :--- | :--- | :--- |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-17-epic-7-rebasage-sans-agent-codeur-et-action-item-incident-tech-lead-report.md` | Création | Rapport Tech Lead de cadrage et rebasage de l'Epic 7 (fractures, amendements `AD-3`/`AD-6`/`AD-18`, retrait `Story 7.3`, création `AIOPS-INCIDENT-LOOP-01`). |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md` | Modification | Amendement `AD-3`, `AD-6` et `AD-18` (table `autonomy_contracts`, signature unique `TEAM_LEAD`/`BU_LEAD` sans co-signature `SECOPS`, `SignedApprovalToken`, `OUTBOX_EVENT` opt-in, suppression du volet code/Sandbox TDD/déploiement dans `AD-18`). |
| `docs/planning-artifacts/epics.md` | Modification | Rebasage complet de l'Epic 7 (`Stories 7.0a, 7.0b, 7.0c, 7.1, 7.2, 7.4`), suppression de `Story 7.3` avec renvoi vers `AIOPS-INCIDENT-LOOP-01`, alignement Studio V2 / Kustomize / Direction C sans jargon. |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Retrait de `7-3-...` du scope actif de `epic-7` et ajout détaillé de `AIOPS-INCIDENT-LOOP-01` sous `action_items:`. |
| `docs/product/capabilities.yaml` | Modification | Actualisation de `CAP-201` (`epic-7 (7-1, 7-2, 7-4, backlog)` et note d'exclusion écriture code/Git + report dans `AIOPS-INCIDENT-LOOP-01`). |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Enregistrement du rapport dans l'index officiel. |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `dist/orcia-site/index.html` | Régénération (`pnpm site:sync`) | Synchronisation du manifeste showcase et du site statique autonome après vérifications. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Porte Architecture Spine (`lint_spine.py`)** : `ok: true`, `total_findings: 0` (vérification mécanique de `ARCHITECTURE-SPINE.md`, 24 décisions d'architecture `AD-1` à `AD-24`, 44 composants Stack épinglés, 0 placeholder ni rupture de séquence).
- **Porte Catalogue & Showcase (`pnpm site:sync` & `pnpm site:check`)** :
  - `techLeadReportsCount`: `146` (incluant le présent rapport) ;
  - `activeRoutesCount`: `26`, `uiPrimitivesCount`: `119`, `installedPacksCount`: `2`, `alembicMigrationsCount`: `45` ;
  - `capabilitiesCount`: `62` (`60/60` capacités `live` avec au moins un test référencé, `CAP-201` et `CAP-202` au statut `planned`, `45` vérifiées en `runtime`) ;
  - Contrôle YAML (`yaml.safe_load` sur `sprint-status.yaml` et `capabilities.yaml`) : `YAML_OK`.
- **Périmètre d'isolation applicative** : **0** ligne de code modifiée dans `packages/`, `apps/api/`, `apps/worker/`, `infra/migrations/` ou `apps/web/src/` (hors régénération automatique de `apps/web/src/generated/orciaSiteManifest.ts` par `pnpm site:sync`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Validation Statique Architecture & Documentation** :
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : `{"ok": true, "spine": "ARCHITECTURE-SPINE.md", "total_findings": 0}`.
  - `.venv/bin/python -c "import yaml; yaml.safe_load(open('docs/implementation-artifacts/sprint-status.yaml')); yaml.safe_load(open('docs/product/capabilities.yaml')); print('YAML_OK')"` : `YAML_OK`.
  - `pnpm site:sync` puis `pnpm site:check` : `[site:check OK] Manifest (146 reports, 26 routes, 119 UI primitives) is in sync.`
- **Couches 1 à 5 (`AD-17`)** : Non applicables à une passe purement documentaire ; les exigences des 5 couches + Sécurité pour les futures Stories `7.0a`, `7.0b`, `7.0c`, `7.1`, `7.2`, `7.4` et `AIOPS-INCIDENT-LOOP-01` sont consignées en Section 2.5 et dans les critères d'acceptation de `epics.md`.
