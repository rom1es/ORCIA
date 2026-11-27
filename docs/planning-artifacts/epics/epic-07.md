## Epic 7: Agents & Workflows Autonomes sous Contrat, Socle d'Observabilité 12-Factor & OpenShift, Déclencheurs Événementiels Idempotents & Gouvernance Post-Hoc

Permettre aux Directeurs de BU, Chefs d'Équipe (`TEAM_LEAD` / `BU_LEAD`), Ingénieurs SRE/Plateforme et Auditeurs SecOps (`Claire UJ-8/UJ-11`, `Marc UJ-5`, `Karim UJ-9`, `Sophie UJ-6`) de disposer préalablement du **socle d'observabilité 12-factor unifié sur `stdout` (Story 7.0a)**, du **puits de logs paramétrable (`LogSinkQueryPort` avec adaptateur prioritaire Elasticsearch/OpenSearch) et des traces OTel OTLP (Story 7.0b, `AD-23`)** et de la **conformité de déploiement en conteneur non-root Kustomize sur plateforme OpenShift avec `sandbox-runner` en sidecar isolé sans Podman-in-Pod (Story 7.0c)**, puis de signer des **Contrats d'Autonomie** dans `autonomy_contracts` depuis **Process Studio V2 (`/processes/studio/$workflowId`)** sur les workflows éligibles (`LOW_NON_CRITICAL`, `STANDARD`, signature unique `TEAM_LEAD`/`BU_LEAD` sans co-signature `SECOPS`, Story 7.1), de déclencher de manière idempotente des **Workflow Runs autonomes** (`MANUAL_AUTONOMOUS`, **Webhooks signés** factorisés avec `Story 18.2`, **Tâches Planifiées `CRON`**, **Événement `OUTBOX_EVENT`** avec génération d'aide `generate-and-attach-help` en **opt-in explicite** désactivé au Jour 0, ou **Alertes de Puits de Logs `LOG_SINK_ALERT`** via `trigger-dispatcher`, Story 7.2), et de superviser ces exécutions via le badge Cyan/Cobalt (`UX-DR17`), le tiroir `Notifications`, `/processes`, la Colonne d'aide droite, l'échantillonnage post-hoc et l'onglet existant « Maîtrise humaine & Qualité » de `/finops` avec une microcopy 100 % métier FR (Story 7.4). *(La boucle fermée de gouvernance d'incident sans modification de code ni écriture Git est différée dans `ACTION_ITEM AIOPS-INCIDENT-LOOP-01`.)*

### Story 7.0a: Socle de Journalisation Unifié 12-Factor (JSON stdout), Masquage des Secrets & Niveau de Log Dynamique

As a Ingénieur Plateforme / SRE ou Tech Lead (`Karim UJ-9`, `Yanis UJ-3`),
I want unifier 100 % de l'émission des logs applicatifs et serveurs (FastAPI, Uvicorn, Dramatiq, DBOS, SQLAlchemy, triggers et scripts d'administration) sur `stdout` au format JSON 1 ligne via `ProcessorFormatter` de structlog, rendre le niveau de log paramétrable par la variable d'environnement `LOG_LEVEL`, masquer systématiquement les secrets et jetons avant émission (`NFR-SEC-4`), et assainir la gestion des logs locaux (`.orcia-run/*.log`),
So that l'ensemble des processus ORCIA respecte la méthodologie 12-Factor, supprime toute stacktrace multi-lignes brute sur `stderr`, élimine tout risque de saturation disque locale et prépare l'ingestion native par les collecteurs de conteneurs sans fuite de secrets (`NFR-SEC-4`, `NFR-OBS-1`, `AD-12`, `AD-23`, Décisions D1, D2).

**Acceptance Criteria:**

