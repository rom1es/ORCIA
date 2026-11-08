---
status: final
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - 'docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md'
  - 'docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md'
  - 'docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md'
  - 'docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md'
  - 'docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md'
  - 'docs/planning-artifacts/research/stack-review-2026-10-27.md'
  - 'docs/planning-artifacts/research/modularity-analysis-2026-10-27.md'
  - 'docs/planning-artifacts/research/technical-frontend-spa-nextjs-vs-vite-tanstack-rou-2026-10-27/report.md'
  - 'docs/planning-artifacts/sprint-change-proposal-2026-10-27.md'
  - 'docs/planning-artifacts/research/architecture-decoupling-audit-2026-10-28.md'
  - 'docs/planning-artifacts/sprint-change-proposal-2026-10-30-epic8-and-ux-rework.md'
  - 'docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/draft-ux-principes-et-architecture-2026-10-30.md'
---

# ORCIA - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for ORCIA, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

- **FR-1 (Interface Chat-First + Canvas, Sélecteur de Périmètre Hiérarchique `⌘W`, Menu Global à 7 Modules & Adaptation au Profil Humain)** : Accès par défaut à l'interface hybride *Chat-First + Canvas* où l'*Agent Assistant* adapte dynamiquement son discours, ses indicateurs et sa terminologie au *Profil Humain* connecté (Rôle, BU, Équipe, Habilitations) via l'*Ontologie*, avec en tête de Sidebar un *Sélecteur de Périmètre Hiérarchique (`⌘W` : `🌐 Plateforme Globale [PLATFORM_ADMIN]` $\rightarrow$ `🏢 BU / Tribu [BU_DIRECTOR]` $\rightarrow$ `👥 Équipe / Sous-Équipe [TEAM_LEAD]` $\rightarrow$ `🗂️ Workspace Solution`)* et un *Menu de Navigation Global* filtré par RBAC donnant accès aux 7 modules (*1. Cockpit & Chat*, *2. Boîte & Mes Runs*, *3. Catalogue Fédéré*, *4. Ontologie & KB*, *5. Gates & Habilitations*, *6. FinOps & Audit*, *7. Administration & Pilotage des Workspaces `/workspaces`*).
- **FR-2 (Centre de Notifications Unifié Individuel/Équipe avec Claim & Présence Temps Réel)** : Boîte de réception unifiée centralisant les notifications personnelles et d'équipe (validation d'artefact à une *Gate Humaine*, *Arbitrage Humain* IA, question/challenge humain, alerte d'habilitation ou d'obsolescence), avec prise en charge atomique (*Claim*) et verrou de présence diffusé en `< 500 ms` via SSE empêchant les validations concurrentes contradictoires.
- **FR-3 (Supervision Multi-Workflows Dynamique, Centre de Pilotage Unifié Multi-Niveaux des Workspaces à 4 Onglets & Séparation Consultation Seule vs Contributeur)** : Suivi simultané en temps réel de multiples *Workflow Runs* et bascule instantanée (`< 1 s`) selon deux modes stricts déterminés par le *Profil Humain* : *Consultation seule (`READ_ONLY_OBSERVER`)* (toute mutation désactivée côté UI et rejetée en `HTTP 403` côté API) ou *Contributeur / Valideur (`CONTRIBUTOR_ACTION_REQUIRED`)*, complété par l'écran **Centre de Pilotage Unifié des Workspaces & de l'Organisation (`/workspaces` & `/workspaces/[workspaceId]`)** structuré en **4 onglets fractals** (*1. Instances de Workflow Runs & Artefacts*, *2. Sources Dédiées & Partagées [`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`]*, *3. Workflows, Agents & Surcharges 4 niveaux*, *4. Équipes, Membres & Gouvernance*) offrant une agrégation *Roll-up* et un *Drill-down* à chaque échelle (`PLATFORM_ADMIN` sur toute la plateforme avec télémétrie technique/FinOps sur les espaces `CONFIDENTIAL_RESTRICTED` sans exposer leurs payloads métiers, `BU_DIRECTOR` sur sa BU/Tribu, `TEAM_LEAD` sur ses équipes/solutions, et Contributeur sur son Workspace).
- **FR-4 (Ancrages Humains Obligatoires — Human-Led Anchors)** : Possibilité de marquer dans un *Workflow* ou un *Gabarit d'Artefact* des sections critiques comme `human_authored_required: true` que l'agent IA a l'interdiction formelle de pré-remplir (rejet API `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED` sans signature humaine `human_anchor_signatures`), basculant l'agent en accompagnement socratique si l'utilisateur tente de déléguer la rédaction.
- **FR-5 (Arbitrage Humain Systématique sur Options Équivalentes — No Silent Arbitrary Choice)** : Obligation pour tout *Agent Exécuteur* rencontrant $\ge 2$ options techniques, fonctionnelles ou métier équivalentes non départagées par l'*Ontologie*, la *KB* ou les *Ancrages Humains* de suspendre l'étape en `WAITING_FOR_HUMAN_ARBITRATION` (`request_human_arbitration(options_matrix)`), de notifier l'humain et de présenter une matrice comparative structurée (avantages, inconvénients, impacts SI/FinOps) avant de poursuivre.
- **FR-6 (Briefing de Revue en 4 Blocs & Validation par Découpage des Artefacts Volumineux)** : Affichage automatique pour tout artefact soumis à une *Gate Humaine* ou dépassant `> 1 500 mots` / `> 3 sections` d'un *Briefing de Revue* structuré en 4 blocs obligatoires (*1. Résumé exécutif*, *2. Éléments clés & Contrôle transverse*, *3. Décisions prises*, *4. Hypothèses retenues*) et d'un mode de *Validation par Découpage* (`chunk_approvals`) permettant d'approuver, co-éditer, commenter ou régénérer chaque section indépendamment.
- **FR-7 (Challenge Amont Inter-Steps, Simulation d'Impact What-If & Boucle de Rétroaction)** : Capacité pour un acteur aval (ex. Architecte au Step 2 ou Tech Lead au Step 3) d'émettre un challenge formel sur une règle ou section d'un *Artefact* amont, avec calcul et prévisualisation immédiate du graphe d'impact (*What-If Impact Preview* via `ImpactSimulatorService` sur les Steps aval, sections du *Blackboard* et axiomes d'*Ontologie*), traduction dans le vocabulaire du profil amont, révision versionnée (`v1.1`) et déclenchement d'un *Replay* ciblé (`FR-16`).
- **FR-8 (Structuration de l'Ontologie en 4 Niveaux incluant Arbre d'Équipes `3_TEAM` & Solution `3_WORKSPACE` avec Héritage & Alignement)** : Gestion d'une *Ontologie* hiérarchisée en 4 strates (*1. Entreprise* $\rightarrow$ *2. Domaine/BU* $\rightarrow$ *3. Niveau 3A : Équipe hiérarchique `3_TEAM` (`Équipe Parente -> Sous-Équipe`) & Niveau 3B : Solution logicielle `3_WORKSPACE`* $\rightarrow$ *4. Éphémère/Run*) avec héritage descendant, mapping de synonymes par métier et résolution versionnée des niveaux 1 à 3 depuis le *Catalogue Fédéré*.
- **FR-9 (Extraction Ontologique Temps Réel, Simulation d'Impact & Promotion Gouvernée)** : Détection en cours de conversation ou d'analyse KB des nouveaux concepts, synonymes ou conflits sémantiques, inscription immédiate au *Niveau 4 (Run)* (isolée sur la branche de snapshots `ACTIVE`), simulation d'impact (*What-If*) avant promotion ou modification aux niveaux supérieurs, et workflow de promotion gouvernée vers les *Niveaux 3 (`3_WORKSPACE` ou `3_TEAM`), 2 et 1*.
- **FR-10 (Triple Exécution Active de l'Ontologie)** : Application active de l'*Ontologie* lors de chaque *Workflow Run* sur 3 plans : (1) validation du typage des objets du *Blackboard* et des *Gabarits d'Artefact*, (2) traduction du vocabulaire par l'*Agent Assistant* selon le *Profil Humain*, et (3) expansion des requêtes RAG et vérification des axiomes aux *Gates Déterministes* et *Agentiques*.
- **FR-11 (Définition Déclarative Workflow-as-Code YAML/JSON & Composition Assistée par l'Agent Assistant)** : Définition et validation par schéma de *Workflows* déclaratifs YAML/JSON, ainsi que composition, modification conversationnelle et prévisualisation graphique dans le *Canvas* de nouveaux *Workflows* par l'*Agent Assistant* à partir des briques du *Catalogue Fédéré*, avec enregistrement en portée `DRAFT`/`WORKSPACE` et exécution interactive ou en tâche de fond (`UJ-10`).
- **FR-12 (Gabarits d'Artefact Multi-Audience Humain vs Agent)** : Support de *Gabarits d'Artefact* bi-faces combinant une structure documentaire Markdown (sections obligatoires, variables Jinja/Mustache, ancres humaines, découpage `FR-6`) pour l'humain et un schéma formel (JSON Schema / YAML Schema typé par l'*Ontologie*) sérialisé dans le *Blackboard* pour les étapes aval.
- **FR-13 (Garantie de la Discipline Intention -> Code)** : Obligation dans tout workflow d'ingénierie logicielle nominal que toute modification de code soit précédée d'une intention validée ou de la mise à jour de l'artefact de spécification/architecture amont et vérifiée par une *Gate* de conformité Doc/Code ; cantonnement des flux de rétro-documentation (`Code -> Doc`) au mode explicite `brownfield_bootstrap`.
- **FR-14 (Orchestration Hybride Multi-LLM Agnostique, Exécution Bimodale & Blackboard Filtré)** : Exécution séquentielle, parallèle ou conditionnelle des *Steps* via un routeur Multi-LLM agnostique (OpenAI, Anthropic, Gemini, Ollama, vLLM), hydratation *Just-In-Time* n'injectant dans chaque *Step* que ses `inputs` déclarés depuis le *Blackboard*, et support bimodal : *Mode Coaching* (interactif) vs *Mode Fast-Path / Tâche de Fond (`BACKGROUND_AUDIT`)* accumulant les marqueurs `[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]` et `[DOC_OBSOLETE_SUSPECTED]` dans `step_memlog_jsonb` pour arbitrage groupé en fin de run (`UJ-10`).
- **FR-15 (Version Pinning Immuable des Workflow Runs — `run-lock.json`)** : Verrouillage au démarrage de chaque *Workflow Run* dans `run-lock.json` des versions exactes et empreintes `SHA-256` du *Workflow*, des surcharges à 4 niveaux, des *Agents*, des *Skills*, des *Gabarits*, de l'*Ontologie* et du snapshot des *Bases de Connaissances*, garantissant une reprise identique même après plusieurs semaines de pause.
- **FR-16 (Replay Ciblé à partir du Step N — Time-Travel Execution)** : Relance d'un *Workflow Run* à partir d'un *Step* $N$ précis en réutilisant le snapshot validé du *Blackboard* à l'étape $N-1$ (0 token reconsommé sur les étapes $1..N-1$), en créant une nouvelle branche `ACTIVE` de snapshots et en marquant l'ancienne branche aval comme `SUPERSEDED`.
- **FR-17 (Gates Déterministes en Sandbox, Conformité Gabarit/Ontologie & Anti-Pattern Drift)** : Exécution automatisée dans une *Sandbox* isolée (`< 5s`, sans réseau) de la validation de schéma du *Gabarit d'Artefact*, des axiomes d'*Ontologie*, des linters/compilateurs/tests et des règles d'analyse statique détectant le *Pattern Drift* vis-à-vis de `ARCHITECTURE-SPINE.md`.
- **FR-18 (Gates Agentiques avec Orthogonalité des Modèles, Lentille `fact_verification` & Contrôle Transverse)** : Audit d'un artefact par un *Agent Évaluateur* opérant obligatoirement sur une famille de modèle distincte de l'*Agent Exécuteur* (`evaluator_model_family != executor_model_family`) et sans accès à sa *Chain-ofThought*, organisé en DAG de 4 lentilles parallèles (*Alignement Transverse Étape 1*, *Vérification Atomique de Faits `fact_verification` avec score de confiance `0..1`*, *Attaque Adversariale & Edge-Cases*, *Conformité Métier/Sécurité*) suivies d'une lentille de synthèse générant le *Briefing de Revue en 4 blocs*.
- **FR-19 (Gates Humaines à Politique Adaptative & Garde-fou Anti-Rubber-Stamping)** : Support de 3 politiques par *Gate Humaine* (`mandatory_full`, `risk_or_exception_based` si `agentic_score >= 0.85` et `0` anomalie, et `sampling` à `20%`) et déclenchement d'une modale de confirmation active (`fast_approval_warning: true`) si un valideur approuve un artefact volumineux en `< 15 secondes` sans inspecter le *Briefing de Revue* ni les sections découpées.
- **FR-20 (Résolution Fédérée à la Volée `db://`, `git://`, `nexus://`, `confluence://`, `jira://`, `orcia://`, Surcharges à 4 Niveaux `Base -> Team -> Workspace -> User` & Cache CAS `SHA-256`)** : Enregistrement des seules URI canoniques et métadonnées dans le *Catalogue Fédéré*, résolution à la volée via les connecteurs dédiés (`db://`, `git://`, `nexus://`, `confluence://<space_key>/<page_id>@v<N>`, `jira://<project_key>/<issue_key>`, et `orcia://` inter-étapes), stockage dans le cache content-addressable MinIO/S3 (`cas/<sha256>`), support des surcharges déclaratives à 4 niveaux (`1. Base -> 2. Standards d'Équipe TEAM hiérarchique -> 3. Solution WORKSPACE -> 4. Utilisateur USER`) et import natif de packs BMAD (`BmadSkillPackAdapter`).
- **FR-21 (Authentification Hybride Bi-Mode, Arbre d'Équipes `OrgUnit` découplé des Espaces Solutions `Workspaces`, Rôle `TEAM_LEAD` & 5 Permissions Dissociées du Catalogue)** : Authentification primaire bi-mode (**SSO d'Entreprise `OIDC / OAuth 2.1`** ET **Authentification Locale autonome `Email + Argon2id + MFA TOTP optionnel`** avec liens d'invitation signés, sur sessions JWT `15 min` + Refresh Token `HttpOnly` révocable en Redis), modélisation RBAC/ABAC sur 3 axes : (1) Arbre hiérarchique d'équipes `org_units` à $N$ niveaux (`Entreprise -> BU -> Tribu/Équipe Parente -> Sous-Équipe`), (2) Groupes transverses, et (3) *Workspaces* représentant chacun **une solution logicielle** (avec ses sources `git://`, `jira://`, `confluence://`, son `ARCHITECTURE-SPINE.md` et ses artefacts isolés, où une même équipe peut gérer plusieurs *Workspaces* et où les équipes parentes disposent d'une visibilité ascendante *Roll-up* en `READ_ONLY_OBSERVER` sauf mode `CONFIDENTIAL_RESTRICTED`), pilotés par un **Chef d'Équipe (`TEAM_LEAD` / `Workspace Admin`)**, et séparation des 5 permissions sur chaque actif du catalogue (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) à travers un cycle de publication hiérarchique (`DRAFT` $\rightarrow$ `SHARED_WORKSPACE` $\rightarrow$ `SHARED_TEAM` $\rightarrow$ `SHARED_BU` $\rightarrow$ `PENDING_APPROVAL` $\rightarrow$ `PUBLISHED_ORG`).
- **FR-22 (Exécution Passthrough / Service Principal & Permission Broker IA connecté à Jira)** : Exécution par défaut avec l'identité déléguée de l'utilisateur déclencheur (*Passthrough* OIDC/OAuth 2.0 3LO/PAT chiffré AES-256-GCM dans le coffre d'identité utilisateur) ou via un *Service Principal* explicitement autorisé ; interception de tout refus d'accès (`HTTP 401/403`, y compris restrictions Confluence ou rôles de transition Jira manquants) par le `PermissionBrokerService` qui interroge la KB des procédures d'habilitation (YAML/Markdown), met l'étape en pause `WAITING_FOR_PERMISSION` et fournit le rôle requis, l'approbateur et le lien pré-rempli de demande d'accès dans *Jira*.
- **FR-23 (Indexation Différenciée Incrémentale, Graphe Tripartite `Confluence ↔ Jira ↔ Git`, Brique `data-freshness` & Alerte `[STALE_WARNING]`)** : Indexation incrémentale en vecteurs `halfvec(1024)` (`pgvector` HNSW + BM25 `tsvector` fusionnés par RRF) selon 3 régimes : (1) *Parent-Child* (`256-512` tokens enfant avec *Contextual Header* $\rightarrow$ `1024-2048` tokens parent) pour *Confluence* (`confluence://` filtré par espace/labels), la documentation Markdown/PDF/OpenAPI (`Docling`) et les tickets *Jira* de référence (`jira://` filtré par JQL sur Epics, Stories, Bugs résolus et Post-mortems), (2) découpage syntaxique par symbole AST (`150-800` tokens via `tree-sitter`) + *Code Property Graph* pour `git://`, reliés au sein d'un *Graphe Tripartite de Traçabilité (`Confluence DOCUMENTS ↔ Jira SPECIFIES/FIXES ↔ Git IMPLEMENTS_ISSUE`)*, et (3) schéma DDL + mapping ontologique uniquement pour `db://` ; contrôle de fraîcheur (`data-freshness`) et levée d'une alerte `[STALE_WARNING]` en cas de dépassement de `freshness_ttl_days` ou de contradiction avec un ticket Jira plus récent ou le code.
- **FR-24 (Actions & Transitions Jira Staged aux Gates, Exécution de Skills en Sandbox & MCP Bidirectionnel Client + Serveur IDE)** : Capacité pour un *Step* ou une *Gate* de : (1) interroger Jira en direct via JQL et préparer les créations (`create_issue`), modifications (`update_issue`, `add_comment`) et transitions de workflows Jira (`transition_issue` après vérification de `GET /rest/api/3/issue/{key}/transitions`) comme *Actions Staged* dans le brouillon de l'étape, exécutées sur Jira uniquement après validation de la *Gate* avec lien `run-lock.json`, tout en recevant les Webhooks `jira:issue_updated` pour déclencher ou réveiller un *Run* en pause ; (2) exécuter des *Skills* en *Sandbox* isolée ; et (3) exposer le *Serveur MCP gouverné d'ORCIA (`/api/v1/mcp`)* aux IDE externes (VS Code, Cursor, Claude Code, Antigravity) en mode *Passthrough*.
- **FR-25 (Provenance Auditable Immuable par Step et par Gate)** : Enregistrement synchrone dans le registre append-only `audit_ledger` (protégé contre `UPDATE`/`DELETE` par trigger PostgreSQL) pour chaque *Step* et *Gate* des URI/hashes `SHA-256` (`run-lock.json`), du modèle LLM et de ses paramètres, du prompt assemblé, des chunks KB injectés, des appels Skills/MCP/mutations Jira, des coûts/tokens, des signatures humaines et des durées de revue, avec export d'audit JSON/Markdown.
- **FR-26 (Comptabilité FinOps Complète Setup + Run vs TTM & Coupe-Circuits Budgétaires)** : Comptabilisation en temps réel des tokens/coûts d'inférence LLM et du temps humain (Setup + Run) par *Step*, *Run*, *Workflow* et *Équipe/BU* comparés au gain de Time-to-Market, avec coupe-circuits automatiques suspendant l'exécution en `PAUSED_BUDGET_EXCEEDED` (`max_cost_usd`) ou `PAUSED_MAX_RETRIES` (`max_agent_retries`, défaut `3`).
- **FR-27 (Indicateurs d'Impact Cognitif, Anti-Rubber-Stamping & Indice de Réversibilité Humaine)** : Calcul et exposition dans le tableau de bord de gouvernance des 3 contre-métriques : (1) *Ratio Cadrage Actif (`Human-Led Anchors` + `Arbitrages`) vs Simple Relecture* (cible $\ge 40\%$), (2) *Taux de Rubber-Stamping aux Gates Humaines* (cible $< 5\%$), et (3) *Indice de Pattern Drift / Réversibilité Humaine* (cible $0\%$ de dérive non approuvée), avec recommandations automatiques d'ajustement des politiques de *Gates*.
- **FR-28 (Workflows Système d'Initialisation, Onboarding Autonome d'Équipe & Multi-Workspaces `TEAM_LEAD` & Auto-Amorçage Gouverné — `orcia://system/bootstrap/*`)** : Embarquement natif de 6 workflows système guidés par l'*Agent Assistant* et verrouillés par des *Gates Déterministes* : `init-organization` (SSO OIDC / Auth locale + RBAC, test d'au moins 2 familles de modèles orthogonales, amorçage Ontologie N1), `init-workspace` (onboarding autonome de l'équipe/sous-équipes et création d'un ou plusieurs *Workspaces* de solutions logicielles par le **Chef d'Équipe `TEAM_LEAD`**, invitation des membres avec pré-affectation du *Profil Humain* et des rôles d'exécution, Inbox, surcharges `TEAM` et `WORKSPACE`, Ontologie `3_TEAM` et `3_WORKSPACE`), `init-datasource` (enrôlement par un Admin ou par le **Chef d'Équipe** dans un *Workspace* ou en portée `SHARED_TEAM` de sources `db://`, `git://`, `nexus://`, `confluence://`, `jira://` ou KB avec signature obligatoire de la fiche *Permission Broker* et de `freshness_ttl_days`), `init-existing-project` (scan brownfield vers `ARCHITECTURE-SPINE.md`), `init-skill` (certification en Sandbox `< 5s`), et `init-user` (confirmation du *Profil Humain* pré-assigné et liaison des comptes Jira/Confluence/Git en mode *Passthrough* au 1er login).
- **FR-29 (Exécution Autonome sous Contrat, Déclencheurs Événementiels Idempotents [Webhooks, Puits de Logs, Cron], Vérification Post-Action en Boucle Fermée & Audit Post-Hoc — `AD-18`, `UJ-11`, `UJ-12`)** : Classification des *Workflows* par criticité (`LOW_NON_CRITICAL`, `STANDARD`, `HIGH_CRITICAL`, avec interdiction d'autonomie de bout en bout sur `HIGH_CRITICAL`), signature préalable obligatoire d'un **Contrat d'Autonomie** dans `human_anchor_signatures`, déclenchement idempotent (`UNIQUE (trigger_id, trigger_idempotency_key)` + verrou Redis + *Self-Trigger Guard*) selon 4 modes (`MANUAL_AUTONOMOUS`, `WEBHOOK`, `LOG_SINK_ALERT`, `CRON`), boucle fermée d'auto-remédiation (`UJ-12` : diagnostic `root_cause_confidence >= 0.90`, intention de remédiation, reproduction/correction TDD en Sandbox, test staging prod-like, déploiement et étape obligatoire `POST_ACTION_VERIFICATION` déclenchant un **Rollback automatique** et l'ouverture du coupe-circuit `CIRCUIT_OPEN` si l'erreur persiste), et tirage aléatoire d'audit humain *a posteriori* (`POST_HOC_AUDIT_SAMPLE`).
- **FR-30 (Imbrication Fractale de Workflows — `Sub-Workflows` & `Workflow-as-Agent`, Profondeur $\le 3$ — `AD-2`, `AD-5`, `AD-12`, `AD-18`)** : Capacité d'invoquer un *Workflow* du Catalogue comme une étape `step_type: SUB_WORKFLOW` ou comme un agent composite (`parent_run_id`, `parent_step_execution_id`, `root_run_id`, `nesting_depth <= 3` sans cycle), avec épinglage récursif dans `run-lock.json` (`sub_workflow_locks`), isolation lexicale du *Blackboard* enfant (`input_mapping` / `output_mapping`), budget FinOps partagé sur `root_run_id` et *Replay* ciblé intra-sous-workflow.

### NonFunctional Requirements

- **NFR-SEC-1 (Isolation Stricte de la Sandbox Déterministe — `AD-9`)** : Toute exécution de script d'un *Skill* ou d'une *Gate Déterministe* s'exécutent dans un worker isolé sans accès réseau (`bubblewrap --unshare-net --ro-bind` sous Linux ou runtime WebAssembly **Wasmtime 27.0**), sans privilèges root, avec un timeout matériel de `5 000 ms`, un plafond mémoire de `256 MB` et un système de fichiers éphémère en lecture seule (hors `/tmp` mémoire de `64 MB`).
- **NFR-SEC-2 (Souveraineté, Classification Ontologique & Pseudonymisation PII Réversible — `AD-10`)** : Le `ModelRouterService` interdit l'envoi vers des APIs Cloud externes de données classifiées sensibles par l'*Ontologie* (routage forcé vers Ollama/vLLM local) et applique à la volée le filtre `PiiReversibleScrubber` (`anonymize_pii_reversible: true`) remplaçant les données personnelles ou secrets métiers par des jetons déterministes stockés en Redis sur la durée du `run_id` et ré-hydratés localement au retour.
- **NFR-SEC-3 (Immuabilité Cryptographique de la Provenance & des Snapshots — `AD-2`, `AD-12`)** : Les tables `audit_ledger` et `blackboard_snapshots` sont strictement *Append-Only* (protégées par trigger PostgreSQL `BEFORE UPDATE OR DELETE RAISE EXCEPTION`), horodatées en UTC ISO-8601 et chaînées par empreintes `SHA-256`.
- **NFR-SEC-4 (Protection des Secrets et Jetons Fédérés — `AD-6`, `AD-12` ; étendue par l'Avenant A2 du 28/10/2026)** : Les jetons personnels (PAT Git, Nexus, Confluence, Jira) en mode *Passthrough* sont chiffrés au repos en **AES-256-GCM** avec une clé dérivée par utilisateur (KMS/Vault) et déchiffrés uniquement en mémoire dans le worker le temps de la résolution ; **aucun secret** n'apparaît dans les tables (`dbos.*`, `audit_ledger`, `domain_events_outbox`, `step_executions`) ni dans les logs (**test du secret témoin** en CI) ; les secrets ne circulent que sous forme de `SecretRef` non sérialisable résolue par `SecretProviderPort` ; aucune valeur par défaut de secret écrite en dur. *Traçabilité : `Story 1.2` (chiffrement Passthrough, livré), `Story 3.2f` (`ConnectorInvoker` sans secret sérialisé), `Story 4.2` + `DEC-SEC-01` / `SEC-03` (secret témoin, masquage structlog).*
- **NFR-PERF-1 (Réactivité Conversationnelle & Bascule Multi-Runs)** : Affichage du premier token de réponse de l'*Agent Assistant* en `< 1,5 s` et bascule entre deux *Workflow Runs* depuis le *Centre de Notifications* en `< 1 s`.
- **NFR-PERF-2 (Latence Temps Réel SSE des Verrous de Présence — `AD-4`)** : L'acquisition d'un verrou d'étape (`SET lock:step:<step_execution_id> <user_id> NX EX 900`) et la diffusion de l'événement SSE `task.claim.locked` ou d'un Webhook Jira entrant à tous les clients connectés s'effectuent en `< 500 ms`.
- **NFR-PERF-3 (Performance du Cache Fédéré CAS & Recherche RAG Hybride — `AD-5`, `AD-8`)** : Résolution d'une ressource déjà présente dans le cache CAS `SHA-256` en `< 50 ms`, résolution CTE de l'Ontologie à 4 niveaux en `< 15 ms` (jusqu'à $10^6$ concepts), et recherche RAG hybride `pgvector halfvec(1024)` HNSW + BM25 `tsvector` en `< 50 ms`.
- **NFR-REL-1 (Persistance Durable des Workflows Longs — `AD-2`)** : Persistance transactionnelle complète de chaque transition d'étape, brouillon (`draft_artifact_jsonb`), memlog (`step_memlog_jsonb`) et snapshot dans PostgreSQL 18, permettant à un *Workflow Run* de rester en pause pendant plusieurs semaines et de survivre à un redémarrage complet des services sans perte d'état.
- **NFR-OBS-1 (Observabilité Structurée & Traçabilité OpenTelemetry)** : Journalisation structurée JSON (`structlog 25.1` côté Python, `pino 9.6` côté Node.js) propageant un `trace_id` W3C OpenTelemetry commun, `workspace_id`, `run_id` et `step_id` à travers FastAPI, SSE, Dramatiq, LiteLLM et la Sandbox, et enveloppe d'erreur normalisée **RFC 9457 Problem Details**.
- **NFR-A11Y-1 (Accessibilité WCAG 2.2 AA & Signalétique Multi-Modale)** : Conformité WCAG 2.2 AA sur l'ensemble des surfaces ; aucun état critique (*Ancrage Humain*, *Arbitrage*, *Gate*, `[STALE_WARNING]`) ne repose sur la couleur seule (combinaison obligatoire Couleur sémantique + Icône + Libellé explicite + annonces `aria-live="polite"`).
- **NFR-TEST-1 (Stratégie de Tests à 5 Couches & Couverture Unitaire $\ge 90\%$ — `AD-17`)** : Toute Story doit livrer ses tests selon les 5 couches obligatoires : (1) Tests unitaires de la plateforme (`pytest 9.0` + `hypothesis 6.135` et `Vitest 3.2` + `Testing Library` + vérification `import-linter 2.7` / `lint-imports` à `0` violation, exécution `< 5s` sans réseau, couverture minimale $\ge 90\%$ sur `packages/orcia-kernel` et `packages/orcia-core`), (2) Tests d'intégration sur vrais conteneurs éphémères via `testcontainers-python 4.10` (PostgreSQL 18 + `pgvector`, Redis 7.4, SeaweedFS 4.17 — zéro mock SQLite/Redis), (3) Tests de contrat OpenAPI 3.1 (`openapi-typescript` 0-diff depuis `apps/api/src/orcia_api/schemas/` + fuzzing `Schemathesis 3.39`), (4) Tests d'orchestration IA par cassettes déterministes `DeterministicCassetteLLM` en CI (`0 $`) et `orcia-evals` en pré-release, et (5) Tests E2E multi-acteurs et multi-device (`@playwright/test 1.52` sur Desktop `1440x900` et Mobile Companion `390x844`).
- **NFR-EXT-1 (Ajout d'un Connecteur sans Modifier le Core — `AD-5`, `AD-20` ; Avenant A2)** : Un nouveau connecteur de source ou d'action (ex. `sap://`) s'ajoute **sans modifier aucun fichier du Core**, en **< 150 lignes** (hors tests) et en **< ½ journée**, via le registre `orcia.connectors`, et passe le kit de conformité `ConnectorPort`. *Traçabilité : `Story 3.2e` (AC connecteur factice `sap://`), `Story 4.4` (Jira = adaptateur `ConnectorPort`).*
- **NFR-ISO-1 (Core Exécutable sans le Pack SDLC — `AD-19`, `AD-20` ; Avenant A2)** : Le Core s'exécute **sans le pack `orcia-pack-sdlc`** : le workflow Finance « Rapprochement de factures » avec un connecteur ERP factice s'exécute de bout en bout en CI avec le pack SDLC désinstallé (job `core-without-sdlc`). *Traçabilité : `Story 3.2e` (contrat `import-linter`, grep vocabulaire = 0), `Story 3.2f` (job `core-without-sdlc`, critère d'acceptation de l'Epic 3).*

### Additional Requirements

- **AR-1 (Starter / Greenfield Monorepo Hybride TypeScript + Python — `AD-1`, `AD-19`)** : Initialisation et structuration d'un monorepo hybride orchestré par **`pnpm 10.6.0` + `Turborepo 2.4.4`** (côté TypeScript/Node.js `24.0.0`) et **`uv 0.13.5` workspace à 4 packages** (côté Python `3.12.9`, `Q1: 1A`), comprenant `apps/web` (SPA pure **`Vite 6.4.1` + `TanStack Router 1.166.2`**, React `19.1.0`, Tailwind CSS `4.3.0`, `TanStack Query 5.90.0`, `@xyflow/react 12.12.0`, `OQ-02`), `apps/api` (FastAPI `0.136.0` portant ses propres schémas `orcia_api/schemas/`), `apps/worker` (moteur durable `DBOS Transact 2.14.0` + `Dramatiq 2.1.0`), `packages/orcia-kernel` (noyau partagé minimal : `ids.py`, `enums.py`, `errors.py`, `events.py`, `ports.py`), `packages/orcia-core` (noyau hexagonal modulaire à domaines bornés indépendants), `packages/ui` (`@orcia/ui` isolé) et `packages/api-client` (SDK généré automatiquement depuis Pydantic v2 / OpenAPI 3.1 via `openapi-typescript 7.13.0` + `openapi-fetch 0.17.0`).
- **AR-2 (Infrastructure Conteneurisée Unifiée & Schéma Relationnel-Graphe/Vecteur — `Structural Seed`)** : Configuration Docker Compose (`infra/docker/`) provisionnant **PostgreSQL `18.0` + `pgvector 0.8.7`**, **Redis `7.4.2`** (files Dramatiq, verrous atomiques `SET NX EX 900` et Pub/Sub SSE) et **SeaweedFS `4.17` (`Apache-2.0`, `OQ-03`)** (stockage CAS immuable `cas/<sha256>` derrière `ObjectStoragePort`), avec migrations **SQLAlchemy `2.1.0` (Asyncio) + Alembic `1.15.1`** implémentant les 18 tables du Core ERD (dont `domain_events_outbox`, schéma PostgreSQL `public` unique avec préfixes de domaine, `Q4: 4A`) à clés primaires **UUIDv7** (`uuid-utils 0.10.0`).
- **AR-3 (Séparation Stricte Brouillon / Snapshot Immuable & Step Memlog — `AD-2`, `AD-13`)** : Stockage transitoire des artefacts en cours d'exécution/évaluation dans `step_executions.draft_artifact_jsonb` (et des raisonnements/hypothèses intermédiaires ou marqueurs `[ASSUMPTION]` dans `step_executions.step_memlog_jsonb`), et écriture dans `blackboard_snapshots` uniquement au statut `COMMITTED` avec gestion des branches `ACTIVE` vs `SUPERSEDED`.
- **AR-4 (Architecture de l'Agent Assistant en Workflow de Nœuds type n8n & `AssistantHarness` à 5 Couches — `AD-15`)** : Implémentation de l'*Agent Assistant* comme un DAG système de 5 nœuds orientés (`orcia://system/workflows/assistant-agent` : *1. Routeur d'Intention $\rightarrow$ 2. Query Planner & Expansion Ontologique $\rightarrow$ 3. Fan-Out Parallèle [RAG, Catalogue, Blackboard, Permission Broker] $\rightarrow$ 4. Tri Critique & Vérification d'Axiomes $\rightarrow$ 5. Synthétiseur Adaptatif au Profil Humain*), visualisable/éditable via **`@xyflow/react 12.12.0`** ou YAML, et exécuté dans le `AssistantHarness` assemblant 5 couches de prompt dont la Couche 1 (Constitution Immuable) interdit toute écriture sur une *Ancre Humaine* ou validation de *Gate* à la place de l'humain.
- **AR-5 (Découplage Arbre d'Équipes / Workspaces Solutions, Surcharge Déclarative à 4 Niveaux & Adaptateur Natif de Packs BMAD — `AD-14`)** : Implémentation dans `packages/orcia-core/catalog` du moteur de fusion déterministe à 4 niveaux (`1. Base URI Catalogue -> 2. Standards d'Équipe TEAM hiérarchique -> 3. Solution WORKSPACE -> 4. Préférences Profil Utilisateur USER`, table `workspace_customization_overrides`) et du `BmadSkillPackAdapter` permettant d'importer et d'exécuter nativement les skills BMAD (`SKILL.md`, `customize.toml`, `steps/*.md`).
- **AR-6 (Pipeline d'Indexation Différenciée Docling + Tree-Sitter, BM25 `tsvector` + RRF & Graphe Tripartite Borné — `AD-8`, `P7`)** : Intégration de **`Docling 2.91.0`** (isolé dans le rôle `worker-indexing` via l'extra `orcia-worker[indexing]`) pour le parsing hiérarchique *Parent-Child* des documents et pages Confluence (`confluence://`), du connecteur **Jira REST API v3 (`jira://`)**, et de **`tree-sitter 0.24.0`** pour le découpage AST et l'extraction du *Code Property Graph* sur `git://`, alimentant le *Graphe Tripartite `Confluence ↔ Jira ↔ Git`* (traversée CTE bornée à `depth <= 2`) et la recherche hybride `pgvector halfvec(1024)` HNSW + PostgreSQL 18 `tsvector` GIN (`ts_rank_cd` pondéré `A/B/C/D`) fusionnée par RRF (`k=60`).
- **AR-7 (Serveur MCP Sortant/Entrant Gouverné `/api/v1/mcp` — `AD-6`)** : Exposition dans `apps/api` du endpoint MCP `/api/v1/mcp` permettant aux IDE externes (VS Code, Cursor, Claude Code, Antigravity) d'interroger l'*Ontologie*, la *KB*, le *Catalogue* et le *Blackboard* en mode *Passthrough* sous contrôle du `PermissionBrokerService` et du garde-fou `AD-3`.
- **AR-8 (Architecture en Monolithe Modulaire, Bus d'Événements Outbox & Plugins — `AD-19`, `M1..M11`, `Q1..Q5`)** : Application stricte du graphe de dépendances unidirectionnel vérifié par `import-linter 2.7` (`orcia_kernel` $\leftarrow$ domaines indépendants de `orcia_core` $\leftarrow$ `orcia_api` / `orcia_worker`), encapsulation de `_internal/` par domaine (`Q4: 4A`), erreurs métier dans `<domaine>/errors.py` héritant de `orcia_kernel.errors.OrciaDomainError`, schémas HTTP dans `apps/api/src/orcia_api/schemas/`, découplage des effets secondaires inter-domaines non bloquants via la table Outbox transactionnelle `domain_events_outbox` (`Q2: 2A`), modèle d'extension hybride (`entry_points` Python en processus + MCP/sous-processus hors processus pour `sandbox-runner`, `Q3: 3A`), 5 rôles de déploiement (`api`, `worker-orchestration`, `worker-indexing`, `trigger-dispatcher`, `sandbox-runner`), et organisation frontend par fonctionnalité `apps/web/src/features/<domaine>/` (`M11`).

### UX Design Requirements

- **UX-DR1 (Système de Design Tokens Direction C & Double Polarité — `DESIGN.md`)** : Implémenter dans Tailwind CSS v4 et CSS Variables la palette sémantique stricte de la Direction C : Sidebar Sombre permanente (`#0F172A`, texte `#F8FAFC`, muet `#94A3B8`, bordure `#1E293B`), Espace Central Haut-Contraste Clair (`#F8FAFC` / `#FFFFFF`, commutable en Dark Slate `#0B0F17`), Dock IA (`#F1F5F9`), Primary Cobalt (`#2563EB` / `#6366F1`), Human-Led Violet (`#6D28D9` / fond `#F5F3FF` exclusivement réservé aux *Ancrages Humains*), Arbitration Amber (`#D97706` / fond `#FFFBEB`), Gate Pass Emerald (`#059669` / fond `#ECFDF5`), Ontology Cyan (`#0284C7` / fond `#F0F9FF`), et Stale/Blocker Crimson (`#DC2626` / fond `#FEF2F2`), ainsi que le duo typographique strict `Inter`/`Geist Sans` (`13.5px` corps, `22px` titres) et `JetBrains Mono` (`12px` pour les URI, hashes `SHA-256` et logs).
- **UX-DR2 (Architecture Spatiale à 3 Colonnes Adaptatives, Sélecteur de Périmètre `⌘W` & Menu Global à 7 Modules — `DESIGN.md`, `EXPERIENCE.md §2`)** : Implémenter la grille Desktop à 3 colonnes : (1) *Global Sidebar Navigation* (`235px` dépliée / `68px` repliée en icônes via le bouton `«` ou raccourci `[`) intégrant en en-tête le **Sélecteur de Périmètre Hiérarchique (`⌘W` : `🌐 Plateforme Globale → 🏢 BU / Tribu → 👥 Équipe → 🗂️ Workspace Solution`)** et affichant les 7 modules filtrés par RBAC (*1. 💬 Cockpit & Chat*, *2. 🔔 Boîte & Mes Runs*, *3. 📦 Catalogue Fédéré*, *4. 🧬 Ontologie & KB*, *5. 🛡️ Gates & Habilitations*, *6. 📊 FinOps & Audit*, *7. ⚙️ Administration & Pilotage des Workspaces `/workspaces`*) avec pastilles temps réel (compteur ambre d'actions *Contributeur* et badge rouge `!` pour `[STALE_WARNING]`) et badge de *Profil Humain* en pied de barre ; (2) *Espace Central / Canvas* (`1fr`, min `640px`, en Split-View Chat + Canvas dans le module 1 et plein écran dans les modules 2 à 7) ; et (3) *Dock Persistant Agent Assistant & Permission Broker* (`360px` à droite dans les modules 2 à 7, repliable via `]`).
- **UX-DR3 (Composant `Human-Led Anchor Card` & Interdiction d'Auto-Complétion IA — `DESIGN.md`, `EXPERIENCE.md §4 & §6`)** : Implémenter le composant `human-led-anchor-card` (bordure gauche violette `4px solid #6D28D9`, fond `#F5F3FF`, en-tête `✍️ ANCRAGE HUMAIN OBLIGATOIRE (human_authored_required: true)` et signature de l'auteur humain) qui verrouille le bouton *Lancer la génération de l'étape* tant qu'un texte humain significatif ($\ge 30$ caractères) n'est pas saisi et signé, interdit strictement tout bouton *"Générer avec l'IA"* à l'intérieur de la carte, et déclenche une relance socratique dans le chat si l'utilisateur demande à l'agent de le rédiger à sa place.
- **UX-DR4 (Composant `Cognitive Review Briefing` 2x2 — `DESIGN.md`, `EXPERIENCE.md §4`)** : Implémenter en tête de tout artefact volumineux ($> 1\,500$ mots ou $> 3$ sections) ou soumis à une *Gate Humaine* la grille $2 \times 2$ `review-briefing-grid` présentant immuablement les 4 blocs (*1. Résumé Exécutif*, *2. Éléments Clés & Contrôle Transverse*, *3. Décisions Prises*, *4. Hypothèses Retenues*) où le bloc 4 conserve une bordure ambre (`#D97706`) tant que le valideur n'a pas inspecté ou pointé les hypothèses.
- **UX-DR5 (Composant `Chunked Validation Card` & Approbation Séquentielle — `DESIGN.md`, `EXPERIENCE.md §4 & §6`)** : Implémenter le composant `chunk-validation-card` segmentant l'artefact (et les éventuelles *Actions Jira Staged*) par section du *Gabarit d'Artefact* avec statut individuel (`PENDING`, `APPROVED`, `CHALLENGED`, `EDITING`), 3 actions directes (*Valider la section*, *Co-éditer*, *Challenger / Rewind amont*), navigation clavier `Alt + ↑ / ↓`, et interdiction formelle d'un bouton *"Tout Approuver en 1 clic"* tant que toutes les sections obligatoires n'ont pas été parcourues et approuvées.
- **UX-DR6 (Composant `Arbitration Tie-Break Matrix` — `DESIGN.md`, `EXPERIENCE.md §4`)** : Implémenter la carte ambre `arbitration-tiebreak-card` dans le Chat, l'Inbox et sur Mobile Companion dès qu'un agent suspend son exécution sur des options équivalentes (`FR-5`), affichant côte à côte chaque option, ses avantages/inconvénients, ses impacts SI/Métier/FinOps, un champ optionnel *"Justification / Autre orientation"* et le bouton de décision qui débloque immédiatement le *Workflow Run*.
- **UX-DR7 (Composant `Upstream Challenge & Rewind Modal` avec Aperçu d'Impact What-If — `EXPERIENCE.md §4`, `FR-7`)** : Implémenter la modale de contestation amont permettant de sélectionner un passage d'un artefact amont ou de signaler une `[STALE_WARNING]`, de visualiser l'**Aperçu de Simulation d'Impact (*What-If Impact Preview*)** listant les *Steps*, sections d'artefacts et axiomes aval impactés, de soumettre le challenge traduit par l'Ontologie aux acteurs amont, et de déclencher le **Replay** ciblé (`FR-16`).
- **UX-DR8 (Composant `Federated URI & RBAC Badge` — `DESIGN.md`)** : Implémenter le badge monospace `uri-badge` (`JetBrains Mono 12px`, `rounded-sm`) distinguant visuellement la source de vérité d'une ressource (`git://` en ambre, `nexus://` en bleu cobalt, `db://` en vert émeraude, `confluence://` et `jira://`, `orcia://`), ses permissions effectives (`DISCOVER`, `EXECUTE`, `🔒 Source masquée`) et son empreinte `SHA-256` tronquée.
- **UX-DR9 (Composant `Presence & Claim Pill` Temps Réel `< 500ms` — `DESIGN.md`, `EXPERIENCE.md §4 & §5`)** : Implémenter la pastille `presence-claim-pill` sur les notifications d'équipe affichant le bouton `Prendre (Claim)` puis basculant en `< 500 ms` via SSE vers `🔒 Pris par vous` / `🔒 En cours : {Prénom}` (opacité `85%` pour les pairs avec action secondaire *Rejoindre en consultation* ou *Force Unclaim* après 15 minutes d'inactivité).
- **UX-DR10 (Modale de Friction Positive `Anti-Rubber-Stamping Guard` — `EXPERIENCE.md §4`)** : Implémenter sur les *Gates Humaines* le détecteur de temps de lecture actif ouvrant une modale de confirmation explicite (*"Validation rapide détectée (< 15s) — Confirmez-vous avoir vérifié les {N} hypothèses retenues par l'Agent Évaluateur ?"*) en cas d'approbation précipitée.
- **UX-DR11 (Traitement Visuel & Comportemental des 5 États Système — `EXPERIENCE.md §5`)** : Implémenter les bandeaux et états dédiés pour : (1) `READ_ONLY_OBSERVER` (bandeau `👁️ Mode Consultation Seule`, masquage/désactivation de tous les contrôles d'édition, d'arbitrage et de Gate), (2) `CONTRIBUTOR_ACTION_REQUIRED` (bandeau Cobalt/Ambre indiquant l'action attendue), (3) `PERMISSION_DENIED_STEP` (ouverture automatique du *Dock Permission Broker* avec le rôle manquant, la procédure KB, le lien Jira pré-rempli et le bouton *Replay Step N*), (4) `STALE_WARNING` (badge rouge `!` sur le module 4 de la Sidebar et bannière d'alerte sur les Runs affectés), et (5) `CLAIMED_BY_PEER`.
- **UX-DR12 (Adaptation Dynamique du Ton et du Vocabulaire par Profil Humain — `EXPERIENCE.md §3`)** : Adapter le rendu et le microcopy de l'*Agent Assistant* dans l'UI selon les 4 archétypes de *Profil Humain* : *Direction / BU Lead* (KPIs budgétaires, TTM, SLA, Ontologie N1/N2), *Product Manager / Métier* (règles de gestion, parcours client, impacts produit), *Architecte / Tech Lead / Dev* (URI exactes, schémas OpenAPI, diffs, hashes `SHA-256`, Ontologie N3), et *SecOps / Auditeur* (preuves de Gates, orthogonalité des modèles, provenance).
- **UX-DR13 (Palette de Commandes Universelle `⌘K` / `Ctrl+K`, Sélecteur de Périmètre `⌘W`, Centre de Pilotage Unifié des Workspaces à 4 Onglets & Raccourcis Clavier Power-User — `EXPERIENCE.md §2 & §6`)** : Implémenter la palette `Command` (`⌘K` / `Ctrl+K`) permettant en `< 1s` de changer de *Workflow Run*, de basculer de périmètre (`⌘W` : `🌐 Plateforme Globale → 🏢 BU → 👥 Équipe → 🗂️ Workspace`), de chercher dans le *Catalogue Fédéré*, d'interroger un concept d'*Ontologie* ou de sauter à une notification, ainsi que l'écran **Centre de Pilotage Unifié des Workspaces (`/workspaces` & `/workspaces/[workspaceId]`, `g w`)** à **4 onglets consolidés** (*1. Instances de Workflow Runs & Artefacts*, *2. Sources Dédiées & Partagées*, *3. Workflows, Agents & Surcharges 4 niveaux*, *4. Équipes, Membres & Gouvernance*) et les raccourcis globaux `g c`, `g i`, `g f`, `g o`, `g g`, `g a`, `g s`, `g w`, `[` (repli Sidebar), `]` (repli Dock IA) et `Alt + ↑ / ↓` (navigation par découpage).
- **UX-DR14 (Explorateur d'Ontologie à 4 Colonnes, Simulation What-If & Gestion KB — `EXPERIENCE.md §2`)** : Implémenter dans le module **🧬 4. Ontologie & KB** un explorateur visuel à 4 colonnes (*1. Entreprise $\rightarrow$ 2. BU $\rightarrow$ 3. Équipe & Workspace $\rightarrow$ 4. Run*) avec tiroir de promotion gouvernée (`TermPromotionDrawer`), aperçu de simulation d'impact (*What-If*), gestion des sources KB (`confluence://`, `jira://`, `git://`, `db://`) et résolution des alertes `[STALE_WARNING]`.
- **UX-DR15 (Éditeur/Visualiseur de Graphe de Workflow `@xyflow/react` & Prévisualisation Conversationnelle — `AD-15`, `FR-11`, `UJ-10`)** : Intégrer `@xyflow/react` dans le *Canvas* et l'Administration pour inspecter visuellement le DAG des *Workflows* (dont le workflow à 5 nœuds de l'*Agent Assistant*) et prévisualiser en temps réel les graphes et manifestes YAML assemblés ou modifiés conversationnellement par l'*Agent Assistant* (`UJ-10`).
- **UX-DR16 (Responsive Design à 3 Breakpoints & Expérience Mobile Companion Restreinte — `DESIGN.md`, `EXPERIENCE.md §8`)** : Implémenter les 3 breakpoints : *Desktop Large (`>= 1280px`)* (3 colonnes complètes), *Laptop / Tablet (`768px - 1279px`)* (Sidebar repliée `68px` + Dock IA en `Sheet` sous `1024px`), et *Mobile Companion (`< 768px`)* (vue mono-colonne à barre d'onglets basse à 3 entrées : `🔔 Inbox`, `💬 Arbitrage/Chat`, `📄 Briefing`, autorisant le triage/*Claim*, les arbitrages, la lecture du *Briefing 4 blocs*, la validation par découpage et le suivi en *Consultation seule*, tout en bloquant l'édition YAML, la co-édition lourde et le module *7. Administration* avec une bannière explicite *"Fonctionnalité réservée au poste Desktop"*).
- **UX-DR17 (Composant `AutonomousExecutionBadge`, Vue Regroupée par Déclencheur & Sorties de Secours `Kill-Switch` / `Rollback` — `DESIGN.md`, `EXPERIENCE.md §4 & §5`, `FR-29`)** : Implémenter dans `@orcia/ui` le composant `AutonomousExecutionBadge` en Cyan/Cobalt (`#0284C7` / fond `#F0F9FF`, sans jamais utiliser le Violet `#6D28D9` réservé à `HumanLedAnchorCard`) affichant `🤖 Exécuté sous Contrat d'Autonomie #{contract_id} — Déclencheur : {MANUAL | WEBHOOK | LOG_SINK_ALERT | CRON} — 0 intervention humaine en cours de run`, le filtre regroupé par déclencheur dans **🔔 2. Boîte & Mes Runs** (Loi de Hick), et les deux sorties de secours immédiates `🛑 Kill-Switch (Suspendre le Trigger & les Runs actifs)` et `⏪ Invalider & Rollback`.

### FR Coverage Map

- **FR-1** : Epic 3 - Interface Chat-First + Canvas, Sélecteur de Périmètre Hiérarchique (`⌘W`), Menu Global 7 modules & adaptation Agent Assistant au Profil Humain
- **FR-2** : Epic 5 - Centre de Notifications Unifié (Individuel & Équipe) avec Claim et verrou SSE < 500ms
- **FR-3** : Epic 5 - Supervision Multi-Workflows, Centre de Pilotage Unifié Multi-Niveaux des Workspaces (`/workspaces` à 4 onglets) et séparation Consultation seule (HTTP 403) vs Contributeur
- **FR-4** : Epic 3 - Ancrages Humains Obligatoires (human_authored_required: true) et accompagnement socratique
- **FR-5** : Epic 3 & Epic 7 - Arbitrage Humain systématique sur options équivalentes (`WAITING_FOR_HUMAN_ARBITRATION`) & politique de départage sous contrat (`tie_break_policy`)
- **FR-6** : Epic 4 - Briefing de Revue (4 blocs) et Validation par Découpage des artefacts volumineux
- **FR-7** : Epic 3 - Challenge Amont Inter-Steps avec Simulation d'Impact (What-If) et boucle de rétroaction
- **FR-8** : Epic 2 - Structuration de l'Ontologie en 4 Niveaux (Entreprise, BU, Équipe hiérarchique `3_TEAM` & Solution `3_WORKSPACE`, Run) avec héritage
- **FR-9** : Epic 2 - Extraction ontologique temps réel, Simulation d'Impact (What-If) et promotion gouvernée
- **FR-10** : Epic 2 - Triple exécution active de l'Ontologie (Typage Blackboard, Traduction Profil, Gates/RAG)
- **FR-11** : Epic 3 - Définition Workflow-as-Code (YAML/JSON) et composition/modification assistée par l'Agent Assistant
- **FR-12** : Epic 3 - Gabarits d'Artefact Multi-Audience (Markdown Humain + JSON/YAML Schema Agent)
- **FR-13** : Epic 3 & Epic 7 - Garantie de la discipline Intention -> Code (mode `brownfield_bootstrap` et boucle d'auto-remédiation `Intention de Remédiation -> Correctif`)
- **FR-14** : Epic 3 & Epic 7 - Orchestration Hybride Multi-LLM agnostique, exécution tri-modale (`Coaching` / `Fast-Path` / `Autonomous Contract`) & Blackboard filtré
- **FR-15** : Epic 3 - Version Pinning immuable des Workflow Runs (`run-lock.json` SHA-256 récursif)
- **FR-16** : Epic 3 - Replay ciblé à partir du Step N (Time-Travel Execution sur branche ACTIVE et intra-sous-workflow)
- **FR-17** : Epic 4 - Gates Déterministes en Sandbox (< 5s, sans réseau, conformité Gabarit/Ontologie & anti-Pattern Drift)
- **FR-18** : Epic 4 - Gates Agentiques avec Orthogonalité des Modèles, lentille fact_verification & Contrôle Transverse
- **FR-19** : Epic 4 & Epic 7 - Gates Humaines à Politique Adaptative, tirage d'audit post-hoc (`POST_HOC_AUDIT_SAMPLE`) et garde-fou anti-Rubber-Stamping (< 15s)
- **FR-20** : Epic 1 - Résolution à la volée du Catalogue Fédéré (db://, git://, nexus://, confluence://, jira://, orcia://), surcharges 4 niveaux (Base -> Team -> Workspace -> User) & cache SHA-256
- **FR-21** : Epic 1 - Authentification hybride bi-mode, hiérarchie d'équipes (`OrgUnit`) découplée des Workspaces solutions, rôle `TEAM_LEAD` & 5 permissions dissociées du Catalogue
- **FR-22** : Epic 1 & Epic 7 - Exécution Passthrough / Service Principal scopé et Permission Broker IA connecté à Jira
- **FR-23** : Epic 2 - Indexation différenciée incrémentale, Graphe Tripartite (Confluence <-> Jira <-> Git), data-freshness & [STALE_WARNING]
- **FR-24** : Epic 4 & Epic 7 - Actions & transitions de workflows Jira Staged aux Gates (+ Webhooks), Skills en Sandbox & MCP Bidirectionnel (/api/v1/mcp)
- **FR-25** : Epic 6 - Provenance Auditable complète et immuable par Step et par Gate (audit_ledger)
- **FR-26** : Epic 6 & Epic 7 - Comptabilité FinOps complète (Coût Setup + Run vs TTM) et coupe-circuits budgétaires par Run/Arbre/Trigger
- **FR-27** : Epic 6 & Epic 7 - Indicateurs d'impact cognitif, anti-Rubber-Stamping, Indice de Réversibilité Humaine et métriques d'autonomie (`SM-A1..A3`)
- **FR-28** : Epic 1 - Workflows Système d'initialisation, onboarding autonome d'équipe & multi-workspaces (`TEAM_LEAD`) et auto-amorçage gouverné (orcia://system/bootstrap/*)
- **FR-29** : Epic 7 - Exécution Autonome sous Contrat, Déclencheurs Événementiels Idempotents (Webhooks, Puits de Logs, Cron), Boucle Fermée d'Auto-Remédiation (`UJ-12`) & Audit Post-Hoc
- **FR-30** : Epic 3 & Epic 7 - Imbrication Fractale de Workflows (`Sub-Workflows` & `Workflow-as-Agent`, profondeur $\le 3$)

- **FR-31** : Epic 8 (+ ad-hoc, Epic 13) - Gouvernance d'entreprise & Paramètres : habilitations RBAC/ABAC à 6 verbes, modèles IA et routage, connecteurs & secrets, packs, wizards (`CAP-050`..`CAP-058`)
- **FR-32** : Epic 9 & 12 (+ ad-hoc, Epic 13) - Coquille 4 zones, recherche ⌘K, accostage Jour 0, aide contextuelle, journal d'activité (`CAP-060`..`CAP-068`)
- **FR-33** : Epic 10 (+ ad-hoc, Epic 13) - Mon Assistant gouverné : 4 niveaux, 3 vitesses, citations déterministes, dossiers & fils (`CAP-070`..`CAP-076`)
- **FR-34** : Epic 11 (+ ad-hoc, Epic 13) - Mes Espaces : ADN, glossaire, routage d'artefacts, rattachement d'équipe (`CAP-067`, `CAP-080`, `CAP-081`, `CAP-084`)
- **FR-35** : Epic 11 (+ ad-hoc, Epic 13) - Exposition MCP/A2A, banc de test, atelier orcia-pack-builder (`CAP-082`..`CAP-084`)
- **FR-36** : ad-hoc, Epic 13 - Gestion des agents et compétences (`CAP-090`..`CAP-092`)

> Source de vérité du statut réel de chaque capacité : `docs/product/capabilities.yaml` (voir `AGENTS.md` §5).

## Epic List

### Epic 1: Amorçage Gouverné de l'Organisation, Onboarding Autonome d'Équipe (`TEAM_LEAD`), Catalogue Fédéré & Permission Broker connecté à Jira
Les Ingénieurs Plateforme, Chefs d'Équipe (`TEAM_LEAD`) et Membres d'équipe (`Karim UJ-9`, `Marc UJ-5`, `Nadia UJ-4`, `Lucas UJ-7`) disposent du socle opérationnel d'ORCIA (monorepo Greenfield `AR-1`, infrastructure `AR-2`, authentification primaire bi-mode **SSO OIDC / OAuth 2.1 + Locale Argon2id/TOTP**, arbre hiérarchique d'équipes `Org -> BU -> Tribu/Équipe Parente -> Sous-Équipe` découplé des `Workspaces` de solutions logicielles, et coquille UI Direction C à 7 modules), initialisent l'organisation dès le Jour 0 et embarquent leurs équipes et leurs différentes solutions logicielles en autonomie via les workflows système (`init-organization`, `init-workspace` piloté par le **Chef d'Équipe**, `init-datasource`, `init-user`), publient et résolvent à la volée des ressources versionnées (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`, packs BMAD et surcharges à 4 niveaux `Base -> Team -> Workspace -> User`) épinglées dans le cache CAS `SHA-256` selon 5 permissions dissociées (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`), et résolvent tout refus d'accès (`401/403`) grâce au **Permission Broker** qui génère la procédure d'habilitation et le lien pré-rempli dans **Jira**.
**FRs covered:** `FR-20`, `FR-21`, `FR-22`, `FR-28`

### Epic 2: Ontologie Dynamique à 4 Niveaux, Simulation d'Impact (*What-If*) & RAG Hybride sur Graphe Tripartite (`Confluence ↔ Jira ↔ Git`)
Les Stewards Métier, PMs, Architectes et Tech Leads (`Hélène UJ-1`, `Antoine UJ-2`, `Yanis UJ-3`, `Arthur UJ-10`) structurent et font évoluer l'**Ontologie à 4 niveaux** (*1. Entreprise $\rightarrow$ 2. BU $\rightarrow$ 3. Équipe hiérarchique `3_TEAM` & Solution `3_WORKSPACE` $\rightarrow$ 4. Run*) avec héritage, extraction sémantique en temps réel, **Simulation d'Impact (*What-If*)** avant promotion gouvernée et triple exécution active ; ils indexent de façon incrémentale et différenciée leurs espaces **Confluence** (`confluence://` en *Parent-Child*), tickets **Jira** de référence (`jira://`), dépôts de code **Git** (`git://` en *AST + Code Graph*) et schémas DB (`db://`) au sein d'un **Graphe Tripartite `Confluence ↔ Jira ↔ Git`** (`halfvec(1024)` + BM25), et détectent/résolvent toute obsolescence documentaire (`[STALE_WARNING]`, brique `data-freshness`) dans le module **🧬 4. Ontologie & KB**.
**FRs covered:** `FR-8`, `FR-9`, `FR-10`, `FR-23`

### Epic 3: Cockpit "Human-Led", Agent Assistant Adaptatif, Moteur d'Orchestration Durable & Sous-Workflows Fractals (`SUB_WORKFLOW <= 3`)
Les Product Managers, Architectes et Tech Leads (`Hélène UJ-1`, `Antoine UJ-2`, `Yanis UJ-3`, `Arthur UJ-10`) dialoguent dans le **💬 1. Cockpit & Chat** avec l'**Agent Assistant** (DAG à 5 nœuds orientés type n8n dans le `AssistantHarness` à 5 couches, adaptant son vocabulaire au **Profil Humain**), définissent ou assemblent conversationnellement des **Workflows-as-Code** YAML/JSON (incluant les étapes composites `SUB_WORKFLOW` jusqu'à une profondeur $\le 3$, la criticité `criticality`, le régime `execution_regime` et la politique `tie_break_policy`) avec prévisualisation graphique (`@xyflow/react`), lancent des **Workflow Runs** épinglés récursivement par `run-lock.json` en mode **Coaching interactif**, **Fast-Path / Tâche de fond (`BACKGROUND_AUDIT`, `UJ-10`)** ou **Autonome sous Contrat (`AUTONOMOUS_CONTRACT`)**, rédigent leurs **Ancrages Humains Obligatoires** (`human_authored_required: true`), tranchent les **Arbitrages Humains** sur options équivalentes, émettent des **Challenges Amont** avec simulation d'impact (*What-If*) et déclenchent un **Replay ciblé** à partir du Step $N$ (y compris à l'intérieur d'un sous-workflow enfant) dans le respect de la discipline `Intention -> Code`.
**FRs covered:** `FR-1`, `FR-4`, `FR-5`, `FR-7`, `FR-11`, `FR-12`, `FR-13`, `FR-14`, `FR-15`, `FR-16`, `FR-30`
**NFRs covered (Avenant A2):** `NFR-EXT-1`, `NFR-ISO-1`, `NFR-SEC-4` (partiel, `3.2f`) — **Critère d'acceptation de l'Epic 3 (Avenant A2, `P2-2`)** : le job CI `core-without-sdlc` (workflow Finance « Rapprochement de factures » + connecteur ERP factice, pack SDLC désinstallé) est au vert ; la discipline `Intention -> Code` (`FR-13`) est portée par le pack `orcia-pack-sdlc` (`AD-20`).

### Epic 4: Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution (Actions Jira, Sandbox & MCP IDE)
Les Tech Leads, SecOps, Développeurs et Auditeurs (`Yanis UJ-3`, `Marc UJ-5`, `Sophie UJ-6`, `Arthur UJ-10`) valident chaque étape via la chaîne de **Gates Déterministes** en **Sandbox isolée** (`< 5s`, sans réseau, conformité Gabarit/Ontologie et anti-**Pattern Drift**), de **Gates Agentiques** avec **Orthogonalité des Modèles**, pseudonymisation PII réversible (`PiiReversibleScrubber`) et DAG de 5 lentilles (dont `fact_verification` et contrôle transverse Étape $N$ vs Étape 1), et de **Gates Humaines Adaptatives** (`mandatory_full`, `risk_or_exception_based`, `sampling`) équipées du **Briefing de Revue (4 blocs)**, de la **Validation par Découpage** et du garde-fou anti-**Rubber-Stamping** (`< 15s`) ; ils exécutent de manière gouvernée (en mode *Staged* validé aux Gates) la création, la modification et les **transitions de workflows Jira** (+ réception des Webhooks `jira:issue_updated`) et interrogent ORCIA depuis leur IDE via le **Serveur MCP gouverné (`/api/v1/mcp`)**.
**FRs covered:** `FR-6`, `FR-17`, `FR-18`, `FR-19`, `FR-24`

### Epic 5: Centre de Notifications Temps Réel (`< 500ms`), Supervision Multi-Runs, Centre de Pilotage Unifié Multi-Niveaux des Workspaces (`/workspaces`) & Expérience Mobile Companion
Les Administrateurs Plateforme (`Karim UJ-9`), Directeurs de BU (`Claire UJ-8`), Chefs d'Équipe (`Marc UJ-5`) et Contributeurs multi-projets (`Nadia UJ-4`) trient leurs notifications personnelles et d'équipe dans **🔔 2. Boîte & Mes Runs**, prennent en charge (*Claim*) atomiquement une notification d'équipe avec verrou de présence temps réel (`< 500ms` via SSE), supervisent simultanément plusieurs **Workflow Runs** avec séparation stricte entre **Consultation seule (`READ_ONLY_OBSERVER`)** et **Contributeur (`CONTRIBUTOR_ACTION_REQUIRED`)**, pilotent et administrent de manière consolidée (*Roll-up* & *Drill-down* via le sélecteur de périmètre **`⌘W`**) l'ensemble des **Workspaces, Instances de Workflow Runs, Sources (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`), Agents/Workflows/Surcharges et Équipes** depuis le **Centre de Pilotage Unifié Multi-Niveaux (`/workspaces` & `/workspaces/[workspaceId]` à 4 onglets)**, pilotent l'interface au clavier (`⌘K`, `⌘W`, `g c`..`g w`, `Alt + ↑/↓`), et traitent leurs arbitrages et validations urgentes en déplacement grâce à l'interface **Mobile Companion** à 3 onglets.
**FRs covered:** `FR-2`, `FR-3`

### Epic 6: Gouvernance Exécutive, Provenance Auditable Immuable, FinOps Consolidé (LLM Internes + Télémétrie MCP/Agents Distants) & Réversibilité Humaine
Les Directeurs de BU, Responsables Produit et Auditeurs (`Claire UJ-8`, `Sophie UJ-6`) pilotent dans **📊 FinOps** l'équation économique consolidée de leurs processus (**Coût de Setup + Coût de Run interne vérifié + Coût externe déclaré MCP/A2A vs gain de TTM**) protégée par le validateur **`RemoteUsageSanitizer`** (`_meta.usage` / `X-Orcia-Usage`), les coupe-circuits budgétaires et anti-boucles (`PAUSED_BUDGET_EXCEEDED`, `PAUSED_MAX_RETRIES`) et les coupe-circuits isolés par connecteur (`CIRCUIT_OPEN`, `AD-12`), inspectent et exportent la **Provenance Auditable** immuable de chaque Step, Gate et test de connexion à chaud (`audit_ledger`, `ADMIN_CONNECTION_TEST`), et suivent les contre-métriques de gouvernance cognitive (**Ratio Cadrage Actif $\ge 40\%$**, **Taux de Rubber-Stamping $< 5\%$**, **Indice de Pattern Drift / Réversibilité Humaine $0\%$**, **Taux d'Escalade Autonome `SM-A1`**, **Taux d'Invalidation Post-Hoc `SM-A2`** et **Coût Moyen par Run Autonome `SM-A3`**) avec recommandations automatiques d'ajustement des Gates.
**FRs covered:** `FR-25`, `FR-26`, `FR-27` (`AD-12`, `Principe M.3`)

### Epic 7: Agents & Workflows Autonomes sous Contrat, Déclencheurs Événementiels (Webhooks, Puits de Logs, Cron), Auto-Remédiation, Génération Automatique d'Aide & Gouvernance Post-Hoc
Les Directeurs de BU, Chefs d'Équipe (`TEAM_LEAD`), Ingénieurs SRE/Plateforme et Auditeurs SecOps (`Claire UJ-8/UJ-11`, `Marc UJ-5`, `Karim UJ-9/UJ-12`, `Sophie UJ-6`) configurent et signent des **Contrats d'Autonomie** sur les workflows éligibles (`LOW_NON_CRITICAL`, `STANDARD`), déclenchent de manière idempotente des **Workflow Runs autonomes** par action manuelle *Fire-and-Forget*, par **Webhooks signés** (Jira, Git, Confluence), par **Tâches Planifiées (`CRON`, `UJ-11`)**, par **Événement Outbox de publication de Pack/Processus (exécutant automatiquement `generate-and-attach-help` sous contrat d'autonomie `AD-18`)**, ou par **Alertes de Puits de Logs (`LOG_SINK_ALERT`, `UJ-12` : boucle fermée d'auto-remédiation AIOps avec diagnostic $\ge 0.90$, reproduction/correction TDD en Sandbox, test staging prod-like, déploiement et vérification post-action dans les logs avec Rollback automatique)**, et supervisent ces runs via le badge `AutonomousExecutionBadge` (`UX-DR17`), l'échantillonnage d'audit *post-hoc* (`POST_HOC_AUDIT_SAMPLE`) et les sorties de secours (`🛑 Kill-Switch` et `⏪ Invalider & Rollback`).
**FRs covered:** `FR-5`, `FR-13`, `FR-14`, `FR-19`, `FR-22`, `FR-24`, `FR-26`, `FR-27`, `FR-29`, `FR-30` (`AD-18`, `Principe D.4`)

### Epic 8: Hub de Paramétrage Post-Jour 0 (`/settings/*`), Gouvernance d'Entreprise à 6 Verbes (`RBAC/ABAC`), Routage Cognitif Abstrait (`simple|medium|complex|auto` & Effort), Studio Visuel Avancé (`Couches`, `Contrat`, `Pré-prompt`) & Wizards d'Initialisation Durables
Les Administrateurs Plateforme (`Karim UJ-9`), Ingénieurs SecOps (`Sophie UJ-6`), Directeurs de BU (`Claire UJ-8`) et Chefs d'Équipe / Tech Leads (`Marc UJ-5`, `Yanis UJ-3`) administrent ORCIA après le Jour 0 sans redéploiement via le **Hub de Paramétrage (`/settings/{iam,connectors,ai-models,packs,workflows,audit}`)** protégé par concurrence optimiste (`ETag`/`If-Match` `412`) et contrat de secret en écriture seule (`SecretInput`/`SecretStatus`), appliquent un modèle d'habilitations hiérarchique **RBAC/ABAC à 6 verbes (`create, read, update, delete, execute, grant`)**, abstraient les modèles LLM en **Tiers Cognitifs (`simple €, medium €€, complex €€€, auto ⚡`)** et **niveaux d'Effort** avec escalade déterministe rejouable sous DBOS, enrichissent le **Studio Visuel de Workflows** (5 onglets de cycle de vie, immutabilité des versions publiées, `Pré-prompt IA`, `Contrat du workflow`, `Déclencheurs`, `▷ Tester`, inspecteur **`COUCHES · N`** et moindre privilège connecteur par étape), et embarquent toute nouvelle équipe grâce à **3 Wizards d'Initialisation Durables DBOS (`/wizards/*`)**.
**FRs covered:** `FR-1`, `FR-10`, `FR-11`, `FR-14`, `FR-16`, `FR-17`, `FR-19`, `FR-24`, `FR-26`, `FR-27`, `FR-28`, `FR-30` (`AD-21`)

### Epic 9: Coquille Ergonomique 4 Zones (Style Portals / EXEMPLE), Recherche Fédérée `⌘K` à 2 Vitesses (*Zero Layout Shift*), Compte Utilisateur (`UserSettingsModal`), Accostage Jour 0 (`Accostage 1/6`) & Aide Contextuelle Hybride (`❓`)
Tous les utilisateurs d'ORCIA bénéficient dès la première seconde d'une **Coquille Globale à 4 Zones** auto-descriptive (`TopHeaderBar 52px`, `Sidebar 240px/68px` aux **8 menus fixes non numérotés** `Cockpit | Mon Assistant | Mes Processus | Mes Agents | Mes Espaces | FinOps | Configuration | Aide` avec terminologie invariante **`Espace`**, `Zone Centrale 1fr` et `Colonne d'Aide Contextuelle ? 340px` auto-repliée sur `< 1440px`), d'un **Cockpit épuré** (extinction automatique des compteurs `0/0/0/0` quand `total == 0` et séparation entre décisions courtes `Tie-Break` et **Vue Fokus de Revue `Run #ID`** avec verrou Redis `AD-4`), d'un **Parcours d'Accostage Progressif Jour 0 (`Accostage 1/6`)** protégé contre le *First-User Takeover* (`LOCK TABLE users` + `ORCIA_BOOTSTRAP_TOKEN`) et débloquant l'essai dès `1 modèle LLM` ($\rightarrow \ge 2$ familles `AD-10`), d'une **Recherche Fédérée & Contextuelle `⌘K` à 2 vitesses sans saut visuel** (3 portées, 7 familles, lexical `< 30 ms` `0 $` en tête + vectoriel HNSW sur pause `450 ms` en bas avec *Deep-Linking Auto-Focus*), d'un **Menu Login (`UserAccountDropdown`) & Modale « Paramètres de mon compte » (`UserSettingsModal` à 4 onglets)** à double persistance `0 ms` anti-FOUC, et d'un **Système d'Aide Hybride (`HelpArticle` factorisé dans `catalog_items` + `cas/<sha256>`)** servi en `< 10 ms` via Redis.
**Principes UX/Architecture couverts:** `Principes A, A.2, A.3, C, D, D.4, E, F, G`, `Section 2`, `AD-4`, `AD-5`, `AD-6`, `AD-8`, `AD-10`, `AD-14`, `AD-16`, `AD-21`

### Epic 10: `Mon Assistant` Tout-en-Un (Style EXEMPLE) — Personnalisation à 4 Niveaux (Mode A & Mode B), Routage à 3 Vitesses (`TTFT < 1,2 s`), Citations Déterministes (`[S1]/[G1]/[O1]`) & Dossiers Thématiques Collaboratifs (`📁 Dossiers`)
Les équipes métiers et techniques disposent dans **`Mon Assistant`** d'un espace de travail conversationnel complet : personnalisable à 4 niveaux (`USER`, `WORKSPACE`, `TEAM`, `PLATFORM`) soit en **Mode A (Formulaire Rapide à 3 onglets)** soit en **Mode B (Studio Graphique `@xyflow/react`)** à l'intérieur des bornes inaltérables `🔒 AssistantHarness` (`AD-15`), garantissant un **`TTFT < 1,2 s`** grâce au cache Redis du prompt assemblé à 5 couches et au **Routage à 3 Vitesses (`⚡ Rapide`, `🔍 Agent & Outils MCP`, `🧠 Approfondi`)**, ancrant chaque affirmation par des **Citations Déterministes (`[S1]`, `[G1]`, `[O1]`)** résolues via `citation_map` SSE avec filtrage `READ_SOURCE` par lecteur (`AD-21`) et garde-fou anti-citation fantôme `< 5 ms`, et structurant le travail au long cours dans des **Dossiers Thématiques (`📁 Dossiers`)** dotés d'une continuité mémoire en Couche 5, d'un partage collaboratif à 3 niveaux (`🔒 Privé | 👥 Partagé | 📦 Espace`), d'un verrou de tour Redis léger (`SET NX EX 60`) et d'une identité `Passthrough` individuelle par message (`AD-6`).
**Principes UX/Architecture couverts:** `Principes B, H, K, K.4, K.5, K.6`, `AD-5`, `AD-6`, `AD-8`, `AD-14`, `AD-15`, `AD-21`

### Epic 11: Gouvernance Métier de l'Espace (`Mes Espaces` à 5 Onglets, Cycle de Vie du Glossaire `✨ À valider`, Routage des Artefacts à 4 Niveaux), Banc de Test MCP/A2A `🔌` & Atelier `orcia-pack-builder`
Les Responsables d'Espace (`TEAM_LEAD`), Stewards Métier (`ONTOLOGY_STEWARD_L3`) et Concepteurs de Packs pilotent leurs espaces dans **`Mes Espaces` structuré en 5 sous-onglets** (`Vue d'ensemble`, `Documents & Sources`, `Livrables & Artefacts`, `Glossaire & Règles métier`, `Membres & Équipe`), gouvernent la localisation et la publication des livrables produits selon une **Cascade à 4 Niveaux** (avec confinement `local://`, bail `ResourceLeasePort` `AD-4` et alias `orcia://workspaces/<ws>/artifacts/<type>/<slug>@v<N>`), alimentent leur **Glossaire métier (`✨ À valider`)** grâce à une extraction en 2 passes à coût maîtrisé (`0 $` déterministe + batch `Top-15`), sélection multiple et simulation *What-If* (`AD-7`), déclarent et testent à chaud des **Services/Serveurs MCP et `@Agents Distants (MCP / A2A)`** via un **Banc de Test en 4 Étapes (`🔌`)** supportant le mode `Passthrough`, et conçoivent/font évoluer/documentent des Packs Métier via le pack système **`packages/orcia-pack-builder`** (5 processus gouvernés dont `generate-and-attach-help` validé par `validate_help_article` en Sandbox Palier 1 `< 5 s`).
**Principes UX/Architecture couverts:** `Principes D.4, I, J, L, M.1, M.2`, `Sections 3 & 4`, `AD-4`, `AD-5`, `AD-6`, `AD-7`, `AD-8`, `AD-9`, `AD-14`, `AD-18`, `AD-20`, `AD-21`

## Epic 1: Amorçage Gouverné de l'Organisation, Onboarding Autonome d'Équipe (`TEAM_LEAD`), Catalogue Fédéré & Permission Broker connecté à Jira

Permettre aux Ingénieurs Plateforme, Chefs d'Équipe (`TEAM_LEAD`) et Membres d'équipe (`Karim UJ-9`, `Marc UJ-5`, `Nadia UJ-4`, `Lucas UJ-7`) de disposer du socle opérationnel d'ORCIA, d'initialiser l'organisation dès le Jour 0 et d'embarquer chaque équipe et ses différentes solutions logicielles (`Workspaces`) en autonomie via les workflows système gouvernés, de publier et résoudre à la volée des ressources fédérées (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`, packs BMAD) avec cache CAS `SHA-256`, surcharges à 4 niveaux et 5 permissions dissociées, et de débloquer tout refus d'accès (`401/403`) grâce au *Permission Broker* connecté à Jira.

### Story 1.1: Amorçage du Monorepo Hybride, Coquille UI Direction C (7 Modules) & Socle de Tests à 5 Couches

As a Ingénieur Plateforme (`Karim, UJ-9`),
I want initialiser le monorepo hybride TypeScript/Python, l'infrastructure conteneurisée (PostgreSQL 18 + pgvector, Redis 7.4, MinIO), la génération automatique du client OpenAPI 3.1, la coquille visuelle Direction C à 7 modules et le harnais de tests à 5 couches,
So that toute l'équipe dispose d'une fondation typée de bout en bout, observable et testée unitairement à $\ge 90\%$ avant de développer les briques métiers (`AR-1`, `AR-2`, `UX-DR1`, `UX-DR2`, `NFR-OBS-1`, `NFR-TEST-1`).

**Acceptance Criteria:**

**Given** un environnement de développement vierge disposant de `Node.js 24.0`, `pnpm 10.6`, `Python 3.12.9`, `uv 0.13.5` et `Docker Compose`
**When** l'ingénieur exécute la commande d'initialisation et de démarrage du monorepo (`pnpm install && uv sync && docker compose up -d`)
**Then** le workspace démarre `apps/web` (Next.js `16.4`, React `19.1`, Tailwind `4.3`, `shadcn/ui`), `apps/api` (FastAPI `0.143`), `apps/worker` (Dramatiq `2.2`), `packages/orcia-core` (squelette hexagonal des 8 domaines) et les conteneurs **PostgreSQL `18.0` + `pgvector 0.8.7`**, **Redis `7.4.2`** et **MinIO**
**And** la génération `openapi-typescript` produit `packages/api-client` avec `0 diff` depuis les schémas Pydantic v2 de `packages/orcia-core/schemas`, et toute erreur API retourne une enveloppe **RFC 9457 Problem Details** corrélée par `trace_id` OpenTelemetry (`structlog` / `pino`).

**Given** l'utilisateur qui ouvre `apps/web` sur un écran Desktop (`>= 1280px`) ou Laptop (`768px - 1279px`)
**When** la coquille applicative Direction C est rendue
**Then** les tokens CSS (`#0F172A` Sidebar, `#F8FAFC` Surface, `#2563EB` Primary, `#6D28D9` Human-Led Violet, `#D97706` Arbitration Amber, `#059669` Gate Emerald, `#0284C7` Ontology Cyan, `#DC2626` Stale Crimson) et les polices (`Inter`, `Instrument Serif`, `JetBrains Mono`) sont appliqués (`UX-DR1`)
**And** la grille à 3 colonnes affiche la *Global Sidebar Navigation* (`235px` dépliée / `68px` repliée via `[`) avec les 7 entrées du Menu Global, l'*Espace Central* (`1fr`) et le *Dock Persistant Agent Assistant & Permission Broker* (`360px`, repliable via `]`) (`UX-DR2`)
**And** la CI exécute avec succès les 5 couches de tests (`pytest` + `hypothesis`, `Vitest`, `testcontainers-python` sur vrais PG18/Redis/MinIO, `Schemathesis` et `@playwright/test`) avec une couverture unitaire $\ge 90\%$ (`AD-17`, `NFR-TEST-1`).

### Story 1.2: Authentification Hybride Bi-Mode (OIDC & Locale), Arbre Hiérarchique d'Équipes (`OrgUnit`) découplé des Espaces Solutions Multi-Sources (`Workspaces`), Rôle `TEAM_LEAD` & 5 Permissions Dissociées

As a Administrateur Plateforme ou Chef d'Équipe (`Karim UJ-9`, `Marc UJ-5`, `Nadia UJ-4`),
I want authentifier les utilisateurs via SSO d'Entreprise (`OIDC / OAuth 2.1`) ou via Authentification Locale autonome (`Email + Argon2id + MFA TOTP`), modéliser un arbre hiérarchique d'équipes (`org_units` à $N$ niveaux : `Entreprise -> BU -> Tribu/Équipe Parente -> Sous-Équipe`) découplé des `Workspaces` représentant chacun une solution logicielle pouvant agréger **plusieurs dépôts `git://`, plusieurs projets `jira://` et plusieurs espaces `confluence://` dédiés**, et appliquer les 5 permissions dissociées (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`),
So that chaque solution logicielle d'une équipe ait ses multiples sources (`N × git://`, `N × jira://`, `N × confluence://`) et artefacts isolés, que les équipes parentes disposent d'une supervision consolidée, et que les sous-équipes héritent des agents de leur équipe parente tout en protégeant les prompts/codes en boîte noire (`FR-21`, `AD-6`, `AD-14`, `NFR-SEC-4`).

**Acceptance Criteria:**

**Given** la migration Alembic créant les tables `org_units` (arbre auto-référencé via `parent_id`), `workspaces` (`owner_org_unit_id`, `visibility_mode: STANDARD | CONFIDENTIAL_RESTRICTED`), `workspace_datasources` (relation `1..N` rattachant à un Workspace ses multiples dépôts `git://`, projets `jira://`, espaces `confluence://`, schémas `db://` et registres `nexus://` qualifiés par `alias` et `role`), `users`, `transverse_groups`, `workspace_memberships`, `workspace_invitations`, `user_passthrough_credentials` et `catalog_acl_entries` à clés primaires `UUIDv7`
**When** un utilisateur s'authentifie soit via **SSO `OIDC / OAuth 2.1`**, soit via le flux **Local autonome (`Email + Argon2id + TOTP optionnel`)** et appelle `/api/v1/auth/me`
**Then** une session JWT courte (`15 min`) + Refresh Token `HttpOnly / Secure / SameSite=Strict` révocable dans Redis est établie, son *Profil Humain* complet (Archétype, Rôle `PLATFORM_ADMIN` / `TEAM_LEAD` / `CONTRIBUTOR` / `GATE_REVIEWER` / `ONTOLOGY_STEWARD_L3` / `OBSERVER`, arbre d'équipes `org_units`, liste des `Workspaces` solutions accessibles) est affiché en pied de Sidebar (`UX-DR2`), et les entrées du Menu Global non autorisées sont masquées côté UI et protégées en `HTTP 403` côté API.

**Given** une équipe (ou sous-équipe) pilotée par un **Chef d'Équipe (`TEAM_LEAD`)** qui maintient plusieurs solutions logicielles (ex. `Workspace 1 : Solution Paiement` avec 3 dépôts `git://`, 2 projets `jira://` et 2 espaces `confluence://`, et `Workspace 2 : Solution Fidélité` avec ses propres sources)
**When** le `TEAM_LEAD` gère son équipe et ses `Workspaces`
**Then** l'ensemble des sources dédiées (`N × git://`, `N × jira://`, `N × confluence://`), les *Workflow Runs* et les *Artefacts* du `Workspace 1` sont strictement isolés de ceux du `Workspace 2` ; le responsable d'une **Équipe Parente / Tribu / BU** dispose automatiquement par héritage ascendant (*Roll-up*) d'un accès `READ_ONLY_OBSERVER` et d'une agrégation FinOps sur les Workspaces des sous-équipes filles (sauf si le Workspace est marqué `CONFIDENTIAL_RESTRICTED`) ; et une équipe partenaire invitée sur le `Workspace 1` n'a aucune visibilité sur le `Workspace 2` (`FR-21`, `AD-14`).

**Given** une ressource du Catalogue publiée en `SHARED_TEAM` ou `SHARED_BU` par une équipe parente avec `DISCOVER` et `EXECUTE` mais **sans** `READ_SOURCE`
**When** un membre d'une sous-équipe fille inspecte la ressource ou l'exécute dans l'un de ses `Workspaces`
**Then** la ressource est automatiquement découvrable et exécutable par héritage descendant dans tous les Workspaces des sous-équipes filles, mais son prompt système et ses scripts sources restent masqués (`🔒 Source masquée`, `HTTP 403 ERR_READ_SOURCE_DENIED`), et tout secret *Passthrough* (`user_passthrough_credentials`) est chiffré en **AES-256-GCM** (`NFR-SEC-4`), avec couverture $\ge 90\%$ sur `packages/orcia-core/permissions`.

### Story 1.3: Catalogue Fédéré Multi-Sources (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`), Cache CAS `SHA-256`, Surcharges à 4 Niveaux (`Base → Team → Workspace → User`) & Adaptateur BMAD

As a Tech Lead ou Ingénieur Plateforme (`Marc UJ-5`, `Karim UJ-9`),
I want enregistrer des ressources par leur URI canonique dans le Catalogue Fédéré, les résoudre à la volée vers le cache immuable MinIO (`cas/<sha256>`), appliquer les surcharges déclaratives à 4 niveaux (`1. Base -> 2. Standards d'Équipe TEAM hiérarchique -> 3. Solution WORKSPACE multi-sources -> 4. Utilisateur USER`) et importer nativement des packs de skills BMAD,
So that une équipe mutualise ses conventions sur toutes ses solutions logicielles au niveau `TEAM` tout en configurant les multiples dépôts `git://`, projets `jira://` et espaces `confluence://` propres à chaque solution au niveau `WORKSPACE` avec une résolution `< 50 ms` (`FR-20`, `FR-21`, `AD-5`, `AD-14`, `AR-5`, `UX-DR8`, `NFR-PERF-3`).

**Acceptance Criteria:**

**Given** la migration Alembic créant les tables `workflow_definitions` (et `catalog_items`) et `workspace_customization_overrides` (`override_layer: TEAM | WORKSPACE | USER`), ainsi que le module **📦 3. Catalogue Fédéré** dans `apps/web`
**When** un utilisateur publie ou promeut une ressource à travers le cycle `DRAFT` $\rightarrow$ `SHARED_WORKSPACE` $\rightarrow$ `SHARED_TEAM` $\rightarrow$ `SHARED_BU` $\rightarrow$ `PENDING_APPROVAL` $\rightarrow$ `PUBLISHED_ORG` avec une URI `db://`, `git://`, `nexus://` (`.tar.gz`/`.zip`), `confluence://<space>/<page>@v<N>` ou `jira://<project>/<issue>`
**Then** le `FederatedUriResolver` télécharge la ressource à la première demande, vérifie ou calcule son empreinte `SHA-256`, la stocke de manière immuable dans MinIO sous `cas/<sha256>`, et toute résolution ultérieure du même hash répond en `< 50 ms` (`NFR-PERF-3`)
**And** chaque carte du Catalogue affiche le composant monospace **`Federated URI & RBAC Badge` (`uri-badge`, `UX-DR8`)** distinguant par couleur et icône la source (`git://`, `nexus://`, `db://`, `confluence://`, `jira://`), les droits effectifs et le hash `SHA-256` tronqué.

**Given** un workflow de base du catalogue et des surcharges déclaratives enregistrées dans `workspace_customization_overrides` aux niveaux `TEAM` (équipe parente / sous-équipe), `WORKSPACE` (mapping des `1..N` dépôts `git://`, `1..N` projets `jira://` et `1..N` espaces `confluence://` dédiés à la solution logicielle) et/ou `USER`
**When** le moteur résout la définition effective du workflow pour un *Run* lancé dans un *Workspace* donné
**Then** il applique la fusion déterministe à **4 niveaux (`1. Base -> 2. Team [Arbre Équipe Parente -> Sous-Équipe] -> 3. Workspace [Solution Multi-Sources] -> 4. User`)** : scalaires écrasés, listes de sources/règles/faits concaténées, lentilles fusionnées par `code`, sans modifier la ressource de base (`AD-14`), et épingle dans `run-lock.json` le vecteur complet des triplets `(alias, uri, resolved_version, sha256)` de toutes les sources du Workspace (`AD-5`)
**And** le `BmadSkillPackAdapter` importe et convertit sans perte un répertoire de skill BMAD (`SKILL.md` + `customize.toml` + `steps/*.md`) référencé via `git://` ou `nexus://` en définition exécutable ORCIA (`AR-5`), avec $\ge 90\%$ de couverture (`hypothesis` + `testcontainers` MinIO/PG18) sur `packages/orcia-core/catalog`.

### Story 1.4: Exécution Passthrough / Service Principal & Permission Broker IA connecté à Jira

As a Développeur ou Contributeur Métier (`Lucas UJ-7`, `Yanis UJ-3`),
I want que chaque résolution de ressource externe s'exécute par défaut avec mon identité déléguée (`Passthrough`) et qu'en cas de refus d'accès (`401/403`), le Permission Broker intercepte l'erreur et m'affiche la procédure d'obtention ainsi que le lien de demande d'accès pré-remplie dans Jira,
So that aucune élévation de privilèges (*Confused Deputy*) ne soit possible et qu'aucun blocage d'habilitation ne laisse l'utilisateur dans une impasse (`FR-22`, `AD-6`, `UX-DR11`).

**Acceptance Criteria:**

**Given** un connecteur externe (`git://`, `nexus://`, `confluence://`, `jira://`, `db://` ou client MCP) configuré par défaut en `execution_identity: passthrough` (ou en `service_principal` uniquement si explicitement approuvé par un Administrateur)
**When** une étape ou une action tente d'accéder à l'un des dépôts Git privés, l'une des pages Confluence restreintes ou l'un des projets/transitions de workflow Jira du Workspace pour lequel l'utilisateur courant ne possède pas le rôle requis (`HTTP 401/403`) ou la permission `EXECUTE`
**Then** le `PermissionBrokerService` intercepte l'exception, recherche le motif d'URI correspondant dans la Base de Connaissances d'Habilitations (fichiers Markdown à frontmatter YAML `uri_pattern`, `required_role`, `approver_team`, `request_url_template`, `sla_hours`), et retourne une enveloppe RFC 9457 enrichie du champ `permission_broker_hint`.

**Given** la réception de l'état `PERMISSION_DENIED_STEP` / `WAITING_FOR_PERMISSION` dans l'interface web
**When** l'utilisateur visualise l'étape bloquée dans le Cockpit ou le Catalogue
**Then** le **Dock Agent Assistant & Permission Broker** s'ouvre automatiquement à droite avec une carte ambre (`#D97706`, `UX-DR11`) présentant : (1) la source exacte (`git://`, `confluence://` ou `jira://`) et le droit ou rôle de projet Jira manquant, (2) l'équipe ou le responsable approbateur identifié et le SLA, (3) le bouton/lien ouvrant la demande d'accès pré-remplie dans **Atlassian Jira**, et (4) le bouton *Mettre en pause / Rejouer l'étape* (`FR-22`)
**And** les tests unitaires et d'intégration couvrent $\ge 90\%$ du `PermissionBrokerService` et vérifient le rendu du composant UI via Vitest / Playwright.

### Story 1.5: Workflows Système d'Amorçage Gouverné Jour 0 & Onboarding Autonome d'Équipe et Multi-Workspaces Multi-Sources par le Chef d'Équipe (`init-organization`, `init-workspace`, `init-datasource`, `init-user`)

As a Ingénieur Plateforme ou Chef d'Équipe (`Karim UJ-9`, `Marc UJ-5`, `Nadia UJ-4`),
I want exécuter les workflows système pré-embarqués (`orcia://system/bootstrap/*`) guidés par l'Agent Assistant et verrouillés par des Gates Déterministes bloquantes, permettant à un Chef d'Équipe (`TEAM_LEAD`) d'embarquer son équipe, ses sous-équipes et chacune de ses solutions logicielles (`Workspaces`) avec ses multiples sources dédiées (`N × git://`, `N × jira://`, `N × confluence://`) en totale autonomie,
So that aucune organisation ne démarre à froid sans modèles LLM orthogonaux configurés, qu'une équipe puisse configurer ses standards une fois et ouvrir autant de Workspaces que de solutions logicielles, et qu'aucune source (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`) ne soit publiée sans fiche Permission Broker ni politique de fraîcheur (`FR-28`, `AD-16`).

**Acceptance Criteria:**

**Given** une nouvelle instance d'ORCIA dans **⚙️ 7. Administration**
**When** l'administrateur lance `orcia://system/bootstrap/init-organization`
**Then** la Gate Déterministe bloque la validation de l'organisation tant que (1) la configuration d'authentification (OIDC et/ou Auth locale Argon2id) et le mapping RBAC ne sont pas valides et (2) `ModelRouterService` (LiteLLM) n'a pas vérifié avec succès la connectivité d'au moins **2 familles de modèles LLM distinctes** (condition requise pour l'orthogonalité des Gates Agentiques `AD-10`), puis amorce le catalogue socle.

**Given** un **Chef d'Équipe (`TEAM_LEAD`)** qui exécute `orcia://system/bootstrap/init-workspace` en self-service
**When** il configure son équipe (et d'éventuelles sous-équipes), invite ses membres et crée un ou plusieurs **Workspaces (solutions logicielles)**
**Then** il définit les standards `TEAM` et l'*Ontologie* `3_TEAM` communs à l'équipe, crée chaque *Workspace* solution avec sa surcharge `WORKSPACE` (`AD-14`), sa boîte de notifications et son *Ontologie* `3_WORKSPACE` (sans conflit avec N1/N2/`3_TEAM`), et pré-assigne à chaque membre invité son archétype de **Profil Humain** et ses rôles d'exécution ; à la première connexion de chaque membre, `orcia://system/bootstrap/init-user` se déclenche automatiquement pour confirmer son *Profil Humain* et lier ses comptes **Jira**, **Confluence** et **Git** en mode *Passthrough* (OAuth 3LO / PAT chiffré AES-256-GCM).

**Given** un Administrateur ou un **Chef d'Équipe (`TEAM_LEAD`, dans un Workspace solution ou en portée `SHARED_TEAM`)** qui exécute `orcia://system/bootstrap/init-datasource` à plusieurs reprises pour rattacher à un même Workspace **plusieurs dépôts `git://`** (ex. `git:backend`, `git:frontend`, `git:infra`), **plusieurs espaces `confluence://`** (avec filtres CQL `space_key`/labels, ex. `confluence:specs`, `confluence:adr`) et **plusieurs projets `jira://`** (avec filtres JQL, ex. `jira:product`, `jira:secops`) dédiés à la solution
**When** il soumet chaque source pour publication et liaison (`workspace_datasources`)
**Then** la Gate Déterministe rejette la publication (`HTTP 422`) tant que (a) la fiche d'habilitation YAML/Markdown du *Permission Broker* n'a pas été rédigée et signée comme **Ancre Humaine** par le propriétaire de la source et (b) le paramètre `freshness_ttl_days` n'est pas renseigné (`FR-28`, `AD-16`), avec une couverture de tests $\ge 90\%$.

## Epic 2: Ontologie Dynamique à 4 Niveaux, Simulation d'Impact (*What-If*) & RAG Hybride sur Graphe Tripartite (`Confluence ↔ Jira ↔ Git`)

Permettre aux Stewards Métier, PMs, Architectes et Tech Leads (`Hélène UJ-1`, `Antoine UJ-2`, `Yanis UJ-3`, `Arthur UJ-10`) de structurer et faire évoluer l'*Ontologie à 4 niveaux* (*1. Entreprise $\rightarrow$ 2. BU $\rightarrow$ 3. Équipe hiérarchique `3_TEAM` & Solution `3_WORKSPACE` $\rightarrow$ 4. Run*) avec héritage, extraction sémantique en temps réel, *Simulation d'Impact (What-If)* avant promotion gouvernée et triple exécution active ; d'indexer de façon incrémentale et différenciée leurs multiples espaces *Confluence* (`1..N confluence://` en *Parent-Child*), multiples projets *Jira* de référence (`1..N jira://`), multiples dépôts *Git* (`1..N git://` en *AST + Code Graph*) et schémas DB (`db://`) au sein d'un *Graphe Tripartite Multi-Sources `Confluence ↔ Jira ↔ Git`* (`halfvec(1024)` + BM25) par Workspace, et de détecter/résoudre toute obsolescence documentaire (`[STALE_WARNING]`, brique `data-freshness`) dans le module **🧬 4. Ontologie & KB**.

### Story 2.1: Modélisation Relationnelle-Graphe de l'Ontologie à 4 Niveaux (Arbre d'Équipes `3_TEAM` & Solution `3_WORKSPACE`), Héritage CTE (`< 15 ms`) & Triple Exécution Active

As a Steward Métier, Chef d'Équipe ou Architecte SI (`Hélène UJ-1`, `Antoine UJ-2`, `Marc UJ-5`),
I want structurer l'Ontologie en 4 niveaux hiérarchiques (`1_ENTERPRISE`, `2_DOMAIN`, `3_TEAM` le long de l'arbre d'équipes `Équipe Parente -> Sous-Équipe` et `3_WORKSPACE` propre à chaque solution logicielle, `4_RUN_EPHEMERAL`) avec héritage d'axiomes, synonymes métiers et triple exécution active (typage du Blackboard/Gabarits, traduction par Profil Humain, expansion RAG & contrôle d'axiomes),
So that le vocabulaire commun d'une équipe soit automatiquement partagé entre toutes ses solutions logicielles tout en permettant à chaque Workspace d'y ajouter ses propres concepts applicatifs avec une résolution en `< 15 ms` (`FR-8`, `FR-10`, `AD-7`, `NFR-PERF-3`).

**Acceptance Criteria:**

**Given** la migration Alembic créant les tables `ontology_concepts`, `ontology_relations` et `ontology_axioms` avec index sur `(level, scope_id, canonical_term)`
**When** le moteur `packages/orcia-core/ontology` résout l'ontologie effective pour un *Workspace* (solution logicielle) ou un *Workflow Run*
**Then** la requête CTE récursive PostgreSQL 18 fusionne par priorité `4_RUN_EPHEMERAL -> 3_WORKSPACE -> 3_TEAM [Sous-Équipe -> Équipe Parente] -> 2_DOMAIN -> 1_ENTERPRISE` en `< 15 ms` (jusqu'à $10^6$ concepts/relations, `NFR-PERF-3`)
**And** un concept défini au Niveau 1 (ex. `"Actif Stratégique"`) ou au Niveau `3_TEAM` d'une équipe parente est automatiquement hérité par toutes ses sous-équipes et tous ses `Workspaces` solutions, et peut être lié à un synonyme local (ex. `"Microservice Tier-1"`) dans `profile_translations_jsonb`, mais toute tentative de spécialisation violant un axiome parent marqué `immutable: true` lève une erreur bloquante `ONTOLOGY_CONFLICT` (`FR-8`, `AD-7`).

**Given** une ontologie active résolue pour une étape
**When** le service d'exécution active l'ontologie sur ses 3 plans (`FR-10`)
**Then** (1) le validateur de schémas vérifie que les entités du *Blackboard* et des *Gabarits d'Artefact* respectent les types et cardinalités ontologiques, (2) le `ProfileSemanticTranslator` traduit les concepts selon l'archétype du *Profil Humain* connecté (`Direction`, `PM/Métier`, `Architecte/Dev`, `SecOps`), et (3) le moteur d'expansion enrichit les requêtes RAG avec les synonymes et concepts reliés tout en détectant les termes bannis/ambigus
**And** les tests unitaires (`pytest` + `hypothesis`) et d'intégration (`testcontainers` PostgreSQL 18) couvrent $\ge 90\%$ de `packages/orcia-core/ontology`.

### Story 2.2: Extraction Ontologique Temps Réel (Isolée par Branche L4), Simulation d'Impact (*What-If*) & Explorateur à 4 Colonnes

As a Product Manager, Tech Lead ou Steward (`Hélène UJ-1`, `Yanis UJ-3`),
I want extraire au fil de l'eau les nouveaux concepts au Niveau 4 (Run) isolés sur la branche active, simuler l'impact (*What-If*) avant toute modification ou promotion, et piloter la promotion gouvernée dans l'Explorateur d'Ontologie à 4 colonnes,
So that au moins 5 concepts découverts en exécution soient capitalisés vers l'Ontologie d'Équipe ou de BU sans jamais polluer un Replay ni casser les workflows existants (`FR-9`, `AD-7`, `UX-DR14`).

**Acceptance Criteria:**

**Given** un nouveau terme métier ou une règle résolue en cours de conversation ou d'analyse KB
**When** l'extracteur ontologique inscrit le concept au niveau `4_RUN_EPHEMERAL` avec la référence `introduced_in_snapshot_id`
**Then** la CTE de résolution n'inclut ce concept L4 que pour les étapes appartenant à la lignée de snapshots `ACTIVE` (excluant automatiquement tout concept L4 issu d'une branche `SUPERSEDED` après un *Replay*, `AD-7`)
**And** une carte de proposition de promotion (badge `{colors.ontology-cyan}` `#0284C7`) est soumise pour gouvernance vers le Niveau 3 (validation Tech Lead / PM) ou les Niveaux 2 et 1 (Gate Humaine Steward).

**Given** un utilisateur qui ouvre le module **🧬 4. Ontologie & KB** (`g o`, `UX-DR14`) et sélectionne un concept pour le promouvoir ou modifier un axiome
**When** il ouvre le tiroir `TermPromotionDrawer` et lance la **Simulation d'Impact Ontologique (*What-If*)**
**Then** le `ImpactSimulatorService` exécute une traversée de graphe (CTE sur `ontology_relations`, `workflow_definitions` et `blackboard_snapshots`) et affiche la liste exacte des *Gabarits d'Artefact*, *Workflows* du Catalogue et *Workflow Runs* actifs impactés avant confirmation (`FR-9`, `AD-7`)
**And** les tests unitaires (`Vitest` sur l'explorateur à 4 colonnes et `pytest` sur `ImpactSimulatorService`) et d'intégration (`testcontainers` PG18) atteignent $\ge 90\%$ de couverture.

### Story 2.3: Indexation Différenciée Incrémentale Multi-Sources (N × Confluence & N × Projets Jira *Parent-Child*, N × Dépôts Code *AST + Code Graph*, Schéma DB) & Recherche Hybride `halfvec(1024)` + BM25

As a Tech Lead ou Architecte (`Yanis UJ-3`, `Arthur UJ-10`),
I want indexer de manière incrémentale et selon 3 régimes adaptés les multiples espaces Confluence et multiples projets Jira de référence d'un Workspace en découpage *Parent-Child*, ses multiples dépôts Git en découpage syntaxique *AST + Code Graph* inter-dépôts, et uniquement le schéma DDL de ses bases `db://` en vecteurs `halfvec(1024)` couplés à BM25,
So that les agents retrouvent en `< 50 ms` le contexte exact à travers tous les dépôts et espaces de la solution logicielle sans souffrir du « syndrome du cimetière wiki » ni couper les fonctions de code au milieu (`FR-23`, `AD-8`, `AR-6`, `NFR-PERF-3`).

**Acceptance Criteria:**

**Given** la migration Alembic créant les tables `kb_documents`, `kb_chunks` (avec `workspace_id`, `datasource_id`, index HNSW sur `embedding halfvec(1024)` et index GIN sur `search_tsv tsvector`) et `code_graph_edges`
**When** le worker Dramatiq `docling_indexer` indexe ou met à jour incrémentalement (par delta `SHA-256` sur chaque dépôt Git, `page.version.number` sur chaque espace Confluence ou timestamp `updated` sur chaque projet Jira du Workspace) les sources enrôlées via `init-datasource`
**Then** il applique strictement les **3 régimes d'indexation (`AD-8`)** :
1. **Régime 1 — Documentation, Multi-Espaces Confluence (`1..N confluence://`) & Multi-Projets Jira de Référence (`1..N jira://`)** : Filtrage CQL par espace (`space_key`, page racine, labels `orcia-kb`, exclusion de `draft`/`archived`) et filtrage JQL par projet Jira (uniquement *Epics, User Stories, Bugs résolus avec Root Cause, Post-mortems*) ; parsing via `Docling 2.142.1` en découpage *Parent-Child* où le **chunk enfant (`256-512` tokens)** préfixé par son *Contextual Header* (`[Alias Source : Espace/Projet > Parent > Titre | Concepts Ontologie]`) porte le vecteur `halfvec(1024)`, tandis que le **chunk parent (`1024-2048` tokens)** est stocké pour injection dans le prompt (et 1 chunk unifié `256-1024` tokens par ticket Jira de référence).
2. **Régime 2 — Multi-Codebases (`1..N git://` via `tree-sitter 0.24.0`)** : Découpage syntaxique strict par symbole AST (`150-800` tokens par fonction/classe/méthode/modèle Pydantic) sur chacun des dépôts Git dédiés au Workspace et extraction déterministe du *Code Property Graph* intra et inter-dépôts (`DEFINES`, `CALLS`, `IMPORTS`, `IMPLEMENTS_CONCEPT`, `TESTED_BY`).
3. **Régime 3 — Bases de Données (`db://`)** : Indexation exclusive du schéma DDL (`CREATE TABLE`, clés étrangères, commentaires) et de son mapping ontologique (**0 ligne transactionnelle** indexée dans le RAG).

**Given** une requête de recherche émise par un Agent ou un utilisateur dans un Workspace avec un `kb_snapshot_hash` épinglé
**When** `HybridRagService` exécute la recherche sur l'ensemble des sources du Workspace (ou un sous-ensemble filtré par `alias` de source)
**Then** il combine en `< 50 ms` (`NFR-PERF-3`) la similarité cosinus `halfvec(1024)` HNSW et le score lexical BM25 natif PostgreSQL 18 (`tsvector` + GIN + `ts_rank_cd` pondéré `A/B/C/D`, sans extension AGPL, `P7`) par *Reciprocal Rank Fusion (RRF, $k=60$)* en respectant source par source les restrictions de lecture Confluence/Jira/Git en mode *Passthrough*, et retourne les chunks parents accompagnés de leur URI et révision exacte
**And** les tests unitaires (`pytest` sur le découpage AST/Parent-Child et le calcul RRF) et d'intégration (`testcontainers` PG18 + `pgvector 0.8.7`) couvrent $\ge 90\%$ de `packages/orcia-core/rag`.

### Story 2.4: Graphe Tripartite Multi-Sources (`Confluence 1..N ↔ Jira 1..N ↔ Git 1..N`), Brique `data-freshness` & Alerte d'Obsolescence `[STALE_WARNING]`

As a Tech Lead ou Architecte (`Yanis UJ-3`, `Arthur UJ-10`),
I want relier automatiquement les pages de tous les espaces Confluence, les tickets de tous les projets Jira et les symboles/commits de tous les dépôts Git d'un même Workspace au sein d'un Graphe Tripartite de Traçabilité unifié, vérifier la fraîcheur via la brique `data-freshness` et lever une alerte `[STALE_WARNING]` dès qu'un document est expiré ou contredit par un ticket Jira plus récent ou par le code,
So that aucune décision d'architecture ou d'audit ne s'appuie sur une documentation périmée sans que l'équipe ne soit immédiatement avertie (`FR-23`, `AD-8`, `UX-DR11`, `UX-DR14`).

**Acceptance Criteria:**

**Given** l'indexation des multiples espaces `confluence://`, des multiples projets `jira://` et des multiples dépôts `git://` rattachés à un même Workspace
**When** l'extracteur de liens croisés détecte les clés de tickets des différents projets Jira du Workspace (`[A-Z][A-Z0-9]+-[0-9]+`, ex. `PAY-123`, `SEC-45`) dans les messages de commits/PRs de n'importe lequel des dépôts Git ou dans les pages de n'importe lequel des espaces Confluence
**Then** il peuple automatiquement les arêtes du **Graphe Tripartite Multi-Sources de Traçabilité** à l'échelle du Workspace : `Confluence (DOCUMENTS)` $\leftrightarrow$ `Jira (SPECIFIES / FIXES / BLOCKS)` $\leftrightarrow$ `Code Git (IMPLEMENTS_ISSUE)` $\leftrightarrow$ `Ontologie (AFFECTS_CONCEPT)`, avec une traversée CTE bornée à `depth <= 2` (`AD-8`, `P7`).

**Given** un chunk documentaire ou une page Confluence dont `now() - last_verified_at > freshness_ttl_days` **OU** qui est contredit par un ticket Jira lié plus récent ou un contrat OpenAPI/code mis à jour dans l'un des dépôts Git du Workspace (détecté lors d'une exécution de la brique de workflow `data-freshness` ou d'un signalement `UJ-3` / `UJ-10`)
**When** ce document est inspecté ou récupéré par le moteur RAG
**Then** le système injecte automatiquement le marqueur `[STALE_WARNING]` dans le contexte de l'agent, allume le badge rouge `!` (`#DC2626`, `UX-DR11`) sur l'entrée **🧬 4. Ontologie & KB** de la Sidebar, et affiche dans l'explorateur KB la liste des *Workflow Runs* actifs impactés avec l'action de mise à jour et de *Replay* (`FR-23`, `UX-DR14`)
**And** lors d'un audit Doc vs Code (`UJ-10`), si le code d'un dépôt Git diffère d'une page Confluence mais correspond à un ticket Jira `Done` plus récent relié dans le Graphe Tripartite, l'écart est qualifié de `[DOC_OBSOLETE_SUSPECTED]` avec citation du ticket Jira justificatif
**And** les tests unitaires et d'intégration couvrent $\ge 90\%$ de la construction du Graphe Tripartite multi-sources et du détecteur `data-freshness` / `[STALE_WARNING]`.

## Epic 3: Cockpit "Human-Led", Agent Assistant Adaptatif, Moteur d'Orchestration Durable & Sous-Workflows Fractals (`SUB_WORKFLOW <= 3`)

Permettre aux Product Managers, Architectes et Tech Leads (`Hélène UJ-1`, `Antoine UJ-2`, `Yanis UJ-3`, `Arthur UJ-10`) de dialoguer dans le **💬 1. Cockpit & Chat** avec l'*Agent Assistant* (DAG à 5 nœuds orientés type n8n dans le `AssistantHarness` à 5 couches, adaptant son vocabulaire au *Profil Humain*), de définir ou d'assembler conversationnellement des *Workflows-as-Code* YAML/JSON (incluant les étapes composites `SUB_WORKFLOW` jusqu'à une profondeur $\le 3$, la criticité `criticality`, le régime `execution_regime` et la politique `tie_break_policy`) avec prévisualisation graphique (`@xyflow/react`), de lancer des *Workflow Runs* épinglés récursivement par `run-lock.json` en mode *Coaching interactif*, *Fast-Path / Tâche de fond (`BACKGROUND_AUDIT`, `UJ-10`)* ou *Autonome sous Contrat (`AUTONOMOUS_CONTRACT`)*, de rédiger leurs *Ancrages Humains Obligatoires* (`human_authored_required: true`), de trancher les *Arbitrages Humains* sur options équivalentes, d'émettre des *Challenges Amont* avec simulation d'impact (*What-If*) et de déclencher un *Replay ciblé* à partir du Step $N$ (y compris à l'intérieur d'un sous-workflow enfant) dans le respect de la discipline `Intention -> Code`.

### Story 3.1: Workflow-as-Code YAML/JSON, Gabarits d'Artefact Multi-Audience, Discipline `Intention -> Code`, Épinglage Récursif `run-lock.json` & Sous-Workflows (`SUB_WORKFLOW <= 3` & Criticité)

As a Concepteur de Workflow ou Architecte (`Antoine UJ-2`, `Marc UJ-5`),
I want définir des Workflows déclaratifs YAML/JSON validés par schéma (supportant `criticality`, `execution_regime`, `tie_break_policy` et les étapes composites `SUB_WORKFLOW` sans cycle jusqu'à une profondeur $\le 3$), associer à chaque Step un Gabarit d'Artefact Multi-Audience (Markdown Humain + JSON Schema Agent), imposer la discipline `Intention -> Code` et figer récursivement toutes les dépendances dans `run-lock.json` au démarrage d'un Run,
So that chaque Workflow Run (et ses éventuels sous-workflows) soit structurellement valide, reproductible à l'identique même après 10 jours de pause et protégé contre la rétro-documentation sauvage de bugs (`FR-11`, `FR-12`, `FR-13`, `FR-15`, `FR-30`, `AD-5`, `AD-18`).

**Acceptance Criteria:**

**Given** la migration Alembic créant les tables `workflow_runs` (incluant `parent_run_id`, `parent_step_execution_id`, `root_run_id`, `nesting_depth <= 3`, `execution_regime`, `criticality`, `trigger_id`, `trigger_idempotency_key`), `run_lock_manifests` et `workflow_triggers`
**When** un concepteur enregistre un manifeste *Workflow-as-Code* YAML/JSON dans `packages/orcia-core/orchestration`
**Then** le validateur vérifie la syntaxe du DAG (Steps `AGENT | SKILL | SUB_WORKFLOW | POST_ACTION_VERIFICATION`, `criticality`, `execution_regime`, `tie_break_policy`, Agents, Skills, KBs, Gabarits, Ancrages Humains, Gates, détection statique de cycles d'appels de sous-workflows et profondeur maximale `nesting_depth <= 3`, `ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED`) et rejette toute définition invalide avec le numéro de ligne et la règle violée (`FR-11`, `FR-30`, `AD-18`)
**And** tout workflow `HIGH_CRITICAL` déclarant `execution_regime: AUTONOMOUS_CONTRACT` est rejeté (`HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`), et tout workflow d'ingénierie logicielle nominal qui comporte une étape d'écriture/modification de code sans étape amont de déclaration d'intention ou de spécification validée est rejeté (`ERR_INTENTION_BEFORE_CODE_REQUIRED`), tandis que les workflows de rétro-documentation (`Code -> Doc`) doivent obligatoirement déclarer `mode: brownfield_bootstrap` (`FR-13`, `FR-29`).

**Given** un *Workflow* valide que l'utilisateur instancie en *Workflow Run*
**When** le moteur initialise le Run
**Then** il résout toutes les URI externes (`db://`, `git://`, `nexus://`, `confluence://`, `jira://`), les surcharges à 4 niveaux et l'arbre récursif des sous-workflows (`sub_workflow_locks`), et inscrit de manière immuable dans `run_lock_manifests` (`run-lock.json`) les triplets `(uri, resolved_version, sha256)` et le `kb_snapshot_hash` (`FR-15`, `FR-30`, `AD-5`)
**And** chaque *Gabarit d'Artefact* (`FR-12`) compile simultanément la vue documentaire Markdown (avec variables Jinja/Mustache et sections de découpage) pour le Canvas humain et le contrat JSON/YAML Schema typé par l'Ontologie pour les Steps aval
**And** les tests unitaires (`pytest` + `hypothesis`) et d'intégration (`testcontainers` PG18 + SeaweedFS S3) couvrent $\ge 90\%$ du validateur de workflows, des gabarits et du verrouillage `run-lock.json`.

### Story 3.2: Moteur d'Orchestration Durable, Checkpoints Immuables du Blackboard, Isolation des Sous-Workflows (`SUB_WORKFLOW`), Hydratation JIT & Exécution Tri-Modale

As a Tech Lead ou Architecte (`Yanis UJ-3`, `Arthur UJ-10`),
I want exécuter les Steps (y compris les étapes composites `SUB_WORKFLOW`) via un moteur durable basé sur des checkpoints immuables du Blackboard (séparant brouillon et snapshot validé et isolant lexicalement les Blackboards parents/enfants), une hydratation Just-In-Time filtrée (`orcia://`) et un mode tri-modal (`INTERACTIVE_COACHING`, `BACKGROUND_FAST_PATH` et `AUTONOMOUS_CONTRACT`),
So that les Workflows longs et imbriqués survivent à tout redémarrage serveur, partagent un plafond budgétaire commun sur `root_run_id`, ne divulguent que le contexte déclaré à chaque Step et permettent d'exécuter un audit complet Doc vs Code en tâche de fond sans blocage intempestif (`FR-14`, `FR-30`, `AD-2`, `AD-12`, `AD-13`, `AD-18`, `AR-3`, `NFR-REL-1`, `NFR-SEC-3`).

**Acceptance Criteria:**

**Given** la migration Alembic créant les tables `step_executions` (colonnes `step_type`, `execution_mode`, `status`, `draft_artifact_jsonb`, `draft_cas_key`, `step_memlog_jsonb`) et `blackboard_snapshots` (protégée par trigger PostgreSQL append-only `BEFORE UPDATE OR DELETE RAISE EXCEPTION`, `NFR-SEC-3`)
**When** le worker d'orchestration démarre l'étape $k$ d'un *Workflow Run*
**Then** le `JitStepHydrator` (`AD-13`) n'injecte dans le contexte de l'*Agent Exécuteur* (routé de façon agnostique via LiteLLM vers OpenAI, Anthropic, Gemini ou Ollama/vLLM local, `FR-14`) que la directive de l'étape $k$ et les artefacts amont explicitement déclarés dans `inputs` via `orcia://runs/{run_id}/steps/{step_key}/artifacts/{artifact_key}` (0 instruction des étapes futures $k+1..N$ et 0 artefact non déclaré)
**And** tant que l'étape est en `EXECUTING_AGENT` ou `EVALUATING_GATES`, le livrable candidat est écrit dans `step_executions.draft_artifact_jsonb` et ses raisonnements/hypothèses dans `step_executions.step_memlog_jsonb` ; ce n'est qu'au statut `COMMITTED` qu'un snapshot immuable est ajouté dans `blackboard_snapshots` (`AD-2`, `AR-3`, `NFR-REL-1`)
**And** lorsqu'une étape est de type `SUB_WORKFLOW`, le moteur instancie un `workflow_run` enfant (`parent_run_id`, `parent_step_execution_id`, `root_run_id`, `nesting_depth = parent.nesting_depth + 1 <= 3`) doté d'un *Blackboard* propre alimenté par `input_mapping`, partageant le budget `max_cost_usd` du `root_run_id`, et reversant ses seules sorties déclarées via `output_mapping` au snapshot parent (`FR-30`, `AD-2`, `AD-18`).

**Given** un *Workflow Run* lancé en mode **`FAST_PATH` / `BACKGROUND_AUDIT` (Tâche de fond, `UJ-10`)** après signature des éventuelles *Ancres Humaines* initiales
**When** l'*Agent Exécuteur* rencontre une ambiguïté ou une divergence entre Documentation (Confluence/Jira) et Codebase (`git://`)
**Then** au lieu de bloquer le worker à mi-parcours, il inscrit dans `step_memlog_jsonb` et dans l'artefact un marqueur structuré `[ASSUMPTION]`, `[BUG_CODE_SUSPECTED]` ou `[DOC_OBSOLETE_SUSPECTED]`, poursuit l'exécution jusqu'au rapport de comparaison final, consolide tous les points d'arbitrage et notifie l'initiateur (`Arthur`) en `< 500 ms` via SSE (`AD-13`)
**And** les tests unitaires (`pytest` + `DeterministicCassetteLLM`) et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ de `packages/orcia-core/orchestration` et `blackboard`.

### Story 3.2a: Phase A — Socle du Monolithe Modulaire (`packages/orcia-kernel`), Workspace `uv` à 4 Packages, Rupture des 3 Cycles, Découplage `schemas/` & `<domaine>/errors.py`, Point d'Assemblage Unique & Garde-Fou `import-linter`

As a Architecte Système ou Tech Lead (`Winston`, `Marc UJ-5`),
I want extraire un noyau partagé minimal `packages/orcia-kernel` (`0` dépendance métier), structurer le dépôt Python en un workspace `uv` à 4 packages (`packages/orcia-kernel`, `packages/orcia-core`, `apps/api`, `apps/worker`), rompre les 3 cycles de dépendances entre domaines (`blackboard ↔ orchestration`, `catalog ↔ bootstrap`, `permissions ↔ bootstrap`), déplacer les 10 fichiers de schémas HTTP (`orcia_core/schemas/`, `2 060` lignes) vers `apps/api/src/orcia_api/schemas/`, éclater `domain/exceptions.py` (`377` lignes, risque `CRITICAL` à 59 dépendants) en `<domaine>/errors.py`, supprimer les 3 singletons d'import `_DEFAULT_*_SERVICE` au profit d'un point d'assemblage unique (`lifespan` + `Depends`), déplacer les classes `InMemory*` dans `tests/unit/fakes/`, et verrouiller le graphe d'imports avec `import-linter` en CI,
So that chaque domaine métier de `packages/orcia-core` évolue et soit testé de manière isolée sans dépendance circulaire, sans fuite de contrat REST dans le domaine et avec une frontière architecturale vérifiée mécaniquement à chaque commit (`AD-1`, `AD-17`, `AD-19`, `AR-8`, `M1..M5`, `P3`, `P4`, `Q1: 1A`, `Q4: 4A`).

**Acceptance Criteria:**

**Given** le dépôt Python restructuré en workspace `uv` à **4 packages** (`pyproject.toml` racine + `packages/orcia-kernel`, `packages/orcia-core`, `apps/api`, `apps/worker` et `uv.lock`) avec bornes minimales alignées sur la Spine (`P3`, `Q1: 1A`)
**When** `packages/orcia-kernel/src/orcia_kernel/` est créé et que les 3 cycles de dépendances de `packages/orcia-core` sont résolus (`M1`, `M2`)
**Then** `orcia_kernel` expose uniquement les primitives universelles (`ids.py` UUIDv7, `enums.py` incluant `StepExecutionState`, `errors.py` avec la classe de base `OrciaDomainError`, `events.py`, et `ports.py` avec `BlackboardPort`, `OutboxRelayPort`, `LLMPort`, `ObjectStoragePort`, `SandboxPort`, `ClockPort`) sans importer aucun domaine métier
**And** les 3 cycles identifiés par GitNexus sont éliminés : (1) `blackboard` n'importe plus `orchestration` (utilise `orcia_kernel.enums.StepExecutionState` et expose `BlackboardPort`), (2) `catalog/service.py` n'importe plus `bootstrap/workflows.py` (les constantes de seeds système sont définies dans `catalog/seeds.py`), et (3) `permissions/broker.py` n'importe plus `bootstrap/workflows.py` (la constante `INIT_USER_WORKFLOW_URI` est définie dans `permissions/seeds.py` et consommée à sens unique par `bootstrap`).

**Given** le découplage des schémas HTTP (`M3`), des exceptions métier (`M4`) et du point d'assemblage (`M5`)
**When** la restructuration est appliquée et que la CI exécute `lint-imports` (`import-linter 2.7`, `P4`)
**Then** les 10 fichiers de `packages/orcia-core/src/orcia_core/schemas/` (`2 060` lignes) sont déplacés dans `apps/api/src/orcia_api/schemas/<domaine>.py` (`0` fichier restant dans `orcia_core/schemas/`), `domain/exceptions.py` (`377` lignes) est remplacé par `<domaine>/errors.py` dans chaque domaine (héritant de `orcia_kernel.errors.OrciaDomainError`) avec un registre HTTP RFC 9457 centralisé dans `apps/api/src/orcia_api/errors/registry.py`, les 3 singletons d'import `_DEFAULT_AUTH_SERVICE`, `_DEFAULT_CATALOG_SERVICE` et `_DEFAULT_ORCHESTRATION_SERVICE` sont supprimés de `apps/api/src/orcia_api/routers/{auth,catalog,orchestration}.py` au profit d'une injection exclusive dans `apps/api/src/orcia_api/dependencies.py` (`lifespan` $\rightarrow$ `app.state` + `Depends()`), et les stores `InMemory*` sont isolés dans `tests/unit/fakes/`
**And** `lint-imports` vérifie avec **`0` violation** : (a) l'ordre strict des couches `orcia_kernel` $\leftarrow$ `orcia_core` $\leftarrow$ (`orcia_api`, `orcia_worker`), (b) l'indépendance entre domaines pairs (`auth`, `permissions`, `catalog`, `ontology`, `rag`, `blackboard`, `gates`, `audit_finops`), (c) l'interdiction d'importer `<domaine>._internal` depuis l'extérieur du domaine (`Q4: 4A`), et (d) l'interdiction de `fastapi`, `sqlalchemy`, `dramatiq`, `dbos`, `redis`, `litellm` dans `orcia_kernel` et dans les modèles/ports de `orcia_core`, avec couverture unitaire $\ge 90\%$.

### Story 3.2s: Spike DBOS Transact sur PostgreSQL 18 (Timebox 2–3 Jours, Validation Pause/Reprise, Fork, Schedule, Idempotence & Unit of Work SQLAlchemy)

As a Architecte Système ou Tech Lead (`Winston`, `Amelia`),
I want mener en parallèle de `Story 3.2a` (`depends_on: []`, timebox stricte de 2 à 3 jours, `ARCH-P2-SPIKE`) un spike technique instrumenté de `DBOS Transact` (`dbos 2.14.0`, MIT) sur PostgreSQL 18 via `testcontainers-python`,
So that le patron exact de session SQLAlchemy (`@DBOS.transaction` vs `AsyncSession` Unit of Work) et les 8 critères de sortie Go/No-Go soient formellement prouvés avant l'écriture des repositories `SQLAlchemy 2.1 Asyncio` (`ARCH-P1`) et l'intégration du moteur durable en `Story 3.2b` (`AD-2`, `AD-13`, `AD-18`, `OQ-01`, `C1`, `C2`).

**Acceptance Criteria:**

**Given** un environnement de test isolé exécutant PostgreSQL 18 + `pgvector` et Redis 7.4 via `testcontainers-python` avec `dbos 2.14.0` (`depends_on: []`, exécutable immédiatement en parallèle de `Story 3.2a`)
**When** la suite de validation du spike exécute les scénarios d'orchestration durable et de défaillance
**Then** les **8 critères de sortie Go/No-Go** suivants sont validés par des tests automatisés reproductibles : (1) pause durable sans consommation de thread/worker (`DBOS.recv`) et reprise exacte après crash brutal (`SIGKILL`) du processus (`DBOS.send`), (2) relance ciblée à partir d'une étape $N$ (`DBOS.fork_workflow(workflow_id, start_step=N)`) sans ré-exécuter les étapes $1..N-1$, (3) planification déclarative périodique (`@DBOS.scheduled`), (4) déduplication transactionnelle stricte par `SetWorkflowID("<trigger_id>:<idempotency_key>")` (`0` doublon en concurrence), (5) cohabitation transactionnelle avec le *Blackboard* en ajout seul (`blackboard_snapshots` protégé par trigger PostgreSQL `BEFORE UPDATE OR DELETE RAISE EXCEPTION`), (6) cohabitation sans conflit de pool ou de boucle d'événements avec `Dramatiq 2.1.0` pour le délestage CPU/I/O lourd, (7) intégration propre avec la *Unit of Work* `SQLAlchemy 2.1 Asyncio` (`asyncpg`) fixant le patron de session pour `ARCH-P1`, et (8) testabilité déterministe complète sous `pytest` + `testcontainers-python` (`< 30 s` de démarrage/nettoyage)
**And** le spike livre le rapport de décision **`docs/implementation-artifacts/tech-lead-reports/3-2s-dbos-spike-report.md`** statuant **Go / No-Go** (`C1`, `C2`) ; l'intégration de DBOS dans `Story 3.2b` (`ARCH-P2`) est conditionnée à un verdict **Go** (avec plan de repli documenté en cas de No-Go).

### Story 3.2b: Phase B — Persistance Réelle `SQLAlchemy 2.1 Asyncio` (`asyncpg`), Intégration du Moteur Durable `DBOS Transact` sur PostgreSQL 18, Stockage CAS `SeaweedFS` (`ObjectStoragePort`), `LiteLLMAdapter` & Instrumentation `OpenTelemetry`

As a Architecte Système ou Ingénieur Plateforme (`Winston`, `Karim UJ-9`),
I want implémenter les repositories `SQLAlchemy 2.1 Asyncio` (`asyncpg`) et la *Unit of Work* dans le sous-package `_internal/` de chaque domaine sur les migrations Alembic `0001..0011` en suivant le patron de session validé par le spike `Story 3.2s` (`ARCH-P1` dépendant de `ARCH-P2-SPIKE`, incluant la recherche hybride SQL `halfvec` + `tsvector` GIN `ts_rank_cd` RRF `P7`), intégrer `DBOS Transact` (`dbos 2.14.0`, MIT) sur PostgreSQL 18 (sous réserve du verdict **Go** de `Story 3.2s`, `ARCH-P2`), brancher `SeaweedFS` (`Apache-2.0`) derrière `ObjectStoragePort` (`ARCH-P6`), implémenter `LiteLLMAdapter` derrière `LLMPort`, et instrumenter la chaîne avec `OpenTelemetry` (`ARCH-P9`),
So that tout `Workflow Run` et toute entité d'ORCIA soient réellement persistés dans PostgreSQL 18 et SeaweedFS, survivent à tout redémarrage de processus avec reprise transactionnelle ACID (`DBOS.recv`, `DBOS.fork_workflow`, `SetWorkflowID`), remplacent proprement le moteur maison en mémoire de `Story 3.2` sans régression ni code mort, et propagent un `trace_id` W3C réel de bout en bout (`AD-2`, `AD-5`, `AD-8`, `AD-10`, `AD-12`, `AD-13`, `AD-18`, `AD-19`, `P1`, `P2`, `P6`, `P7`, `P9`, `OQ-01`, `OQ-03`, `C1`, `C2`, `C4`, `C6`).

**Acceptance Criteria:**

**Given** le verdict **Go** du spike `Story 3.2s` (`ARCH-P2-SPIKE`) et l'achèvement de `Story 3.2a` (`ARCH-M5`, `ARCH-P3`, `ARCH-P4`)
**When** `DBOS Transact` (`dbos 2.14.0`) est intégré dans `apps/worker` et `packages/orcia-core/orchestration/_internal/` et qu'un *Workflow Run* s'exécute, se met en pause sur `WAITING_FOR_HUMAN_ARBITRATION` (`DBOS.recv`), exécute un `SUB_WORKFLOW` enfant (`nesting_depth <= 3`), est planifié via `@DBOS.scheduled` ou fait l'objet d'un *Rewind / Replay* à partir du Step $N$ (`DBOS.fork_workflow`)
**Then** chaque transition d'étape (`@DBOS.step()`) et chaque création de snapshot `blackboard_snapshots` (`ACTIVE` / `SUPERSEDED`) est persistée de manière transactionnelle dans PostgreSQL 18 sans consommer de worker actif pendant les pauses, reprend exactement à l'étape en pause après extinction et redémarrage complet du processus, et `SetWorkflowID("<trigger_id>:<idempotency_key>")` garantit l'unicité stricte d'instanciation en complément de la contrainte SQL `UNIQUE` (`AD-2`, `AD-13`, `AD-18`, `P2`)
**And** les tests de la `Story 3.2` (`tests/unit/test_durable_orchestration_and_blackboard.py`) sont conservés comme tests de non-régression et restent verts ; le code du moteur maison remplacé (`DurableOrchestrationEngine` en mémoire et `step_runner.py` Dramatiq) est supprimé (`0` code mort) ; le rapport Tech Lead de `3.2b` (`docs/implementation-artifacts/tech-lead-reports/3-2b-tech-lead-report.md`) documente explicitement ce remplacement (`C4`).

**Given** les 11 migrations Alembic (`0001..0011`) appliquées dans le schéma PostgreSQL `public` unique (`Q4: 4A`) et le conteneur **SeaweedFS `4.17` (`chrislusf/seaweedfs`, `Apache-2.0`)** remplaçant MinIO dans `docker-compose.yml` (`OQ-03`, `P6`)
**When** les services des domaines (`auth`, `catalog`, `permissions`, `bootstrap`, `ontology`, `rag`, `orchestration`, `blackboard`) sont invoqués via `apps/api` ou `apps/worker`
**Then** chaque domaine persiste et relit ses entités via son repository `SQLAlchemy 2.1 Asyncio` (`asyncpg`, Unit of Work alignée sur `Story 3.2s`) encapsulé dans `<domaine>/_internal/` (`ARCH-P1`, `C2`, `C6`), `HybridRagService` exécute en SQL réel la recherche hybride `pgvector halfvec(1024)` HNSW + `tsvector` GIN (`ts_rank_cd` pondéré `A/B/C/D`) fusionnée par RRF (`k=60`) et la CTE du graphe tripartite bornée à `depth <= 2` (`P7`), l'adaptateur S3 v4 `SeaweedFS` implémente `ObjectStoragePort` (`cas/<sha256>`), `LiteLLMAdapter` implémente `LLMPort` aux côtés de `DeterministicCassetteLLM`, et `OpenTelemetry` (`opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy`) injecte le `trace_id` W3C réel dans `structlog`, `audit_ledger` et toutes les enveloppes **RFC 9457** (`P1`, `P9`)
**And** les tests d'intégration sur conteneurs éphémères réels `testcontainers-python` (PostgreSQL 18 + `pgvector`, Redis 7.4, SeaweedFS) valident la persistance et la reprise après redémarrage avec une couverture $\ge 90\%$ et `lint-imports` à `0` violation.

### Story 3.2c: Phase C — Bus d'Événements de Domaine, Table Outbox Transactionnelle (`domain_events_outbox`) Indépendante du Moteur (`OutboxRelayPort`) & Plugins `entry_points`

As a Architecte Système ou Tech Lead (`Winston`, `Marc UJ-5`),
I want créer la table Outbox transactionnelle `domain_events_outbox` (migration Alembic `0012`, indépendante du moteur d'orchestration et dépendant uniquement de `ARCH-P1`), publier dans la même transaction SQL que le changement d'état du Run/Step les événements immuables du domaine (`StepCompleted`, `ArtifactProduced`, `GateEvaluated`, `RunTerminated`, `HumanArbitrationRequested`), relayer ces événements de manière idempotente via le port `OutboxRelayPort` (implémentable avec Dramatiq ou DBOS) vers les abonnés découplés (`audit_finops`, `ontology`, `sse`, réveil de déclencheurs), et charger les extensions internes via les `entry_points` Python (`orcia.uri_resolvers`, `orcia.llm_gateways`),
So that le moteur d'orchestration (`orchestration/engine.py`) reste compact et fermé à la modification (principe Open/Closed) lorsque les Epics 4 à 7 ajoutent de nouveaux effets secondaires ou connecteurs, sans dépendre du moteur d'orchestration choisi ni jamais perdre un événement d'audit ou de notification en cas de crash entre l'écriture SQL et le traitement aval (`AD-12`, `AD-19`, `AR-8`, `M6`, `M7`, `Q2: 2A`, `Q3: 3A`, `C3`).

**Acceptance Criteria:**

**Given** la migration Alembic immuable `0012_domain_events_outbox` créant dans le schéma `public` la table `domain_events_outbox` (`event_id UUIDv7 PK`, `event_type`, `aggregate_type`, `aggregate_id`, `run_id`, `workspace_id`, `payload_jsonb`, `trace_id`, `status PENDING | PUBLISHED | FAILED`, `attempts`, `created_at`, `published_at`) avec index partiel sur `status = 'PENDING'` et test complet `upgrade()` / `downgrade()` (`ARCH-M6.depends_on = [ARCH-P1]` uniquement, `C3`)
**When** une transition d'état se produit sur `workflow_runs`, `step_executions` ou `blackboard_snapshots`
**Then** le moteur d'orchestration n'effectue d'appels directs synchrones que pour les décisions bloquantes du flux d'exécution (`permissions`, passage des `gates` et arbitrage humain), et écrit dans la **même transaction SQL (`AsyncSession`)** les événements immuables de `orcia_kernel.events` (`StepCompleted`, `ArtifactProduced`, `GateEvaluated`, `RunTerminated`, `HumanArbitrationRequested`) dans `domain_events_outbox` (`M6`, `Q2: 2A`)
**And** le relais Outbox abstrait derrière **`orcia_kernel.ports.OutboxRelayPort`** (avec deux implémentations possibles dans `apps/worker` : acteur `Dramatiq` ou workflow planifié `DBOS`, utilisant `SELECT ... FOR UPDATE SKIP LOCKED` par lots, `C3`) distribue de manière idempotente (`0` doublon par `event_id`) ces événements aux abonnés découplés (`audit_finops` pour l'écriture `audit_ledger`/coûts, `ontology` pour l'extraction L4 asynchrone, `sse` pour la diffusion Redis Pub/Sub `< 500 ms` et le réveil des triggers/sous-workflows), sans qu'`orchestration/engine.py` n'importe `audit_finops`, `ontology` ni `sse`.

**Given** les groupes de plugins Python `entry_points` `orcia.uri_resolvers` (`git://`, `jira://`, `confluence://`, `db://`, `nexus://`, `orcia://`) et `orcia.llm_gateways` déclarés dans `packages/orcia-core/pyproject.toml` (en limitant la création de nouveaux ports à la Règle de Trois, `M7`, `Q3: 3A`)
**When** `FederatedUriResolver` ou `ModelRouterService` démarre au sein du point d'assemblage
**Then** il découvre et enregistre dynamiquement via `importlib.metadata.entry_points` tous les résolveurs d'URI et passerelles LLM installés sans modifier le cœur du domaine
**And** un test d'intégration (`testcontainers` PG18 + Redis) simulant un crash immédiatement après le `COMMIT` SQL mais avant le relais Outbox vérifie que 100 % des événements en attente sont livrés sans doublon au redémarrage, avec couverture $\ge 90\%$ et `lint-imports` à `0` violation.

### Story 3.2d: Phase D — Migration Frontend SPA Pure `Vite 6 + TanStack Router v1`, Intégration `TanStack Query v5` / `Tailwind v4` / `@xyflow/react v12` / `openapi-fetch` & Découpage par Fonctionnalité `features/<domaine>/`

As a Architecte Frontend ou UX Designer (`Sally`, `Amelia`),
I want mener **en parallèle de `Story 3.2b` et `Story 3.2c`** (dès la fin de `Story 3.2a`, `depends_on: [ARCH-P3, ARCH-M3]`, `C7`) la migration de `apps/web` de Next.js App Router vers une SPA pure `Vite 6 + TanStack Router v1`, installer et configurer `@tanstack/react-query 5.90`, `tailwindcss 4.3`, `@xyflow/react 12.12` et `openapi-fetch 0.17`, générer le client OpenAPI découpé par domaine à partir de `apps/api/src/orcia_api/schemas/`, et organiser `apps/web/src/` en routes minces (`src/routes/`) et modules fonctionnels isolés (`src/features/<domaine>/`),
So that le frontend élimine 100 % de la surface d'attaque serveur Node.js/RSC, divise par 8 son empreinte mémoire en production (`nginx:alpine` statique), supprime les erreurs d'hydratation SSR sur `@xyflow/react` et le buffering SSE, et permette de développer les Epics 3 à 7 dans des modules frontend découplés sans attendre la fin des travaux backend de persistance et d'outbox (`AD-1`, `AD-15`, `AD-19`, `AR-1`, `AR-8`, `P8`, `M11`, `OQ-02`, `C7`).

**Acceptance Criteria:**

**Given** l'achèvement de `Story 3.2a` (`ARCH-P3`, `ARCH-M3`) et le remplacement de Next.js dans `apps/web/package.json` par `vite ^6.4.1`, `@vitejs/plugin-react ^4.5.2`, `@tanstack/react-router ^1.166.2`, `@tanstack/router-plugin ^1.166.2`, `@tanstack/react-query ^5.90.0`, `tailwindcss ^4.3.0`, `@xyflow/react ^12.12.0` et `openapi-fetch ^0.17.0` (`P8`, `OQ-02`, `C7`)
**When** les routes de `apps/web` sont compilées et exécutées en développement et en build de production (en parallèle de `Story 3.2b` et `Story 3.2c`)
**Then** les 10 fichiers de routes existants (`75` lignes dans `apps/web/src/app/`) sont convertis vers `apps/web/src/routes/` avec `createRootRouteWithContext<{ queryClient: QueryClient }>()`, validation typée des paramètres de recherche d'URL (`validateSearch`) et préchargement déclaratif (`loader`), sans aucun serveur Node.js/RSC en production.

**Given** l'organisation modulaire par fonctionnalité (`M11`, `AD-19`) et la génération du SDK OpenAPI 3.1 (`packages/api-client`)
**When** `pnpm turbo run lint typecheck test` est exécuté en CI
**Then** `apps/web/src/` est structuré en `src/routes/` (assemblage mince) et `src/features/<domaine>/` (`cockpit`, `inbox`, `catalog`, `ontology`, `gates`, `finops`, `admin`, `workspaces`), une règle ESLint interdit tout import direct entre deux dossiers `features/<domaine_A>/` et `features/<domaine_B>/`, `@orcia/ui` (`packages/ui`) ne comporte aucun import de `@tanstack/react-router`, `next/*` ni `@orcia/api-client`, et `packages/api-client/src/generated/` est régénéré avec `0 diff` depuis `apps/api/src/orcia_api/schemas/`
**And** les tests unitaires (`Vitest 3.2` + `@testing-library/react`) et E2E (`@playwright/test 1.52`) passent à 100 % avec couverture $\ge 90\%$.

### Story 3.2e: Séparation Core et Pack SDLC (`orcia-pack-sdlc`) & Interface de Connecteur Unique (`ConnectorPort`, Registre `orcia.connectors`, Table `connector_schemes`) — Avenant A2

As a Architecte Système ou Ingénieur Plateforme (`Winston`, `Karim UJ-9`),
I want — après `Story 3.2c` (done), en parallèle de `Story 3.2d` — sortir tout le vocabulaire SDLC du kernel et de l'orchestration vers un premier pack métier `packages/orcia-pack-sdlc` (P0-1), et unifier l'ajout de types de source derrière une interface de connecteur unique `ConnectorPort` branchée sur `FederatedUriResolver` via le registre `orcia.connectors` et la table `connector_schemes` (P0-2), en commençant par déplacer les données de démonstration hors des packages de domaine (Étape 0, `DEC-SEED-01`),
So that ORCIA devienne une plateforme réellement agnostique où un vertical hors IT ou un nouveau connecteur (`sap://`) s'ajoute sans modifier le Core, tout en conservant intégralement le comportement SDLC du MVP (`FR-13` portée par le pack) (`AD-5`, `AD-19`, `AD-20`, `NFR-EXT-1`, `NFR-ISO-1`, audit `L1..L11`, `K1`, `K2`, `K6`, `K9`).

**Acceptance Criteria:**

- **AC-E0 (`DEC-SEED-01`)** : **Given** les données de démonstration présentes dans `rag/__init__.py:L49-95` et `orchestration/seeds.py:L29-158` (Étape 0, `DEC-SEED-01`), **When** l'Étape 0 de la story est livrée, **Then** les données de référence sont déplacées dans `bootstrap/seeder.py` (upserts idempotents `INSERT ... ON CONFLICT DO UPDATE`) et les jeux de démonstration dans `tests/fixtures/` ou dans le pack SDLC, sans aucune donnée de démonstration restante dans les `__init__.py` et `seeds.py` des domaines du Core (`AD-20` règle 5).
- **AC-E1** : **Given** le package `packages/orcia-pack-sdlc` ajouté comme 5ᵉ package du workspace `uv` et déclarant ses `entry_points` (`orcia.connectors` pour `git`, `jira`, `confluence`, `nexus` ; `orcia.workflow_policies` pour la règle `FR-13` ; registre de marqueurs `sdlc.*` ; format de catalogue `BMAD_PACK` ; `orcia.indexers` pour les régimes code AST et Jira et le graphe tripartite) (P0-1), **When** `.venv/bin/lint-imports` est exécuté, **Then** un nouveau contrat `import-linter` « `orcia_kernel` et `orcia_core` n'importent jamais `orcia_pack_sdlc` » est KEPT (4 contrats au total, `0` violation).
- **AC-E2** : **When** `grep -rnIiE "writes_code|BUG_CODE|DOC_OBSOLETE|brownfield|confluence|git://|jira" packages/orcia-kernel packages/orcia-core/src/orcia_core/orchestration` est exécuté, **Then** le grep retourne **`0` ligne** (référence au commit `8678266` : `33` lignes dans 7 fichiers) **And** `WorkflowStepSpec` expose des `tags` / `policies` génériques à espace de noms (`sdlc.writes_code`, `sdlc.declares_intention`, `sdlc.mode.brownfield_bootstrap`) en *Expand → Contract* sur le schéma Pydantic et l'API (les 3 booléens et `mode` dépréciés restent acceptés et traduits pendant l'*Expand*), `MemlogMarkerType` devient une chaîne `<namespace>.<marker>` validée par registre, une politique référencée mais non enregistrée est rejetée (`ERR_UNKNOWN_WORKFLOW_POLICY`), et la règle `FR-13` (`yaml_validator.py:L158-185`) s'applique à l'identique via le plugin du pack (tests de `Story 3.1` conservés en non-régression).
- **AC-E3** : **Given** `orcia_kernel.ports.ConnectorPort` (`capabilities()`, `fetch(uri)`, `invoke(action, payload, idempotency_key)`, `health()`, `map_error(exc)`) et le registre `orcia.connectors` branché sur `FederatedUriResolver` sans changer la signature publique de `parse_federated_uri` (risque GitNexus **CRITICAL**, 7 flux) (P0-2), **When** un connecteur factice `sap://` est ajouté sous `tests/fixtures/plugins/orcia_connector_sap_fake/` et enregistré par `entry_points`, **Then** il est résolu de bout en bout **sans qu'aucun fichier du Core ne soit modifié** (`git diff --stat packages/orcia-kernel packages/orcia-core` vide pour ce connecteur), en **< 150 lignes** (`wc -l`), et passe le kit de conformité `tests/conformance/connector_port/` (`NFR-EXT-1`).
- **AC-E4** : **Then** `ALLOWED_SCHEMES` (`catalog/cas_resolver.py:L24`) et les 4 `Literal` de schémas (`catalog/models.py:L14`, `permissions/models.py:L23`, `permissions/broker_models.py:L16`, `rag/models.py:L57`) sont supprimés au profit d'une source de vérité unique, et les 7 flux GitNexus traversant `parse_federated_uri` (`import_bmad_skill_pack`, `resolve_effective_workflow`, `instantiate_workflow_run` API et `run_lock_service`, `import_from_archive_bytes`, `build_default_orchestration_setup_service`, `build_default_federated_catalog_service`) restent verts.
- **AC-E5** : **Given** les 4 contraintes `CHECK` de schémas (`0002:L97-98`, `0002:L174`, `0004:L24-25`, `0004:L60-61`), **When** les nouvelles révisions Alembic `0013` (*Expand* : table `connector_schemes` à PK UUIDv7 et `scheme` UNIQUE, *seed* idempotent des 5 schémas existants, clés étrangères `NOT VALID` puis `VALIDATE` depuis `workspace_datasources`, `user_passthrough_credentials`, `permission_broker_policies`, `permission_broker_tickets`) et `0014` (*Contract* : suppression des 4 `CHECK`) sont appliquées puis annulées, **Then** `upgrade()` et `downgrade()` (qui restaure les `CHECK`) passent sur `testcontainers` PostgreSQL 18 **avec des lignes préexistantes conservées** dans les 4 tables, en SQL brut (`op.execute(sa.text(...))`, aucun modèle ORM importé) et sans modifier aucune révision existante (`0001..0012`).
- **AC-E6** : **Then** les schémas HTTP restent dans `apps/api/src/orcia_api/schemas/` et le SDK `packages/api-client` n'est régénéré (0-diff) qu'après la livraison de `Story 3.2d`.
- **AC-E7** : **Then** la couverture unitaire est $\ge 90\%$ et les 5 couches de tests (`AD-17`) sont livrées, avec le rapport Tech Lead `docs/implementation-artifacts/tech-lead-reports/3-2e-...-tech-lead-report.md`.

### Story 3.2f: Exécution Réelle des Étapes (`orcia.step_executors`), Taxonomie d'Erreurs & `ConnectorInvoker` (Relances, `Retry-After`, Coupe-Circuit) et Preuve sur un Vertical Finance (`core-without-sdlc`) — Avenant A2

As a Tech Lead ou Ingénieur Plateforme / SRE (`Yanis UJ-3`, `Karim UJ-9`),
I want — après `Story 3.2e` — que chaque étape durable DBOS appelle un exécuteur réel résolu dans le registre `orcia.step_executors` (P0-3, reprise de l'écart `EC-1` de `Story 3.2b`), que tout appel sortant passe par un `ConnectorInvoker` appliquant la taxonomie d'erreurs du kernel (P0-4), et que le Core prouve son agnosticisme sur un workflow Finance exécuté pack SDLC désinstallé (P2-2),
So that ORCIA exécute enfin du travail réel de bout en bout via l'API, reprenne après redémarrage, distingue panne passagère et erreur métier sans relances coûteuses ni doublons, et ne repose plus sur un moteur simulé, un état global ou une API privée de DBOS (`AD-2`, `AD-12`, `AD-13`, `AD-20`, `NFR-ISO-1`, `NFR-SEC-4`, `PROC-01`, audit `K3`, `K4`, `L5`, `L6`).

**Acceptance Criteria:**

- **AC-F1 (`PROC-01`)** : **Given** le registre `orcia.step_executors` (`AGENT`, `SKILL`, `SUB_WORKFLOW`, `HUMAN_TASK`, `HTTP_ACTION`) et un moteur DBOS unique injecté par le *Composition Root* (`lifespan` dans `apps/api/src/orcia_api/dependencies.py`, `on_startup` dans `apps/worker`) (P0-3), **When** un *Workflow Run* est instancié via l'API (`POST /api/v1/runs`), exécute ses étapes, se met en pause sur une étape `HUMAN_TASK`, puis le processus est arrêté et redémarré, **Then** le run reprend exactement à l'étape en pause et termine avec des livrables produits par les exécuteurs réels (cassettes `DeterministicCassetteLLM` en CI), **sans aucun contenu simulé ou figé** (`PROC-01`).
- **AC-F2** : **Then** le moteur simulé en mémoire (`DurableOrchestrationEngine`, `draft_payload` factice de `engine.py:L258-275`, marqueurs de `engine.py:L349-388`) et le contenu figé de `_internal/dbos_engine.py:L244-247` sont supprimés (`0` code mort), les tests de `Story 3.2` et des 8 fichiers de tests appelant `engine.*` sont repris en non-régression sur le moteur réel, et `grep -rn "_recover_pending_workflows\|_ACTIVE_ENGINE" packages apps` retourne `0` ligne (API publique DBOS uniquement, `AD-2` règle 3).
- **AC-F3** : **Given** la taxonomie `orcia_kernel.errors` (`TransientInfraError(retry_after_s)`, `RateLimitedError`, `UpstreamTimeoutError`, `FunctionalConnectorError`, `PolicyDeniedError`, `PermanentInfraError`) et le `ConnectorInvoker` exécuté comme étape durable DBOS (P0-4), **When** un connecteur de test répond successivement `429` avec `Retry-After: 2` puis `200`, puis un autre répond une erreur fonctionnelle métier, puis un troisième échoue N fois consécutives, **Then** le premier est relancé après au moins 2 s puis réussit, le deuxième n'est **jamais relancé** (`0` relance) et l'étape passe en `WAITING_FOR_HUMAN_ARBITRATION`, et le coupe-circuit du troisième connecteur **s'ouvre après N échecs** puis passe en semi-ouvert après délai.
- **AC-F4** : **Then** chaque tentative transmet la même `idempotency_key`, une relance DBOS ne crée **aucun doublon** d'effet externe ni de ligne `audit_ledger` / `domain_events_outbox`, chaque tentative est imputée au budget `max_agent_retries` / `max_cost_usd` (`AD-12`), et aucune valeur de secret n'est sérialisée dans les entrées/sorties d'étapes DBOS (`NFR-SEC-4`).
- **AC-F5** : **Given** le workflow Finance « Rapprochement de factures » et un connecteur ERP factice (`tests/fixtures/plugins/`) (P2-2), **When** le job CI **`core-without-sdlc`** désinstalle `orcia-pack-sdlc` puis exécute ce workflow de bout en bout, **Then** le run se termine avec succès (`NFR-ISO-1`, critère d'acceptation de l'Epic 3).
- **AC-F6** : **Then** `lint-imports` passe à `0` violation, la couverture unitaire est $\ge 90\%$ et les 5 couches de tests (`AD-17`) sont livrées (incluant la reprise après redémarrage sur `testcontainers` PG18 + Redis), et le rapport Tech Lead `3-2f-...` documente la fermeture de l'écart `EC-1` constaté sur `Story 3.2b` (qui reste `done`, non rouverte).

### Story 3.3: Agent Assistant (DAG 5 Nœuds type n8n, `AssistantHarness` 5 Couches), Adaptation au Profil Humain & Composition Conversationnelle de Workflows (`@xyflow/react`)

As a Directrice de BU, Product Manager ou Architecte (`Claire UJ-8`, `Hélène UJ-1`, `Arthur UJ-10`),
I want — une fois **`Story 3.2c` ET `Story 3.2d`** terminées (`C7`) **ainsi que `Story 3.2f`** (Avenant A2 : exécution réelle des étapes) — dialoguer dans le Cockpit Chat-First + Canvas (et le Dock persistant) avec l'Agent Assistant structuré en DAG de 5 nœuds orientés dans le `AssistantHarness` à 5 couches, qui adapte son discours à mon Profil Humain et peut assembler/modifier conversationnellement un Workflow avec aperçu graphique `@xyflow/react`,
So that j'obtienne un premier token en `< 1,5 s` dans mon vocabulaire métier et puisse créer, ajuster et lancer en tâche de fond un workflow sur mesure en quelques messages (`FR-1`, `FR-11`, `AD-15`, `AD-19`, `AR-4`, `UX-DR12`, `UX-DR15`, `NFR-PERF-1`, `C7`).

**Acceptance Criteria:**

**Given** l'achèvement conjoint de **`Story 3.2c`** (bus d'événements Outbox backend) **ET de `Story 3.2d`** (SPA `Vite 6 + TanStack Router v1`, `@xyflow/react` et `apps/web/src/features/cockpit/`, `C7`), ainsi que le workflow système `orcia://system/workflows/assistant-agent` implémenté en DAG de 5 nœuds (*1. Routeur d'Intention $\rightarrow$ 2. Query Planner & Expansion Ontologique $\rightarrow$ 3. Fan-Out Parallèle [RAG, Catalogue, Blackboard, Permission Broker] $\rightarrow$ 4. Tri Critique & Vérification d'Axiomes $\rightarrow$ 5. Synthétiseur Adaptatif au Profil Humain*) exécuté dans `AssistantHarness` (`AD-15`, `AR-4`)
**When** un utilisateur interroge l'Agent Assistant depuis **💬 1. Cockpit & Chat** (`apps/web/src/features/cockpit/`) ou le Dock latéral
**Then** le `AssistantHarness` assemble les **5 couches de prompt** (avec la Couche 1 Constitutionnelle immuable interdisant toute écriture sur une *Ancre Humaine* ou approbation de *Gate*), diffuse le premier token en `< 1,5 s` via SSE (`NFR-PERF-1`), et adapte le registre et les indicateurs au *Profil Humain* connecté (`Direction/BU` $\rightarrow$ KPIs FinOps/TTM N1/N2 ; `PM/Métier` $\rightarrow$ règles de gestion ; `Architecte/Tech Lead` $\rightarrow$ URI, OpenAPI, hashes `SHA-256` N3 ; `SecOps` $\rightarrow$ preuves de Gates, `FR-1`, `UX-DR12`).

**Given** `Arthur` (`UJ-10`) qui demande à l'Agent Assistant de lui proposer un workflow pour comparer la documentation Confluence/Jira à une codebase `git://`, puis demande une modification d'étape
**When** l'Agent Assistant génère puis ajuste la proposition à partir des briques du *Catalogue Fédéré*
**Then** le **Canvas** affiche côte à côte le graphe interactif du workflow rendu avec **`@xyflow/react 12.12.0`** et le manifeste YAML mis à jour (`UX-DR15`, `FR-11`), et permet à `Arthur` en un clic (ou par confirmation dans le chat) d'enregistrer le workflow dans le Workspace et de lancer son exécution en tâche de fond (`BACKGROUND_AUDIT`)
**And** les schémas HTTP vivent dans `apps/api/src/orcia_api/schemas/`, les erreurs dans `<domaine>/errors.py`, `lint-imports` passe avec `0` violation, et les tests unitaires (`pytest` + `Vitest` sur `@xyflow/react`), d'intégration (`testcontainers` PG18 + Redis + SeaweedFS) et `DeterministicCassetteLLM` couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

**Given** les Stories `3.2e` et `3.2f` livrées (Avenant A2, `AD-20`) et l'action `DEC-CTX-01` (`ContextSourcePort`, `VectorStorePort`, plugins `orcia.indexers`)
**When** l'Agent Assistant compose puis lance un workflow
**Then** le workflow s'exécute via les exécuteurs réels du registre `orcia.step_executors`, le contexte injecté aux nœuds passe par `ContextSourcePort` (JSON, CAS, document) et non par des fichiers Markdown locaux, et l'Assistant du Core ne contient aucun vocabulaire SDLC (gabarits et briques SDLC fournis par `orcia-pack-sdlc`).

### Story 3.4: Ancrages Humains Obligatoires (`human-led-anchor-card`), Arbitrage Humain Systématique (`arbitration-tiebreak-card`) & Politique de Départage (`tie_break_policy`)

As a Product Manager ou Architecte (`Hélène UJ-1`, `Antoine UJ-2`),
I want rédiger et signer obligatoirement les sections `human_authored_required: true` avant toute génération IA, trancher via une matrice comparative tout Arbitrage Humain lorsque l'agent rencontre des options équivalentes, et appliquer de manière déterministe la politique `tie_break_policy` déclarée sur l'étape ou le workflow,
So that l'humain conserve la maîtrise intellectuelle (*Think*) sans biais d'ancrage cognitif et qu'aucun agent ne prenne de décision arbitraire silencieuse (`FR-4`, `FR-5`, `FR-29`, `AD-3`, `AD-18`, `AD-19`, `UX-DR3`, `UX-DR6`).

**Acceptance Criteria:**

**Given** la migration Alembic créant les tables `human_anchor_signatures` et `human_arbitration_requests`, ainsi qu'une étape de workflow comportant un champ marqué `human_authored_required: true`
**When** l'utilisateur ouvre l'étape dans le **Canvas** du Cockpit
**Then** le composant **`Human-Led Anchor Card` (`human-led-anchor-card`, bordure gauche violette `4px solid #6D28D9`, fond `#F5F3FF`, `UX-DR3`)** est affiché **sans aucun bouton "Générer avec l'IA"**, verrouillant le lancement de l'agent tant qu'un texte humain significatif ($\ge 30$ caractères) n'est pas saisi et signé dans `human_anchor_signatures` (`content_sha256`, `authored_by_user_id`)
**And** toute tentative d'écriture par une identité d'agent sur ce champ est rejetée par l'API avec `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED` (`AD-3`), et si l'utilisateur demande dans le chat *"Remplis-le pour moi"*, l'Agent Assistant refuse poliment et engage un questionnement socratique (`FR-4`).

**Given** un *Agent Exécuteur* qui identifie $\ge 2$ options techniques, fonctionnelles ou métier équivalentes
**When** l'agent invoque l'outil système obligatoire `request_human_arbitration(options_matrix)` (`AD-3`, `AD-18`)
**Then** en mode `PAUSE_AND_ESCALATE` (défaut `COACHING` et `HIGH_CRITICAL`), l'étape passe atomiquement au statut `WAITING_FOR_HUMAN_ARBITRATION` (`DBOS.recv`), publie `HumanArbitrationRequested` via `domain_events_outbox` pour notification SSE temps réel, et affiche dans le Chat et le Canvas la carte ambre **`Arbitration Tie-Break Matrix` (`arbitration-tiebreak-card`, `#D97706`, `UX-DR6`)** comparant chaque option (avantages, inconvénients, impacts SI/FinOps, recommandation) ; en mode `ONTOLOGY_AXIOM_FIRST`, le moteur vérifie d'abord si un axiome de l'Ontologie départage formellement les options ; en mode `DEFER_AND_CONTINUE_WITH_ASSUMPTION` (`BACKGROUND_FAST_PATH` / `AUTONOMOUS_CONTRACT` non critique), le choix par défaut et l'hypothèse `[ASSUMPTION]` sont journalisés dans `step_memlog_jsonb`
**And** dès que l'humain sélectionne une option (avec justification optionnelle), la décision est enregistrée dans le *Blackboard* et relance immédiatement l'exécution de l'étape (`DBOS.send`, `FR-5`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`), d'intégration (`testcontainers` PG18 + Redis) et E2E (`Playwright`) couvrent $\ge 90\%$ de `AD-3`, `UX-DR3` et `UX-DR6` (`AD-17`, `AD-19`).

### Story 3.5: Challenge Amont Inter-Steps avec Simulation d'Impact (*What-If*) & Replay Ciblé à partir du Step $N$ (incluant Replay Intra-Sous-Workflow)

As a Architecte SI ou Tech Lead (`Antoine UJ-2`, `Yanis UJ-3`, `Lucas UJ-7`),
I want émettre un Challenge formel vers un Step amont avec prévisualisation immédiate du graphe d'impact (*What-If Impact Preview*) et relancer un Replay ciblé à partir d'un Step $N$ (y compris un Step $k$ à l'intérieur d'un sous-workflow enfant) en réutilisant le snapshot validé de l'étape $N-1$,
So that les incohérences métier ou d'API soient corrigées à la source et rejouées sans reconsommer un seul token sur les étapes amont non impactées (`FR-7`, `FR-16`, `FR-30`, `AD-2`, `AD-7`, `AD-18`, `AD-19`, `UX-DR7`).

**Acceptance Criteria:**

**Given** un contributeur aval (ex. `Antoine` au Step 2 ou `Yanis` au Step 3) qui sélectionne une règle ou section d'un *Artefact* amont dans le Canvas et clique sur *Challenger / Rewind amont*
**When** la modale **`Upstream Challenge & Rewind Modal` (`UX-DR7`)** s'ouvre
**Then** le `ImpactSimulatorService` (`AD-7`) calcule par traversée de graphe (CTE sur les références `orcia://` de `blackboard_snapshots` et `ontology_relations`) et affiche l'**Aperçu de Simulation d'Impact (*What-If Impact Preview*)** listant exactement quels *Steps* aval, quelles sections d'*Artefacts* et quels axiomes d'*Ontologie* seront invalidés, tandis que l'agent traduit l'impact technique dans le vocabulaire du profil amont (`Hélène`, PM) et lui envoie une notification de challenge via `domain_events_outbox` (`FR-7`, `AD-19`).

**Given** un arbitrage amont validé (créant une révision `v1.1` de l'artefact amont), une résolution d'habilitation (`UJ-7`), une mise à jour de KB (`UJ-3`) ou un échec sur l'étape $k$ d'un sous-workflow enfant (`SUB_WORKFLOW`, `FR-30`)
**When** l'utilisateur habilité déclenche l'action **Replay à partir du Step $N$** (`POST /api/v1/runs/{run_id}/steps/{step_id}/replay`, `FR-16`, `FR-30`)
**Then** le moteur d'orchestration (`DBOS.fork_workflow`) réutilise strictement le snapshot validé de l'étape $N-1$ (et, en cas de Replay intra-sous-workflow, ne rejoue que l'étape $k$ du sous-workflow enfant sans recalculer les étapes amont du workflow parent) ainsi que les versions `SHA-256` figées dans `run-lock.json` (**0 ré-exécution et 0 token consommé** sur les étapes $1..N-1$), marque les anciens snapshots des étapes $\ge N$ comme `SUPERSEDED`, et crée une nouvelle branche `ACTIVE` de snapshots dans `blackboard_snapshots` (`AD-2`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`hypothesis` sur l'arbre de branchement `ACTIVE`/`SUPERSEDED`) et d'intégration (`testcontainers` PG18 + SeaweedFS) vérifient à $\ge 90\%$ qu'aucun snapshot existant n'est jamais muté lors d'un Replay (`AD-17`, `AD-19`).

## Epic 4: Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution (Actions Jira, Sandbox & MCP IDE)

Permettre aux Tech Leads, SecOps, Développeurs et Auditeurs (`Yanis UJ-3`, `Marc UJ-5`, `Sophie UJ-6`, `Arthur UJ-10`) de valider chaque étape via la chaîne de *Gates Déterministes* en *Sandbox isolée bimodale hors processus* (`AD-9`, `AD-19`, `Q3: 3A`, `Q5` : Palier 1 `wasmtime-py < 5s / 256MB` pour règles pures et Palier 2 conteneur isolé `gVisor/Rootless < 60s / 1024MB` sans réseau pour linters, compilateurs et tests TDD `UJ-12`, sans Rust dans le MVP), de *Gates Agentiques* avec *Orthogonalité des Modèles*, pseudonymisation PII réversible (`PiiReversibleScrubber`) et DAG de 5 lentilles (dont `fact_verification` et contrôle transverse Étape $N$ vs Étape 1), et de *Gates Humaines Adaptatives* (`mandatory_full`, `risk_or_exception_based`, `sampling`) équipées du *Briefing de Revue (4 blocs)*, de la *Validation par Découpage* et du garde-fou anti-*Rubber-Stamping* (`< 15s`) ; tout en exécutant de manière gouvernée (en mode *Staged* validé aux Gates) la création, la modification et les *transitions de workflows Jira* (+ réception des Webhooks `jira:issue_updated`) et en interrogeant ORCIA depuis leur IDE via le *Serveur MCP gouverné (`/api/v1/mcp`)*.

### Story 4.1: Sandbox Déterministe Isolée Hors Processus Palier 1 (`wasmtime-py < 5 s`, sans réseau), Détection de Pattern Drift & Workflows Système `init-existing-project` / `init-skill`

As a Tech Lead ou Ingénieur SecOps (`Marc UJ-5`, `Sophie UJ-6`),
I want exécuter les Gates Déterministes rapides et les Skills purs via `orcia_kernel.ports.SandboxPort` par délégation hors processus au service `sandbox-runner` (protocole MCP/sous-processus isolé, Palier 1 `wasmtime-py 27.0.0`, `< 5 s`, `256 MB`, `0` réseau, sans Rust dans le MVP selon `Q5`), détecter automatiquement tout Pattern Drift vis-à-vis de `ARCHITECTURE-SPINE.md` et certifier les projets/skills via `init-existing-project` et `init-skill`,
So that aucun code généré ou script de validation ne puisse compromettre le worker d'orchestration, exfiltrer des données ni introduire des dépendances ou motifs architecturaux non autorisés (`FR-17`, `FR-28`, `AD-9`, `AD-19`, `M8`, `Q3: 3A`, `Q5`, `NFR-SEC-1`).

**Acceptance Criteria:**

**Given** la migration Alembic créant la table `gate_evaluations`, ainsi que le port `orcia_kernel.ports.SandboxPort` déléguant hors processus au runner de sandbox Palier 1 (`infra/sandbox/`, runtime WebAssembly `wasmtime-py 27.0.0`, `Q3: 3A`, `Q5`)
**When** une *Gate Déterministe* rapide ou un *Skill* pur (`sandbox_tier: TIER_1_WASM`) s'exécute à la fin d'un Step
**Then** le sous-processus/service `sandbox-runner` tourne sans privilèges root, sans aucun accès réseau, avec un système de fichiers éphémère en lecture seule (hors `/tmp` mémoire de `64 MB`), un plafond RAM de `256 MB` et un timeout matériel de `5 000 ms` (`AD-9`, `NFR-SEC-1`)
**And** il vérifie (1) le schéma JSON/YAML du *Gabarit d'Artefact*, (2) les axiomes formels de l'*Ontologie*, et (3) les règles d'analyse statique de **Pattern Drift** (rejetant toute bibliothèque ou motif absent du `ARCHITECTURE-SPINE.md` de référence, `FR-17`), puis publie `GateEvaluated` dans `domain_events_outbox` (`AD-19`).

**Given** un projet existant (*Brownfield*) ou un nouveau *Skill* soumis au Catalogue
**When** l'utilisateur exécute `orcia://system/bootstrap/init-existing-project` ou `init-skill` (`FR-28`, `AD-16`)
**Then** `init-existing-project` scanne le dépôt `git://` pour générer et faire signer un `ARCHITECTURE-SPINE.md` initial (`[ADOPTED]`) servant de baseline anti-*Pattern Drift*, et `init-skill` refuse de publier tout *Skill* qui échoue aux contraintes d'isolation de la Sandbox (`< 5 000 ms`, `0` appel réseau)
**And** `lint-imports` passe à `0` violation et les tests unitaires et d'intégration (incluant des tests d'évasion réseau et mémoire de la sandbox hors processus) couvrent $\ge 90\%$ de `packages/orcia-core/gates` (`AD-17`, `AD-19`).

**Given** la Story `3.2f` livrée (Avenant A2)
**When** une *Gate Déterministe* est exécutée
**Then** elle est invoquée comme exécuteur `SKILL` du registre `orcia.step_executors`, et ses échecs sont classés dans la taxonomie `orcia_kernel.errors` (dépassement de délai → `UpstreamTimeoutError`, violation d'isolation → `PolicyDeniedError`) pour que le `ConnectorInvoker` ne relance que les erreurs passagères (`AD-12`).

### Story 4.1a: Phase E — Sandbox Bimodale Palier 2 Hors Processus (Conteneur Isolé `gVisor/Rootless`, `< 60 s`, `1024 Mo`, `--network=none`) & Séparation des 5 Rôles de Déploiement (Isolation de `Docling`)

As a Ingénieur SecOps ou SRE (`Sophie UJ-6`, `Karim UJ-9/UJ-12`),
I want compléter la Sandbox WASM Palier 1 (`< 5 s`) par un runner Palier 2 hors processus en conteneur éphémère isolé sans réseau (`gVisor runsc` en Kubernetes / `Podman/Docker rootless --network=none --read-only --pids-limit=64 --memory=1024m`, `< 60 s`, sans Rust selon `Q5`) et configurer l'image conteneur backend unique pour s'exécuter selon 5 rôles opérationnels distincts (`api`, `worker-orchestration`, `worker-indexing` isolant `Docling 2.91`, `trigger-dispatcher`, `sandbox-runner`),
So that les linters, compilateurs et suites de tests unitaires `pytest`/`vitest` de la boucle d'auto-remédiation TDD (`Red -> Green`, `UJ-12`) s'exécutent dans un budget réaliste et hermétique, et que la consommation CPU/RAM lourde de `Docling` ne dégrade jamais la latence de l'API ni du worker d'orchestration (`FR-17`, `FR-29`, `AD-9`, `AD-18`, `AD-19`, `P5`, `M8`, `M9`, `Q3: 3A`, `Q5`).

**Acceptance Criteria:**

**Given** une *Gate Déterministe* ou une étape de reproduction/correction TDD (`UJ-12`) déclarant `sandbox_tier: TIER_2_CONTAINER`
**When** le service hors processus `sandbox-runner` (`ContainerSandboxRunner`) lance l'exécution sur le snapshot CAS (`SeaweedFS`) monté en lecture seule
**Then** le conteneur s'exécute avec `--network=none`, `--read-only`, `--tmpfs /tmp:rw,noexec,nosuid,size=256m`, `--memory=1024m`, `--cpus=2.0`, `--pids-limit=64` et un timeout matériel strict de `60 000 ms` (`AD-9`, `P5`, sans dépendance aux `user namespaces` Kubernetes hôtes ni binaire Rust dans le MVP `Q5`)
**And** il permet d'exécuter `pytest`, `ruff`, `mypy`, `tsc` et `vitest` pour vérifier qu'un test unitaire reproduisant un bug échoue avant correctif (`Red`) et passe à `100 %` après correctif (`Green`).

**Given** la configuration de packaging `apps/worker/pyproject.toml` (avec l'extra optionnel `orcia-worker[indexing]` pour `docling 2.91.0`) et `infra/docker/docker-compose.yml` (`M9`, `AD-19`)
**When** la plateforme est déployée
**Then** la même image conteneur s'exécute selon **5 rôles séparés** par leur commande de démarrage et leurs extras : (1) `api` (FastAPI REST + SSE), (2) `worker-orchestration` (DBOS Transact, sans charger `Docling`), (3) `worker-indexing` (Dramatiq + `Docling` + `tree-sitter`), (4) `trigger-dispatcher` (Webhooks, Log Sink, Cron), et (5) `sandbox-runner` (Wasmtime Palier 1 & gVisor/Podman Palier 2)
**And** `lint-imports` vérifie qu'`apps/api` et le code d'orchestration n'importent jamais `docling`, avec tests d'intégration d'isolation réseau/fichiers couvrant $\ge 90\%$.

### Story 4.2: Gates Agentiques avec Orthogonalité des Modèles, Pseudonymisation PII Réversible (`PiiReversibleScrubber`) & DAG de 5 Lentilles (dont `fact_verification`)

As a Ingénieur SecOps ou Architecte (`Sophie UJ-6`, `Antoine UJ-2`, `Arthur UJ-10`),
I want qu'une Gate Agentique route obligatoirement l'évaluation vers une famille de modèle distincte de l'exécuteur (sans sa Chain-of-Thought), pseudonymise les PII de manière réversible avant tout appel Cloud, et exécute en parallèle les 4 lentilles d'audit (dont `fact_verification` et Contrôle Transverse Étape 1) suivies de la lentille de synthèse,
So that le biais d'auto-complaisance LLM, l'effet téléphone arabe entre étapes et les hallucinations factuelles soient neutralisés à la source (`FR-18`, `AD-10`, `NFR-SEC-2`).

**Acceptance Criteria:**

**Given** une *Gate Agentique* déclenchée après une étape exécutée par un modèle de la famille $F_{\text{exec}}$ (ex. `anthropic/claude-*`)
**When** `ModelRouterService` (LiteLLM) prépare l'invocation de l'*Agent Évaluateur*
**Then** il impose par construction que `evaluator_model_family != executor_model_family` (ex. `google/gemini-*` ou `openai/gpt-*`, levant une erreur bloquante si la règle est violée), purge intégralement la chaîne de raisonnement interne (*Chain-of-Thought*) de l'exécuteur (`FR-18`, `AD-10`)
**And** il route les données classifiées sensibles par l'Ontologie exclusivement vers les modèles locaux (Ollama/vLLM) et applique à la volée le filtre **`PiiReversibleScrubber` (`anonymize_pii_reversible: true`)** qui remplace les données personnelles ou secrets par des jetons déterministes stockés en Redis sur la durée du `run_id` et les ré-hydrate localement au retour (`NFR-SEC-2`).

**Given** l'artefact candidat transmis à la *Gate Agentique*
**When** le moteur de Gate exécute le **DAG de Lentilles d'Évaluation (`AD-10`)**
**Then** il lance en parallèle et sans visibilité croisée les **4 Lentilles Indépendantes** :
1. *Lentille 1 — Alignement Transverse Étape 1* : vérifie que l'artefact du Step $N$ ne contredit aucune exigence ou invariant du `PRD` (Step 1) ou de l'`Architecture` (Step 2).
2. *Lentille 2 — Vérification Atomique de Faits (`fact_verification`)* : décompose l'artefact en assertions factuelles atomiques, confronte chacune à l'*Ontologie (N1..N4)* et aux *KBs* épinglées avec un score de confiance (`0..1`), et bloque toute assertion sous le seuil configuré.
3. *Lentille 3 — Attaque Adversariale & Edge-Cases*.
4. *Lentille 4 — Conformité Domaine & Sécurité*.
**And** la *Lentille 5 — Synthèse & Structure* (`after`) consolide `lens_findings_jsonb`, intègre `step_memlog_jsonb`, calcule `agentic_score`, structure le **Briefing de Revue en 4 blocs** dans `gate_evaluations.briefing_4blocks_jsonb` et publie `GateEvaluated` dans `domain_events_outbox` (`AD-19`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest` sur l'orthogonalité, la purge CoT et `PiiReversibleScrubber`), d'intégration (`testcontainers` PG18 + Redis) et `DeterministicCassetteLLM` couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

**Given** la Story `3.2f` livrée et l'action `DEC-SEC-01` (reliée à `SEC-03`) (Avenant A2)
**When** une *Gate Agentique* appelle un modèle via LiteLLM avec un secret canari injecté dans la configuration du fournisseur
**Then** l'appel passe par le `ConnectorInvoker` (relances passagères, `Retry-After`, budget `AD-12`), la clé du fournisseur est une `SecretRef` résolue par `SecretProviderPort` (suppression de la valeur par défaut `sk-orcia-local` de `bootstrap/_internal/litellm_adapter.py:L31`), et le **test du secret témoin** vérifie l'absence du canari dans `dbos.*`, `audit_ledger`, `domain_events_outbox`, `step_executions` et les logs structlog masqués (`NFR-SEC-4`).

### Story 4.3: Gates Humaines Adaptatives, Briefing de Revue 4 Blocs (`review-briefing-grid`), Validation par Découpage (`chunk-validation-card`) & Garde-fou Anti-Rubber-Stamping (`< 15 s`)

As a Valideur Métier, Tech Lead ou SecOps (`Hélène UJ-1`, `Nadia UJ-4`, `Sophie UJ-6`),
I want inspecter en tête de tout artefact le Briefing de Revue en 4 blocs, valider ou amender l'artefact section par section (`Validation par Découpage`), bénéficier des 3 politiques de Gates Adaptatives et être protégé contre le Rubber-Stamping (`< 15 s`),
So that le taux de validation aveugle reste strictement $< 5\%$ tout en automatisant le passage des étapes à faible risque parfaitement conformes (`FR-6`, `FR-19`, `AD-11`, `AD-19`, `UX-DR4`, `UX-DR5`, `UX-DR10`).

**Acceptance Criteria:**

**Given** la migration Alembic créant la table `chunk_approvals`, ainsi que le module **🛡️ 5. Gates & Habilitations** (`g g`, `apps/web/src/features/gates/`) permettant de configurer la politique d'une *Gate Humaine* (`mandatory_full`, `risk_or_exception_based`, `sampling`)
**When** une étape atteint une *Gate Humaine* configurée en `risk_or_exception_based`
**Then** la Gate passe automatiquement si et seulement si `deterministic_status == PASS` **ET** `agentic_score >= 0.85` **ET** `ontology_conflicts == 0` **ET** `stale_warnings == 0` (et qu'aucune section ne porte `human_authored_required: true`) ; sinon, ou dans `20 %` des cas en mode `sampling`, elle requiert l'intervention humaine (`FR-19`, `AD-11`).

**Given** un valideur humain qui ouvre dans le **Canvas** une étape soumise à une *Gate Humaine* (ou un artefact $> 1\,500$ mots / $> 3$ sections)
**When** la vue de validation est rendue
**Then** elle affiche en haut la grille $2 \times 2$ **`Cognitive Review Briefing` (`review-briefing-grid`, `UX-DR4`)** (*1. Résumé Exécutif*, *2. Éléments Clés & Contrôle Transverse*, *3. Décisions Prises*, *4. Hypothèses Retenues* encadré en ambre `#D97706` tant qu'il n'est pas inspecté), suivie des cartes **`Chunked Validation Card` (`chunk-validation-card`, `UX-DR5`)** navigables via `Alt + ↑ / ↓` avec 3 actions par section (*Valider la section*, *Co-éditer* avec signature dans `human_anchor_signatures`, ou *Challenger / Rewind amont*), **sans aucun bouton "Tout Approuver en 1 clic"** tant que toutes les sections obligatoires ne sont pas `APPROVED` (`FR-6`)
**And** si le valideur soumet une approbation sur un artefact $> 1\,000$ mots en moins de `15 secondes` de lecture active, la modale **`Anti-Rubber-Stamping Guard` (`UX-DR10`)** exige une confirmation explicite des hypothèses et enregistre `fast_approval_warning: true` (`AD-11`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`), d'intégration (`testcontainers` PG18) et E2E (`Playwright`) couvrent $\ge 90\%$ de ces composants et règles (`AD-17`, `AD-19`).

### Story 4.4: Actions & Transitions de Workflows Jira Multi-Projets Staged aux Gates (+ Webhooks `jira:issue_updated`) & Serveur MCP Gouverné (`/api/v1/mcp` pour IDE)

As a Tech Lead, Développeur ou Architecte (`Yanis UJ-3`, `Lucas UJ-7`, `Arthur UJ-10`),
I want que les agents puissent interroger en JQL temps réel les multiples projets Jira rattachés au Workspace, préparer des créations/modifications/transitions de tickets Jira (en routant vers le projet Jira approprié par alias/composant) en mode *Staged* soumis aux Gates, réveiller un Run sur Webhook `jira:issue_updated`, et exposer le Serveur MCP gouverné d'ORCIA (`/api/v1/mcp`) à mon IDE (VS Code, Cursor, Claude Code, Antigravity),
So that les workflows Jira des différents projets de la solution avancent automatiquement en toute sécurité dès qu'une Gate est franchie et que les développeurs accèdent au contexte gouverné d'ORCIA directement depuis leur éditeur de code (`FR-24`, `AD-5`, `AD-6`, `AD-19`, `AR-7`).

**Acceptance Criteria:**

**Given** un *Step* utilisant le connecteur/Skill **Jira (`jira://`)** en mode *Passthrough* (OAuth 2.0 3LO / PAT) dans un Workspace rattachant un ou plusieurs projets Jira dédiés (ex. `jira:product`, `jira:secops`)
**When** l'*Agent Exécuteur* propose de créer un ticket (`create_issue` en sélectionnant le `project_key` cible parmi les projets du Workspace), de le modifier/commenter (`update_issue`, `add_comment`) ou de faire avancer son workflow Jira (`transition_issue`)
**Then** le connecteur interroge d'abord `GET /rest/api/3/issue/{key}/transitions` sur le projet concerné pour valider que la transition cible est légale et que tous les champs obligatoires de l'écran de transition sont fournis, puis enregistre l'opération comme **Action Staged** dans `step_executions.draft_artifact_jsonb` (affichée comme carte révisable dans la *Validation par Découpage* `UX-DR5`)
**And** l'appel d'écriture ou de transition vers l'API REST Jira v3 n'est exécuté qu'au passage effectif de la **Gate** de l'étape (`AD-5`, `AD-11`), en inscrivant automatiquement le lien de provenance `run-lock.json` dans le ticket Jira.

**Given** un *Workflow Run* en pause en attente de la résolution d'un ticket sur l'un des projets Jira liés (`UJ-3`), ou un développeur connecté depuis son IDE externe (VS Code, Cursor, Claude Code, Antigravity)
**When** Jira émet le Webhook `jira:issue_updated` (statut passé à `Done`) **OU** que l'IDE appelle le **Serveur MCP gouverné `/api/v1/mcp`** (`AR-7`)
**Then** le Webhook Jira notifie l'équipe en `< 500 ms` via `domain_events_outbox` / SSE pour déclencher le *Replay* ciblé (`FR-16`), et le serveur `/api/v1/mcp` expose en mode *Passthrough* les outils de consultation de l'*Ontologie (N1..N4)*, de la *KB* multi-sources, du *Catalogue* et du *Blackboard* tout en bloquant matériellement toute écriture sur les sections `human_authored_required: true` (`AD-3`, `AD-6`, `FR-24`)
**And** `lint-imports` passe à `0` violation et les tests unitaires, de contrat et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du connecteur d'actions Jira multi-projets stagées, du récepteur de Webhooks et du serveur MCP `/api/v1/mcp` (`AD-17`, `AD-19`).

**Given** la Story `3.2e` livrée et l'action `DEC-ACC-01` (Avenant A2)
**When** un agent prépare une action Jira *Staged* ou qu'un refus d'accès déclenche le *Permission Broker*
**Then** Jira est un adaptateur `ConnectorPort` du pack `orcia-pack-sdlc` (`invoke(action, payload, idempotency_key)` via `ConnectorInvoker`), la demande d'accès passe par `AccessRequestChannelPort` avec la colonne générique `request_url` (nouvelle révision *Expand* + backfill SQL, puis *Contract* de `jira_request_url`), et le serveur MCP reste hors processus (`Q3 = 3A`, `NFR-EXT-1`).

## Epic 5: Centre de Notifications Temps Réel (`< 500ms`), Supervision Multi-Runs, Centre de Pilotage Unifié Multi-Niveaux des Workspaces (`/workspaces`) & Expérience Mobile Companion

Permettre aux Administrateurs Plateforme (`Karim UJ-9`), Directeurs de BU (`Claire UJ-8`), Chefs d'Équipe (`Marc UJ-5`) et Contributeurs multi-projets (`Nadia UJ-4`) de trier leurs notifications personnelles et d'équipe dans **🔔 2. Boîte & Mes Runs**, de prendre en charge (*Claim*) atomiquement une notification d'équipe avec verrou de présence temps réel (`< 500ms` via SSE), de superviser simultanément plusieurs *Workflow Runs* avec séparation stricte entre *Consultation seule (`READ_ONLY_OBSERVER`)* et *Contributeur (`CONTRIBUTOR_ACTION_REQUIRED`)*, de piloter et d'administrer de manière consolidée (*Roll-up* & *Drill-down* via le sélecteur de périmètre **`⌘W`**) l'ensemble des **Workspaces, Instances de Workflow Runs, Sources (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`), Agents/Workflows/Surcharges et Équipes** depuis le **Centre de Pilotage Unifié Multi-Niveaux (`/workspaces` & `/workspaces/[workspaceId]` à 4 onglets)**, de piloter l'interface au clavier (`⌘K`, `⌘W`, `g c`..`g w`, `Alt + ↑/↓`), et de traiter leurs arbitrages et validations urgentes en déplacement grâce à l'interface **Mobile Companion** à 3 onglets conforme WCAG 2.2 AA.

### Story 5.1: Centre de Notifications Unifié (Individuel & Équipe), Prise en Charge Atomique (`Claim`) & Verrou de Présence SSE `< 500 ms`

As a Product Manager ou Lead Multi-Projets (`Nadia, UJ-4`),
I want consulter dans une boîte unifiée mes notifications personnelles et d'équipe, les filtrer par portée/type, et prendre en charge (`Claim`) atomiquement une notification d'équipe avec diffusion SSE en `< 500 ms`,
So that deux membres d'une même équipe ne travaillent jamais en doublon ni ne soumettent des validations contradictoires sur la même étape (`FR-2`, `AD-4`, `AD-19`, `UX-DR9`, `UX-DR11`, `NFR-PERF-2`).

**Acceptance Criteria:**

**Given** la migration Alembic créant la table `task_notifications` (référençant `step_execution_id`, `target_team_id`, `target_user_id`, `claimed_by_user_id`), l'abonné Outbox `notifications` consommant `domain_events_outbox` (`AD-19`), ainsi que le broker SSE `/api/v1/events/stream` branché sur Redis Pub/Sub `channel:workspace:{ws_id}`
**When** une étape requiert une action humaine (*Gate Humaine*, *Arbitrage Humain*, *Challenge Humain*, *Alerte Habilitation / Obsolescence*)
**Then** la notification apparaît instantanément dans **🔔 2. Boîte & Mes Runs** (`g i`, `apps/web/src/features/inbox/`), filtrable par portée (*À moi*, *À mon équipe*) et par type, et incrémente le badge compteur ambre sur la Sidebar (`FR-2`, `UX-DR2`).

**Given** une notification d'équipe affichant le composant **`Presence & Claim Pill` (`presence-claim-pill`, `UX-DR9`)** à deux coéquipiers connectés simultanément (`Nadia` et `Thomas`)
**When** `Nadia` clique sur `Prendre (Claim)` (`POST /api/v1/tasks/{task_id}/claim` ou `POST /api/v1/runs/{run_id}/steps/{step_id}/claim`)
**Then** l'API acquiert le verrou atomique Redis `SET lock:step:{step_execution_id} {user_id} NX EX 900`, persiste `claimed_by_user_id` en base et publie `task.claim.locked` sur Redis Pub/Sub (`AD-4`)
**And** en `< 500 ms` (`NFR-PERF-2`), l'interface de `Nadia` affiche `🔒 Pris par vous` et celle de `Thomas` passe en état `CLAIMED_BY_PEER` (opacité `85%`, pastille émeraude `🔒 En cours : Nadia`, avec possibilité de *Force Unclaim* après 15 minutes d'inactivité, `UX-DR9`, `UX-DR11`)
**And** `lint-imports` passe à `0` violation et les tests d'intégration (`testcontainers` Redis + PG18 sous concurrence) et E2E multi-navigateurs (`@playwright/test` à 2 contextes simultanés) valident l'atomicité du verrou et la latence `< 500 ms` (`AD-17`, `AD-19`).

**Given** la Story `3.2f` livrée et l'action `DEC-CONC-01` (Avenant A2, `AD-4`)
**When** deux *Runs* concurrents tentent d'écrire sur la même ressource partagée (même `resource_uri`)
**Then** un seul obtient le bail `ResourceLeasePort` (bail PostgreSQL `resource_leases` + jeton de fencing monotone), l'écriture portant un jeton périmé est rejetée par le connecteur, l'acquisition multi-ressources suit l'ordre canonique par `resource_uri`, et une attente cyclique parent-enfant (`SUB_WORKFLOW`) est détectée et levée par délai d'expiration (tests sous concurrence `testcontainers` PG18).

### Story 5.2: Supervision Multi-Runs Dynamique (`< 1 s`), Sélecteur de Périmètre Hiérarchique (`⌘W`), Centre de Pilotage Unifié Multi-Niveaux des Workspaces (`/workspaces` à 4 Onglets), Séparation `READ_ONLY_OBSERVER` (`HTTP 403`) vs `CONTRIBUTOR_ACTION_REQUIRED` & Palette `⌘K`

As a Administrateur Plateforme (`Karim UJ-9`), Directrice de BU (`Claire UJ-8`), Chef d'Équipe (`Marc UJ-5`) ou Lead Multi-Projets (`Nadia UJ-4`),
I want superviser simultanément mes Workflow Runs actifs en distinguant ceux où une action est attendue (`Contributeur`) de ceux que je suis en `Consultation seule`, basculer de périmètre organisationnel (`🌐 Plateforme Globale → 🏢 BU → 👥 Équipe → 🗂️ Workspace`) via `⌘W` pour consulter et gérer dans un écran unifié (`/workspaces` & `/workspaces/[workspaceId]` à 4 onglets) l'ensemble des instances de runs, des sources dédiées/partagées (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`), des agents/workflows/surcharges et des équipes selon mon niveau hiérarchique, basculer entre deux Runs en `< 1 s` via la palette `⌘K`, et être protégé en `HTTP 403` contre toute mutation accidentelle en mode Observateur,
So that je puisse piloter aussi bien un Workspace isolé qu'une Équipe, une BU entière ou la Plateforme Globale sans jamais interférer par erreur dans une étape qui ne m'est pas assignée (`FR-1`, `FR-3`, `AD-4`, `AD-14`, `AD-19`, `UX-DR2`, `UX-DR11`, `UX-DR13`, `NFR-PERF-1`).

**Acceptance Criteria:**

**Given** un utilisateur qui consulte **🔔 2. Boîte & Mes Runs** ou ouvre la palette de commandes universelle **`⌘K` / `Ctrl+K` (`UX-DR13`)**
**When** il visualise ses *Workflow Runs* ou recherche un Run / Workspace / concept d'Ontologie / item du Catalogue
**Then** la vue scinde clairement les Runs en **Actions Requises (`CONTRIBUTOR_ACTION_REQUIRED`)** en haut et **En Suivi (`READ_ONLY_OBSERVER`)** en bas (`FR-3`), les raccourcis clavier (`g c`, `g i`, `g f`, `g o`, `g g`, `g a`, `g s`, `g w`, `[`, `]`, `Alt + ↑/↓`) sont actifs, et le clic sur un Run charge son contexte complet dans le Cockpit en `< 1 s` (`NFR-PERF-1`).

**Given** un utilisateur habilité (`PLATFORM_ADMIN`, `BU_DIRECTOR`, `TEAM_LEAD` ou Contributeur) qui utilise le **Sélecteur de Périmètre Hiérarchique (`⌘W` / `Ctrl+W`, `UX-DR2`, `UX-DR13`)** en tête de Sidebar et ouvre le **Centre de Pilotage Unifié des Workspaces (`/workspaces` ou `/workspaces/$workspaceId` sous `TanStack Router v1`, `apps/web/src/features/workspaces/`, `g w`)**
**When** il sélectionne une échelle (`🌐 Plateforme Globale`, `🏢 BU / Tribu`, `👥 Équipe / Sous-Équipe` ou `🗂️ Workspace Solution`) et navigue à travers les **4 onglets fractals** (`GET /api/v1/control-center/overview?scope_type=GLOBAL|BU|TEAM|WORKSPACE&scope_id={id}`)
**Then** l'écran consolide dynamiquement par *Roll-up* SQL (`WITH RECURSIVE org_tree`) et permet le *Drill-down* en 1 clic sur :
- **Onglet 1 (`▶️ Instances de Workflow Runs & Artefacts`)** : la liste temps réel (SSE) des *Workflow Runs* du périmètre filtré (statut, étape courante, mode `Coaching` vs `Fast-Path`, verrou *Claim*, actions requises, budget consommé, et lancement d'un nouveau Run ou *Replay*) ;
- **Onglet 2 (`🔌 Sources Dédiées & Partagées`)** : toutes les sources rattachées aux Workspaces et Équipes du périmètre (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://` de `workspace_datasources`), leur état d'indexation dans le *Graphe Tripartite*, les alertes `[STALE_WARNING]`, le bouton `+ Rattacher une source` (`init-datasource`) et le tiroir méthodologique **`<GuidanceDrawer />`** en 5 étapes ;
- **Onglet 3 (`🤖 Workflows, Agents & Surcharges 4 niveaux`)** : les *Workflows* et *Agents* actifs avec aperçu `@xyflow/react`, l'inspecteur des surcharges déclaratives (`1. Base -> 2. Équipe TEAM -> 3. Solution WORKSPACE -> 4. Utilisateur USER`) et le contrat `ARCHITECTURE-SPINE.md` ;
- **Onglet 4 (`👥 Équipes, Membres & Gouvernance`)** : l'arborescence `org_units`, les *Workspaces / Produits* rattachés qualifiés par leur phase de cycle de vie **`RUN | BUILD | MIGRATION`** (`<ProductLifecycleCard />`, adaptant dynamiquement les workflows suggérés), les membres invités (`init-user`), les délégations de Gates et la politique de visibilité (`STANDARD` vs `CONFIDENTIAL_RESTRICTED`, où le `PLATFORM_ADMIN` conserve la supervision technique/FinOps des espaces `CONFIDENTIAL_RESTRICTED` sans exposer leurs payloads métiers du *Blackboard* sauf habilitation explicite).

**Given** un utilisateur qui ouvre un *Workflow Run* avec le statut `READ_ONLY_OBSERVER` (y compris un Directeur de BU ou un Lead d'équipe parente en supervision *Roll-up*, ou une étape verrouillée par un pair `CLAIMED_BY_PEER`)
**When** le Cockpit affiche le Run ou qu'une requête `POST/PUT/PATCH/DELETE` de mutation d'étape/artefact/Gate est envoyée à l'API
**Then** l'interface affiche le bandeau supérieur `👁️ Mode Consultation Seule — Vous suivez ce Workflow Run en tant qu'Observateur` (`UX-DR11`) et désactive tous les boutons d'édition, d'arbitrage et d'approbation de Gate
**And** le middleware FastAPI `RunAccessGuard` vérifie en $O(1)$ le rôle et la détention de `lock:step:{step_execution_id}` et rejette toute tentative de mutation avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` (`FR-3`, `AD-4`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest` sur `RunAccessGuard` et l'agrégation récursive `control-center/overview`, `Vitest` sur la palette `⌘K`, le sélecteur `⌘W` et les 4 onglets `/workspaces`), d'intégration (`testcontainers` PG18 + Redis) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 5.3: Expérience Responsive à 3 Breakpoints, Interface Mobile Companion Restreinte (3 Onglets) & Conformité Accessibilité WCAG 2.2 AA

As a Contributeur ou Valideur en mobilité (`Nadia UJ-4`, `Hélène UJ-1`),
I want utiliser ORCIA sur Desktop (`>= 1280px`), Laptop (`768px - 1279px`) et sur Smartphone (`< 768px`) via l'interface Mobile Companion dédiée à 3 onglets (`🔔 Inbox`, `💬 Arbitrage/Chat`, `📄 Briefing`), avec une conformité WCAG 2.2 AA complète,
So that je puisse débloquer mon équipe en moins de 10 minutes depuis mon téléphone tout en étant protégé contre les manipulations lourdes inadaptées au mobile (`UX-DR16`, `NFR-A11Y-1`, `NFR-TEST-1`).

**Acceptance Criteria:**

**Given** un utilisateur qui accède à `apps/web` depuis un viewport **Mobile Companion (`< 768px`, ex. `390x844`)** (`UX-DR16`)
**When** l'application adapte sa mise en page
**Then** la grille à 3 colonnes est remplacée par une vue mono-colonne pilotée par une barre d'onglets basse à 3 entrées (`🔔 Inbox`, `💬 Arbitrage/Chat`, `📄 Briefing`) permettant de trier et *Claim* les notifications, trancher les *Arbitrages Humains* (`arbitration-tiebreak-card`), lire le *Briefing de Revue (4 blocs)*, approuver les sections par découpage et suivre les Runs en *Consultation seule*
**And** l'édition de manifestes YAML *Workflow-as-Code*, la co-édition lourde d'artefacts multi-pages et le module *7. Administration* sont explicitement bloqués sur mobile avec la bannière *"Fonctionnalité réservée au poste Desktop"* (`UX-DR16`).

**Given** l'ensemble des surfaces Desktop, Laptop et Mobile Companion d'ORCIA
**When** un audit d'accessibilité automatisé et clavier est exécuté (`NFR-A11Y-1`)
**Then** 100% des écrans respectent les ratios de contraste **WCAG 2.2 AA**, aucun état critique (*Ancrage Humain*, *Arbitrage*, *Gate*, `[STALE_WARNING]`) n'utilise la couleur seule (toujours **Couleur sémantique + Icône dédiée + Libellé textuel explicite** : `✍️ Ancrage Humain`, `⚖️ Arbitrage IA`, `🛡️ Gate`, `🚨 Obsolète`), et les régions `aria-live="polite"` annoncent les nouvelles notifications, les *Claims* SSE et le streaming de l'Agent Assistant
**And** la suite E2E `@playwright/test` s'exécute sur les viewports Desktop (`1440x900`) et Mobile (`390x844`) avec $\ge 90\%$ de couverture des composants UI.

### Story 5.4: Coquille Globale Direction C Enrichie (Mire `/login` Bi-Mode, Mode Rail Collapsible, Header Santé DBOS/Outbox & Accueil Anti-Empty-State Scopé)

As a Utilisateur authentifié ou Administrateur Plateforme (`Hélène UJ-1`, `Marc UJ-5`, `Karim UJ-9`),
I want disposer d'une mire de connexion `/login` bi-mode claire (SSO OIDC primaire + accordéon d'administration locale Argon2id/TOTP), d'une Sidebar repliable en Mode Rail (`68px`, `[`) affichant le Pack actif, d'une barre supérieure exposant la santé temps réel du moteur (`DBOS/PG18`, `Outbox DLQ`) et le Sprint/Lot actif, et d'un tableau de bord d'accueil Anti-Empty-State (`/`) proposant une boîte de prompt scopée aux sources RAG autorisées ainsi qu'un widget de Sprint actif avec audit IA en 1 clic,
So that la prise en main quotidienne soit immédiate sans page blanche ni surcharge cognitive (Loi de Hick) tout en rendant transparents le périmètre documentaire interrogé et la santé de l'orchestrateur (`FR-1`, `AD-15`, `AD-19`, `AD-21`, `UX-DR1`, `UX-DR2`).

**Acceptance Criteria:**

**Given** un utilisateur non authentifié accédant à une route protégée de `apps/web`
**When** le guard `beforeLoad` de TanStack Router intercepte la navigation
**Then** il redirige vers la route dédiée **`/login`** qui présente en action primaire le bouton **SSO d'Entreprise (OIDC PKCE)** et, dans un accordéon secondaire replié par défaut (*« Connexion locale / Administrateur de secours »*), le formulaire email + mot de passe Argon2id + code TOTP 2FA avec gestion typée des erreurs RFC 9457 (session expirée, compte désactivé, échec OIDC) (`AD-15`, `AD-21`).

**Given** un utilisateur connecté naviguant dans la coquille globale Direction C (`AppShell`)
**When** il actionne le bouton de repli ou le raccourci `[` sur la Sidebar gauche (`<CollapsibleAppRail />`) ou consulte l'en-tête (`TopHeaderBar`)
**Then** la Sidebar bascule fluidement entre le mode étendu (`240px`) et le **Mode Rail (`72px`)** (état persisté), affiche en pied le badge du **Pack Métier actif** (`orcia-pack-sdlc`) et les pastilles temps réel (actions requises, santé Outbox), tandis que le Header affiche le sélecteur Workspace/Pack couplé au Sprint/PI actif ainsi que les pastilles de santé `DBOS/PG18` et `Outbox` (`AD-21`).

**Given** un utilisateur qui arrive sur la page d'accueil `/`
**When** le tableau de bord d'accueil Anti-Empty-State est rendu
**Then** il affiche le **`<SprintContextWidget />`** du Sprint/Lot actif doté du CTA 1-clic *« Auditer les risques du sprint / lot avec l'IA »* ainsi que la **`<ScopedPromptBox />`** permettant de choisir explicitement le périmètre de sources RAG (filtré par le *Permission Broker*) et le Tier cognitif avant d'envoyer une requête à l'Agent Assistant
**And** `lint-imports` passe à `0` violation et les tests unitaires (`Vitest` sur `<CollapsibleAppRail />`, `<SprintContextWidget />`, `<ScopedPromptBox />` et `/login`) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

## Epic 6: Gouvernance Exécutive, Provenance Auditable Immuable, FinOps Consolidé (LLM Internes + Télémétrie MCP/Agents Distants) & Réversibilité Humaine

Permettre aux Directeurs de BU, Responsables Produit et Auditeurs (`Claire UJ-8`, `Sophie UJ-6`) de piloter dans **📊 FinOps** l'équation économique consolidée de leurs processus (*Coût de Setup + Coût de Run interne vérifié + Coût externe déclaré MCP/A2A vs gain de TTM*) protégée par le validateur **`RemoteUsageSanitizer`** (`_meta.usage` / `X-Orcia-Usage`), les coupe-circuits budgétaires et anti-boucles (`PAUSED_BUDGET_EXCEEDED`, `PAUSED_MAX_RETRIES`) et les coupe-circuits isolés par connecteur (`CIRCUIT_OPEN`, `AD-12`), d'inspecter et d'exporter la *Provenance Auditable* immuable de chaque Step, Gate et test de connexion à chaud (`audit_ledger`, `ADMIN_CONNECTION_TEST`), et de suivre les 3 contre-métriques de gouvernance cognitive (*Ratio Cadrage Actif $\ge 40\%$*, *Taux de Rubber-Stamping $< 5\%$*, *Indice de Pattern Drift / Réversibilité Humaine $0\%$*) avec recommandations automatiques d'ajustement des Gates.

> **Réconciliation du 2026-11-08 (`CAP-ACT-3`)** : constat dans le code — aucune migration Alembic ne crée `audit_ledger`, `packages/orcia-core/.../audit_finops/` ne contient que `errors.py`, `/finops` n'est qu'une coquille `ModuleWorkspaceView` et le **Journal d'activité** (`/activity`, `CAP-065`, livré hors epic le 2026-11-05) lit `auditEvents` issus du snapshot d'accostage (`bootstrap_accostage.py`), **sans** registre append-only. Les Stories 6.1 à 6.4 restent donc **intégralement `backlog`**. Rebasage : (a) Story 6.1 doit **remplacer la source** de `/activity` par `audit_ledger` (le composant `ActivityLogExplorerView` et ses filtres sont réutilisés, pas recréés) ; (b) les statuts d'avancement figurent dans `capabilities.yaml` (`CAP-065` partial, `CAP-200` planned).

### Story 6.1: Registre de Provenance Auditable Immuable (`audit_ledger` Append-Only), Traçabilité des Tests à Chaud (`ADMIN_CONNECTION_TEST`) & Export de Conformité JSON/Markdown

As a Ingénieur SecOps ou Auditeur Interne (`Sophie UJ-6`, `Claire UJ-8`),
I want enregistrer de manière immuable dans `audit_ledger` la provenance complète de chaque Step, Gate, appel MCP/Agent distant (avec la nature des métriques déclarées) et essai à chaud du banc de test (`ADMIN_CONNECTION_TEST`), et l'exporter en JSON/Markdown,
So that nous puissions prouver réglementairement à 100% quelles ressources exactes, quels modèles internes ou services distants et quels experts humains ont produit et validé chaque livrable sans polluer les runs de production (`FR-25`, `AD-12`, `AD-19`, `NFR-SEC-3`, `Principe M.2`).

**Acceptance Criteria:**

**Given** la migration Alembic créant la table `audit_ledger` protégée par un trigger PostgreSQL `BEFORE UPDATE OR DELETE RAISE EXCEPTION` (`NFR-SEC-3`) et l'abonné Outbox idempotent de `packages/orcia-core/audit_finops` (`AD-19`)
**When** un appel LLM, une exécution de *Skill*/*MCP*/*Agent distant A2A*, un essai à chaud du banc de test (`actor_type: ADMIN_CONNECTION_TEST`, isolé hors run de production), une mutation *Jira*, un passage de *Gate*, une action humaine ou une modification de paramètre système (`SettingsChanged`, `AD-21`) se produit
**Then** `packages/orcia-core/audit_finops` consomme les événements de `domain_events_outbox` (`StepCompleted`, `GateEvaluated`, `ArtifactProduced`, `RunTerminated`, `SettingsChanged`) sans couplage entrant depuis `orchestration/engine.py` et écrit sans doublon (idempotence par `event_id`) une entrée horodatée UTC ISO-8601 contenant `run_id` (nullable pour `ADMIN_CONNECTION_TEST`), `step_execution_id`, `actor_type`, `actor_id`, `event_type`, `model_id`, `inference_tier`, `effort`, `input_tokens`, `output_tokens`, `cost_usd`, `native_metric_type`, `native_metric_value`, `reported_by_remote`, `latency_ms`, `trace_id`, `run_lock_sha256`, les hashes `SHA-256` du *Pré-prompt IA* et du *Contrat du workflow*, et les références CAS (`SeaweedFS`) des prompts/chunks KB injectés (`FR-25`, `AD-12`, `AD-19`, `AD-21`)
**And** toute tentative de `UPDATE` ou `DELETE` sur `audit_ledger` lève une exception PostgreSQL immédiate.

**Given** un auditeur habilité dans **📊 FinOps** (`g f`, `apps/web/src/features/finops/`)
**When** il inspecte un *Workflow Run* ou appelle `GET /api/v1/audit/ledger/{run_id}/export?format=json|md`
**Then** le système génère le dossier complet de **Provenance Auditable** attestant qu'aucune étape n'a consommé une ressource absente de `run-lock.json`
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`) et d'intégration (`testcontainers` PG18 vérifiant le trigger append-only + SeaweedFS) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

### Story 6.2: Comptabilité FinOps Complète (Coût de Setup + Coût de Run vs TTM) & Coupe-Circuits Budgétaires / Anti-Boucles

As a Directrice de BU ou Responsable d'Équipe (`Claire UJ-8`, `Marc UJ-5`),
I want comptabiliser en temps réel le coût complet d'un processus (amortissement du Setup + coût des tokens LLM + temps humain de cadrage/revue) comparé au gain de Time-to-Market, et suspendre automatiquement tout Run qui dépasse son plafond budgétaire ou son nombre maximal de tentatives,
So that nous mesurions la réduction de $\ge 25\%$ du coût complet (`SM-1`) tout en éliminant tout risque de dérive financière par boucle d'agents infinie (`FR-26`, `AD-12`, `AD-19`).

**Acceptance Criteria:**

**Given** un *Workflow*, un *Workflow Run* et la hiérarchie de périmètres (`GLOBAL -> BU -> TEAM -> WORKSPACE`, `AD-21`) configurés avec `max_cost_usd`, quotas hiérarchiques et `max_agent_retries` (défaut : `3`), ainsi qu'une baseline déclarée de coût et de TTM manuel
**When** un Step accumule des appels LLM (y compris les escalades du routeur `auto` enregistrées dans `inference_attempts`) ou des boucles de correction suite à un rejet de Gate
**Then** le coupe-circuit vérifie à chaque appel LLM coûteux et à chaque transition les seuils du Run et du périmètre : s'ils sont atteints, il suspend immédiatement l'étape en statut `PAUSED_BUDGET_EXCEEDED` ou `PAUSED_MAX_RETRIES`, émet une alerte SSE via `domain_events_outbox` au responsable du Run, et exige un arbitrage humain ou une extension explicite (`POST /api/v1/runs/{run_id}/budget-override`) pour reprendre (`FR-26`, `AD-12`, `AD-19`, `AD-21`).

**Given** une Directrice de BU (`Claire, UJ-8`) qui consulte **📊 FinOps** ou interroge `Mon Assistant`
**When** le tableau de bord FinOps est affiché
**Then** il ventile par *Step*, par *Tier cognitif (`simple | medium | complex | auto`)* et *niveau d'Effort (`default | fast | balanced | deep`)*, par *Workflow Run*, par *Workflow* et par *Équipe/BU* le **Coût de Setup** (temps de conception/maintenance du workflow), le **Coût de Run** (tokens LLM en `numeric(12, 6)` USD + temps humain valorisé) et l'écart de **Time-to-Market (TTM)** par rapport à la baseline (`SM-1`, `SM-5`, `AD-21`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`hypothesis` sur les calculs de coûts et coupe-circuits) et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du service FinOps (`AD-17`, `AD-19`).

### Story 6.3: Tableau de Bord Exécutif d'Impact Cognitif, Anti-Rubber-Stamping & Indice de Réversibilité Humaine

As a Directrice de BU, Tech Lead ou SecOps (`Claire UJ-8`, `Marc UJ-5`, `Sophie UJ-6`),
I want suivre par Workflow et par Équipe/BU les 3 contre-métriques de gouvernance humaine et technique (Ratio Cadrage Actif $\ge 40\%$, Taux de Rubber-Stamping $< 5\%$, Indice de Pattern Drift / Réversibilité Humaine $0\%$) et recevoir des recommandations automatiques d'ajustement des Gates,
So that l'accélération par l'IA ne transforme jamais nos experts humains en simples tamponneurs passifs ni notre codebase en boîte noire non maintenable (`FR-27`, `AD-19`, `SM-C1`, `SM-C2`, `SM-C3`).

**Acceptance Criteria:**

**Given** les données agrégées depuis `human_anchor_signatures`, `human_arbitration_requests`, `gate_evaluations` (`review_duration_ms`, `fast_approval_warning`) et `audit_ledger`
**When** l'utilisateur ouvre l'onglet Gouvernance & Réversibilité de **📊 FinOps** (`g f`, `apps/web/src/features/finops/`)
**Then** le système calcule et affiche par *Workflow*, *Équipe* et *BU* les **3 indicateurs de maîtrise humaine (`FR-27`)** :
1. **Ratio Cadrage Actif ("Human-Led Think") vs Simple Relecture (`SM-C2`)** : $\frac{\text{Temps Ancrages Humains} + \text{Arbitrages} + \text{Challenges}}{\text{Temps Humain Total}}$ (alerte ambre si $< 40\%$).
2. **Taux de Validation Aveugle / Rubber-Stamping (`SM-C1`)** : pourcentage d'approbations aux Gates Humaines avec `fast_approval_warning: true` ou sans ouverture du *Briefing de Revue* (alerte rouge si $\ge 5\%$).
3. **Indice de Pattern Drift & Réversibilité Humaine (`SM-C3`)** : taux d'écarts architecturaux détectés par rapport à `ARCHITECTURE-SPINE.md` (cible $0\%$ hors dérogation signée).

**Given** un *Workflow* présentant un taux d'approbation aux *Gates Humaines* $> 98\%$ avec un temps médian de revue inférieur au seuil minimal et `0` modification/commentaire sur une période donnée
**When** l'analyseur de gouvernance évalue le *Workflow*
**Then** il génère une alerte et une recommandation actionnable proposant soit de basculer la *Gate* en politique `risk_or_exception_based` / `sampling`, soit de renforcer les *Ancrages Humains Obligatoires* (`FR-27`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`), d'évaluation (`orcia-evals`) et E2E (`Playwright`) couvrent $\ge 90\%$ du tableau de bord et des règles d'alerte (`AD-17`, `AD-19`).

### Story 6.4: Télémétrie FinOps Multi-Métriques des Services MCP & Agents Distants (`_meta.usage` / `X-Orcia-Usage`), `RemoteUsageSanitizer`, Onglet `🌐 Par Service MCP & Agent Distant` & Coupe-Circuit Isolé par Connecteur (`AD-12`, Principe M.3)

As a Directrice de BU, Administrateur Plateforme ou Chef d'Équipe (`Claire UJ-8`, `Karim UJ-9`, `Marc UJ-5`),
I want collecter et normaliser les métriques de consommation retournées par les serveurs MCP et agents distants (`Tokens LLM distants`, `Coût monétaire €/$`, `Unités/Crédits métiers` + barème de conversion en fallback), les protéger contre toute donnée corrompue via `RemoteUsageSanitizer`, ventiler clairement le coût interne vérifié et le coût externe déclaré dans `📊 FinOps`, et isoler le coupe-circuit de chaque connecteur,
So that nous suivions le coût consolidé réel sans jamais additionner des choux et des carottes ni laisser un serveur MCP tiers bogué épuiser le budget global ou bloquer les LLM internes (`FR-26`, `AD-12`, `AD-19`, `Principe M.3`).

**Acceptance Criteria:**

**Given** un appel exécuté via `ConnectorInvoker` vers un serveur MCP ou un agent distant A2A retournant un bloc `CallToolResult._meta.usage` ou un en-tête `X-Orcia-Usage` (ou ne retournant aucune métrique)
**When** le **`RemoteUsageSanitizer`** (`packages/orcia-core/audit_finops`) inspecte la télémétrie reçue avant publication dans `domain_events_outbox` (`StepCompleted`)
**Then** :
1. Il extrait les 3 formats de métriques (`input_tokens`/`output_tokens` distants, `cost`/`currency`, ou `units`/`unit_name` tels que `pages_ocr`, `recherches_api`, `minutes_gpu`) ou applique le **barème de conversion par défaut** configuré sur le connecteur (`coût fixe par appel` ou `coût par unité × taux de change €`) ;
2. Il rejette toute valeur négative (`< 0`), `NaN` ou `Infinity`, applique le plafond de sécurité par appel **`max_reported_cost_per_call`** (défaut `5,00 €`) en écrêtant la valeur au-delà et en émettant `REMOTE_USAGE_ANOMALY_CAPPED`, et convertit `native_currency` vers le pivot `numeric(12, 6)` USD en base (`AD-12`) pour un affichage unifié en `€` ;
3. Si un service distant dépasse son sous-plafond mensuel ou journalier dédié (ex. `max 50 € / mois` ou `500 appels / jour`), seul le coupe-circuit de ce connecteur passe à **`CIRCUIT_OPEN`** dans `ConnectorInvoker` (`AD-12`), sans bloquer les modèles LLM internes de l'Espace.

**Given** l'écran **`📊 FinOps`** (`apps/web/src/features/finops/`)
**When** l'utilisateur consulte les **4 compteurs KPI d'en-tête** et l'onglet **`🌐 Par Service MCP & Agent Distant`**
**Then** :
1. Le compteur 1 (**`COÛT CONSOLIDÉ (€)`**) affiche le total en `€` en distinguant visuellement **`Coût interne vérifié : X €`** et **`Coût externe déclaré (MCP) : Y €`** ;
2. Le compteur 2 (**`TOKENS LLM (INTERNES & DISTANTS)`**) additionne uniquement de vrais tokens LLM, tandis que le compteur 3 (**`APPELS & UNITÉS EXTERNES (MCP)`**) affiche séparément le nombre d'appels et les unités métiers (`pages OCR`, `requêtes API`, `crédits`) ;
3. L'onglet **`🌐 Par Service MCP & Agent Distant`** affiche la table détaillée (*Service / Agent*, *Type*, *Appels*, *Métrique native consommée*, *Mode de valorisation `🟢 Temps réel (_meta.usage)` vs `🔵 Barème fixe`*, *Coût consolidé (€)* et *Quota / Plafond*)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest` + `hypothesis` sur `RemoteUsageSanitizer` avec valeurs négatives/`NaN`/overflow, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

## Epic 7: Agents & Workflows Autonomes sous Contrat, Déclencheurs Événementiels (Webhooks, Puits de Logs, Cron), Auto-Remédiation, Génération Automatique d'Aide & Gouvernance Post-Hoc

Permettre aux Directeurs de BU, Chefs d'Équipe (`TEAM_LEAD`), Ingénieurs SRE/Plateforme et Auditeurs SecOps (`Claire UJ-8/UJ-11`, `Marc UJ-5`, `Karim UJ-9/UJ-12`, `Sophie UJ-6`) de configurer et signer des **Contrats d'Autonomie** sur les workflows éligibles (`LOW_NON_CRITICAL`, `STANDARD`), de déclencher de manière idempotente des **Workflow Runs autonomes** par action manuelle *Fire-and-Forget*, par **Webhooks signés** (Jira, Git, Confluence), par **Tâches Planifiées (`CRON`, `UJ-11`)**, par **Événement Outbox de publication de Pack/Processus (exécutant automatiquement `generate-and-attach-help` sous contrat d'autonomie `AD-18`)**, ou par **Alertes de Puits de Logs (`LOG_SINK_ALERT`, `UJ-12` : boucle fermée d'auto-remédiation AIOps avec diagnostic $\ge 0.90$, reproduction/correction TDD en Sandbox Palier 2, test staging prod-like, déploiement et vérification post-action dans les logs avec Rollback automatique)**, et de superviser ces runs via le badge `AutonomousExecutionBadge` (`UX-DR17`), l'échantillonnage d'audit *post-hoc* (`POST_HOC_AUDIT_SAMPLE`) et les sorties de secours (`🛑 Kill-Switch` et `⏪ Invalider & Rollback`).

### Story 7.1: Contrat d'Autonomie Signé, Identité Service-Principal Scopée & Régime d'Exécution `AUTONOMOUS_CONTRACT`

As a Chef d'Équipe ou Ingénieur SecOps (`Marc UJ-5`, `Sophie UJ-6`),
I want déclarer et signer un Contrat d'Autonomie sur un Workflow éligible (`LOW_NON_CRITICAL` ou `STANDARD`), lui attacher un `service_principal` à privilèges minimaux et activer le régime `AUTONOMOUS_CONTRACT`,
So that les processus répétitifs, analytiques (`UJ-11`) ou documentaires (`generate-and-attach-help` classé `LOW_NON_CRITICAL`) puissent s'exécuter de bout en bout sans intervention humaine synchrone tout en bloquant formellement toute autonomie non supervisée sur les processus `HIGH_CRITICAL` (`FR-5`, `FR-22`, `FR-29`, `AD-3`, `AD-6`, `AD-18`, `AD-19`, `Principe D.4`).

**Acceptance Criteria:**

**Given** un *Workflow* enregistré dans le Catalogue
**When** un `TEAM_LEAD` tente d'activer `execution_regime: AUTONOMOUS_CONTRACT` sur un workflow de criticité `HIGH_CRITICAL`
**Then** l'API rejette la requête avec `HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE` (`AD-18`, `FR-29`)
**And** sur un workflow `LOW_NON_CRITICAL` (tel que `orcia://pack-builder/workflows/generate-and-attach-help`) ou `STANDARD`, l'activation requiert la signature d'un **Contrat d'Autonomie** dans `human_anchor_signatures` (co-signé par un `SECOPS` si une identité `service_principal` est utilisée), définissant les sources autorisées en lecture seule, la liste blanche des *Actions Staged* (ex. publication d'une fiche `HELP_ARTICLE` dans `catalog_items` + `cas/<sha256>` + export `.md` Git), les plafonds budgétaires et la `tie_break_policy`.

**Given** un *Workflow Run* s'exécutant sous `AUTONOMOUS_CONTRACT` (`UJ-11` ou `generate-and-attach-help`)
**When** toutes les *Gates Déterministes* (`PASS`, y compris `validate_help_article` en Sandbox Palier 1) et *Gates Agentiques* (`agentic_score >= 0.85`, `fact_verification >= 0.90`, `0` conflit d'ontologie, `0` `[STALE_WARNING]`) sont franchies
**Then** le Run finalise son livrable et exécute les seules *Actions Staged* autorisées par le contrat avec le statut `COMMITTED_AUTONOMOUS`
**And** si un seuil de Gate n'est pas atteint ou qu'un conflit survient, le Run suspend immédiatement l'action d'écriture et escalade vers l'équipe propriétaire (`PAUSED_AUTONOMOUS_ESCALATION`) via `domain_events_outbox`
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest` + `hypothesis`) et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

**Given** la Story `3.2f` livrée (Avenant A2) et le modèle à 6 verbes d'`AD-21` (`Story 8.1`)
**When** un *Run* `AUTONOMOUS_CONTRACT` exécute une étape ou une *Action Staged* autorisée par le contrat
**Then** l'action passe par le `ConnectorInvoker` (coupe-circuit par connecteur, `idempotency_key`, relances passagères seulement), l'identité `service_principal` est évaluée selon le verbe **`execute`** (avec respect du moindre privilège par étape `Lire` vs `Écrire` déclaré dans le Studio) et n'utilise que des `SecretRef` résolues par `SecretProviderPort` (`NFR-SEC-4`, `AD-21`).

### Story 7.2: Déclencheurs Événementiels Idempotents (`WEBHOOK`, `LOG-SINK-ALERT`, `CRON`, `OUTBOX_EVENT`, `MANUAL_AUTONOMOUS`), Déduplication & Protection Anti-Boucle (*Self-Trigger Guard*)

As a Ingénieur Plateforme / SRE ou Directrice de BU (`Karim UJ-9/UJ-12`, `Claire UJ-11`),
I want enregistrer des déclencheurs autonomes planifiés (`CRON`) ou événementiels (`WEBHOOK` Jira/Git/Confluence, `LOG_SINK_ALERT` depuis le puits de logs, ou événement interne `domain_events_outbox` tel que la publication d'un Pack ou d'un Processus déclenchant `generate-and-attach-help`) exécutés par le rôle `trigger-dispatcher` et dotés d'une clé d'idempotence stricte (`DBOS SetWorkflowID`), d'une fenêtre de cooldown et d'un garde-fou anti-auto-déclenchement,
So that les rapports analytiques périodiques (`UJ-11`), la mise à jour automatique des fiches d'aide (`Principe D.4`) et les diagnostics d'erreurs de logs (`UJ-12`) se lancent automatiquement sans jamais créer de doublons lors des ré-essais ni provoquer de tempête de boucles infinies (`FR-24`, `FR-26`, `FR-29`, `AD-12`, `AD-18`, `AD-19`).

**Acceptance Criteria:**

**Given** un déclencheur actif dans `workflow_triggers` (`WEBHOOK`, `LOG_SINK_ALERT`, `CRON` via `@DBOS.scheduled`, écouteur d'événement `domain_events_outbox` ou `MANUAL_AUTONOMOUS`) configuré depuis la modale **`⚡ Déclencheurs`** du Studio (`Story 8.5`) et géré par le rôle `trigger-dispatcher` (`M9`, `AD-19`, `AD-21`)
**When** deux événements identiques (même `X-Webhook-Delivery-Id`, même `error_fingerprint_sha256` dans la fenêtre `cooldown_window_seconds`, même publication de version `@vX.Y.Z`, ou même fenêtre `CRON`) ou un ré-essai se présentent simultanément
**Then** `DBOS SetWorkflowID("<trigger_id>:<idempotency_key>")`, le verrou atomique Redis `SET lock:trigger:{trigger_id}:{idempotency_key} NX EX 86400` et la contrainte PostgreSQL `UNIQUE (trigger_id, trigger_idempotency_key)` garantissent qu'un seul `workflow_run` est créé (`AD-18`).

**Given** un événement Webhook, Outbox ou de puits de logs dont l'émetteur est le `service_principal` d'ORCIA ou qui contient le marqueur `x-orcia-origin-run-id`
**When** le récepteur de triggers inspecte l'événement
**Then** le **Self-Trigger Guard** ignore l'événement et publie la prévention de boucle dans `domain_events_outbox` vers `audit_ledger`
**And** si le déclencheur dépasse `max_runs_per_hour`, `max_daily_cost_usd` ou `max_consecutive_failures` (défaut `3`), son statut passe automatiquement à `CIRCUIT_OPEN` avec alerte SSE `< 500 ms`
**And** `lint-imports` passe à `0` violation et les tests unitaires et d'intégration sous concurrence (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du dispatcher de triggers (`AD-17`, `AD-19`).

**Given** la Story `3.2f` livrée (Avenant A2)
**When** un déclencheur `WEBHOOK` ou `LOG_SINK_ALERT` instancie un *Run* dont une étape échoue sur un connecteur
**Then** l'échec est classé par la taxonomie `orcia_kernel.errors` : seules les erreurs passagères sont relancées par le `ConnectorInvoker`, et les erreurs fonctionnelles comptent dans `max_consecutive_failures` du déclencheur sans relance automatique.

### Story 7.3: Boucle Fermée d'Auto-Remédiation (`UJ-12` : Diagnostic >= 0.90, Reproduction TDD en Sandbox Palier 2, Test Staging Prod-Like, Déploiement & Vérification Post-Action avec Rollback Automatique)

As a Ingénieur SRE ou Tech Lead (`Karim UJ-12`, `Yanis UJ-3`),
I want qu'une erreur détectée dans le puits de logs déclenche un workflow autonome de diagnostic qui, uniquement si la cause racine est certaine ($\ge 0.90$), rédige l'intention de remédiation, reproduit et corrige le bug par tests unitaires TDD en Sandbox Palier 2 (`TIER_2_CONTAINER < 60 s`), valide le correctif au plus proche des conditions de production, l'applique en production puis vérifie dans le puits de logs que l'erreur a disparu (avec Rollback automatique sinon),
So that les incidents récurrents à cause racine claire soient résolus en quelques minutes avec la même rigueur d'ingénierie qu'un développeur senior et une sécurité de retour arrière immédiat (`FR-13`, `FR-17`, `FR-18`, `FR-29`, `FR-30`, `AD-9`, `AD-10`, `AD-18`, `AD-19`, `UJ-12`).

**Acceptance Criteria:**

**Given** un *Workflow Run* d'auto-remédiation déclenché par `LOG_SINK_ALERT` (`UJ-12`)
**When** l'étape de diagnostic analyse la stacktrace et le *Graphe Tripartite (`Confluence ↔ Jira ↔ Git`)*
**Then** si `root_cause_confidence < 0.90` ou si le périmètre touche une zone `HIGH_CRITICAL`, le workflow s'arrête immédiatement après le diagnostic et crée un ticket Jira d'escalade sans modifier aucun code (`FR-29`, `AD-18`).

**Given** un diagnostic avec `root_cause_confidence >= 0.90` sur un périmètre autorisé par le *Contrat d'Autonomie*
**When** le workflow poursuit la chaîne de remédiation (potentiellement structurée en `SUB_WORKFLOW`, `FR-30`)
**Then** il exécute séquentiellement : (1) la génération et validation de l'**Intention de Remédiation** (`FR-13`), (2) l'écriture dans le service hors processus `sandbox-runner` Palier 2 (`TIER_2_CONTAINER`, `gVisor/Podman rootless --network=none < 60 s`, `AD-9`, `P5`, sans Rust selon `Q5`) d'un test unitaire reproduisant l'erreur (`Red`) puis du correctif applicatif ou IaC faisant passer 100 % des tests unitaires et du contrôle anti-*Pattern Drift* (`Green`) validé par une *Gate Agentique Orthogonale* (`AD-10`), (3) le déploiement et le test de non-régression / rejeu de trafic sur l'environnement **Staging / Prod-Like**, (4) la mise en production selon la stratégie du contrat, et (5) l'étape obligatoire **`POST_ACTION_VERIFICATION`** qui observe le puits de logs et les métriques pendant `verification_window_seconds`
**And** si l'erreur réapparaît dans le puits de logs ou si le taux d'erreur/latence se dégrade pendant `POST_ACTION_VERIFICATION`, ORCIA déclenche automatiquement le **Rollback** vers la version précédente, bascule le déclencheur en `CIRCUIT_OPEN` et notifie l'astreinte en `< 500 ms` via `domain_events_outbox`
**And** `lint-imports` passe à `0` violation et les tests unitaires, cassettes déterministes (`DeterministicCassetteLLM`) et tests d'intégration (`testcontainers` PG18 + Redis + SeaweedFS) couvrent $\ge 90\%$ de la boucle fermée et du Rollback automatique (`AD-17`, `AD-19`).

**Given** les Stories `3.2e` et `3.2f` livrées (Avenant A2, `AD-20`)
**When** la boucle d'auto-remédiation génère l'Intention de Remédiation puis le correctif
**Then** la discipline `Intention -> Code` (`FR-13`) est appliquée par la politique `orcia.workflow_policies` du pack `orcia-pack-sdlc` (étapes étiquetées `sdlc.declares_intention` / `sdlc.writes_code`), les marqueurs émis sont à espace de noms (`sdlc.*`), et le déploiement et le Rollback passent par le `ConnectorInvoker` avec bail `ResourceLeasePort` sur la cible (`DEC-CONC-01`).

### Story 7.4: Supervision UX des Runs Autonomes (`AutonomousExecutionBadge`, `UX-DR17`), Sorties de Secours (`Kill-Switch` & `Rollback`), Échantillonnage Post-Hoc & Métriques `SM-A1..A3`

As a Directrice de BU, Chef d'Équipe ou Auditeur SecOps (`Claire UJ-8/UJ-11`, `Marc UJ-5`, `Sophie UJ-6`),
I want distinguer visuellement tout run ou livrable exécuté sans humain (`AutonomousExecutionBadge`), disposer d'un filtre regroupé par déclencheur dans le tiroir `🔔 Notifications` et `Mes Processus › Exécutions & Décisions`, auditer par échantillonnage post-hoc une fraction des runs autonomes, actionner en 1 clic le `Kill-Switch` ou l'invalidation/Rollback (y compris le retour à `@v(N-1)` d'une fiche `HelpArticle` rattachée automatiquement), et suivre les indicateurs `SM-A1`, `SM-A2`, `SM-A3` séparément des indicateurs `SM-C1`/`SM-C2`,
So that l'ouverture aux workflows autonomes préserve la lisibilité cognitive du portail (Loi de Hick), la transparence d'audit et le contrôle humain immédiat (`FR-27`, `FR-29`, `AD-19`, `UX-DR17`, `Principe D.4`, `SM-C1`, `SM-C2`, `SM-A1`, `SM-A2`, `SM-A3`).

**Acceptance Criteria:**

**Given** un *Workflow Run* ou un *Artefact* (y compris une fiche `HelpArticle` dans la Colonne `❓`) produit sous `AUTONOMOUS_CONTRACT`
**When** il est affiché dans le Cockpit, le tiroir `🔔 Notifications`, `Mes Processus › Exécutions & Décisions`, la Colonne `❓` ou `Mes Espaces`
**Then** le composant **`AutonomousExecutionBadge` (`UX-DR17` dans `@orcia/ui`)** est rendu en Cyan/Cobalt (`#0284C7` / fond `#F0F9FF`, **jamais** en Violet `#6D28D9` réservé à `HumanLedAnchorCard`) avec la mention du contrat et du déclencheur, les runs autonomes nominaux sont regroupés par déclencheur dans un tiroir replié (seules les escalades, ouvertures `CIRCUIT_OPEN` et tirages `POST_HOC_AUDIT_SAMPLE` remontant en priorité), et les boutons **`🛑 Kill-Switch`** et **`⏪ Invalider & Rollback`** (restaurant instantanément `@v(N-1)` dans `catalog_items` et invalidant le cache Redis `< 10 ms` pour les fiches d'aide) sont immédiatement accessibles.

**Given** le module **📊 FinOps** (`g f`, `apps/web/src/features/finops/`)
**When** les indicateurs de gouvernance sont calculés
**Then** `SM-C1` et `SM-C2` sont calculés sur le périmètre des runs interactifs et des Gates Humaines sans être faussés par les runs autonomes, tandis que les 3 nouveaux indicateurs **`SM-A1` (Taux d'Escalade Autonome)**, **`SM-A2` (Taux d'Invalidation Post-Hoc / Rollback, cible $< 1\%$)** et **`SM-A3` (Coût Moyen & Gain TTM par Run Autonome)** sont affichés avec alerte automatique si `SM-A2 >= 1%`
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`), d'intégration (`testcontainers` PG18) et E2E (`Playwright`) couvrent $\ge 90\%$ des composants `UX-DR17`, du `Kill-Switch` et des métriques `SM-A1..A3` (`AD-17`, `AD-19`).

## Epic 8: Hub de Paramétrage Post-Jour 0 (`/settings/*`), Gouvernance d'Entreprise à 6 Verbes (`RBAC/ABAC`), Routage Cognitif Abstrait (`simple|medium|complex|auto` & Effort), Studio Visuel Avancé (`Couches`, `Contrat`, `Pré-prompt`) & Wizards d'Initialisation Durables

Permettre aux Administrateurs Plateforme (`Karim UJ-9`), Ingénieurs SecOps (`Sophie UJ-6`), Directeurs de BU (`Claire UJ-8`) et Chefs d'Équipe / Tech Leads (`Marc UJ-5`, `Yanis UJ-3`) d'administrer ORCIA après le Jour 0 sans redéploiement via le **Hub de Paramétrage (`/settings/{iam,connectors,ai-models,packs,workflows,audit}`)** protégé par concurrence optimiste (`ETag`/`If-Match` `412`) et contrat de secret en écriture seule (`SecretInput`/`SecretStatus`), d'appliquer un modèle d'habilitations hiérarchique **RBAC/ABAC à 6 verbes (`create, read, update, delete, execute, grant`)** distinguant l'utilisation (`execute`) de la lecture des secrets (`read`) avec délégation bornée (`grant`), d'abstraire les modèles LLM en **Tiers Cognitifs (`simple €, medium €€, complex €€€, auto ⚡`)** et **niveaux d'Effort** avec escalade déterministe rejouable sous DBOS, d'enrichir le **Studio Visuel de Workflows** (5 onglets de cycle de vie, immutabilité des versions publiées, `Pré-prompt IA`, `Contrat du workflow`, `Déclencheurs`, `▷ Tester`, inspecteur **`COUCHES · N`** et moindre privilège connecteur par étape), et d'embarquer toute nouvelle équipe sans page blanche grâce à **3 Wizards d'Initialisation Durables DBOS (`/wizards/*`)**.

### Story 8.1: Modèle d'Habilitations Hiérarchique RBAC/ABAC à 6 Verbes (`create, read, update, delete, execute, grant`), Délégation Bornée & Invariants Anti-Verrouillage

As a Ingénieur SecOps, Administrateur Plateforme ou Chef d'Équipe (`Sophie UJ-6`, `Karim UJ-9`, `Marc UJ-5`),
I want évaluer toutes les permissions selon une matrice hiérarchique à 6 verbes atomiques (`create, read, update, delete, execute, grant`) sur l'arbre `Organisation -> BU -> Équipe -> Workspace -> Pack -> Ressource -> Action`, permettre à un `TEAM_LEAD` titulaire du verbe `grant` de déléguer localement un sous-ensemble de ses droits sans escalade de privilèges, et empêcher tout verrouillage administratif accidentel,
So that un contributeur ou un agent puisse exécuter (`execute`) un connecteur, un modèle IA ou un workflow sans jamais lire (`read`) ses secrets, que les ressources non autorisées restent découvrables passivement (`🔒 Non habilité` + demande d'accès), et que le dernier administrateur ou IdP ne puisse jamais être désactivé (`FR-27`, `AD-6`, `AD-19`, `AD-21`, `NFR-SEC-3`).

**Acceptance Criteria:**

**Given** la migration Alembic créant/étendant les tables d'habilitations hiérarchiques (`role_permission_grants` avec `scope_path`, `verb IN ('create','read','update','delete','execute','grant')`, ainsi que les colonnes préparatoires `effect DEFAULT 'ALLOW'`, `inheritance_block DEFAULT FALSE`, `conditions_jsonb DEFAULT '{}'` et `hidden_when_unauthorized DEFAULT FALSE` pour `ACTION_ITEM-8.1..8.3`)
**When** le *Permission Broker* (`packages/orcia-core/permissions`) évalue une requête d'accès ou d'exécution sur une ressource
**Then** un sujet disposant de `execute` sans `read` peut invoquer la ressource via `ConnectorInvoker` / `LLMPort` mais se voit refuser (`HTTP 403`) tout accès en lecture aux paramètres secrets ou à la configuration détaillée
**And** si le sujet ne dispose ni de `read` ni de `execute`, l'API retourne les métadonnées publiques de découverte passive (`locked: true`, `reason: "MISSING_PERMISSION"`, bouton *Demander l'accès* émettant `AccessRequested` dans `domain_events_outbox`), sauf si `hidden_when_unauthorized: true` auquel cas l'API retourne `HTTP 404` (`AD-21`).

**Given** un responsable local (`TEAM_LEAD` ou `BU_DIRECTOR`) disposant du verbe `grant` sur son périmètre ou un administrateur modifiant les accès dans `/settings/iam`
**When** il délègue un rôle/droit à un membre ou Service Principal **OU** tente de retirer le dernier `PLATFORM_ADMIN` actif / désactiver la dernière méthode d'authentification active
**Then** le moteur vérifie l'invariant de confinement $\text{Droits délégués} \subseteq \text{Droits détenus}$ (rejetant toute escalade avec `HTTP 403 ERR_GRANT_ESCALATION_FORBIDDEN`), rejette toute tentative de verrouillage avec `HTTP 422 ERR_ADMIN_LOCKOUT_PREVENTED`, et publie chaque octroi/révocation dans `domain_events_outbox` (`PermissionGranted`, `PermissionRevoked`, `SettingsChanged`) consommé par `audit_ledger`
**And** toute révocation de Service Principal ou de droit `execute` prend effet au plus tard à la **prochaine frontière de `@DBOS.step`** des runs en cours (`AD-21`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest` + `hypothesis` sur l'arbre d'héritage et l'invariant de confinement `grant`) et d'intégration (`testcontainers` PG18) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

### Story 8.2: Abstraction Cognitive des Modèles LLM (`simple, medium, complex, auto`), Niveaux d'Effort (`default, fast, balanced, deep`), Budgets Hiérarchiques & Escalade Déterministe DBOS (`PROC-01`)

As a Architecte IA, Directrice de BU ou Concepteur de Workflow (`Karim UJ-9`, `Claire UJ-8`, `Yanis UJ-3`),
I want que les étapes de workflows référencent exclusivement des tiers cognitifs abstraits (`simple €, medium €€, complex €€€, auto ⚡`) et des niveaux d'effort (`default, fast, balanced, deep`) mappés par Workspace dans `/settings/ai-models` vers les fournisseurs/modèles physiques LiteLLM, avec escalade automatique déterministe en mode `auto` et protection `HTTP 409` des modèles épinglés par des runs actifs,
So that nous puissions changer de modèle ou de fournisseur IA à chaud sans éditer aucun workflow, optimiser automatiquement les coûts FinOps via le tier `auto` sans briser le déterminisme du rejeu DBOS, et respecter l'Orthogonalité des Modèles (`FR-19`, `FR-24`, `AD-10`, `AD-12`, `AD-19`, `AD-21`, `PROC-01`).

**Acceptance Criteria:**

**Given** la migration Alembic créant `workspace_llm_tier_mappings` (associant par `scope_id` chaque `InferenceTier: simple | medium | complex | auto` et niveau d'`effort: default | fast | balanced | deep` à un fournisseur/modèle `LiteLLM`, un `secret_ref`, des paramètres d'inférence, un budget de tokens et un ordre de fallback) et la table `inference_attempts`
**When** un `@DBOS.step` exécute un appel LLM avec `inference_tier: auto` (ou un tier explicite, défaut `medium`)
**Then** le routeur cognitif résout le mapping actif du Workspace, vérifie que l'invariant d'**Orthogonalité des Modèles (`AD-10`)** entre Agent Exécuteur et Agent Évaluateur est respecté, démarre en mode `auto` sur le tier `simple` et, uniquement si la *Gate Déterministe* (schéma JSON/Pydantic ou assertion Sandbox) échoue, escalade vers `medium` puis `complex` en enregistrant chaque tentative comme sous-étape idempotente dans `inference_attempts` (garantissant qu'un rejeu DBOS après crash ne ré-exécute pas les paliers déjà tentés) (`AD-21`).

**Given** un administrateur dans `/settings/ai-models` qui modifie un plafond budgétaire hiérarchique (`GLOBAL -> BU -> TEAM -> WORKSPACE`) ou tente de supprimer un modèle physique actuellement épinglé dans le `run-lock.json` d'un *Workflow Run* actif
**When** la requête est soumise à l'API
**Then** tout abaissement de budget s'applique immédiatement au **prochain appel LLM coûteux** sans faire échouer rétroactivement les étapes déjà validées, tandis que la suppression d'un modèle épinglé est refusée avec `HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` exposant la liste des runs actifs et les options explicites **Drainer** (bloquer les nouveaux runs) ou **Forcer** (`PLATFORM_ADMIN` uniquement)
**And** conformément à **`PROC-01`**, un *Workflow Run* réel de bout en bout traverse l'API (`instanciation -> exécution avec tier auto -> pause -> redémarrage -> reprise`) avec `0` contenu simulé et $\ge 90\%$ de couverture (`AD-17`, `AD-19`, `AD-21`).

### Story 8.3: Socle Settings Versionnés (`platform_settings`, `ETag`/`If-Match` `412`), Contrat Secret Write-Only (`SecretInput`/`SecretStatus`), Coquille `/settings/*`, Primitives `<PermissionGuard>` / `<SecretField>` & Console Rejeu Outbox

As a Administrateur Plateforme ou Ingénieur SecOps (`Karim UJ-9`, `Sophie UJ-6`),
I want disposer du socle relationnel versionné `platform_settings` protégé par `ETag`/`If-Match` (`HTTP 412`), du contrat de secret en écriture seule (`SecretInput`/`SecretStatus`) couplé au composant `<SecretField />`, de la coquille `/settings/{iam,connectors,ai-models,packs,workflows,audit}` gardée par `<PermissionGuard />`, et d'une console `/settings/audit` permettant le rejeu borné (`--dry-run`) des événements Outbox,
So that tout paramétrage post-Jour 0 soit versionné sans conflit d'édition concurrente, qu'aucun secret ne puisse jamais fuiter ni être écrasé par son masque visuel, et que le backlog Outbox soit gouvernable en toute sécurité (`AD-6`, `AD-12`, `AD-19`, `AD-21`, `NFR-SEC-4`).

**Acceptance Criteria:**

**Given** la migration Alembic créant `platform_settings` (`id` UUIDv7, `scope_level`, `scope_id`, `category`, `key`, `value_jsonb` sans secret, `secret_ref` UUIDv7 nullable, `version`, `etag`, `updated_at`, `updated_by`) et les schémas Pydantic v2 `SecretInput` (`action: "keep" | "set" | "clear"`) et `SecretStatus` (`configured`, `fingerprint: "sha256:<8-hex salé par resource_id>"`, `updated_at`, `updated_by`) dans `apps/api/src/orcia_api/schemas/settings.py`
**When** un client appelle `PATCH /api/v1/settings/...`
**Then** l'API exige l'en-tête `If-Match` (`HTTP 428 ERR_PRECONDITION_REQUIRED` si absent, `HTTP 412 ERR_SETTINGS_VERSION_CONFLICT` si périmé), rejette tout `READ_ONLY_OBSERVER` avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`, applique `SecretInput` via `SecretProviderPort` sans jamais retourner la valeur du secret, et émet exactement un événement `SettingsChanged` dans `domain_events_outbox`
**And** le **test du secret témoin (`DEC-SEC-01`)** prouve que la valeur secrète n'apparaît dans aucune réponse API, aucun log `structlog`, ni dans `platform_settings`, `domain_events_outbox`, `audit_ledger`, `step_executions` ou `dbos.*` (`NFR-SEC-4`, `AD-21`).

**Given** l'arborescence TanStack Router `/settings/{iam,connectors,ai-models,packs,workflows,audit}` et les composants `@orcia/ui` **`<PermissionGuard />`** et **`<SecretField />`**
**When** un utilisateur consulte `/settings/*` ou déclenche un rejeu depuis `/settings/audit` (`POST /api/v1/admin/outbox/replays`)
**Then** chaque route vérifie les permissions en `beforeLoad`, `<SecretField />` affiche uniquement l'empreinte `sha256` et les actions *Remplacer* / *Effacer* (sans jamais pré-remplir `••••••••`), et l'endpoint de rejeu Outbox borne le lot à $\le 500$ événements, cible un consommateur déclaré idempotent et s'exécute en mode `dry_run: true` par défaut
**And** `lint-imports` passe à `0` violation, le SDK OpenAPI `@orcia/api-client` est régénéré à `0-diff`, et les tests unitaires (`pytest`, `Vitest`), de contrat (`schemathesis`) et d'intégration (`testcontainers` PG18) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`, `AD-21`).

### Story 8.4: Hub des Connecteurs (`/settings/connectors`), Test de Connexion Fail-Fast DBOS, Garde-fous d'Ingestion (`C0–C3`, Arbitrage PII, Linter OCR `0 char`) & Test de Réciprocité RAG

As a Chef d'Équipe, Responsable Produit ou Ingénieur SecOps (`Marc UJ-5`, `Hélène UJ-1`, `Sophie UJ-6`),
I want administrer dans `/settings/connectors` les instances de sources de données par périmètre avec test de connectivité fail-fast DBOS, imposer à l'ingestion documentaire la classification `C0–C2` vs `C3`, la détection automatique de PII avec modale d'arbitrage humain, le rejet immédiat des PDF scannés vides (`0 char`), et vérifier en 1 clic la réciprocité RAG avec citation obligatoire,
So that aucune source mal configurée, aucun document `C3` non autorisé, aucune donnée personnelle non arbitrée ni aucune coquille PDF vide ne pollue le Graphe Tripartite ou les prompts des agents (`FR-10`, `FR-16`, `FR-17`, `AD-5`, `AD-8`, `AD-10`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** l'écran `/settings/connectors` (accompagné du `<GuidanceDrawer />` en 5 étapes) et un connecteur enregistré dans `orcia.connectors` (`git://`, `jira://`, `confluence://`, `db://`, `nexus://`, `s3://`, `mcp://`)
**When** un utilisateur habilité crée ou met à jour une instance dans `workspace_datasources` via `<SecretField />` et clique sur **`Tester la connexion`** (`POST /api/v1/settings/connectors/{id}/test-connection`)
**Then** un `@DBOS.step` de healthcheck à timeout court (`< 5 s`) vérifie l'authentification et la portée réelle auprès du système cible, persiste le statut (`HEALTHY` / `DEGRADED` / `UNREACHABLE`) et retourne un diagnostic RFC 9457 actionnable en cas d'échec (`AD-21`).

**Given** un utilisateur qui téléverse ou synchronise un document dans une source RAG du Workspace
**When** le pipeline d'ingestion pré-analyse le fichier
**Then** :
1. **Classification de sécurité obligatoire** : l'utilisateur doit qualifier la source en `C0–C2 (Interne / Standard)` ou `C3 (Confidentiel Restreint — exigeant un Workspace habilité C3)` ;
2. **Linter anti-coquille vide (`0 char` OCR fail-fast)** : tout PDF scanné ou document dont l'extraction texte produit `0` caractère exploitable est rejeté immédiatement avec l'erreur `HTTP 422 ERR_EMPTY_OR_UNREADABLE_DOCUMENT` avant toute vectorisation ;
3. **Garde-fou PII avec Arbitrage Humain** : si le scanner détecte des données personnelles (emails, nir, téléphones, IBAN), l'indexation se met en pause et affiche une modale d'arbitrage humain proposant **3 choix explicites** : *Pseudonymiser avant indexation* (via `PiiReversibleScrubber`), *Indexer tel quel (dérogation auditée dans `audit_ledger`)* ou *Annuler l'import* ;
4. **Test de Réciprocité RAG en 1 clic (*« Vérifier qu'il répond »*)** : une fois indexé, un bouton déclenche une micro-requête de contrôle sur le document et vérifie que l'agent restitue une réponse citant explicitement l'URI et le chunk du document (`AD-8`, `AD-21`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + SeaweedFS) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

### Story 8.5: Studio Visuel de Workflows Enrichi (5 Onglets de Cycle de Vie, Barre de Gouvernance `Pré-prompt`/`Contrat`/`Déclencheurs`/`Tester`, Inspecteur `COUCHES · N`, Moindre Privilège Connecteur) & Registre des Packs (`/settings/packs`)

As a Architecte, Tech Lead ou Product Manager (`Antoine UJ-2`, `Yanis UJ-3`, `Hélène UJ-1`),
I want gérer mes workflows dans un Studio structuré en 5 onglets de cycle de vie (`Publiés`, `Brouillons`, `Corbeille`, `Exécutions actives`, `Suspendus en arbitrage`) où toute édition d'une version publiée crée automatiquement une branche brouillon (`vX.Y.Z-draft`), configurer en barre supérieure le `Pré-prompt IA`, le `Contrat du workflow` (paramètres typés `p_1..p_n` + sections Markdown obligatoires), les `Déclencheurs` et le bac à sable `▷ Tester`, inspecter et désactiver à la volée les sous-couches d'une macro-étape via le popover **`COUCHES · N`**, borner chaque connecteur en `Lire` vs `Écrire` par étape, et activer les Packs Métier par périmètre dans `/settings/packs`,
So that le Workflow Studio offre une gouvernance industrielle complète de la conception jusqu'au test à blanc (*What-If*) sans jamais compromettre l'immutabilité des versions en production (`FR-1`, `FR-11`, `FR-14`, `FR-26`, `FR-30`, `AD-2`, `AD-5`, `AD-18`, `AD-19`, `AD-20`, `AD-21`).

**Acceptance Criteria:**

**Given** le Hub des Workflows (`/studio` et `/settings/workflows`) structuré en **5 onglets avec compteurs temps réel** (`Publiés`, `Brouillons`, `Corbeille`, `Exécutions actives`, `Suspendus en arbitrage`)
**When** un utilisateur clique sur **`Modifier`** sur un workflow à l'état `PUBLISHED` (ex. `v1.0.0`)
**Then** la version `v1.0.0` reste strictement immuable pour les `run-lock.json` existants et le système crée automatiquement une révision `v1.1.0-draft` éditable dans le Canvas `@xyflow/react` (`AD-14`, `AD-21`).

**Given** un workflow ouvert dans l'éditeur visuel `/studio/$workflowId`
**When** le concepteur utilise la **Barre Supérieure de Gouvernance (`<WorkflowTopGovernanceBar />`)**, les nœuds du graphe et le popover **`<LayersInspectorPopover />` (`COUCHES · N`)**
**Then** :
1. **`Pré-prompt IA`** : permet d'éditer les instructions système globales du workflow, épinglées par empreinte `SHA-256` dans `run-lock.json` ;
2. **`Contrat du workflow`** : définit les paramètres d'entrée typés (`p_1..p_n`, liés aux concepts de l'Ontologie) et la liste des sections Markdown obligatoires attendues en sortie (vérifiées automatiquement par une *Gate Déterministe* de structure) ;
3. **`▷ Tester` (Dry-Run *What-If*)** : génère dynamiquement un formulaire de test à partir du `Contrat du workflow` et lance une exécution en mode simulation isolée sans écriture externe ;
4. **Distinction bimodale & Moindre Privilège par étape** : chaque nœud distingue visuellement un `Program Executor` (déterministe) d'un `Agent Executor` (sélecteurs de `InferenceTier` et d'`Effort`), affiche les Gates sur les arêtes, et borne chaque connecteur attaché à l'étape au mode **`Lire` (`READ_ONLY`)** ou **`Écrire` (`READ_WRITE_STAGED`)** ;
5. **Inspecteur `COUCHES · N` sur les macro-étapes (`SUB_WORKFLOW`)** : affiche les sous-couches regroupées en 3 zones (*1. Entrées & Contexte*, *2. Capacités & Raisonnement*, *3. Livrables & Pré-Gates*), permet de réordonner, supprimer ou basculer l'icône œil `👁️` (`enabled: false`), ce qui marque la sous-étape `SKIPPED` dans le checkpoint DBOS sans rompre le graphe (`AD-21`).

**Given** l'écran `/settings/packs` listant les Packs Métier découverts via `entry_points` (`AD-20`, ex. `orcia-pack-sdlc`)
**When** un administrateur active, configure (via le JSON Schema exposé par le pack) ou désactive un pack sur un périmètre (`GLOBAL | BU | TEAM | WORKSPACE`)
**Then** la désactivation d'un pack utilisé par des runs actifs est protégée par `HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` (*Drainer* / *Forcer*), un pack désinstallé mais référencé en base s'affiche en statut `ORPHANED` sans crash au démarrage, et les tests unitaires (`pytest`, `Vitest`), d'intégration (`testcontainers` PG18) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`, `AD-20`, `AD-21`).

### Story 8.6: Parcours d'Initialisation Guidés par Profil (3 Wizards Durables DBOS `wizard_sessions`), Espace Démo Pré-rempli (*Zero Empty-State*) & Validation Bout-en-Bout

As a Nouvel Administrateur, Tech Lead SDLC ou Manager Métier (`Karim UJ-9`, `Yanis UJ-3`, `Hélène UJ-1`),
I want être guidé lors de la création ou de la configuration d'un espace par l'un des 3 Wizards Durables DBOS adaptés à mon Profil Humain (`Tech Lead SDLC`, `Business/Ops Manager`, `Platform/SecOps Admin`) avec sauvegarde automatique de ma progression (`wizard_sessions`), test fail-fast à chaque étape et option d'Espace Démo pré-rempli (*Zero Empty-State*),
So that n'importe quelle équipe puisse configurer ses sources, ses tiers IA, ses politiques de Gates et lancer son premier Workflow Run validé en moins de 10 minutes sans jamais faire face à une page blanche ni perdre sa saisie en cas d'interruption (`FR-28`, `AD-2`, `AD-16`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** la migration Alembic créant la table `wizard_sessions` (`id` UUIDv7, `wizard_type IN ('sdlc_tech_lead', 'ops_manager', 'secops_admin')`, `user_id`, `scope_id`, `current_step_index`, `state_jsonb`, `dbos_workflow_id`, `status`) et la route `/wizards/$wizardType`
**When** un utilisateur démarre un Wizard d'initialisation, ferme son navigateur à l'étape 3 sur 5, puis se reconnecte
**Then** le workflow durable DBOS restaure exactement l'état `wizard_sessions` à l'étape 3 (en ne stockant que des `secret_ref` via `SecretProviderPort`), permet de tester en 1 clic chaque connecteur ou modèle configuré avant de passer à l'étape suivante, et exécute en étape finale une micro-requête de réciprocité RAG prouvant que l'espace est opérationnel (`AD-16`, `AD-21`).

**Given** un nouvel utilisateur qui choisit l'option **« Démarrer avec l'Espace de Démonstration Pré-rempli (*Zero Empty-State*) »**
**When** le seeder idempotent (`packages/orcia-core/bootstrap/seeder.py`) provisionne l'espace de démonstration
**Then** l'utilisateur accède immédiatement à un Workspace pré-câblé avec une ontologie de référence, un corpus documentaire indexé, un workflow publié prêt à être testé dans le Studio ou le Cockpit, et `0` secret en clair
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`), d'intégration (`testcontainers` PG18 + Redis + SeaweedFS avec test de reprise après interruption du Wizard) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`, `AD-21`).

## Epic 9: Coquille Ergonomique 4 Zones (Style Portals / EXEMPLE), Recherche Fédérée `⌘K` à 2 Vitesses (*Zero Layout Shift*), Compte Utilisateur (`UserSettingsModal`), Accostage Jour 0 (`Accostage 1/6`) & Aide Contextuelle Hybride (`❓`)

Permettre à tous les utilisateurs d'ORCIA de bénéficier dès la première seconde d'une **Coquille Globale à 4 Zones** auto-descriptive (`TopHeaderBar 52px`, `Sidebar 240px/68px` aux **8 menus fixes non numérotés** `Cockpit | Mon Assistant | Mes Processus | Mes Agents | Mes Espaces | FinOps | Configuration | Aide` avec terminologie invariante **`Espace`**, `Zone Centrale 1fr` et `Colonne d'Aide Contextuelle ? 340px` auto-repliée sur `< 1440px`), d'un **Cockpit épuré** (extinction automatique des compteurs `0/0/0/0` quand `total == 0` et séparation entre décisions courtes `Tie-Break` et **Vue Fokus de Revue `Run #ID`** avec verrou Redis `AD-4`), d'un **Parcours d'Accostage Progressif Jour 0 (`Accostage 1/6`)** protégé contre le *First-User Takeover* (`LOCK TABLE users` + `ORCIA_BOOTSTRAP_TOKEN`) et débloquant l'essai dès `1 modèle LLM` ($\rightarrow \ge 2$ familles `AD-10`), d'une **Recherche Fédérée & Contextuelle `⌘K` à 2 vitesses sans saut visuel** (3 portées, 7 familles, lexical `< 30 ms` `0 $` en tête + vectoriel HNSW sur pause `450 ms` en bas avec *Deep-Linking Auto-Focus*), d'un **Menu Login (`UserAccountDropdown`) & Modale « Paramètres de mon compte » (`UserSettingsModal` à 4 onglets)** à double persistance `0 ms` anti-FOUC, et d'un **Système d'Aide Hybride (`HelpArticle` factorisé dans `catalog_items` + `cas/<sha256>`)** servi en `< 10 ms` via Redis (`Principes A, A.2, A.3, C, D, D.4, E, F, G`, `Section 2`).

### Story 9.1: Coquille 4 Zones Direction C (8 Menus Non Numérotés, Terminologie Fixe `Espace`, Cockpit Épuré avec Extinction `0/0/0/0` & Séparation Cockpit vs Vue Fokus de Revue `Run #ID`)

As a Utilisateur Métier, Chef d'Équipe ou Administrateur (`Hélène UJ-1`, `Marc UJ-5`, `Karim UJ-9`),
I want naviguer dans une coquille à 4 zones dotée de 8 entrées fixes non numérotées (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`), d'une terminologie invariante `Espace`, d'un Cockpit qui masque automatiquement les compteurs vides `0/0/0/0` et distingue les décisions courtes (`Tie-Break`) de la Vue Fokus de Revue (`Run #ID`),
So that l'interface reste immédiatement lisible sans surcharge visuelle (Loi de Hick) et que les revues d'artefacts complexes disposent de tout l'espace central et d'un verrou de présence exclusif (`Principes A, C, E, F, G`, `AD-4`, `AD-19`, `UX-DR1`, `UX-DR2`).

**Acceptance Criteria:**

**Given** un utilisateur connecté sur Desktop (`>= 1280px`) ou Laptop (`768px - 1279px`)
**When** la coquille applicative `AppShell` est affichée
**Then** elle structure l'écran en **4 zones strictes** : (1) `TopHeaderBar` (`52px`) contenant le sélecteur fixe **`Espace : [Nom] ⌄`** (`⌘W`), la barre de recherche fédérée `⌘K`, le bouton `? Aide`, le tiroir `🔔 Notifications` (`420px`) et le bouton `👤 Login` avec badge de Casquette métier ; (2) `Sidebar` (`240px` / `68px` Rail via `[`) présentant exactement les **8 entrées non numérotées** (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`) avec en pied le sélecteur de Pack Métier ; (3) `Zone Centrale` (`1fr`) ; et (4) `Colonne d'Aide Contextuelle ?` (`340px` à droite, qui se replie automatiquement par défaut sur les écrans `< 1440px` dès que `total >= 1` décision est en attente).

**Given** l'écran d'accueil **`Cockpit`** (`/`)
**When** le nombre total d'actions requises (`Ancrages Humains + Arbitrages + Revues + Alertes`) vaut `total == 0` **OU** `total >= 1`
**Then** :
1. Si `total == 0`, les 4 compteurs KPI (`0/0/0/0`) et la barre de filtres sont **automatiquement masqués** au profit d'une bannière sobre `✅ Aucune décision en attente` suivie de l'Accès Rapide à `Mon Assistant` et des 3 cartes d'orientation ;
2. Si `total >= 1`, les décisions courtes (**`Arbitrage Tie-Break`** à 2–3 options) se tranchent directement sur place en 1 clic dans le `Cockpit`, tandis que les actions lourdes (**`Ancrage Humain Violet`**, **`Briefing de Revue 4 blocs`**, **`Validation par Découpage`** et **`Challenge Amont What-If`**) affichent un résumé compact et un bouton **`Ouvrir l'atelier de revue →`** qui bascule vers la **Vue Fokus de Revue (`Mes Processus › Exécutions & Décisions › Run #ID`)** en acquérant automatiquement le verrou de présence Redis (`SET lock:step:<step_execution_id> <user_id> NX EX 900`, `AD-4`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`Vitest`) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 9.2: Parcours d'Accostage Progressif Jour 0 (`Accostage 1/6`), Protection Anti-*First-User Takeover* & Palier Progressif `1 Modèle → ≥ 2 Familles AD-10`

As a Administrateur Plateforme ou Premier Utilisateur au Jour 0 (`Karim UJ-9`, `Marc UJ-5`),
I want initialiser une instance vierge d'ORCIA sans risque de prise de contrôle concurrente (*First-User Takeover*), débloquer l'essai de `Mon Assistant` dès le 1er modèle LLM configuré puis les Gates Agentiques dès la 2e famille orthogonale, et suivre ma progression via le bandeau interactif `Accostage 1/6`,
So that l'installation initiale soit à la fois sécurisée cryptographiquement et praticable en moins de 5 minutes sans blocage bureaucratique (`Section 2`, `AD-10`, `AD-16`, `AD-19`).

**Acceptance Criteria:**

**Given** une base PostgreSQL 18 vierge (`COUNT(*) FROM users == 0`) lors du premier accès à `/welcome-setup`
**When** la création du premier compte `PLATFORM_ADMIN` est soumise
**Then** la transaction acquiert `LOCK TABLE users IN EXCLUSIVE MODE` (garantissant qu'un seul premier administrateur peut être créé même sous requêtes concurrentes) et, pour tout `ORCIA_ENV != "local"`, exige la validation du jeton d'amorçage **`ORCIA_BOOTSTRAP_TOKEN`** généré au démarrage (rejet `HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN` sinon).

**Given** l'**Assistant de Bienvenue en 3 étapes** et le bandeau de progression **`Accostage 1/6`** dans le `Cockpit`
**When** l'administrateur configure un **seul modèle LLM** (ex. `Ollama local` ou `OpenAI`) à l'étape 2
**Then** le système active immédiatement le **Mode Essai Rapide** (`Mon Assistant` et le `Cockpit` deviennent utilisables avec un badge ambre non bloquant `⚠️ 1 seule famille de modèles configurée — Ajoutez une 2e famille dans Configuration › Modèles IA pour activer les Gates Agentiques AD-10`), et déverrouille automatiquement les Gates Agentiques dès qu'une **2e famille de modèles distincte** est validée
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration sous concurrence (`testcontainers` PG18 vérifiant le `LOCK TABLE users`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 9.3: Recherche Fédérée & Contextuelle `⌘K` à 2 Vitesses (*Zero Layout Shift*, 3 Portées, 7 Familles & Deep-Linking Auto-Focus)

As a Utilisateur Métier, Architecte ou Tech Lead (`Hélène UJ-1`, `Antoine UJ-2`, `Yanis UJ-3`),
I want rechercher instantanément depuis la barre supérieure (`⌘K`) n'importe quel dossier, discussion, processus, livrable, source, terme du glossaire, agent ou fiche d'aide selon 3 portées (`📍 Cet écran`, `📦 Cet Espace`, `🌐 Tous mes Espaces`) avec un affichage en 2 vitesses sans aucun saut visuel (*Zero Layout Shift*) et une ouverture profonde au clic,
So that je retrouve n'importe quelle connaissance ou action en moins d'une seconde sans que la liste ne saute sous mon curseur ni que les coûts d'embeddings n'explosent à la frappe (`Principe A.2`, `AD-8`, `AD-19`, `AD-21`, Composant 17 `top-header-search-command`).

**Acceptance Criteria:**

**Given** le composant `@orcia/ui` **`top-header-search-command`** (`680px × max 480px`) ouvert via `⌘K` / `Ctrl+K` et l'endpoint `GET /api/v1/search` filtré par `PermissionGuard` (`AD-21`)
**When** l'utilisateur saisit une requête et choisit l'une des **3 pilules de portée** (`📍 Cet écran` | `📦 Cet Espace` par défaut | `🌐 Tous mes Espaces`)
**Then** :
1. **Vitesse 1 (`As-You-Type`, `< 30 ms`, `0 $` d'appel LLM)** : à chaque frappe (`debounce 80 ms`), une requête SQL unique (`UNION ALL` sur `PostgreSQL tsvector` + trigrammes `pg_trgm`) retourne les résultats exacts/préfixes groupés parmi les **7 familles** (`📁 Dossiers & 💬 Discussions`, `☍ Processus & ▶ Exécutions`, `📄 Livrables & Artefacts`, `🗄️ Sources & Extraits`, `📖 Glossaire & Règles Métier`, `🤖 Agents & Compétences`, `❓ Fiches d'Aide & Actions`) et **verrouille leur position en tête** de chaque catégorie ;
2. **Vitesse 2 (`Pause de frappe 450 ms`, uniquement si $\ge 3$ mots ou clic sur `✨ Recherche sémantique`)** : la recherche vectorielle `pgvector halfvec(1024)` HNSW + `RRF` (`AD-8`, cachée 5 min dans Redis par `(workspace_id, sha256(query_norm))`) ajoute ses trouvailles **exclusivement en bas** de chaque catégorie avec le badge `✨ Passage proche`, sans jamais déplacer la ligne actuellement sélectionnée au clavier (`↑`/`↓`).

**Given** un résultat sélectionné dans `top-header-search-command`
**When** l'utilisateur appuie sur `Entrée ↵` (ou `⌘+Entrée` / `Ctrl+Entrée`, ou clique sur le pied de liste `💬 Poser la question « ... » à Mon Assistant →`)
**Then** `Entrée ↵` exécute le **Deep-Linking + Auto-Focus** vers l'élément exact (avec surlignage temporaire Ambre/Cobalt `2 s`, ou ouverture directe de la Colonne `❓` sans quitter l'écran pour une fiche d'aide), `⌘+Entrée` ouvre l'aperçu dans le panneau latéral droit sans quitter l'écran courant, et le bouton de pied bascule vers `Mon Assistant` en pré-attachant les meilleurs extraits trouvés
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du moteur de recherche à 2 vitesses (`AD-17`, `AD-19`).

### Story 9.4: Menu Déroulant du Login (`UserAccountDropdown`), Modale « Paramètres de mon compte » (`UserSettingsModal` à 4 Onglets) & Double Persistance `0 ms` Anti-FOUC

As a Utilisateur Connecté (`Hélène UJ-1`, `Yanis UJ-3`, `Lucas UJ-7`),
I want ouvrir au clic sur mon login dans la `TopHeaderBar` un menu rapide (`UserAccountDropdown`) permettant de basculer en 1 clic le thème ou la langue et de me déconnecter, ou d'ouvrir la modale `⚙️ Paramètres de mon compte` (`UserSettingsModal` à 4 onglets) en fermant automatiquement le menu rapide,
So that je gère mes préférences d'affichage sans clignotement (`0 ms` anti-FOUC), ma sécurité (`Argon2id`/`TOTP`), mes jetons personnels `Passthrough` et mes clés IDE MCP dans un espace personnel clairement séparé de la configuration d'entreprise (`Principe A.3`, `AD-6`, `AD-19`, `AD-21`, Composant 18).

**Acceptance Criteria:**

**Given** le bouton **`👤 Login · [Casquette]`** à l'extrême droite de la `TopHeaderBar`
**When** l'utilisateur clique sur son login, actionne un switch rapide (`🌓 Apparence` ou `🌐 Langue`) ou clique sur **`🚪 Se déconnecter`**
**Then** :
1. Le menu déroulant **`UserAccountDropdown` (`280px`)** s'ouvre avec l'identité/rôle, le sélecteur de Casquette métier, les 2 bascules 1-clic (`☀️ Clair / 🌙 Sombre`, `FR / EN`), les entrées `⚙️ Paramètres de mon compte...` (`g u`) et `🔗 Mes accès aux sources...`, et le bouton **`🚪 Se déconnecter`** ;
2. Tout changement de thème ou de langue est écrit **instantanément (`0 ms`) dans `localStorage`** (`orcia_theme`, `orcia_locale`, lu dès `index.html` avant le premier rendu React pour garantir **zéro FOUC**) ET synchronisé en arrière-plan via `PATCH /api/v1/users/me/preferences` ;
3. Le clic sur **`🚪 Se déconnecter`** appelle `POST /api/v1/auth/logout`, révoque immédiatement le JWT et le Refresh Token `HttpOnly` dans Redis (`AD-6`), purge les caches sensibles du navigateur et redirige vers `/login`.

**Given** le menu `UserAccountDropdown` ouvert
**When** l'utilisateur clique sur **`⚙️ Paramètres de mon compte...`** (ou tape `g u`)
**Then** `UserAccountDropdown` **se ferme automatiquement** et la modale centrée **`UserSettingsModal` (`720px × max 600px`)** s'ouvre sur ses **4 onglets** :
1. **`🎨 Préférences & Affichage`** : Mode Clair/Sombre/Auto, Langue FR/EN, Casquette métier par défaut, ouverture auto de l'Aide `❓`, notifications `🔔`, et lien de renvoi `💬 Personnaliser le comportement de Mon Assistant →` (sans dupliquer la zone de saisie Couche 5) ;
2. **`👤 Profil & Sécurité`** : Identité, changement de mot de passe local `Argon2id`, `MFA TOTP`, révocation des sessions actives ;
3. **`🔗 Accès aux sources (Passthrough)`** : gestion par `<SecretField />` write-only des jetons personnels Git/Jira/Confluence/Notion chiffrés `AES-256-GCM` (`user_passthrough_credentials`, `AD-6`) avec bouton `🔌 Tester mon jeton` ;
4. **`💻 Clés IDE & MCP`** : génération et révocation instantanée (`< 10 ms` Redis) des jetons personnels scopés (`pat_mcp_*` hachés `SHA-256` en base, expiration obligatoire `30j/90j`, plafond `RPM`, sélection des Espaces autorisés et des capacités exposées : `Mon Assistant`, `Agents publiés de l'Espace`, `Recherche KB & Glossaire`, `Brouillons Staged`) pour `/api/v1/mcp`, avec sélecteur de cible (**Tout l'Espace `/api/v1/mcp/spaces/<ws_slug>`** ou **Un agent précis `/api/v1/mcp/agents/<agent_slug>`**) et extrait JSON prêt à copier pour **VS Code / Cursor / Claude Code / Antigravity / JetBrains** (`Principe M.4`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 9.5: Système d'Aide Contextuelle Hybride (`HelpArticle` dans `catalog_items` + `cas/<sha256>`), Colonne `❓` (`340px`), Menu `Aide` & Seeder Git-Seeded

As a Utilisateur Métier ou Administrateur (`Hélène UJ-1`, `Karim UJ-9`),
I want consulter à tout moment dans la Colonne `❓` (`340px`) ou dans le menu `Aide` une documentation contextuelle bilingue (`fr`/`en`) liée dynamiquement à l'écran actif, servie en `< 10 ms` depuis la base PostgreSQL (`catalog_items`), le stockage CAS S3 (`cas/<sha256>`) et Redis, et initialisée automatiquement au démarrage depuis Git,
So that chaque écran d'ORCIA soit auto-documenté en langage clair et que de nouvelles fiches d'aide puissent être rattachées à chaud ou restaurées (`⏪ Rollback`) sans créer de 19e table SQL ni redéployer l'application (`Principes D & D.4`, `AD-5`, `AD-14`, `AD-19`).

**Acceptance Criteria:**

**Given** la table existante `catalog_items` (`AD-5`), une migration Alembic ajoutant l'index GIN `idx_catalog_help_routes` sur `(metadata_jsonb->'bound_routes') WHERE item_type = 'HELP_ARTICLE'`, le stockage CAS `SeaweedFS` (`cas/<sha256>`) et `workspace_customization_overrides` (`AD-14`)
**When** le seeder de démarrage (`packages/orcia-core/bootstrap/seeder.py`) s'exécute
**Then** il charge par `INSERT ... ON CONFLICT DO UPDATE` idempotent toutes les fiches Markdown à frontmatter YAML déclaratif situées dans `docs/help/{fr,en}/` et `packages/orcia-pack-*/help/{fr,en}/` sous `item_type = "HELP_ARTICLE"`, stocke leur corps Markdown dans `cas/<sha256>`, et ne écrase jamais une version `@v(N+1)` plus récente publiée à chaud.

**Given** un utilisateur qui navigue vers une route TanStack Router (ex. `/mes-espaces/$id/sources`) avec la **Colonne d'Aide Contextuelle `❓` (`340px`)** ouverte ou qui consulte le menu **`Aide`**
**When** l'interface appelle `GET /api/v1/help/resolve?route=/mes-espaces/$id/sources&pack=orcia-pack-sdlc&lang=fr`
**Then** le service résout en `< 10 ms` (via le cache Redis `help:route:<route>:<pack>:<lang>`) la fiche active en appliquant la fusion à 4 niveaux (`Base -> Pack -> Team/Workspace -> User`, `AD-14`), affiche dans la Colonne `❓` le résumé *« À quoi sert cet écran ? »*, les accordéons *Pas-à-pas*, *Termes clés* et *Questions fréquentes*, ainsi que le bouton **`Poser une question à l'assistant sur cet écran →`**, et permet à un administrateur d'effectuer un **`⏪ Rollback` en 1 clic** vers `@v(N-1)`
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis + SeaweedFS) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

## Epic 10: `Mon Assistant` Tout-en-Un (Style EXEMPLE) — Personnalisation à 4 Niveaux (Mode A & Mode B), Routage à 3 Vitesses (`TTFT < 1,2 s`), Citations Déterministes (`[S1]/[G1]/[O1]`) & Dossiers Thématiques Collaboratifs (`📁 Dossiers`)

Permettre aux équipes métiers et techniques de disposer dans **`Mon Assistant`** d'un espace de travail conversationnel complet : personnalisable à 4 niveaux (`USER`, `WORKSPACE`, `TEAM`, `PLATFORM`) soit en **Mode A (Formulaire Rapide à 3 onglets)** soit en **Mode B (Studio Graphique `@xyflow/react`)** à l'intérieur des bornes inaltérables `🔒 AssistantHarness` (`AD-15`), garantissant un **`TTFT < 1,2 s`** grâce au cache Redis du prompt assemblé à 5 couches et au **Routage à 3 Vitesses (`⚡ Rapide`, `🔍 Agent & Outils MCP`, `🧠 Approfondi`)**, ancrant chaque affirmation par des **Citations Déterministes (`[S1]`, `[G1]`, `[O1]`)** résolues via `citation_map` SSE avec filtrage `READ_SOURCE` par lecteur (`AD-21`) et garde-fou anti-citation fantôme `< 5 ms`, et structurant le travail au long cours dans des **Dossiers Thématiques (`📁 Dossiers`)** dotés d'une continuité mémoire en Couche 5, d'un partage collaboratif à 3 niveaux (`🔒 Privé | 👥 Partagé | 📦 Espace`), d'un verrou de tour Redis léger (`SET NX EX 60`) et d'une identité `Passthrough` individuelle par message (`Principes B, H, K, K.4, K.5, K.6`).

### Story 10.1: Gouvernance & Personnalisation à 4 Niveaux de `Mon Assistant` (Bornes `🔒 AssistantHarness`, Mode A Formulaire Rapide à 3 Onglets & Mode B Studio Graphique)

As a Contributeur Métier, Chef d'Équipe ou Architecte (`Hélène UJ-1`, `Marc UJ-5`, `Antoine UJ-2`),
I want personnaliser le comportement de `Mon Assistant` selon mes droits à 4 niveaux (`USER`, `WORKSPACE`, `TEAM`, `PLATFORM`) soit via la modale simple `⚙ Réglages de l'assistant` à 3 onglets (**Mode A**), soit via l'éditeur graphique `@xyflow/react` (**Mode B** `☍ Personnaliser dans le Studio`), tout en garantissant que les bornes de sécurité `🔒 AssistantHarness` restent inaltérables,
So that chaque utilisateur et chaque équipe adapte le ton, les sources prioritaires et le raisonnement de son assistant sans jamais pouvoir contourner les règles de sécurité ou d'Ancrage Humain (`Principes B, H, K`, `AD-14`, `AD-15`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** le workflow système `orcia://system/workflows/assistant-agent` (5 nœuds orientés : `1. Routeur d'Intention`, `2. Query Planner & Expansion Ontologique`, `3. Fan-Out Parallèle`, `4. Tri Critique & Vérification d'Axiomes`, `5. Synthétiseur Adaptatif`) encadré par les bornes d'entrée/sortie Python **`🔒 AssistantHarness`** (`AD-15`)
**When** un utilisateur ouvre `Mon Assistant › ⚙ Réglages de l'assistant` (**Mode A**)
**Then** la modale affiche **3 onglets** adaptés à ses droits :
1. **`👤 Mes préférences (Couche 5 — USER)`** : ton/concision, format de réponse favori, Casquette métier par défaut et instructions personnelles permanentes ;
2. **`📦 Réglages de l'Espace (Couche 4 — WORKSPACE)`** (éditable par `TEAM_LEAD`, lecture seule sinon) : instructions métier de l'Espace, sources cochées par défaut, agents `@` recommandés, politique d'arbitrage et interrupteur **`🔌 Exposer l'Assistant de l'Espace en MCP (`/api/v1/mcp` — outil `assistant.ask`)`** (soumis à la Règle de l'Entonnoir `Principe G` si gelé par l'Équipe ou le Socle, avec bouton `📋 Copier la config MCP` — `Principe M.4`) ;
3. **`👁️ Assemblage complet (Lecture seule)`** : visualisation transparente des **5 couches de prompt actives** (`1. 🔒 Constitution`, `2. Pack Métier`, `3. Équipe`, `4. Espace`, `5. Utilisateur`).

**Given** un `TEAM_LEAD` ou `PLATFORM_ADMIN` qui clique sur **`☍ Personnaliser dans le Studio`** (**Mode B**)
**When** il modifie les sous-couches (`COUCHES · N`), ajoute un sous-agent ou ajuste le `Pré-prompt IA`, teste dans `▷ Tester` puis clique sur **`Enregistrer pour cet Espace / cette Équipe`** (ou **`↺ Réinitialiser à la configuration par défaut`**)
**Then** les bornes `🔒 AssistantHarness` (Entrée/Sortie Couche 1) sont verrouillées et impossibles à supprimer ou court-circuiter (`HTTP 422 ERR_IMMUTABLE_HARNESS_BOUNDARY` en cas de tentative via API), la personnalisation est enregistrée comme surcharge scopée (`TEAM` ou `WORKSPACE`) dans `workspace_customization_overrides` sans altérer le workflow socle, et le bouton `↺ Réinitialiser` restaure en 1 clic le comportement standard
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 10.2: Garantie de Latence (`TTFT < 1,2 s`), Cache Redis du Prompt Assemblé & Routage Conversationnel à 3 Vitesses (`⚡ Rapide`, `🔍 Agent & Outils`, `🧠 Approfondi`)

As a Utilisateur de `Mon Assistant` (`Hélène UJ-1`, `Yanis UJ-3`, `Lucas UJ-7`),
I want que `Mon Assistant` affiche le premier mot de sa réponse en moins de `1,2 seconde` (`TTFT < 1,2 s`) grâce au cache Redis du prompt assemblé et à l'exécution déterministe `< 80 ms` des nœuds 1 à 4, et pouvoir basculer entre 3 vitesses d'exécution (`⚡ Rapide`, `🔍 Agent & Outils MCP`, `🧠 Approfondi`),
So that la conversation quotidienne soit aussi fluide qu'un chat instantané tout en permettant de mobiliser des outils MCP ou un audit multi-étapes lorsque la question l'exige (`Principe K.4`, `AD-8`, `AD-15`, `AD-19`, `NFR-PERF-1`).

**Acceptance Criteria:**

**Given** un utilisateur qui envoie un message dans `Mon Assistant`
**When** le pipeline d'exécution démarre en **`⚡ Vitesse 1 (Rapide / Directe — défaut)`**
**Then** :
1. Le prompt système fusionné des 5 couches est lu en **`< 5 ms`** depuis le cache Redis (`assistant:prompt:<workspace_id>:<user_id>:<hat>`, `ttl=300s`, invalidé automatiquement sur événement Outbox `SettingsChanged`, modification de surcharge ou promotion au Glossaire) ;
2. Les nœuds 1 à 4 s'exécutent en Python/SQL déterministe en **`< 80 ms` avec `0` appel LLM intermédiaire**, via une seule requête SQL parallèle (`UNION ALL` combinant `pgvector` HNSW + `tsvector` RRF sur les sources cochées et le Glossaire actif) ;
3. Un **seul appel LLM** est déclenché au nœud 5 en **streaming SSE direct** (`text/event-stream`), délivrant le premier token en **`TTFT < 1,2 s`** (`NFR-PERF-1`).

**Given** la pilule de vitesse **`⚡ Standard ⌄ / 🧠 Approfondi`** dans la barre de saisie de `Mon Assistant` et la détection d'intention du Nœud 1
**When** l'utilisateur invoque `@Agent` / `/Compétence` (**`🔍 Vitesse 2`**) ou sélectionne **`🧠 Approfondi`** (**`🧠 Vitesse 3`**)
**Then** `Vitesse 2` affiche un indicateur d'étape temps réel (`🔍 Interrogation de Jira...`) pendant l'appel `ConnectorInvoker` (`TTFT < 2,5 s`), tandis que `Vitesse 3` active la planification LLM intermédiaire et la vérification multi-lentilles (`AD-10`) avec barre de progression étape par étape
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis mesurant le cache hit `< 5 ms` et l'invalidation Outbox) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 10.3: Citation Déterministe & Vérification des Sources (`[S1]`, `[G1]`, `[O1]`), Filtrage `READ_SOURCE` par Lecteur & Garde-Fou Anti-Citation Fantôme

As a Utilisateur Métier, Architecte ou Auditeur (`Hélène UJ-1`, `Antoine UJ-2`, `Sophie UJ-6`),
I want que chaque réponse de `Mon Assistant` s'appuie sur une Table de Preuves Numérotées (`[S1]`, `[G1]`, `[O1]`), affiche des pastilles de citation cliquables ouvrant l'extrait exact surligné (tout en masquant l'extrait si un co-lecteur n'a pas le droit `READ_SOURCE`), et neutralise automatiquement toute citation inventée,
So that aucune URI ni aucun numéro de ligne ne puisse être halluciné et qu'aucun partage de discussion ne provoque de fuite documentaire (`Principe K.5`, `AD-5`, `AD-8`, `AD-15`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** les extraits récupérés en `< 60 ms` aux nœuds 2–4 (avec métadonnées `source_uri`, `title`, `section_or_symbol`, `page_or_lines`, `version_sha256`, `authority_role: REFERENCE | ACTIVE` et `freshness_status: FRESH | STALE_WARNING`)
**When** le `AssistantHarness` assemble le contexte du nœud 5 et ouvre le flux SSE
**Then** :
1. Il injecte une **Table de Preuves Numérotées** à identifiants courts (`[S1..Sn]` Sources RAG où `RÉFÉRENCE` prime sur `ACTIF`, `[G1..Gn]` Glossaire/Axiomes, `[O1..On]` Outils MCP) et émet dès `t = 80 ms` l'événement SSE `citation_map` ;
2. Lorsqu'un utilisateur consulte la discussion, l'API filtre dynamiquement chaque entrée de `citation_map` via `PermissionGuard` (`AD-21`) : si le lecteur ne possède pas `READ_SOURCE` sur la source sous-jacente, le `snippet` est purgé côté serveur et la pastille s'affiche en **`[S1 · 🔒 Source restreinte — Demander l'accès]`** ;
3. En post-stream (`< 5 ms`), le vérificateur déterministe contrôle que chaque balise `[S1]`/`[G1]`/`[O1]` produite appartient à la `citation_map` et remplace toute balise hors bornes par un badge d'alerte **`[Citation non vérifiée]`** tracé dans `audit_ledger`.

**Given** une réponse contenant des pastilles `[S1]`, `[G1]`, `[O1]` ou une Carte Artefact dans `Mon Assistant`
**When** un utilisateur habilité survole ou clique sur une pastille, déplie le bandeau **`📚 N sources citées`** ou clique sur **`📤 Publier vers une source...` / `📌 Officialiser dans le Coffre (@v1)`**
**Then** un Popover affiche le titre, le badge **`📚 RÉFÉRENCE`** / **`🛠️ ACTIF`** (ou **`⚠️ STALE_WARNING`**), la section/lignes exactes, le passage surligné et le bouton **`Ouvrir le document complet →`**, tandis que toute action d'officialisation `@v1` ou d'écriture vers le SI externe (`git://`, `confluence://`, `jira://`) est matériellement bloquée en écriture directe (`HTTP 422 ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE`, **Verrou V5 `AD-15`**) et déclenche obligatoirement le passage par la **Gate de Validation & Publication du Processus**
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 vérifiant le masquage `READ_SOURCE`, le garde-fou anti-citation fantôme et le Verrou V5) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 10.4: Dossiers Thématiques (`📁 Dossiers`), Continuité Mémoire Couche 5, Partage Collaboratif (`🔒 Privé | 👥 Partagé | 📦 Espace`) & Verrou de Tour Redis

As a Membre d'Équipe ou Chef d'Équipe (`Hélène UJ-1`, `Yanis UJ-3`, `Marc UJ-5`),
I want organiser mes échanges dans `Mon Assistant` au sein de `📁 Dossiers` thématiques dotés de notes épinglées, d'une mémoire partagée entre discussions du même dossier et d'un bouton de lancement de Processus en 1 clic, et pouvoir partager un dossier ou une discussion avec mes collègues de l'Espace en `👁️ Lecture seule` ou `✍️ Co-contributeur` sous identité `Passthrough` individuelle,
So that nous ne repartions jamais de zéro d'une discussion à l'autre et puissions co-construire un cadrage à plusieurs sans conflit d'écriture ni usurpation d'identité (`Principe K.6`, `AD-4`, `AD-6`, `AD-15`, `AD-19`, `AD-21`, Composant 15).

**Acceptance Criteria:**

**Given** l'en-tête sobre de `Mon Assistant` structuré en **3 onglets** (`💬 Discussion active` avec pilule `📁 Dossier ⌄` et bouton `📌 Notes du dossier`, `📁 Dossiers (N)`, `🕘 Historique & Recherche`)
**When** l'utilisateur crée ou sélectionne un `📁 Dossier` (ex. `📁 Refonte Tunnel Checkout`), épingle des décisions dans `📌 Notes du dossier` et ouvre une nouvelle discussion dans ce dossier
**Then** le `AssistantHarness` injecte automatiquement en **Couche 5 (`AD-15`)** les notes épinglées, pièces jointes/livrables de travail et résumés consolidés des discussions précédentes du dossier, et le bouton **`☍ Lancer un Processus à partir de ce dossier →`** pré-remplit les paramètres d'entrée (`Contrat du workflow`) d'un processus (notamment le **Workflow Pilote Semaine 1 `orcia://pack-sdlc/workflows/ticket-to-tech-spec`**) avec la synthèse du dossier.

**Given** un propriétaire de `📁 Dossier` ou de discussion qui clique sur **`👥 Partager`**
**When** il choisit l'un des **3 niveaux de visibilité** strictement confinés aux membres de l'Espace courant (`🔒 Privé` par défaut, `👥 Partagé avec des collègues choisis` en `👁️ Lecture seule` ou `✍️ Co-contributeur`, ou `📦 Ouvert à tout l'Espace`)
**Then** :
1. Si la discussion cite des sources restreintes, la modale affiche un avertissement préventif indiquant que leurs extraits seront masqués (`🔒 Source restreinte`) pour les collègues non habilités ;
2. Lorsqu'un **Co-contributeur (`✍️`)** envoie un message, le moteur acquiert un **verrou de tour Redis léger** (`SET lock:thread:<thread_id> <user_id> NX EX 60`), diffuse en temps réel via SSE aux pairs présents l'indicateur `✍️ {Prénom} interroge l'assistant...` puis les tokens générés, et exécute tous les connecteurs externes et outils MCP avec **l'identité `Passthrough` personnelle de l'auteur du message** (`AD-6`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis vérifiant le verrou de tour, l'isolation `Passthrough` et le confinement à l'Espace) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

## Epic 11: Gouvernance Métier de l'Espace (`Mes Espaces` à 5 Onglets, Chaîne Causale `DIRECTIVE ➔ NORME ➔ MÉCANISME`, Compilateur `Text-to-Starlark` Palier 1b `< 2 ms`, Cycle de Vie du Glossaire `✨ À valider`, Routage des Artefacts à 4 Niveaux), Exposition & Banc de Test MCP/A2A `🔌` & Atelier `orcia-pack-builder`

Permettre aux Responsables d'Espace (`TEAM_LEAD`), Stewards Métier (`ONTOLOGY_STEWARD_L3`) et Concepteurs de Packs de piloter leurs espaces dans **`Mes Espaces` structuré en 5 sous-onglets** (`Vue d'ensemble`, `Documents & Sources`, `Livrables & Artefacts`, `Glossaire & Règles métier`, `Membres & Équipe`), de gouverner la localisation et la publication des livrables produits selon une **Cascade à 4 Niveaux** (avec confinement `local://`, bail `ResourceLeasePort` `AD-4`, alias `orcia://workspaces/<ws>/artifacts/<type>/<slug>@v<N>`, **Registre des Exceptions Acquittées `workspace_exception_waivers` `Verrou V1` gouverné par la Chaîne Causale ADN `DIRECTIVE ➔ NORME ➔ MÉCANISME` `AD-7`** et **Rebase d'Édition Externe `ExternalEditRebaser` marquant les sections retouchées dans Git/Confluence en `🔒 HUMAN_AMENDED_EXTERNAL` `Verrou V2`**), de compiler au Design-Time des règles métiers en français vers des scripts **`Starlark` Palier 1b (`starlark-pyo3` + `google-re2` $O(n)$, `< 2 ms`, `0 $` LLM au Run-Time, auto-testés sur cas `PASS`/`FAIL`, `AD-9`)**, d'alimenter leur **Glossaire métier (`✨ À valider`, plafonné à `max 15` FIFO et promu *In-Flow* dans le Briefing 4 blocs `Verrou V4`)** grâce à une extraction en 2 passes à coût maîtrisé (`0 $` déterministe sur `git push` + batch `Top-15` uniquement sur MR/PR/Sync/Gate), sélection multiple et simulation *What-If* (`AD-7`), de déclarer et tester à chaud des **Services/Serveurs MCP et `@Agents Distants (MCP / A2A)`** via un **Banc de Test en 4 Étapes (`🔌`)** ET d'**exposer en MCP Gouverné (`/api/v1/mcp`) les Agents Locaux de la Bibliothèque ainsi que `Mon Assistant`** sous les 7 verrous matériels de sécurité (incluant le **Confinement d'Orthogonalité par `SovereigntyTier C0..C3` `Verrou V3`**), et de concevoir/faire évoluer/documenter des Packs Métier via le pack système **`packages/orcia-pack-builder`** (`Principes D.4, I, J, L, M.1, M.2, M.4`, `Sections 3 & 4`).

### Story 11.1: Refonte de `Mes Espaces` en 5 Sous-Onglets, Cascade de Localisation des Artefacts Produits à 4 Niveaux, `ExternalEditRebaser` (`Verrou V2`), `workspace_exception_waivers` Gouverné par Chaîne ADN (`Verrou V1`) & Workflow Pilote `sdlc/ticket-to-tech-spec`

As a Responsable d'Espace, Product Manager ou Tech Lead (`Marc UJ-5`, `Hélène UJ-1`, `Yanis UJ-3`),
I want gérer mon Espace à travers 5 sous-onglets clairs (`Vue d'ensemble`, `Documents & Sources`, `Livrables & Artefacts`, `Glossaire & Règles métier`, `Membres & Équipe`), qualifier mes sources en `Lecture seule` vs `Lecture & Écriture (Cible)`, acquitter une fois pour toutes un écart documentaire local connu tant que son `sha256` ne change pas tout en protégeant les Directives d'Entreprise inviolables (`Verrou V1` + `AD-7`), protéger en `🔒 HUMAN_AMENDED_EXTERNAL` toute section d'artefact modifiée dans Git/Confluence après publication (`Verrou V2`), et exécuter le Workflow Pilote Semaine 1 `sdlc/ticket-to-tech-spec`,
So that nous sachions toujours exactement où est stocké chaque livrable produit par ORCIA, sans fatigue de validation sur les écarts connus ni écrasement des retouches humaines faites dans l'IDE (`Principes I & J`, `AD-3`, `AD-4`, `AD-5`, `AD-7`, `AD-11`, `AD-14`, `AD-19`, `AD-20`, `AD-21`).

**Acceptance Criteria:**

**Given** l'écran **`Mes Espaces › [Espace actif]`** structuré en **5 sous-onglets** et le registre **`workspace_exception_waivers`** (`Verrou V1`, `AD-11`) couplé à la CTE récursive `dna_chain` (`DIRECTIVE ➔ NORME ➔ MÉCANISME`, `AD-7`)
**When** le Responsable d'Espace configure l'onglet **`2. Documents & Sources`**, arbitre un écart `[STALE_WARNING]` / `ONTOLOGY_CONFLICT` avec la case **`[✓] Acquitter cet écart tant que la source ne change pas`**, ou configure le bloc **« Sortie & Localisation »** d'une étape dans `Mes Processus › Studio`
**Then** :
1. Chaque source de l'Espace est qualifiée par rôle (**`📚 RÉFÉRENCE`** vs **`🛠️ ACTIF`**) et par mode d'accès (**`👁️ Lecture seule`** vs **`✍️ Lecture & Écriture (Cible d'artefacts)`**), avec un sélecteur **`📌 Destination par défaut des livrables de l'Espace`** (`Coffre interne ORCIA S3 CAS` par défaut ou une source cible externe) ;
2. Tout écart acquitté sur une `NORME` locale (`3_WORKSPACE` / `3_TEAM`) est enregistré dans `workspace_exception_waivers` sous `(workspace_id, source_uri, source_sha256, conflict_rule_id, expires_at)` et ne bloque plus le passage automatique `risk_or_exception_based` (`AD-11`) tant que `source_sha256` est inchangé ; en revanche, si `dna_chain` remonte jusqu'à une `DIRECTIVE` de niveau `1_ENTERPRISE` marquée `inviolable: true`, l'acquittement local par un simple `TEAM_LEAD` est rejeté (`HTTP 403 ERR_ENTERPRISE_DIRECTIVE_WAIVER_FORBIDDEN` — badge `🔒 Directive Organisationnelle`) et requiert `PLATFORM_ADMIN` ou `SECOPS` ;
3. Lors de la production d'un artefact (notamment par le **Workflow Pilote Semaine 1 `orcia://pack-sdlc/workflows/ticket-to-tech-spec`** en 3 étapes : *1. Ingestion Jira + 1 Ancrage Humain + Traversée Graphe Tripartite $\rightarrow$ 2. Spécification Technique & Impact AST Git avec Gate Orthogonale Confinée par `SovereigntyTier` (`Verrou V3`) $\rightarrow$ 3. Briefing 4 blocs & Publication Staged*), le moteur résout sa destination selon la **cascade à 4 niveaux**.

**Given** un artefact validé à une Gate et publié vers une destination cible (`git://` ou `confluence://`), puis modifié directement par un développeur dans Git ou Confluence hors d'ORCIA (`@v(N+1)` externe)
**When** un Run ou Replay ultérieur résout cet artefact et que l'utilisateur consulte le sous-onglet **`3. Livrables & Artefacts`**
**Then** :
1. Toute écriture vers `local://` est confinée à la racine autorisée de l'Espace (`os.path.realpath`, rejet `HTTP 403 ERR_PATH_TRAVERSAL_DENIED` sur tout `../`), toute publication vers une source partagée acquiert un bail **`ResourceLeasePort`** (`AD-4`), et chaque version validée reçoit une empreinte immuable `cas/<sha256>` dans `SeaweedFS` ainsi qu'une URI canonique `orcia://workspaces/<ws_slug>/artifacts/<type>/<slug>@v<N>` (`AD-5`) ;
2. **`ExternalEditRebaser` (`Verrou V2`, `AD-3` / `AD-5`)** détecte la divergence `SHA-256` avec la cible externe, exécute un diff par section, importe la version externe sans jamais l'écraser, marque automatiquement les sections retouchées par l'humain en **`chunk_approvals.status = HUMAN_AMENDED_EXTERNAL`** (inviolables par l'agent aval) et marque `[SUPERSEDED_BY_HUMAN_COMMIT]` les hypothèses contradictoires antérieures dans `step_memlog_jsonb`
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + SeaweedFS) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 11.2: Chaîne Causale ADN (`DIRECTIVE ➔ NORME ➔ MÉCANISME`), Compilateur `Text-to-Starlark` Palier 1b (`starlark-pyo3` + `google-re2` $O(n)$ `< 2 ms`), Cycle de Vie du Glossaire (`✨ À valider <= 15 FIFO`) & Promotion *In-Flow* (`Verrou V4`)

As a Responsable Métier / Steward Ontologique, Architecte ou Chef d'Équipe (`Hélène UJ-1`, `Antoine UJ-2`, `Marc UJ-5`),
I want structurer mes règles métiers selon la chaîne causale `🛡️ DIRECTIVE ➔ 📏 NORME ➔ ⚙️ MÉCANISME`, compiler en 1 clic une Norme exprimée en français en un mécanisme de Gate déterministe `Starlark` auto-testé (`PASS`/`FAIL` en `< 5 ms` au Design-Time via `starlark-pyo3` + `google-re2` $O(n)$, puis `0 $` LLM et `< 2 ms` au Run-Time), et alimenter le Glossaire via une extraction en 2 passes (`0 $` sur `git push` + batch `Top-15` sur MR/PR/Sync/Gate) et la promotion *In-Flow* dans le Briefing 4 blocs (`Verrou V4`),
So that chaque règle de gouvernance soit explicable de bout en bout (du *Pourquoi* stratégique au *Comment* exécutable) et vérifiée en moins de `2 ms` sans coût LLM au Run-Time ni corvée d'administration (`Principe L`, `AD-7`, `AD-8`, `AD-9`, `AD-11`, `AD-19`, Composant 16).

**Acceptance Criteria:**

**Given** les tables `ontology_concepts`, `ontology_axioms` et `ontology_relations` enrichies par `dna_stereotype` (`CONCEPT | DIRECTIVE | NORM | MECHANISM`), `mechanism_payload_jsonb` et les prédicats `OPERATIONALIZES_DIRECTIVE` / `IMPLEMENTS_NORM` (`AD-7`), ainsi que l'adaptateur isolé `StarlarkMechanismSandbox` (`packages/orcia-core/src/orcia_core/gates/_internal/starlark_sandbox.py` utilisant `starlark-pyo3` `max_steps = 100 000` et **`google-re2` `max_mem = 8 MB`** en temps linéaire $O(n)$, `AD-9` Palier 1b)
**When** un utilisateur clique sur **`⚡ Générer le Mécanisme de Gate (Starlark)`** depuis une `Norme` du Glossaire (**Parcours A**) ou saisit une règle en français dans l'éditeur assisté de `Mes Processus › Studio` (**Parcours B**)
**Then** :
1. `TextToStarlarkCompilerService.compile_from_natural_language()` génère en 1 appel LLM un `GeneratedStarlarkMechanism` (`starlark_code`, `passing_test_payload`, `failing_test_payload`, `explanation_fr`), valide d'abord les deux payloads de test contre le `target_json_schema`, puis exécute immédiatement `StarlarkMechanismSandbox.evaluate_script()` en `< 5 ms` pour prouver que `passing_test_payload` rend `PASS` et `failing_test_payload` rend `FAIL` sur `rule_id` (avec 1 boucle automatique de *Self-Correction* en cas d'erreur de syntaxe Starlark, de regex non compatible RE2 ou d'assertion) ;
2. L'UI affiche le badge **`✓ Vérifié sur cas de test (PASS/FAIL en < 5 ms)`**, l'explication en français et le bouton **`✍️ Signer & Activer la Gate`** qui scelle le `sha256` dans `mechanism_payload_jsonb` ;
3. Au Run-Time, le mécanisme s'exécute en **`< 2 ms` et `0 token` LLM** (avec `orcia_sys.emit_effect` confiné aux seules **Actions Staged** `step_executions.draft_artifact_jsonb`), et le `CognitiveReviewBriefing` affiche sur 1 ligne le fil d'Ariane causal complet : `🛡️ [DIRECTIVE N1] ➔ 📏 [NORME N2/N3] ➔ ⚙️ Vérifié par : <script>.star`.

**Given** l'indexation d'une source via `domain_events_outbox`, un `git push` / une ouverture de Merge Request ou le passage d'une Gate Humaine
**When** le service `OntologyExtractor` (`packages/orcia-core/ontology`) analyse les contenus et que le valideur consulte le Briefing 4 blocs ou `Mes Espaces › Glossaire & Règles métier › ✨ À valider (N <= 15)`
**Then** :
1. **Passe 1 déterministe (`0 $` d'appel LLM, seule autorisée sur un simple `git push`)** : extrait les candidats via `tree-sitter` et `Docling`, les déduplique contre `ontology_concepts` et filtre les empreintes déjà écartées (`REJECTED_CANDIDATE`) ;
2. **Passe 2 de consolidation LLM bornée (1 seul appel batch `simple €` sur le `Top-15` par source, déclenchée uniquement sur MR/PR, synchronisation manuelle ou passage de Gate)** : rédige la définition concise, détecte tout **`⚠️ ONTOLOGY_CONFLICT`**, plafonne la file **`✨ À valider (N)`** à **maximum `15` candidats actifs par Espace** (avec purge TTL à 30 jours des entrées `4_RUN_EPHEMERAL` non promues), et affiche les **`Top-3` termes L4 ($\ge 0.85$) sous forme de cases pré-cochées (`[✓] Promouvoir au Glossaire de l'Espace`) directement dans le Briefing de Revue en 4 blocs (`Verrou V4`)** ;
3. Toute promotion ou modification déclenche l'aperçu `ImpactSimulatorService` (*What-If*, `AD-7`) en cas de conflit, passe les termes à `ACTIVE` en `3_WORKSPACE` et invalide immédiatement le Cache Redis du prompt de `Mon Assistant`
**And** `lint-imports` passe à `0` violation (garantissant qu'aucun module de `orcia_kernel` ou `orcia_core.*.domain` n'importe `starlark` ou `re2`) et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 11.3: Déclaration Guidée des Services / Serveurs MCP & `@Agents Distants (MCP / A2A)`, Exposition MCP Gouvernée des Agents de la Bibliothèque & de `Mon Assistant` (`/api/v1/mcp`) et Banc de Test à Chaud en 4 Étapes (`🔌`)

As a Administrateur Plateforme, Chef d'Équipe ou Concepteur d'Agents (`Karim UJ-9`, `Marc UJ-5`, `Yanis UJ-3`, `Lucas UJ-7`),
I want déclarer un serveur MCP distant ou un `@Agent Distant (MCP / A2A)` en les validant via le Banc de Test & Découverte Automatique à Chaud en 4 étapes (`🔌`), ET pouvoir exposer en 1 clic n'importe quel Agent Local de ma bibliothèque (`catalog_items`) ou `Mon Assistant` (`orcia://system/workflows/assistant-agent`) sur le Serveur MCP Gouverné d'ORCIA (`/api/v1/mcp`),
So that nous consommions des outils externes sans jamais activer un service défaillant en production ET que nos développeurs/systèmes externes puissent invoquer nos agents et notre assistant depuis leurs IDE (VS Code, Cursor, Claude Code, Antigravity) sous nos 7 verrous matériels de sécurité (`Principes M.1, M.2 & M.4`, `AD-3`, `AD-5`, `AD-6`, `AD-12`, `AD-15`, `AD-19`, `AD-21`, Composant 19 `remote-service-test-bench`).

**Acceptance Criteria:**

**Given** la modale **`+ Déclarer un service / serveur MCP`** (`Configuration › Connecteurs` ou `Mes Agents › Outils`) et la modale **`+ Nouvel agent › 🌐 Agent Distant (MCP / A2A)`** (`Mes Agents`)
**When** l'utilisateur renseigne le protocole (`MCP Streamable HTTP / SSE`, `OpenAPI 3.1 REST`, `A2A / Agent Distant` ou `WASM Sandbox`), l'URL, l'identité d'exécution (`Passthrough` `AD-6` par défaut ou `<SecretField />` write-only `AD-21`), la classification (`C0–C2` vs `C3`) et clique sur **`🔌 Tester la connexion & Découvrir les capacités`** (`POST /api/v1/settings/connectors/test-and-discover`)
**Then** le composant `@orcia/ui` **`remote-service-test-bench`** exécute et affiche en temps réel les **4 étapes de vérification** :
1. **`1. Réseau, TLS & Anti-SSRF`** : validation DNS/TLS et blocage de toute IP privée/loopback/metadata cloud non explicitement autorisée ;
2. **`2. Authentification`** : validation du secret via `SecretProviderPort` ; si le service est configuré en mode **`Passthrough` (`AD-6`)** et que l'administrateur n'a pas lié son propre jeton personnel, l'étape affiche **`🟠 En attente de jeton utilisateur (Passthrough)`** (avec bouton optionnel *Tester avec mon jeton personnel*), **sans bloquer le bouton `Activer`** dès lors que les étapes 1 et 3 sont vertes ;
3. **`3. Découverte Automatique du Contrat`** : appel `tools/list` / `resources/list` ou lecture de l'`Agent Card` / `openapi.json`, pré-remplissant la liste des outils avec qualification automatique **`👁️ Lecture seule`** vs **`✍️ Écriture -> Action Staged obligatoire (AD-3)`** ;
4. **`4. 💬 Essai Rapide à Chaud (Dry-Run)`** : exécution d'un appel de test en lecture seule borné par un **timeout strict de `5 s`**, une **taille maximale de réponse de `1 Mo`** et tracé dans `audit_ledger` sous `actor_type: ADMIN_CONNECTION_TEST` (`run_id: null`), affichant le JSON retourné et les métriques FinOps détectées dans `_meta.usage` / `X-Orcia-Usage`.

**Given** l'écran **`🤖 Mes Agents`** (carte épinglée `🤖 Assistant de l'Espace` et cartes/modale `+ Nouvel agent / Modifier` des `🤖 Agents Locaux` de `catalog_items`) et le service `GovernedMcpServerService` (`packages/orcia-core/src/orcia_core/orchestration/mcp_server.py`)
**When** un Responsable d'Espace (`TEAM_LEAD`) ou Concepteur habilité active l'interrupteur **`🔌 Exposer en MCP`** sur un Agent Local (en choisissant le régime `👁️ Consultation & Analyse` ou `✍️ Co-pilotage Gouverné Staged`) ou sur `🤖 Assistant de l'Espace`, puis qu'un client IDE externe appelle `/api/v1/mcp` (`/api/v1/mcp/spaces/{ws_slug}` ou `/api/v1/mcp/agents/{agent_slug}`)
**Then** :
1. **`tools/list` & `prompts/list` dynamiques filtrés par `PermissionGuard` (`AD-21`)** : le serveur MCP expose dynamiquement **`assistant.ask`**, **`agent.invoke`**, **`agent.list_exposed`** ainsi qu'un outil dédié **`agent.<agent_slug>`** pour chaque agent de l'Espace marqué `mcp_exposed: true` sur lequel l'appelant détient le verbe **`execute`** ;
2. **Application stricte des 7 Verrous Matériels de Sécurité (`Principe M.4`)** :
   - **Authentification Scopée & Révocation `< 10 ms`** : validation du jeton `pat_mcp_*` (haché `SHA-256`, borné aux `workspace_ids` et capacités autorisées) ou OAuth 2.1 PKCE ;
   - **Identité `Passthrough` obligatoire (`AD-6`)** : exécution de l'agent/assistant et de ses connecteurs (`git://`, `jira://`, `confluence://`) avec les jetons personnels `user_passthrough_credentials` de l'appelant et déclenchement du *Permission Broker* en cas de `401/403` ;
   - **Protection de la Propriété Intellectuelle (`execute` $\neq$ `read`, `AD-21`)** : un appelant ayant `execute` sans `read` (`READ_SOURCE`) peut invoquer l'agent via MCP mais ne peut jamais lire son `system_prompt` (Couches 1 à 4), ses `SecretRef` (`NFR-SEC-4`) ni les extraits `[S1]` de sources restreintes (`[S1 · 🔒 Source restreinte]`) ;
   - **Traversée de `🔒 AssistantHarness` & `PiiReversibleScrubber` (`AD-15`, `Story 4.2`)** : confinement de l'input MCP en Couche 5 délimitée, scan PII/Secrets avant tout appel LLM Cloud et vérification anti-citation fantôme `< 5 ms` ;
   - **Sanctuarisation des Ancrages Humains (`AD-3`) & Mode Observateur (`AD-4`)** : rejet `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED` sur toute section `human_authored_required: true` et rejet `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` pour tout `READ_ONLY_OBSERVER` ;
   - **Mutations Externes en `Action Staged` uniquement (`AD-4`, `AD-5`, `AD-11`)** : aucune écriture directe vers Jira/Git/Confluence hors brouillon `step_executions.draft_artifact_jsonb` soumis à Gate ;
   - **Quotas FinOps (`_meta.usage`), Rate-Limiting Redis & Audit Immuable (`AD-12`, `Story 6.1`)** : retour de `CallToolResult._meta.usage`, imputation sur le quota de l'Espace, badge **`💻 Appelé via MCP (IDE)`** dans l'historique et `📊 FinOps`, et écriture immuable dans `audit_ledger` (`actor_type: MCP_IDE_CLIENT`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis + serveur/client MCP) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 11.4: Pack Métier Système `packages/orcia-pack-builder` — Création, Évolution *What-If*, Certification de Règles `Starlark` (Palier 1b `< 2 ms`) & d'Outils en Sandbox (Palier 2) et Promotion depuis un Espace (Processus 1 à 4)

As a Architecte Métier, Tech Lead ou Ingénieur Plateforme (`Antoine UJ-2`, `Yanis UJ-3`, `Karim UJ-9`),
I want disposer du pack système pré-installé `packages/orcia-pack-builder` embarquant 4 agents spécialisés et 4 processus gouvernés pour créer un nouveau Pack Métier (`packages/orcia-pack-{pack_slug}/`), simuler l'impact d'une évolution (*What-If*), compiler et certifier ses règles de validation métiers en `Starlark` Palier 1b (`< 2 ms` via `starlark-pyo3` + `google-re2` $O(n)$) ou ses outils lourds en Sandbox Palier 2, et promouvoir une brique d'un Espace vers un Pack partagé,
So that ORCIA puisse s'étendre à de nouveaux métiers (Finance, Juridique, RH, Retail, Ops) sans jamais compiler d'outils tiers en WASI et avec la même rigueur d'isolation `AD-20` et `AD-9` que le pack SDLC (`Sections 3 & 4.1..4.3`, `AD-7`, `AD-9`, `AD-19`, `AD-20`).

**Acceptance Criteria:**

**Given** le package Python `packages/orcia-pack-builder` enregistré via les `entry_points` `orcia.packs` (`AD-20`) et activable dans un Espace « Atelier »
**When** un concepteur lance l'un des **4 premiers processus gouvernés** du pack (accompagnés par `@Architecte-Métier-Pack`, `@Ingénieur-Prompt-et-Workflow`, `@Certificateur-Sécurité-et-Sandbox` et `@Rédacteur-Documentation-Orcia`)
**Then** :
1. **Processus 1 (`create-business-pack`)** : exige un `✍️ Ancrage Humain Violet` d'intention métier, structure la chaîne causale `DIRECTIVE ➔ NORME ➔ MÉCANISME` du glossaire socle (`AD-7`), les profils humains, les agents et les processus, génère l'arborescence complète dans **`packages/orcia-pack-{pack_slug}/`** (avec `0` écriture dans `packages/orcia-kernel` ou `packages/orcia-core`, vérifié par `lint-imports`), et valide le manifeste `pack.yaml` en Sandbox Palier 1a (`< 5 s`) ainsi que les règles métiers `.star` en Palier 1b (`starlark-pyo3` + `google-re2` `< 2 ms`) avant publication ;
2. **Processus 2 (`evolve-business-pack`)** : exécute `ImpactSimulatorService` (*What-If*, `AD-7`) pour identifier tous les Espaces et Processus impactés par la nouvelle version `@vX.Y.Z` sans jamais altérer les `run-lock.json` des runs en cours ;
3. **Processus 3 (`certify-pack-tool`)** : certifie en priorité les règles métiers déterministes via `StarlarkMechanismSandbox` (**Palier 1b `starlark-pyo3` + `google-re2` $O(n)$ `< 2 ms`** sur vecteurs `passing_test_payload` / `failing_test_payload`), ou exécute les tests TDD et l'audit de sécurité d'un outil lourd dans **`sandbox-runner` Palier 2** (`TIER_2_CONTAINER`, `gVisor/Podman rootless --network=none < 60 s`, `AD-9`) ;
4. **Processus 4 (`export-from-workspace-to-pack`)** : nettoie toute référence ou secret spécifique à un Espace et promeut un agent, un processus, une norme ou un mécanisme Starlark éprouvé vers une nouvelle révision du Pack Métier
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`) et d'intégration (`testcontainers` PG18 + SeaweedFS) couvrent $\ge 90\%$ de `packages/orcia-pack-builder` (`AD-17`, `AD-19`, `AD-20`).

### Story 11.5: Processus 5 `generate-and-attach-help`, Validateur Déterministe `validate_help_article` (Palier 1 `< 5 s`) & Rattachement à Chaud / Export Git

As a Responsable Produit, Tech Lead ou Créateur de Pack (`Hélène UJ-1`, `Yanis UJ-3`, `Antoine UJ-2`),
I want exécuter le Processus 5 (`generate-and-attach-help`) de `orcia-pack-builder` pour rédiger automatiquement en français et en anglais les fiches d'aide `HelpArticle`, les vérifier en `< 5 s` via la Gate Déterministe `validate_help_article` et les rattacher à chaud en `< 100 ms` à la Colonne `❓` (`340px`), au menu `Aide`, à la recherche `⌘K` et au RAG `RÉFÉRENCE` (tout en exportant le fichier `.md` vers Git),
So that aucune nouvelle fonctionnalité ni aucun nouveau Pack Métier ne soit jamais livré sans son aide contextuelle à jour (`Principe D.4`, `Section 4.4`, `AD-5`, `AD-9`, `AD-18`, `AD-19`, `AD-20`).

**Acceptance Criteria:**

**Given** le workflow `orcia://pack-builder/workflows/generate-and-attach-help` lancé soit manuellement avec revue humaine (`Action Staged`), soit automatiquement sur événement de publication d'un Pack/Processus sous `AUTONOMOUS_CONTRACT` (`AD-18`)
**When** l'étape 2 (`@Rédacteur-Documentation-Orcia`) génère la fiche Markdown bilingue (`fr`/`en`) à frontmatter YAML déclaratif (`id`, `version`, `bound_routes`, `pack_id`, `roles_allowed`, `glossary_terms`, `related_workflows`) et la soumet à l'étape 3 (**Gate Déterministe `validate_help_article` en Sandbox Palier 1 `< 5 s`**)
**Then** `validate_help_article` vérifie automatiquement :
1. Que chaque route de `bound_routes` existe dans l'arbre TanStack Router ou le manifeste du Pack ;
2. Qu'aucun composant UI inexistant dans `@orcia/ui` n'est cité et que les 3 sections obligatoires (`## 1. À quoi sert cet écran ?`, `## 2. Comment faire (Pas-à-pas)`, `## 3. Questions fréquentes & Dépannage`) ainsi que les ancres `#` sont présentes ;
3. Que les termes de `glossary_terms` sont alignés avec le Glossaire et qu'**aucun secret ou token** ne figure dans le texte (`0` fuite).

**Given** une fiche `HelpArticle` ayant franchi la Gate Déterministe (et la Gate Agentique / Revue Humaine selon le régime)
**When** l'étape 4 exécute le rattachement à chaud
**Then** la fiche est persistée atomiquement dans `catalog_items` (`item_type = "HELP_ARTICLE"`) + `cas/<sha256>` (`SeaweedFS`), son vecteur `halfvec(1024)` + `tsvector` est indexé avec `authority_role = "REFERENCE"`, le cache Redis `help:route:*` est invalidé pour un affichage immédiat en `< 100 ms` dans la Colonne `❓` (`340px`), et le fichier `.md` est exporté vers `docs/help/{fr,en}/` ou `packages/orcia-pack-{slug}/help/{fr,en}/`
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis + SeaweedFS) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

## Epic 12: Intégration Bout-en-Bout du Portail SPA (`apps/web`) — Bascule sur le Shell 4 Zones Direction C (8 Entrées Fixes), Cockpit Épuré, `Mon Assistant` (Epic 10), `Mes Espaces` 5 Onglets & Atelier `orcia-pack-builder` (Epic 11)

Réaliser la bascule visuelle et fonctionnelle complète de l'application SPA `apps/web` vers la refonte des **Epics 9, 10 et 11** conçue par **Sally (`bmad-agent-ux-designer`)** et **Winston (`bmad-agent-architect`)** : remplacer l'ancien `<AppShell />` à 3 zones (et son dock droit permanent + barre mobile du bas) par le **Shell 4 Zones Direction C (`FourZoneDirectionCShell`)** avec ses **8 entrées fixes** (`1. Cockpit`, `2. Mon Assistant`, `3. Mes Espaces`, `4. Mes Agents`, `5. Mes Processus`, `6. Centre de Contrôle`, `7. Paramètres`, `8. Aide`), unifier les jetons sémantiques CSS et classes utilitaires dans `@orcia/ui/styles/tokens.css`, épurer le Cockpit (`StreamlinedCockpitView` + `ProgressiveDay0AccostageBanner` sans les anciens blocs redondants), et monter dans `apps/web` l'intégralité des écrans **`Mon Assistant` (Epic 10)** et **`Mes Espaces` 5 sous-onglets / Chaîne ADN Starlark / Banc de Test MCP `🔌` / Atelier `orcia-pack-builder` (Epic 11)**.

### Story 12.1: Bascule de `apps/web` sur le Shell 4 Zones Direction C (`FourZoneDirectionCShell`), Navigation 8 Entrées Fixes, Unification CSS (`tokens.css`) & Cockpit Épuré (Epic 9)

As a Utilisateur d'ORCIA (Contributeur, Chef d'Équipe, Architecte ou Administrateur),
I want que le portail `apps/web` démarre directement dans le nouveau **Shell 4 Zones Direction C** (`FourZoneDirectionCShell`) avec la barre supérieure `52px` (sélecteur d'Espace, recherche globale `⌘K` `TopHeaderSearchCommand`, bouton `❓` et menu Avatar `UserAccountDropdownAndSettingsModal`), le rail gauche à **8 entrées fixes**, la colonne d'aide contextuelle `❓` (`340px` `ContextualHelpColumnAndCenter`) et le **Cockpit épuré** (`StreamlinedCockpitView` + `ProgressiveDay0AccostageBanner`), sans l'ancien dock droit ni les anciens blocs redondants ni aucun bouton HTML non stylé,
So that l'expérience visuelle réelle au lancement de l'interface corresponde à 100 % à la refonte Direction C et aux 11 règles fondamentales UX/UI (`DESIGN.md`, `EXPERIENCE.md`, `UX-DR1`, `AD-19`).

**Acceptance Criteria:**

**Given** le fichier `packages/ui/src/styles/tokens.css`, le conteneur `apps/web/src/components/ShellContainer.tsx`, le routeur `apps/web/src/router.tsx` et la vue `apps/web/src/features/cockpit/index.tsx`
**When** l'utilisateur démarre et ouvre `apps/web` sur `/cockpit` ou navigue entre les entrées du rail latéral gauche
**Then** :
1. `packages/ui/src/styles/tokens.css` définit tous les alias de jetons sémantiques Direction C (`--color-surface-elevated`, `--color-surface-base`, `--color-surface-muted`, `--color-border-subtle`, `--color-text-primary`, `--color-text-secondary`, `--color-accent-primary`, `--color-status-success`, `--color-status-warning`, `--color-status-danger`) et les classes utilitaires de mise en page utilisées par les primitives des Epics 9, 10 et 11 (sans aucune couleur hexadécimale hors de `tokens.css`) ;
2. `ShellContainer.tsx` monte **`FourZoneDirectionCShell`** en lieu et place de l'ancien `AppShell` (supprimant le dock latéral droit figé *« Agent Assistant & Permission Broker »* et l'ancienne barre basse `Inbox | Arbitrage/Chat | Briefing`), intègre dans le Header `52px` la recherche `⌘K` (`TopHeaderSearchCommand`) et le menu Compte/Paramètres (`UserAccountDropdownAndSettingsModal`), et peuple la colonne `❓` (`340px`) avec `ContextualHelpColumnAndCenter` ;
3. Le rail gauche expose les **8 entrées fixes** (`Cockpit` `/cockpit`, `Mon Assistant` `/assistant`, `Mes Espaces` `/workspaces`, `Mes Agents` `/agents`, `Mes Processus` `/processes`, `Centre de Contrôle` `/control-center`, `Paramètres` `/settings`, `Aide` `/help`) et le Cockpit (`CockpitFeaturePanel`) affiche uniquement la bannière d'accostage progressif **`ProgressiveDay0AccostageBanner`** et le flux **`StreamlinedCockpitView`** (sans l'ancien `ScopedPromptBox` ni l'ancienne `PlatformOnboardingChecklistCard` dupliquée)
**And** `pnpm turbo run lint typecheck test` passe à `0` erreur.

### Story 12.2: Montage de l'Écran Dédié `Mon Assistant` (`/assistant`) Tout-en-Un dans `apps/web` (Epic 10 : Dossiers Collaboratifs, Sélecteur 3 Vitesses, Citations `[S1]`/`[G1]`/`[O1]` & Gouvernance 4 Niveaux)

As a Utilisateur Métier, Product Manager ou Tech Lead (`Hélène UJ-1`, `Yanis UJ-3`, `Marc UJ-5`),
I want accéder depuis l'entrée **`2. 💬 Mon Assistant`** du rail gauche (ou depuis le raccourci du Cockpit) à l'écran complet `Mon Assistant` réunissant mes dossiers thématiques et fils collaboratifs, le sélecteur 3 vitesses (`⚡ Rapide`, `🧠 Réflexion`, `🔬 Recherche Approfondie`), les pastilles de citations déterministes `[S1]` / `[G1]` / `[O1]`, la carte d'artefact `📄 Ouvrir dans l'Atelier` et la modale `⚙️ Gouvernance & Instructions (4 niveaux)` (Mode A Formulaires & Mode B Studio),
So that je puisse utiliser concrètement dans le navigateur toutes les capacités conversationnelles et collaboratives livrées dans l'Epic 10 (`Principes B, H, K`, `AD-6`, `AD-15`, `AD-19`).

**Acceptance Criteria:**

**Given** la route `/assistant` et le module feature `apps/web/src/features/inbox/index.tsx` (ou vue dédiée `Mon Assistant`)
**When** l'utilisateur clique sur **`💬 Mon Assistant`** dans le rail gauche ou sur la carte d'accès rapide du Cockpit
**Then** :
1. L'écran monte et orchestre de façon interactive les 4 briques `@orcia/ui` de l'Epic 10 :
   - **`AssistantFoldersAndCollaborativeThreadView`** (barre latérale des dossiers thématiques, visibilité `🔒 Privé` / `👁️ Lecture seule` / `✍️ Co-contribution`, recherche plein texte dans l'historique) ;
   - **`AssistantSpeedSelectorAndStreamView`** (sélecteur 3 vitesses `⚡ Rapide`, `🧠 Réflexion`, `🔬 Recherche Approfondie`, indicateur TTFT `< 1,2 s` et progression temps réel) ;
   - **`AssistantCitationPillsAndArtifactCard`** (pastilles interactives `[S1]` Sources, `[G1]` Glossaire & Normes, `[O1]` Outils MCP, tiroir de preuve et carte d'artefact long) ;
   - **`AssistantGovernanceModalAndStudio`** (ouverture de la modale `⚙️ Personnaliser & Gouverner` avec bascule Mode A Formulaires 4 niveaux $\leftrightarrow$ Mode B Studio DAG) ;
2. Toutes les étiquettes proviennent des dictionnaires `fr.ts` / `en.ts` (`100 %` parité bilingue)
**And** `pnpm turbo run lint typecheck test` passe à `0` erreur.

### Story 12.3: Montage dans `apps/web` de `Mes Espaces` à 5 Sous-Onglets (`/workspaces`), Chaîne ADN & Glossaire Starlark, Banc de Test MCP/A2A `🔌` (`/agents`, `/settings`) & Atelier `orcia-pack-builder` (`/processes`, `/help`) (Epic 11)

As a Responsable d'Espace, Steward Métier, Concepteur de Pack ou Administrateur (`Marc UJ-5`, `Hélène UJ-1`, `Antoine UJ-2`, `Karim UJ-9`),
I want retrouver et manipuler directement dans les écrans **`3. 📦 Mes Espaces`**, **`4. 🤖 Mes Agents`**, **`5. 🔗 Mes Processus`**, **`7. ⚙️ Paramètres`** et **`8. ❓ Aide`** de `apps/web` les 5 sous-onglets de l'Espace (`Vue d'ensemble`, `Documents & Sources`, `Livrables & Artefacts`, `Glossaire & Règles métier`, `Membres & Équipe`), le compilateur `Text-to-Starlark` & la file `✨ À valider` du Glossaire, le Banc de Test à Chaud en 4 étapes (`🔌`) + exposition MCP gouvernée, ainsi que l'Atelier Système `orcia-pack-builder` (Processus 1 à 5 et validateur `validate_help_article`),
So that toutes les fonctionnalités de gouvernance métier, de sécurité MCP et d'extensibilité par Packs de l'Epic 11 soient pleinement opérationnelles dans l'interface web (`Principes D.4, I, J, L, M`, `AD-7`, `AD-9`, `AD-19`, `AD-20`).

**Acceptance Criteria:**

**Given** les routes `/workspaces`, `/agents`, `/processes`, `/control-center`, `/settings` et `/help` dans `apps/web`
**When** l'utilisateur navigue vers ces écrans depuis le rail gauche à 8 entrées
**Then** :
1. **`📦 Mes Espaces` (`/workspaces`)** monte **`WorkspaceFiveTabsAndExternalRebaseView`** (navigation interactive entre les 5 sous-onglets, qualification des sources `📚 RÉFÉRENCE` / `🛠️ ACTIF`, dérogations d'exception `Verrou V1`, et statut `🔒 HUMAN_AMENDED_EXTERNAL` `Verrou V2`) ainsi que **`DnaStarlarkCompilerAndGlossaryLifecycleView`** dans l'onglet `Glossaire & Règles métier` (fil d'Ariane causal `🛡️ DIRECTIVE ➔ 📏 NORME ➔ ⚙️ MÉCANISME`, compilation Starlark `< 2 ms` et promotion *In-Flow* `Verrou V4`) ;
2. **`🤖 Mes Agents` (`/agents`) & `⚙️ Paramètres` (`/settings`)** montent **`RemoteServiceTestBenchAndMcpExposureView`** permettant d'exécuter visuellement les 4 étapes du Banc de Test à Chaud (`🔌`) et d'activer l'exposition MCP gouvernée (`/api/v1/mcp`) ;
3. **`🔗 Mes Processus` (`/processes`) & `❓ Aide` (`/help`)** montent **`PackBuilderProcessesStudioView`** (Processus 1 à 4 de `orcia-pack-builder` avec Ancrage Humain Violet obligatoire, simulation *What-If* et certification Starlark) ainsi que **`HelpArticleGeneratorAndValidatorView`** (Processus 5 `generate-and-attach-help` & Gate `validate_help_article` `< 5 s`) et le Centre d'Aide complet ;
4. L'isolation d'architecture (`check-feature-boundaries.mjs`, `ui-isolation.test.ts`, parité i18n `fr`/`en`) et l'ensemble des tests Vitest de `packages/ui` et `apps/web` passent à `100 %`.

### Story 12.4: Épuration UX « Zéro Donnée Fictive », Modale de Création du Compte Administrateur au 1er Démarrage, Grisage des Fonctionnalités Non Configurées, Nettoyage de la Sidebar & Purge des Libellés NFR

As a Administrateur de la Plateforme ou Utilisateur d'ORCIA (`Karim UJ-9`, `Hélène UJ-1`, `Yanis UJ-3`),
I want que l'application démarre au 1er lancement sur la modale de création du compte Administrateur de la plateforme, parte d'une interface 100 % vierge sans aucune donnée fictive (`0` dossier `PAY-142`, `0` source `PSD2`, `0` règle Starlark pré-remplie, `0` profil fictif `Administrateur / Tech Lead`), grise (`disabled`) toutes les entrées de navigation et fonctionnalités non encore accessibles faute de configuration suffisante, retire le bouton de langue redondant de la `TopHeaderBar`, supprime le sélecteur `Pack Métier actif` et les raccourcis parasites du bas de la Sidebar gauche, remplace « Casquette métier » par le sélecteur « Rôle » avec des libellés humains, et purge tous les textes liés aux NFR et à la plomberie technique (`< 500ms`, `0 ms`, `< 2 ms`, `340px`, `Couche 5`, `AD-*`, `UX-DR*`),
So that l'interface respecte intégralement les 11 règles fondamentales UX/UI (`EXPERIENCE.md`, `DESIGN.md` — Centrer sur l'utilisateur, Loi de Hick / Minimalisme, et credo « partir d'une interface vide »).

**Acceptance Criteria:**

**Given** le premier démarrage de la plateforme (`0` compte administrateur initialisé) dans `apps/web`
**When** l'application s'affiche dans le navigateur
**Then** :
1. **Modale de 1er démarrage (`first-boot-admin-setup-modal`)** : l'écran affiche en premier plan la modale dédiée de création du compte **Administrateur de la plateforme** (Nom complet, Adresse e-mail, Mot de passe, jeton d'amorçage si requis) sans aucune identité fictive pré-remplie ; une fois validée, l'identité active affiche le nom saisi et le rôle **`Administrateur de la plateforme`** (et jamais `Administrateur / Tech Lead`) ;
2. **Credo « Partir d'une interface vide » (`0` donnée fictive)** : tous les écrans (`Cockpit`, `Mon Assistant`, `Mes Espaces`, `Mes Agents`, `Mes Processus`, `FinOps`, `Configuration`, `Aide`) démarrent avec `0` dossier fictif (`PAY-142` / `ADR-019` supprimés), `0` message ou extrait pré-rempli, `0` source ou dérogation fictive, `0` mécanisme Starlark ou candidat glossaire fictif, et `0` service MCP fictif ;
3. **Grisage (`disabled`) des fonctionnalités non accessibles faute de configuration** : dans la Sidebar à 8 entrées (`FourZoneDirectionCShell`) et dans les vues centrales, toute fonctionnalité dont les prérequis de configuration ne sont pas remplis (ex. `Mon Assistant` et `Mes Agents` tant qu'aucun modèle IA n'est configuré ; `Mes Processus` et `FinOps` tant qu'aucun Espace ou modèle IA n'est configuré) est visuellement grisée (`disabled`, `aria-disabled="true"`) avec une infobulle explicite indiquant la configuration requise ;
4. **Nettoyage de la `TopHeaderBar`, du bas de la Sidebar et du Menu Utilisateur** :
   - Le bouton de langue redondant (`shell-locale-toggle`) est retiré de la `TopHeaderBar` (le sélecteur de langue résidant dans le menu de l'utilisateur à droite) ;
   - Le sélecteur `Pack Métier actif` et les raccourcis redondants (`sidebarModuleShortcuts`) sont retirés du bas de la Sidebar gauche ;
   - Dans le menu de l'utilisateur à droite (`UserAccountDropdownAndSettingsModal`), le sélecteur est conservé et renommé **« Rôle »** (`Role` en anglais) avec des libellés métiers lisibles (*Administrateur de la plateforme*, *Product Manager / Métier*, *Architecte*, *Tech Lead / Développeur*, *Sécurité & Conformité*) ;
5. **Purge complète des textes NFR et du jargon interne** : toutes les mentions de latences NFR (`< 500ms`, `0 ms`, `< 30 ms`, `< 50 ms`, `< 2 ms`, `< 5 s`, `< 100 ms`, `< 1,2 s`, `< 10 ms`, `< 15 s`), de dimensions en pixels (`340px`, `420px`, `280px`, `720px × max 600px`) et de références internes (`Couche 5`, `Mode A — 3 onglets`, `AD-*`, `UX-DR*`, `LOCK TABLE users`, `POST /api/v1/auth/logout → /login`) sont retirées des dictionnaires `fr.ts`, `en.ts` et `epic5..11_labels.ts`
**And** la parité bilingue `fr`/`en` à `100 %`, l'isolation `@orcia/ui` et `pnpm turbo run lint typecheck test` passent à `0` erreur.

## Epic 13: Évolutions Continues & Traçabilité des Capacités (Travaux Hors Epic Rattachés au PRD)

Garantir qu'aucune évolution fonctionnelle livrée hors Story ne reste orpheline : chaque demande ad-hoc fonctionnelle est rattachée à un FR du PRD, à une capacité `CAP-xxx` de `docs/product/capabilities.yaml` et à une Story rétroactive `13.x`. Les travaux d'hygiène (purge, accessibilité, câblage, refactoring) ne sont pas des fonctionnalités : ils se traitent comme NFR / garde-fous.
**FRs covered:** `FR-31`, `FR-32`, `FR-33`, `FR-34`, `FR-35`, `FR-36` (rattachement rétroactif des travaux hors epic).

### Story 13.1: Registre des Capacités, Contrôle de Couverture CI & Régularisation PRD v2

As a Product Owner / Tech Lead,
I want un registre unique des capacités livrées, relié au PRD, aux epics et aux surfaces réelles, contrôlé en CI,
So that je sache à tout moment ce qui est en place, quelle en est l'origine (epic ou ad-hoc), et que toute nouvelle route ou tout nouveau routeur soit rattaché à une capacité.

**Acceptance Criteria:**

**Given** `docs/product/capabilities.yaml`
**When** `pnpm site:check` s'exécute
**Then** il échoue si un `id` est dupliqué, un champ obligatoire manque, un `FR-n` n'existe pas dans le PRD, ou si une route SPA / un routeur FastAPI n'est ni référencé par une capacité ni listé dans `coverage_exemptions` avec une raison
**And** le PRD v2.0 définit `FR-31` à `FR-36` (§4.10) et la FR Coverage Map les référence.

### Story 13.2 (gabarit) : Évolution Fonctionnelle Rétroactive `13.x`

Toute demande ad-hoc fonctionnelle crée une Story `13.x` (rattachée au `FR-3x` concerné) ainsi qu'une entrée ou mise à jour `CAP-xxx` ; le rapport Tech Lead porte le champ `Capacité(s)`.