**Given** `configure_logging(service: str, log_level: str | None = None)` centralisé dans `packages/orcia-core/src/orcia_core/observability/logging.py`
**When** un log est émis par l'API, le worker, Dramatiq, DBOS, SQLAlchemy ou Uvicorn
**Then** l'événement est formaté via `structlog.stdlib.ProcessorFormatter` sur `stdout` sous la règle stricte **1 ligne = 1 événement JSON sérialisé**
**And** les exceptions et stacktraces sont sérialisées dans le champ JSON unique `exception` sans aucune ligne brute multi-lignes sur `stderr`
**And** les champs JSON respectent le schéma normalisé aligné ECS (`timestamp` ISO-8601 UTC, `level`, `logger`, `message`, `service`, `env`, `version`, `trace_id`, `span_id`, `workspace_id`, `run_id`, `step_id`, `ctx`)
**And** la variable d'environnement `LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` ; défaut `INFO`) est prise en compte dynamiquement par tous les processus (`apps/api`, `apps/worker`, `scripts/`)
**And** les sondes d'infrastructure HTTP régulières (`/api/v1/health`, `/ready`) sont filtrées des journaux d'accès pour éviter la saturation inutile.

**Given** la présence de secrets, mots de passe temporaires, tokens JWT ou jetons PAT dans les structures de données
**When** un log est émis
**Then** le processeur de masquage structlog remplace systématiquement les valeurs sensibles par un masque anonymisé, vérifié en CI par le test du secret témoin (`NFR-SEC-4`).

**Given** l'environnement de développement local (`scripts/manage.py`) et `apps/web/package.json`
**When** les processus locaux sont démarrés
**Then** les fichiers de logs `.orcia-run/*.log` appliquent une rotation automatique bornée (`RotatingFileHandler` max 50 Mo) ou sont redirigés vers `stdout`
**And** la dépendance non utilisée `pino` dans `apps/web/package.json` est retirée
**And** `lint-imports` passe à `0` violation et les tests unitaires couvrent $\ge 90\%$ du socle de logging (`AD-17`, `AD-23`).

### Story 7.0b: Puits de Logs Paramétrable (`LogSinkQueryPort`), Adaptateur Elasticsearch / OpenSearch Prioritaire, Traces OTel OTLP & Profils Compose

As a Architecte Système ou Ingénieur SRE (`Winston`, `Karim`),
I want abstraire l'accès en lecture au puits de logs derrière le port `LogSinkQueryPort`, implémenter l'adaptateur prioritaire de production `ElasticsearchLogSinkAdapter` (compatible Elasticsearch et OpenSearch sans API propriétaire) validé par le kit de contrat commun `LogSinkContractTestKit`, exporter les traces distribuées OpenTelemetry via le protocole standard OTLP vers `OTEL_EXPORTER_OTLP_ENDPOINT`, et fournir les profils Docker Compose dev (`logs-elastic`, `logs-loki`),
So that le code applicatif demeure totalement découplé du puits de logs, que la bascule d'infrastructure soit garantie par les 4 invariants de réversibilité sans surcharger la CI (`LokiLogSinkAdapter` restant différé en P2 dans `OBS-LOGSINK-LOKI-01`), et que `Story 7.2` (`LOG_SINK_ALERT`) puis `AIOPS-INCIDENT-LOOP-01` (`POST_ACTION_VERIFICATION`) disposent de leur socle d'interrogation (`FR-23`, `FR-24`, `FR-29`, `NFR-OBS-1`, `AD-12`, `AD-18`, `AD-23`, Décisions D3, D4, D6, D7, D9, D10).

**Acceptance Criteria:**

**Given** le port abstrait `LogSinkQueryPort` (`query_logs`, `count_errors`, `healthcheck`) dans le domaine hexagonal de `orcia-core`
**When** l'adaptateur prioritaire `ElasticsearchLogSinkAdapter` (`opensearch-py` / `elasticsearch-py`) est instancié
**Then** il passe avec succès le kit de test de contrat commun réutilisable `LogSinkContractTestKit` sous `testcontainers` (OpenSearch/Elasticsearch) — kit prêt à valider `LokiLogSinkAdapter` ultérieurement via `OBS-LOGSINK-LOKI-01`
**And** l'adaptateur effectif est sélectionné au Composition Root (`lifespan` API / `on_startup` worker) via la variable d'environnement `LOG_SINK_BACKEND=elasticsearch|loki|none` (défaut `none` si non configuré).

**Given** l'instrumentation OpenTelemetry des processus Python (`opentelemetry-sdk`, `opentelemetry-exporter-otlp`, instrumentations `fastapi`, `sqlalchemy`, `httpx`)
**When** des requêtes et étapes de workflow sont exécutées
**Then** les spans et traces sont exportés via le protocole standard OTLP vers `OTEL_EXPORTER_OTLP_ENDPOINT` (ou désactivés sans erreur si `OTEL_TRACES_EXPORTER=none`)
**And** le `trace_id` et le `span_id` courants sont injectés de manière déterministe dans le contexte structlog de chaque log JSON émis
**And** aucun exportateur OTel Logs n'est instancié dans le code Python (conformité stricte à l'émission 12-factor JSON stdout).

**Given** les 4 invariants de réversibilité (`AD-23`)
**When** l'architecture est auditée
**Then** (1) les logs sont émis uniquement sur stdout JSON, (2) les traces utilisent OTLP standard, (3) l'empreinte `error_fingerprint_sha256`, la déduplication et le masquage sont 100 % dans le code ORCIA (zéro logique d'alerte dans le collecteur), et (4) la lecture du puits passe exclusivement par `LogSinkQueryPort`
**And** le fichier `infra/docker/docker-compose.yml` intègre les profils optionnels `--profile logs-elastic` (OpenSearch/Elasticsearch + Grafana) et `--profile logs-loki` (Loki + Grafana)
**And** `lint-imports` passe à `0` violation et les tests unitaires et d'intégration couvrent $\ge 90\%$ (`AD-17`, `AD-23`).

### Story 7.0c: Conformité & Préparation au Déploiement OpenShift (Dockerfiles Non-Root, Kustomize SCC Restricted, FS Read-Only, Sonde `/ready` & Contrat `ClusterLogForwarder`)

As a Ingénieur Plateforme / DevOps ou SecOps (`Karim UJ-9`, `Sophie UJ-6`),
I want livrer les Dockerfiles multi-rôles non-root (`Dockerfile` Python + `Dockerfile.web`), les manifestes **Kustomize** (`infra/k8s/base/` et `infra/k8s/overlays/openshift/`) conformes OpenShift SCC `restricted` (UID arbitraire non root, `readOnlyRootFilesystem: true`, `tmpfs` `/tmp`), isoler `sandbox-runner` en **sidecar/pod HTTP/MCP interne sans réseau sortant (zéro Podman-in-Pod / conteneur imbriqué)**, exposer la sonde `/ready` (`< 100 ms`), et formaliser le contrat d'intégration avec le `ClusterLogForwarder` vers Elasticsearch/OpenSearch,
So that les conteneurs ORCIA soient déployables sur un cluster OpenShift d'entreprise avec le plus haut niveau de durcissement sans privilèges élevés, sans stockage persistant pour les logs techniques et sans dépendance à des `user namespaces` privilégiés (`FR-28`, `NFR-SEC-1`, `NFR-OBS-1`, `AD-9`, `AD-12`, `AD-19`, `AD-23`, Décision D8).

**Acceptance Criteria:**

**Given** les `Dockerfile`s (`Dockerfile` multi-rôles Python + `Dockerfile.web` Vite statique) et les manifestes Kustomize (`infra/k8s/base/` + `infra/k8s/overlays/openshift/`)
**When** les conteneurs ORCIA (`api`, `worker-orchestration`, `worker-indexing`, `trigger-dispatcher`, `sandbox-runner`, `web`) sont exécutés sous OpenShift SCC `restricted`
**Then** les conteneurs s'exécutent avec succès sous un UID Linux arbitraire non root (`securityContext.runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`)
**And** le système de fichiers racine est monté en lecture seule (`readOnlyRootFilesystem: true`), les seuls répertoires temporaires autorisés étant des volumes mémoire `tmpfs` montés sur `/tmp` (`sizeLimit: 64Mi` / `256Mi` pour `sandbox-runner`)
**And** `sandbox-runner` fonctionne en sidecar/pod HTTP/MCP interne dédié dépourvu d'interface/egress réseau sortant (`NetworkPolicy` isolée, zéro Podman-in-Pod ni conteneur imbriqué)
**And** aucun log ni fichier d'état n'est écrit sur le système de fichiers du pod.

**Given** les sondes de santé de conteneurs
**When** OpenShift interroge `livenessProbe` (`GET /api/v1/health`) et `readinessProbe` (`GET /ready`)
**Then** les deux sondes répondent en `< 100 ms` sans déclencher de requêtes SQL lourdes ni générer d'entrées d'accès bruyantes dans les logs.

**Given** le composant OpenShift Logging (`ClusterLogForwarder`) déployé sur le cluster cible
**When** les logs émis sur `stdout` par les pods ORCIA sont collectés
**Then** le document de contrat d'intégration plateforme (`OPS-OPENSHIFT-LOGGING-01`) consigne : (1) l'activation de `structuredTypeKey` pour le parsing natif du JSON émis par ORCIA, (2) la création du compte de service / clé d'API restreint en lecture seule à l'index Elasticsearch du namespace ORCIA pour `LogSinkQueryPort`, (3) la politique `NetworkPolicy` d'egress autorisant les flux sortants vers Elasticsearch et le collecteur OTel/Tempo d'entreprise, et (4) le masquage préalable obligatoire des secrets dans le pod avant émission (`NFR-SEC-4`)
**And** les tests de validation de conteneur rootless, la sonde `/ready` et la validation statique Kustomize passent avec succès (`AD-17`, `AD-23`).

### Story 7.1: Contrat d'Autonomie Signé (`autonomy_contracts`), Identité Service-Principal Scopée, Modale Studio V2 & Régime `AUTONOMOUS_CONTRACT`

As a Chef d'Équipe ou Directeur de BU (`Marc UJ-5`, `Claire UJ-8`),
I want déclarer et signer un Contrat d'Autonomie sur un Workflow éligible (`LOW_NON_CRITICAL` ou `STANDARD`) directement depuis **Process Studio V2 (`/processes/studio/$workflowId`)**, lui attacher un `service_principal` existant habilité sur l'Espace dans `iam_accounts` et activer le régime `AUTONOMOUS_CONTRACT`,
So that les processus répétitifs, analytiques (`UJ-11`) ou documentaires (`generate-and-attach-help` dans `packs/orcia-docs/`, classé `LOW_NON_CRITICAL`) puissent s'exécuter de bout en bout sans intervention humaine synchrone et sans goulet bureaucratique `SECOPS`, tout en bloquant formellement toute autonomie non supervisée sur les processus `HIGH_CRITICAL` (`FR-5`, `FR-22`, `FR-29`, `AD-3`, `AD-6`, `AD-18`, `AD-19`, `Principe D.4`).

**Acceptance Criteria:**

**Given** la migration Alembic créant la table dédiée **`autonomy_contracts`** (`UUIDv7`, `workspace_id`, `workflow_def_id`, `workflow_version_sha256`, `service_principal_id` FK `iam_accounts`, `allowed_actions_jsonb`, `allowed_sources_jsonb`, `max_cost_per_run_usd`, `tie_break_policy`, `signed_by_user_id`, `signed_at`, `revoked_at`), élargissant `workflow_runs.status` (`PAUSED_AUTONOMOUS_ESCALATION`, `COMMITTED_AUTONOMOUS`) et les événements Outbox Epic 7 (`AutonomousContractSigned`, `AutonomousEscalated`), et un *Workflow* enregistré dans Process Studio V2
**When** un utilisateur tente d'activer `execution_regime: AUTONOMOUS_CONTRACT` sur un workflow de criticité `HIGH_CRITICAL`
**Then** l'API rejette la requête avec `HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE` (`AD-18`, `FR-29`)
**And** sur un workflow `LOW_NON_CRITICAL` (tel que `packs/orcia-docs/workflows/generate-and-attach-help`) ou `STANDARD`, l'activation requiert une signature unique dans `autonomy_contracts` par un `TEAM_LEAD` ou `BU_LEAD` du périmètre (sans co-signature `SECOPS`, `AD-6`, `AD-18`), sous double garde automatique du moteur : (1) le `SERVICE_PRINCIPAL` doit déjà être actif et habilité sur l'Espace dans `iam_accounts` (provisionné par `PLATFORM_ADMIN`/`SECOPS`), et (2) l'invariant de confinement `Actions autorisées ⊆ Droits(Signataire) ∩ Droits(SERVICE_PRINCIPAL)` est vérifié (`HTTP 403` sinon) et scellé dans `audit_ledger`
**And** la modale `OrciaDialog` **« Contrat d'autonomie »** est intégrée directement dans l'en-tête de `WorkflowFiveBlocksCanvas.tsx` (`/processes/studio/$workflowId`) et le composant orphelin `WorkflowTopGovernanceBar.tsx` est supprimé.

**Given** un *Workflow Run* s'exécutant sous `AUTONOMOUS_CONTRACT` (`UJ-11` ou `generate-and-attach-help`)
**When** toutes les *Gates Déterministes* (`PASS`, y compris `validate_help_article`) et *Gates Agentiques* (`agentic_score >= 0.85`, `fact_verification >= 0.90`, `0` conflit d'ontologie, `0` `[STALE_WARNING]`) sont franchies
**Then** le `PermissionBroker` émet automatiquement un `SignedApprovalToken` strictement scopé aux actions autorisées par le contrat valide pour `OrciaConnectorProtocol.execute_write()`, le Run finalise son livrable et exécute les seules actions autorisées avec le statut `COMMITTED_AUTONOMOUS`
**And** si un seuil de Gate n'est pas atteint, que le contrat est révoqué ou qu'un conflit survient, le Run suspend immédiatement l'action d'écriture et escalade vers l'équipe propriétaire (`PAUSED_AUTONOMOUS_ESCALATION`) via `domain_events_outbox`
**And** l'action passe par le `ConnectorInvoker` (coupe-circuit par connecteur, `idempotency_key`), le `service_principal` est évalué selon le verbe `execute` (`AD-21`) avec uniquement des `SecretRef` résolues par `SecretProviderPort` (`NFR-SEC-4`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest` + `hypothesis`) et d'intégration verticale `HTTP ➔ PostgreSQL 18` (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

### Story 7.2: Déclencheurs Événementiels Idempotents (`WEBHOOK`, `LOG_SINK_ALERT`, `CRON`, `OUTBOX_EVENT`, `MANUAL_AUTONOMOUS`), Déduplication & Protection Anti-Boucle (*Self-Trigger Guard*)

As a Ingénieur Plateforme / SRE ou Directrice de BU (`Karim UJ-9`, `Claire UJ-11`),
I want enregistrer des déclencheurs autonomes planifiés (`CRON`) ou événementiels (`WEBHOOK` mutualisé HMAC, `LOG_SINK_ALERT` via interrogation de `LogSinkQueryPort` livrée en `Story 7.0b`, ou événement interne `OUTBOX_EVENT` pour la génération automatique d'aide en **opt-in explicite** désactivé au Jour 0) depuis la modale **« Déclencheurs »** de Process Studio V2, exécutés par le démon réel `trigger-dispatcher` et dotés d'une clé d'idempotence stricte (`DBOS SetWorkflowID`), d'une fenêtre de cooldown et d'un garde-fou anti-auto-déclenchement,
So that les rapports analytiques périodiques (`UJ-11`), la mise à jour opt-in des fiches d'aide (`Principe D.4`) et la surveillance des erreurs de logs se lancent automatiquement sans jamais créer de doublons lors des ré-essais, sans coût LLM surprise au Jour 0 et sans tempête de boucles infinies (`FR-24`, `FR-26`, `FR-29`, `AD-12`, `AD-18`, `AD-19`, `AD-23`).

**Acceptance Criteria:**

**Given** la Story `7.0b` livrée (`LogSinkQueryPort`, `AD-23`), la migration Alembic ajoutant `'OUTBOX_EVENT'` au `CHECK` de `workflow_triggers.trigger_type`, reliant `workflow_triggers.contract_id` à `autonomy_contracts(id)` et ajoutant le drapeau opt-in `auto_help_on_publish DEFAULT FALSE` + les événements Outbox (`TriggerFired`, `SelfTriggerBlocked`, `TriggerCircuitOpened`), et la modale `OrciaDialog` **« Déclencheurs »** dans `WorkflowFiveBlocksCanvas.tsx` (`/processes/studio/$workflowId`)
**When** deux événements identiques (même `X-Webhook-Delivery-Id`, même `error_fingerprint_sha256` dans `cooldown_window_seconds`, même publication de version `@vX.Y.Z`, ou même fenêtre `CRON`) ou un ré-essai se présentent simultanément
**Then** le démon réel `trigger-dispatcher` (`apps/worker/src/orcia_worker/roles.py`, `AD-19`) et `SqlWorkflowTriggerRepository` orchestrent : pour `LOG_SINK_ALERT`, l'interrogation périodique de `LogSinkQueryPort` (décision D5, `AD-23`, plus webhook de repli `/api/v1/triggers/alerts`) avec calcul de `error_fingerprint_sha256` en Python pur ; pour `WEBHOOK`, la validation HMAC temps-constant et l'anti-rejeu **factorisés avec le socle de `Story 18.2`** (`datasource_webhooks.py`) ; pour `CRON`, la planification `@DBOS.scheduled` ; et pour `OUTBOX_EVENT`, le déclenchement de `generate-and-attach-help` (`packs/orcia-docs/`) uniquement si l'**opt-in explicite** est activé sur l'Espace ou le Processus (désactivé par défaut au Jour 0)
**And** `DBOS SetWorkflowID("<trigger_id>:<idempotency_key>")`, le verrou atomique Redis `SET lock:trigger:{trigger_id}:{idempotency_key} NX EX 86400` et la contrainte PostgreSQL `UNIQUE (trigger_id, trigger_idempotency_key)` garantissent qu'un seul `workflow_run` est créé (`AD-18`).

**Given** un événement Webhook, Outbox ou de puits de logs dont l'émetteur est le `service_principal` d'ORCIA ou qui contient le marqueur `x-orcia-origin-run-id`
**When** le récepteur de triggers inspecte l'événement
**Then** le **Self-Trigger Guard** ignore l'événement et publie la prévention de boucle dans `domain_events_outbox` vers `audit_ledger`
**And** si le déclencheur dépasse `max_runs_per_hour`, `max_daily_cost_usd` ou `max_consecutive_failures` (défaut `3`), son statut passe automatiquement à `CIRCUIT_OPEN` avec alerte SSE `< 500 ms`
**And** les erreurs de connecteur sont classées par la taxonomie `orcia_kernel.errors` : seules les erreurs passagères sont relancées par `ConnectorInvoker`, et les erreurs fonctionnelles incrémentent `max_consecutive_failures` sans relance automatique
**And** `lint-imports` passe à `0` violation, `Vitest` (survie au `F5` de la modale Studio V2), les tests unitaires et d'intégration sous concurrence (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du dispatcher et des routeurs (`AD-17`, `AD-19`, `AD-23`).

> **Note de rebasage (2026-11-17)** : L'ancienne `Story 7.3` (volet « agent codeur / écriture Git / Sandbox TDD applicative / CI-CD externe ») a été retirée du périmètre actif d'ORCIA car ORCIA ne gère ni le code source ni le déploiement des applications représentées dans les Espaces (cf. Epics 14 & 18). Le besoin de boucle fermée sur incidents détectés dans les logs **sans modification de code ni écriture Git** est tracé dans l'action item **`AIOPS-INCIDENT-LOOP-01`** de `docs/implementation-artifacts/sprint-status.yaml`.

### Story 7.4: Supervision UX des Runs Autonomes (`AutonomousExecutionBadge`, `UX-DR17`), Sorties de Secours, Échantillonnage Post-Hoc & Métriques `SM-A1..A3`

As a Directrice de BU, Chef d'Équipe ou Auditeur SecOps (`Claire UJ-8/UJ-11`, `Marc UJ-5`, `Sophie UJ-6`),
I want distinguer visuellement tout run ou fiche d'aide exécuté sans humain (`AutonomousExecutionBadge` Cyan/Cobalt `#0284C7`), consulter ces exécutions regroupées par déclencheur dans le tiroir `Notifications` et sur `/processes`, actionner en 1 clic l'**Arrêt d'urgence** et l'**Annulation / rétablissement de la version précédente** (y compris dans `ShellContextualHelpColumn.tsx` pour les fiches `HELP_ARTICLE`), auditer par échantillonnage post-hoc une fraction des runs autonomes, et suivre les indicateurs `SM-A1..A3` dans l'onglet existant **« Maîtrise humaine & Qualité »** de `/finops` avec une microcopy 100 % métier FR,
So that l'ouverture aux workflows autonomes préserve la lisibilité cognitive du portail (Loi de Hick, 0 nouvel onglet dans `/finops`), la transparence d'audit et le contrôle humain immédiat sans aucun jargon technique dans l'interface (`FR-27`, `FR-29`, `AD-19`, `AD-21`, `AD-22`, `UX-DR17`, `Principe D.4`, `SM-C1`, `SM-C2`, `SM-A1`, `SM-A2`, `SM-A3`).

**Acceptance Criteria:**

**Given** un *Workflow Run* ou un *Artefact* (y compris une fiche `HELP_ARTICLE` affichée dans la Colonne d'aide contextuelle droite `ShellContextualHelpColumn.tsx`) produit sous `AUTONOMOUS_CONTRACT`
**When** il est affiché dans `/processes`, le tiroir `Notifications` ou la Colonne d'aide contextuelle droite
**Then** le composant **`AutonomousExecutionBadge` (`UX-DR17` dans `@orcia/ui`)** est rendu en Cyan/Cobalt via les tokens CSS de `tokens.css` (`#0284C7` / fond `#F0F9FF`, **jamais** en Violet `#6D28D9` réservé à `HumanLedAnchorCard`) avec le libellé métier *« Automatisé sous contrat »* et le nom du déclencheur, les runs nominaux sont regroupés par déclencheur dans un bloc replié du tiroir `Notifications` (seules les escalades, déclencheurs suspendus et tirages de contrôle qualité post-hoc remontant en priorité), et les actions **« Arrêt d'urgence »** (effectif à la prochaine frontière de `@DBOS.step`, `AD-21.5`) et **« Annuler et rétablir la version précédente »** (restaurant instantanément `@v(N-1)` dans `catalog_items` et invalidant le cache Redis `< 10 ms` pour les fiches d'aide) sont immédiatement accessibles sans aucun jargon interne (`Kill-Switch`, `Rollback`, `Service Principal`, `CIRCUIT_OPEN`, `SM-A1..A3` proscrits côté UI).

**Given** l'écran **`Coûts & Activité` (`/finops`)** et son onglet existant **« Maîtrise humaine & Qualité »** (`Story 6.3`)
**When** les indicateurs de gouvernance sont calculés et affichés
**Then** aucun 5ᵉ onglet n'est ajouté à `/finops`, les indicateurs interactifs `SM-C1` et `SM-C2` restent strictement isolés sur les runs interactifs et les Gates Humaines sans être faussés par les runs autonomes, et les 3 indicateurs d'autonomie **`SM-A1` (Taux d'escalade autonome)**, **`SM-A2` (Taux d'annulation / rétablissement post-contrôle, cible $< 1\%$)** et **`SM-A3` (Coût moyen & gain de délai par exécution automatisée)** s'affichent dans **« Maîtrise humaine & Qualité »** (masqués proprement tant qu'il existe `0` exécution autonome) avec alerte visuelle si `SM-A2 >= 1%` et panneau de revue des dossiers tirés au sort (`10–20 %`)
**And** `lint-imports` passe à `0` violation, l'audit zéro-bouton-muet / zéro-jargon et les tests unitaires (`pytest`, `Vitest` avec survie au `F5`), d'intégration (`testcontainers` PG18) et E2E (`Playwright` Desktop + Mobile) couvrent $\ge 90\%$ des composants `UX-DR17`, de l'arrêt d'urgence, du rétablissement `@v(N-1)` et des métriques `SM-A1..A3` (`AD-17`, `AD-19`, `AD-22`).
