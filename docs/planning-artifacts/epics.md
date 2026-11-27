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
- **FR-13** : Epic 3 (et gouvernance d'incident sans modification de code différée dans `AIOPS-INCIDENT-LOOP-01`) - Garantie de la discipline Intention -> Code (mode `brownfield_bootstrap` et dossier d'intention de remédiation)
- **FR-14** : Epic 3 & Epic 7 - Orchestration Hybride Multi-LLM agnostique, exécution tri-modale (`Coaching` / `Fast-Path` / `Autonomous Contract`) & Blackboard filtré
- **FR-15** : Epic 3 - Version Pinning immuable des Workflow Runs (`run-lock.json` SHA-256 récursif)
- **FR-16** : Epic 3 - Replay ciblé à partir du Step N (Time-Travel Execution sur branche ACTIVE et intra-sous-workflow)
- **FR-17** : Epic 4 - Gates Déterministes en Sandbox (< 5s, sans réseau, conformité Gabarit/Ontologie & anti-Pattern Drift)
- **FR-18** : Epic 4 - Gates Agentiques avec Orthogonalité des Modèles, lentille fact_verification & Contrôle Transverse
- **FR-19** : Epic 4 & Epic 7 - Gates Humaines à Politique Adaptative, tirage d'audit post-hoc (`POST_HOC_AUDIT_SAMPLE`) et garde-fou anti-Rubber-Stamping (< 15s)
- **FR-20** : Epic 1 - Résolution à la volée du Catalogue Fédéré (db://, git://, nexus://, confluence://, jira://, orcia://), surcharges 4 niveaux (Base -> Team -> Workspace -> User) & cache SHA-256
- **FR-21** : Epic 1 - Authentification hybride bi-mode, hiérarchie d'équipes (`OrgUnit`) découplée des Workspaces solutions, rôle `TEAM_LEAD` & 5 permissions dissociées du Catalogue
- **FR-22** : Epic 1 & Epic 7 - Exécution Passthrough / Service Principal scopé et Permission Broker IA connecté à Jira
- **FR-23** : Epic 2, Epic 19 - Indexation différenciée incrémentale, Graphe Tripartite (Confluence <-> Jira <-> Git), embeddings sémantiques réels (EmbeddingPort dim 1024, AD-24), data-freshness & [STALE_WARNING]
- **FR-24** : Epic 4 & Epic 7 - Actions & transitions de workflows Jira Staged aux Gates (+ Webhooks), Skills en Sandbox & MCP Bidirectionnel (/api/v1/mcp)
- **FR-25** : Epic 6 - Provenance Auditable complète et immuable par Step et par Gate (audit_ledger)
- **FR-26** : Epic 6 & Epic 7 - Comptabilité FinOps complète (Coût Setup + Run vs TTM) et coupe-circuits budgétaires par Run/Arbre/Trigger
- **FR-27** : Epic 6 & Epic 7 - Indicateurs d'impact cognitif, anti-Rubber-Stamping, Indice de Réversibilité Humaine et métriques d'autonomie (`SM-A1..A3`)
- **FR-28** : Epic 1 - Workflows Système d'initialisation, onboarding autonome d'équipe & multi-workspaces (`TEAM_LEAD`) et auto-amorçage gouverné (orcia://system/bootstrap/*)
- **FR-29** : Epic 7 - Exécution Autonome sous Contrat (`autonomy_contracts`), Déclencheurs Événementiels Idempotents (Webhooks, Puits de Logs, Cron, Outbox opt-in) & Supervision Post-Hoc (boucle d'incident sans code/Git différée dans `AIOPS-INCIDENT-LOOP-01`)
- **FR-30** : Epic 3 & Epic 7 - Imbrication Fractale de Workflows (`Sub-Workflows` & `Workflow-as-Agent`, profondeur $\le 3$)

- **FR-31** : Epic 8, Epic 19, Epic 20 (+ ad-hoc, Epic 13) - Gouvernance d'entreprise & Paramètres : habilitations RBAC/ABAC à 6 verbes, délégation « Mon Organisation » (`BU_LEAD` / `TEAM_LEAD`), rôle `ONTOLOGY_LEAD`, modèles IA et routage, découverte 0 token, embeddings réels & Hub fiable, connecteurs & secrets, packs, wizards (`CAP-050`..`CAP-058`, `CAP-067`, `CAP-190`)
- **FR-32** : Epic 9, Epic 12, Epic 20 (+ ad-hoc, Epic 13) - Coquille 4 zones, recherche ⌘K, accostage Jour 0, aide contextuelle, consolidation « Mon Compte » (style ChatGPT), page « Profil » & journal d'activité scopé (`CAP-060`..`CAP-069`)
- **FR-33** : Epic 10 (+ ad-hoc, Epic 13) - Mon Assistant gouverné : 4 niveaux, 3 vitesses, citations déterministes, dossiers & fils (`CAP-070`..`CAP-076`)
- **FR-34** : Epic 11 (+ ad-hoc, Epic 13) - Mes Espaces : ADN, glossaire, routage d'artefacts, rattachement d'équipe (`CAP-067`, `CAP-080`, `CAP-081`, `CAP-084`)
- **FR-35** : Epic 11 (+ ad-hoc, Epic 13) - Exposition MCP/A2A, banc de test, atelier orcia-pack-builder (`CAP-082`..`CAP-084`)
- **FR-36** : ad-hoc, Epic 13 - Gestion des agents et compétences (`CAP-090`..`CAP-092`)
- **Couverture Intégrale User Journeys & Vérité E2E PG18 (`FR-1`..`FR-36`, `UJ-1`..`UJ-20`, `CAP-001`..`CAP-203`)** : Epic 21 - Classification `feature | foundation` (`capabilities.yaml`), référentiel complet `UJ-1`..`UJ-20` (`prd.md` & `EXPERIENCE.md`), verrou CI `pnpm site:check`, campagne Playwright intégrale (`00..21` + `shell.spec.ts`) avec survie `F5`, assertions `SELECT` PostgreSQL 18, captures PNG finales, audit croisé Sally × Winston & initialisation de l'Epic 22
- **Remédiation E2E Vérité PG18, Portails & Shell Direction C, Purge Jargon, Gardes CI, Campagne & Initialisation Epic 23 (`FR-1`..`FR-36`, `REM-01`..`REM-34`, `CAP-001`..`CAP-203`)** : Epic 22 (`22.1`..`22.10`) - Unification UUIDv7 Workspaces & droits `PLATFORM_ADMIN`, Portals `OrciaDialog` & Tailwind v4, purge `display: none` & découplage `/catalog`/`/agents`/`/help`, câblage PG18 de tous les silos RAM (`assistant_folders`, `task_notifications`, `permission_broker_tickets`, `dbos_uow`, `human_anchor_signatures`, `upstream_challenges`, `run_lock_manifests`, `gate_evaluations`, `chunk_approvals`, `declarative_pack_bundles`, `wizard_sessions`, garde `KILL_SWITCH_STOPPED`), refonte Direction C `8` entrées / Mobile `< 768px` / `docs/help/` dynamique / Cockpit `<= 3` blocs, purge intégrale du jargon technique, activation des `5` gardes CI anti-régression & assertions `SELECT` PG18 sur `100 %` des `55` blocs `test(...)` E2E (`22.8`), campagne E2E intégrale `e2e-campaign-epic-22` + captures PNG + audit croisé Sally × Winston + mise à jour honnête `capabilities.yaml` (`22.9`), rapports Tech Lead individuels & initialisation de l'Epic 23 (`22.10`)
- **Remédiation Finale E2E Desktop, Transport SSE Authentifié, Aide Contextuelle 4 Blocs, Unification Accostage `X/6`, Sobriété Direction C, Durcissement Anti-Goodhart, Campagne Desktop `52/52` & Clôture Epic 23 (`FR-1`..`FR-36`, `REM23-01`..`REM23-13`, `P0-UX-1`..`P3-UX-12`, `ARCH23-01`..`ARCH23-10`, `CAP-001`..`CAP-203`)** : Epic 23 (`23.1`..`23.5` $\rightarrow$ `23.6a` $\rightarrow$ `23.7` $\rightarrow$ `23.8`, `Story 23.6` et compatibilité Mobile Companion `390×844` / `CAP-042` reportées vers `ACTION_ITEM-23.6`) - Déblocage `resetDay0()` (`TRUNCATE ... RESTART IDENTITY CASCADE` strictement isolé `orcia_e2e`, protection `connector_schemes` et `FLUSHDB` Redis sans désactiver les triggers append-only), factorisation SSE authentifié `createRequestSse` (`Bearer` + RFC 9457) sur `/assistant/three-speed/stream`, `/trace-stream` et `/events/stream` + diagnostic critique `401` (`Se reconnecter →`) + alignement *fail-closed* `00-stack-smoke` (#3/#4), Zone 4 `Aide Contextuelle` fidèle à la route avec ses `4` blocs `DESIGN.md` natifs sans plomberie interne, unification PG18 `Accostage X/6` + fin des fantômes Jour 0 (`AP`, `Notifications 4`) + épuration `FirstBootAdminSetupModal`, réduction Cockpit `<= 3` blocs + `TopHeaderBar` sans doublon/troncatures + logo Zone 1 + `/assistant`/`/login` + preuves `#10`, durcissement anti-Goodhart (`23.6a` : introspection dynamique `information_schema`/`pg_constraint`, `operation.security` dans `vitestFetchTransport` + interdiction AST `fetch`/`EventSource`, `catch` muets + constantes fantômes, audit SQL domaine `55/55` sans `SELECT 1`, regex anti-jargon, contrats géométriques Direction C + Chaîne Canari Desktop + Tir de reconnaissance Desktop V0), campagne E2E intégrale figée Desktop `--project=desktop-cockpit` (`24` specs / `55` scénarios Desktop, `52` exécutés + `3` `mobile-only` skipped) + captures PNG d'état final + bilan exhaustif + audit croisé Sally × Winston + `capabilities.yaml` (`CAP-042` maintenue `failed_e2e` vers `ACTION_ITEM-23.6`) (`23.7`), et clôture conditionnelle Epic 23 (`Case B` déclenchant l'initialisation complète de l'`Epic 24`) (`23.8`)
- **Remédiation Finale `Case B` post-`23.7` : Persistance PG18, Triggers UUIDv7, Refonte CSS Tailwind v4, Navigation Zone 4, Zéro Jargon & Preuve Desktop `52/52` (`FR-1`..`FR-36`, `REM24-01`..`REM24-12`, `UX23-01`..`UX23-17`, `ARCH24-01`..`ARCH24-12`, `CAP-002`..`CAP-201`)** : Epic 24 (`24.1`..`24.7`, `CAP-042` maintenue sous `ACTION_ITEM-23.6`) - Persistance PG18 `jira_staged_actions` / `GovernedMcpServerService` + câblage `SqlWorkflowDefinitionsV2Store` (`24.1`), correction collision `tid[:8]` triggers UUIDv7 + `await` waivers & ADN Starlark PG18 sans `"default-ws"` (`24.2`), fin `PASS` optimiste banc distant + contrat `audit_ledger` + cache Redis `TwoSpeedFederatedSearchService` (`24.3`), ordre CSS Tailwind v4 (`tokens.css` $\rightarrow$ `virtual:orcia-tailwind.css`) + `OrciaDialog` Agent + contraste dark RGAA + shell (`24.4`), identité `platformAdmin` Accostage + route `/inbox` Zone 4 + breadcrumb `/organization`/`/spaces` + verrouillage Jour 0 (`24.5`), filtre `ci.lang = locale` `Cmd+K` + purge enums/jargon + `5` compteurs packs + troncatures `1440×900` (`24.6`), réconciliation sélecteurs E2E `/catalog` & `07-spaces`, captures jalons `< 450 KB`, campagne figée `52/52` PASS Desktop + contre-audit `0 P0 / 0 P1` & promotion `runtime` (`64/65`) sans boucle infinie (`24.7`)

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

### Epic 7: Agents & Workflows Autonomes sous Contrat, Socle d'Observabilité 12-Factor & OpenShift, Déclencheurs Événementiels Idempotents & Gouvernance Post-Hoc
Les Directeurs de BU, Chefs d'Équipe (`TEAM_LEAD` / `BU_LEAD`), Ingénieurs SRE/Plateforme et Auditeurs SecOps (`Claire UJ-8/UJ-11`, `Marc UJ-5`, `Karim UJ-9`, `Sophie UJ-6`) disposent du socle d'observabilité 12-factor unifié sur `stdout` (Story 7.0a), du puits de logs paramétrable (`LogSinkQueryPort` avec adaptateur prioritaire Elasticsearch/OpenSearch et traces OTel OTLP, Story 7.0b, `AD-23`) et de la conformité de déploiement en conteneur non-root Kustomize sur plateforme OpenShift (Story 7.0c), signent des **Contrats d'Autonomie** dans `autonomy_contracts` depuis Process Studio V2 (signature unique `TEAM_LEAD`/`BU_LEAD` sous double garde noyau sans co-signature `SECOPS`, Story 7.1), déclenchent de manière idempotente des **Workflow Runs autonomes** (`MANUAL_AUTONOMOUS`, **Webhooks signés** factorisés avec `Story 18.2`, **Tâches Planifiées `CRON`**, **Événement `OUTBOX_EVENT`** avec aide auto `generate-and-attach-help` en **opt-in explicite**, ou **Alertes de Puits de Logs `LOG_SINK_ALERT`**, Story 7.2), et supervisent ces exécutions dans la coquille Direction C (`/processes`, tiroir `Notifications`, Colonne d'aide droite et onglet existant « Maîtrise humaine & Qualité » de `/finops`, sans nouvel onglet et avec microcopy métier FR sans jargon, Story 7.4). *(La boucle fermée de gouvernance d'incident sans modification de code ni écriture Git est tracée dans `ACTION_ITEM AIOPS-INCIDENT-LOOP-01`.)*
**FRs covered:** `FR-5`, `FR-14`, `FR-19`, `FR-22`, `FR-24`, `FR-26`, `FR-27`, `FR-29`, `FR-30` (`AD-3`, `AD-6`, `AD-18`, `AD-23`, `Principe D.4`)

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

### Epic 19: Hub Modèles IA Fiable, Découverte 0 Token, Test Réel & Embeddings Sémantiques (`AD-24`)
Les Administrateurs Plateforme et Responsables IA découvrent automatiquement les modèles disponibles via des appels légers aux endpoints standards des fournisseurs sans consommer de tokens (`0 $`), configurent leurs modèles chat/raisonnement et leur **modèle d'embedding sémantique unique GLOBAL** dans une modale épurée avec placeholders contextuels dynamiques, valident la connectivité réelle (chat `max_tokens=1` et validation stricte de dimension 1024 pour embeddings) avec latence mesurée et erreurs explicites RFC 9457, s'appuient sur un démarrage Jour 0 sans aucun nom de modèle propriétaire codé en dur dans le code source où le wizard guide obligatoirement vers la configuration du modèle d'embedding (faute de quoi Mon Assistant, la recherche RAG et l'ingestion documentaire sont totalement bloqués avec l'erreur harmonisée `ERR_NO_ACTIVE_EMBEDDING_MODEL`), et bénéficient d'une recherche vectorielle RAG robuste reposant sur de vrais embeddings vectoriels (`EmbeddingPort`) avec réindexation bloquante gouvernée (Assistant totalement bloqué, recherche renvoyant HTTP 503 `ERR_RAG_REINDEX_IN_PROGRESS` sans aucun repli dégradé lexical, et nouvelles ingestions mises en file) et suppression définitive de tout hachage SHA-256 en production (`AD-8`, `AD-10`, `AD-16`, `AD-24`, `CAP-190`).
**FRs covered:** `FR-14`, `FR-18`, `FR-23`, `FR-28`, `FR-31`, `FR-33` (`AD-8`, `AD-10`, `AD-16`, `AD-24`)

### Epic 21: Couverture Intégrale par User Journeys (`UJ-1`..`UJ-20`), Campagne End-to-End avec Vérité PostgreSQL 18, Captures d'État Final, Audit Croisé UX/Architecture & Préparation de l'Epic 22
Systématiser la preuve de fonctionnement réel de 100 % des `62` capacités métier (`kind: feature`) d'ORCIA : classification complète des `65` capacités de `capabilities.yaml`, référentiel complet `UJ-1` à `UJ-20` dans `prd.md` et `EXPERIENCE.md`, refactoring modulaire de `sync_site_catalog.py` (`< 350` lignes) et verrouillage CI `CAP ↔ UJ ↔ Spec E2E`, harnais Playwright de vérité PostgreSQL 18 en lecture seule (`orcia_e2e`) avec capture PNG systématique de l'état final (succès et échecs), mise à niveau des 16 specs existantes + écriture des 8 nouvelles specs (`14`..`21`), exécution intégrale sans retry ni maquillage, inspection croisée **Sally (UX) × Winston (Architecture)**, rapports Tech Lead pré-implémentation et initialisation complète de l'**Epic 22** de remédiation.
**FRs covered:** `FR-1`..`FR-36`, `UJ-1`..`UJ-20`, `CAP-001`..`CAP-203` (`AD-17`, `NFR-TEST-1`)

### Epic 22: Remédiation E2E Vérité PG18, Portails & Shell Direction C, Purge Jargon, Gardes CI, Assainissement Fail-Closed, Campagne Intégrale & Initialisation Epic 23 (`Stories 22.1`..`22.10` + `22.8a`)
Résoudre de bout en bout les `34` chantiers issus de l'audit croisé Sally × Winston (`REM-01`..`REM-34`) et les `47` échecs/timeouts de la campagne E2E Epic 21 en **`11` Stories (`22.1`..`22.8` + intercalaire `22.8a` + clôture `22.9`..`22.10`)** réparties sur `4` vagues topologiques : unification UUIDv7 des espaces et correction des faux `403` admin (`22.1`), Portals `OrciaDialog` + Tailwind v4 + purge `display: none` + découplage `/catalog`/`/agents`/`/help` + bouton invitation `/organization` + alignement `data-testid`/contrats (`22.2`), câblage PostgreSQL 18 de tous les silos RAM (`assistant_folders`, `task_notifications`/SSE, `permission_broker_tickets` + fallback `git://*` en `22.3` ; `dbos_uow`, `human_anchor_signatures`, `upstream_challenges`, `run_lock_manifests`, `gate_evaluations`, `chunk_approvals` & garde `KILL_SWITCH_STOPPED` en `22.4` ; `declarative_pack_bundles` & `wizard_sessions` en `22.5`), alignement coquille Direction C `8` entrées + Mobile Companion `< 768px` + `docs/help/` dynamique sans `Chef1`/`aqwZSX` + Cockpit `<= 3` blocs (`22.6`), finitions UX/UI et purge intégrale du jargon technique (`22.7`), activation des `5` gardes CI anti-régression (`REM-34`) + `4` verrous anti-faux-positifs (sync `data-testid` E2E↔UI, helper Playwright typé OpenAPI, purge `ORCIA_E2E_SEED_FIXTURES` + relecture à froid PG18 `reloadColdFromPg` via `/api/v1/_e2e/evict-memory-caches`, réécriture `<RouterProvider>` de `zero-dead-buttons` + sonde `[role="alert"]` + Direction C / WCAG AA), couverture `SELECT` PostgreSQL 18 sur `100 %` des `55` blocs `test(...)` E2E (`110` scénarios) + paramétrage `ORCIA_E2E_CAMPAIGN_DIR` + budget `< 35s` (`REM-33`) (`22.8`), assainissement *Fail-Closed* de `vitest.setup.ts` contre `openapi.json` (`< 350` L), purge des fallbacks RAM + test Composition Root `create_app()` sans `dependency_overrides` ni `app.state.*` manuel et pipeline GitHub Actions complet à `5` couches (`22.8a`), exécution intégrale de la campagne E2E (`e2e-campaign-epic-22`), archivage des captures PNG, bilan d'exécution, audit croisé Sally × Winston et mise à jour honnête de `capabilities.yaml` (`22.9`), puis rédaction des rapports Tech Lead individuels (`23-1..23-N`), plan de correction global et initialisation complète de l'Epic 23 (`22.10`).
**FRs covered:** `FR-1`..`FR-36`, `UJ-1`..`UJ-20`, `CAP-001`..`CAP-203`, `REM-01`..`REM-34` (`AD-1`..`AD-24`, `UX-DR1`..`UX-DR17`)

### Epic 23: Déblocage Reset PG18/Redis, Transport SSE Authentifié, Zone 4 & Accostage `X/6`, Sobriété Direction C, Durcissement Anti-Goodhart, Campagne Desktop `52/52` & Clôture Conditionnelle (`Stories 23.1`..`23.5` $\rightarrow$ `23.6a` $\rightarrow$ `23.7` $\rightarrow$ `23.8` ; `23.6` reportée en `ACTION_ITEM-23.6`)
Résoudre intégralement et sans régression les `90` échecs (`3` `HTTP 401` directs + `87` cascades `resetDay0()`) sur `24` specs E2E ainsi que les chantiers Sally × Winston (`REM23-01`..`REM23-13`, `P0-UX-1`..`P3-UX-12`, `ARCH23-01`..`ARCH23-10`) issus de `e2e-campaign-epic-22` sur la séquence **`23.1`..`23.5` $\rightarrow$ `23.6a` $\rightarrow$ `23.7` $\rightarrow$ `23.8`** (la **`Story 23.6` et le périmètre Mobile Companion `390×844` / `CAP-042` étant reportés en `ACTION_ITEM-23.6`** pour priorisation ultérieure) : déblocage `resetDay0()` par `TRUNCATE ... RESTART IDENTITY CASCADE` strictement isolé sur `orcia_e2e` + protection `connector_schemes` + `FLUSHDB` Redis sans jamais désactiver les triggers append-only (`23.1`), factorisation SSE authentifié `createRequestSse` (`Bearer` + RFC 9457) pour `/assistant/three-speed/stream`, `/trace-stream` et `/events/stream` (verrouillé serveur), diagnostic critique `401` (`Se reconnecter →`) et alignement *fail-closed* `00-stack-smoke` #3/#4 (`23.2`), fidélité route-par-route de Zone 4 (`Aide Contextuelle`) avec les `4` blocs `DESIGN.md` natifs et masquage de la plomberie technique (`23.3`), unification PG18 `Accostage X/6` + fin des fantômes pré-admin (`AP`, `Notifications 4`) + purge des `5` props mortes `ShellContainer` + épuration `FirstBootAdminSetupModal` (`23.4`), réduction Cockpit `<= 3` blocs + suppression `topbar-fixed-workspace-selector` Desktop + logo `ORCIA` Zone 1 + `/assistant`/`/login` + captures de preuve `#10` (`23.5`), durcissement anti-Goodhart (`23.6a` : introspection PG18 dynamique, `operation.security` OpenAPI + interdiction AST `fetch`/`EventSource`, `catch` muets + constantes fantômes, SQL domaine `55/55` sans `SELECT 1`, regex anti-jargon, contrats géométriques Direction C + Chaîne Canari Desktop + Tir de reconnaissance Desktop V0), campagne Playwright E2E intégrale figée Desktop `--project=desktop-cockpit` (`24` specs / `55` scénarios Desktop, `52` exécutés + `3` `mobile-only` skipped) avec captures PNG d'état final, bilan exhaustif, audit croisé Sally × Winston et mise à jour honnête de `capabilities.yaml` (`CAP-042` maintenue `failed_e2e` vers `ACTION_ITEM-23.6`) (`23.7`), puis clôture conditionnelle déclenchant le scénario `Case B` et l'initialisation complète de l'`Epic 24` (`23.8`).
**FRs covered:** `FR-1`..`FR-36`, `UJ-1`..`UJ-20`, `CAP-001`..`CAP-203`, `REM23-01`..`REM23-13` (`AD-1`..`AD-24`, `UX-DR1`..`UX-DR17`)

### Epic 24: Remédiation Finale `Case B` post-`23.7` — Persistance PG18 (Jira Staged, MCP, VSM v2), Triggers UUIDv7, Refonte CSS Tailwind v4, Navigation Zone 4, Zéro Jargon & Preuve Desktop `52/52` (`Stories 24.1`..`24.7` ; `CAP-042` maintenue sous `ACTION_ITEM-23.6`)
Résoudre les `8` échecs/timeouts Desktop (`#15`, `#16`, `#40`, `#41`, `#45`, `#47`, `#48`, `#49`) ainsi que les `17` constats UX `UX23-01`..`UX23-17` (`1 P0` + `9 P1` + `5 P2` + `2 P3`) et `12` diagnostics `ARCH24-01`..`ARCH24-12` (`REM24-01`..`REM24-12`) issus de `Story 23.7` selon `docs/planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md` : persistance PG18 des actions Jira staged (`jira_staged_actions`), gouvernance MCP & `SqlWorkflowDefinitionsV2Store` (`vsm_definitions_v2`) sans helper lazy routeur (`24.1`), correction collision `tid[:8]` des triggers UUIDv7 + `await` waivers & ADN Starlark PG18 sans `"default-ws"` (`24.2`), fin du `PASS` optimiste banc distant + contrat `audit_ledger` (`ADMIN_CONNECTION_TEST`) + cache Redis `TwoSpeedFederatedSearchService` (`24.3`), refonte layering CSS Tailwind v4 (`main.tsx` / `tokens.css`) + `OrciaDialog` Agent + contraste RGAA sombre + shell (`24.4`), identité `platformAdmin` Accostage + route Zone 4 `/inbox` + fil d'Ariane `/organization`/`/spaces` + verrouillage `Mes Espaces` Jour 0 (`24.5`), filtre `ci.lang = locale` `Cmd+K` + purge enums/jargon + `5` compteurs `/settings/packs` + troncatures `1440×900` (`24.6`), réconciliation sélecteurs E2E `/catalog` & `07-spaces`, captures jalons `< 450 KB`, campagne figée `52/52` PASS Desktop (`0` échec), contre-audit `0 P0 / 0 P1` et promotion des `25` capacités vers `runtime` sans boucle infinie (`24.7`).
**FRs covered:** `FR-1`..`FR-36`, `UJ-1`..`UJ-20`, `CAP-002`..`CAP-201` (`25` Desktop `failed_e2e`), `REM24-01`..`REM24-12`, `UX23-01`..`UX23-17`, `ARCH24-01`..`ARCH24-12` (`AD-1`..`AD-24`, `UX-DR1`..`UX-DR17`)

### Epic 27: English-Only Development & Documentation Governance, 100% Bilingual FR/EN Web Application & Deterministic i18n Controls (`Stories 27.1`..`27.8`)
Enforce English-only development communication, documentation, Tech Lead reports, and code comments/docstrings across ORCIA while keeping the web application (`apps/web` + `@orcia/ui`) and backend user-facing responses (`Accept-Language` RFC 9457 error catalogs and Assistant prompt bundles) **100% bilingual compatible in French (`fr`) and English (`en`)**. Remediate all `3,809` audited occurrences (`ACTION_ITEM-I18N.1`, Categories A/B/C/D across `461` files) in 6 lots (`Stories 27.1`–`27.8`) protected by 4 deterministic CI gates with decreasing ratchet baselines locked to `0` (`ClientErrorCode` + `resolveClientErrorMessage`, TS/JSX AST ban on inline locale ternaries and raw JSX strings, FR↔EN dictionary key/placeholder parity & zero-jargon audit, backend RFC 9457 `fr`/`en` catalog completeness & English-only comment/docstring check on touched files) and verified via bilingual (`fr` & `en`) Playwright E2E scenarios.
**Requirements & Decisions covered:** `ACTION_ITEM-I18N.1`, `epic-27-decisions-grill-2026-11-23.md` (`D1–D4`), `AD-17`, `AD-19`, RFC 9457, UX Rules 1–3 (`CAP-001`..`CAP-260`)

### Epic 28: Unified "Mes Espaces" (`/workspaces`) 5-Tab Screen, Component De-Duplication & Direction C Sobriety (`Stories 28.1`..`28.4`)
Eliminate the 6-block vertical stacking, duplicate 3-tab vs 5-tab systems, redundant headers, raw `personal-<uuid>` slug leaks, permanent bottom-of-page DNA Starlark/glossary panels, and `total == 0` counter/filter clutter on `/workspaces` (`WX-01`..`WX-06`, audited by Sally & Winston in `docs/planning-artifacts/sprint-change-proposal-2026-11-23-epic-28-workspaces-unification.md`). Converge `WorkspacesFeaturePanel` onto a single compact workspace header synchronized with the global Sidebar Active Workspace Selector and a single canonical 5-tab container (`1. Accostage & Vue d'ensemble` | `2. Documents & Sources` | `3. Livrables & Artefacts` | `4. Glossaire & Règles Métiers` | `5. Membres & Paramètres de l'espace`) wired 100% to scoped PostgreSQL 18 truth (`<= 300` lines per file, bilingual `fr`/`en`).
**Requirements & Decisions covered:** `FR-8`..`FR-10`, `FR-20`, `FR-23`, `FR-34`, `UJ-5`, `UJ-9`, `UJ-18`, `CAP-010`, `CAP-067`, `CAP-080`, `CAP-081`, `CAP-084`, `CAP-180`, `DESIGN.md` (§Brand & Style #3, §Do's and Don'ts), `EXPERIENCE.md` (§1.1, §1.2, §2.2 `Mes Espaces`), `WX-01`..`WX-06`

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

## Epic 14: ORCIA Process Studio v2 — Cartographie VSM (`ValueStreamMapSpec`), Studio Agentique Déterministe à 5 Blocs (`Control-M`), Gates Multi-Niveaux Auto-Heal (3x) & Portail HITL 4 Actions (`specs/epic-09-process-studio/`)

Déployer l'**ORCIA Process Studio v2** en séparant la **Cartographie de Chaîne de Valeur (`ValueStreamMapSpec`)** (vue macro de gouvernance en 4 phases, 11 étapes, 5 points de passage humains et 8 boucles de retour extraite de `Workflow agentique 2.html`) et les **Workflows DBOS Unitaires et Bornés (`WorkflowDefinitionV2`)** (`wf-01-qualification-prd`, `wf-03-etude-architecture`, `wf-06-decoupe-us`, `wf-08-dev-external-gate`), avec zéro « Agent Orchestrateur » lisant le chat (`DeterministicSubStepSpec` + `DBOS.recv`), support des modes `NATIVE_ORCIA` et `EXTERNAL_DELEGATED_GATE`, stockage S3 `ClaimCheckPointer` (`> 4 Ko`), idempotence cyclique `:iter-{iteration}` et Studio 5 blocs façon Control-M assisté par Co-pilote.

### Story 14.1: Modèle Agnostique `orcia-core` (VSM + Workflows Bornés + Claim-Check S3) & Seed Déclaratif `packs/sdlc/`
- **CA-14.1.1 (Zéro fuite SDLC dans Core)** : Aucun mot-clé métier SDLC (`jira`, `confluence`, `git`, `prd`, `wsjf`, `rovo`, `copilot`, `safe`) dans `packages/orcia-core` (`tests/unit/core/test_core_domain_isolation.py`).
- **CA-14.1.2 (Immuabilité & Fork Draft)** : Toute modification d'un workflow `PUBLISHED` crée une branche `vX.Y.Z-draft` sans impacter les exécutions DBOS actives.
- **CA-14.1.3 (Claim-Check obligatoire)** : Tout livrable d'étape ou diff `> 4 Ko` est persisté dans SeaweedFS avec empreinte `SHA-256` (`ClaimCheckPointer`).

### Story 14.2: Vue Cartographie de Chaîne de Valeur (Macro-VSM) & Comparaison 3 États (`/processes/vsm/$vsmId`)
- **CA-14.2.1 (Commutateur 3 États en Consultation)** : Bascule fluide `Aujourd'hui | Avec les agents | Comparer`.
- **CA-14.2.2 (Boucles de retour SVG sans collision)** : Tracé dynamique des boucles principales et secondaires (`ReturnLoopsSvgOverlay.tsx`), fiche modale à 6 onglets (`StepDetailSheet.tsx`), opportunités `P1..P3` et mode `Présenter`.
- **CA-14.2.3 (Pont VSM ➔ Workflow Exécutable)** : Ouverture directe du Workflow dans le Studio 5 Blocs ou lancement/suivi d'exécution unitaire.

### Story 14.3: Studio de Conception de Workflow (5 Blocs Control-M + Co-pilote Gauche + Sous-Étapes DBOS `/processes/studio/$workflowId`)
- **CA-14.3.1 (Co-pilote & Suggestions Catalogue)** : `StudioCopilotSidebar.tsx` suggérant les `Toolboxes MCP`, `Skills` et `Gates` du Pack actif avec attachement `[+]`.
- **CA-14.3.2 (Séquence de Sous-Étapes Déterministes DBOS)** : Enchaînement de $N$ sous-étapes séparées par des jalons DBOS (`requires_human_checkpoint`) et bypass unitaire (`enabled: false` $\rightarrow$ `SKIPPED`).
- **CA-14.3.3 (Modes `NATIVE_ORCIA` vs `EXTERNAL_DELEGATED_GATE`)** : Configuration du mode natif ORCIA ou sas externe délégué (IDE Copilot / Rovo / Webhook).

### Story 14.4: Pipeline Ordonné de Gates (4 Runners Déterministes Génériques Auto-Heal 3x ➔ Probabilistes) & Test Mode What-If
- **CA-14.4.1 (Ordre Inviolable & Auto-Heal)** : Exécution des 4 runners génériques (`markdown_contract_runner`, `json_schema_runner`, `cli_sandbox_runner`, `catalog_invariant_runner`) avec auto-remédiation bornée à `max_self_heal_retries = 3`.
- **CA-14.4.2 (Gates Probabilistes Conditionnées)** : Exécution des Hunters contradictoires uniquement si 100 % des Gates déterministes sont `NOMINAL`.
- **CA-14.4.3 (Exécution Sandbox What-If)** : Simulation isolée sans `execute_write` externe retournant `ImpactAssessmentResult`.

### Story 14.5: Les 5 Dispositifs d'Interaction Humaine (HITL) & Boucles de Reprise Itératives (`InteractiveRunDrawer.tsx`)
- **CA-14.5.1 (Write-Preview Gate Obligatoire)** : Interception de toute écriture externe via `preview_write()` (`WritePreviewCard`) et exigence d'un `SignedApprovalToken` du *Permission Broker* avant `execute_write()`.
- **CA-14.5.2 (Arbitrage Souverain à 4 Actions sur Diff S3)** : `APPROVE` (Accepter & Signer), `AMEND_DIFF` (Amender directement le Diff S3), `REJECT_AND_LOOP` (Refuser & Choisir la boucle de retour), `SUSPEND_SLA` (Suspendre le SLA).
- **CA-14.5.3 (Incrémentation d'itération sur Boucle de Retour)** : Clé d'idempotence `f"{run_id}:{sub_step.id}:iter-{iteration}"` et réinjection des remarques en mode `corrections`.

## Epic 15: Simplification Architecturale des Packs & Connecteurs (`packages/orcia-connectors`, Fusion `orcia-kernel` dans `orcia-core` & Packs 100 % Déclaratifs `packs/<domaine>/`) (`specs/epic-10-packs-simplification/`)

Simplifier radicalement l'architecture Python backend autour de **2 uniques packages Python** dans `packages/` (`packages/orcia-core` qui absorbe `orcia-kernel` dans `orcia_core.kernel`, et `packages/orcia-connectors` qui unifie Jira, Confluence, Git, SQL et MCP derrière `OrciaConnectorProtocol` à 4 méthodes) et convertir tous les Packs métiers en **bundles 100 % déclaratifs (YAML + Markdown, zéro code Python/React)** sous `packs/sdlc/` et `packs/orcia-docs/`.

### Story 15.1: Création de `packages/orcia-connectors` (`OrciaConnectorProtocol`) & Fusion de `orcia-kernel` dans `orcia-core` (`TASK-01`)
- **CA-15.1.1 (Contrat Unique à 4 Méthodes)** : `OrciaConnectorProtocol` (`healthcheck`, `read`, `preview_write`, `execute_write`) et adaptateurs `atlassian_jira.py`, `atlassian_confluence.py`, `git_provider.py`, `sql_readonly.py`, `mcp_client_bridge.py` vérifiant la signature `SignedApprovalToken` du *Permission Broker*.
- **CA-15.1.2 (2 Packages Python Uniques dans `packages/`)** : Absorption de `packages/orcia-kernel` dans `packages/orcia-core/src/orcia_core/kernel/` et suppression de `packages/orcia-kernel/`.

### Story 15.2: Chargeur `DeclarativePackLoader`, Exportateur `.zip` & Conversion Déclarative `packs/sdlc/` et `packs/orcia-docs/` (`TASK-02` & `TASK-03`)
- **CA-15.2.1 (Packs 100 % Déclaratifs)** : Chargement à chaud via `DeclarativePackLoader` de `packs/sdlc/` et `packs/orcia-docs/` (YAML + Markdown uniquement) et suppression définitive de `packages/orcia-pack-sdlc/` et `packages/orcia-pack-builder/`.
- **CA-15.2.2 (Export d'Espace en Archive `.zip` de Pack)** : `POST /api/v1/packs/export/{workspace_id}` exportant les Agents, Skills, Gates et Workflows sous forme d'archive déclarative `.zip`.

### Story 15.3: Écran `/settings/packs` Simplifié (`PacksRegistryPage.tsx`) & Monitoring Temps Réel des Connecteurs Requis (`TASK-06`)
- **CA-15.3.1 (Registre des Packs Déclaratifs & Healthcheck Connecteurs)** : Affichage des Packs chargés depuis `packs/`, de leur `bundle_sha256`, des compteurs d'objets, du statut `healthcheck()` de leurs `required_connectors` et du bouton d'export `.zip`.

## Epic 16: Orchestration Réflexive (`Mon Assistant`, `Mes Agents` & Processus Pilotés par l'Objectif) et Articulation avec les Processus Pilotés par les Jalons (`specs/epic-16-reflexive-agent-harness/`, `CAP-160`)

Déployer le moteur d'orchestration réflexif `NonDeterministicReflexiveRuntime` (`asyncio` pur + streaming temps réel sans overhead DBOS) pour **Mon Assistant** (2 modes uniques `Standard` / `Approfondi`), **Mes Agents** et les **Processus pilotés par l'objectif (adaptatifs)**, articulé avec les **Processus pilotés par les jalons (étapes garanties)**, les 4 primitives d'exploration chirurgicale par tranches de lignes (`#L1-200`, max `250` lignes sous contrôle RBAC `READ_SOURCE`), le mécanisme *Stateless Suspend/Resume* sur `WritePreviewCard` survivant au `F5`, et les composants `@orcia/ui` `<AgentExecutionTrace />` & `<SourceLineInspectorDrawer />` garantis 100 % sans jargon technique.
**FRs covered:** `FR-1`, `FR-14`, `FR-20`, `FR-22`, `FR-24`, `FR-33`, `FR-36`.

### Story 16.1: Ports Hexagonaux (`SurgicalExplorerPort`) & 4 Primitives d'Exploration Chirurgicale (`packages/orcia-connectors` & `/api/v1/sources/inspect-lines`)
- **CA-16.1.1 (Isolation Hexagonale & 4 Primitives `#Lstart-end`)** : Définition de `SurgicalExplorerPort` dans `orcia_core/ports/` (`0` import `orcia_connectors` dans `orcia_core`, `lint-imports` vert) et implémentation de `SurgicalContextExplorer` (`check_resource_state`, `outline_resource_structure`, `search_workspace_snippets`, `inspect_resource_lines` borné à `250` lignes max avec badges `M↓`, `Y`, `TS`, `PY`, `DOC`).
- **CA-16.1.2 (Sécurité RBAC `READ_SOURCE` Anti-Confused Deputy)** : Vérification systématique de l'appartenance de l'URI à l'Espace/Pack (anti-Path-Traversal & SSRF) et de la permission `READ_SOURCE` via le *Permission Broker* sur `SurgicalContextExplorer` et `GET /api/v1/sources/inspect-lines` (retour d'un descripteur gouverné `redacted` sans fuite de contenu si non habilité).

### Story 16.2: Moteur `NonDeterministicReflexiveRuntime` (`asyncio` pur, Vrai Streaming SSE, 2 Modes `Standard`/`Approfondi` & *Suspend/Resume* `WritePreviewCard` survivant au `F5`)
- **CA-16.2.1 (Boucle Réflexive Sans DBOS & Vrai Streaming SSE)** : Exécution `Think -> Act -> Observe` en `asyncio` pur (zéro écriture dans les tables système DBOS), alignée sur les 2 modes `Standard` (`4` tours / `8 000` tokens) et `Approfondi` (`25` tours / `48 000` tokens), vrai streaming SSE (`thinking_delta`, `token_delta`, événements de trace), séparation `■ Arrêter` vs `Synthétiser maintenant` (`force_final=True`), `max_delegation_depth = 1` sur budget partagé, et archivage final `ClaimCheckStorageService` + événement Outbox.
- **CA-16.2.2 (Stateless Suspend/Resume sur `WritePreviewCard` & Survie au `F5`)** : Sauvegarde légère d'un `ReflexiveSessionSnapshot` (`WAITING_WRITE_PREVIEW`, TTL `24h`) libérant la coroutine ASGI, survie complète au rechargement `F5`, et reprise idempotente après signature humaine `SignedApprovalToken` (`POST /api/v1/executions/{execution_id}/approve-write`).

### Story 16.3: Double Mode dans `Mes Processus` (« Piloté par l'objectif (adaptatif) » vs « Piloté par les jalons (étapes garanties) »), `ProcessExecutionDispatcher` & Packs Déclaratifs
- **CA-16.3.1 (Pré-Refactoring Modulaire & Studio 5 Blocs Sans Jargon Technique)** : Découpage de `WorkflowFiveBlocksCanvas.tsx` en modules `< 350` lignes, sélecteur métier bilingue `fr`/`en` (*Processus piloté par l'objectif (adaptatif)* vs *Processus piloté par les jalons (étapes garanties)*, `0` terme technique en UI ou infobulle `ⓘ`), permutation propre du Bloc 2 sans perte de saisie en brouillon, et badges sur `ProcessesHubPage.tsx`.
- **CA-16.3.2 (Aiguillage `ProcessExecutionDispatcher` & Encapsulation Principe 7)** : Exécution via `NonDeterministicReflexiveRuntime` + `GatePipelineExecutor` (auto-heal 3x) en mode `NON_DETERMINISTIC`, et via `BoundedWorkflowLauncherPort` (`run_bounded_workflow_v2` encapsulant la boucle réflexive dans les sous-étapes `agent_executor`) en mode `DETERMINISTIC_DBOS` ; configuration de `packs/orcia-docs/` en piloté par l'objectif et de `packs/sdlc/` en piloté par les jalons par défaut.

### Story 16.4: Composants `@orcia/ui` `<AgentExecutionTrace />` & `<SourceLineInspectorDrawer />` et Intégration Bout-en-Bout (`Mon Assistant`, `Mes Agents`, `Mes Processus`)
- **CA-16.4.1 (Composants Purs `@orcia/ui` & Zéro Jargon)** : `<AgentExecutionTrace />` et `<SourceLineInspectorDrawer />` dans `packages/ui` (`tokens.css`, `<OrciaIcon />`, Radix `Dialog`/`Sheet` fermable par `Échap`, parité `fr.ts`/`en.ts`, test CI anti-jargon technique, action `Synthétiser maintenant` distincte de `■ Arrêter`, état gouverné `🔒 Extrait protégé`).
- **CA-16.4.2 (Unification Bout-en-Bout & Validation E2E)** : Fusion sans doublon dans `Mon Assistant` (`/assistant`, relié aux pastilles `[S1]`), intégration dans le Banc de Test de `Mes Agents` (`/agents`) et dans `InteractiveRunDrawer.tsx` de `Mes Processus` (`/processes`), promotion de `CAP-160` en `status: live` (`verification: runtime`) et validation Playwright E2E multi-viewports.

---

## Epic 17: Refonte de la Gouvernance IAM par Délégation Hiérarchique, Organigramme en Modales, Annuaire des Comptes & `Mon Compte`, Connecteurs Socle vs Sources `Passthrough` et Coquille `@orcia/ui`

Corriger intégralement les failles d'ergonomie, de modélisation organisationnelle et de gouvernance RBAC de l'écran `Configuration` (`/settings`) et de la coquille Direction C (`@orcia/ui`) : (1) assainir le Design System `@orcia/ui` (reset CSS `<button>`, icônes SVG filaires monochromes unifiées, repli de la Sidebar aligné avec `<kbd>[</kbd>`, bouton `.orcia-ds-btn-danger` rouge sémantique) et structurer `/settings` en **5 onglets adaptatifs** (`Organisation`, `Comptes & Habilitations`, `Modèles IA`, `Connecteurs & SSO`, `Packs Métiers`) protégés par une évaluation réelle des droits ; (2) refondre l'onglet `Organisation` en véritable arbre visuel indenté (`Direction / BU -> Pôle -> Équipe`) éditable en **Modales** sans contrôles personnels égarés ; (3) doter `Comptes & Habilitations` d'un **Annuaire des Comptes** affichant dès le Jour 0 l'administrateur initial (`PLATFORM_ADMIN + SECOPS`), d'une **Matrice à 6 Rôles Délégués** (`PLATFORM_ADMIN`, `SECOPS`, `BU_LEAD`, `TEAM_LEAD`, `CONTRIBUTOR`, `OBSERVER`) sans case toxique `« Lire / Voir les secrets »` (secrets 100 % Write-Only `AD-21`), et d'un tiroir d'exceptions/isolation réservé `SECOPS` ; (4) séparer strictement `Connecteurs & SSO` (Socle) de `Mes Espaces › Sources`, enrichir `👤 Mon Compte` (`Passthrough` 1 fois par connecteur d'entreprise pour que le nom de l'utilisateur apparaisse dans Jira/Git) et ajouter le repli d'indexation RAG sur un **Membre référent de l'équipe** en l'absence de compte de service.

### Story 17.1: Coquille `@orcia/ui` Direction C (Reset CSS `<button>`, Icônes SVG Filaires Monochromes, Repli Sidebar) & Navigation `/settings` à 5 Onglets Adaptatifs sous Garde RBAC Réelle
- **CA-17.1.1 (Reset CSS `<button>`, Harmonisation Sidebar & `.orcia-ds-btn-danger`)** : Suppression des bordures noires User-Agent sur `FourZoneDirectionCShell.tsx` via `tokens.css`, alignement visuel de `Documentation` avec les 8 entrées du menu, et classe `.orcia-ds-btn-danger` (`--color-stale-crimson` `#DC2626`).
- **CA-17.1.2 (Jeu d'Icônes SVG Filaires Monochromes & Bouton Repli Sidebar)** : Rendu SVG filaire monochrome `16px` (`stroke="currentColor"`) unifié dans `<OrciaIcon />` (`iconRegistry.ts`) sans mélange d'émojis polychromes dans la Sidebar ni les onglets, et refonte du bouton de repli en en-tête de Sidebar avec badge `<kbd>[</kbd>` monospace (zéro caractère corrompu `([)`).
- **CA-17.1.3 (5 Onglets Adaptatifs `/settings` & Garde RBAC Réelle)** : Remplacement des 6 onglets (retrait des doublons `Atelier de Processus` et `📖 Glossaire & Règles` d'espace) par 5 onglets adaptatifs (`Organisation`, `Comptes & Habilitations`, `Modèles IA`, `Connecteurs & SSO`, `Packs Métiers`), sous-titre aligné, pluralisation `i18n` propre (zéro `(s)` brut), évaluation réelle des droits par rôle (`PLATFORM_ADMIN` / `SECOPS` complets, `BU_LEAD` / `TEAM_LEAD` scopés sur `Organisation` et `Comptes & Habilitations`, `OBSERVER` en lecture seule / verrouillé), et libellé dynamique de rôle + entrée `Mon Compte` dans `ShellContainer.tsx`.

### Story 17.2: Organigramme Hiérarchique Visuel Indenté (`BU -> Pôle -> Équipe`), Modales d'Édition / Rattachement / Membres & Suppression Sécurisée
- **CA-17.2.1 (Arbre Indenté Multi-Niveaux & Choix de Parent Universel)** : Sélection de l'unité parente disponible aussi bien pour une sous-BU / Pôle que pour une Équipe (rattachée par défaut à la première BU existante), affichage de l'arbre indenté avec compteurs accordés (`membre(s)`, `espace(s)` rattachés) et distinction explicite `Équipe` (collectif humain & imputation FinOps) vs `Espace` (solution applicative dans `Mes Espaces`).
- **CA-17.2.2 (Modales Dédiées RGAA & Persistance PostgreSQL 18)** : Création, renommage, changement d'unité parente (`PATCH /api/v1/org-units/{id}`) et gestion du Responsable (`BU_LEAD` / `TEAM_LEAD`) & des Membres dans des modales dédiées conformes `DESIGN.md` (zéro placeholder coupé, retrait complet de `Retirer mon rattachement` et du badge personnel hors de l'admin globale).
- **CA-17.2.3 (Suppression Sécurisée `.orcia-ds-btn-danger`)** : Bouton de suppression rouge sémantique avec modale de confirmation signalant la facturation active et blocage explicite (`HTTP 409`) si des sous-unités ou espaces y sont encore rattachés.

### Story 17.3: Annuaire des Comptes dès le Jour 0, Modèle Simplifié à 6 Rôles Délégués (`PLATFORM_ADMIN`, `SECOPS`, `BU_LEAD`, `TEAM_LEAD`, `CONTRIBUTOR`, `OBSERVER`), Suppression de « Lire / Voir les secrets » & Tiroir d'Isolation `SECOPS`
- **CA-17.3.1 (Annuaire des Comptes & Anti-Lockout PostgreSQL 18)** : Persistance verticale (`GET/POST/PATCH/DELETE /api/v1/settings/iam/accounts`) affichant dès le Jour 0 le compte administrateur initial avec cumul par défaut `PLATFORM_ADMIN + SECOPS`, création/invitation d'utilisateurs locaux/OIDC et de `Comptes de service`, rattachement aux équipes, et invariant anti-lockout (`HTTP 422 ERR_ADMIN_LOCKOUT_PREVENTED` sur le dernier `PLATFORM_ADMIN`).
- **CA-17.3.2 (Matrice des 6 Rôles Délégués & Éradication de « Lire / Voir les secrets »)** : Remplacement de l'éditeur manuel à 6 cases par la matrice claire des 6 rôles natifs (`HierarchicalRbacService` enrichi de `BU_LEAD`), garantie `SecretStatus` 100 % Write-Only (`AD-21`, aucun rôle ne voit un secret en clair) et séparation de `Consulter` vis-à-vis de l'administration des connecteurs.
- **CA-17.3.3 (Tiroir Replié d'Exceptions & Isolation Réservé `SECOPS`)** : Sélecteurs fermés liés aux rôles/comptes réels (zéro saisie texte libre `TEAM_LEAD`), périmètre restreint par défaut (alerte sur `Plateforme entière`), exclusion de `grant` de toute sélection groupée, et bouton de validation positionné en bas à droite du formulaire.

### Story 17.4: Onglet `Connecteurs & SSO` (Socle), Enrichissement de `👤 Mon Compte` (`Passthrough` par Connecteur) & Synchronisation RAG dans `Mes Espaces › Sources` avec Repli sur Membre Référent
- **CA-17.4.1 (Registre Socle `Connecteurs & SSO` sans Pollution d'Espace)** : Persistance dédiée (`/api/v1/settings/connectors`) des instances d'entreprise (`GitLab`, `Jira`, `Confluence`, `SSO OIDC`) avec validation anti-SSRF et `SecretStatus` Write-Only persisté en PostgreSQL 18, sans jamais créer de source parasite dans `workspaces[0]`.
- **CA-17.4.2 (`👤 Mon Compte` Complet & `Passthrough` 1 Fois par Outil)** : Affichage dans `UserSettingsModalTabs` du profil réel, des rôles et des équipes de facturation en lecture, et gestion dans `Mes Connexions Outils` d'un jeton personnel chiffré `AES-256-GCM` par Connecteur d'entreprise (garantissant que le nom de l'utilisateur apparaît comme auteur dans Jira/Git), complété par une bannière douce *Cold-Start* 1-clic dans `Mes Espaces`.
- **CA-17.4.3 (Synchronisation RAG avec Repli sur Membre Référent)** : Dans `Mes Espaces › Sources`, choix explicite de l'identité de synchronisation d'indexation lecture seule entre `Compte de service` et `Membre référent de l'équipe` (fallback pilote passant en `🟠 Synchronisation en pause — Référent à renouveler` si le référent quitte l'équipe ou n'a plus de jeton actif, avec vérification `Passthrough` du lecteur courant maintenue sur `[S1]`).

### Story 17.5: Refonte du Hub des Modèles IA (`/settings/ai-models` & onglet `Modèles IA`) — Table de Supervision Santé, Modales `OrciaDialog`, Chiffrement `AES-256-GCM` (`SecretStatus` + `masked_hint` 3–4 car.) & Garde de Suppression / Drainage
- **CA-17.5.1 (Table Maîtresse Pleine Largeur, Route `/settings/ai-models` & Garde RBAC 6 Verbes)** :
  - **Given** un utilisateur sur `/settings/ai-models` ou `/settings?tab=models` **When** la page est affichée **Then** aucun formulaire d'ajout permanent n'est visible en pleine page, un récapitulatif de couverture des 4 tiers (`Simple`, `Standard`, `Approfondi`, `Automatique`) et un tableau plein largeur présentent les modèles avec statut de santé (`OPERATIONAL | DEGRADED | ERROR | UNTESTED`), latence (`ms`), dernière vérification et empreinte d'authentification (ou Empty-State didactique si `0` modèle), **And** le bouton `+ Connecter un modèle` ainsi que les actions de mutation sont protégés par `<PermissionGuard>` sur les 6 verbes (`create`, `update`, `delete`, `execute`) et rejettent `READ_ONLY_OBSERVER` avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`.
- **CA-17.5.2 (Modale `OrciaDialog`, Tuiles Fournisseurs & Chiffrement Réel `AES-256-GCM` avec `masked_hint` `AD-21.3`)** :
  - **Given** un clic sur `+ Connecter un modèle`, `Modifier` ou `Remplacer la clé` **When** la modale centrée `OrciaDialog` s'ouvre **Then** elle propose en création des tuiles radio fournisseurs (`Anthropic`, `OpenAI`, `Mistral`, `Google Gemini` avec sélecteur `/v1beta` vs `/v1beta/openai`, `Ollama / vLLM`, `Passerelle Custom`), préserve les 3 modes d'authentification (`api_key`, `env_var` avec nom de variable, `none_local`), persiste l'ensemble dans `workspace_llm_tier_mappings` (PostgreSQL 18) via `POST`/`PATCH /api/v1/settings/ai-models/mappings`, **And** chiffre la clé API via `PassthroughVaultCipher` (`AES-256-GCM`) sous contrat Write-Only `<SecretField />` (`keep | set | clear`) retournant uniquement `SecretStatus` (`configured`, `fingerprint` `sha256:<8-hex>`, `masked_hint` `••••••••<3-4 derniers car.>` si `len >= 12`, `updated_at`, `updated_by`) sans jamais ré-exposer le secret en clair.
- **CA-17.5.3 (Test de Connectivité Asynchrone `< 5 s`, Menu `[ ⋮ ]` & Garde Double Workflows / Runs Actifs)** :
  - **Given** un modèle enregistré dans le Hub **When** l'utilisateur clique sur `Tester` (`POST /api/v1/settings/ai-models/mappings/{id}/test`) **Then** le serveur applique la validation anti-SSRF (`422 ERR_UNSAFE_LLM_ENDPOINT_URL`), déchiffre la clé ou lit la variable d'environnement, exécute le test asynchrone non bloquant et persiste `health_status`, `last_tested_at` et `last_latency_ms` en base ; **And when** l'utilisateur ouvre `[ ⋮ ]` (`OrciaDropdownMenu`) et choisit `Supprimer` **Then** une modale `OrciaDialog` interroge `/delete-impact` et bloque la suppression définitive s'il s'agit du dernier modèle actif d'un Tier requis par des workflows publiés (`409 ERR_AI_MODEL_REQUIRED_BY_WORKFLOWS`) ou propose le drainage (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` -> `DRAINING`) si des runs DBOS actifs l'épinglent.

## Epic 18: Refonte Multi-Nature des Sources d'Espace (`/workspaces/$wsId/sources`), Moteur de Fraîcheur Différentiel (`SHA-256` & Sonde `24h`), Contrat d'Outils Normalisé `codegraph-mcp` & Service Souverain `GitNexus`

Découpler rigoureusement les **Connecteurs d'Entreprise** (infrastructure globale administrée une seule fois dans `/settings`) des **Sources d'Espace** (rattachées par chaque équipe dans `/workspaces/$wsId/sources`), prendre en charge leur triple nature réelle (`DOCUMENT_KB` Confluence/docs, `WORK_TRACKER` Jira, `SOURCE_CODE` Git avec indexation AST légère `0 $` LLM + graphe déterministe `GitNexus` activable/désactivable par le Responsable d'espace via `SERVICE_ACCOUNT` ou jeton personnel `WORKSPACE_LEAD_TOKEN`, et `RELATIONAL_SCHEMA` DDL), industrialiser le moteur de fraîcheur (`WEBHOOK_PUSH` via `domain_events_outbox`, court-circuit `SHA-256` *no-op* et sonde légère `24h`), normaliser l'exploration déterministe du code derrière le contrat lecture seule `codegraph-mcp` (`5` outils agnostiques `GitNexus` / `Sourcegraph SCIP` dans `packages/orcia-connectors`), et durcir le sidecar Docker `gitnexus-mcp` monté strictement en lecture seule (`:ro`, réseau interne sans jeton Git) (`FR-17`, `FR-23`, `FR-24`, `FR-34`, `FR-35`, `AD-17`, `AD-19`, `AD-21`).

### Story 18.1: Déport des Sources dans `/workspaces/$wsId/sources`, Filtres Multi-Nature Direction C, Modale `OrciaDialog` & Gouvernance `GitNexus` par Responsable d'Espace

As a Responsable d'Espace (`TEAM_LEAD` / `BU_LEAD`),
I want consulter, filtrer par nature, rattacher en modale centrée `OrciaDialog`, synchroniser manuellement et gouverner l'activation `GitNexus` (avec compte de service ou mon jeton personnel chiffré) des sources directement sous `/workspaces/$wsId/sources`,
So that l'administration globale `/settings` reste strictement dédiée aux connecteurs socle et chaque équipe maîtrise le périmètre et le moteur d'indexation de ses dépôts et bases documentaires (`FR-23`, `FR-34`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** un utilisateur naviguant vers `/workspaces/$wsId/sources` ou `/workspaces/$wsId` (synchronisé avec le sélecteur d'espace et le fil d'Ariane)
**When** la page se charge
**Then** elle affiche les pastilles de filtrage Direction C (`Toutes | Connaissances | Backlog & Tickets | Code & Contrats | Schémas SQL`), l'horodatage de fraîcheur (`last_sync_at`), l'empreinte `fingerprint_hash`, le mode (`WEBHOOK_PUSH` / `POLLING_24H`), un bouton actif `Synchroniser` (`POST /api/v1/workspaces/{ws_id}/datasources/{id}/sync`) et — pour les sources `SOURCE_CODE` — un interrupteur `GitNexus` (`SERVICE_ACCOUNT` vs `WORKSPACE_LEAD_TOKEN`)
**And** dans `/settings`, l'ancien bloc résiduel `register-connector-form` / `datasources-table` est définitivement purgé au profit d'un lien vers `/workspaces/$wsId/sources`.

**Given** un clic sur `+ Rattacher une Source` ou `Modifier`
**When** la modale centrée `OrciaDialog` s'ouvre (laissant visible la Zone 4 d'Aide Contextuelle `340px`)
**Then** elle permet de choisir la `source_nature`, le connecteur homologué, `target_scope`, `target_ref`, `sync_mode`, l'identité de synchro RAG et les options `GitNexus` (`codegraph_enabled`, `codegraph_auth_mode`) ; la mutation rejette `READ_ONLY_OBSERVER` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`) et refuse à un simple `CONTRIBUTOR` d'activer/désactiver `GitNexus` (`HTTP 403 ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED`), tandis que l'état créé/modifié persiste intégralement en PostgreSQL 18 et survit au rechargement `F5`.

### Story 18.2: Moteur de Fraîcheur Différentiel, Webhooks `Outbox`, Court-Circuit `SHA-256`, Sonde `24h` & Cycle de Vie Disque `GitNexus`

As a Développeur ou utilisateur d'Agent IA,
I want que les webhooks entrants validés par HMAC et la sonde légère `24h` réconcilient les index sans recalcul inutile grâce à l'empreinte `SHA-256`, et que le worker d'indexation maintienne ou purge immédiatement le graphe `GitNexus` selon le choix du Responsable d'espace,
So that les réponses et revues d'architecture s'appuient sur des index à jour à coût token nul sur les dépôts inchangés (`0 $` LLM sur `git push` et les week-ends calmes) (`FR-23`, `FR-24`, `AD-12`, `AD-17`).

**Acceptance Criteria:**

**Given** un événement Webhook entrant sur `POST /api/v1/webhooks/datasources/{datasource_id}`
**When** la signature HMAC est vérifiée en temps constant (sinon `HTTP 401 ERR_WEBHOOK_SIGNATURE_INVALID`) et la livraison dédupliquée sur `(datasource_id, delivery_key)` dans `datasource_webhook_deliveries`
**Then** si `remote_fingerprint_sha256` est identique à `fingerprint_hash`, le traitement court-circuite immédiatement en `NO_OP_UNCHANGED` (`0` embedding recalculé) ; sinon l'événement neutre `DatasourceSyncRequested` est publié atomiquement dans `domain_events_outbox` pour `worker-indexing`.

**Given** une source dont le dernier signal remonte à `> 24h` lors de `POST /api/v1/workspaces/{workspace_id}/datasources/reconcile-staleness`
**When** la sonde légère `24h` (`RemoteFingerprintProbePort`, `0 $` LLM) interroge la cible
**Then** un dépôt calme à empreinte inchangée reste `SYNCED` (`last_probe_at` mis à jour), une dérive d'empreinte déclenche `AUTO_HEAL_DELTA_SYNC`, et une source muette/injoignable bascule en `STALE` avec publication de `DatasourceFreshnessEvaluated` ; de plus, l'acteur `codegraph_indexer` utilise `SERVICE_ACCOUNT` ou `WORKSPACE_LEAD_TOKEN` (basculant en `PAUSED_REFERENT_RENEWAL_REQUIRED` si le jeton du responsable expire) et purge immédiatement `${GITNEXUS_STORAGE_ROOT}/{ws_id}/{ds_id}` lorsque `codegraph_enabled` repasse à `false`.

### Story 18.3: Contrat d'Outils Normalisé `codegraph-mcp` Lecture Seule (`5` Outils) & Intégration Workflows de Revue

As a Agent d'Architecture ou *Blind Hunter*,
I want invoquer un contrat normalisé et agnostique `codegraph-mcp` limité en lecture seule aux dépôts `codegraph_enabled` de l'espace courant,
So that l'analyse d'impact et l'exploration de code reposent sur un graphe déterministe et sur des tranches de lignes bornées sans aucun chunking vectoriel naïf ni dérive silencieuse vis-à-vis de `run-lock.json` (`FR-17`, `FR-35`, `AD-19`, `AD-20`).

**Acceptance Criteria:**

**Given** `CodegraphMcpConnector` dans `packages/orcia-connectors` (`5` outils : `codegraph_locate_symbol`, `codegraph_get_call_hierarchy`, `codegraph_find_references`, `codegraph_calculate_blast_radius`, `codegraph_read_span` borné à `<= 250` lignes sans traversée de chemin)
**When** un agent ou le routeur `/api/v1/workspaces/{workspace_id}/codegraph/invoke` appelle un outil
**Then** `workspace_id` est injecté côté serveur (rejet si le dépôt n'est pas `SOURCE_CODE` et `codegraph_enabled = true` dans cet espace), `preview_write`/`execute_write` sont refusés en lecture seule, un écart `indexed_commit_sha != run_lock_commit_sha` émet l'alerte explicite `GRAPH_MOVED_SINCE_RUN_LOCK`, et le fournisseur est interchangeable par configuration (`CODEGRAPH_PROVIDER=gitnexus | sourcegraph_scip`).

**Given** un workflow déclaratif de revue (`packs/sdlc/workflows/wf-03-etude-architecture.yaml`)
**When** l'étape d'étude d'impact s'exécute via `mcp:codegraph` (`scope: read`)
**Then** l'Agent Executor invoque `codegraph_calculate_blast_radius` en respectant l'isolation `lint-imports` (`orcia_core` n'importe jamais `orcia_connectors`) et la cohérence OpenAPI `0-diff`.

### Story 18.4: Infrastructure `docker-compose.yml` (`gitnexus-mcp` Isolé `:ro`), Registre des Capacités (`CAP-180`) & Validation `AD-17` Complète

As a Administrateur Plateforme / Ingénieur DevOps,
I want déployer le sidecar `gitnexus-mcp` dans `infra/docker/docker-compose.yml` avec montage `:ro` d'un volume dédié sur un réseau interne dépourvu de jetons Git et tracer l'ensemble de l'`Epic 18` dans `capabilities.yaml`,
So that l'architecture locale et CI offre un graphe de code souverain, isolé et auditable à `100 %` (`AD-17`, `AD-19`, `NFR-SEC`).

**Acceptance Criteria:**

**Given** `infra/docker/docker-compose.yml` et `.env.example`
**When** la pile est inspectée et testée par les garde-fous d'infrastructure et de sécurité
**Then** `worker-indexing` monte `gitnexus_graphs:/data/graphs` en lecture-écriture (`GITNEXUS_CONTENT_RETENTION=symbol`), tandis que `gitnexus-mcp` (`ghcr.io/abhigyanpatwari/gitnexus:latest`, `mcp --http --port 8095`) monte `gitnexus_graphs:/data/graphs:ro`, tourne sur le réseau `codegraph-internal` (`internal: true`) sans port exposé ni jeton Git, protégé par `ORCIA_CODEGRAPH_INTERNAL_TOKEN` et durcissement conteneur (`read_only: true`, `no-new-privileges: true`), et le chart Helm 9 services est tracé dans `DEVOPS-HELM-01` (`sprint-status.yaml`).

**Given** l'enregistrement de `CAP-180` (et la mise à jour de `CAP-054`/`CAP-080`) dans `docs/product/capabilities.yaml` et des 4 rapports Tech Lead dans `docs/implementation-artifacts/tech-lead-reports/README.md`
**When** toutes les portes CI sont exécutées (`ruff`, `mypy --strict`, `lint-imports`, `lint_spine.py`, `export_openapi.py --check`, `pytest --cov-fail-under=90` + intégration PG18, `pnpm turbo run lint typecheck test`, `pnpm site:sync`, `pnpm site:check`)
**Then** toutes les vérifications passent à `0` erreur sans contournement.

---

## Epic 19: Hub Modèles IA Fiable, Découverte 0 Token, Test Réel & Embeddings Sémantiques (AD-24)

Éliminer toute illusion d'opérationnalité des modèles IA en découvrant automatiquement les modèles disponibles sans token dépensé (`0 $`), en assainissant la modale UI (placeholders dynamiques contextuels sans puces codées en dur trompeuses), en exécutant des tests de connectivité réels (chat `max_tokens=1` et validation stricte dimension 1024 pour embeddings) avec mesure réelle de la latence et restitution fine des erreurs HTTP RFC 9457, en purgeant intégralement le backend et l'amorçage Jour 0 de tout nom de modèle propriétaire codé en dur, en intégrant le rôle d'embedding dans le Hub avec un modèle unique GLOBAL, en remplaçant définitivement le hachage SHA-256 en production par de vrais embeddings vectoriels via `EmbeddingPort` HTTPX avec blocage explicite de toute indexation (ni chunks ni BM25) et de l'Assistant sans modèle actif (`ERR_NO_ACTIVE_EMBEDDING_MODEL`), en assurant une réindexation idempotente bloquante avec blocage total de la recherche RAG (HTTP 503 RFC 9457 `ERR_RAG_REINDEX_IN_PROGRESS` avec progression, zéro repli lexical dégradé), blocage complet de Mon Assistant (bannière avec % et saisie désactivée) et mise en file d'attente des nouvelles ingestions, et en maintenant strictement le Codegraph GitNexus à 0 token hors du périmètre des embeddings (`AD-8`, `AD-10`, `AD-16`, `AD-24`, `CAP-190`, `FR-14`, `FR-18`, `FR-23`, `FR-28`, `FR-31`, `FR-33`).

### Story 19.1: Modale UI Connecter un Modèle — Champs Vides, Placeholders Dynamiques par Fournisseur & Suppression des Puces Codées en Dur (D1)

As a Administrateur Plateforme / Responsable IA (`Karim UJ-9`),
I want que la modale d'ajout/modification d'un modèle démarre avec des champs textuels entièrement vides, des placeholders contextuels adaptés au fournisseur sélectionné, et sans aucune puce de suggestions codées en dur,
So that l'interface ne suggère jamais de modèles potentiellement absents de l'infrastructure de l'entreprise et force une configuration explicite ou issue d'une découverte dynamique (`AD-24.1`, `FR-31`, `UX-DR1`, `UX-DR2`).

**Dépendances :** Aucune (frontend autonome, mockable).
**Références :** `AD-24.1`, `FR-31`, `UX-DR1`, `UX-DR2`.
**Fichiers impactés connus :** `apps/web/src/features/settings/components/AiModelModal.tsx`, `apps/web/src/features/settings/components/AiModelForm.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`.
**Tests existants à adapter :** `apps/web/src/features/settings/__tests__/AiModelModal.test.tsx`, `tests/unit/test_codebase_architectural_anti_patterns_audit.py`.

**Acceptance Criteria:**

**Given** la modale `AiModelModal` (`OrciaDialog`) ouverte lors d'un clic sur `+ Connecter un modèle`
**When** l'utilisateur observe l'état initial des champs
**Then** les champs `model_name` et `base_url` sont strictement vides (`value === ""` sans pré-remplissage résiduel ni valeur par défaut cachée), et aucune puce de modèle codée en dur (`gpt-4o`, `claude-3-5-sonnet`, `mistral-large`, `nomic-embed-text`) n'est affichée dans le DOM (`AD-24.1`).

**Given** la sélection successive des tuiles radio de fournisseurs (`Ollama / vLLM`, `Mistral`, `OpenAI`, `Anthropic`, `Google Gemini`, `Custom OpenAI-compatible`)
**When** l'utilisateur commute de fournisseur
**Then** les placeholders des champs `base_url` et `model_name` s'adaptent dynamiquement (ex. Ollama : `http://localhost:11434` / `llama3.2:latest`, OpenAI : `https://api.openai.com/v1` / `gpt-4o-mini`, Custom : `https://mon-llm-interne.corp/v1`), tandis que les libellés et microcopies proviennent du dictionnaire typé `i18n` (zéro texte français en dur dans le JSX).

**Given** les 5 couches de validation `AD-17`
**When** les suites de tests sont exécutées
**Then** Couche 1 (Vitest) teste le changement de fournisseur, la vacuité initiale et l'absence de puces codées en dur ; Couche 3 valide le contrat OpenAPI 3.1 `0-diff` ; Couche 5 (Playwright) vérifie le montage accessible et l'absence de régression visuelle (`zero-dead-buttons-and-silent-catches-audit.test.tsx`).

---

### Story 19.2: Découverte Dynamique des Modèles 0 Token (`GET /models`), Combobox Filtrable & Saisie Libre (D2)

As a Administrateur Plateforme (`Karim UJ-9`),
I want que le Hub interroge automatiquement les métadonnées du fournisseur pour lister les modèles réels disponibles sans consommer de tokens d'inférence (`0 $`), et m'offre une combobox filtrable avec saisie libre,
So that je puisse sélectionner immédiatement un modèle vérifié sur mon instance locale ou distante sans risque d'erreur de frappe (`AD-24.2`, `FR-31`, `NFR-PERF-1`, `NFR-OBS-1`).

**Dépendances :** Indépendante du backend d'embedding (nécessite l'endpoint de découverte côté `apps/api` et le composant combobox côté `apps/web`).
**Références :** `AD-24.2`, `FR-31`, `NFR-PERF-1`, `NFR-OBS-1`.
**Fichiers impactés connus :** `apps/api/src/orcia_api/routers/ai_models.py`, `apps/api/src/orcia_api/schemas/ai_models.py`, `packages/orcia-core/src/orcia_core/llm/discovery.py`, `apps/web/src/features/settings/components/AiModelDiscoveryCombobox.tsx`.
**Tests existants à adapter :** `tests/unit/test_ai_models_router.py`, `apps/web/src/features/settings/__tests__/AiModelModal.test.tsx`.

**Acceptance Criteria:**

**Given** une URL et/ou une clé API renseignée pour un fournisseur (`Ollama`, `Mistral`, `OpenAI`, `Anthropic`, `vLLM` ou compatible)
**When** le bouton ou déclencheur de découverte `Découvrir les modèles` est sollicité (`GET /api/v1/settings/ai-models/discover?provider={provider}&base_url={url}`)
**Then** l'API backend effectue un appel réseau asynchrone non bloquant (`httpx.AsyncClient`) vers l'endpoint standard de métadonnées du fournisseur (`GET /api/tags` pour Ollama, `GET /v1/models` pour OpenAI/Mistral/vLLM) sans envoyer aucun prompt d'inférence (`0 token LLM consommé`, coût `0 $`), avec un timeout strict de `3 000 ms` et validation anti-SSRF (`is_safe_llm_endpoint_url`).

**Given** la réponse réussie du endpoint de découverte
**When** la liste des modèles est retournée au frontend
**Then** le champ `model_name` se transforme en combobox filtrable avec recherche textuelle instantanée, affichant les identifiants réels retournés (avec badge ou tag de contexte si disponible), tout en préservant la possibilité de saisie libre d'un identifiant non listé (mode fallback si l'endpoint `/models` est restreint).

**Given** un échec réseau ou un refus d'accès du endpoint de découverte (ex. proxy d'entreprise bloquant `GET /models` ou clé sans droit de lecture des métadonnées)
**When** la requête de découverte échoue
**Then** une notification non bloquante informe l'utilisateur sans bloquer le formulaire, et le champ `model_name` bascule en saisie libre standard sans perte des données déjà saisies.

---

### Story 19.3: Test de Connexion Réel Chat (`max_tokens=1`) & Embeddings (Validation Dim 1024), Latence Réelle & Erreurs RFC 9457 (D3)

As a Administrateur Plateforme / Responsable IA (`Karim UJ-9`),
I want tester la connectivité réelle de chaque modèle avec un appel minimal vérifié (chat `max_tokens=1` ou embedding sur chaîne test avec contrôle de dimension 1024), mesurer la latence aller-retour réelle et recevoir un diagnostic d'erreur RFC 9457 précis en cas d'échec,
So that aucun modèle étiqueté « Opérationnel » ne soit en réalité muet, bridé ou mal dimensionné (`AD-24.3`, `FR-14`, `FR-18`, `FR-31`, `NFR-OBS-1`, `NFR-TEST-1`).

**Dépendances :** Dépend de Story 19.5 pour la validation des modèles d'embedding via `EmbeddingPort`.
**Références :** `AD-24.3`, `FR-14`, `FR-18`, `FR-31`, `NFR-OBS-1`.
**Fichiers impactés connus :** `apps/api/src/orcia_api/routers/ai_models.py`, `packages/orcia-core/src/orcia_core/llm/connection_test.py`, `packages/orcia-core/src/orcia_core/llm/errors.py`, `apps/web/src/features/settings/components/AiModelConnectionTestButton.tsx`.
**Tests existants à adapter :** `tests/unit/test_ai_model_connection_test.py`, `tests/integration/test_ai_models_api_pg18.py`.

**Acceptance Criteria:**

**Given** un modèle de type chat / raisonnement enregistré ou en cours de saisie
**When** l'utilisateur déclenche le test de connexion (`POST /api/v1/settings/ai-models/mappings/{id}/test` ou `POST /test-connection`)
**Then** le backend envoie une requête réelle d'inférence minimale (`max_tokens=1`, prompt `"ping"`) via `httpx.AsyncClient` non bloquant, mesure le temps aller-retour précis en millisecondes (`latency_ms`), et valide le statut `OPERATIONAL` uniquement si le statut HTTP est 200 et qu'un token valide est retourné.

**Given** un modèle avec l'usage `embedding` (cf. Story 19.5)
**When** l'utilisateur déclenche son test de connexion
**Then** le backend soumet une chaîne test (`"orcia connection test"`) à l'API d'embeddings via `EmbeddingPort`, vérifie que le vecteur retourné contient exactement **1024 dimensions** de type flottant fini (`len(vector) == 1024` et tous nombres finis), et rejette avec `HTTP 422 ERR_EMBEDDING_DIMENSION_MISMATCH` si la dimension diffère de 1024 (ex. 768 ou 1536) en indiquant la dimension constatée et la dimension requise.

**Given** une erreur lors du test de connexion (authentification 401/403, modèle introuvable 404, rate limit 429, timeout ou URL inaccessible)
**When** le test échoue
**Then** l'API retourne une enveloppe **RFC 9457 Problem Details** enrichie (`error_code`, `status`, `detail`, `remediation_hint`, `raw_provider_status`, `trace_id`), sans masquer l'erreur dans un faux `200 OK`, et le Hub affiche le statut `ERROR` avec l'explication exploitable dans l'UI.

---

### Story 19.4: Suppression Intégrale des Noms de Modèles en Dur Backend, Tier Mappings Vides & Amorçage Jour 0 Propre (D4)

As a Développeur / Ingénieur Plateforme (`Karim UJ-9`),
I want que le backend, les constantes, les scripts de seed et l'amorçage Jour 0 soient intégralement purgés de tout nom de modèle propriétaire codé en dur et que les tier mappings soient initialisés vides,
So that ORCIA démarre dans un état neutre, souverain et gouverné, sans présumer des abonnements ou modèles disponibles dans l'infrastructure de déploiement (`AD-24.4`, `FR-28`, `FR-31`, `NFR-ISO-1`).

**Dépendances :** Aucune (backend / seeds autonome).
**Références :** `AD-24.4`, `FR-28`, `FR-31`.
**Fichiers impactés connus :** `packages/orcia-core/src/orcia_core/llm/constants.py`, `packages/orcia-core/src/orcia_core/llm/service.py`, `packages/orcia-core/src/orcia_core/bootstrap/seeder.py`, `infra/scripts/maintenance/09_reset_db_first_boot.py`, `apps/api/src/orcia_api/routers/ai_models.py`.
**Tests existants à adapter :** `tests/unit/test_ai_models_seeds.py`, `tests/integration/test_reset_db_first_boot.py`, `tests/unit/test_codebase_architectural_anti_patterns_audit.py`.

**Acceptance Criteria:**

**Given** le code source de `packages/orcia-core` et `apps/api`
**When** une recherche globale (grep / audit statique) est exécutée sur les constantes de seed
**Then** `DEFAULT_LLM_MODEL_ENDPOINT_SEEDS` et `build_default_tier_mappings` ne contiennent plus aucun nom de modèle propriétaire en dur (`gpt-4o`, `claude-3-5-sonnet`, `mistral-large`, `nomic-embed-text`), et toute valeur codée en dur est remplacée par des structures vides ou des gabarits configurables (`AD-24.4`).

**Given** une réinitialisation Jour 0 de la base de données via `pnpm db:reset` (`09_reset_db_first_boot.py --apply`)
**When** l'état initial des tables de modèles et de tiers est vérifié par `SELECT` SQL
**Then** la table `workspace_llm_tier_mappings` est initialisée avec `0` mapping ou des mappings non assignés (`model_id IS NULL`), et l'état Jour 0 est préservé sans injection de modèles fantômes.

**Given** un premier démarrage ou une réinitialisation Jour 0 via `pnpm db:reset` (`09_reset_db_first_boot.py --apply`)
**When** l'administrateur se connecte et accède à la plateforme ou au Cockpit
**Then** le wizard d'accueil / parcours d'onboarding Jour 0 guide explicitement l'administrateur vers la configuration obligatoire du modèle d'embedding dans `/settings/ai-models`, et Mon Assistant affiche d'emblée une bannière d'avertissement persistante avec désactivation complète de la zone de saisie et de tout envoi de message tant qu'aucun modèle d'embedding n'a été configuré et validé (`AD-16`, `AD-24.6`).

**Given** une tentative d'invocation d'un tier ou d'un workflow alors qu'aucun modèle n'est mappé
**When** le moteur LLM tente de résoudre le modèle pour un tier donné
**Then** il lève immédiatement `ERR_TIER_MODEL_NOT_CONFIGURED` avec une enveloppe RFC 9457 guidant l'utilisateur vers `/settings/ai-models` pour configurer le modèle manquant, sans tentative d'appel silencieux vers des endpoints inexistants.

---

### Story 19.5: Usage Embedding dans le Hub des Modèles, Port Hexagonal `EmbeddingPort` & Adaptateurs HTTPX (D5, D6)

As a Tech Lead / Architecte (`Winston`),
I want déclarer le rôle `embedding` dans le Hub des modèles IA, imposer la sélection d'un **modèle d'embedding unique GLOBAL** pour l'instance, et router les requêtes via un port hexagonal découplé `EmbeddingPort` avec adaptateurs HTTPX,
So that la génération de vecteurs sémantiques repose sur une interface standardisée sans aucun SDK vendeur ni couplage propriétaire (`AD-8`, `AD-24.5`, `AD-24.6`, `FR-23`, `FR-31`).

**Dépendances :** Précède Story 19.3 (partie embedding), Story 19.6 et Story 19.7.
**Références :** `AD-8`, `AD-24.5`, `AD-24.6`, `FR-23`, `FR-31`, `AD-19`.
**Fichiers impactés connus :** `packages/orcia-kernel/src/orcia_kernel/ports.py` (ou `packages/orcia-core/src/orcia_core/rag/ports.py`), `packages/orcia-core/src/orcia_core/rag/adapters/embedding_httpx.py`, `apps/api/src/orcia_api/schemas/ai_models.py`, `packages/orcia-core/src/orcia_core/llm/models.py`.
**Tests existants à adapter :** `tests/unit/test_embedding_port.py`, `tests/unit/test_ai_models_schemas.py`.

**Acceptance Criteria:**

**Given** la gestion des modèles dans `/settings/ai-models`
**When** un modèle est configuré ou modifié
**Then** un sélecteur d'usage permet de déclarer son rôle : `chat_reasoning`, `embedding`, ou `both` ; et un indicateur strict `is_primary_embedding: true` garantit qu'exactement **un seul modèle d'embedding actif** est désigné au niveau GLOBAL de l'instance ORCIA (`AD-24.5`). Si un nouveau modèle est désigné comme primaire, l'ancien est automatiquement basculé en inactif pour l'embedding.

**Given** le contrat hexagonal `EmbeddingPort`
**When** un appel `embed_texts(texts: list[str]) -> list[list[float]]` ou `embed_query(query: str) -> list[float]` est exécuté
**Then** l'appel passe par un adaptateur HTTPX (`HttpxEmbeddingAdapter`) sans aucun SDK tiers (`openai`, `anthropic`, `litellm`), couvrant nativement :
- `gemini_native` via `:batchEmbedContents` avec le paramètre obligatoire `output_dimensionality=1024` ;
- `openai_compatible` via `/v1/embeddings` avec transmission de `dimensions=1024` lorsque supporté par le modèle (OpenAI `text-embedding-3`, TEI, vLLM) ;
- Ollama en privilégiant son endpoint standard compatible OpenAI `/v1/embeddings` ou natif `/api/embed` (l'ancien endpoint `/api/embeddings` déprécié étant formellement banni) ;
- et excluant formellement le fournisseur `Anthropic` qui n'offre aucune API native d'embeddings ;
tout en vérifiant rigoureusement que la dimension de chaque vecteur retourné est exactement de 1024 (rejet par `ERR_EMBEDDING_DIMENSION_MISMATCH` sinon) et en levant `ERR_EMBEDDING_GENERATION_FAILED` en cas d'erreur réseau HTTP (`AD-24.4`, `AD-24.6`).

**Given** la vérification architecturale `lint-imports`
**When** l'ordonnancement des dépendances est audité
**Then** `EmbeddingPort` réside dans le noyau hexagonal sans aucune importation vers `fastapi`, `sqlalchemy` ou des SDK externes, respectant strictement `AD-19`.

---

### Story 19.6: Migration Alembic, Suppression Intégrale du Hachage SHA-256 en Prod & Blocage sans Modèle (D7, D8, D10, D11)

As a Tech Lead / Développeur Backend (`Amelia`),
I want exécuter la migration de schéma Alembic, supprimer définitivement tout repli sur le pseudo-hachage SHA-256 en runtime de production, et bloquer immédiatement toute indexation de source si aucun modèle d'embedding n'est configuré,
So that le RAG d'ORCIA ne stocke plus jamais de vecteurs factices et garantisse une sémantique vectorielle réelle de bout en bout (`AD-8`, `AD-24.7`, `AD-24.8`, `AD-24.10`, `AD-24.11`, `FR-23`).

**Dépendances :** Dépend de Story 19.5 (`EmbeddingPort` requis). Précède Story 19.7.
**Références :** `AD-8`, `AD-24.7`, `AD-24.8`, `AD-24.10`, `AD-24.11`, `FR-23`.
**Fichiers impactés connus :** `infra/migrations/versions/0019_add_embedding_model_metadata.py`, `packages/orcia-core/src/orcia_core/rag/service.py`, `packages/orcia-core/src/orcia_core/rag/indexer.py`, `packages/orcia-core/src/orcia_core/rag/vector.py` (ou suppression de `compute_deterministic_halfvec_1024` vers `tests/unit/fakes/`).
**Tests existants à adapter :** `tests/unit/test_rag_service.py`, `tests/unit/test_differentiated_indexer.py`, `tests/integration/test_rag_pipeline_pg18.py`.

**Acceptance Criteria:**

**Given** la migration Alembic `0019` (ou numéro séquentiel suivant)
**When** la migration est appliquée via `.venv/bin/alembic upgrade head`
**Then** elle ajoute les colonnes de métadonnées de traçabilité d'embedding sur `kb_chunks` (`embedding_model_id UUID REFERENCES workspace_llm_tier_mappings(id)`, `embedding_generated_at TIMESTAMP`) avec clauses `upgrade()` et `downgrade()` testées sous PostgreSQL 18 `testcontainers` (`AD-24.7`).

**Given** le runtime de production de `packages/orcia-core/rag`
**When** l'indexeur différentiel traite des documents ou chunks
**Then** la fonction de pseudo-hachage `compute_deterministic_halfvec_1024` est totalement éliminée du code applicatif de production et déplacée exclusivement sous `tests/unit/fakes/fake_embeddings.py` pour les tests unitaires hors ligne (`AD-24.8`).

**Given** une source documentaire dont l'indexation est déclenchée alors qu'aucun modèle d'embedding n'est configuré ou validé (`is_primary_embedding = true` absent, que ce soit au Jour 0 après `pnpm db:reset` ou suite à la suppression d'un modèle)
**When** `DifferentiatedIncrementalIndexer` ou `POST /api/v1/workspaces/{ws_id}/datasources/{id}/sync` s'exécute
**Then** l'ingestion est totalement bloquée avec émission de l'erreur harmonisée `HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL` (aucun chunk n'est inséré dans `kb_chunks`, aucun index lexical BM25 n'est généré : zéro chunk sans vecteur, zéro corruption d'état), et la source passe en statut `AWAITING_EMBEDDING_MODEL` (`AD-24.6`).

**Given** l'absence de modèle d'embedding actif (`is_primary_embedding = true` absent, au Jour 0 après `pnpm db:reset` ou après suppression/désactivation d'un modèle)
**When** un utilisateur accède à Mon Assistant dans le Cockpit ou soumet une requête de recherche RAG directe
**Then** la recherche RAG retourne immédiatement l'enveloppe RFC 9457 avec le code d'erreur harmonisé `ERR_NO_ACTIVE_EMBEDDING_MODEL`, et Mon Assistant est totalement bloqué : une bannière persistante indique que le modèle d'embedding est manquant avec un lien d'action direct vers `/settings/ai-models`, et le champ d'entrée de texte ainsi que le bouton d'envoi de message sont matériellement désactivés (`disabled = true`, aucun envoi de prompt possible) (`AD-24.6`).

**Given** l'exploration et l'analyse de code via Codegraph / GitNexus
**When** une source `SOURCE_CODE` est synchronisée avec `codegraph_enabled = true`
**Then** GitNexus génère son graphe de symboles déterministe AST de manière souveraine à `0 token LLM`, strictement indépendant du pipeline d'embeddings textuels RAG (`AD-24.11`).

---

### Story 19.7: Réindexation Bloquante Idempotente, Suivi de Progression & Verrouillage Assistant/Recherche (D9, D12)

As a Administrateur Plateforme / Responsable IA (`Karim UJ-9`),
I want déclencher une réindexation globale bloquante et idempotente lors de l'enregistrement ou du changement du modèle d'embedding, suivre sa progression, et verrouiller totalement la recherche vectorielle et l'assistant sans mode dégradé,
So that aucun calcul de similarité cosinus incohérent ne soit exécuté entre des espaces vectoriels de modèles différents (`AD-24.7`, `FR-23`, `FR-31`, `FR-33`).

**Dépendances :** Dépend de Story 19.5 et Story 19.6.
**Références :** `AD-24.7`, `FR-23`, `FR-31`, `FR-33`, `NFR-REL-1`, `NFR-OBS-1`.
**Fichiers impactés connus :** `packages/orcia-core/src/orcia_core/rag/service.py`, `packages/orcia-core/src/orcia_core/rag/reindex.py`, `apps/api/src/orcia_api/routers/rag.py`, `apps/web/src/features/settings/components/AiModelReindexProgressModal.tsx`, `apps/web/src/features/cockpit/components/ChatAssistantInput.tsx`.
**Tests existants à adapter :** `tests/unit/test_rag_reindexing.py`, `tests/integration/test_rag_reindexing_pg18.py`.

**Acceptance Criteria:**

**Given** un changement ou une première configuration du modèle d'embedding principal (`POST /api/v1/settings/ai-models/reindex-embeddings`)
**When** la réindexation est initiée
**Then** elle acquiert un verrou d'indexation exclusif (`ResourceLeasePort` / Redis `lock:rag:reindex`), met à jour le statut global `reindexing_status = IN_PROGRESS`, et recalcule les vecteurs 1024 de tous les `kb_chunks` existants par lots idempotents (`batch_size = 50`), avec mise à jour continue de `progress_percentage`, `processed_chunks` et `total_chunks` (`AD-24.7`).

**Given** une réindexation globale en cours (`reindexing_status == IN_PROGRESS`)
**When** un utilisateur effectue une recherche RAG (`TwoSpeedFederatedSearchService`, recherche `⌘K` ou endpoint API) ou sollicite Mon Assistant (`AssistantHarness`)
**Then** aucun mode dégradé lexical ni repli Vitesse 1 n'est toléré :
- toute recherche RAG est immédiatement rejetée avec le statut **`HTTP 503 Service Unavailable`** au format RFC 9457 Problem Details portant le code **`ERR_RAG_REINDEX_IN_PROGRESS`** et incluant le pourcentage d'avancement (`progress_percentage`) ;
- Mon Assistant est **totalement bloqué** : l'interface affiche une bannière d'indisponibilité bloquante avec la progression en temps réel (`Réindexation sémantique en cours : {progress}%`), et la zone de saisie textuelle ainsi que le bouton d'envoi de message sont matériellement désactivés (`disabled = true`, aucun envoi de prompt possible tant que le recalcul n'est pas terminé) (`AD-24.7`).

**Given** de nouvelles tentatives d'ingestion documentaire pendant la réindexation (`reindexing_status == IN_PROGRESS`)
**When** une synchronisation de datasource ou un webhook Confluence/Jira/Git arrive
**Then** les ingestions documentaires ne sont pas traitées immédiatement mais automatiquement suspendues et placées dans une file d'attente persistante (`rag_reindexing_pending_ingestions`), garantissant qu'aucun calcul vectoriel concurrent ne s'exécute sur l'ancien modèle et que l'ingestion reprendra dès la fin de la réindexation (`AD-24.7`).

**Given** l'achèvement réussi de la réindexation
**When** le dernier lot est persisté
**Then** le verrou est libéré, `reindexing_status` passe à `COMPLETED`, un événement outbox `EmbeddingReindexCompleted` est émis, et la recherche hybride RRF (`halfvec(1024)` HNSW + `tsvector` GIN) redevient immédiatement disponible avec 100 % de vecteurs homogènes générés par le nouveau modèle actif.

**Given** aucun chunk documentaire ni source documentaire à réindexer (total = 0, ex. Jour 0 après `pnpm db:reset`)
**When** un modèle d'embedding est activé ou changé
**Then** le job passe directement à `COMPLETED` (traçé avec `EmbeddingReindexStarted` et `EmbeddingReindexCompleted`, idempotent) SANS phase de blocage visible : aucune réponse 503 `ERR_RAG_REINDEX_IN_PROGRESS`, aucune bannière « Réindexation 0 % », Assistant immédiatement débloqué.

**Given** les 5 couches de validation `AD-17` de l'ensemble de l'Epic 19
**When** toutes les suites de tests et portes de gouvernance sont exécutées
**Then** couverture unitaire $\ge 90\%$ sur `orcia_core/llm` et `orcia_core/rag`, tests d'intégration réels sur PostgreSQL 18 + `pgvector` avec `testcontainers`, contrats OpenAPI 3.1 `0-diff`, cassettes déterministes CI et tests Playwright passent sans aucun warning ni contournement.

---

## Epic 20: Gouvernance Déléguée (« Mon Organisation » & Audit Scopé), Glossaire PG18 & Rôle `ONTOLOGY_LEAD`, Consolidation « Mon Compte » (Style ChatGPT) et Page « Profil »

Corriger les blocages de délégation hiérarchique et les fractures de navigation constatés en exploitation : offrir un menu dédié **« Mon Organisation »** (`/organization`, placé sous `Mes Espaces`) aux `PLATFORM_ADMIN`, `BU_LEAD` (ex. Martin Pecheur) et `TEAM_LEAD` (ex. Pascal Lacdap) avec confinement strict de sous-arbre et invitation IAM scopée (`+ Inviter un utilisateur` sans escalade vers `PLATFORM_ADMIN`/`SECOPS`), filtrer le **Journal d'Activité** (`/activity` & `audit_ledger`) selon le périmètre réel de chaque rôle (incluant `org_unit_id` et suppression de `Plateforme entière` hors `PLATFORM_ADMIN`/`SECOPS`), renommer l'entrée gauche `Aide` en **« Glossaire »** (`/ontology`) adossée à PostgreSQL 18 avec le nouveau 7e rôle officiel **`ONTOLOGY_LEAD`** (désigné par BU) et un circuit de promotion palier par palier (`L4 → L3 → L2 → L1`) doté d'un onglet `Propositions à valider`, supprimer le contrôle de login redondant en haut à droite ainsi que le faux sélecteur `Rôle` au profit d'un popup **« Mon Compte »** consolidé en bas à gauche (style ChatGPT) et d'une modale unifiée **Paramètres** persistée en PostgreSQL 18, et livrer la page dédiée **« Mon Profil »** (`/profile`) affichant identité, rattachements, 4 KPIs de jetons/séries et les agents/processus/outils les plus utilisés alimentés par les tours `Mon Assistant` (`CAP-010`, `CAP-050`, `CAP-051`, `CAP-058`, `CAP-060`, `CAP-063`, `CAP-064`, `CAP-065`, `CAP-067`, `CAP-069`, `FR-8`, `FR-9`, `FR-21`, `FR-25`, `FR-31`, `FR-32`).

### Story 20.1: Menu « Mon Organisation » (`/organization`), Délégation `BU_LEAD` / `TEAM_LEAD`, Invitation IAM Scopée & Journal d'Activité Filtré par Périmètre

As a Responsable de Direction (`BU_LEAD`), Responsable d'Équipe (`TEAM_LEAD`) ou Administrateur Plateforme (`PLATFORM_ADMIN`),
I want gérer directement l'organigramme, les sous-BUs, les équipes, les co-responsables, les référents glossaire et l'invitation d'utilisateurs depuis un menu dédié « Mon Organisation » sous « Mes Espaces », et consulter un Journal d'Activité strictement filtré sur mon périmètre autorisé,
So that chaque responsable administre son périmètre en autonomie sans être bloqué sur `/settings` ni voir d'événements hors de ses droits (`FR-21`, `FR-25`, `FR-31`, `FR-32`, `IAM-ORG-DELEGATION-01`).

**Acceptance Criteria:**

**Given** un utilisateur connecté avec rôle `PLATFORM_ADMIN`, `BU_LEAD` (ex. Martin Pecheur) ou `TEAM_LEAD` (ex. Pascal Lacdap)
**When** il observe la barre latérale gauche et navigue vers `/organization`
**Then** l'entrée **« Mon Organisation »** apparaît juste sous « Mes Espaces » (tandis que l'onglet `organisation` est retiré de `/settings`, qui conserve 5 onglets : `iam`, `authentication`, `models`, `connectors`, `packs`) ; le `BU_LEAD` peut créer des sous-BUs et équipes dans son sous-arbre, modifier ses unités dirigées (co-responsables `lead_user_ids`, référents glossaire `ontology_lead_user_ids`), supprimer uniquement ses unités enfants (rejet `403 ERR_ORG_UNIT_ROOT_DELETE_FORBIDDEN` sur sa BU racine dirigée) et inviter un compte humain dans son sous-arbre via `POST /api/v1/org-units/invite-user` (rejet `403` sur `PLATFORM_ADMIN` / `SECOPS` / hors sous-arbre) ; le `TEAM_LEAD` peut modifier le nom, les co-responsables et les membres de ses seules équipes (sans créer ni supprimer d'unité).

**Given** les mutations d'organisation et d'accounts IAM (`ORG_UNIT_*`, `IAM_ACCOUNT_*`) ainsi que la consultation de `/activity`
**When** un utilisateur liste le Journal d'Activité via `GET /api/v1/audit/ledger` ou ouvre `/activity`
**Then** les mutations sont journalisées dans `audit_ledger` avec `org_unit_id`, `PLATFORM_ADMIN`/`SECOPS` conservent l'accès global (`Plateforme entière`), `BU_LEAD` accède aux événements de ses BUs/sous-BUs/équipes/espaces (y compris `workspace_id IS NULL AND org_unit_id IN (...)`), `TEAM_LEAD` accède à ses équipes et espaces, et `CONTRIBUTOR`/`OBSERVER` uniquement aux espaces dont ils sont membres — sans jamais proposer ni sélectionner `Plateforme entière` côté UI pour les non-admins/non-SecOps.

---

### Story 20.2: Menu « Glossaire » (`/ontology`), Persistance PostgreSQL 18 de l'Ontologie L1–L4, Rôle `ONTOLOGY_LEAD` & Promotions Palier par Palier (`L4 → L3 → L2 → L1`)

As a Membre d'Espace, Référent Glossaire (`ONTOLOGY_LEAD`), Responsable d'Équipe / BU ou Administrateur Plateforme,
I want accéder au Glossaire & Ontologie depuis le menu gauche renommé « Glossaire » (`/ontology`) persistant réellement en PostgreSQL 18, avec délégation de la validation L2 BU au rôle officiel `ONTOLOGY_LEAD` et promotion palier par palier (`L4 → L3 → L2 → L1`),
So that le vocabulaire métier et les règles de l'organisation soient gouvernés durablement sans confusion avec le Centre d'Aide (`/help`) ni perte au rafraîchissement (`F5`) (`FR-8`, `FR-9`, `FR-31`, `FR-34`).

**Acceptance Criteria:**

**Given** la navigation principale de la barre latérale gauche et les routes `/ontology` et `/help`
**When** l'utilisateur clique sur « Glossaire » dans la barre latérale gauche
**Then** la route `/ontology` s'ouvre avec l'explorateur d'ontologie/glossaire L1–L4 et l'onglet **`Propositions à valider (N)`** sans bannière `/showcase` ni centre d'aide statique (ceux-ci étant réservés à `/help`), tandis que le 7e rôle officiel `ONTOLOGY_LEAD` (« Référent Glossaire ») est synchronisé de façon bidirectionnelle entre `org_units.ontology_lead_user_ids_jsonb` (BU) et `iam_accounts.roles_jsonb`.

**Given** un terme ou une règle persisté en PostgreSQL 18 (`ontology_concepts`, `ontology_promotion_proposals`)
**When** un membre propose une promotion (`POST /api/v1/ontology-rag/ontology/promotions`) ou qu'un valideur habilité tranche (`POST /api/v1/ontology-rag/ontology/promotions/{id}/decide`)
**Then** l'auteur ne peut proposer que vers le palier immédiatement supérieur (`4_WORKSPACE` $\rightarrow$ `3_TEAM`, `3_TEAM` $\rightarrow$ `2_DOMAIN`, `2_DOMAIN` $\rightarrow$ `1_ENTERPRISE`) avec détection de collision, et seule la validation autorisée (`TEAM_LEAD`/`ONTOLOGY_LEAD`/`BU_LEAD` pour `3_TEAM`, `ONTOLOGY_LEAD` de la BU / `BU_LEAD` pour `2_DOMAIN`, `PLATFORM_ADMIN` pour `1_ENTERPRISE`) approuve ou rejette avec survie complète au `F5`.

---

### Story 20.3: Suppression du Login Top-Right, Popup « Mon Compte » en Bas à Gauche (Style ChatGPT) & Modale Unifiée « Paramètres » Persistée en PG18

As a Utilisateur authentifié ORCIA,
I want un en-tête épuré sans bouton login redondant ni faux sélecteur de rôle RBAC, un popup « Mon Compte » en bas à gauche inspiré de ChatGPT, et une modale unifiée « Paramètres » à 5 onglets persistée en PostgreSQL 18,
So that mes préférences (thème, langue, casquette IA, instructions, connexions outils, clés MCP) survivent au rechargement sans jamais altérer mes droits RBAC réels (`FR-32`, `CAP-060`, `CAP-063`, `UX-AUTH-DOUBLE-ICON-01`).

**Acceptance Criteria:**

**Given** la coquille 4 zones (`FourZoneDirectionCShell`)
**When** l'utilisateur observe le haut-droite et clique sur son bloc compte en bas à gauche
**Then** la zone haut-droite ne contient plus le contrôle Login/Compte (seulement `[❓ Aide]` et `[🔔 Notifications]`), le faux sélecteur `Rôle` (`dropdown-hat-selector`) est supprimé (`settingsRbacResolver` évalue l'union complète `session.roles`), et le clic sur le pied du rail gauche ouvre un popup style ChatGPT proposant : en-tête cliquable vers `/profile`, `Personnalisation`, `Profil`, `Paramètres`, `Aide ›` (`/help`, `/showcase`) et `Se déconnecter` (zéro double icône/emoji).

**Given** la modale unifiée « Paramètres » à 5 onglets (`Général`, `Personnalisation`, `Compte & Sécurité`, `Connexions aux outils`, `Clés IDE & MCP`)
**When** l'utilisateur modifie son thème, sa langue, sa casquette IA ou génère/révoque une clé MCP
**Then** les réglages sont persistés en PostgreSQL 18 (`user_preferences`, `user_mcp_tokens` hachés SHA-256 sans aucune clé codée en dur) via `/api/v1/users/me/preferences` et `/api/v1/users/me/mcp-tokens`, survivent au `F5` (`unmount()` + `render()`) et sont remis à zéro proprement par `pnpm db:reset`.

---

### Story 20.4: Page Dédiée « Mon Profil » (`/profile`, Style ChatGPT : Identité, 4 KPIs Tokens/Séries & Éléments Populaires) & Télémétrie Tokens de `Mon Assistant`

As a Utilisateur authentifié ORCIA,
I want consulter ma page personnelle `/profile` présentant mon identité, mes rattachements BU/Équipes/Rôles, mes 4 indicateurs de consommation de tokens et séries d'activité ainsi que mes agents/processus/outils les plus utilisés,
So that je dispose d'une vue synthétique claire de mon activité réelle sur la plateforme, alimentée aussi bien par `Mon Assistant` que par les workflows (`FR-25`, `FR-32`, `CAP-069`).

**Acceptance Criteria:**

**Given** un tour complété dans `Mon Assistant` (`assistant_workspace.py` / `assistant_background_turns.py`)
**When** l'exécution se termine (streaming SSE ou non-streaming)
**Then** les tokens (`input_tokens`, `output_tokens`, réels via `usage` ou estimation déterministe tracée) sont enregistrés dans `audit_ledger` avec `event_type = "ASSISTANT_TURN_COMPLETED"`, `actor_id`, `actor_email`, `model_id` et `workspace_id`.

**Given** l'utilisateur authentifié ouvrant `/profile` (via l'entrée `Profil` ou l'en-tête du popup `Mon Compte`)
**When** `GET /api/v1/users/me/profile-summary` s'exécute
**Then** l'agrégation SQL strictement confinée à l'utilisateur retourne son identité, ses BU/équipes/rôles, ses 4 KPIs (`total_tokens`, `peak_daily_tokens`, `longest_streak_days`, `current_streak_days`) et ses `popular_items` (Top 5 agents/processus/compétences/outils utilisés, vide `[]` au Jour 0), rendus dans `UserProfileOverviewPage` avec un bouton `Modifier` ouvrant la modale Paramètres (`Compte & Sécurité`), tandis que la Heatmap 12 mois et le tableau Statistiques détaillées restent différés dans `ACTION_ITEM-20.1`.

---

## Epic 21: Couverture Intégrale par User Journeys (UJ-1..UJ-20), Campagne End-to-End avec Vérité PostgreSQL 18, Captures d'État Final, Audit Croisé UX/Architecture & Préparation de l'Epic 22

Garantir que **100 % des fonctionnalités métier (`kind: feature`, soit les `62` capacités fonctionnelles sur les `65` entrées de `docs/product/capabilities.yaml`)** d'ORCIA sont décrites par des User Journeys complets (`UJ-1` à `UJ-20`) dans le PRD (`prd.md`) et `EXPERIENCE.md`, contrôlées de manière bloquante en CI par `pnpm site:check`, et couvertes par des tests End-to-End Playwright vérifiant systématiquement le rendu et les interactions UI, la survie au rechargement `F5` (`page.reload()`) **ET** la persistance réelle en base PostgreSQL 18 (`orcia_e2e`, zéro validation sur état uniquement conservé en mémoire RAM Python). L'Epic organise ensuite l'exécution de la campagne intégrale avec capture PNG de l'état final de chaque test (succès comme échecs), son analyse croisée par **Sally (UX)** et **Winston (Architecture)**, la production des rapports Tech Lead pré-implémentation individuels et l'initialisation complète du plan directeur de l'**Epic 22** de remédiation.

> **Règle stricte de non-maquillage pour l'Epic 21 :** les tests E2E ne doivent ni omettre les assertions `SELECT` PostgreSQL 18, ni affaiblir les vérifications de survie au `F5`, ni neutraliser (`test.skip` / `test.fixme`) les échecs révélant une persistance encore en mémoire RAM Python, un câblage vertical incomplet ou un défaut UI ; les échecs honnêtes constatés durant la campagne constituent l'entrée officielle de l'audit Sally × Winston et de l'Epic 22.

### Story 21.1: Classification des 65 Capacités (`kind: feature | foundation`, `e2e_exempt_reason`, `uj`, `db_tables`, `read_only_surface`) & Validation de Schéma dans `capabilities_registry.py`

As a Product Manager / Tech Lead (`John` / `Amelia`),
I want classifier exhaustivement les 65 capacités recensées dans `docs/product/capabilities.yaml` en `kind: feature` (62 capacités métier) ou `kind: foundation` (3 capacités socles d'architecture/hygiène : `CAP-006`, `CAP-100`, `CAP-202`) avec les champs structurés `e2e_exempt_reason`, `uj`, `db_tables` et `read_only_surface`, et renforcer la validation de schéma dans `infra/scripts/capabilities_registry.py`,
So that le périmètre exact à couvrir par des User Journeys et des tests End-to-End avec vérité PostgreSQL 18 soit formellement tracé et contrôlé sans angle mort (`FR-1`..`FR-36`, `AD-17`, `NFR-TEST-1`).

**Dépendances :** Aucune (socle documentaire et schéma de pilotage de l'Epic 21). Précède Story 21.2, Story 21.3 et Stories 21.5..21.7.
**Références :** `docs/product/capabilities.yaml`, `infra/scripts/capabilities_registry.py`, `AD-17`, `NFR-TEST-1`, `GEMINI.md` §5.
**Fichiers impactés :** `docs/product/capabilities.yaml`, `infra/scripts/capabilities_registry.py`, `tests/unit/test_capabilities_registry.py`.

**Acceptance Criteria:**

**Given** les 65 capacités (`CAP-001` à `CAP-203`) présentes dans `docs/product/capabilities.yaml`
**When** le schéma de chaque entrée est complété et audité
**Then** chaque capacité déclare explicitement `kind: feature` (62 entrées métier) ou `kind: foundation` (3 entrées d'infrastructure/hygiène : `CAP-006`, `CAP-100`, `CAP-202`) ; toute capacité `foundation` possède un champ non vide `e2e_exempt_reason` justifiant sa couverture hors E2E, et toute capacité `feature` renseigne `uj: [UJ-...]` ainsi que soit `db_tables: [...]` (tables PostgreSQL 18 cibles pour les assertions SQL), soit `read_only_surface: true` lorsque la surface est strictement en lecture/consultation sans écriture SQL propre.

**Given** les règles de validation ajoutées dans `infra/scripts/capabilities_registry.py` (`validate_registry`)
**When** la validation du registre est exécutée
**Then** elle rejette avec un message explicite : toute capacité sans `kind` dans `{feature, foundation}`, toute capacité `foundation` sans `e2e_exempt_reason`, toute capacité `feature` sans `uj` valide (`UJ-1`..`UJ-20`), et toute capacité `feature` dépourvue à la fois de `db_tables` non vide et de `read_only_surface: true`.

**Given** la suite de tests unitaires du registre (`tests/unit/test_capabilities_registry.py`)
**When** `.venv/bin/pytest tests/unit/test_capabilities_registry.py` est exécuté
**Then** les cas nominaux sur les 65 capacités et les cas de rejet de schéma (absence de `kind`, `foundation` sans exemption, `feature` sans `db_tables` ni `read_only_surface`) passent à `100 %` et `pnpm site:check` reste vert.

---

### Story 21.2: Référentiel Complet des User Journeys (`UJ-1` à `UJ-20`) dans `prd.md` & `Key Flows` dans `EXPERIENCE.md` avec Test de Cohérence Automatique

As a Product Manager (`John`) & UX Designer (`Sally`),
I want compléter le référentiel des User Journeys (`UJ-1` à `UJ-20`) dans `prd.md` (§2.3 et §4.10) en annotant `AIOPS-INCIDENT-LOOP-01` sur `UJ-12` et en rédigeant `UJ-13` à `UJ-20`, puis enrichir les `Key Flows` dans `EXPERIENCE.md` (§9) et verrouiller l'alignement par un test de cohérence automatique,
So that chaque capacité fonctionnelle `feature` et chaque exigence `FR-1`..`FR-36` dispose d'un scénario utilisateur nommé, bout-en-bout et testable sans ambiguïté de périmètre (`FR-1`..`FR-36`, `UX-DR1`..`UX-DR17`).

**Dépendances :** Dépend de Story 21.1 (attribution cible des `UJ` dans `capabilities.yaml`). Précède Story 21.3 et Stories 21.5..21.7.
**Références :** `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md` (§2.3, §4.10), `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` (§9, §1.2), `docs/implementation-artifacts/sprint-status.yaml` (`AIOPS-INCIDENT-LOOP-01`).
**Fichiers impactés :** `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md`, `tests/unit/test_uj_prd_experience_consistency.py`.

**Acceptance Criteria:**

**Given** `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md` (§2.3 et §4.10)
**When** le référentiel des User Journeys est complété
**Then** `UJ-12` inclut l'annotation explicite `AIOPS-INCIDENT-LOOP-01` bornant la boucle d'incident sans écriture de code ni mutation Git, les 8 nouveaux parcours `UJ-13` à `UJ-20` sont rédigés au format standard du PRD (`Persona + contexte`, `Entry state`, `Path`, `Climax`, `Resolution`, `Edge case`) pour couvrir l'intégralité des capacités post-MVP (`Auth/2FA/Compte/Profil`, `Mon Organisation/IAM/SecOps/Observateur`, `Hub Modèles IA/Réindexation/Connecteurs`, `Préférences/Clés MCP`, `Citations Assistant/V5/Background Audit`, `Sources multi-nature/codegraph-mcp/ADN Starlark/Promotions Glossaire ONTOLOGY_LEAD`, `Catalogue RBAC/Packs/Process Studio v2/Wizards/Banc MCP`, `Aide contextuelle /help & /showcase`), et chaque `FR-31`..`FR-36` (§4.10) référence explicitement ses `UJ-*` (`Réalise UJ-...`).

**Given** `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` (§9)
**When** la section `Key Flows` est mise à jour
**Then** les flux comportementaux couvrent `UJ-1` à `UJ-20` en respectant les 3 invariants de microcopy utilisateur sans jargon technique interne (`EXPERIENCE.md` §1.2).

**Given** le test de cohérence automatique `tests/unit/test_uj_prd_experience_consistency.py`
**When** `.venv/bin/pytest tests/unit/test_uj_prd_experience_consistency.py` est exécuté
**Then** il vérifie automatiquement : l'existence des 20 titres `UJ-1` à `UJ-20` dans `prd.md` (§2.3), l'absence de trou de numérotation, le référencement `UJ-*` sur `FR-1`..`FR-36` (incluant `§4.10`), la couverture de `UJ-1`..`UJ-20` dans `EXPERIENCE.md` (§9), et l'absence de `UJ` référencé dans `capabilities.yaml` qui serait absent du PRD ou de `EXPERIENCE.md`.

---

### Story 21.3: Refactoring Modulaire de `sync_site_catalog.py` (`< 350` Lignes) & Verrouillage CI Bloquant `CAP ↔ UJ ↔ Spec E2E` (`pnpm site:check`)

As a Tech Lead / Ingénieur Plateforme (`Amelia` / `Karim`),
I want découper `infra/scripts/sync_site_catalog.py` sous `< 350` lignes via `_site_repo_parsers.py` et `_site_html_renderer.py`, et implémenter le contrôle CI bloquant `CAP ↔ UJ ↔ Spec E2E` dans `infra/scripts/uj_e2e_coverage.py` et `infra/scripts/capabilities_registry.py`,
So that `pnpm site:check` bloque automatiquement toute capacité `feature` sans `UJ`, toute capacité `live` `feature` sans spec E2E fonctionnelle (hors smoke `11-*`), et toute mention abusive `verification: runtime` sans E2E passant, tout en éliminant la dette de taille sur `sync_site_catalog.py` (`GEMINI.md` § Policy & §5, `AD-17`).

**Dépendances :** Dépend de Story 21.1 et Story 21.2. Précède Stories 21.4..21.8.
**Références :** `infra/scripts/sync_site_catalog.py`, `infra/scripts/capabilities_registry.py`, `GEMINI.md` (seuil 300–400 lignes & §5).
**Fichiers impactés :** `infra/scripts/sync_site_catalog.py`, `infra/scripts/_site_repo_parsers.py`, `infra/scripts/_site_html_renderer.py`, `infra/scripts/uj_e2e_coverage.py`, `infra/scripts/capabilities_registry.py`, `tests/unit/test_uj_e2e_coverage_gate.py`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`.

**Acceptance Criteria:**

**Given** le script `infra/scripts/sync_site_catalog.py` (actuellement > 880 lignes)
**When** l'extraction modulaire est réalisée
**Then** les fonctions d'introspection du dépôt sont déplacées dans `infra/scripts/_site_repo_parsers.py` et le rendu HTML statique dans `infra/scripts/_site_html_renderer.py`, ramenant `infra/scripts/sync_site_catalog.py` strictement sous `< 350` lignes, tout en conservant `parse_active_routes` et les artefacts générés par `pnpm site:sync` strictement fonctionnels et conformes à `pnpm site:check`.

**Given** le nouveau module `infra/scripts/uj_e2e_coverage.py` intégré à `infra/scripts/capabilities_registry.py` (`run_registry_check`)
**When** `pnpm site:check` s'exécute
**Then** il échoue avec un diagnostic explicite si :
- une capacité `kind: feature` ne possède pas au moins un `UJ` valide (`UJ-1`..`UJ-20`) présent dans `prd.md` ;
- une capacité `live` de type `feature` ne référence aucune spec E2E fonctionnelle sous `apps/web/e2e/` (les specs purement smoke `11-*` comme `11-screens-smoke-without-server-errors.spec.ts` sont explicitement exclues du décompte fonctionnel), sauf exemption transitoire déclarée via `e2e_backlog_story` ou `e2e_remediation_ref` ;
- une capacité déclare `verification: runtime` sans au moins une spec E2E fonctionnelle référencée et active (ou alors que son dernier statut E2E enregistré est en échec).

**Given** les tests unitaires `tests/unit/test_uj_e2e_coverage_gate.py` et les outils qualité Python
**When** `.venv/bin/pytest tests/unit/test_uj_e2e_coverage_gate.py`, `.venv/bin/ruff check infra/scripts`, et `pnpm site:check` s'exécutent
**Then** tous les scénarios de blocage (smoke `11-*` seul, `feature` sans `UJ`, `runtime` sans spec fonctionnelle, taille de `sync_site_catalog.py < 350` lignes) et le cas nominal passent sans contournement.

---

### Story 21.4: Harnais Playwright de Vérité PostgreSQL 18 (`query_db.py` + `dbAssertions.ts`), Fixture Capture PNG Systématique (`e2eCaptureFixture.ts`) & Mise à Niveau des 16 Specs Existantes

As a Tech Lead / QA Automation (`Amelia` / `Winston`),
I want fournir un harnais Playwright interrogeant PostgreSQL 18 (`orcia_e2e`) en lecture seule stricte sans ajouter de package npm (`infra/scripts/e2e/query_db.py` + `apps/web/e2e/support/dbAssertions.ts`), une fixture capturant systématiquement le screenshot PNG final de chaque test en succès comme en échec (`apps/web/e2e/support/e2eCaptureFixture.ts`), et mettre à niveau les 16 specs existantes (`00..13` + `shell.spec.ts`) avec en-têtes `@uj`/`@cap`, vérification `F5` et assertions `SELECT` PostgreSQL 18,
So that chaque test E2E prouve la persistance réelle en base de données (zéro faux positif sur état en RAM Python) et produise une preuve visuelle exploitable par Sally et Winston (`AD-17`, `GEMINI.md` §3).

**Dépendances :** Dépend de Story 21.3. Précède Stories 21.5..21.8.
**Références :** `infra/scripts/e2e/e2e_stack.py`, `infra/scripts/e2e/e2e_stack_config.py`, `apps/web/playwright.config.ts`, `GEMINI.md` §3, règle de non-maquillage Epic 21.
**Fichiers impactés :** `infra/scripts/e2e/query_db.py`, `apps/web/e2e/support/dbAssertions.ts`, `apps/web/e2e/support/e2eCaptureFixture.ts`, `apps/web/e2e/00-stack-smoke.spec.ts` .. `apps/web/e2e/13-epic-7-autonomous-governance-and-supervision.spec.ts`, `apps/web/e2e/shell.spec.ts`, `tests/unit/test_e2e_query_db_readonly.py`.

**Acceptance Criteria:**

**Given** le script `infra/scripts/e2e/query_db.py` et les helpers `apps/web/e2e/support/dbAssertions.ts` (exécutant `.venv/bin/python infra/scripts/e2e/query_db.py` sans aucun ajout dans `apps/web/package.json`)
**When** un test Playwright invoque une assertion PostgreSQL 18 (`queryDbRows`, `expectDbRowExists`, `expectDbRowCount`)
**Then** `query_db.py` charge `.orcia-run/e2e-stack-state.json`, vérifie `is_isolated_e2e_database_url` (refus strict hors base `orcia_e2e` éphémère), rejette toute requête non strictement lecture seule (`SELECT` / `WITH ... SELECT` uniquement, rejet de `INSERT`/`UPDATE`/`DELETE`/`DDL`/multi-statements `;`, transaction PostgreSQL en mode `READ ONLY`), et retourne le résultat JSON structuré sans erreur.

**Given** la fixture `apps/web/e2e/support/e2eCaptureFixture.ts`
**When** n'importe quel test E2E se termine (statut `passed`, `failed` ou `timedOut`)
**Then** une capture PNG pleine page de l'état final est enregistrée systématiquement sous `docs/implementation-artifacts/e2e-campaign-epic-21/screenshots/<spec-slug>/<test-slug>--<status>.png` et une entrée JSONL correspondante (`spec`, `test_title`, `uj`, `cap`, `status`, `screenshot_path`, `url`, `duration_ms`, `timestamp`) est ajoutée à `docs/implementation-artifacts/e2e-campaign-epic-21/manifest.jsonl`.

**Given** les 16 specs E2E existantes (`00` à `13` incluant `12-finops-*` et `12-epic16-*`, plus `shell.spec.ts`)
**When** elles sont mises à niveau
**Then** chaque fichier déclare ses métadonnées d'en-tête `@uj` et `@cap`, utilise `e2eCaptureFixture`, vérifie la survie au rafraîchissement (`await page.reload()`) après toute mutation, et exécute des assertions `SELECT` PostgreSQL 18 réelles sur les tables cibles (`db_tables`) — sans jamais contourner, désactiver ni marquer `test.skip` / `test.fixme` les échecs révélant un défaut réel.

---

### Story 21.5: Nouvelles Specs E2E Lot A (`14` à `16`) — Auth/2FA/Compte/Profil (`UJ-13`, `UJ-16`), Mon Organisation/IAM/SecOps/Inbox & Garde `READ_ONLY_OBSERVER` `403` (`UJ-4`, `UJ-14`), Hub Modèles IA/Réindexation/Connecteurs & Permission Broker (`UJ-7`, `UJ-15`)

As a Utilisateur, Responsable BU/Équipe, Administrateur Plateforme & Développeur (`UJ-4`, `UJ-7`, `UJ-13`, `UJ-14`, `UJ-15`, `UJ-16`),
I want couvrir par trois nouvelles specs Playwright (`14`, `15`, `16`) les parcours Authentification exclusive / 2FA / Mot de passe temporaire / Mon Compte / `/profile`, Gouvernance déléguée « Mon Organisation » / IAM / SecOps / `/inbox` navigateur + garde `READ_ONLY_OBSERVER` `403`, et Hub Modèles IA / Réindexation bloquante / Connecteurs / Passthrough & Permission Broker avec `F5` et assertions `SELECT` PostgreSQL 18,
So that les fondations identitaires, organisationnelles et IA soient validées bout en bout de l'UI jusqu'à la base de données (`FR-2`, `FR-3`, `FR-21`, `FR-22`, `FR-31`, `FR-32`).

**Dépendances :** Dépend de Story 21.3 et Story 21.4.
**Références :** `UJ-4`, `UJ-7`, `UJ-13`, `UJ-14`, `UJ-15`, `UJ-16`, `CAP-001`, `CAP-003`, `CAP-040`, `CAP-041`, `CAP-043`, `CAP-050`..`CAP-054`, `CAP-058`, `CAP-063`, `CAP-067`, `CAP-069`, `CAP-190`, `CAP-203`.
**Fichiers impactés :** `apps/web/e2e/14-auth-2fa-account-and-profile.spec.ts`, `apps/web/e2e/15-organization-iam-secops-inbox-and-observer.spec.ts`, `apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts`, `docs/product/capabilities.yaml`.

**Acceptance Criteria:**

**Given** `apps/web/e2e/14-auth-2fa-account-and-profile.spec.ts` (`@uj UJ-13 UJ-16`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste la politique d'authentification exclusive (`LOCAL` / `OIDC`), le double facteur (`TOTP` / `EMAIL_OTP`), la connexion par mot de passe temporaire et changement obligatoire, le popup « Mon Compte » + modale Paramètres 5 onglets (préférences, clés IDE/MCP) et la page `/profile` (identité, 4 KPIs tokens/séries, éléments populaires), contrôle la survie après `page.reload()` (`F5`), et vérifie via `SELECT` PG18 (`iam_accounts`, `platform_auth_settings`, `user_preferences`, `user_mcp_tokens`, `audit_ledger`).

**Given** `apps/web/e2e/15-organization-iam-secops-inbox-and-observer.spec.ts` (`@uj UJ-4 UJ-14`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste `/organization` avec `BU_LEAD` et `TEAM_LEAD` (création de sous-BU/équipe, invitation scopée sans escalade, interdiction `403` de suppression de la BU racine), `/settings` IAM (matrice des rôles, exceptions SecOps), `/inbox` navigateur (filtres personnel/équipe/autonome) et la garde `READ_ONLY_OBSERVER` rejetant toute mutation (`403`), contrôle la survie au `page.reload()` (`F5`), et vérifie via `SELECT` PG18 (`org_units`, `iam_accounts`, `iam_secops_exceptions`, `audit_ledger` avec `org_unit_id`, `inbox_notifications`).

**Given** `apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts` (`@uj UJ-7 UJ-15`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste `/settings/ai-models` (champs vides initiaux, découverte `0` token, test de connexion chat/embedding dim 1024, modèle d'embedding unique GLOBAL, blocage Assistant/RAG sans embedding `ERR_NO_ACTIVE_EMBEDDING_MODEL` et réindexation bloquante `503 ERR_RAG_REINDEX_IN_PROGRESS`), les connecteurs socle et Passthrough utilisateur, et le `PermissionBroker` affichant la procédure + lien Jira + `Replay Step N`, vérifie la survie au `page.reload()` (`F5`) et exécute des `SELECT` PG18 (`workspace_llm_tier_mappings`, `enterprise_connectors`, `user_passthrough_credentials`, `rag_reindexing_jobs`), sans masquer un éventuel échec via `test.skip`.

---

### Story 21.6: Nouvelles Specs E2E Lot B (`17` & `18`) — Sources d'Espace Multi-Nature / Fraîcheur `SHA-256` / `codegraph-mcp` / Chaîne ADN Starlark / Promotions Glossaire `L4 → L1` (`UJ-5`, `UJ-18`) & Catalogue Fédéré RBAC / Packs / Wizards / Banc de Test MCP-A2A (`UJ-9`, `UJ-19`)

As a Tech Lead, Référent Glossaire (`ONTOLOGY_LEAD`), Administrateur Plateforme & Concepteur de Packs (`UJ-5`, `UJ-9`, `UJ-18`, `UJ-19`),
I want couvrir par deux nouvelles specs Playwright (`17` & `18`) les sources d'espace multi-nature, la fraîcheur `SHA-256`, `codegraph-mcp`, la chaîne ADN Starlark & waivers, les promotions Glossaire `ONTOLOGY_LEAD` (`L4 → L1`), le Catalogue Fédéré RBAC, les packs déclaratifs, les wizards durables et le banc de test MCP/A2A avec `F5` et assertions `SELECT` PostgreSQL 18,
So that la gouvernance documentaire, sémantique et catalogue soit validée jusqu'en base PostgreSQL (`FR-8`, `FR-9`, `FR-10`, `FR-20`, `FR-23`, `FR-28`, `FR-34`, `FR-35`).

**Dépendances :** Dépend de Story 21.3 et Story 21.4.
**Références :** `UJ-5`, `UJ-9`, `UJ-18`, `UJ-19`, `CAP-002`, `CAP-010`, `CAP-011`, `CAP-055`..`CAP-057`, `CAP-080`..`CAP-084`, `CAP-150`, `CAP-180`.
**Fichiers impactés :** `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts`, `apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts`, `docs/product/capabilities.yaml`.

**Acceptance Criteria:**

**Given** `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts` (`@uj UJ-5 UJ-18`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle valide l'ajout et la gestion de sources multi-nature dans `/workspaces/$wsId/sources`, la sonde de fraîcheur `SHA-256` et `[STALE_WARNING]`, l'invocation lecture seule `codegraph-mcp`, la compilation `Text-to-Starlark` de la chaîne ADN (`Directive → Norme → Mécanisme`) + acquittement `workspace_exception_waivers`, et le workflow complet de promotion Glossaire `ONTOLOGY_LEAD` (`L4 → L3 → L2 → L1`) dans `/ontology` avec détection de collision, contrôle la survie au `page.reload()` (`F5`), et vérifie par `SELECT` PG18 (`workspace_datasources`, `datasource_webhook_deliveries`, `workspace_exception_waivers`, `ontology_concepts`, `ontology_promotion_proposals`).

**Given** `apps/web/e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts` (`@uj UJ-9 UJ-19`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle valide le Catalogue Fédéré (`/catalog`) avec ses permissions RBAC (`DISCOVER`, `EXECUTE`, `READ_SOURCE`, `EDIT`, `ADMIN`) et cycle de publication, l'écran `/settings/packs` (packs déclaratifs `packs/sdlc`, `packs/orcia-docs`, activation et prérequis connecteurs), les wizards d'initialisation durables (`/wizards`) et le banc de test MCP/A2A (`🔌`), contrôle la survie au `page.reload()` (`F5`), et vérifie par `SELECT` PG18 (`catalog_items`, `workflow_definitions`, `declarative_packs`, `workspace_pack_activations`, `wizard_runs`, `audit_ledger`).

---

### Story 21.7: Nouvelles Specs E2E Lot C (`19` à `21`) — Orchestration `What-If`/Replay/Gates Orthogonales (`UJ-1`..`UJ-3`, `UJ-6`), Process Studio v2/FinOps/Autonomie/`LOG_SINK_ALERT` (`UJ-8`, `UJ-11`, `UJ-12`, `UJ-19`), Citations Assistant `[S1]/[G1]/[O1]`/Verrou V5/Background Audit/`/help`/`/showcase` (`UJ-10`, `UJ-17`, `UJ-20`) — Couverture `100 %` des `62` Capacités `feature`

As a PM, Architecte, Tech Lead, SecOps, Directrice BU & Utilisateur (`UJ-1`..`UJ-3`, `UJ-6`, `UJ-8`, `UJ-10`..`UJ-12`, `UJ-17`, `UJ-19`, `UJ-20`),
I want couvrir par trois nouvelles specs Playwright (`19`, `20`, `21`) l'orchestration `What-If` / `[STALE_WARNING]` / Replay Step N / Gates orthogonales, Process Studio v2 (Macro-VSM 11 étapes, Studio 5 blocs, HITL 4 actions), FinOps cognitif, autonomie & déclencheur `LOG_SINK_ALERT`, ainsi que les citations Assistant `[S1]/[G1]/[O1]` & Verrou V5, audit en tâche de fond, `/help` (`ⓘ`) & `/showcase` avec `F5` et assertions `SELECT` PostgreSQL 18,
So that **100 % des `62` capacités `feature` soient couvertes avec `0` `e2e_backlog_story` résiduel** et vérifiées par `pnpm site:check` (`FR-1`..`FR-36`, `AD-17`).

**Dépendances :** Dépend de Story 21.3, Story 21.4, Story 21.5 et Story 21.6. Précède Story 21.8.
**Références :** `UJ-1`..`UJ-3`, `UJ-6`, `UJ-8`, `UJ-10`..`UJ-12`, `UJ-17`, `UJ-19`, `UJ-20`, `CAP-020`..`CAP-024`, `CAP-030`..`CAP-033`, `CAP-064`, `CAP-065`, `CAP-066`, `CAP-068`, `CAP-070`..`CAP-076`, `CAP-090`..`CAP-092`, `CAP-140`, `CAP-160`, `CAP-200`, `CAP-201`.
**Fichiers impactés :** `apps/web/e2e/19-orchestration-whatif-replay-and-gates.spec.ts`, `apps/web/e2e/20-process-studio-v2-finops-and-log-sink.spec.ts`, `apps/web/e2e/21-assistant-citations-v5-audit-help-showcase.spec.ts`, `docs/product/capabilities.yaml`.

**Acceptance Criteria:**

**Given** `apps/web/e2e/19-orchestration-whatif-replay-and-gates.spec.ts` (`@uj UJ-1 UJ-2 UJ-3 UJ-6`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste `Workflow-as-Code`, Challenge Amont avec simulation `What-If`, signalement `[STALE_WARNING]` + Replay Step N, Gate Déterministe Sandbox et Gate Agentique Orthogonale (`evaluator_model_family != executor_model_family`) + Gate Humaine, vérifie la survie au `page.reload()` (`F5`), et valide via `SELECT` PG18 (`workflow_runs`, `step_executions`, `blackboard_snapshots`, `gate_evaluations`, `run_locks`).

**Given** `apps/web/e2e/20-process-studio-v2-finops-and-log-sink.spec.ts` (`@uj UJ-8 UJ-11 UJ-12 UJ-19`)
**When** la spec s'exécute sur `orcia_e2e` avec `e2eCaptureFixture`
**Then** elle teste la Macro-VSM 11 étapes (`/processes/vsm/$vsmId`), le Studio 5 blocs (`/processes/studio/$workflowId`), la revue HITL 4 actions, le tableau FinOps cognitif + quotas connecteurs (`/finops`), et le déclenchement idempotent `LOG_SINK_ALERT` (`AIOPS-INCIDENT-LOOP-01`) avec contrat d'autonomie et `Kill-Switch`/`Rollback`, vérifie la survie au `page.reload()` (`F5`), et valide via `SELECT` PG18 (`workflows_v2`, `autonomy_contracts`, `workflow_triggers`, `finops_cost_entries`, `audit_ledger`).

**Given** `apps/web/e2e/21-assistant-citations-v5-audit-help-showcase.spec.ts` (`@uj UJ-10 UJ-17 UJ-20`)
**When** la spec s'exécute et que `docs/product/capabilities.yaml` est mis à jour
**Then** elle teste les citations déterministes `[S1]/[G1]/[O1]`, le Verrou V5 d'officialisation via Gate, l'audit en tâche de fond (`BACKGROUND_AUDIT`), le renvoi ciblé `/help` (`ⓘ`) et le site vitrine `/showcase` avec `F5` et assertions `SELECT` PG18 (`assistant_threads`, `assistant_messages`, `catalog_items`), et **100 % des `62` capacités `feature` possèdent une couverture E2E fonctionnelle (`0` `e2e_backlog_story` résiduel dans `capabilities.yaml`, `pnpm site:check` passant à `0` erreur)**.

---

### Story 21.8: Campagne E2E Intégrale (`00..21` + `shell.spec.ts`, `--retries=0 --max-failures=0`), Archivage Screenshots PNG & `playwright-results.json`, Bilan d'Exécution, Audit Croisé Sally × Winston & Vérité dans `capabilities.yaml`

As a UX Designer (`Sally`), Architecte (`Winston`) & Tech Lead (`Amelia`),
I want exécuter l'intégralité des specs E2E (`00..21` + `shell.spec.ts`) sans aucun retry ni arrêt anticipé (`--retries=0 --max-failures=0`), archiver toutes les captures PNG d'état final (succès et échecs) et `playwright-results.json`, produire le bilan factuel d'exécution, mener l'inspection croisée Sally × Winston dans `synthese-remediation-sally-winston-epic-21.md`, et mettre à jour honnêtement `docs/product/capabilities.yaml`,
So that chaque écart UI, UX, de persistance ou d'architecture soit objectivé par des preuves visuelles et SQL irréfutables avant planification de la remédiation (`AD-17`, `GEMINI.md` §5).

**Dépendances :** Dépend de Story 21.7 (100 % des specs écrites). Précède Story 21.9.
**Références :** `apps/web/playwright.config.ts`, `docs/product/capabilities.yaml`, `EXPERIENCE.md`, `DESIGN.md`, `ARCHITECTURE-SPINE.md`.
**Fichiers impactés :** `docs/implementation-artifacts/e2e-campaign-epic-21/playwright-results.json`, `docs/implementation-artifacts/e2e-campaign-epic-21/manifest.jsonl`, `docs/implementation-artifacts/e2e-campaign-epic-21/screenshots/**/*.png`, `docs/implementation-artifacts/e2e-campaign-epic-21/bilan-execution-tests-e2e-epic-21.md`, `docs/implementation-artifacts/e2e-campaign-epic-21/synthese-remediation-sally-winston-epic-21.md`, `docs/product/capabilities.yaml`.

**Acceptance Criteria:**

**Given** l'ensemble des suites Playwright (`00..21` incluant `12-finops-*` et `12-epic16-*`, plus `shell.spec.ts`) sur `desktop-cockpit` (`1440x900`) et `mobile-companion` (`390x844`)
**When** la campagne intégrale est lancée avec `--retries=0 --max-failures=0` et le reporter JSON activé
**Then** la totalité des tests s'exécute sans aucun `test.skip` / `test.fixme` masquant un échec, et les artefacts complets (`playwright-results.json`, `manifest.jsonl`, et l'intégralité des captures PNG d'état final en succès comme en échec sous `screenshots/`) sont archivés dans `docs/implementation-artifacts/e2e-campaign-epic-21/`.

**Given** les résultats et captures archivés
**When** `docs/implementation-artifacts/e2e-campaign-epic-21/bilan-execution-tests-e2e-epic-21.md` est rédigé
**Then** il dresse l'inventaire chiffré exact (total tests, verts, rouges, 0 skippé), la matrice de couverture `CAP ↔ UJ ↔ Spec ↔ Vérification UI/F5/SQL`, la cause racine observée de chaque échec et les liens vers toutes les captures PNG correspondantes.

**Given** la revue croisée de toutes les captures PNG et traces d'échecs par **Sally (UX)** et **Winston (Architecture)**
**When** ils produisent `docs/implementation-artifacts/e2e-campaign-epic-21/synthese-remediation-sally-winston-epic-21.md`
**Then** chaque défaillance E2E et chaque anomalie visuelle/ergonomique/architecturale détectée sur capture (surcharge, jargon, défaut de feedback, état RAM non persisté en PG18, violation `AD-*`) est formalisée avec sévérité (`P0`..`P3`), capacité `CAP-*` / parcours `UJ-*` touché et recommandation de correction ciblée.

**Given** l'état réel constaté à l'issue de la campagne
**When** `docs/product/capabilities.yaml` est mis à jour et contrôlé par `pnpm site:check`
**Then** seules les capacités dont 100 % des assertions E2E (UI + `F5` + `SELECT` PG18) ont réussi conservent ou reçoivent `verification: runtime` (avec date `verified_at`), tandis que toute capacité touchée par au moins un échec passe honnêtement à `verification: failed_e2e`.

---

### Story 21.9: Analyse Tech Lead & Impact GitNexus (`repo: "ORCIA"`), Rapports Tech Lead Pré-Implémentation (`22-1-...` à `22-N-...`), Plan Directeur & Initialisation Complète de l'Epic 22

As a Tech Lead (`Amelia`) & Architecte (`Winston`),
I want conduire l'analyse Tech Lead et d'impact GitNexus (`repo: "ORCIA"`) pour chaque échec E2E et chaque point de la synthèse Sally × Winston, rédiger les Rapports Tech Lead pré-implémentation individuels (`22-1-...` à `22-N-...`), publier le plan directeur `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`, et initialiser complètement l'**Epic 22** dans `epics.md` et `sprint-status.yaml` avec un test automatique garantissant `100 %` de traçabilité,
So that chaque correction de l'Epic 22 démarre avec une architecture validée, zéro angle mort et une traçabilité intégrale jusqu'au retour au vert de toutes les capacités (`GEMINI.md` § Policy, `AD-17`).

**Dépendances :** Dépend de Story 21.8. Clôture l'Epic 21.
**Références :** `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md`, `docs/implementation-artifacts/e2e-campaign-epic-21/bilan-execution-tests-e2e-epic-21.md`, `docs/implementation-artifacts/e2e-campaign-epic-21/synthese-remediation-sally-winston-epic-21.md`, `GEMINI.md` (§ Protocole Tech Lead).
**Fichiers impactés :** `docs/implementation-artifacts/tech-lead-reports/22-1-*.md` .. `22-N-*.md`, `docs/implementation-artifacts/tech-lead-reports/README.md`, `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`, `docs/planning-artifacts/epics.md` (ajout Epic 22), `docs/implementation-artifacts/sprint-status.yaml` (ajout `epic-22` et `22-1-...`..`22-N-...`), `tests/unit/test_epic21_to_epic22_traceability.py`.

**Acceptance Criteria:**

**Given** l'ensemble des échecs E2E de `bilan-execution-tests-e2e-epic-21.md` et des points de remédiation de `synthese-remediation-sally-winston-epic-21.md`
**When** le Tech Lead exécute l'analyse d'impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` avec `repo: "ORCIA"`) sur les modules concernés
**Then** tous les défauts sont regroupés en `N` Stories cohérentes `Story 22.1` à `Story 22.N`, et chaque Story dispose d'un Rapport Tech Lead pré-implémentation individuel (`docs/implementation-artifacts/tech-lead-reports/22-1-...-tech-lead-report.md` .. `22-N-...`) conforme à `TECH-LEAD-REPORT-TEMPLATE.md` (Sections 1 & 2 rédigées, Section 3 préparée) et enregistré dans `docs/implementation-artifacts/tech-lead-reports/README.md`.

**Given** le plan directeur `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md`
**When** il consolide la feuille de route de remédiation
**Then** il contient la matrice complète reliant chaque échec E2E, chaque constat Sally × Winston (`P0`..`P3`) et chaque `CAP-*` en `failed_e2e` à une Story `22.k`, l'ordonnancement topologique d'exécution, les migrations/refactorings requis et la condition de sortie de l'Epic 22 (`100 %` des capacités `feature` repassées à `verification: runtime`).

**Given** l'ajout de l'**Epic 22** et de ses Stories `22.1` à `22.N` dans `docs/planning-artifacts/epics.md` et `docs/implementation-artifacts/sprint-status.yaml`, ainsi que `tests/unit/test_epic21_to_epic22_traceability.py`
**When** `.venv/bin/pytest tests/unit/test_epic21_to_epic22_traceability.py` et `pnpm site:sync` + `pnpm site:check` s'exécutent
**Then** le test automatique prouve `100 %` de traçabilité bidirectionnelle (aucun échec E2E, aucun constat Sally × Winston et aucune capacité `failed_e2e` orpheline), et `epics.md`, `sprint-status.yaml` et les rapports Tech Lead sont prêts pour le démarrage de l'Epic 22.

---

## Epic 22: Remédiation E2E Vérité PostgreSQL 18, Portails & Shell Direction C, Purge Jargon, Gardes CI, Assainissement Fail-Closed, Campagne Intégrale & Initialisation Epic 23 (`Stories 22.1`..`22.10` + `22.8a`)

Résoudre de manière ordonnée et définitive les **`34` chantiers de l'audit croisé Sally × Winston (`REM-01` .. `REM-34`)** et les **`47` scénarios E2E en échec ou timeout (`14 / 24` specs)** identifiés à l'issue de la campagne Epic 21, afin d'éliminer tout silo mémoire RAM (« Dual-Stack »), restaurer la conformité Direction C (`8` menus, Mobile Companion `< 768px`, aide contextuelle dynamique sans jargon ni faux exemples, Cockpit `<= 3` blocs), verrouiller la non-régression par `5` gardes CI automatisées + `4` verrous anti-faux-positifs + `100 %` d'assertions `SELECT` PostgreSQL 18 sur les `55` blocs `test(...)` E2E avec purge `ORCIA_E2E_SEED_FIXTURES` et relecture à froid PG18 (`22.8`), assainir *Fail-Closed* `vitest.setup.ts`, valider le Composition Root `create_app()` sans `dependency_overrides` ni `app.state.*` manuel et activer la CI GitHub Actions complète à `5` couches (`22.8a`), exécuter la campagne intégrale `e2e-campaign-epic-22` avec captures PNG finales, bilan factuel, audit croisé **Sally × Winston** et mise à jour honnête de `capabilities.yaml` (`22.9`), puis produire les rapports Tech Lead individuels, le plan de correction global et l'initialisation complète de l'**Epic 23** pour traiter tout reliquat ou amélioration (`22.10`).

> **Référentiel directeur :** `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md` — chaque Story dispose de son rapport Tech Lead pré-implémentation individuel dans `docs/implementation-artifacts/tech-lead-reports/22-1-*` .. `22-10-*` (y compris `22-8a-*` et le rapport d'analyse des causes racines `2026-11-18-rca-epic-21-enrichissement-22-8-et-story-22-8a-tech-lead-report.md`).

### Story 22.1: Socle Identité UUIDv7 Workspaces, Permissions `PLATFORM_ADMIN` & Fin du Mode Dégradé `marc` / Bypass PG (`REM-01`, `REM-02`, `REM-07`)

As a Administrateur Plateforme, Chef d'Équipe & Développeur (`Karim`, `Marc`, `Amelia`),
I want unifier l'identité des espaces de travail sur l'`UUIDv7` réel retourné par PostgreSQL 18 avec propagation exacte du `slug`, corriger l'évaluation `MatrixPermissionEvaluator` afin qu'un `PLATFORM_ADMIN` ne soit pas rétrogradé à tort en `READ_ONLY_OBSERVER` (`HTTP 403`) sur ses nouveaux espaces `STANDARD`, et purger l'identité `"marc"` codée en dur ainsi que le drapeau `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`,
So that toute création d'espace, rattachement de source, évaluation de Gate ou exécution réflexive persiste en PostgreSQL 18 avec son identifiant canonique sans jamais recevoir de faux rejet `403`/`404` ni masquer d'erreur (`FR-3`, `FR-21`, `FR-23`, `FR-28`, `AD-1`, `AD-6`, `AD-19`, `UJ-5`, `UJ-6`, `UJ-9`, `UJ-14`, `UJ-17`, `UJ-18`).

**Dépendances :** Vague 0 (socle transverse prioritaire). Précède Stories `22.3`, `22.4`, `22.5`.
**REM couverts :** `REM-01`, `REM-02`, `REM-07`.
**CAP ancrées (`failed_e2e`) :** `CAP-011`, `CAP-022`, `CAP-050`, `CAP-067`, `CAP-072`, `CAP-076`, `CAP-080`, `CAP-180`.
**Fichiers impactés :** `apps/web/src/components/platformSetupStore.tsx`, `apps/web/src/features/cockpit/*`, `packages/orcia-core/src/orcia_core/permissions/evaluator.py`, `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_platform_setup_relational_sync.py`, `apps/api/src/orcia_api/routers/*`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py`.

**Acceptance Criteria:**

**Given** un utilisateur qui crée une BU, une équipe et un espace (ex. `slug: 'espace-e2e-compta'`) depuis l'UI ou l'API
**When** `POST /api/v1/workspaces` et `platformSetupStore.createWorkspace` s'exécutent
**Then** aucun identifiant synthétique `"ws-1"` / `"ws-${len+1}"` ni `.catch(() => undefined)` n'est utilisé : l'API retourne l'`UUIDv7` PostgreSQL 18 et persiste exactement `input.slug` dans `workspaces` (`SELECT id, slug FROM workspaces` retrouve l'espace après `F5`), et le rattachement d'une source `SOURCE_CODE` (`/api/v1/workspaces/{uuid}/datasources`) persiste dans `workspace_datasources` sans `404` ni contournement `ws-\d+`.

**Given** un `PLATFORM_ADMIN` agissant sur un espace `STANDARD` fraîchement créé (sans header `X-Orcia-Access-Mode: READ_ONLY_OBSERVER`)
**When** il appelle `POST /api/v1/gates/deterministic/evaluate` ou `POST /api/v1/executions/reflexive`
**Then** un `WorkspaceMembershipEntity` propriétaire est enregistré pour le créateur/admin sur l'UUID réel PG18, `MatrixPermissionEvaluator.resolve_workspace_access` maintient un accès contributeur/admin autorisé (n'appliquant `READ_ONLY_OBSERVER` que sur `CONFIDENTIAL_RESTRICTED` sans délégation ou sur header explicite), et les requêtes réussissent (`HTTP 200`/`201`) tout en conservant `403 ERR_OBSERVER_MODE_READ_ONLY` pour un véritable observateur.

**Given** le Cockpit, le Composition Root et les routeurs FastAPI
**When** l'application démarre en dehors des harnais de tests unitaires
**Then** `CockpitHumanLedGovernanceSection` et `cockpit/index.tsx` utilisent exclusivement l'identité JWT session issue de `useAuthSessionStore` (`0` occurrence `"marc"`), `get_accostage_service` lit `orcia_env`/`bootstrap_token` depuis les settings injectés, et `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` est totalement supprimé des routeurs (`HTTP 503` fail-fast si PG18 absent).

---

### Story 22.2: Portals Modales `OrciaDialog`, Compilation Tailwind v4, Purge `display: none`, Découplage `/catalog`/`/agents`/`/help`, Bouton Invitation & Alignement `data-testid`/Contrats (`REM-03`, `REM-04`, `REM-05`, `REM-06`, `REM-16`, `REM-24`, `REM-25`)

As a Utilisateur, Administrateur & QA (`Karim`, `Alice`, `Sally`),
I want unifier 100 % des modales derrière `<OrciaDialog>` (`DialogPrimitive.Portal`) avec Tailwind CSS v4 compilé et footer sticky, purger les `4` wrappers `style={{ display: "none" }}`, découpler `/catalog`, `/agents` et `/help`, exposer explicitement le bouton d'invitation sur `/organization` et aligner les `data-testid` et le payload `plaintext_value`,
So that aucune modale ne soit coupée par Zone 4 ou le bord bas d'écran, qu'aucun doublon DOM ni panneau caché ne bloque les parcours utilisateur et que les contrats UI/API soient rigoureusement alignés (`FR-1`, `FR-20`, `FR-21`, `FR-31`, `FR-32`, `FR-34`, `FR-35`, `AD-22`, `UJ-5`, `UJ-9`, `UJ-13`..`UJ-20`).

**Dépendances :** Vague 0. Complémentaire à `Story 22.1`.
**REM couverts :** `REM-03`, `REM-04`, `REM-05`, `REM-06`, `REM-16`, `REM-24`, `REM-25`.
**CAP ancrées (`failed_e2e`) :** `CAP-001`, `CAP-002`, `CAP-010`, `CAP-041`, `CAP-051`, `CAP-052`, `CAP-053`, `CAP-054`, `CAP-058`, `CAP-063`, `CAP-064`, `CAP-066`, `CAP-069`, `CAP-081`, `CAP-082`, `CAP-084`, `CAP-092`, `CAP-140`, `CAP-190`, `CAP-200`, `CAP-203`.
**Fichiers impactés :** `apps/web/vite.config.ts`, `packages/ui/src/styles/tokens.css`, `packages/ui/src/primitives/{RadixDesignSystemPrimitives,UserSettingsModalDialog,AiModelConfigModal,FourZoneSidebarRail}.tsx`, `apps/web/src/router.tsx`, `apps/web/src/components/{ShellContainer,SettingsOrganizationUnitsBlock}.tsx`, `apps/web/src/features/{catalog,workspaces,inbox}/index.tsx`, `apps/web/src/routes/{help,settingsAiModelsPresets}.ts*`, `WorkflowStudioHeaderBar.tsx`, `apps/web/e2e/20-process-studio-v2-finops-and-log-sink.spec.ts`.

**Acceptance Criteria:**

**Given** `apps/web/vite.config.ts` et `packages/ui`
**When** n'importe quelle modale (`UserSettingsModalDialog`, `FirstBootAdminSetupModal`, `AiModelConfigModal`, `UpstreamChallengeRewindModal`) s'ouvre sur Desktop `1440×900` ou Mobile `390×844`
**Then** `@tailwindcss/vite` compile les classes utilitaires (`@source "../../packages/ui/src"`), les tokens `--z-overlay: 1000` / `--z-dialog: 1010` s'appliquent, la modale monte via `OrciaDialog` (`DialogPrimitive.Portal` dans `document.body`) au-dessus de Zone 4 (`four-zone-contextual-help-column`), son corps défile dans `max-height: min(90vh, 760px)` avec un footer sticky visible (`Annuler` / `Enregistrer`), et `AiModelConfigModal` n'affiche aucune erreur de clé API avant saisie/soumission.

**Given** les vues `/catalog`, `/agents`, `/spaces`, `/workspaces/$wsId` et `/help`
**When** l'utilisateur navigue vers chacune de ces routes
**Then** les `4` wrappers `style={{ display: "none" }}` (`features/catalog`, `features/workspaces`, `InboxAuxiliaryPanels`, `FourZoneSidebarRail`) sont supprimés ; `/catalog` affiche `CatalogExplorerPanel` visible (`catalog-explorer-panel`) ; `/agents` onglet MCP ne monte qu'**une seule** instance de `RemoteServiceTestBenchAndMcpExposureView` ; `/workspaces/$wsId` affiche `DnaStarlarkCompilerAndGlossaryLifecycleView` visible dans son onglet et persiste les waivers (`workspace_exception_waivers`) en PG18 ; et `/help` masque `<ShellContextualHelpColumn>` dans Zone 4 (`1` seule instance `contextual-help-hybrid-panel`), ouvre `help-accordion-steps-content` sur mobile et applique `pl-5` sur les puces.

**Given** l'écran `/organization`, la modale Modèles IA, le Studio V2 et le test `20-process-studio` #2
**When** l'utilisateur ou le test accède à ces contrôles
**Then** `open-invite-org-user-modal-btn` est toujours rendu sur `/organization` (invitation racine autorisée ou état explicite), `settingsAiModelsPresets.ts` expose `llm-provider-preset-ollama`, `WorkflowStudioHeaderBar.tsx` expose `studio-view-mode-whatif` (avec libellés distincts), et `20-process-studio` #2 envoie `SecretInputPayload.plaintext_value` conforme au contrat OpenAPI (`HTTP 201`).

---

### Story 22.3: Persistance PG18 Assistant (`assistant_folders`), Notifications (`task_notifications`, `/inbox`, SSE) & Permission Broker (`permission_broker_tickets`, fallback `git://*`) (`REM-08`, `REM-10`, `REM-13`)

As a Utilisateur, Collaborateur d'Équipe & Développeur (`Nadia`, `Lucas`, `Marc`),
I want persister en PostgreSQL 18 les dossiers collaboratifs de Mon Assistant (sans fuite de prompt interne `[LAYER_5_*]`), les notifications d'équipe + baux de ressources (`task_notifications`, `resource_leases`) couplés au SSE `< 500 ms` sur `/inbox`, et les tickets du Permission Broker (`permission_broker_tickets`) avec politique socle fallback pour `git://*`,
So that toute création de dossier, prise en charge multi-acteurs et interception d'accès survive au redémarrage de l'API et au `F5` (`FR-2`, `FR-22`, `FR-33`, `AD-1`, `AD-4`, `AD-6`, `NFR-PERF-2`, `NFR-REL-1`, `UJ-4`, `UJ-7`, `UJ-14`, `UJ-17`).

**Dépendances :** Dépend de `Story 22.1` et `Story 22.2`.
**REM couverts :** `REM-08`, `REM-10`, `REM-13`.
**CAP ancrées (`failed_e2e`) :** `CAP-003`, `CAP-040`, `CAP-043`, `CAP-070`, `CAP-071`, `CAP-073`, `CAP-074`, `CAP-075`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/orchestration/{assistant_folders_and_sharing,_internal/sql_assistant_folders,_internal/sql_task_notifications}.py`, `packages/orcia-core/src/orcia_core/permissions/{broker,seeds,_internal/sql_permission_broker}.py`, `apps/api/src/orcia_api/dependencies/{core_and_lifespan,portal_and_assistant}.py`, `apps/api/src/orcia_api/routers/{assistant_workspace_folders,inbox_and_leases,permission_broker}.py`.

**Acceptance Criteria:**

**Given** un utilisateur créant un dossier ou une note épinglée dans `/assistant`
**When** `POST /api/v1/assistant/folders` s'exécute puis que l'API redémarre et le navigateur exécute `F5`
**Then** l'adaptateur SQLAlchemy Asyncio écrit et relit dans `assistant_folders`, `assistant_threads` et `assistant_folder_shares` (`SELECT` PG18 retrouve le dossier), et la balise `[LAYER_5_FOLDER_CONTINUITY ...]` reste confinée à l'assemblage interne `AssistantHarness` sans jamais apparaître dans `pinned_notes` ni dans l'UI.

**Given** deux acteurs `A` et `B` sur `/inbox` ou `POST /api/v1/tasks/{id}/claim`
**When** `A` prend en charge une notification d'équipe puis `B` tente la même action
**Then** `SqlTaskNotificationRepository` et `SqlResourceLeaseRepository` persistent l'état `CLAIMED` dans `task_notifications` et `resource_leases` en PG18 tout en maintenant le verrou Redis `SET NX` et la diffusion SSE `< 500 ms`, `B` reçoit `HTTP 409`, et `/inbox` affiche la boîte de réception réelle sans redirection erronée vers `/assistant`.

**Given** un accès refusé ou testé via `POST /api/v1/permissions/broker/check-access` avec `target_uri: "git://gitlab.internal/platform/infra-core"`
**When** le `PermissionBrokerService` évalue la requête
**Then** la politique fallback configurable (`git://*`, `jira://*`, `confluence://*`) ou la fiche `workspace_datasources` est résolue (`HTTP 200`, zéro `404`), un ticket est persisté dans `permission_broker_tickets` (`SELECT` PG18 `>= 1` ligne) et l'UI affiche la carte ambre de procédure (`UX-DR11`) avec lien Jira et action de replay.

---

### Story 22.4: Persistance PG18 Orchestration (`dbos_uow`, `human_anchor_signatures`, `upstream_challenges`, `run_lock_manifests`), Gates (`gate_evaluations`, `chunk_approvals`) & Garde `KILL_SWITCH_STOPPED` (`REM-09`, `REM-11`, `REM-12`)

As a Tech Lead, Architecte, Valideur & Superviseur (`Yanis`, `Antoine`, `Claire`, `Sophie`),
I want initialiser `app.state.dbos_uow` et persister dans PostgreSQL 18 les ancres humaines (`human_anchor_signatures`), challenges amont (`upstream_challenges`), verrous de version (`run_lock_manifests`), évaluations de Gates (`gate_evaluations`, `chunk_approvals`), monter `<UpstreamChallengeRewindModal>` avec séparation stricte `/gates` vs `/processes`, et protéger `KILL_SWITCH_STOPPED` dans `_sql_autonomous_rollback.py`,
So that tout cycle d'orchestration durable, contestation What-If, validation par découpage et arrêt d'urgence survive au redémarrage de l'API et au `F5` avec une traçabilité SQL complète (`FR-4`..`FR-7`, `FR-14`..`FR-19`, `FR-29`, `AD-2`, `AD-3`, `AD-7`, `AD-11`, `AD-18`, `UJ-1`..`UJ-3`, `UJ-5`, `UJ-6`, `UJ-11`, `UJ-12`).

**Dépendances :** Dépend de `Story 22.1` et `Story 22.2`.
**REM couverts :** `REM-09`, `REM-11`, `REM-12`.
**CAP ancrées (`failed_e2e`) :** `CAP-020`, `CAP-021`, `CAP-023`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-201`.
**Fichiers impactés :** `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`, `apps/api/src/orcia_api/routers/{orchestration,blackboard_and_engine,challenge_and_replay,gates,human_gates}.py`, `packages/orcia-core/src/orcia_core/orchestration/_internal/{sql_repository,_sql_autonomous_rollback}.py`, `packages/orcia-core/src/orcia_core/gates/_internal/sql_gate_repository.py`, `apps/web/src/features/{cockpit,gates}/*`.

**Acceptance Criteria:**

**Given** un run instancié depuis le Cockpit puis signé sur une ancre violette (`>= 30` car.) et contesté via `<UpstreamChallengeRewindModal>`
**When** les mutations `POST /anchors/sign`, `POST /challenges` et `POST /replay` s'exécutent puis la page est rechargée (`F5`)
**Then** `app.state.dbos_uow` est initialisé dans `core_and_lifespan.py`, `human_anchor_signatures`, `run_lock_manifests`, `workflow_runs`, `step_executions`, `blackboard_snapshots` (append-only `ACTIVE`/`SUPERSEDED`) et `upstream_challenges` contiennent les lignes persistées en PG18, `get_orchestration_state` relit depuis PG18, et `UpstreamChallengeRewindModal` est monté et interactif (`upstream-challenge-reason-input` visible).

**Given** une Gate Déterministe, Agentique ou Humaine ouverte sur `/gates`
**When** le valideur inspecte le Briefing 4 blocs, approuve les sections par découpage (`chunk_approvals`) avec contrôle `< 15 s`, ou déclenche l'action Jira Staged puis rafraîchit (`F5`)
**Then** `/gates` affiche la vue dédiée aux Gates (sans empiler `Mes Processus` ni son formulaire permanent), et `SqlGateEvaluationRepository` persiste les évaluations et approbations dans `gate_evaluations` et `chunk_approvals` en PG18.

**Given** un run autonome arrêté d'urgence (`KILL_SWITCH_STOPPED`) et un second run audité post-hoc (`invalidate-and-restore`)
**When** `restore_help_article_and_rollback_run_sql` (`_sql_autonomous_rollback.py`) s'exécute
**Then** la clause `AND status <> 'KILL_SWITCH_STOPPED'` interdit l'écrasement d'un run stoppé par kill-switch, et le `SELECT status FROM workflow_runs WHERE status = 'KILL_SWITCH_STOPPED'` après `F5` retrouve bien la ligne arrêtée.

---

### Story 22.5: Persistance PG18 Packs Déclaratifs (`declarative_pack_bundles`) & Parcours Wizards Durables (`wizard_sessions`) (`REM-14`, `REM-15`)

As a Administrateur Plateforme & Concepteur de Packs (`Karim`, `Marc`),
I want synchroniser les manifests YAML dans `declarative_pack_bundles` au démarrage et à l'export dans `packs.py`, et raccorder intégralement `/wizards` (`DurableOnboardingWizardService` + `routes/wizards.tsx` via `@orcia/api-client`) à `wizard_sessions` tout en supprimant la triple numérotation et `sdlc_tech_lead`,
So that les bundles de packs déclaratifs et la progression des wizards survivent au redémarrage et au `F5` avec une ergonomie propre au-dessus de la ligne de flottaison (`FR-11`, `FR-28`, `FR-31`, `FR-34`, `FR-35`, `AD-1`, `AD-20`, `NFR-REL-1`, `UJ-19`).

**Dépendances :** Dépend de `Story 22.1` et `Story 22.2`.
**REM couverts :** `REM-14`, `REM-15`.
**CAP ancrées (`failed_e2e`) :** `CAP-055`, `CAP-056`, `CAP-057`, `CAP-150`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/bootstrap/{durable_wizards,_internal/sql_wizard_sessions,_internal/sql_declarative_packs}.py`, `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`, `apps/api/src/orcia_api/routers/{packs,studio_and_wizards}.py`, `apps/web/src/routes/wizards.tsx`, `packages/ui/src/primitives/DurableWizardRunnerView.tsx`.

**Acceptance Criteria:**

**Given** le démarrage du serveur FastAPI et la page `/settings/packs`
**When** les packs `packs/<domaine>/pack.yaml` sont chargés ou exportés en ZIP (`packs.py`)
**Then** un upsert idempotent (`INSERT ... ON CONFLICT DO UPDATE`) persiste les bundles et empreintes `SHA-256` dans `declarative_pack_bundles` (`SELECT COUNT(*) FROM declarative_pack_bundles >= 1` après `F5`).

**Given** l'utilisateur ouvrant `/wizards` et avançant/reculant dans un parcours guidé jusqu'à l'achèvement
**When** il interagit avec les étapes puis recharge la page (`F5`)
**Then** `routes/wizards.tsx` appelle `@orcia/api-client` (`GET`/`POST /api/v1/wizards/*`) sans état `useState` purement local, `DurableOnboardingWizardService` lit/écrit dans `wizard_sessions` PG18, `wizard-completed-badge` s'affiche après `F5`, l'identifiant brut `sdlc_tech_lead` est remplacé par son libellé métier traduit, la triple numérotation `1. #1/5 1.` est supprimée, et l'étape active apparaît au-dessus de la ligne de flottaison.

---

### Story 22.6: Coquille Direction C `8` Entrées, Mobile Companion `< 768px`, Aide Contextuelle Dynamique par Route (`docs/help/`) & Cockpit `<= 3` Blocs (`REM-17`, `REM-18`, `REM-19`, `REM-20`, `REM-21`)

As a Utilisateur Desktop & Mobile Companion (`Claire`, `Nadia`, `Marc`, `Sally`),
I want aligner la coquille sur les `8` entrées de `DESIGN.md` avec Double Sélecteur + Fil d'Ariane et état actif exact, câbler le `MobileCompanionView` (`< 768px`) avec barre basse `3` onglets + réponse SSE visible et fin des faux positifs `overflow-x: hidden`, servir une aide contextuelle dynamique par route sans `Chef1`/`aqwZSX`, et ramener le Cockpit à `<= 3` blocs réhydratés depuis PG18 sans `"LOCK TABLE..."`,
So that l'expérience globale Desktop et Mobile soit conforme à Direction C (`DESIGN.md` / `EXPERIENCE.md`) sur 100 % des écrans, y compris ceux précédemment `PASSED` (`FR-1`, `FR-3`, `FR-28`, `FR-32`, `FR-33`, `UX-DR1`, `UX-DR2`, `UX-DR13`, `UX-DR16`, `NFR-A11Y-1`, `UJ-8`, `UJ-13`, `UJ-14`, `UJ-17`, `UJ-20`).

**Dépendances :** Dépend de `Stories 22.1`..`22.5`.
**REM couverts :** `REM-17`, `REM-18`, `REM-19`, `REM-20`, `REM-21`.
**CAP ancrées (`failed_e2e`) :** `CAP-068` (+ conformité transverse `CAP-042`, `CAP-060`, `CAP-061`, `CAP-064`, `CAP-065`, `CAP-067`, `CAP-071`, `CAP-074`, `CAP-075`, `CAP-200`, `CAP-203`).
**Fichiers impactés :** `packages/ui/src/primitives/{FourZoneDirectionCShell,FourZoneSidebarRail,FourZoneTopHeaderSection,MobileCompanionView,ProgressiveDay0AccostageBanner,StreamlinedCockpitView,AssistantSpeedSelectorAndStreamView}.tsx`, `packages/ui/src/styles/tokens.css`, `apps/web/src/components/{ShellContextualHelpColumn,_contextualHelpSections,shellPresets,shellScopeOptions}.ts*`, `packages/orcia-core/src/orcia_core/catalog/contextual_help.py`, `docs/help/{fr,en}/*.md`.

**Acceptance Criteria:**

**Given** un viewport Mobile (`390×844`, `< 768px`)
**When** `FourZoneDirectionCShell` rend la coquille via `useResponsiveBreakpoint()`
**Then** la sidebar rail gauche disparaît au profit d'une barre basse fixe à `3` onglets (`Cockpit`, `Mon Assistant / Arbitrage`, `Décisions`), la `TopHeaderBar` tient sur `1` ligne (`min-w-0`), les routes Desktop-only (`/settings`, `/organization`, `/processes/studio/*`) affichent la bannière dédiée, aucun `<select>` ou bouton ne déborde hors de `390px` (y compris `/activity` et `/cockpit`), et dans `/assistant` la réponse streamée reste visible au-dessus d'un compositeur à `2` lignes propres.

**Given** la navigation Desktop dans `FourZoneSidebarRail` et `FourZoneTopHeaderSection`
**When** l'utilisateur parcourt les écrans (`Cockpit`, `/profile`, `/help`, `/finops`, `/spaces`, `/settings`)
**Then** la sidebar affiche strictement les `8` entrées de `DESIGN.md` (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`), le Double Sélecteur empilé (`Équipe / BU` + `Espace`) figure en tête de sidebar, le Breadcrumb cliquable figure dans `TopHeaderBar`, et `Cockpit` n'est plus surligné à tort sur `/profile` ou `/help`.

**Given** la colonne droite d'aide contextuelle (`340px`) et le Cockpit post-admin
**When** l'utilisateur change de route ou clique sur un bouton `ⓘ`, ou observe le Cockpit après création de `Alice Admin E2E`
**Then** `contextual_help.py` et `docs/help/{fr,en}/*.md` servent une fiche dédiée à la route active (format 4 sections, zéro `Chef1`/`aqwZSX`, zéro blocage sur `@1.1.0`), `ProgressiveDay0AccostageBanner` reflète fidèlement PG18 (`Étape 1` cochée/repliée après création admin, `Étape 2` décochée si `0` `org_units`, libellé explicite `Accostage X/5`, zéro `"LOCK TABLE users IN EXCLUSIVE MODE"`), et le Cockpit ne dépasse pas `3` blocs majeurs.

---

### Story 22.7: Finitions UX/UI (Compteurs `0`/Modales, Erreurs RFC 9457 Actionnables, Grilles, Studio V2, Assistant/`⌘K`, Devise `€`/Dates FR, Contraste `(!)`) & Purge Intégrale du Jargon Technique (`REM-22`, `REM-23`, `REM-26`, `REM-27`, `REM-28`, `REM-29`, `REM-30`, `REM-31`, `REM-32`)

As a Utilisateur Métier, Auditeur & Responsable UX (`Sally`, `Claire`, `Yanis`),
I want masquer les compteurs à `0` et convertir les formulaires permanents en modales `+ Nouveau...`, afficher des bannières RFC 9457 actionnables sur toute erreur HTTP, purger intégralement le jargon technique et les constantes brutes de l'UI/SSE, unifier l'affichage sur `€` et les dates FR, corriger les grilles `/finops`/`/profile`/`/ontology`/Studio/`/agents` MCP/`/assistant`/`⌘K`, et retirer les pastilles rouges `(!)` des boutons primaires bleus,
So that chaque écran d'ORCIA atteigne un niveau irréprochable d'ergonomie, de contraste WCAG 2.2 AA et de langage métier sans aucun terme d'implémentation (`FR-25`, `FR-26`, `FR-32..FR-36`, `NFR-A11Y-1`, `NFR-OBS-1`, `UX-DR1`, `UX-DR11`, `UX-DR12`, `UJ-1`..`UJ-20`).

**Dépendances :** Dépend de `Story 22.6`.
**REM couverts :** `REM-22`, `REM-23`, `REM-26`, `REM-27`, `REM-28`, `REM-29`, `REM-30`, `REM-31`, `REM-32`.
**CAP impactées (transverse UX) :** `CAP-002`, `CAP-003`, `CAP-010`, `CAP-023`, `CAP-030`, `CAP-051`, `CAP-052`, `CAP-054`, `CAP-060`, `CAP-062`, `CAP-065`, `CAP-069`, `CAP-073`, `CAP-075`, `CAP-080`, `CAP-082`, `CAP-083`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-150`, `CAP-160`, `CAP-200`, `CAP-201`.
**Fichiers impactés :** `apps/web/src/i18n/locales/*.ts`, `packs/*/help/**/*.md`, `packages/ui/src/primitives/{AssistantThinkingSubWindow,WorkflowStudioHeaderBar,StudioCopilotSidebar,RemoteServiceTestBenchAndMcpExposureView,FinopsGovernanceDashboardView,UserProfileOverviewPage,CommandPaletteModal,AgentExecutionTrace}.tsx`, `packages/ui/src/components/DisabledButtonAlertIndicator.tsx`, `apps/web/src/features/*`.

**Acceptance Criteria:**

**Given** les vues `/processes`, `/gates`, `/agents`, `/spaces`, `/profile` et toute mutation `@orcia/api-client` en erreur (`403`/`404`/`422`)
**When** les collections sont vides (`total === 0`) ou qu'une requête échoue côté API
**Then** les badges/compteurs `0` sont masqués, la création de processus ou d'espace passe par une modale `<OrciaDialog>` (`+ Nouveau processus` / `+ Nouvel espace`), et toute erreur HTTP déclenche `<OrciaAlertBanner>` traduite depuis le RFC 9457 en français métier actionnable (zéro échec silencieux).

**Given** les dictionnaires `i18n`, `packs/*/help/**/*.md`, `AssistantThinkingSubWindow` et `AgentExecutionTrace`
**When** l'utilisateur parcourt l'ensemble de l'application (y compris les traces réflexives `12-epic16`, l'arbitrage `19-orchestration`, `/settings/packs`, `/finops`, `/ontology` et `/spaces`)
**Then** aucune constante brute ou jargon interne (`SYNTHESIS_READY`, `OAUTH2_PASSTHROUGH`, `TECH_LEAD`, `IMMUTABLE`, `PAUSE_AND_ESCALATE`, `OPT_A_*`, `OPT_B_*`, `PENDING`, `Vitesse 2 (450 ms)`, `DeclarativePackLoader`, `orcia-connectors`, `WritePreviewCard`, `packs/<domaine>/`, `Tier cognitif`, `Guardrails`, `Dry-Run`, `AES-256-GCM`, `1024-dim RAG`, `demande_source`, `(published)`/`(draft)`, `[STALE_WARNING]`, routes brutes) n'apparaît à l'écran ; toutes les sommes utilisent `€` et toutes les dates utilisent `Intl.DateTimeFormat(locale)` (`jj/mm/aaaa`).

**Given** les grilles, Studio V2, `/agents` MCP, `/assistant`, `⌘K` et les boutons primaires désactivés
**When** ils sont rendus sur `1440×900`
**Then** `/finops` (`4` KPIs + onglets 1 ligne), `/profile` (`2×2` ou `4×1`) et `/ontology` (`2×2`) sont équilibrés ; Studio V2 supprime le doublon de version et le débordement de `Demander` ; `/agents` MCP supprime le vide gauche ; `+ Nouvelle conversation` est stylé en bouton secondaire, le pavé central est déporté vers `ⓘ`, `⌘K` masque les sections vides ; les titres numérotés et `||` doubles sont retirés ; et `DisabledButtonAlertIndicator` retire la pastille rouge `(!)` des boutons bleus et de l'onglet actif sidebar tout en évitant les troncatures abusives.

---

### Story 22.8: Activation des `5` Gardes CI Anti-Régression + `4` Verrous Anti-Faux-Positifs, Purge `ORCIA_E2E_SEED_FIXTURES` & Relecture à Froid PG18, Couverture `100 %` Assertions SQL sur `55` Blocs `test(...)`, Paramétrage `ORCIA_E2E_CAMPAIGN_DIR` & Budget `< 35s` (`REM-33`, `REM-34`)

As a Tech Lead, Architecte & QA Automation (`Amelia`, `Winston`, `Sally`),
I want activer les `5` gardes automatisées anti-régression en CI (anti-jargon UI, interdiction `display: none`, intégrité CSS Tailwind + tokens Direction C / contraste WCAG AA, interdiction `[LAYER_5_*]` & `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`, contrôle géométrique Playwright Desktop/Mobile) **et** les `4` verrous anti-faux-positifs issus de la RCA Epic 21 (`e2e-testids-sync-audit.test.ts`, helper Playwright typé OpenAPI `typedApiRequest.ts` + garde statique `e2e-openapi-helper-audit.test.ts`, purge totale de `ORCIA_E2E_SEED_FIXTURES="1"` remplacée par création via API réelle + relecture à froid PostgreSQL 18 `reloadColdFromPg()` via `POST /api/v1/_e2e/evict-memory-caches` actif uniquement si `ORCIA_ENV == "e2e"`, réécriture anti-Goodhart de `zero-dead-buttons-and-silent-catches-audit.test.tsx` sous `<RouterProvider>` réel + sonde `[role="alert"]` anti-échec HTTP silencieux), généraliser les assertions `SELECT` PostgreSQL 18 effectives sur **100 % des `55` blocs `test(...)` E2E (`110` scénarios)** avec `test_e2e_sql_coverage_audit.py`, paramétrer `ORCIA_E2E_CAMPAIGN_DIR` (ciblant `e2e-campaign-epic-22`) dans le harnais, et optimiser les temps d'exécution E2E sous `< 35 s`,
So that aucun test Vitest ou Playwright ne puisse passer à tort sur des `data-testid` orphelins, des payloads non typés, des fixtures pré-injectées ou du cache RAM, tout en préparant `Story 22.8a` puis la campagne intégrale `Story 22.9` et `Story 22.10` (`AD-17`, `NFR-TEST-1`, `NFR-PERF-1`, `NFR-A11Y-1`). *(Note : l'assainissement Fail-Closed de `vitest.setup.ts`, le test Composition Root sans override et la CI GitHub Actions complète sont portés par `Story 22.8a`, la campagne E2E intégrale + captures PNG + audit Sally × Winston + `capabilities.yaml` par `Story 22.9`, et les rapports Tech Lead + initialisation Epic 23 par `Story 22.10`.)*

**Dépendances :** Dépend de `Stories 22.1`..`22.7`. Précède `Story 22.8a`.
**REM couverts :** `REM-33`, `REM-34`.
**CAP couvertes :** `CAP-100` (`hygiène` — durcissement CI, verrous anti-faux-positifs & couverture SQL E2E `100 %` préparant `22.8a` puis `22.9`).
**Fichiers impactés :** `apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts`, `apps/web/src/__tests__/no-hidden-legacy-panels-audit.test.ts`, `apps/web/src/__tests__/css-class-integrity-audit.test.ts`, `apps/web/src/__tests__/e2e-testids-sync-audit.test.ts`, `apps/web/src/__tests__/e2e-openapi-helper-audit.test.ts`, `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`, `apps/web/e2e/support/{layoutGeometryAssertions,e2eCaptureFixture,typedApiRequest}.ts`, `apps/web/playwright.config.ts`, `apps/api/src/orcia_api/routers/` (`_e2e/evict-memory-caches` si `ORCIA_ENV == "e2e"`), `tests/unit/test_no_raw_enum_codes_in_ui_streams.py`, `tests/unit/test_e2e_sql_coverage_audit.py`, `apps/web/e2e/*.spec.ts` (assertions PG18 sur `55/55` blocs `test(...)` et budget `< 35 s`).

**Acceptance Criteria:**

**Given** les `5` gardes CI initiales + les `4` verrous anti-faux-positifs de la Story `22.8`
**When** `pnpm turbo run lint typecheck test` et `.venv/bin/pytest` s'exécutent
**Then** (1) `anti-jargon-and-secrets-ui-audit.test.ts` garantit `0` terme banni dans `i18n`, `_contextualHelpSections.ts`, `packages/ui/src` et `docs/help/` ; (2) `no-hidden-legacy-panels-audit.test.ts` garantit `0` `display: none` sur panneaux métier et `100 %` des `role="dialog"` via `Portal` ; (3) `css-class-integrity-audit.test.ts` vérifie la compilation CSS, la cohérence des tokens Direction C et l'absence de styles inline violant WCAG AA ; (4) `test_no_raw_enum_codes_in_ui_streams.py` garantit `0` `[LAYER_5_*]` dans les DTOs/streams et `0` `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC` hors tests unitaires ; (5) `e2e-testids-sync-audit.test.ts` vérifie que `100 %` des `data-testid` ciblés dans `apps/web/e2e/*.spec.ts` existent dans `apps/web/src/` ou `packages/ui/src/` ; (6) `e2e-openapi-helper-audit.test.ts` interdit les appels `page.request.post/put/patch` bruts au profit de `typedApiRequest.ts` typé sur `packages/api-client` ; (7) `zero-dead-buttons-and-silent-catches-audit.test.tsx` monte les vues sous un `<RouterProvider>` réel sans court-circuit neutre et vérifie les boutons d'action interactifs ; et (8) `layoutGeometryAssertions.ts` vérifie `rect.right <= window.innerWidth + 1`, `elementFromPoint`, la sonde `[role="alert"]` sur toute réponse HTTP `>= 400`, et la conformité Direction C / WCAG AA.

**Given** les `24` specs Playwright (`55` blocs `test(...)` produisant `110` scénarios Desktop `1440×900` + Mobile `390×844`) et le test statique `tests/unit/test_e2e_sql_coverage_audit.py`
**When** l'audit de couverture SQL E2E, la purge `ORCIA_E2E_SEED_FIXTURES` et les ciblages `14-auth` / `16-ai-models` s'exécutent
**Then** `ORCIA_E2E_SEED_FIXTURES="1"` est totalement supprimé de `apps/web/playwright.config.ts` et `apps/web/e2e/`, les mutations E2E exécutent `reloadColdFromPg()` (appelant `POST /api/v1/_e2e/evict-memory-caches` actif uniquement lorsque `ORCIA_ENV == "e2e"` et renvoyant `404` sinon) suivi d'un rechargement de page confirmant la persistance froide PG18, **100 % des `55` blocs `test(...)` E2E (`55/55`)** exécutent au moins une assertion réelle `SELECT` PostgreSQL 18 (`queryPgCount`/`queryPgRows`) adaptée au domaine testé (`test_e2e_sql_coverage_audit.py`), `e2eCaptureFixture.ts` supporte `ORCIA_E2E_CAMPAIGN_DIR`, et les parcours lents (`14-auth` #2, `16-ai-models` #2) sont optimisés sous `< 35 s` (`REM-33`).

**Given** la pyramide Python + TypeScript validée après ces ajouts
**When** `.venv/bin/pytest`, `pnpm turbo run lint typecheck test`, `lint-imports` et `lint_spine.py` s'exécutent
**Then** toutes les vérifications unitaires, statiques et architecturales passent avec `>= 90 %` de couverture unitaire et `0` anomalie, débloquant `Story 22.8a` puis la campagne en `Story 22.9`.

---

### Story 22.8a: Assainissement Fail-Closed de `vitest.setup.ts`, Test Composition Root sans Override & CI GitHub Actions Complète

As a Architecte Plateforme, Tech Lead & DevOps (`Winston`, `Amelia`),
I want découper (`< 350` lignes) et convertir le harnais `apps/web/src/__tests__/vitest.setup.ts` en mode **Fail-Closed** validé dynamiquement contre `packages/api-client/openapi.json` (UUIDv7 stricts sur `format: "uuid"` rejetant `"ws-1"`, validation `required` et `additionalProperties: false`, suppression du fallback catch-all `return jsonResponse({})` au profit d'un rejet explicite), éliminer tout fallback silencieux en mémoire RAM dans `packages/orcia-core` et prouver par un nouveau test d'intégration Couche 2 (`tests/integration/test_composition_root_zero_ram_silo_postgres18.py`) que `create_app()` démarré **sans aucun `dependency_overrides` ni injection manuelle `app.state.*`** persiste et relit les données en PostgreSQL 18 (en nettoyant `app.state.dbos_uow = uow` dans `test_epics_1_7_vertical_sql_wiring_postgres18.py` et en verrouillant par les audits AST `test_integration_no_manual_app_state_audit.py` et `test_zero_orphan_sql_adapters_audit.py`), et déployer les workflows GitHub Actions complets (`.github/workflows/ci.yml` + `.github/workflows/e2e.yml` sharded en `4` shards `--retries=0`, couverture combinée `--cov=packages/orcia-core --cov-fail-under=90` et contrat Shift-Left),
So that aucune désynchronisation de schéma DTO Frontend/Backend, aucun silo RAM caché derrière un mock `app.state` en test d'intégration, ni aucune régression sur les couches `1..5` d'ORCIA ne puisse plus franchir une PR sans échec bloquant (`AD-17`, `AD-19`, `NFR-TEST-1`, `GEMINI.md` §3/§6).

**Dépendances :** Dépend de `Story 22.8` (et `Stories 22.1`..`22.7`). Précède `Story 22.9`.
**CAP couvertes :** Hygiène transverse CI/Testing & `AD-17` (`CAP-100` reste `foundation` / `live` / `runtime`).
**Fichiers impactés :** `apps/web/src/__tests__/vitest.setup.ts` (split `< 350` L + helpers modulaires sous `apps/web/src/__tests__/mocks/`), `packages/api-client/openapi.json`, `packages/orcia-core/src/orcia_core/**` (purge fallbacks RAM résiduels), `tests/integration/test_composition_root_zero_ram_silo_postgres18.py`, `tests/integration/test_epics_1_7_vertical_sql_wiring_postgres18.py`, `tests/unit/test_integration_no_manual_app_state_audit.py`, `tests/unit/test_zero_orphan_sql_adapters_audit.py`, `.github/workflows/ci.yml`, `.github/workflows/e2e.yml`, `docs/testing-strategy.md`.

**Acceptance Criteria:**

**Given** le fichier `apps/web/src/__tests__/vitest.setup.ts` découpé en modules `< 350` lignes adossés à `packages/api-client/openapi.json`
**When** un appel `@orcia/api-client` en test Vitest cible une route inexistante, un champ manquant (`required`), un champ inconnu (`additionalProperties: false`) ou un identifiant invalide comme `"ws-1"` sur un paramètre `format: "uuid"`
**Then** le harnais *Fail-Closed* lève une erreur explicite et fait échouer le test immédiatement (`0` fallback `return jsonResponse({})`), et `pnpm --filter @orcia/web test` + `typecheck` passent à `100 %` sans aucun faux négatif ni court-circuit `isJsdom`.

**Given** le Composition Root réel `create_app()` démarré contre `PostgreSQL 18 + Redis 7.4` (`testcontainers`) sans `app.dependency_overrides` ni injection manuelle `app.state.*`
**When** `tests/integration/test_composition_root_zero_ram_silo_postgres18.py`, `test_epics_1_7_vertical_sql_wiring_postgres18.py` (nettoyé de `app.state.dbos_uow = uow`) et les audits statiques `test_integration_no_manual_app_state_audit.py` + `test_zero_orphan_sql_adapters_audit.py` s'exécutent
**Then** tous les endpoints critiques persistent et relisent à froid depuis PostgreSQL 18 sans aucun silo RAM, `0` fichier dans `tests/integration/` n'injecte manuellement `app.state.*`, et `100 %` des adaptateurs SQL dans `_internal/sql_*.py` ont au moins un appelant actif hors `tests/`.

**Given** les workflows GitHub Actions `.github/workflows/ci.yml` et `.github/workflows/e2e.yml` (`4` shards Playwright `--retries=0`)
**When** la validation complète des workflows et la pyramide locale (`pytest` couverture combinée `--cov=packages/orcia-core --cov-fail-under=90`, `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck test`, `lint_spine.py`, `pnpm site:check`) s'exécutent
**Then** la totalité des `5` couches `AD-17` et la couverture combinée `>= 90 %` passent, et la CI bloquante est opérationnelle avant le lancement de la campagne E2E intégrale en `Story 22.9`.

---

### Story 22.9: Campagne E2E Intégrale Vérité PostgreSQL 18, Captures PNG Finales (Succès & Échecs), Bilan & Audit Croisé Sally × Winston

As a UX Designer (`Sally`), Architecte (`Winston`) & Tech Lead (`Amelia`),
I want exécuter l'intégralité de la campagne Playwright E2E (`00..21` + `shell.spec.ts`, `110` scénarios Desktop `1440×900` et Mobile `390×844`) sans aucun retry ni arrêt anticipé (`--retries=0 --max-failures=0 --timeout=35000`) avec `ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-22`, archiver toutes les captures PNG d'état final (succès et échecs), rédiger le bilan factuel d'exécution, mener l'audit croisé **Sally (UX) × Winston (Architecture)** sur l'ensemble des résultats et captures, et mettre à jour honnêtement `docs/product/capabilities.yaml`,
So that ORCIA dispose d'une preuve runtime exhaustive et vérifiable post-remédiation Epic 22 sur PostgreSQL 18 et identifie sans complaisance tout échec résiduel ou axe d'amélioration UX/Architecture (`AD-17`, `NFR-TEST-1`, `GEMINI.md` §5).

**Dépendances :** Dépend de `Story 22.8` et `Story 22.8a`. Précède `Story 22.10`.
**CAP couvertes :** Vérification runtime réelle de `100 %` des `65` capacités (`62` `feature` + `3` `foundation`, `CAP-001`..`CAP-203`) dans `docs/product/capabilities.yaml`.
**Fichiers impactés :** `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json`, `docs/implementation-artifacts/e2e-campaign-epic-22/manifest.jsonl`, `docs/implementation-artifacts/e2e-campaign-epic-22/screenshots/**/*.png`, `docs/implementation-artifacts/e2e-campaign-epic-22/bilan-execution-tests-e2e-epic-22.md`, `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-sally-ux.md`, `docs/implementation-artifacts/e2e-campaign-epic-22/notes-audit-winston-architecture.md`, `docs/implementation-artifacts/e2e-campaign-epic-22/synthese-remediation-sally-winston-epic-22.md`, `docs/product/capabilities.yaml`, `infra/scripts/uj_e2e_coverage.py` (référentiel résultats campagne active).

**Acceptance Criteria:**

**Given** l'ensemble des `24` specs Playwright (`110` scénarios Desktop `1440×900` + Mobile `390×844`) configuré avec `ORCIA_E2E_CAMPAIGN_DIR=docs/implementation-artifacts/e2e-campaign-epic-22`
**When** la campagne E2E intégrale s'exécute contre PostgreSQL 18 + `pgvector` + Redis 7.4 avec `--retries=0 --max-failures=0 --timeout=35000`
**Then** la totalité des `24` specs s'exécute jusqu'au bout sans aucun `test.skip`/`test.fixme` masquant un échec, et tous les artefacts bruts sont archivés dans `docs/implementation-artifacts/e2e-campaign-epic-22/` : `playwright-results.json`, `manifest.jsonl` (`110` entrées) et `100 %` des captures PNG d'état final (succès comme échecs) sous `screenshots/`.

**Given** les artefacts bruts (`playwright-results.json`, `manifest.jsonl`, `screenshots/**/*.png`)
**When** le bilan et l'audit croisé **Sally × Winston** sont conduits
**Then** `bilan-execution-tests-e2e-epic-22.md` inventorie exactement les résultats (`passed`, `failed`, `timedOut`, `skipped`, assertions `F5` et `SELECT` PG18), `notes-audit-sally-ux.md` analyse les captures PNG Desktop/Mobile (ergonomie, surcharge, jargon, accessibilité), `notes-audit-winston-architecture.md` évalue la conformité `AD-1`..`AD-24`, et `synthese-remediation-sally-winston-epic-22.md` consolide chaque échec résiduel et chaque point d'amélioration priorisé (`P0`..`P3`) en chantiers structurés.

**Given** l'état réel observé dans `docs/implementation-artifacts/e2e-campaign-epic-22/playwright-results.json`
**When** `docs/product/capabilities.yaml` est mis à jour et validé par `pnpm site:sync && pnpm site:check`
**Then** toute capacité dont `100 %` des specs E2E associées sont vertes passe à `verification: runtime` (`verified_at` à jour, `e2e_remediation_ref` supprimé), tandis que toute capacité touchée par au moins un échec résiduel est honnêtement maintenue/marquée en `verification: failed_e2e` en vue de son traitement dans `Story 22.10` / `Epic 23`.

---

### Story 22.10: Rapports Tech Lead Individuels pour Tests en Échec & Plan Sally × Winston, Plan de Correction Global & Initialisation Epic 23

As a Tech Lead (`Amelia`) & Architecte (`Winston`),
I want conduire l'analyse d'impact GitNexus (`repo: "ORCIA"`) sur les constats issus de la campagne Epic 22, rédiger les Rapports Tech Lead individuels (`23-1-...` à `23-N-...`) pour chaque lot cohérent couvrant les tests E2E en échec et les points d'amélioration du plan Sally × Winston (`synthese-remediation-sally-winston-epic-22.md`), produire le plan de correction global `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`, et initialiser complètement l'**Epic 23** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml` avec un test automatique `tests/unit/test_epic22_to_epic23_traceability.py`,
So that chaque échec résiduel ou amélioration identifié à l'issue de l'Epic 22 démarre dans l'Epic 23 avec une traçabilité totale et zéro angle mort (`GEMINI.md` § Policy, `AD-17`).

**Dépendances :** Dépend de `Story 22.9`. Clôture l'Epic 22.
**CAP couvertes :** `none (gouvernance documentaire & planification Epic 23 — rattache toute capacité failed_e2e résiduelle et tout chantier Sally × Winston Epic 22)` — classification : `doc`.
**Fichiers impactés :** `docs/implementation-artifacts/tech-lead-reports/23-1-*.md` .. `23-N-*.md`, `docs/implementation-artifacts/tech-lead-reports/README.md`, `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`, `docs/planning-artifacts/epics.md` (ajout `Epic 23`), `docs/implementation-artifacts/sprint-status.yaml` (ajout `epic-23` + `23-1..23-N`, clôture `epic-22: done`), `docs/product/capabilities.yaml` (références `e2e_remediation_ref`), `tests/unit/test_epic22_to_epic23_traceability.py`.

**Acceptance Criteria:**

**Given** l'ensemble des tests E2E en échec de `bilan-execution-tests-e2e-epic-22.md` et des points d'amélioration du plan Sally × Winston (`synthese-remediation-sally-winston-epic-22.md`)
**When** le Tech Lead exécute l'analyse d'impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` avec `repo: "ORCIA"`) sur les symboles et modules concernés
**Then** tous les échecs E2E résiduels et points d'amélioration Sally × Winston sont regroupés en `N` lots cohérents (`Story 23.1` à `Story 23.N`), chacun doté d'un Rapport Tech Lead pré-implémentation individuel (`docs/implementation-artifacts/tech-lead-reports/23-1-...-tech-lead-report.md` .. `23-N-...`) conforme à `TECH-LEAD-REPORT-TEMPLATE.md` et enregistré dans `docs/implementation-artifacts/tech-lead-reports/README.md`.

**Given** le plan de correction global `docs/planning-artifacts/sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md`
**When** il consolide la feuille de route de l'Epic 23
**Then** il contient l'ordonnancement par vagues et les matrices complètes reliant chaque échec E2E résiduel, chaque point d'amélioration Sally × Winston et chaque éventuelle `CAP-*` en `failed_e2e` à une Story `23.k` et son rapport Tech Lead `23-k-*`.

**Given** l'initialisation complète de l'**Epic 23** dans `epics.md`, `sprint-status.yaml` et `capabilities.yaml`, ainsi que `tests/unit/test_epic22_to_epic23_traceability.py`
**When** `.venv/bin/pytest tests/unit/test_epic22_to_epic23_traceability.py`, `.venv/bin/python scripts/check_implementation_docs.py` et `pnpm site:sync && pnpm site:check` s'exécutent
**Then** `100 %` de traçabilité bidirectionnelle est prouvée (aucun échec E2E ni point Sally × Winston orphelin), `epic-22` passe à `done`, et `Epic 23` est prêt pour exécution immédiate.

---

## Epic 23: Déblocage Reset PG18/Redis, Transport SSE Authentifié, Zone 4 & Accostage `X/6`, Sobriété Direction C, Durcissement Anti-Goodhart, Campagne Desktop `52/52` & Clôture Conditionnelle

Résoudre de manière définitive et vérifiable par PostgreSQL 18 les échecs E2E (`3` rejets `HTTP 401` directs + `87` cascades `resetDay0()`) répartis sur `24` specs ainsi que les `13` chantiers `REM23-01`..`REM23-13` (`12` défauts UX/UI Sally `P0-UX-1`..`P3-UX-12` + `10` défauts d'architecture Winston `ARCH23-01`..`ARCH23-10`) sur la séquence **`23.1`..`23.5` $\rightarrow$ `23.6a` $\rightarrow$ `23.7` $\rightarrow$ `23.8`**, avec report explicite de la **`Story 23.6` et de la compatibilité Mobile Companion (`--project=mobile-companion`, `390×844`, `CAP-042`) vers `ACTION_ITEM-23.6`** pour priorisation ultérieure. Durant l'Epic 23, chaque lot applique l'**Étape 0 Réconciliation E2E ↔ `DESIGN.md`** et la **Chaîne Canari Desktop Obligatoire**, suivis du **Tir de reconnaissance Desktop V0** en sortie de `23.6a`, de la campagne figée `--project=desktop-cockpit` (`24` specs / `55` scénarios Desktop) en `23.7` et d'une clôture directe sans `Epic 24` vide si `52/52` PASS Desktop et `0` écart `P0`/`P1` en `23.8`.

### Story 23.1: Déblocage `resetDay0()` (`TRUNCATE CASCADE` E2E Isolé `orcia_e2e`), Protection `connector_schemes` & Purge Redis `FLUSHDB` (`REM23-01` / `ARCH23-01`)

As a Ingénieur Plateforme & Mainteneur du Harnais E2E (`Winston`),
I want protéger `connector_schemes` dans `09_reset_db_first_boot.py` sans affaiblir aucun trigger append-only, et implémenter dans `infra/scripts/e2e/reset_day0.py` (sous garde bloquant `is_isolated_e2e_database_url` `orcia_e2e` uniquement) un `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` excluant `alembic_version` et `connector_schemes` complété par un nettoyage `dbos.*`, un reset `platform_auth_settings` (`boot_epoch`), une éviction caches API et un `FLUSHDB` Redis (`state["redis_url"]`),
So that l'insertion réelle de lignes `step_executions`, `blackboard_snapshots` et `audit_ledger` par les tests E2E (tels que `#10`) ne provoque plus jamais de `RestrictViolationError` en cascade (`87` échecs `#11`–`#110`) tout en respectant strictement la politique `GEMINI.md` interdisant `DISABLE TRIGGER`.

**Dépendances :** Clôture de `Story 22.10`. Vague 0 (`P0`), bloque `Story 23.3`–`23.6`.
**CAP couvertes :** `CAP-003`, `CAP-011`, `CAP-020`, `CAP-021`, `CAP-022`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-054`, `CAP-065`, `CAP-082`, `CAP-140`, `CAP-200`, `CAP-201` (et déblocage des `87` échecs `beforeEach` `#11`–`#110`).
**Fichiers impactés :** `infra/scripts/maintenance/09_reset_db_first_boot.py`, `infra/scripts/e2e/reset_day0.py`, `apps/web/e2e/support/day0.ts`, `tests/unit/`, `tests/integration/`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-1-reset-jour0-e2e-truncate-cascade-connector-schemes-et-redis-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une base `orcia_e2e` contenant des lignes dans `users`, `workflow_runs`, `step_executions`, `blackboard_snapshots` (protégée `BEFORE UPDATE OR DELETE ... FOR EACH ROW` + FK `ON DELETE RESTRICT`), `audit_ledger`, `connector_schemes` et des clés actives dans Redis (`help:*`, `lock:step:*`)
**When** `reset_day0.py` s'exécute après validation de `is_isolated_e2e_database_url(database_url)`
**Then** toutes les tables applicatives et append-only (hors `alembic_version` et `connector_schemes`) sont vidées via `TRUNCATE TABLE ... RESTART IDENTITY CASCADE`, `connector_schemes` reste peuplée, les triggers `trg_blackboard_snapshots_append_only` et `prevent_audit_ledger_mutation` demeurent actifs (`0` `DISABLE TRIGGER`), Redis est vidé par `FLUSHDB`, et un test `testcontainers` PG18 + Redis prouve `COUNT(*) == 0` sur `users`/`step_executions`/`blackboard_snapshots` et l'enchaînement vert `03-human-led` → `04-multi-actor` → `shell.spec.ts`.

**Given** une chaîne de connexion pointant hors de la base isolée `orcia_e2e` ou une invocation de `09_reset_db_first_boot.py`
**When** `reset_day0.py` ou `09_reset_db_first_boot.py` s'exécute
**Then** `reset_day0.py` refuse immédiatement l'exécution par `RuntimeError` hors `orcia_e2e`, et `09_reset_db_first_boot.py` préserve `connector_schemes` dans `PROTECTED_TABLES` sans jamais utiliser `TRUNCATE` sur les tables append-only ni `DISABLE TRIGGER`.

---

### Story 23.2: Transport SSE Authentifié `createRequestSse`, Alignement *Fail-Closed* `00-stack-smoke` (#3/#4) & Diagnostic `401` Session Expirée (`REM23-02`, `REM23-03`, `REM23-04`)

As a Utilisateur de `Mon Assistant` & Architecte Sécurité (`Sally` × `Winston`),
I want factoriser une primitive `createRequestSse` dans `packages/api-client/src/helpers.ts` (injectant `Authorization: Bearer`, `credentials: "include"`, `Accept-Language`, refresh `401` et parsing RFC 9457 `OrciaProblemError`, tout en scindant `bootstrapAndOntology.ts` > 400 L), migrer `streamAssistantTurnSse`, `useReflexiveExecutionController` (`/trace-stream`) et `useWorkspaceEventsSse` (`/events/stream`, protégé serveur par `resolve_request_user` + `_enforce_inbox_workspace_guard`), aligner `00-stack-smoke.spec.ts` #3/#4 sur `ORCIA_ENV="e2e"`, et corriger le message d'erreur `401` dans `useAssistantStreamingTurn.ts` (`P0-UX-1`),
So that les `3` échecs `HTTP 401` directs disparaissent sans relâcher la sécurité serveur, les flux `/trace-stream` et `/events/stream` soient authentifiés, et une session expirée affiche une alerte claire avec action `Se reconnecter →` au lieu d'accuser le modèle IA.

**Dépendances :** Aucun prérequis bloquant hors Vague 0 (parallélisable/séquentiel avec `Story 23.1`, avant Vague 1).
**CAP couvertes :** `CAP-004`, `CAP-040`, `CAP-071`, `CAP-074`, `CAP-075`, `CAP-160`.
**Fichiers impactés :** `packages/api-client/src/helpers.ts`, `packages/api-client/src/domains/bootstrapAndOntology.ts` (+ `assistantStreaming.ts`), `apps/api/src/orcia_api/routers/inbox_and_leases.py`, `apps/web/src/features/shared/useReflexiveExecutionController.ts`, `apps/web/src/components/useWorkspaceEventsSse.ts`, `apps/web/src/features/inbox/useAssistantStreamingTurn.ts`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/e2e/00-stack-smoke.spec.ts`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-2-transport-sse-authentifie-createrequestsse-smoke-00-et-diagnostic-401-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un utilisateur authentifié envoyant un message dans `Mon Assistant` ou suivant une trace réflexive `/trace-stream` / un flux `/events/stream`
**When** le client `@orcia/api-client` ouvre le flux SSE via `createRequestSse`
**Then** l'en-tête `Authorization: Bearer` et `Accept-Language` sont automatiquement transmis (test `02-assistant` #7 vert avec `DeterministicCassetteLLM`), `GET /api/v1/events/stream` rejette en `401` sans jeton et en `403` hors périmètre workspace, et `00-stack-smoke.spec.ts` #3/#4 vérifient explicitement le rejet `401` anonyme puis réussissent avec jeton premier admin.

**Given** un flux `Mon Assistant` recevant une erreur `OrciaProblemError` de statut `401` ou `403` vs `502`/`503`/`504`
**When** `useAssistantStreamingTurn` affiche le bandeau d'erreur (`role="alert"`)
**Then** un rejet `401`/`403` affiche un message métier FR/EN (*« Votre session a expiré ou doit être renouvelée pour continuer la conversation. »*, zéro code `HTTP 401`, zéro accusation du modèle IA, contraste WCAG AA `>= 4,5:1`) accompagné d'un CTA **`Se reconnecter →`** vers `/login`, tandis que le diagnostic d'indisponibilité IA reste réservé aux erreurs `502`/`503`/`504` / pannes réseau.

---

### Story 23.3: Zone 4 (`Aide Contextuelle`) 100 % Fidèle à la Route, Blocs `DESIGN.md` Restaurés & Suppression de la Plomberie Interne (`REM23-05`)

As a Utilisateur découvrant ORCIA sur `/cockpit`, `/assistant` ou les écrans métiers (`Sally`),
I want supprimer l'écrasement global `GENERAL_SECTIONS_FR` dans `ShellContextualHelpColumn.tsx:L71` (et le `catch {}` muet + init optimiste `["BASE","PACK","WORKSPACE"]`), étendre `contextual_help_loader.py` & `HelpArticleSchemaItem` (`real_example_text`, `common_pitfalls_items`) pour rendre nativement les `4` blocs prescrits par `DESIGN.md` (`À quoi sert cet écran`, `EN N GESTES`, encadré ambre `UN EXEMPLE RÉEL`, `CE QUI COINCE SOUVENT`), scinder `ContextualHelpColumnAndCenter.tsx` (`394` L), masquer la plomberie `@version` / `Sources du guide` aux non-admins et ajouter un indicateur visuel de scroll sur `FourZoneHelpAsideColumn.tsx`,
So that Zone 4 n'affiche plus jamais de fiches Cockpit sur `/assistant` ni de métadonnées internes brutes et présente l'aide structurée attendue par `DESIGN.md`.

**Dépendances :** Vague 0 (`Story 23.1`, `Story 23.2`).
**CAP couvertes :** `CAP-064`, `CAP-068`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/catalog/contextual_help_loader.py`, `docs/help/{fr,en}/*.md`, `apps/api/src/orcia_api/schemas/catalog.py`, `apps/api/src/orcia_api/routers/portal_and_help.py`, `packages/api-client`, `apps/web/src/components/{ShellContextualHelpColumn,contextualHelpCatalog,_contextualHelpSections}.ts*`, `packages/ui/src/primitives/{ContextualHelpColumnAndCenter,FourZoneHelpAsideColumn}.tsx`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-3-zone-4-aide-contextuelle-fidele-a-la-route-et-4-blocs-design-md-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un utilisateur naviguant vers `/assistant` puis `/cockpit` avec le panneau Zone 4 ouvert
**When** `/api/v1/help/resolve` retourne le guide Markdown de la route active
**Then** Zone 4 affiche exclusivement les sections de la route active (zéro carte `"Le Cockpit regroupe..."` sur `/assistant`, zéro incohérence avec `Polyvalent · Standard`), rend nativement `À quoi sert cet écran`, `EN N GESTES`, l'encadré ambre `UN EXEMPLE RÉEL` et `CE QUI COINCE SOUVENT`, masque `@version` / `Sources du guide : BASE...` hors tiroir technique admin, loge proprement toute erreur réseau sans `catch {}` silencieux, et affiche un repère de défilement si le contenu excède la hauteur.

---

### Story 23.4: Unification `Accostage X/6` PG18, Suppression des Fantômes Jour 0 (`AP`, `Notifications 4`) & Ergonomie Modale Premier Admin (`REM23-06`, `REM23-07`, `REM23-08`)

As a Premier Administrateur amorçant ORCIA au Jour 0 (`Sally` × `Winston`),
I want supprimer le split-brain backend (`{"first-admin"}` en dur dans `progressive_accostage.py:L146`) vs frontend (`/5` sans `adminCreated` dans `platformSetupStore.tsx`, `521` L à scinder) pour aligner toute la pile sur une source PG18 unique **`Accostage X/6`** (incluant `workspace_llm_tier_mappings`), supprimer le profil fantôme `AP` et `Notifications 4` lorsque `platformAdmin === null` (`0` utilisateur en base), homogénéiser les entrées verrouillées au Jour 0 tout en purgeant les `5` props mortes de `ShellContainer.tsx` (`403` L), et corriger `FirstBootAdminSetupModal.tsx` (zéro double `Annuler (Esc)`, placeholder vide + bouton œil, hiérarchie CTA `#2563EB`),
So that le parcours Jour 0 soit fidèle à la réalité PostgreSQL 18 sans identité fantôme, sans compteur dupliqué ni troncature, et doté d'une modale de premier démarrage irréprochable.

**Dépendances :** Vague 0 (`Story 23.1`, `Story 23.2`).
**CAP couvertes :** `CAP-005`, `CAP-060`, `CAP-061`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py`, `apps/web/src/components/{platformSetupStore,platformSetupAccostage,platformSetupHydration,ShellContainer,shellPresets,shellScopeOptions,FirstBootAdminSetupModal}.ts*`, `apps/web/src/features/cockpit/index.tsx`, `packages/ui/src/primitives/{ProgressiveDay0AccostageBanner,FourZoneSidebarRail,RadixDesignSystemPrimitives}.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/e2e/shell.spec.ts`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-4-unification-accostage-x-sur-6-fin-fantomes-jour0-et-modale-admin-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une plateforme fraîchement réinitialisée au Jour 0 (`0` utilisateur dans `users`)
**When** la SPA démarre et affiche la modale obligatoire `FirstBootAdminSetupModal`
**Then** aucun profil fantôme `AP` ni compteur `Notifications 4` n'apparaît dans la coquille, les entrées verrouillées portent un état désactivé uniforme et explicite (tout en respectant la garde RBAC de `Configuration` vérifiée par `shell.spec.ts`), la modale ne comporte ni double bouton `Annuler (Esc)` ni points noirs `••••••••••••` pré-remplis, dispose d'un bouton œil et d'un CTA primaire `#2563EB` net, et après création du premier admin + `F5`, un unique badge **`Accostage 1/6`** (puis `2/6` après modèle IA dans `workspace_llm_tier_mappings`) s'affiche sans doublon `1. Modèles IA` ni libellé tronqué.

---

### Story 23.5: Sobriété Cockpit (`<= 3` Blocs), `TopHeaderBar` Sans Doublon/Troncatures, Logo Zone 1, Épuration `/assistant` & `/login` et Preuves `#10` (`REM23-09`..`REM23-12`)

As a Utilisateur quotidien d'ORCIA sur Desktop (`1440×900`) & Auditeur UX (`Sally`),
I want ramener `/cockpit` à **`<= 3` blocs visuels** (montage conditionnel de `CockpitHumanLedGovernanceSection` lorsqu'une décision/run le requiert), supprimer `topbar-fixed-workspace-selector` dupliqué sur Desktop `>= 768px`, déplacer le logo `ORCIA` en tête de Zone 1 (`DESIGN.md` §2.1), inclure l'équipe dans `buildShellBreadcrumbItems`, raccourcir le placeholder de recherche à `Rechercher… (⌘K)`, doter le loader initial et `/login` du logo ORCIA + bouton œil, exclure `/assistant` (`inbox`) de la carte d'en-tête `ModuleWorkspaceView`, masquer les compteurs `(0)` (avec mise à jour `02-assistant.spec.ts`), unifier `orcia-ds-btn` + contraste `➤`, remplacer `"embedding"` par `"indexation sémantique"` dans `fr.ts`, et ajouter des captures intermédiaires sur `HumanLedAnchorCard`/`ArbitrationTieBreakCard` dans `03-human-led-anchor-and-arbitration.spec.ts`,
So that l'écran principal respecte la Loi de Hick sans aucune troncature à `1440px`, l'espace `/assistant` soit épuré de tout jargon et les cartes identitaires `#6D28D9`/`#D97706` soient auditables visuellement.

**Dépendances :** Vague 0 (`Story 23.1`, `Story 23.2`).
**CAP couvertes :** `CAP-001`, `CAP-023`, `CAP-041`, `CAP-062`, `CAP-070`, `CAP-072`, `CAP-073`, `CAP-190`.
**Fichiers impactés :** `apps/web/src/features/cockpit/{index,CockpitRunsSection,CockpitHumanLedGovernanceSection}.tsx`, `packages/ui/src/primitives/{StreamlinedCockpitView,FourZoneTopHeaderSection,FourZoneSidebarRail,BiModeLoginView,AssistantSpeedSelectorAndStreamView}.tsx`, `apps/web/src/components/{shellPresets,ShellAuthFallbackView,ModuleWorkspaceView}.ts*`, `apps/web/src/features/inbox/{index,SavedConversationsAndThreadView}.tsx`, `apps/web/src/i18n/locales/fr.ts`, `apps/web/e2e/{02-assistant-streaming-and-folders,03-human-led-anchor-and-arbitration}.spec.ts`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-5-sobriete-cockpit-topbar-sans-doublon-assistant-et-login-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un utilisateur connecté naviguant sur `/cockpit`, `/assistant` et `/login` en résolution Desktop `1440×900`
**When** les composants Direction C mis à jour sont rendus
**Then** `/cockpit` présente au plus `3` blocs visuels distincts sans montage à vide au bas de la page, la `TopHeaderBar` ne contient plus `topbar-fixed-workspace-selector` ni aucune troncature sur le fil d'Ariane ou la recherche `Rechercher… (⌘K)`, le logo `ORCIA` figure en tête de Zone 1 et sur `/login` (avec bouton œil), `/assistant` n'affiche ni double carte d'en-tête ni compteur `(0)` ni terme `"embedding"` (sélecteurs `02-assistant.spec.ts` synchronisés), et `03-human-led-anchor-and-arbitration.spec.ts` attache les captures de preuve de `HumanLedAnchorCard` (`#6D28D9`) et `ArbitrationTieBreakCard` (`#D97706`).

---

### Story 23.6: Stabilisation Specs `04`–`21` & Mobile Companion (`390×844`) & Audit `100 %` Assertions SQL PostgreSQL 18 Effectives (`55/55` Blocs E2E) (`REM23-13` / `ARCH23-10`) *(Reportée en `ACTION_ITEM-23.6`)*

> **Décision de report (`Step 2a Epic 23`, 2026-11-19)** : La **Story `23.6`** ainsi que l'ensemble du périmètre de compatibilité/fonctionnement Mobile (`--project=mobile-companion`, `390×844`, `CAP-042` et assertions responsive mobile) sont **déplacés vers `action_items:` (`ACTION_ITEM-23.6` dans `docs/implementation-artifacts/sprint-status.yaml`)** pour priorisation ultérieure. Le durcissement SQL PG18 effectif (`55/55` blocs E2E sans `SELECT 1` ni table alibi) est repris dans **`Story 23.6a`**, et l'exécution E2E Desktop (`--project=desktop-cockpit`, `1440×900`, `24` specs / `55` scénarios Desktop) dans **`Story 23.7`**.

As a Architecte (`Winston`), UX Designer (`Sally`) & Tech Lead (`Amelia`),
I want stabiliser l'ensemble des parcours `04`–`21`, `shell.spec.ts` et `mobile-companion` (`390×844`) mis au jour après le déblocage de `resetDay0()` (`23.1`–`23.5`), et auditer puis renforcer chacun des `55` blocs `test(...)` E2E (`55/55` sur `24` specs) afin que chaque bloc exécute des vérifications effectives en base de données PostgreSQL 18 (`expectDbRowExists`, `expectDbRowCount`, `queryDbRows` ciblant les tables réelles du domaine testé — zéro assertion purement mémoire, zéro `SELECT 1` ou requête factice),
So that l'ensemble des `24` specs soit vert en Desktop comme en Mobile Companion et que la preuve SQL PostgreSQL 18 soit irréfutable avant le gel applicatif de la campagne intégrale en `Story 23.7` (`P0-UX-2`, `AD-17`, `GEMINI.md` §3).

**Statut Sprint :** Déplacée vers `action_items:` (`ACTION_ITEM-23.6`, `status: open`, `priority: P2`).
**Dépendances :** Clôture de `Stories 23.1`..`23.5` (reportée hors chemin critique Epic 23 via `ACTION_ITEM-23.6`).
**CAP couvertes :** `CAP-042` *(maintenue `failed_e2e` vers `ACTION_ITEM-23.6`)* ; les autres `CAP-*` Desktop sont vérifiées en `Story 23.7`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-6-campagne-e2e-integrale-mobile-companion-audit-et-62-capacites-runtime-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** le report explicite du périmètre Mobile Companion (`--project=mobile-companion`, `390×844`, `CAP-042`) vers `ACTION_ITEM-23.6`
**When** la priorisation ultérieure reprendra ce chantier Mobile Companion
**Then** les specs `04`–`21`, `shell.spec.ts` et `05-mobile-companion-and-rgaa.spec.ts` seront stabilisées sur `390×844` (barre basse 3 onglets, zéro overflow horizontal, bannière desktop-only sur `/configuration` et `/organization`) sans `ORCIA_E2E_SEED_FIXTURES` ni `test.skip` masquant un échec.

---

### Story 23.6a: Durcissement Anti-Goodhart : Gardes OpenAPI `security`, Audits AST (`catch` muets, Constantes Fantômes, SQL Domaine, Jargon), Contrats Géométriques Direction C & Reset PG18 Dynamique (`CAP-100`, `hygiène`)

As a Architecte (`Winston`), Tech Lead (`Amelia`) & UX Designer (`Sally`),
I want fermer les `4` failles de type « loi de Goodhart » identifiées par la RCA Epic 22 (1. introspection SQL dynamique `information_schema.tables` & `pg_constraint` dans `reset_day0.py` & `09_reset_db_first_boot.py` ; 2. enforcement de `operation.security` dans `vitestFetchTransport` + interdiction AST/ESLint de `fetch(` et `new EventSource(` hors `packages/api-client/src/helpers.ts` ; 3. détection AST des `catch` muets et constantes fantômes sur `100 %` de `apps/web/src/**`, durcissement AST de `test_e2e_sql_coverage_audit.py` interdisant `SELECT 1` et tables hors domaine sur les `55` blocs `test(...)` E2E, et regex structurelles anti-jargon ; 4. contrats géométriques & sobriété Direction C Desktop `1440×900` dans `layoutGeometryAssertions.ts` branchés sur `shell.spec.ts` et `11-screens-smoke-without-server-errors.spec.ts` + helper `captureMilestoneScreenshot`), puis valider la **Chaîne Canari Desktop Obligatoire** et le **Tir de reconnaissance Desktop V0** (`24` specs / `55` scénarios Desktop sous `--project=desktop-cockpit`),
So that aucun test unitaire, test Vitest, contrôle AST ou parcours E2E Desktop ne puisse plus produire de faux positif avant le gel de la campagne figée `Story 23.7` (`AD-17`, `AD-19`, `NFR-TEST-1`, `DESIGN.md`, `CAP-100`).

**Dépendances :** Clôture de `Stories 23.1`..`23.5` (et **Étape 0 Réconciliation E2E ↔ `DESIGN.md`**). Précède et bloque `Story 23.7`.
**CAP couvertes :** `CAP-100` (`hygiène`).
**Fichiers impactés :** `infra/scripts/e2e/reset_day0.py`, `infra/scripts/maintenance/09_reset_db_first_boot.py`, `tests/unit/test_e2e_reset_day0_guard.py`, `tests/integration/test_e2e_reset_day0_postgres18_and_redis.py`, `apps/web/src/__tests__/setup/{transportAndOpenApiValidator,openApiRequestValidator}.ts`, `apps/web/src/__tests__/{vitest-transport-fail-closed-openapi.test.ts,zero-dead-buttons-and-silent-catches-audit.test.tsx,anti-jargon-and-secrets-ui-audit.test.ts}`, `tests/unit/test_e2e_sql_coverage_audit.py`, `apps/web/e2e/support/{layoutGeometryAssertions,e2eCaptureFixture}.ts`, `apps/web/e2e/{shell,11-screens-smoke-without-server-errors}.spec.ts` (et mise à niveau de toute spec E2E présentant une requête SQL alibi).
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-6a-durcissement-anti-goodhart-gardes-openapi-ast-geometrie-et-reset-pg18-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** le harnais Reset Jour 0 (`reset_day0.py` & `09_reset_db_first_boot.py`) exécuté sur une base PostgreSQL 18 (`testcontainers`) + Redis 7.4
**When** l'introspection SQL dynamique interroge `information_schema.tables` (`public`, `dbos`) et `pg_constraint`
**Then** aucune table créée par Alembic n'est orpheline de la stratégie de purge/protection, zéro `DISABLE TRIGGER` n'est utilisé, les contraintes `ON DELETE RESTRICT` et triggers append-only (`audit_ledger`, `blackboard_snapshots`) demeurent intacts, Redis atteint `DBSIZE == 0`, et les seeds socles `connector_schemes` & `catalog_items` restent intacts.

**Given** le transport Vitest (`vitestFetchTransport` / `openApiRequestValidator.ts`) validé contre `packages/api-client/openapi.json` et le code source `apps/web/src/**` + `packages/api-client/src/domains/**`
**When** une requête est émise sans en-tête `Authorization: Bearer <non-vide>` vers une opération déclarant `security` dans `openapi.json`, ou lorsqu'un fichier applicatif appelle directement `fetch(` ou `new EventSource(`
**Then** `vitestFetchTransport` rejette immédiatement l'appel en `HTTP 401 application/problem+json` (prouvé dans `vitest-transport-fail-closed-openapi.test.ts`) et l'audit AST / ESLint échoue immédiatement sur tout contournement `fetch(` / `new EventSource(` hors `packages/api-client/src/helpers.ts`.

**Given** les gardes AST frontend (`apps/web/src/__tests__/`) et Python (`tests/unit/test_e2e_sql_coverage_audit.py`)
**When** les audits s'exécutent sur `100 %` de `apps/web/src/**`, `apps/web/src/i18n/locales/`, `docs/help/` et les `55` blocs `test(...)` des `24` specs `apps/web/e2e/*.spec.ts`
**Then** tout `catch {}` / `.catch(() => ...)` muet, toute constante fantôme (`DEFAULT_HUMAN_PROFILE`, `GENERAL_SECTIONS_*`, compteur d'accostage parallèle), toute chaîne jargon structurée (`\bHTTP\s+[45]\d\d\b`, `@\d+\.\d+\.\d+`, `\b[A-Z]{3,}\s*→\s*[A-Z]{3,}\b`, `\(Esc\)`, `SCREAMING_SNAKE_CASE` multi-segments), et toute requête SQL alibi (`SELECT 1` ou table hors domaine) est rejeté automatiquement, et `100 %` des `55` blocs E2E vérifient au moins une table PostgreSQL 18 du domaine métier.

**Given** les contrats géométriques Direction C (`layoutGeometryAssertions.ts`) et `captureMilestoneScreenshot` (`< 440 KB`) branchés sur `shell.spec.ts` et `11-screens-smoke-without-server-errors.spec.ts` sous `--project=desktop-cockpit` (`1440×900`)
**When** la **Chaîne Canari Desktop Obligatoire** puis le **Tir de reconnaissance Desktop V0** (`24` specs / `55` scénarios Desktop) s'exécutent
**Then** `/cockpit` affiche `<= 3` blocs, Zone 1 / Zone 2 / Accostage n'ont aucune troncature, `<= 1` sélecteur d'espace visible existe sur Desktop, `<= 1` bouton annuler/fermer apparaît par dialog, `0` `placeholder` contient `•`, Zone 4 change effectivement avec ses `4` blocs `DESIGN.md` sur `/cockpit -> /assistant -> /spaces`, et l'ensemble des 5 couches `AD-17` est `100 %` vert avant `Story 23.7`.

---

### Story 23.7: Campagne Playwright E2E Intégrale Desktop Epic 23 (`--project=desktop-cockpit`), Captures PNG d'État Final (`55/55`), Bilan Exhaustif & Audit Croisé Sally × Winston

As a UX Designer (`Sally`), Architecte (`Winston`) & Tech Lead (`Amelia`),
I want exécuter sans retouche de code applicatif l'intégralité de la campagne Playwright E2E **Desktop** (`--project=desktop-cockpit`, `1440×900`, `24` specs, `55` scénarios Desktop dont `52` exécutés et `3` `mobile-only` skipped, `--retries=0 --max-failures=0 --timeout=35000`, `0` `ORCIA_E2E_SEED_FIXTURES`) après validation `100 %` verte de `23.1`..`23.5` + `23.6a` sur les 5 couches `AD-17` et le Tir de reconnaissance Desktop V0 vers `docs/implementation-artifacts/e2e-campaign-epic-23/`, archiver `playwright-results.json`, `manifest.jsonl` et `100 %` des captures PNG d'état final (`55/55` Desktop, `< 450 KB` par fichier), rédiger le bilan exhaustif `bilan-execution-tests-e2e-epic-23.md`, conduire l'audit croisé **Sally (UX) × Winston (Architecture)** (`notes-audit-sally-ux.md`, `notes-audit-winston-architecture.md`, `synthese-remediation-sally-winston-epic-23.md`), basculer `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py` et mettre à jour honnêtement `docs/product/capabilities.yaml` (en maintenant `CAP-042` Mobile Companion `failed_e2e` avec `e2e_remediation_ref: "ACTION_ITEM-23.6"`),
So that 100 % des User Journeys (`UJ-1`..`UJ-20`) et des capacités Desktop (`61/62` `feature` + `3/3` `foundation`) disposent d'une preuve runtime et visuelle irréfutable sans maquillage (`P0-UX-2`, `AD-17`, `NFR-TEST-1`, `GEMINI.md` §5).

**Dépendances :** Clôture complète à `100 %` vert sur les 5 couches `AD-17` de `Stories 23.1`..`23.5` et `Story 23.6a`. Précède `Story 23.8`.
**CAP couvertes :** Vérification runtime réelle sur Desktop de `61 / 62` capacités `feature` + `3 / 3` `foundation` (`CAP-001`..`CAP-203`), `CAP-042` restant `failed_e2e` vers `ACTION_ITEM-23.6`.
**Fichiers impactés :** `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`, `docs/implementation-artifacts/e2e-campaign-epic-23/manifest.jsonl`, `docs/implementation-artifacts/e2e-campaign-epic-23/screenshots/**/*.png`, `docs/implementation-artifacts/e2e-campaign-epic-23/bilan-execution-tests-e2e-epic-23.md`, `docs/implementation-artifacts/e2e-campaign-epic-23/notes-audit-sally-ux.md`, `docs/implementation-artifacts/e2e-campaign-epic-23/notes-audit-winston-architecture.md`, `docs/implementation-artifacts/e2e-campaign-epic-23/synthese-remediation-sally-winston-epic-23.md`, `infra/scripts/uj_e2e_coverage.py`, `docs/product/capabilities.yaml`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-7-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** les Stories `23.1`..`23.5` et `23.6a` clôturées à `100 %` vert sur les 5 couches `AD-17` et la pile `orcia_e2e` (PostgreSQL 18 + `pgvector`, Redis 7.4, FastAPI, SPA Vite, `DeterministicCassetteLLM` `0 $`, sans `ORCIA_E2E_SEED_FIXTURES`) prête pour une campagne figée
**When** la campagne Playwright intégrale Desktop (`--project=desktop-cockpit`, `24` specs, `55` scénarios Desktop `1440×900`, `--retries=0 --max-failures=0 --timeout=35000`) est exécutée sans aucune retouche de code vers `docs/implementation-artifacts/e2e-campaign-epic-23/`
**Then** tous les artefacts bruts sont archivés (`playwright-results.json`, `manifest.jsonl` à `55` entrées Desktop, `55/55` captures PNG d'état final sous `screenshots/**/*.png` avec taille `< 450 KB` par fichier), et `e2e-campaign-epic-22/` reste intact comme archive historique.

**Given** les artefacts bruts de `e2e-campaign-epic-23/`
**When** le bilan factuel et l'audit croisé **Sally × Winston** sont conduits sur les `55` scénarios Desktop (`52` exécutés + `3` `mobile-only` skipped)
**Then** `bilan-execution-tests-e2e-epic-23.md` inventorie exactement les résultats (`52` `passed` attendus, `0` `failed`, `0` `timedOut`, `3` `skipped` `mobile-only`, delta vs Epic 22), `notes-audit-sally-ux.md` évalue les captures PNG Desktop (Direction C, contrastes WCAG, lisibilité, langue FR), `notes-audit-winston-architecture.md` vérifie la conformité `AD-1`..`AD-24` & SQL PG18, et `synthese-remediation-sally-winston-epic-23.md` consigne tout échec résiduel ou écart `P0`/`P1` (ou confirme `0` écart `P0`/`P1`, en traçant `CAP-042` vers `ACTION_ITEM-23.6`).

**Given** les résultats réels de `docs/implementation-artifacts/e2e-campaign-epic-23/playwright-results.json`
**When** `PLAYWRIGHT_RESULTS_PATH` dans `infra/scripts/uj_e2e_coverage.py` bascule vers `e2e-campaign-epic-23/playwright-results.json`, que `docs/product/capabilities.yaml` est mis à jour et que `pnpm site:sync && pnpm site:check` s'exécute
**Then** toute capacité Desktop dont `100 %` des specs associées sont vertes passe à `verification: runtime` (`verified_at` à jour, `e2e_remediation_ref` supprimé), **`CAP-042` reste honnêtement en `verification: failed_e2e` avec `e2e_remediation_ref: "ACTION_ITEM-23.6"`**, toute autre capacité encore en échec éventuel reste en `failed_e2e`, et `pnpm site:check` ainsi que `tests/unit/test_uj_e2e_coverage_gate.py` passent à `0` erreur.

---

### Story 23.8: Clôture Epic 23, Bilan Conditionnel (`52/52` PASS Desktop & `0` `P0`/`P1` $\rightarrow$ Sans Epic 24 Vide) & Éventuelle Initialisation Epic 24

As a Tech Lead (`Amelia`) & Architecte (`Winston`),
I want évaluer la condition de sortie de `Story 23.7` sur `--project=desktop-cockpit` (`52/52` PASS Desktop et `0` écart `P0`/`P1` dans `synthese-remediation-sally-winston-epic-23.md`) afin de clôturer directement l'Epic 23 (`epic-23: done`) **sans créer d'Epic 24 artificiel vide** lorsque le nominal est atteint (avec `CAP-042` rattachée à `ACTION_ITEM-23.6`), et n'activer le workflow d'initialisation de l'**Epic 24** (rapports Tech Lead `24-1..24-K`, `sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`, `tests/unit/test_epic23_to_epic24_traceability.py`) **que si** un échec Desktop (`> 0`) ou un écart `P0`/`P1` (`> 0`) subsiste en `Story 23.7`,
So that l'Epic 23 se clôture proprement sans dette bureaucratique tout en garantissant `100 %` de traçabilité si un reliquat réel devait être traité en Epic 24 (`GEMINI.md` § Policy, `AD-17`).

**Dépendances :** Dépend de `Story 23.7`. Clôture l'Epic 23.
**CAP couvertes :** `none (gouvernance documentaire & clôture Epic 23 — rattache CAP-042 à ACTION_ITEM-23.6 et, uniquement si échec Desktop ou écart P0/P1 résiduel, initialise Epic 24)` — classification : `doc`.
**Fichiers impactés :** `docs/implementation-artifacts/sprint-status.yaml` (`23-8-...: done`, `epic-23: done`), `docs/implementation-artifacts/tech-lead-reports/23-8-...-tech-lead-report.md` (+ `README.md`), `docs/product/capabilities.yaml`, `tests/unit/test_epic22_to_epic23_traceability.py` *(et uniquement si reliquat `P0`/`P1` ou échec Desktop > 0 : `24-1..24-K`, `sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`, `epics.md` `Epic 24`, `test_epic23_to_epic24_traceability.py`)*.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** la `Story 23.7` achevée avec **`52/52` PASS Desktop (`0` failed, `0` timedOut, `3` skipped `mobile-only`)** et **`0` écart `P0`/`P1`** dans `synthese-remediation-sally-winston-epic-23.md`
**When** `Story 23.8` vérifie la traçabilité finale et clôture l'Epic 23
**Then** `epic-23` passe à `done`, `CAP-042` reste proprement rattachée à `ACTION_ITEM-23.6`, **aucun Epic 24 artificiel vide n'est créé**, et `test_epic22_to_epic23_traceability.py`, `check_implementation_docs.py` ainsi que `pnpm site:sync && pnpm site:check` passent à `0` erreur.

**Given** un éventuel échec Desktop (`> 0`) ou écart `P0`/`P1` (`> 0`) constaté dans `bilan-execution-tests-e2e-epic-23.md` ou `synthese-remediation-sally-winston-epic-23.md`
**When** le Tech Lead exécute l'analyse d'impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`) sur les symboles concernés
**Then** tous les constats sont regroupés en `K` lots cohérents (`Story 24.1`..`Story 24.K`) dotés chacun d'un rapport Tech Lead pré-implémentation (`24-1..24-K`), du plan directeur `sprint-change-proposal-2026-11-19-epic-24-remediation-plan.md`, de l'initialisation complète dans `epics.md`/`sprint-status.yaml`/`capabilities.yaml` et de `tests/unit/test_epic23_to_epic24_traceability.py`, avec `100 %` de traçabilité bidirectionnelle avant passage de `epic-23: done`.

---

## Epic 24: Remédiation Finale `Case B` post-`23.7` — Persistance PG18 (Jira Staged, MCP, VSM v2), Triggers UUIDv7, Refonte CSS Tailwind v4, Navigation Zone 4, Zéro Jargon, Correctifs Utilisateur (`USER24-BUG-1..6`) & Preuve Desktop `52/52`

Résoudre l'ensemble des reliquats identifiés lors du déclenchement **`Case B`** de la `Story 23.7` (`e2e-campaign-epic-23/`, commit `dd2d382` : `8` échecs/timeouts Desktop `#15`, `#16`, `#40`, `#41`, `#45`, `#47`, `#48`, `#49`, `17` constats `UX23-01`..`UX23-17` = `1 P0` + `9 P1` + `5 P2` + `2 P3`, `12` diagnostics `ARCH24-01`..`ARCH24-12`, `12` remédiations `REM24-01`..`REM24-12` et les `6` remontées utilisateur `USER24-BUG-1..6`) conformément au plan directeur [`docs/planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](./sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md), en **3 vagues** (`Stories 24.1`..`24.7`), avec garantie stricte de persistance PostgreSQL 18 sans état RAM fantôme ni régression Jour 0 (`CAP-042` demeurant explicitement rattachée à `ACTION_ITEM-23.6`) et sortie conditionnelle sans boucle infinie d'un Epic 25.

---

### Story 24.1: Persistance PostgreSQL 18 des Actions Jira Staged, Propositions MCP & Workflow VSM v2

As a Architecte (`Winston`) & Tech Lead (`Amelia`),
I want éliminer le stockage en mémoire RAM de `MultiProjectJiraStagedActionService` (`459` L $\rightarrow$ `< 300` L), `GovernedMcpServerService` et `SqlWorkflowDefinitionsV2Store` en câblant des adaptateurs PostgreSQL 18 stricts via `apps/api/src/orcia_api/dependencies/` et en supprimant les helpers lazy `_get_jira_service`/`_get_mcp_service` ainsi que `get_vsm_store()`/`get_runs_store()` dans `_workflows_helpers.py`,
So that les actions Jira staged (`06 #15`), propositions MCP (`19#2 #47`) et le workflow VSM `11` étapes (`20#1 #48`, `UX23-01` `P0`) survivent durablement aux rechargements à froid PG18 et aux redémarrages multi-workers (`REM24-01`, `REM24-02`, `ARCH24-01`, `ARCH24-02`, `ARCH24-12`).

**Dépendances :** Vague 0 (pré-requis pour `24.4`, `24.6`, `24.7`).
**CAP couvertes :** `CAP-020`, `CAP-021`, `CAP-024`, `CAP-030`, `CAP-031`, `CAP-032`, `CAP-033`, `CAP-140` (`8` capacités Desktop `failed_e2e`).
**Fichiers impactés :** `infra/migrations/versions/*`, `infra/scripts/maintenance/_first_boot_reset_guards.py`, `packages/orcia-connectors/src/orcia_connectors/jira_actions.py`, `packages/orcia-core/src/orcia_core/orchestration/mcp_server.py`, `packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflows_v2.py`, `apps/api/src/orcia_api/routers/jira_and_mcp.py`, `apps/api/src/orcia_api/routers/_workflows_helpers.py`, `apps/api/src/orcia_api/dependencies/reflexive_execution.py`, `apps/web/src/features/gates/GatesAdaptiveHumanReviewSection.tsx`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/24-1-persistance-pg18-actions-jira-staged-mcp-et-vsm-v2-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une action Jira staged (`06 #15`) ou une proposition de gouvernance MCP (`19#2 #47`) soumise via FastAPI sur Composition Root réel `create_app()`
**When** le service persiste la mutation dans la table PG18 `jira_staged_actions` / table MCP gouvernée et publie l'événement dans `domain_events_outbox`
**Then** une requête `SELECT` directe sur PostgreSQL 18 confirme l'enregistrement (`UUIDv7`), l'état reste inchangé après éviction cache / redémarrage backend / rechargement `F5`, zéro helper lazy `_get_jira_service`/`_get_mcp_service` ne subsiste dans `jira_and_mcp.py`, et `jira_actions.py` (`459` L) ainsi que `GatesAdaptiveHumanReviewSection.tsx` (`378` L) sont découpés sous `< 300` L.

**Given** le studio processus `VSM v2` (`20#1 #48`) et la table PG18 `vsm_definitions_v2`
**When** le backend démarre en mode applicatif avec `strict_sql=True` et le seeder idempotent des VSM/packs exécuté
**Then** `SqlWorkflowDefinitionsV2Store` est injecté uniquement depuis `dependencies/` (suppression de `get_vsm_store()`/`get_runs_store()` dans `_workflows_helpers.py`), le workflow canonique `11` étapes se charge et survit au `F5` (`0` état fantôme `UX23-01`), et toute nouvelle table mutable est enregistrée dans `_first_boot_reset_guards.py`.

---

### Story 24.2: Déclencheurs UUIDv7 sans Collision, Waivers `await`, ADN Starlark PG18 & Purge `default-ws` (`USER24-BUG-6`)

As a Tech Lead (`Amelia`) & Architecte (`Winston`),
I want corriger la collision temporelle `f"trg-{tid[:8]}"` dans `_triggers_lifecycle_ops.py:46-47` (`trigger_key` optionnel exposé), forcer `await` + état `submitting` + persistance PG18 pour les waivers et mécanismes Starlark ADN (`dna_starlark_and_glossary_lifecycle.py` `447` L $\rightarrow$ `< 350` L), purger tout fallback `"default-ws"`/`"ws-claims-alpha"`/`"ws-mon-compte"` (en ne montant plus le détail/ADN de `/spaces` à `0` espace), et brancher le rendu des 5 onglets de `WorkspaceFiveTabsAndExternalRebaseView.tsx` sur `activeTab`,
So that deux créations séquentielles de déclencheurs (`20#2 #49`) ne se heurtent plus jamais sur la clé `UUIDv7` et que la gouvernance d'espace (`17#3 #40`, `UX23-06`, `USER24-BUG-6`) repose exclusivement sur des espaces réels persistés en PostgreSQL 18 (`REM24-03`, `REM24-04`, `ARCH24-03`, `ARCH24-04`).

**Dépendances :** Vague 0 (parallélisable avec `24.1` et `24.3`).
**CAP couvertes :** `CAP-010`, `CAP-011`, `CAP-081`, `CAP-084`, `CAP-180`, `CAP-201` (`6` capacités Desktop `failed_e2e`).
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/orchestration/_triggers_lifecycle_ops.py`, `packages/orcia-core/src/orcia_core/orchestration/dna_starlark_and_glossary_lifecycle.py`, `apps/api/src/orcia_api/dependencies/workspace_and_packs.py`, `apps/api/src/orcia_api/routers/workflow_triggers.py`, `apps/api/src/orcia_api/routers/workspace_governance.py`, `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, `apps/web/src/features/workspaces/index.tsx`, `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`, `WorkflowTriggersModal`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/24-2-triggers-uuidv7-sans-collision-waivers-await-adn-pg18-et-fin-default-ws-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** deux ou plusieurs déclencheurs créés séquentiellement dans la même seconde via `WorkflowTriggersModal` ou `POST /api/v1/workflows/.../triggers` (`20#2 #49`)
**When** `execute_create_trigger` génère une clé (via suffixe entropique `tid` complet/`[-12:]`, jamais `tid[:8]`) ou utilise le champ optionnel `trigger_key`
**Then** `100 %` des déclencheurs créés sont persistés distinctement dans `workflow_triggers` sans erreur `409`/collision (sauf doublon utilisateur explicite retourné en `409` RFC 9457 lisible).

**Given** la page `/spaces` avec `0` espace puis avec un espace réel (aucun fallback `"default-ws"`, `"ws-claims-alpha"` ou `"ws-mon-compte"`, `17#3 #40`, `USER24-BUG-6`)
**When** l'utilisateur visite `/spaces` sans espace, puis crée un espace, change d'onglet dans `WorkspaceFiveTabsAndExternalRebaseView` et enregistre un waiver ou compile une règle ADN Starlark
**Then** à `0` espace ni `WorkspaceDnaAndWaiversSection` ni `default-ws` ne sont montés, le panneau des 5 onglets commute fidèlement selon `activeTab` (l'onglet 5 `Membres & Équipe` n'affiche plus `2. DOCUMENTS & SOURCES`), la requête HTTP de waiver/ADN est attendue via `await` avec indicateur `submitting`, le mécanisme Starlark signé est relu à froid depuis PostgreSQL 18 via `dependencies/workspace_and_packs.py`, et `dna_starlark_and_glossary_lifecycle.py` (`447` L) est découpé sous `< 350` L.

---

### Story 24.3: Banc de Test MCP, `audit_ledger`, Fin du `PASS` Optimiste & Assainissement Composition Root

As a Architecte (`Winston`) & Tech Lead (`Amelia`),
I want supprimer le `PASS` optimiste synchrone de `useCatalogRemoteTestBench.ts`, câbler `handleToggleMcp`/`handleActivateRemoteService` sur `PUT /api/v1/mcp/exposure` et PG18, aligner l'écriture `ADMIN_CONNECTION_TEST` dans `audit_ledger`, migrer `_speed2_cache` vers Redis `300s` et raccorder les healthchecks réels de `PacksRegistryPage` ainsi que le `wfKey` réel dans `cockpit/index.tsx:113`,
So that les résultats du banc de test distant (`18#5 #45`) reflètent la réponse HTTP réelle et la traçabilité append-only `audit_ledger` sans aucun cache métier RAM (`REM24-05`, `REM24-06`, `ARCH24-05`, `ARCH24-07`, `ARCH24-12`).

**Dépendances :** Vague 0 (parallélisable avec `24.1` et `24.2`).
**CAP couvertes :** `CAP-055`, `CAP-082`, `CAP-092`, `CAP-150`, `CAP-200` (`5` capacités Desktop `failed_e2e`).
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/orchestration/remote_test_bench_and_mcp_exposure.py`, `packages/orcia-core/src/orcia_core/audit_finops/outbox_subscriber.py`, `packages/orcia-core/src/orcia_core/rag/two_speed_search.py`, `apps/api/src/orcia_api/routers/mcp_and_test_bench.py`, `apps/api/src/orcia_api/dependencies/`, `apps/web/src/features/catalog/useCatalogRemoteTestBench.ts`, `packages/ui/src/primitives/RemoteServiceTestBenchAndMcpExposureView.tsx`, `apps/web/src/features/settings/packs/PacksRegistryPage.tsx`, `apps/web/src/features/cockpit/index.tsx`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/24-3-banc-mcp-audit-ledger-fin-pass-optimiste-et-assainissement-composition-root-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une exécution du banc de test distant et une activation MCP depuis `/catalog` (`18#5 #45`)
**When** l'utilisateur déclenche le test puis bascule l'exposition MCP (`PUT /api/v1/mcp/exposure`)
**Then** aucun statut `PASS` optimiste synchrone n'apparaît avant réception d'un `HTTP 200` (erreur HTTP $\ge 400$ affichée dans `[role="alert"]`), une ligne immuable `event_type = 'ADMIN_CONNECTION_TEST'` est insérée en PG18 dans `audit_ledger`, les expositions MCP et jetons PAT survivent au `F5` en PG18 (`remote_test_bench_and_mcp_exposure.py` `440` L découpé `< 350` L), `_speed2_cache` utilise Redis `7.4` (`TTL 300s` cloisonné par contexte), `PacksRegistryPage` lit la santé API réelle et `cockpit/index.tsx:113` transmet le `wfKey` réel.

---

### Story 24.4: Refonte CSS Tailwind v4 Layering, Verrouillage Scroll Shell (`USER24-BUG-1`), Modales Onglets & Clés MCP (`USER24-BUG-4A/4B/5`), `AgentDetail` & Contraste RGAA

As a UX Designer (`Sally`) & Tech Lead (`Amelia`),
I want rétablir l'import de `tokens.css` avant `virtual:orcia-tailwind.css` dans `apps/web/src/main.tsx:1-2` en découpant/encapsulant `tokens.css` (`1 266` L) dans `@layer utilities`, verrouiller le scroll vertical Desktop (`100dvh`/`overflow: hidden`) sur `FourZoneDirectionCShell` (`348` L) avec un test systématique anti-débordement (`USER24-BUG-1`), passer `UserSettingsModalDialog` en mode onglets horizontaux `.orcia-ds-tabs` comme dans « Mes Espaces » (`USER24-BUG-4A` résolvant `UX23-02`), supprimer l'entrée redondante `Paramètres` de `SidebarAccountPopover` pour ne garder que `Personnalisation` (`USER24-BUG-4B`), réinitialiser l'affichage unique des clés PAT MCP à la fermeture de la modale avec libellés français lisibles (`USER24-BUG-5`), porter `AgentDetailAndSandboxModal` (`318` L) sur `OrciaDialog`, supprimer la transition `150ms` des onglets + unifier `[aria-selected="true"]` sur `FinopsScopePills`, corriger le contraste sombre `--color-sidebar-active-fg >= 4.5:1` et éliminer la bande `#EAF2FB`,
So that l'ensemble des écrans respecte Direction C sans régression responsive (`md:flex-row`, `sm:grid-cols-2 xl:grid-cols-4`), sans débordement vertical hors écran de travail ni défaut RGAA (`REM24-07`, `UX23-02..04`, `UX23-13`, `UX23-14`, `UX23-16`, `ARCH24-08`, `ARCH24-11`, `USER24-BUG-1`, `USER24-BUG-4A`, `USER24-BUG-4B`, `USER24-BUG-5`).

**Dépendances :** Vague 1 (après `24.1`).
**CAP couvertes :** `none (hygiène/ux transverse Direction C — sécurise CAP-060, CAP-063, CAP-090, CAP-200 avant la campagne finale 24.7)` — classification : `ux`.
**Fichiers impactés :** `apps/web/src/main.tsx`, `packages/ui/src/styles/tokens*.css`, `packages/ui/src/components/AgentDetailAndSandboxModal.tsx`, `packages/ui/src/primitives/FourZoneDirectionCShell.tsx`, `packages/ui/src/primitives/FourZoneSidebarRail.tsx`, `packages/ui/src/primitives/FourZoneHelpAsideColumn.tsx`, `packages/ui/src/primitives/UserSettingsModalDialog.tsx`, `packages/ui/src/primitives/SidebarAccountPopover.tsx`, `packages/ui/src/primitives/UserSettingsMcpTokensTab.tsx`, `apps/web/src/components/useSidebarAccountSettings.ts`, `packages/ui/src/primitives/finops/*`, `apps/web/src/features/finops/index.tsx`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/24-4-refonte-css-tailwind-tokens-modales-rgaa-contraste-onglets-et-shell-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** le bundle CSS produit par Vite + Tailwind v4 et affiché à `1440×900` en thèmes clair et sombre
**When** l'utilisateur ouvre `/cockpit`, `/finops`, `/agents`, les formulaires d'authentification et la modale Agent (`AgentDetailAndSandboxModal`)
**Then** les grilles responsives (`sm:grid-cols-2 xl:grid-cols-4`, `md:flex-row`) ne sont plus écrasées par des utilitaires non layerés (`tokens.css` scindé en partials `< 350` L), `AgentDetailAndSandboxModal` hérite d'`OrciaDialog` (`max-h-[82vh]`, footer sticky, `@slug` complet), le fondu `150ms` d'onglet est supprimé avec `[aria-selected="true"]` uniforme sur `FinopsScopePills`, `--color-sidebar-active-fg` atteint `>= 4.5:1` en dark mode, le viewport Desktop verrouille strictement `document.documentElement.scrollHeight <= window.innerHeight + 1` (seules les colonnes internes scrollent, `0` bande `#EAF2FB`, `0` scroll sous le shell, vérifié systématiquement en Vitest et Playwright `USER24-BUG-1`), `Accostage` se compacte lorsque des runs existent et `Journal d'Activité →` est aligné dans `/finops`.

**Given** le menu Compte en bas à gauche (`SidebarAccountPopover`) et la modale `Personnalisation` (`UserSettingsModalDialog`)
**When** l'utilisateur ouvre le menu Compte, bascule entre les 5 onglets, génère une clé éditeur MCP, puis ferme et rouvre la modale
**Then** le menu Compte n'affiche plus le doublon `Paramètres` (seule l'entrée `Personnalisation` subsiste `USER24-BUG-4B`), la modale utilise des onglets horizontaux `.orcia-ds-tabs` au-dessus du contenu (`aria-orientation="horizontal"`, `USER24-BUG-4A`), les clés existantes s'affichent en français lisible sans `IDE MCP (SPACE · default)` ni `60 RPM`, et la bannière contenant le secret en clair ne réapparaît plus après fermeture puis réouverture de la modale (`USER24-BUG-5`).

---

### Story 24.5: Identité Accostage Cockpit, Route « 1. Compte Admin » (`USER24-BUG-2`), Synchronisation Navigation Zone 4 & Cohérence Jour 0

As a UX Designer (`Sally`) & Architecte (`Winston`),
I want transmettre le véritable `platformAdmin` dans `apps/web/src/features/cockpit/index.tsx:207-209` (jamais `authDisplayName`) et filtrer les jalons Accostage selon les permissions utilisateur, corriger la route inexistante `/welcome-setup` du jalon `1. Compte Admin` vers `/profile` post-admin (`/cockpit` Jour 0) et auditer les 6 jalons contre `router.tsx` (`USER24-BUG-2`), créer l'entrée Zone 4 dédiée `/inbox` (`_contextualHelpSections.ts:242` + `docs/help/{fr,en}/inbox.md`), surligner `help` dans la Sidebar sur `/showcase`, corriger les fils d'Ariane `/organization`, `/spaces` et `[Espace]`, afficher les `6` onglets `/settings` sur `1` ligne et verrouiller uniformément `Mes Espaces` avant création de l'admin Jour 0,
So that la navigation et l'accostage progressif reflètent fidèlement les droits réels et la route active dès le Jour 0 sans aucun `Not Found` (`REM24-08`, `UX23-07`, `UX23-09`, `UX23-15`, `ARCH24-09`, `USER24-BUG-2`).

**Dépendances :** Vague 1 (après `24.2`).
**CAP couvertes :** `CAP-050`, `CAP-067` (`2` capacités Desktop `failed_e2e`, plus protection de non-régression `CAP-005`, `CAP-060`, `CAP-061`, `CAP-064`, `CAP-068`).
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py`, `packages/orcia-core/src/orcia_core/catalog/contextual_help.py`, `docs/help/{fr,en}/inbox.md`, `apps/web/src/components/platformSetupAccostage.ts`, `apps/web/src/features/cockpit/index.tsx`, `apps/web/src/components/{shellPresets.ts,_contextualHelpSections.ts,ShellContainer.tsx}`, `FirstBootAdminSetupModal.tsx`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/24-5-identite-accostage-cockpit-sync-navigation-zone4-et-coherence-jour0-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un utilisateur authentifié (standard ou administrateur plateforme) et une pile réinitialisée au Jour 0 (`pnpm db:reset`)
**When** il visite `/cockpit` (et clique sur « 1. Compte Admin » ou tout autre jalon de « Étape 3 : Parcours en 6 jalons »), `/inbox`, `/showcase`, `/organization`, `/spaces` et `/settings`
**Then** le clic sur `1. Compte Admin` (et sur chacun des 6 jalons) aboutit sur une route valide déclarée dans `router.tsx` sans jamais afficher `Not Found` (`USER24-BUG-2`), `Accostage` affiche le véritable `platformAdmin` (jamais `authDisplayName` d'un non-admin) et uniquement les jalons autorisés par ses permissions, `/inbox` charge sa propre aide Zone 4 (`docs/help/{fr,en}/inbox.md`), `/showcase` met `help` en surbrillance dans la barre latérale, `/organization` ne dépend plus du parent masqué `Configuration`, `[Espace]` apparaît dynamiquement dans le fil d'Ariane, `/spaces` ne duplique plus son breadcrumb ni le pied de pack actif, `/settings` tient sur `1` ligne pour ses `6` onglets, `Mes Espaces` est verrouillé uniformément pré-admin avec modale `FirstBootAdminSetupModal` explicitement non fermable, et `ShellContainer.tsx` (`378` L) est découpé sous `< 280` L.

---

### Story 24.6: Recherche `Cmd+K` Filtrée par Langue, Rendu Markdown Aide (`USER24-BUG-3`), Purge du Jargon, Compteurs Packs & Microcopy

As a UX Designer (`Sally`) & Tech Lead (`Amelia`),
I want filtrer `HELP_ARTICLE` sur `ci.lang = locale` dans `sql_federated_search.py` (`portal_and_help.py:106`), remplacer l'émoji rouge `❓` de `TopHeaderSearchCommand` par `OrciaIcon`, appliquer le rendu Markdown (`renderInlineMarkdownNodes` / `FormattedMarkdownContent`) à tous les blocs de `ContextualHelpSharedBlocks.tsx` et `ContextualHelpSectionsAndFooter.tsx` (« Ce qui coince souvent », « Questions fréquentes », « Un exemple réel », « Comment procéder pas à pas », « Repères utiles ») sur `/help` et Zone 4 (`USER24-BUG-3`), traduire `100 %` des enums et valeurs brutes (`PENDING`, `RUNNING`, `PAUSE_AND_ESCALATE`, `OPT_A_*`, `1_NETWORK_TLS_ANTI_SSRF..4_HOT_DRY_RUN`, `COMPLETED`, `PASS`, `HTTP 403`, `(AD-24.7)`, `PostgreSQL 18`, `< 15 s`, `0.5 ms`, `depth=0/1`, `0` nu `CatalogExplorerPanel.tsx:149`), rendre les tips `PermissionBrokerCard` via `FormattedMarkdownContent` + URI décodé, corriger la grille `5` compteurs de `/settings/packs` et éliminer toutes les troncatures `1440×900` et défauts microcopy (`UX23-16`),
So that l'interface française et anglaise soit dépourvue de jargon technique, de syntaxe Markdown brute non rendue, de fuites multilingues et de défauts typographiques (`REM24-09`, `REM24-10`, `UX23-05`, `UX23-08`, `UX23-10..12`, `UX23-16`, `ARCH24-10`, `ARCH24-11`, `USER24-BUG-3`).

**Dépendances :** Vague 1 (après `24.1` et `24.3`).
**CAP couvertes :** `CAP-056`, `CAP-057` (`2` capacités Desktop `failed_e2e`).
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py`, `apps/api/src/orcia_api/routers/portal_and_help.py`, `packages/ui/src/primitives/TopHeaderSearchCommand.tsx`, `packages/ui/src/primitives/ContextualHelpSharedBlocks.tsx`, `packages/ui/src/primitives/ContextualHelpSectionsAndFooter.tsx`, `packages/ui/src/shell/CatalogExplorerPanel.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `docs/help/fr/*.md`, `apps/web/src/features/settings/packs/PacksRegistryPage.tsx`, `apps/web/src/features/admin/iam/IamSecopsExceptionForm.tsx`, `apps/web/src/features/processes/studio/StudioCopilotSidebar.tsx`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/24-6-recherche-cmdk-filtre-langue-purge-jargon-packs-et-microcopy-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une session configurée en `fr` (ou `en`) utilisant `Cmd+K`, `/help`, Zone 4, `/catalog`, `/settings/packs`, `/wizards`, `/ontology`, `/showcase`, `/spaces`, `/finops` et les écrans d'exécution/permissions
**When** l'utilisateur effectue une recherche, déplie « Ce qui coince souvent » ou « Questions fréquentes » dans `/help` / Zone 4, consulte un pack, ouvre une demande de permission ou inspecte les étapes en `1440×900`
**Then** `/help` et Zone 4 restituent du HTML formaté (`<strong>`, `<code>`) sans aucune étoile `**` ni backtick brut (`USER24-BUG-3`), `load_federated_search_candidates_pg18` n'inclut aucun `HELP_ARTICLE` d'une autre langue, `TopHeaderSearchCommand` affiche une icône blanche `OrciaIcon` sans émoji `❓`, aucune enum technique brute ni `0` nu (`CatalogExplorerPanel.tsx:149`) n'est visible, `PermissionBrokerCard` rend le Markdown via `FormattedMarkdownContent` et décode les URIs, `/settings/packs` affiche exactement ses `5` compteurs (`4 Compétences`) avec singulier pour `n <= 1`, `docs/help/fr/` est purgé de `` `@` `` et `L4 → L1`, les troncatures `1440×900` disparaissent (`PacksRegistryPage.tsx` `381` L et `IamSecopsExceptionForm.tsx` `403` L découpés `< 300` L), et les finitions `UX23-16` (`/ontology`, `/showcase` `4` onglets, `/wizards`, `Mes Espaces`, `paliers`, `Cassette`, `0.002 €`) sont appliquées.

---

### Story 24.7: Réconciliation des Sélecteurs E2E, Captures Jalons, Campagne Figée `52/52` & Clôture Epic 24

As a QA / Tech Lead (`Amelia`), UX Designer (`Sally`) & Architecte (`Winston`),
I want corriger `openCatalogOrAgentsPage` (`apps/web/e2e/support/workspaceAndCatalogHelpers.ts:126-130`) pour distinguer `/catalog` (`catalog-explorer-panel`) de `/agents` (`agents-and-skills-manager-view`) et borner `07-spaces-org-and-workspace-persistence.spec.ts:42` sur `page.getByRole("main")`, ajouter les captures jalons `< 450 KB` (`milestone-*.png`) VSM `11` étapes, drawer HITL et tripartite/waivers (en stabilisant `00 #3/#4` et `04 #12`), puis exécuter la campagne figée Desktop `--project=desktop-cockpit --retries=0 --max-failures=0` dans `e2e-campaign-epic-24/`,
So that **`52/52` scénarios Desktop PASS (`0` failed, `0` timedOut, `3` `mobile-only` skipped, `0` flaky)** et le contre-audit Sally × Winston (`0 P0 / 0 P1`) prouvent la complétude runtime pour promouvoir les `25` capacités vers `runtime` (`64/65` avec `CAP-042` maintenue sur `ACTION_ITEM-23.6`) et clôturer l'Epic 24 sans boucle infinie (`REM24-11`, `REM24-12`, `ARCH24-06`, `UX23-17`).

**Dépendances :** Vague 2 — requiert la clôture `100 %` verte de `Stories 24.1`..`24.6`.
**CAP couvertes :** `CAP-002`, `CAP-080` (`2` capacités assignées directement + promotion finale des `25` capacités Desktop vers `runtime` ; `CAP-042` maintenue sur `ACTION_ITEM-23.6`).
**Fichiers impactés :** `apps/web/e2e/support/workspaceAndCatalogHelpers.ts`, `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts`, specs `00`, `04`, `06`, `17`, `20`, `docs/implementation-artifacts/e2e-campaign-epic-24/**`, `infra/scripts/uj_e2e_coverage.py`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/24-7-reconciliation-e2e-captures-jalons-campagne-52-sur-52-et-cloture-epic-24-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** les Stories `24.1`..`24.6` validées sur les 5 couches `AD-17` et la base réinitialisée proprement au Jour 0 via `pnpm db:reset` (sans `ORCIA_E2E_SEED_FIXTURES`)
**When** les sélecteurs `/catalog` (`workspaceAndCatalogHelpers.ts:126-130`) et `07-spaces` (`L42`) sont corrigés, que les captures jalons `milestone-*.png` (`< 450 KB`) sont ajoutées, que la non-régression des `6` correctifs utilisateur (`USER24-BUG-1..6`) est vérifiée en E2E et que la campagne figée `--project=desktop-cockpit --retries=0 --max-failures=0` est archivée dans `docs/implementation-artifacts/e2e-campaign-epic-24/`
**Then** la campagne prouve **`52/52` PASS Desktop (`0` failed, `0` timedOut, `3` `mobile-only` skipped, `0` flaky)**, `100 %` des captures PNG font `< 450 KB`, le contre-audit visuel et architectural Sally × Winston atteste **`0 P0 / 0 P1`** et la résolution visuelle de `USER24-BUG-1..6`, `PLAYWRIGHT_RESULTS_PATH` bascule sur `e2e-campaign-epic-24/playwright-results.json`, les `25` capacités Desktop passent à `verification: runtime` (`64/65`, `CAP-042` inchangée sous `ACTION_ITEM-23.6`), `pnpm site:sync && pnpm site:check` passe à `0` erreur et `epic-24` se clôture à `done` sans créer d'Epic 25 automatique.

---

## Epic 25: Sobriété Cockpit Jour 0, Coquille 9 Entrées (Mon Organisation & Administration), Espace Personnel Automatique PG18, Hub Modèles IA Fiable & Découplage Mon Assistant / RAG (AD-24)

Corriger les frictions UX et architecturales constatées post-Epic 24 lors de l'utilisation réelle Jour 0 : provisionner automatiquement un Espace Personnel privé (`PRIVATE_USER` PG18) pour chaque utilisateur sans rompre la vérité terrain `0` user / `0` workspace après `pnpm db:reset`, unifier le Guide d'Accostage (`6` jalons dont `4. Premier Espace d'équipe`, non repliable tant que `< 6/6`), dégriser `Mes Processus` dès `1` modèle IA actif, aligner la coquille sur **9 entrées fixes** (`Mon Organisation` ouvert à tous sous `Mes Espaces`, `Administration` strictement `5` onglets réservée `PLATFORM_ADMIN` / `SECOPS`, logo cliquable `[O] ORCIA › <Écran>` unique en `TopHeaderBar`, sélecteur unique d'`Espace actif` groupé par `Personnel` + `Équipe / BU`, retrait des `ⓘ` et `Active context`), purger les résidus démo RAM (`marc.lead@orcia.io`, `DEFAULT_ARBITRATION_OPTIONS`) et blocs d'attente à vide du `Cockpit`, fiabiliser la suppression PG18 et le retour d'erreur localisé dans le Hub des Modèles IA (`<OrciaSpinner />`, masquage réindexation à `0` document indexé), et découpler `Mon Assistant` (actif dès `1` modèle `chat` sans modèle `embedding`) tout en bloquant dès `POST /datasources` et l'UI l'ajout de sources RAG vectorielles (`source_nature != 'SOURCE_CODE'`) selon l'amendement `AD-8` / `AD-16` / `AD-24`.

---

### Story 25.1: Provisionnement Automatique de l'Espace Personnel (`PRIVATE_USER` PG18), Guide d'Accostage Unifié & Dégrisage `Mes Processus`

As a Utilisateur / Administrateur Plateforme (`Thomas`, `Claire`, `Lucas`),
I want recevoir automatiquement et de manière idempotente un **Espace Personnel privé** (`visibility_mode = 'CONFIDENTIAL_RESTRICTED'` en SQL + `settings_jsonb.ui_visibility_mode = 'PRIVATE_USER'` + `settings_jsonb.personal_owner_user_id`) lors de l'initialisation du 1er Admin Jour 0, de la création d'un compte IAM ou de ma première connexion (tout en conservant `0` workspace après `pnpm db:reset` tant que `0` user existe), disposer d'un **Guide d'Accostage unifié** à `6` jalons (incluant `4. Premier Espace d'équipe`, avec coches vertes et flèches alignées verticalement proche du texte, non repliable tant que `< 6/6`) et voir **`Mes Processus`** dégrisé dès `1` modèle IA configuré,
So that chaque utilisateur dispose immédiatement d'un espace personnel isolé en PG18 sans fuite inter-admins, que la progression d'accostage reste claire et stable jusqu'à `6/6` et que la création/exécution de processus démarre dès le premier modèle `chat` (`AD-16` amendé Epic 25, `AD-21`).

**Dépendances :** Clôture Epic 24 (`epic-24: done`), amendement `AD-16` Epic 25.
**CAP couvertes :** `CAP-004`, `CAP-005`, `CAP-061`, `CAP-067`, `CAP-020`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/bootstrap/`, `packages/orcia-core/src/orcia_core/permissions/`, `apps/api/src/orcia_api/routers/bootstrap.py`, `apps/api/src/orcia_api/routers/bootstrap_accostage.py`, `apps/api/src/orcia_api/routers/org_and_workspaces.py`, `apps/web/src/components/platformSetupAccostage.ts`, `apps/web/src/components/platformSetupWorkspaces.ts`, `apps/web/src/features/cockpit/PlatformOnboardingChecklistCard.tsx`, `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx`, `apps/web/src/components/ShellContainer.tsx`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-1-espace-personnel-auto-pg18-accostage-unifie-et-degrisage-processus-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une base réinitialisée au Jour 0 via `pnpm db:reset` (`0` utilisateur en PG18)
**When** aucun compte administrateur n'a encore été créé, puis que le 1er `PLATFORM_ADMIN` s'initialise (ou qu'un nouvel utilisateur est créé via IAM / effectue sa première connexion)
**Then** avant création du 1er admin la table `workspaces` contient strictement `0` ligne, puis lors de l'initialisation / création IAM / première connexion un Espace Personnel privé unique est provisionné transactionnellement et de manière idempotente en PostgreSQL 18 (`visibility_mode = 'CONFIDENTIAL_RESTRICTED'`, `settings_jsonb.ui_visibility_mode = 'PRIVATE_USER'`, `settings_jsonb.personal_owner_user_id = <user_id>`), strictement accessible à son propriétaire (aucun accès implicite par un autre `PLATFORM_ADMIN`).

**Given** un utilisateur connecté sur `/cockpit` avec moins de `6/6` jalons d'accostage complétés et `1` modèle IA `chat` actif configuré
**When** il consulte le Guide d'Accostage unifié et la barre latérale de navigation
**Then** le Guide d'Accostage affiche les `6` jalons dont `4. Premier Espace d'équipe`, ses coches vertes et flèches d'action sont alignées verticalement à proximité immédiate du texte, le bloc demeure **non repliable** tant que la complétion est `< 6/6`, et l'entrée **`Mes Processus`** est immédiatement dégrisée et navigable dès `1` modèle IA actif (sans attendre un second modèle ou un modèle d'embedding).

---

### Story 25.2: Coquille 9 Entrées (`Mon Organisation` & `Administration` 5 Onglets), TopBar `[O] ORCIA › Écran`, Sélecteur d'Espace Unique & Retrait `ⓘ` / `Active context`

As a UX Designer (`Sally`) & Utilisateur Authentifié (`Claire`, `Marc`, `Lucas`, `Thomas`),
I want naviguer via une barre latérale à **9 entrées fixes** (incluant **`Mon Organisation`** sous `Mes Espaces` visible par tous les utilisateurs authentifiés — lecture seule pour les membres simples, édition/invitation selon `can_*` pour Leads/Admins — et le renommage de `Configuration` en **`Administration`** strictement réservé `PLATFORM_ADMIN` / `SECOPS` à `5` onglets : `Comptes & Habilitations`, `Authentification`, `Modèles IA`, `Connecteurs`, `Packs Métiers`), cliquer sur **`[O] ORCIA › <Écran>`** tout en haut à gauche de la `TopHeaderBar` pour revenir à `/cockpit` (sans doublon `[O] ORCIA` dans la Sidebar), basculer grâce à un **sélecteur unique d'`Espace actif`** groupé (`Personnel` + `Équipe / BU`) câblé sur tous les écrans, et bénéficier d'en-têtes dépourvus d'icônes flottantes `ⓘ` et de badge `Active context`,
So that l'architecture d'information soit cohérente entre la Sidebar, la `TopHeaderBar` et l'ensemble des écrans métiers sans duplication de sélecteurs ni bruit visuel (`DESIGN.md`, `EXPERIENCE.md`).

**Dépendances :** Dépend de `Story 25.1` (Espace Personnel disponible dans le groupe `Personnel` du sélecteur).
**CAP couvertes :** `CAP-058`, `CAP-060`, `CAP-064`, `CAP-067`, `CAP-203`.
**Fichiers impactés :** `packages/ui/src/primitives/FourZoneDirectionCShell.tsx`, `packages/ui/src/primitives/FourZoneSidebarRail.tsx`, `packages/ui/src/shell/AppShellTopbar.tsx`, `packages/ui/src/shell/GlobalSidebar.tsx`, `packages/ui/src/shell/ScopeSwitcher.tsx`, `apps/web/src/components/ShellContainer.tsx`, `apps/web/src/components/shellPresets.ts`, `apps/web/src/components/shellBreadcrumbAndScope.ts`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/features/admin/`, `apps/web/src/features/organization/`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-2-coquille-9-entrees-mon-organisation-administration-topbar-orcia-et-selecteur-espace-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un utilisateur authentifié (membre simple, Lead ou `PLATFORM_ADMIN` / `SECOPS`) sur l'application Desktop
**When** il inspecte la barre latérale gauche et la `TopHeaderBar` sur `/cockpit`, `/assistant`, `/processes`, `/agents`, `/spaces`, `/organization`, `/finops` et `/settings`
**Then** la Sidebar affiche exactement **`9` entrées fixes** (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `Mon Organisation`, `FinOps`, `Administration`, `Aide`), `Mon Organisation` (`/organization`) est accessible à tous les utilisateurs authentifiés (en lecture seule de l'organigramme pour un membre simple, avec actions d'édition/invitation conditionnées par `can_*` pour Leads/Admins), `Administration` est visible uniquement pour `PLATFORM_ADMIN` / `SECOPS` avec strictement **`5` onglets** (`Comptes & Habilitations`, `Authentification`, `Modèles IA`, `Connecteurs`, `Packs Métiers`), la `TopHeaderBar` affiche tout en haut à gauche le logo cliquable **`[O] ORCIA › <Écran>`** ramenant à `/cockpit`, et aucun doublon `[O] ORCIA` n'apparaît dans la Sidebar.

**Given** le sélecteur unique d'`Espace actif` en haut de la Sidebar et les en-têtes de cartes principales des écrans métiers
**When** l'utilisateur change d'espace (entre `Personnel` et `Équipe / BU`) puis navigue entre `Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces` et `FinOps`
**Then** un seul sélecteur d'espace groupé (`Personnel` + `Équipe / BU`) remplace l'ancien double sélecteur empilé, l'espace sélectionné reste synchronisé et actif sur `100 %` des 6 écrans cibles (avec survie au `F5`), aucune icône flottante `ⓘ` n'apparaît dans les en-têtes de cartes principales (l'aide étant pilotée par `? Aide` de la `TopHeaderBar`), et aucun badge `Active context` / `Contexte actif` n'est affiché.

---

### Story 25.3: Sobriété Cockpit Jour 0, Purge du Run Démo RAM (`marc.lead@orcia.io`) & Retrait des Blocs d'Attente à Vide

As a Architecte (`Winston`) & UX Designer (`Sally`),
I want purger définitivement le run démo en mémoire RAM (`marc.lead@orcia.io`) et la constante `DEFAULT_ARBITRATION_OPTIONS`, supprimer le bandeau `"Aucune décision en attente"`, le prompt rapide `"Accès rapide à Mon Assistant"` et le badge `"Contexte actif"` du `Cockpit`, et n'afficher des cartes d'ancrage ou d'arbitrage que lorsqu'une action réelle est effectivement en attente en PostgreSQL 18,
So that le `Cockpit` respecte strictement la sobriété Jour 0 (`<= 3` blocs, zéro donnée fictive RAM) tout en affichant instantanément les vraies décisions humaines persistées en PG18 (`AD-17`, `DESIGN.md`, `EXPERIENCE.md`).

**Dépendances :** Parallélisable après `Story 25.1` (coordonnée avec `Story 25.2` sur le `Cockpit`).
**CAP couvertes :** `CAP-005`, `CAP-023`, `CAP-060`, `CAP-100`.
**Fichiers impactés :** `apps/web/src/features/cockpit/index.tsx`, `apps/web/src/features/cockpit/cockpitGovernanceHelpers.ts`, `apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx`, `apps/web/src/features/cockpit/CockpitRunsSection.tsx`, `apps/web/src/features/cockpit/useCockpitGovernanceController.ts`, `packages/ui/src/primitives/StreamlinedCockpitView.tsx`, `packages/ui/src/primitives/CockpitDecisionsCard.tsx`, `packages/ui/src/primitives/CockpitOrientationCards.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-3-sobriete-cockpit-jour0-purge-run-demo-ram-et-retrait-blocs-attente-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** le code source `apps/web/src/**` et `packages/ui/src/**` audité après purge et redémarrage sur une base Jour 0
**When** un utilisateur ouvre `/cockpit` avec `0` exécution / arbitrage en base PG18
**Then** aucune référence à `marc.lead@orcia.io` ni à `DEFAULT_ARBITRATION_OPTIONS` n'existe dans le code de production, le bandeau `"Aucune décision en attente"`, le bloc prompt rapide `"Accès rapide à Mon Assistant"` et le badge `"Contexte actif"` ne sont jamais rendus sur `/cockpit`, et aucune carte factice d'ancrage humain ou d'arbitrage ne s'affiche tant qu'aucune action réelle n'est en attente en PostgreSQL 18.

**Given** une exécution réelle persistée en PostgreSQL 18 requérant un ancrage humain (`human_authored_required`) ou un arbitrage (`WAITING_FOR_HUMAN_ARBITRATION`) sur l'espace actif
**When** l'utilisateur ouvre `/cockpit`
**Then** la carte d'ancrage ou d'arbitrage correspondant à l'enregistrement réel PG18 s'affiche dans la limite de sobriété (`<= 3` blocs) et disparaît dès traitement ou résolution en base.

---

### Story 25.4: Hub Modèles IA — Suppression PG18 Fiable sans Fallback RAM (`settingsAiModelsFallback.ts`), `<OrciaSpinner />` Unifié, Erreur Locale & Masquage Réindexation

As a Administrateur Plateforme (`Thomas`) & Tech Lead (`Amelia`),
I want supprimer tout fallback mémoire RAM (`settingsAiModelsFallback.ts`) sur le Hub des Modèles IA afin que l'ajout et la suppression soient `100 %` fiables en PostgreSQL 18 (avec propagation immédiate vers `F5` et l'état réel), unifier les états de chargement sur `<OrciaSpinner />`, afficher toute erreur ou timeout de test/connexion localisée directement sous la carte du modèle concerné, et masquer le bloc de réindexation vectorielle tant que `0` document est indexé,
So that la gestion des modèles IA dans `Administration › Modèles IA` (`/settings/ai-models`) reflète fidèlement PostgreSQL 18 sans faux succès RAM ni bruit visuel (`AD-24`, `AD-17`).

**Dépendances :** Parallélisable avec `Story 25.2` et `Story 25.3`.
**CAP couvertes :** `CAP-053`, `CAP-100`, `CAP-190`.
**Fichiers impactés :** `apps/web/src/features/admin/ai-models/AiModelConfigModal.tsx`, `apps/web/src/features/admin/ai-models/AiModelDeleteDialog.tsx`, `apps/web/src/features/admin/ai-models/AiModelsMasterTable.tsx`, `apps/web/src/features/admin/ai-models/AiModelReindexPanel.tsx`, `apps/web/src/features/admin/ai-models/aiModelsApiBridge.ts`, `apps/web/src/features/admin/ai-models/useAiModelConfigModalState.ts`, `apps/api/src/orcia_api/routers/ai_models_hub.py`, `apps/api/src/orcia_api/routers/_ai_models_test_and_reindex_routes.py`, `packages/ui/src/primitives/`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-4-hub-modeles-ia-suppression-fiable-spinner-unifie-erreur-locale-et-masquage-reindexation-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un administrateur connecté sur `Administration › Modèles IA` (`/settings/ai-models`)
**When** il supprime un modèle IA existant puis recharge la page (`F5`), et qu'il lance un test de connexion provoquant un timeout ou une erreur fournisseur (`401`/`404`/`5xx`)
**Then** le modèle supprimé est effectivement supprimé en PostgreSQL 18 sans aucun recours à `settingsAiModelsFallback.ts` (absent du bundle/runtime) et ne réapparaît plus après `F5`, l'action en cours affiche le composant unifié `<OrciaSpinner />`, et le message d'erreur ou de timeout s'affiche localisé directement sous la carte/ligne du modèle testé (`[role="alert"]`) sans effacer l'état des autres modèles.

**Given** un environnement comportant `0` document indexé dans `kb_documents` / `kb_chunks` en PostgreSQL 18
**When** l'administrateur consulte `Administration › Modèles IA` (y compris après configuration ou changement du modèle d'embedding)
**Then** le bloc/panneau de réindexation vectorielle reste strictement masqué tant que `0` document indexé existe en base, et n'apparaît que lorsque `>= 1` document indexé nécessite une réindexation.

---

### Story 25.5: Découplage `Mon Assistant` sans Modèle d'Embedding, Blocage Ciblé des Sources RAG (`POST /datasources` + UI) & Clôture Epic 25

As a Utilisateur (`Lucas`, `Hélène`), Architecte (`Winston`) & Tech Lead (`Amelia`),
I want rendre **`Mon Assistant`** immédiatement utilisable dès qu'au moins `1` modèle `chat` actif est configuré — même sans modèle d'`embedding` actif GLOBAL (`AssistantHarness` en mode conversationnel direct + Rôle/Casquette + Glossaire/Ontologie SQL sans interroger `pgvector`, avec indicateur UI non-bloquant signalant l'inactivité de la recherche documentaire) —, appliquer le blocage **`HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL`** dès l'ajout (`POST /datasources`), la synchronisation et l'UI pour toute source RAG (`source_nature != 'SOURCE_CODE'`) tout en préservant les sources `SOURCE_CODE` (GitNexus AST sans embedding), puis clôturer l'Epic 25 avec mise à jour de `capabilities.yaml` et `pnpm site:sync && pnpm site:check`,
So that les utilisateurs puissent échanger avec `Mon Assistant` dès la configuration d'un premier LLM `chat` sans friction artificielle, tout en conservant une frontière matérielle stricte contre toute ingestion RAG dégradée (`AD-8`, `AD-16`, `AD-24` amendés Epic 25).

**Dépendances :** Dépend de `Stories 25.1`..`25.4`. Clôture l'Epic 25.
**CAP couvertes :** `CAP-011`, `CAP-022`, `CAP-074`, `CAP-075`, `CAP-076`, `CAP-180`, `CAP-190` (+ vérification transverse et clôture `capabilities.yaml`).
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/orchestration/assistant_harness.py`, `packages/orcia-core/src/orcia_core/rag/`, `apps/api/src/orcia_api/routers/assistant.py`, `apps/api/src/orcia_api/routers/assistant_llm_bridge.py`, `apps/api/src/orcia_api/routers/workspace_datasources.py`, `apps/web/src/features/assistant/`, `apps/web/src/features/workspaces/sources/`, `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-5-decouplage-assistant-sans-modele-semantique-blocage-sources-rag-et-cloture-epic-25-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une instance ORCIA disposant d'au moins `1` modèle `chat` actif configuré et de `0` modèle d'`embedding` actif GLOBAL
**When** un utilisateur ouvre `/assistant` et envoie un message à `Mon Assistant`
**Then** la saisie et l'envoi ne sont pas bloqués, `AssistantHarness` répond en streaming SSE réel en exploitant le mode conversationnel direct + Rôle/Casquette + Glossaire/Ontologie SQL (sans appel `pgvector`), et un indicateur UI non-bloquant informe l'utilisateur que la recherche documentaire est inactive tant qu'aucun modèle d'indexation sémantique n'est configuré (avec lien vers `Administration › Modèles IA`).

**Given** une instance ORCIA avec `0` modèle d'`embedding` actif GLOBAL et un utilisateur tentant d'ajouter ou synchroniser une source documentaire RAG (`source_nature != 'SOURCE_CODE'`) vs une source `SOURCE_CODE`
**When** la requête est soumise via l'UI (`Mes Espaces › Documents & Sources`) ou l'API (`POST /api/v1/workspaces/{workspace_id}/datasources` et endpoint de synchronisation)
**Then** l'ajout ou la synchronisation d'une source RAG (`source_nature != 'SOURCE_CODE'`) est explicitement bloqué côté UI (indication claire + redirection vers `Administration › Modèles IA`) et rejeté côté API avec `HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL` (RFC 9457), tandis que l'ajout et la synchronisation d'une source `SOURCE_CODE` (GitNexus AST sans embedding) réussissent et restent persistés en PG18.

**Given** l'ensemble des Stories `25.1`..`25.5` validées à `100 %` vert sur les 5 couches `AD-17`
**When** la clôture de l'Epic 25 met à jour `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml` et exécute `pnpm site:sync && pnpm site:check`
**Then** toutes les vérifications Python (`ruff`, `mypy --strict`, `lint-imports`, `pytest --cov-fail-under=90`), TypeScript (`pnpm turbo run lint typecheck test`), `lint_spine.py` (`0 findings`) et `pnpm site:check` passent sans erreur, et `epic-25` passe à `done`.

---

## Epic 26: Unified, Governed & Persistent "Mon Assistant" Harness — Single Turn Engine, Governed Tool Loop, Real Context, Scope Security & Zero RAM State (AD-3, AD-15, AD-19, AD-24, proposed AD-25)

Remediate the "Mon Assistant" harness debt identified by [`2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md`](../implementation-artifacts/tech-lead-reports/2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md) (38 findings `H-01..H-38`, including 14 P0). The master plan is [`sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md`](./sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md) (**8 lots, 13 stories**), governed by [`epic-26-decisions-grill-2026-11-21.md`](../implementation-artifacts/epic-26-decisions-grill-2026-11-21.md) (`D1–D11` amended by `R1–R9`).

The target converges the three existing execution paths into **one unified turn engine** (`AssistantTurnEngine`):
- **Speed 1** via a single-shot fast-path (`TTFT p95 < 1.2 s`);
- **Speed 2 / Speed 3** on the `ASSISTANT` profile of `NonDeterministicReflexiveRuntime`;
- **Single-process hosting (`R1`)** inside `apps/api` (`asyncio.Task` + `SIGTERM` drain, Redis registry/streams/`stop`, no Dramatiq worker);
- **Fixed `N1–N5` phases** with sealed constitutional guards (`Layer 1`, `N1`, `V5`, `CitationGuard`), Mode A 3-level text governance only (`R2` Mode B deferred in `ACTION_ITEM-26.1`), and a UI **"Deepen"** button after Speed 1 instead of auto-escalation (`R3`);
- **Direct atomic cutover (`R4`)** in `26.7` without a legacy facade (`ACTION_ITEM-26.2`), **audit ledger** phantom tracking without a drafts table (`R5`), **measure-first** prompt assembly without a Redis prompt cache (`R6`, `ACTION_ITEM-26.3`), **3 text adapters** + **2 native tool-calling dialects** (`R7`, `ACTION_ITEM-26.4`), and **env-var SSRF allowlist + DNS pinning** (`R8`, `ACTION_ITEM-26.5`).

All changes preserve `25-5` decoupling invariants (assistant active with `1` `chat` model without `embedding`) and default `PROCESS` behavior in `NonDeterministicReflexiveRuntime`.

**Execution order (`R9`, sequential Lot 3 & risk-tiered workers):**
- Lot 0: `26.0` (`bmad-architect-worker` `pro` → STOP)
- Lot 1: `26.1` (2 `flash` workers + `pro` review)
- Lot 2: `26.2` (1 `flash` worker)
- Lot 3 (sequential on `workspace: "inherit"`, linear Alembic chain): `26.3` → `26.4a` → `26.4b` (1 `flash` worker each)
- Lot 4: `26.5` (1 `flash` worker)
- Lot 5: `26.6a` (1 `flash`) → `26.6b` (2 `flash` workers + `pro` review)
- Lot 6: `26.7` (2 `flash` workers + mandatory `pro` review) → `26.8` (1 `flash` worker)
- Lot 7: `26.9` (1 `flash` worker) → `26.10` (1 `flash` worker + mandatory final `pro` closure gate)

No story starts until its dependencies are `done`. Each story produces one atomic local commit, followed by a STOP and user GO check at the end of each lot.

---

### Story 26.0: ADR Unified Assistant Turn Engine (`AD-25`), `AD-15`/`AD-21`/`AD-24` Updates, SSE v2 Contract & Env-Var SSRF Policy

As a Principal Architect (`Winston`),
I want to ratify and record decisions `D1–D11` as amended by `R1–R9` in the Architecture Spine and ERD, and freeze the OpenAPI/SSE v2 turn contract,
So that all 12 implementation stories execute against an unambiguous, linted architectural contract.

**Lot:** 0 — Framing. **Dependencies:** Epic 25 closed (`epic-25: done`). **Agent:** `bmad-architect-worker` (`pro`).
**Findings covered:** `H-38` + prerequisites `D1–D11` / `R1–R9`.
**CAPs covered:** `none (doc)`.
**Impacted files:** `docs/implementation-artifacts/epic-26-decisions-grill-2026-11-21.md` (input), `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md`, `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md` (ERD), `docs/planning-artifacts/sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-0-adr-unified-turn-engine-sse-v2-and-ssrf-policy-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the Epic 26 master plan, consolidated decisions `D1–D11` + `R1–R9`, and audit `H-01..H-38`
**When** the ADR is authored
**Then** `ARCHITECTURE-SPINE.md` adds `AD-25` ("Unified Assistant Turn Engine") locking: Speed 1 single-shot fast-path (`TTFT p95 < 1.2 s`, post-first-byte persistence); Speed 2/3 `ASSISTANT` profile on `NonDeterministicReflexiveRuntime`; single-process `apps/api` `asyncio.Task` hosting with Redis Streams/registry/`stop` and `SIGTERM` graceful drain (crashed turns flagged `ERR_ASSISTANT_TURN_INTERRUPTED`, no Dramatiq worker, `R1`); **"Deepen"** UI button creating linked Speed 2 turns (`parent_turn_id`, deterministic `low_evidence`, no auto-escalation, `R3`); fixed `N1–N5` phases with sealed constitutional guards and Mode B graphical studio deferred (`R2`); 3 preserved text streaming adapters + 2 native tool-calling dialects (`OpenAI-compatible` & `Anthropic`, `R7`); no assembled-prompt Redis cache until measured p95 `> 50 ms` (`R6`, `FR-33` / Story `10.2` deferral note); no drafts persistence table & phantom citations routed to `audit_ledger` (`R5`); direct cutover without strangler facade (`R4`); and forbidden `ConnectorReflexiveWriteGateAdapter` in `ASSISTANT` profile.

**Given** security, data model, and MCP requirements
**When** `AD-15`, `AD-21`, `AD-24`, and `architecture.md` ERD are updated
**Then** `AD-15` references `AD-25`; `AD-21`/`AD-24` specify ops env-var SSRF allowlist `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` (`localhost` only when `ORCIA_ENV in ("local", "test")`), permanent cloud-metadata/link-local/internal-port blocks, connection-time DNS pinning (`R8`), public Day-0 `GET /bootstrap/platform-setup-state` projection `{is_initialized, step}`, and 0-token `supports_tools` Hub discovery (`+ PLATFORM_ADMIN` override, `D5`); and the ERD specifies `assistant_thread_messages` (`D4`) and `assistant_turn_feedback` upsert table (`R5`, no Mode B or drafts tables).

**Given** the SSE v2 and canonical REST contract
**When** the specification is frozen and checks run
**Then** SSE events `thinking_delta`, `tool_call`, `tool_result`, `approval_required`, `token_delta`, `citation_map`, `turn_completed` (with `low_evidence`), `turn_stopped`, and `stream_error` (RFC 9457 + `trace_id`, including `ERR_ASSISTANT_TURN_INTERRUPTED` and `422 ERR_MODEL_TOOLS_UNSUPPORTED`) and routes `POST /api/v1/assistant/turns`, `GET /api/v1/assistant/turns/{turn_id}/stream?after=`, `GET /api/v1/assistant/turns/active`, `POST /api/v1/assistant/turns/{turn_id}/{stop,approve,synthesize-now,feedback}`, and `GET /api/v1/assistant/threads/{thread_id}/messages` are fully specified; `npx gitnexus analyze` refreshes cleanly (`0` `assistant_*` symbol with empty `filePath`); and `lint_spine.py` passes with `0 findings`.

---

### Story 26.1: Immediate Security Hardening — Pre-Stream Scope & Observer Guards, Server-Side `READ_SOURCE` / `CONFIDENTIAL_RESTRICTED`, Layer 1 Immutability, Env-Var SSRF + DNS Pinning & Secret Hygiene

As a SecOps Lead (`Sophie`) and Workspace User,
I want every `/api/v1/assistant/*` mutation route to enforce workspace scope access and `READ_ONLY_OBSERVER` checks before opening any response stream, filter `READ_SOURCE` and `CONFIDENTIAL_RESTRICTED` context server-side, prevent Layer 1 overrides, enforce DNS-pinned SSRF checks, and protect setup state and secrets,
So that no user can trigger cross-workspace IDOR, crash ASGI mid-stream, leak confidential data or API keys, or inject privileged instructions.

**Lot:** 1 — Security. **Dependencies:** `26.0`. **Agent:** 2 distinct `bmad-dev-worker` (`flash`: Impl + Independent Verification) + `bmad-architect-worker` (`pro` review, `R9`).
**Findings covered:** `H-06`, `H-07`, `H-08`, `H-15`, `H-16`, `H-17`, `H-30` (prod `assert`).
**CAPs covered:** `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-073`, `CAP-074` (`D9`: downgrade `CAP-022`, `CAP-070`, `CAP-072` to `verification: api` in `docs/product/capabilities.yaml`).
**Impacted files:** `apps/api/src/orcia_api/routers/assistant_workspace.py`, `assistant_workspace_governance.py`, `assistant_workspace_citations.py`, `assistant_workspace_folders.py`, `assistant.py`, `assistant_llm_prompts.py`, `assistant_llm_providers.py`, `assistant_llm_resolver.py`, `assistant_background_turns.py`, `bootstrap_accostage.py`, `apps/api/src/orcia_api/schemas/assistant_citations_and_folders.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py`, `assistant_three_speed_router.py`, `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py`, `tests/security/`, `docs/product/capabilities.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-1-immediate-security-hardening-scope-observer-and-ssrf-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a `READ_ONLY_OBSERVER` user or a user lacking access to the target workspace (addressed by UUID **or** slug)
**When** they call any mutating `/api/v1/assistant/*` endpoint (`three-speed/stream|turn|stop|feedback`, `chat*`, `governance*`, `citations/*`, `artifacts/action`, `folders*`, `threads*`, `launch-process`)
**Then** FastAPI dependencies (`resolve_workspace_access` / `ScopeAccessGuard` resolving both slugs and UUIDs via `evaluator`) reject the call with `HTTP 403` (`ERR_OBSERVER_MODE_READ_ONLY` or scope-denied RFC 9457 + `trace_id`) **before HTTP `200` headers or any SSE byte**, governance edits are scoped strictly to the caller's authorized workspaces, and cross-workspace IDOR security tests pass.

**Given** an assistant turn on a workspace containing `CONFIDENTIAL_RESTRICTED` or unauthorized sources
**When** prompt context is assembled and citations are checked
**Then** `READ_SOURCE` permissions are resolved strictly server-side (`PermissionBrokerService` / `evaluator`), client field `reader_allowed_source_uris` is removed from schemas and SDK (`0-diff`), zero unauthorized or confidential content appears in captured LLM payloads, and model endpoint resolution uses the real workspace `scope_id` (removing the hardcoded UUID).

**Given** a turn payload containing `system_instructions_override`, `role: "tool"` history messages, or `[LAYER_*]`/`[CONSTITUTIONAL_*]` tags in user/workspace/folder text
**When** instructions are built
**Then** Layer 1 cannot be overridden on assistant routes, history is restricted to `user|assistant`, user/folder blocks are delimited and sanitized, and `agents_and_skills.py` retains its existing behavior under regression tests.

**Given** an LLM endpoint in PG18 targeting cloud metadata, link-local, internal ORCIA ports (`5432`, `6379`, S3), or a hostname resolving via DNS rebinding to `169.254.169.254`
**When** saved in Hub or connected at runtime
**Then** validation rejects it both on save and at connection time using **DNS resolution pinning** (`getaddrinfo`), while hosts/CIDRs declared in ops env var `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` (`localhost` permitted only when `ORCIA_ENV in ("local", "test")`, `R8`) remain reachable; `GET /bootstrap/platform-setup-state` returns only `{is_initialized, step}` unauthenticated (`0` sensitive values, `0` internal URIs, `pnpm db:reset` intact) with detailed view gated to `PLATFORM_ADMIN`; provider credential field is excluded from `platform_setup_snapshot`; `str(exc)` passes through the redaction scrubber with bounded `_REGISTERED_SECRET_VALUES`; production `assert det_ms < 80.0` is deleted; and `CAP-022`, `CAP-070`, `CAP-072` move to `verification: api` (`pnpm site:sync && pnpm site:check` passes).

---

### Story 26.2: Core LLM Streaming Extraction (`LlmStreamingPort`, All 3 Text Adapters Preserved), Unified Localized `AssistantPromptBuilder`, Removal of Prod Test Branches & `< 300 L` Splits

As a Tech Lead (`Amelia`),
I want to extract LLM streaming, prompt building, and usage telemetry out of `apps/api/routers/` into `orcia_core` ports/adapters, unify the three prompt builders into one localized `AssistantPromptBuilder`, derive default hats from user profiles, remove production `testclient`/`pytest` branches, and split oversized harness files,
So that the harness complies with `AD-1` / `AD-19` and provides a clean core foundation for persistence and convergence.

**Lot:** 2 — Core Foundations. **Dependencies:** `26.1`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-24`, `H-25`, `H-30` (P2 hardcoded literals), `H-31`, `H-34`.
**CAPs covered:** `CAP-069`, `CAP-074`, `CAP-076`.
**Impacted files:** `apps/api/src/orcia_api/routers/assistant_llm_{bridge,prompts,providers,resolver,gemini_adapter}.py`, `assistant_background_turns.py`, `_assistant_usage_telemetry.py`, `_assistant_workspace_context.py`, `agents_and_skills.py`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py`, `core_and_lifespan.py`, `packages/orcia-core/src/orcia_core/ports/`, `packages/orcia-core/src/orcia_core/orchestration/assistant_harness.py`, `assistant_governance.py`, `assistant_three_speed_router.py`, `assistant_agent.py`, `assistant_citations_and_v5_guard.py`, `assistant_folders_and_sharing.py`, `apps/api/src/orcia_api/schemas/assistant.py`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-2-core-llm-streaming-extraction-and-unified-prompt-builder-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** ~2,100 L of LLM bridge, prompt, provider, and telemetry logic currently inside `apps/api/routers/`
**When** extracted to `orcia_core`
**Then** `LlmStreamingPort` lives in `orcia_core/ports/` (zero SDK imports) with concrete `httpx` adapters in `orcia_core` preserving all **3** text/reasoning streaming adapters (OpenAI-compatible, Anthropic, and native Gemini `CAP-076`, `R7`) following `embedding_httpx.py`; routers become thin HTTP handlers; `orcia_api` imports zero `_internal` modules; `orcia_core` imports zero `testing.cassette_llm`; inter-router import `agents_and_skills.py` → `assistant_llm_bridge` is replaced by the port; and `lint-imports` holds `5/5` contracts.

**Given** the three existing prompt builders (`AssistantHarness.assemble_prompt`, `build_assistant_system_instructions`, `assemble_five_layers_preview`)
**When** unified into `AssistantPromptBuilder`
**Then** a single builder assembles all 5 layers (Layer 1 immutable), localized cleanly via `fr`/`en` dictionaries (`0` French leakage when `locale="en"`), resolving default `active_hat` from `user.human_profile_archetype` (never RBAC `PLATFORM_ADMIN`), and replacing hardcoded `pack_key`, pilot URIs, and synthetic latencies with real values and `perf_counter()` timings.

**Given** production harness source files
**When** audited
**Then** zero `client_host == "testclient"`, `"pytest" in sys.modules`, or `ORCIA_FORCE_LIVE_LLM_IN_TESTS` branches remain (Cassette LLM injected strictly at test Composition Root), and all touched Python/TS harness files stay `<= 300` lines.

---

### Story 26.3: Turn Reliability — Redis Registry `(workspace, user, turn_id)`, Graceful Drain & Liveness Key, Cursor SSE Reattachment, 100% Async Loop & Rate Limiting

As a Multi-Tab Assistant User and Platform Operator,
I want every turn to be tracked in Redis, cleanly stoppable with partial FinOps accounting, resumable via SSE cursor across workers and F5, and executed on a strictly non-blocking async event loop with bounded retries and rate limits,
So that concurrent tabs never overwrite each other, API pods remain responsive, and `--workers > 1` works reliably.

**Lot:** 3 — Reliability & Persistence (1st of 3 sequential stories on `workspace: "inherit"`, `R9`). **Dependencies:** `26.2`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-10`, `H-11`, `H-20`, `H-21`, `H-23`, `H-33`.
**CAPs covered:** `CAP-069`, `CAP-075`.
**Impacted files:** core turn orchestrator from `26.2`, `apps/api/src/orcia_api/routers/assistant_workspace.py`, `assistant.py`, `packages/orcia-core/src/orcia_core/orchestration/step_executors.py`, `assistant_agent.py`, `packages/orcia-core/src/orcia_core/rag/context_adapters.py`, `hybrid_rag_service.py`, `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` (`SIGTERM` drain), `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-3-turn-reliability-redis-registry-async-loop-and-rate-limit-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** two concurrent turns started on the same workspace by different tabs or users
**When** they execute inside `apps/api` (`R1`)
**Then** each turn is indexed in Redis by `(workspace_id, user_id, turn_id)` with TTL and a refreshed liveness key; active `asyncio.Task` handles are held in a tracked set with `add_done_callback` (zero task overwrite or premature GC); event streams are bounded in Redis Streams with post-completion TTL; module-level `ACTIVE_WORKSPACE_TURNS` is deleted; and `SIGTERM` triggers bounded graceful draining capped by the profile wall-clock budget (crashed/orphaned turns emit `stream_error` `ERR_ASSISTANT_TURN_INTERRUPTED` on reattach without auto-retry, no Dramatiq worker).

**Given** a running turn where the user invokes `stop` or reloads/reconnects SSE across workers
**When** `stop` or `GET …/stream?after=<cursor>` runs
**Then** `stop` propagates via Redis, emits terminal `turn_stopped`, and persists partial streamed tokens in `audit_ledger` inside `finally` (`turn_id` idempotency preserved); cursor reattachment replays missed events without duplicates; and a 2-instance integration test sharing Redis verifies cross-worker `stop`, reattachment, and orphan crash detection.

**Given** all execution and RAG paths
**When** turns run
**Then** zero blocking calls hit the event loop (remove `ThreadPoolExecutor(...).result()`, convert SSE generators and hybrid RAG search to `async`, remove `if loop.is_running(): pass`); provider/empty-stream failures emit structured `stream_error` (RFC 9457 + `trace_id`); bounded pre-first-byte retry (2x backoff on `429/502/503`) + inter-chunk idle timeout apply; and Redis sliding-window rate limits + per-user concurrency semaphores enforce `HTTP 429` RFC 9457.

---

### Story 26.4a: Redis Thread Turn Locks, Outbox Domain Event Emission, Hub Snapshot Invalidation, Prompt-Cache Removal (`R6`) & Alembic DDL Migration

As a Platform Operator,
I want thread turn locks and AI Hub snapshots coordinated via Redis and invalidated cleanly, per-request DDL migrated to Alembic, and dead in-memory prompt-cache machinery removed pending latency measurement (`R6`),
So that multi-worker coordination is consistent without degrading PostgreSQL on every request or maintaining premature cache invalidation complexity.

**Lot:** 3 — Reliability & Persistence (2nd of 3 sequential stories on `workspace: "inherit"`, `R9`). **Dependencies:** `26.3`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-09` (thread locks), `H-19` (resolved by removal), `H-22` (Outbox), `H-32`, `H-35`.
**CAPs covered:** `CAP-071`, `CAP-073`.
**Impacted files:** `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py`, `_assistant_folders_sync.py`, `assistant_folders_and_sharing.py`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py`, `_rag_availability_guards.py`, `apps/api/src/orcia_api/routers/assistant_llm_resolver.py` (or core successor), `infra/migrations/versions/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-4a-redis-thread-locks-outbox-hub-invalidation-and-alembic-ddl-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** thread turn locking and legacy prompt-cache code (`R6`)
**When** the application boots from the real Composition Root
**Then** thread locks use `RedisThreadTurnLock` (`SET NX EX`) wired to `app.state.redis_client` (`InMemory*` kept solely under `tests/unit/fakes/`); `InMemoryPromptCacheStore`, `AssembledPromptCachePort`, and forged `outbox_event_id` generation are **deleted** (no Redis assembled-prompt cache or Outbox cache consumer built under measure-first policy `R6`, tracked via `ACTION_ITEM-26.3`).

**Given** AI Hub updates and harness domain events
**When** models change or assistant events occur
**Then** `platform_setup_snapshot` uses a bounded Redis/local TTL invalidated upon AI Hub mutations, and harness lifecycle events emit through `SqlDomainEventsOutboxRepository` (`domain_events_outbox`).

**Given** `ensure_ai_model_mappings_schema_on_postgres18` and `_rag_availability_guards.py`
**When** a turn executes
**Then** zero runtime `CREATE`/`ALTER`/`CREATE INDEX` DDL runs per request (schema managed by an incremental raw-SQL Alembic revision with tested `upgrade()`/`downgrade()`), and zero ephemeral `httpx.AsyncClient()` instances are created (all reuse `app.state.http_client`).

---

### Story 26.4b: PG18 Persistence for Mode A 3-Level Governance, Turn Feedback, Folder Metadata & `audit_ledger` Phantom Citation Logging — Mode B Deleted & Drafts Omitted (`R2`, `R5`)

As a Workspace Admin (`Claire`) and Assistant User,
I want Mode A 3-level governance instructions, turn feedback, and folder attachments/tags persisted in PostgreSQL 18, phantom citations logged to the append-only `audit_ledger`, and unused RAM-only Mode B routes removed,
So that assistant configuration, feedback, and compliance logs survive restarts and multi-worker deployments without creating orphan SQL tables.

**Lot:** 3 — Reliability & Persistence (3rd of 3 sequential stories on `workspace: "inherit"`, linear Alembic `down_revision` chained on `26.4a`, `R9`). **Dependencies:** `26.4a`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-09` (governance, phantom audit, feedback, folders), `H-37` (partial: `BUG-E2E-01b`).
**CAPs covered:** `CAP-070`, `CAP-072`, `CAP-073`.
**Impacted files:** `infra/migrations/versions/`, `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py`, `assistant_citations_and_v5_guard.py`, `assistant_folders_and_sharing.py`, `_internal/_sql_assistant_folders_queries.py`, new `_internal/sql_assistant_*.py`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py`, `apps/api/src/orcia_api/routers/assistant_workspace.py`, `assistant_workspace_governance.py`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-4b-pg18-persistence-mode-a-governance-feedback-and-folders-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a reset database (`pnpm db:reset`) upgraded with Story `26.4b` Alembic migrations (chained linearly on `26.4a`, single `alembic heads`)
**When** `upgrade()` and `downgrade()` execute
**Then** Mode A governance (`USER`, `WORKSPACE`, `TEAM`) persists in existing `workspace_customization_overrides` (migration `0003`); new `UUIDv7` raw-SQL table `assistant_turn_feedback` (`UNIQUE (turn_id, user_id)` upsert) stores turn feedback; `assistant_folders` adds `working_attachments_uris JSONB` and `evidence_tags TEXT[]`; and **neither** a Mode B studio table (`R2`, `ACTION_ITEM-26.1`) **nor** a citation drafts table (`R5`) is created.

**Given** RAM-only Mode B routes and `_phantom_audit_log` (`R2`, `R4`, `R5`)
**When** the story completes
**Then** `POST /api/v1/assistant/governance/mode-b/{save,reset}` (zero UI callers), their schemas, SDK entries (`0-diff`), and `_studio_graphs` RAM state are deleted; `GET /governance` returns Mode A configuration only; `AssistantCitationAndV5GuardService._phantom_audit_log` RAM list is replaced by idempotent `audit_ledger` events (`ASSISTANT_PHANTOM_CITATION_PURGED` via `SqlAuditLedgerService`); and `execute_artifact_card_action` / `_saved_drafts` remain temporarily intact solely to keep E2E spec `21` (`/artifacts/action`) passing until deleted together in `26.7`.

**Given** Mode A updates, turn feedback, folder attachments/tags, and phantom citation events
**When** verified on the real Composition Root `create_app()` (zero `dependency_overrides`) after cold cache eviction
**Then** PG18 `SELECT` integration tests prove full durability across restarts, zero business state remains in `AssistantFourLevelGovernanceService` or `_folder_meta`, and `test_zero_orphan_sql_adapters_audit.py` passes with zero orphan SQL adapters.

---

### Story 26.5: Real Context — PG18 Ontology Relevance (`ProfileSemanticTranslator` & Axioms), Async `SqlHybridRagRepository`, Active Blackboard Snapshots, Server `EvidenceTable`, `assistant_thread_messages` & Token Budget Trimmer

As a Business User (`Thomas`, `Lucas`),
I want the assistant to reason over my workspace's real PG18 ontology (relevant concepts, axioms, profile-adapted terms), real indexed workspace sources (hybrid PG18 RAG), and active Blackboard snapshots within a controlled token budget,
So that responses are grounded in verifiable organizational truth rather than test seeds or the first eight arbitrary concepts.

**Lot:** 4 — Real Context. **Dependencies:** `26.4b`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-12`, `H-13`, `H-18` (server history & budget), `R6` prompt-assembly latency measurement.
**CAPs covered:** `CAP-022`, `CAP-190`.
**Impacted files:** `AssistantPromptBuilder` (from `26.2`), `packages/orcia-core/src/orcia_core/ontology/`, `packages/orcia-core/src/orcia_core/rag/`, `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`, `_core_providers.py`, `apps/api/src/orcia_api/routers/_assistant_workspace_context.py` (or successor), `infra/migrations/versions/` (`assistant_thread_messages`, `D4`).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-5-real-context-ontology-hybrid-rag-blackboard-and-context-budget-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a workspace whose PG18 ontology defines L1–L4 concepts and axioms
**When** prompt Layer 2 is assembled
**Then** it queries `OntologyGovernanceService.resolve_snapshot(workspace_scope_id=…)`, ranks concepts by lexical (+ vector when embedding is active) relevance to the query, applies `ProfileSemanticTranslator` for `active_hat`, injects applicable axioms, removes `list(concepts)[:8]` on an empty bundle, and passes a golden ontology eval (`0 $`).

**Given** a workspace with indexed sources (with an active `embedding` model, **or without** one per `25-5`)
**When** federated context (`N3`/`N4`) is built
**Then** async `SqlHybridRagRepository.search_hybrid_rrf` feeds the assistant pipeline when an embedding model is active, and cleanly skips vector retrieval without error when none exists (`get_optional_embedding_port`); `build_seeded_rag_service()` is disconnected from production; a real SQL provider supplies active Blackboard snapshots (replacing `lambda _ws: ()`); and a server `EvidenceTable` (filtered by `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED`, sorted by authority and freshness, `[STALE_WARNING]`) feeds Layer 4.

**Given** a long conversation thread and a model with known context window and `max_tokens_budget`
**When** multi-turn messages are built and assembly latency is measured
**Then** Alembic migration adds `assistant_thread_messages` (`UUIDv7` PK, `thread_id` FK `ON DELETE CASCADE`, `turn_id`, `role CHECK IN ('user', 'assistant')`, `content`, `citation_map JSONB`, `token_count`, `created_at`, index `(thread_id, created_at)`); history is loaded from PG18 (eliminating `" | "` splitting of `thread_summary`) and trimmed within `max_tokens_budget`; and `perf_counter()` records SQL prompt-assembly latency (`R6` baseline for `ACTION_ITEM-26.3`).

---

### Story 26.6a: `LlmStreamingPort` Native Tool Calls on 2 Dialects (OpenAI-Compatible & Anthropic), `supports_tools` Flag & Loop Budgets

As an Agentic Loop Developer,
I want the streaming port to parse and re-inject native `tool_calls` cleanly across OpenAI-compatible and Anthropic dialects, persist each model's `supports_tools` capability, and enforce iteration, token, and wall-clock budgets,
So that tool execution builds on a deterministic, bounded transport without breaking native Gemini text streaming.

**Lot:** 5 — Tool Loop. **Dependencies:** `26.5`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-03` (transport), `H-04`, `H-27` (dialects).
**CAPs covered:** `CAP-074`, `CAP-076`, `CAP-190` (`supports_tools` discovery).
**Impacted files:** `LlmStreamingPort` & adapters (from `26.2`), AI Hub (`packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_*.py`, `apps/api/src/orcia_api/routers/ai_models_hub.py`), `packages/orcia-core/src/orcia_core/testing/` (cassettes), `infra/migrations/versions/` (`supports_tools` column).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-6a-llm-streaming-port-tool-calls-and-loop-budgets-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** recorded streamed and non-streamed payloads for **OpenAI-compatible** (`delta.tool_calls`, covering OpenAI, vLLM, Ollama `/v1`, Azure) and **Anthropic** (`tool_use` / `input_json_delta`), per `R7`
**When** processed by `LlmStreamingPort` adapters
**Then** the port emits typed `ContentDelta | ReasoningDelta | ToolCallDelta | Usage | Finish` events, reassembles arguments by `id`/index, stops on `finish_reason=tool_calls` / `stop_reason=tool_use`, formats tool results cleanly (`role: "tool"` / `tool_result`), preserves `tools` on OpenAI 404 fallback, and preserves `reasoning`/`content` separation (with all 3 text streaming adapters including native Gemini `CAP-076` intact).

**Given** a model configured in the AI Models Hub
**When** 0-token discovery or connection testing runs
**Then** `supports_tools` is persisted in PG18 with manual `PLATFORM_ADMIN` override; native Gemini REST and non-`/v1` native Ollama endpoints default to `supports_tools=false` (`ACTION_ITEM-26.4`); `supports_tools=false` models never receive `tools` (zero XML/ReAct prompt emulation), expose Speed 2/3 as unavailable, and return `HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED` (RFC 9457) if Speed 2/3 is requested via API (`D5`).

**Given** a multi-step tool loop hitting profile budgets (iterations, tokens, wall-clock duration)
**When** any limit is reached
**Then** execution terminates cleanly with forced synthesis or explicit `stream_error` (`TurnBudgetExceededError`, RFC 9457), and extended `DeterministicCassetteLLM` cassettes validate both tool-calling dialects at `>= 90%` unit coverage.

---

### Story 26.6b: Governed Assistant Tool Router — Dynamic PG18/RBAC/MCP Catalog, `PermissionBroker` → Lock V5 / Human Anchor → Sandboxed Executor → `audit_ledger` & Outbox, Idempotency & Anti-Injection

As a SecOps Lead (`Sophie`) and Tool-Enabled User,
I want every assistant tool derived from an authorized workspace catalog and routed sequentially through Permission Broker, Lock V5, deterministic human-anchor guards, timeout-capped sandboxed execution, secret scrubbing, and `audit_ledger`,
So that Speed 2/3 can investigate reliably (surgical reads, RAG, ontology, skills, read-only connectors) without ever writing directly to enterprise systems or drafting human-anchored deliverables.

**Lot:** 5 — Tool Loop. **Dependencies:** `26.6a`. **Agent:** 2 distinct `bmad-dev-worker` (`flash`: Impl + Independent Verification) + `bmad-architect-worker` (`pro` review, `R9`).
**Findings covered:** `H-03` (execution), `H-22` (per-tool ledger), `H-27` (catalog), `H-28`, `H-29`.
**CAPs covered:** `CAP-160`, `CAP-022`; new **`CAP-260`** ("Governed Tool Loop for Mon Assistant") created in `verification: api` (`D9`).
**Impacted files:** `packages/orcia-core/src/orcia_core/ports/` (`AssistantToolExecutorPort`), `packages/orcia-core/src/orcia_core/agents/` (`GovernedAssistantToolRouter`, `ASSISTANT` profile), `packages/orcia-core/src/orcia_core/permissions/broker.py`, `orchestration/assistant_citations_and_v5_guard.py`, `orchestration/human_anchors_and_arbitration.py`, `orchestration/agents_and_skills_manager.py`, `packages/orcia-connectors/src/orcia_connectors/surgical.py`, `reflexive_write_gate.py`, `docs/product/capabilities.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-6b-governed-assistant-tool-router-broker-v5-anchors-and-audit-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a user in a workspace
**When** the turn's tool catalog is built
**Then** it includes only authorized tools: the 4 `SurgicalContextExplorer` primitives (`#Lstart-end`), `kb.search` (when RAG is active), ontology lookup, PG18 `enabled_in_workspace` skills with real `input_parameters`, and MCP-exposed tools filtered by `mcp_tool_permissions` + RBAC; the hardcoded single tool and 10-item RAM skill cap are removed.

**Given** any LLM-requested tool call
**When** handled by `GovernedAssistantToolRouter`
**Then** it enforces: `PermissionBrokerService` (`passthrough`, `READ_SOURCE`) → Lock V5 & deterministic per-tool anchor guard (SI write or `human_authored_required=true` → rejected or surfaced as `approval_required` → `CONTINUE_IN_PROCESS`, with `HumanArbitrationRequested` written to `domain_events_outbox`) → executor (Tier 1/2 sandbox for skills) under `asyncio.wait_for` → `scrub_connector_secrets` → `audit_ledger` `ASSISTANT_TOOL_INVOKED` / `ASSISTANT_TOOL_DENIED` (masked args, verdict, latency, cost), emitting `tool_call`, `tool_result`, and `approval_required` SSE events.

**Given** a replayed call (`idem:{turn_id}:{iteration}:{tool_call_id}`), injected prompt directives inside tool output, or attempt to bind `ConnectorReflexiveWriteGateAdapter`
**When** processed
**Then** duplicate calls execute once; tool outputs are wrapped in delimited untrusted blocks that cannot alter Layer 1 or guards (verified by `assistant_tool_output_injection.jsonl` golden eval); `ASSISTANT` profile tests prove `ConnectorReflexiveWriteGateAdapter` is unreachable; lexical `HUMAN_ANCHOR_WRITE_REFUSAL` heuristic is replaced by deterministic tool-level gating; and `CAP-260` is added to `capabilities.yaml` (`verification: api`).

---

### Story 26.7: Unified Turn Engine Convergence (`AssistantTurnEngine`), Atomic Direct UI & E2E Cutover Without Facade (`R4`), Server Citations (`citation_map`) & Deletion of Legacy Routes

As a User of "Mon Assistant",
I want every message to trigger a single, end-to-end governed turn execution with server-verified citations and direct UI cutover (zero parallel double execution, zero strangler facade),
So that displayed answers reflect ORCIA's actual guarantees without double LLM spend or legacy surface duplication.

**Lot:** 6 — Convergence. **Dependencies:** `26.6b`. **Agent:** 2 distinct `bmad-dev-worker` (`flash`: Impl + Independent Verification) + mandatory `bmad-architect-worker` (`pro` review, `R9`).
**Findings covered:** `H-01`, `H-02`, `H-09` (`_saved_drafts` deleted), `H-14` (server).
**CAPs covered:** `CAP-022`, `CAP-071`, `CAP-072`, `CAP-160`, `CAP-260`.
**Impacted files:** `packages/orcia-core/src/orcia_core/orchestration/` (`AssistantTurnEngine`, `assistant_three_speed_router.py`, `assistant_agent.py`, `assistant_citations_and_v5_guard.py`), `packages/orcia-core/src/orcia_core/agents/reflexive_runtime.py`, `apps/api/src/orcia_api/routers/assistant_turns.py` (new), `assistant_workspace.py`, `assistant_workspace_citations.py`, `assistant.py`, `mcp_and_test_bench.py` / `governed_mcp_exposure.py` (`assistant.ask`), `apps/api/src/orcia_api/schemas/assistant_turns.py`, `packages/api-client/`, `infra/migrations/versions/` (`reflexive_execution_sessions.execution_profile`), `apps/web/src/features/inbox/` (`useInboxPanelController.ts`, `useAssistantStreamingTurn.ts`, `assistantBackgroundStreamStore.ts`, `inboxTurnSyncHelpers.ts`), `apps/web/e2e/` (`02`, `12`, `16`, `21`).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-7-unified-turn-engine-convergence-direct-cutover-and-citations-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a Speed 1, Speed 2, or Speed 3 turn submitted via `POST /api/v1/assistant/turns`
**When** executed by `AssistantTurnEngine` inside `apps/api` (`R1`)
**Then** Speed 1 takes the single-shot fast-path (`TTFT p95 < 1.2 s` and prompt-assembly p95 `< 50 ms` verified in real PG18 Layer 2 without a prompt cache per `R6`, post-first-byte persistence, `turn_completed.low_evidence` set deterministically on empty `EvidenceTable`, `parent_turn_id` supported for linked Speed 2 "Deepen" turns per `R3`), Speed 2/3 run on `NonDeterministicReflexiveRuntime` with `execution_profile = 'ASSISTANT'` (fixed `N1–N5` phases, `PROCESS` default unchanged and `16-2` / `process_dispatcher` green), and exactly one LLM execution path triggers per user turn (ending parallel `three-speed` + `reflexive` calls).

**Given** a synthesizing response and MCP `assistant.ask`
**When** the response completes
**Then** `AssistantCitationAndV5GuardService.verify_and_sanitize_citations` runs server-side **before** `turn_completed` against the server `EvidenceTable`, strips and logs ungrounded `[Sn]`/`[Gn]`/`[On]` tags to `audit_ledger` (`ASSISTANT_PHANTOM_CITATION_PURGED`), and emits `citation_map` SSE; golden evals prove `0` phantom citations on the live path; and `assistant.ask` (`POST /mcp/spaces/{ws}/invoke`, `D7`) executes synchronously via `AssistantTurnEngine` Speed 1 read-only under all 7 MCP locks + `QuotaGuard` + `ScopeAccessGuard` + `CitationGuard`.

**Given** `apps/web` is the sole turn API consumer (`R4`)
**When** direct cutover completes in one atomic commit
**Then** `apps/web` turn transport (`POST /assistant/turns`, `GET …/stream?after=<cursor>`, `GET /assistant/turns/active`, `POST /assistant/turns/{id}/{stop,feedback}`) and Playwright specs `02`, `12`, `16`, `21` migrate directly to the canonical v2 routes (`ACTION_ITEM-26.2` tracks any future facade); legacy routes `/three-speed/*` (`stream`, `turn`, `active-turn`, `stop`, `feedback`, `invalidate-cache`), `/chat`, `/chat/stream`, `/citations/verify-turn`, and `/artifacts/action` — together with `_saved_drafts` and `execute_artifact_card_action` (`R5`) — are **deleted** with their schemas, tests, and OpenAPI SDK entries (`0-diff`).

---

### Story 26.8: `CONTINUE_IN_PROCESS` Wired to Durable DBOS + PG18 & Human Anchors (`WAITING_FOR_HUMAN_ANCHOR`), Direct Deletion of `/workflows/save-and-launch`

As a Human-Led Contributor,
I want assistant proposals requiring SI writes or human-authored deliverables to launch durable DBOS + PG18 processes that pause at human anchors and Gates,
So that the assistant can never bypass `AD-2` / `AD-3` / V5 and conversation-to-process continuity is fully auditable.

**Lot:** 6 — Convergence. **Dependencies:** `26.7`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-05`.
**CAPs covered:** `CAP-022`, `CAP-160`, `CAP-260`.
**Impacted files:** `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py` (`save_and_launch_workflow`), `engine.py`, `human_anchors_and_arbitration.py`, `orchestration_sql_wiring.py`, `apps/api/src/orcia_api/routers/assistant.py`, `assistant_turns.py`, `assistant_workspace_folders.py`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-8-continue-in-process-dbos-pg18-and-human-anchors-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an `approval_required` turn proposal approved via `POST /api/v1/assistant/turns/{id}/approve` or a process launched via `POST /api/v1/assistant/folders/{id}/launch-process` containing a `human_authored_required: true` step
**When** launched
**Then** execution runs on durable DBOS + PG18 (`workflow_runs`, `step_executions`, `blackboard_snapshots`, `domain_events_outbox` verified by SQL `SELECT`), initializes anchored steps in `WAITING_FOR_HUMAN_ANCHOR`, halts at the first `WAITING_*` state, and rejects unsigned commits with `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`.

**Given** legacy `POST /api/v1/assistant/workflows/save-and-launch` (`D6`, `R4`)
**When** the story completes
**Then** the route and its in-memory `WorkflowEngineService` execution path are **deleted directly** with SDK entries (`0-diff`, zero `deprecated` window), and real Composition Root PG18 integration tests verify turn → approval → human-anchor pause → resume after signature.

---

### Story 26.9: UI & SDK Wiring — Mode A Governance API, `citation_map` Pills, PG18 Thread History, Tool Trace, Approval Cards, "Deepen" Button & F5 Cold Survival

As a User of "Mon Assistant",
I want the workspace screen to rely exclusively on the unified backend APIs for Mode A governance, server citations, PG18 thread history, tool traces, approval cards, and one-click "Deepen", without local business state,
So that what I see matches persisted server truth and survives hard refreshes.

**Lot:** 7 — UI & Closure. **Dependencies:** `26.7`, `26.8`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-14` (UI), `H-18` (UI), `H-26`.
**CAPs covered:** `CAP-070`, `CAP-071`, `CAP-072`, `CAP-073`, `CAP-260`.
**Impacted files:** `apps/web/src/features/inbox/` (`useInboxPanelController.ts`, `useAssistantStreamingTurn.ts`, `assistantBackgroundStreamStore.ts`, `assistantTurnPayloadHelper.ts`, `assistantAutocompleteHelpers.ts`, `inboxCitationHelpers.ts`, `InboxAuxiliaryPanels.tsx`, `index.tsx`), `packages/ui/src/` (`AssistantToolCallTrace`, `AssistantApprovalRequiredCard`, Deepen button, `supports_tools=false` notice), `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/api/src/orcia_api/routers/assistant_workspace_folders.py`, `packages/api-client/`, `apps/web/e2e/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-9-ui-and-sdk-wiring-mode-a-citations-history-and-deepen-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a user on `/assistant`
**When** sending turns, refreshing (F5), and navigating threads
**Then** history and `thread_id` rehydrate from `GET /api/v1/assistant/threads/{id}/messages` in PG18 (`0` `localStorage` history sent in payloads), duplicate route `POST /threads/{id}/turns` is **deleted** (`R4`, `0-diff` SDK), `AssistantToolCallTrace` renders jargon-free tool activity, and after a Speed 1 turn UI renders a localized **"Deepen"** button (visible when `supports_tools=true`, emphasized when `low_evidence`, `R3`) creating a linked Speed 2 turn (`parent_turn_id`) verified by `RouterProvider` Vitest tests and Playwright `22-assistant-tool-loop-approval-and-reattach.spec.ts` (`reloadColdFromPg`).

**Given** citations, approval proposals, or a model with `supports_tools=false`
**When** rendered
**Then** citation pills come exclusively from server `citation_map` (deleting `filterUsedRagSourcesForTurn` and client-fabricated `[Sn]`/`REFERENCE`/`FRESH` logic), `AssistantApprovalRequiredCard` routes to Process Gates, Speed 2/3 controls disable cleanly with localized microcopy, all strings live in `i18n/locales/{fr,en}.ts` (French default), and zero-dead-buttons + `data-testid` sync audits pass.

**Given** Mode A governance controls and `launch-process`
**When** modified by the user
**Then** reads/writes use `@orcia/api-client` (PG18 Mode A endpoints, `POST /folders/{id}/launch-process`, `assembledLayers` populated from server, zero business `localStorage`), **no Mode B Studio UI** is shipped (`R2`, `ACTION_ITEM-26.1`, studio trigger removed without leaving dead buttons), and cold-PG18 F5 survival holds end-to-end.

---

### Story 26.10: Golden Evals, Red-Team & Multi-Worker Verification, Anti-Regression AST Audits, 0-Uncalled Route Check, `runtime` Promotion & Epic 26 Closure

As a Tech Lead and QA Lead,
I want to lock all Epic 26 guarantees with golden evals, security/red-team tests, multi-worker Redis integration tests, AST audits, and honest capability promotion after E2E proof,
So that harness debt cannot regress and Epic 26 closes cleanly across all `AD-17` verification layers.

**Lot:** 7 — UI & Closure. **Dependencies:** `26.9`. **Agent:** 1 `bmad-dev-worker` (`flash`) + mandatory final `bmad-architect-worker` (`pro`) closure gate (`R9`).
**Findings covered:** `H-36`, `H-37`.
**CAPs covered:** `CAP-022`, `CAP-069`..`CAP-076`, `CAP-160`, `CAP-190`, `CAP-260`.
**Impacted files:** `tests/evals/golden/` (`assistant_tool_loop.jsonl`, `assistant_anchor_and_v5.jsonl`, `assistant_tool_output_injection.jsonl`), `tests/security/`, `tests/integration/`, `tests/unit/` (AST audits), `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-10-golden-evals-red-team-multi-worker-and-epic-26-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Stories `26.0`–`26.9` implemented
**When** the full verification suite runs
**Then** golden evals (`assistant_tool_loop.jsonl`, `assistant_anchor_and_v5.jsonl`, `assistant_tool_output_injection.jsonl`, `0` phantom citations) pass at `0 $` via `DeterministicCassetteLLM`; security tests verify cross-workspace IDOR (`UUID` + slug), pre-stream `403` Observer, `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` + DNS-rebinding SSRF, Day-0 `platform-setup-state` non-leak, and `CONFIDENTIAL_RESTRICTED` masking; 2-instance API + Redis integration tests verify cross-worker `stop`, cursor reattachment, and `ERR_ASSISTANT_TURN_INTERRUPTED` crash detection (`R1`); and new AST audits forbid module-level mutable state, unguarded `/assistant/*` mutation routes, and `testclient` branches in `src/`.

**Given** route deletions across `26.4b`–`26.9` and open legacy items (`H-36`, `H-37`)
**When** closure audits execute
**Then** an endpoint inventory audit confirms `0` assistant route without an active UI or documented MCP caller (`0` legacy `deprecated` routes), `require_rag_available` and `dependency_overrides` are absent from assistant tests, `BUG-E2E-01b` and `AUTH-01` are closed (or explicit remaining scope is tracked cleanly), and the `2026-11-21` audit report Section 3 records final status for `H-01..H-38`.

**Given** Stories `26.0`–`26.9` are `done` and Playwright `02`, `12`, `16`, `21`, `22` pass on the real unified engine
**When** Epic 26 closes
**Then** `CAP-022`, `CAP-070`, `CAP-072`, and `CAP-260` promote to `verification: runtime` in `docs/product/capabilities.yaml`, all DoD exit metrics hold (`1` LLM path/turn, `1` prompt builder, `0` business RAM state, `0` harness file `> 300 L`, `>= 90%` unit coverage), `ruff`, `mypy --strict`, `lint-imports` (`5/5`), `pytest --cov-fail-under=90`, `pnpm turbo run lint typecheck test`, `lint_spine.py` (`0 findings`), and `pnpm site:sync && pnpm site:check` pass, and `epic-26` becomes `done`.

---

## Epic 27: English-Only Development & Documentation Governance, 100% Bilingual FR/EN Web Application & Deterministic i18n Controls (`AD-17`, `AD-19`, RFC 9457)

Enforce **English** as the mandatory language for all development communications, documentation, Tech Lead reports, commit messages, and code comments/docstrings while preserving and guaranteeing **100% French (`fr`) and English (`en`) bilingual compatibility** across the web application (`apps/web` + `@orcia/ui`) and user-facing backend APIs (`Accept-Language` RFC 9457 error catalogs and Assistant prompt bundles).

This Epic fully executes [`ACTION_ITEM-I18N.1`](../implementation-artifacts/sprint-status.yaml) based on the [`2026-11-20` i18n audit report](../implementation-artifacts/tech-lead-reports/2026-11-20-audit-i18n-chaines-codees-en-dur-tech-lead-report.md) (`3,809` raw heuristic hits across `461` files: `A=71`, `B=577`, `C=2,816`, `D=193`, `E=152`) and the active decisions [`epic-27-decisions-grill-2026-11-23.md`](../implementation-artifacts/epic-27-decisions-grill-2026-11-23.md) (`D1–D4`).

**Execution order across 6 lots (8 stories):**
- **Lot 0 — Deterministic Guardrails & Foundation:** `27.1` (`bmad-dev-worker` `flash`)
- **Lot 1 — Category A Client Errors:** `27.2` (`bmad-dev-worker` `flash`, depends on `27.1`)
- **Lot 2 — Category C `apps/web` Shell, Routes & Features:** `27.3` (`flash`) → `27.4` (`flash`, depends on `27.1`)
- **Lot 3 — Category C Studio/VSM & `@orcia/ui` Design System:** `27.5` (`flash`, depends on `27.3`, `27.4`) → `27.6` (`flash`, depends on `27.5`)
- **Lot 4 — Categories B & D Backend RFC 9457, Prompts & Seeds:** `27.7` (`flash`, depends on `27.1`)
- **Lot 5 — Zero-Baseline Lock & Bilingual E2E Closure:** `27.8` (`flash` + mandatory `bmad-architect-worker` `pro` final gate, depends on `27.2`, `27.5`, `27.6`, `27.7`)

Every modified or created source file must stay `<= 300` lines, preserve `AD-19` modular monolith boundaries (`lint-imports`), keep `0-diff` OpenAPI 3.1 SDK compliance, use English-only code comments/docstrings, and maintain strictly decreasing deterministic ratchet baselines down to **`0`** in Story `27.8`.

---

### Story 27.1: Deterministic i18n CI Guardrails (Gates 1–4) & Shared Client Error Code Resolution Foundation (`ClientErrorCode` + `resolveClientErrorMessage`)

As a Platform Tech Lead and Release Gatekeeper,
I want four deterministic AST/dictionary/contract CI gates installed alongside a shared `ClientErrorCode` + `resolveClientErrorMessage` helper in the frontend,
So that no new hardcoded FR/EN strings, locale ternaries, missing dictionary keys, client error prose, non-localized backend error codes, or non-English code comments can enter the codebase while legacy occurrences ratchet down cleanly to zero.

**Lot:** 0 — Deterministic Guardrails & Foundation. **Dependencies:** None (Epic 27 branch initialized). **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 2 guardrail + Lot 1 shared helper), `D3` (Gates 1–4).
**CAPs covered:** `CAP-100` (`hygiene` — CI guardrails & shared i18n resolution foundation).
**Impacted files:** `apps/web/src/lib/clientErrorCodes.ts` (new), `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts` (new), `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json` (new), `apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts` (new), `apps/web/src/__tests__/client-error-code-contract-audit.test.ts` (new), `apps/web/src/__tests__/client-error-code-resolution.test.ts` (new), `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` (new), `tests/unit/i18n_backend_audit_baseline.json` (new).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-1-deterministic-i18n-ci-guardrails-and-client-error-code-foundation-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** TypeScript/React sources in `apps/web/src/` and `packages/ui/src/` (excluding `apps/web/src/i18n/locales/`, `generated/`, and `__tests__/`)
**When** Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`) executes via `pnpm turbo run test`
**Then** the TypeScript Compiler AST visitor detects every inline locale ternary (`locale === "fr" ? ... : ...`, `isFr ? ... : ...`) and raw user-facing JSX text or UI attribute (`title`, `placeholder`, `aria-label`, `alt`, `label`, `description`, `emptyMessage`, `helperText`, etc.), fails immediately on any file exceeding its recorded entry in `i18n-hardcoded-locale-baseline.json` (ratchet), and allows explicit benign technical markers only when annotated as non-user-facing.

**Given** all `fr` and `en` dictionary files under `apps/web/src/i18n/locales/`
**When** Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`) and Gate 3 (`client-error-code-contract-audit.test.ts`) run
**Then** Gate 2 fails on any missing nested key between FR and EN, any mismatched `{param}` interpolation placeholder, any empty translation value, or any UX Rule 3.1 forbidden internal jargon token; Gate 3 verifies `ClientErrorCode` + `resolveClientErrorMessage(code, labels, params)` resolves `ERR_CLIENT_TIMEOUT`, `ERR_CLIENT_NETWORK`, `ERR_CLIENT_ABORTED`, `ERR_CLIENT_SSE_DISCONNECTED`, `ERR_CLIENT_INVALID_PAYLOAD`, and `ERR_CLIENT_UNKNOWN` cleanly in both `fr` and `en` (falling back safely on unknown codes with parameterized duration/details) and enforces a strictly bounded ratchet baseline across `*ApiBridge.ts`, `packages/api-client/src/`, `formatRfc9457ErrorToBanner.ts`, stores, and controllers.

**Given** Python modules across `packages/orcia-core`, `apps/api`, and `apps/worker`
**When** Gate 4 (`test_i18n_backend_catalog_and_english_dev_audit.py`) executes via `.venv/bin/pytest tests/unit`
**Then** it asserts every `OrciaDomainError` / registered RFC 9457 `error_code` provides non-empty `fr` and `en` localized templates resolved via `Accept-Language`, flags any hardcoded single-language LLM prompt directive outside `PROMPT_LOCALES`, enforces an English-only comment/docstring check on newly added or modified Python/TypeScript lines relative to `main` (while recording legacy ratchet counts in `i18n_backend_audit_baseline.json`), and all unit/Turbo gates pass at `>= 90%` branch coverage on new code.

---

### Story 27.2: Category A Remediation (`71` Hits / `26` Files) — Migrate All Client API Bridges, SSE Stores, Controllers & `formatRfc9457ErrorToBanner` to `ClientErrorCode`

As a French or English ORCIA User,
I want every client-side timeout, network disconnect, stream interruption, and RFC 9457 banner fallback to come from structured `ClientErrorCode` keys resolved in my active language,
So that no hardcoded French/English error string or hardcoded `"16 s"` delay ever leaks into error banners or notifications.

**Lot:** 1 — Category A Client Errors. **Dependencies:** `27.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 1 — Category A `71` hits / `26` files).
**CAPs covered:** `CAP-001`..`CAP-260` (cross-cutting client error localization).
**Impacted files:** `apps/web/src/lib/formatRfc9457ErrorToBanner.ts`, `packages/api-client/src/helpers.ts`, `packages/api-client/src/sseAndQueryHelpers.ts`, `packages/api-client/src/domains/workflowsV2.ts`, `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx`, `apps/web/src/features/inbox/assistantBackgroundStreamStore.ts`, `apps/web/src/features/inbox/useAssistantStreamingTurn.ts`, `apps/web/src/components/useSidebarAccountSettings.ts`, `apps/web/src/components/platformSetup{Workspaces,Store,Hydration}.ts*`, `apps/web/src/components/ShellFederatedSearchModal.tsx`, `apps/web/src/routes/settingsAiModelsPresets.ts`, `apps/web/src/routes/useAiModelsSectionController.ts`, `apps/web/src/routes/wizards.tsx`, `apps/web/src/routes/activityApiBridge.ts`, `apps/web/src/features/admin/{ai-models/aiModelsApiBridge.ts,connectors/useEnterpriseConnectorsController.ts,iam/iamApiBridge.ts,organization/orgUnitsApiBridge.ts}`, `apps/web/src/features/processes/{ProcessStudioAndPackAuthoringSection.tsx,execution/useInteractiveProcessRunController.ts}`, `apps/web/src/features/settings/packs/usePacksRegistryHealthchecks.ts`, `apps/web/src/features/inbox/usePermissionBrokerTickets.ts`, `apps/web/src/stores/authSessionStore.ts`, `packages/ui/src/primitives/UserPasswordChangeCard.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-2-category-a-client-error-codes-bridges-stores-and-rfc9457-banner-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** all `26` files identified in Category A of `_i18n-audit-inventory-raw.md` (including `formatRfc9457ErrorToBanner.ts`, `*ApiBridge.ts`, `packages/api-client`, stores, and controllers)
**When** refactored to emit structured `ClientErrorCode` values (`ERR_CLIENT_*`) with typed parameters (such as timeout duration in seconds)
**Then** zero inline `locale === "fr" ? ... : ...` error ternaries or raw French/English fallback sentences remain in any API bridge, `packages/api-client` helper, SSE runner, store, or `formatRfc9457ErrorToBanner.ts`, all `UserPasswordChangeCard` error fallbacks are passed via typed props from `apps/web` dictionaries, and Gate 3 (`client-error-code-contract-audit.test.ts`) baseline reaches **`0`**.

**Given** an API request timeout, network offline error, SSE disconnect, or unknown HTTP `5xx` error without a localized `problem.detail`
**When** rendered in `fr` and `en` in Vitest under `<RouterProvider>` (`apps/web/src/__tests__/`)
**Then** `[role="alert"]` displays the exact localized copy from `apps/web/src/i18n/locales/{fr,en}.ts` (preserving UX Rule 3.1 zero-jargon and HTTP `>= 400` visibility) and all touched files remain `<= 300` lines with English-only comments/docstrings.

---

### Story 27.3: Category C Remediation (Part 1) — `apps/web` Shell, Contextual Help, Notifications, Routes & Bootstrap Wizards

As a French or English ORCIA User,
I want the shell navigation, breadcrumbs, scope selector, federated search, contextual help panels, notifications, activity formatters, and bootstrap wizards to resolve 100% of their labels from typed `fr`/`en` dictionaries,
So that switching between French and English updates every navigation chrome, help article wrapper, notification, and onboarding step cleanly.

**Lot:** 2 — Category C Core Web (`apps/web`). **Dependencies:** `27.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 3 — Category C `apps/web` shell, help, routes, wizards).
**CAPs covered:** `CAP-004`, `CAP-058`, `CAP-060`, `CAP-065`, `CAP-066`, `CAP-068`, `CAP-100`.
**Impacted files:** `apps/web/src/components/_contextualHelpSections.ts`, `apps/web/src/components/_contextualHelpSectionsEn.ts`, `apps/web/src/components/contextualHelpCatalog.ts`, `apps/web/src/components/shellNotificationBuilder.ts`, `apps/web/src/components/shellScopeOptions.ts`, `apps/web/src/components/shellBreadcrumbBuilders.ts`, `apps/web/src/components/CreateProcessFormDialog.tsx`, `apps/web/src/components/Shell*.tsx`, `apps/web/src/components/platformSetup*.ts*`, `apps/web/src/routes/activityFormatters.ts`, `apps/web/src/routes/*.tsx`, `apps/web/src/features/bootstrap/WizardsStepForm.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts` (modular sub-dictionaries `<= 300` L), `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-3-category-c-shell-contextual-help-notifications-routes-and-wizards-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the shell, contextual help (`_contextualHelpSections*.ts`, `contextualHelpCatalog.ts`), notifications (`shellNotificationBuilder.ts`), breadcrumbs, scope selector, route components, `activityFormatters.ts`, and `WizardsStepForm.tsx`
**When** migrated to modular typed sub-dictionaries under `apps/web/src/i18n/locales/`
**Then** zero inline `locale === "fr"` / `isFr ? ... : ...` expressions or raw hardcoded JSX text strings remain in `apps/web/src/components/`, `apps/web/src/routes/`, or `apps/web/src/features/bootstrap/`, `_contextualHelpSections*.ts` are unified into typed `fr`/`en` dictionary modules, all touched files stay `<= 300` lines, and Gate 1 + Gate 2 pass with a strictly reduced baseline.

**Given** shell chrome, notifications, activity feed entries, and wizards rendered in both `fr` and `en`
**When** exercised in Vitest (`i18n-and-shell.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`)
**Then** zero French strings leak in `en` mode, zero English strings leak in `fr` mode, all existing `data-testid` hooks stay intact (`e2e-testids-sync-audit.test.ts` passes), and zero UX Rule 3.1 jargon appears.

---

### Story 27.4: Category C Remediation (Part 2) — `apps/web` Cockpit, Inbox/Assistant, Workspaces, Gates, Catalog & Admin Features

As a French or English ORCIA User,
I want every label, tooltip, badge, modal, and empty state across Cockpit, Mon Assistant, Mes Espaces, Gates, Catalog, Agents, and Administration screens to live in typed `fr`/`en` dictionaries,
So that all primary business workspaces are genuinely bilingual without inline conditionals.

**Lot:** 2 — Category C Core Web (`apps/web`). **Dependencies:** `27.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 3 — Category C `apps/web` feature modules).
**CAPs covered:** `CAP-001`..`CAP-091`, `CAP-180`, `CAP-190`, `CAP-200`..`CAP-260`.
**Impacted files:** `apps/web/src/features/cockpit/*`, `apps/web/src/features/inbox/*`, `apps/web/src/features/workspaces/*`, `apps/web/src/features/gates/*`, `apps/web/src/features/catalog/*`, `apps/web/src/features/admin/*`, `apps/web/src/features/settings/*`, `apps/web/src/features/shared/*`, `apps/web/src/i18n/locales/*`, `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-4-category-c-cockpit-assistant-workspaces-gates-catalog-and-admin-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** all modules in `apps/web/src/features/{cockpit,inbox,workspaces,gates,catalog,admin,settings,shared}/`
**When** audited by Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`) and Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`)
**Then** zero hardcoded user-facing strings or inline `locale === "fr"` ternaries remain in those feature directories, all new keys are symmetrically populated in `fr` and `en` dictionary files (`<= 300` lines each), no UX Rule 3.1 jargon is introduced, and `i18n-hardcoded-locale-baseline.json` drops strictly for every remediated file.

**Given** Vitest feature suites and `zero-dead-buttons-and-silent-catches-audit.test.tsx`
**When** executed via `pnpm turbo run lint typecheck test`
**Then** all feature views render cleanly in both `fr` and `en`, F5 survival and `data-testid` sync audits pass (`0` regressions), and all touched files comply with the English comment/docstring policy.

---

### Story 27.5: Category C Remediation (Part 3) — Process Studio v2, VSM, Execution Panels & Bilingual Catalog Data Modules (`apps/web` Gate 1 Baseline = 0)

As a French or English Process Designer or Contributor,
I want Process Studio v2, the Value Stream Map, interactive execution/HITL panels, and reference process catalog data (`processStudioV2Data.ts` — 434 raw hits) to resolve all user-facing strings from typed bilingual dictionaries,
So that `apps/web/src/` reaches zero hardcoded locale violations (`baseline = 0`).

**Lot:** 3 — Category C Studio/VSM & `@orcia/ui`. **Dependencies:** `27.3`, `27.4`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 3 — `processStudioV2Data.ts`, `StepDetailSheet.tsx`, `studioCatalogLabels.ts`, `InteractiveRunDeliverableAndHitlPanels.tsx`, etc.).
**CAPs covered:** `CAP-020`..`CAP-036`, `CAP-140`, `CAP-160`.
**Impacted files:** `apps/web/src/features/processes/processStudioV2Data.ts` (split into `<= 300` L modules), `apps/web/src/features/processes/vsm/StepDetailSheet.tsx`, `apps/web/src/features/processes/vsm/ValueStreamMapView.tsx`, `apps/web/src/features/processes/studio/*`, `apps/web/src/features/processes/execution/*`, `apps/web/src/features/processes/{ProcessCatalogCardGrid,ProcessesHubPage,ProcessStudioAndPackAuthoringSection}.tsx`, `apps/web/src/i18n/locales/*`, `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-5-category-c-process-studio-v2-vsm-execution-and-bilingual-catalog-data-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `apps/web/src/features/processes/` (including the `434`-hit `processStudioV2Data.ts` hotspot, `StepDetailSheet.tsx`, `studioCatalogLabels.ts`, `StudioCopilotSidebar.tsx`, and `InteractiveRunDeliverableAndHitlPanels.tsx`)
**When** refactored into localized typed dictionaries and clean `<= 300` line helper/data modules keyed by `fr`/`en`
**Then** Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`) reports **`0` violations across the entire `apps/web/src/` workspace** (`apps/web` baseline slice reduced to `0`).

**Given** Process Studio v2, VSM detail sheets, and interactive execution/HITL panels rendered in `fr` and `en`
**When** validated with `pnpm turbo run lint typecheck test`
**Then** Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`), `e2e-testids-sync-audit.test.ts`, and `zero-dead-buttons-and-silent-catches-audit.test.tsx` pass completely with zero regressions.

---

### Story 27.6: Category C Remediation (Part 4) — `@orcia/ui` Design System Components & Primitives via Typed Label Props (`packages/ui` Gate 1 Baseline = 0)

As a Design System Maintainer (`Sally`),
I want every component and primitive in `packages/ui/src/` to receive 100% of its user-facing labels, placeholders, aria-labels, and showcase copy as typed props (with zero hardcoded French/English defaults or inline `locale` ternaries inside `@orcia/ui`),
So that `@orcia/ui` remains strictly presentation-only, framework-isolated, and 100% bilingual across both `fr` and `en`.

**Lot:** 3 — Category C Studio/VSM & `@orcia/ui`. **Dependencies:** `27.5`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 3 — `OrciaProductShowcaseSiteView.tsx` 178 hits, `iconRegistry.ts` 73 hits, `AgentGovernanceTypesAndDefaults.ts`, `AgentSixBlocks*`, `Assistant*`, `TemporaryPasswordInvitationModal.tsx`, `RemoteServiceTestBenchAndMcpExposureView.tsx`, etc.).
**CAPs covered:** `CAP-060`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-200`, `CAP-260`.
**Impacted files:** `packages/ui/src/primitives/**`, `packages/ui/src/components/**`, `packages/ui/src/shell/**`, `packages/ui/src/__tests__/**`, `apps/web/src/i18n/locales/*`, `apps/web/src/routes/showcase.tsx`, `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-6-category-c-orcia-ui-design-system-primitives-typed-label-props-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** every primitive and component in `packages/ui/src/` (including `OrciaProductShowcaseSiteView.tsx`, `AgentGovernanceTypesAndDefaults.ts`, `AgentSixBlocks*`, `Assistant*`, `RgaaModalGuardLabels.ts`, and `iconRegistry.ts` reviewed for true UI labels vs internal icon IDs)
**When** refactored so all user-visible text is injected via typed label props from `apps/web/src/i18n/locales/{fr,en}.ts` (or typed `labels` props in `packages/ui` tests)
**Then** `packages/ui/src/` contains zero hardcoded user-facing French/English strings or `locale === "fr"` ternaries, `packages/ui` preserves zero imports of `@tanstack/react-router` or `@orcia/api-client`, all modified files stay `<= 300` lines, and Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`) baseline drops to **`0` for both `apps/web/src/` and `packages/ui/src/`**.

**Given** `@orcia/ui` component tests and `apps/web` consumer routes (including `/showcase`)
**When** executed via `pnpm turbo run lint typecheck test`
**Then** all `packages/ui` and `apps/web` Vitest suites pass cleanly in both `fr` and `en`, and zero dead buttons or broken `data-testid` attributes are introduced.

---

### Story 27.7: Categories B & D Remediation (`577` + `193` Hits) — Bilingual RFC 9457 Backend Error Catalogs (`Accept-Language`), Prompt Localization & Seed Display Localization (Gate 4 Baseline = 0)

As a Bilingual User and Backend Maintainer,
I want every backend RFC 9457 error envelope (`Category B`), LLM prompt/governance template, and user-facing seed/payload text (`Category D`) to localize cleanly via `Accept-Language` / `locale` while maintaining English-only code comments and docstrings,
So that backend API responses work seamlessly in French and English without leaking hardcoded single-language strings.

**Lot:** 4 — Categories B & D Backend. **Dependencies:** `27.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 4 — Category B `577` hits & Category D `193` hits).
**CAPs covered:** `CAP-001`..`CAP-260` (cross-cutting backend RFC 9457, prompts, and seed localization).
**Impacted files:** `packages/orcia-core/src/orcia_core/*/errors.py`, `packages/orcia-core/src/orcia_core/permissions/{_error_catalog.py,_auth_error_catalog.py,seeds.py}`, `packages/orcia-core/src/orcia_core/orchestration/{assistant_harness.py,assistant_governance.py,assistant_prompt_locales.py,assistant_three_speed_router.py,ai_models_connection.py,governed_mcp_exposure.py,notifications_and_claims.py,pack_builder_processes.py,remote_test_bench.py,studio_and_packs.py,step_executors.py}`, `packages/orcia-core/src/orcia_core/bootstrap/orchestration_seeds.py`, `packages/orcia-core/src/orcia_core/catalog/{cas_resolver.py,seeds.py}`, `packages/orcia-core/src/orcia_core/agents/llm_adapter.py`, `apps/api/src/orcia_api/routers/*.py`, `apps/api/src/orcia_api/schemas/*.py`, `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`, `tests/unit/i18n_backend_audit_baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-7-categories-b-and-d-bilingual-rfc9457-backend-catalogs-prompts-and-seeds-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** all `OrciaDomainError` subclasses, router error handlers, and `detail_override` paths identified in Category B (`577` raw hits)
**When** audited and migrated to bilingual `fr`/`en` entries in the domain error catalogs resolved via `Accept-Language` (`get_localized_error_text`)
**Then** every `error_code` returns an accurate, jargon-free localized `detail` in both French (`Accept-Language: fr`) and English (`Accept-Language: en`) without hardcoded French-only `detail_override` prose, preserving invariant `error_code` and W3C `trace_id` (`RFC 9457` + `0-diff` OpenAPI).

**Given** backend LLM prompts (`assistant_llm_prompts.py`, `assistant_harness.py`, `assistant_governance.py`, `llm_adapter.py`) and user-facing payload/seed strings (`permissions/seeds.py`, `orchestration_seeds.py`, `catalog/seeds.py`, `rag_seeds.py`) identified in Category D (`193` raw hits)
**When** refactored to resolve display titles/prompts from explicit `fr`/`en` locale bundles or English canonical technical identifiers without breaking deterministic replay/Day-0 reset (`pnpm db:reset`)
**Then** zero hardcoded French-only LLM directives remain outside `PROMPT_LOCALES["fr"]`, seed/default outputs respect the active `locale`, Gate 4 (`test_i18n_backend_catalog_and_english_dev_audit.py`) baseline reaches **`0`**, all touched Python files remain `<= 300` lines with English comments/docstrings, `lint-imports` keeps `5/5` contracts, `export_openapi.py --check` returns `0-diff`, and combined Python unit/PG18 coverage stays `>= 90%`.

---

### Story 27.8: Zero-Baseline Deterministic Lock, Bilingual (`fr` & `en`) Playwright E2E Verification, Showcase Sync & Epic 27 Closure

As a Tech Lead and QA Gatekeeper,
I want all 4 deterministic i18n CI baseline files locked strictly to `0` violations, bilingual (`fr` and `en`) Playwright end-to-end verification passing without `ORCIA_E2E_SEED_FIXTURES`, and all documentation/showcase artifacts synchronized,
So that ORCIA ships permanently bilingual in French and English for end users while enforcing English-only development and documentation governance.

**Lot:** 5 — Zero-Baseline Lock & Bilingual E2E Closure. **Dependencies:** `27.2`, `27.5`, `27.6`, `27.7`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory final `bmad-architect-worker` (`pro`) closure gate.
**Findings covered:** `ACTION_ITEM-I18N.1` (full closure), `D1–D4`.
**CAPs covered:** `CAP-001`..`CAP-260`, `CAP-100`.
**Impacted files:** `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`, `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts`, `apps/web/src/__tests__/client-error-code-contract-audit.test.ts`, `tests/unit/i18n_backend_audit_baseline.json`, `apps/web/e2e/23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` (new), `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/2026-11-20-audit-i18n-chaines-codees-en-dur-tech-lead-report.md`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-8-zero-baseline-lock-bilingual-e2e-verification-and-epic-27-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Stories `27.1`–`27.7` completed
**When** all 4 deterministic CI gates run
**Then** every baseline ratchet file (`i18n-hardcoded-locale-baseline.json`, `client-error-code-contract-audit`, `i18n_backend_audit_baseline.json`) equals **`0`**, zero inline `locale === "fr"` ternaries or hardcoded UI/error strings remain across `apps/web/src`, `packages/ui/src`, `packages/api-client/src`, `apps/api/src`, and `packages/orcia-core`, and Gates 1–4 fail closed on any non-zero violation.

**Given** a live dual-server Playwright E2E stack booted from Day-0 reset (`env -u ORCIA_E2E_SEED_FIXTURES`)
**When** `23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` and the impacted Playwright Desktop E2E specs execute across both **French (`fr`)** and **English (`en`)** user sessions (including account language switching, `F5` cold PG18 persistence, client timeout/error banners, and RFC 9457 API errors)
**Then** all UI views, modals, contextual help panels, Assistant turns, and error banners render cleanly in both `fr` and `en` with zero language leakage, zero jargon, and zero console/API regressions.

**Given** full `AD-17` verification and `bmad-architect-worker` (`pro`) closure review
**When** closing Epic 27
**Then** `ruff check`, `ruff format --check`, `mypy --strict`, `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`), `export_openapi.py --check` (`0-diff`), `detect-secrets-hook`, full `tests/unit` + `tests/security` + `tests/evals` + `tests/contract` (`>= 90%` branch coverage), impacted PG18+Redis integration suites, `pnpm turbo run lint typecheck test`, `scripts/check_implementation_docs.py`, and `pnpm site:sync && pnpm site:check` all pass, `ACTION_ITEM-I18N.1` and `epic-27` become `done`, and GitNexus index is refreshed cleanly.

---

## Epic 28: Unified "Mes Espaces" (`/workspaces`) 5-Tab Screen, Component De-Duplication & Direction C Sobriety (`Stories 28.1`..`28.4`)

Eliminate the 6-block vertical stacking, duplicate 3-tab vs 5-tab systems, redundant headers, raw `personal-<uuid>` slug leaks, permanent bottom-of-page DNA Starlark/glossary panels, and empty-state `0 / 0 / 0` counter/filter clutter on `/workspaces` (`WX-01`..`WX-06`, audited in `docs/planning-artifacts/sprint-change-proposal-2026-11-23-epic-28-workspaces-unification.md`), converging the screen onto a single compact workspace header synchronized with the global Sidebar Active Workspace Selector and a single canonical 5-tab container (`Accostage & Vue d'ensemble` | `Documents & Sources` | `Livrables & Artefacts` | `Glossaire & Règles Métiers` | `Membres & Paramètres de l'espace`) wired 100% to scoped PostgreSQL 18 truth.

> **Coordination Gate:** Do not start Story `28.1` until Epic 27 (`Stories 27.4` & `27.6` touching `apps/web/src/features/workspaces/` and `packages/ui/src/primitives/`) merges; rebase `feat/epic-28-workspaces-screen-unification` onto `main` first so all touched files inherit the bilingual `fr`/`en` dictionary architecture (`0` Gate 1/2/3 baseline).

### Story 28.1: Single Compact Workspace Header, Global Sidebar Scope Synchronization, Zero Raw UUID Leak & Workspace Switcher/Creation Flow (`WX-02`, `WX-06`)

As an ORCIA Workspace Contributor or Lead (`Hélène UJ-1`, `Karim UJ-9`, `Marc UJ-5`),
I want `/workspaces` ("Mes Espaces") to display a single compact workspace header synchronized directly with the global Sidebar Active Workspace Selector — without stacked redundant headers, duplicate workspace summary cards, or raw `personal-<uuid>` slugs — while preserving `+ Nouvel espace` modal creation and workspace switching,
So that I always know which workspace I am managing and never face competing workspace headers or technical UUID leaks.

**Lot:** 1 — Header & Scope Unification. **Dependencies:** `Epic 27 (27.4, 27.6)`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `WX-02`, `WX-06`.
**CAPs covered:** `CAP-067`, `CAP-080`.
**Impacted files:** `apps/web/src/routes/workspaces.tsx`, `apps/web/src/components/ModuleWorkspaceView.tsx`, `apps/web/src/features/workspaces/index.tsx`, `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx`, `apps/web/src/features/workspaces/WorkspaceStudioSummaryCard.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/28-1-single-workspace-header-sidebar-scope-sync-and-zero-uuid-leak-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authenticated user navigating to `/workspaces` (or `/spaces`)
**When** the page renders
**Then** `WorkspacesFeaturePanel` renders **at most one compact page header** synchronized with the global Sidebar `activeWorkspaceId` (removing the duplicate secondary `<nav>`, stacked summary card headers, and generic redundant banner chrome), displays the workspace human-readable name, lifecycle phase badge, and visibility badge (`Personnel` / `Équipe`), exposes a clean compact workspace switcher (plus `+ Nouvel espace` modal trigger and team-sharing CTA when permitted), and hides **all** raw `personal-<uuid>` technical slugs or raw `orcia://workspaces/personal-<uuid>` strings from primary UI text (`EXPERIENCE.md` §1.2 #1).

**Given** a user switching workspaces via either the global Left Sidebar Active Workspace Selector or the compact `/workspaces` switcher
**When** changing from the personal workspace to a team workspace and reloading (`F5`)
**Then** both the Sidebar selector, `TopHeaderBar` breadcrumb, and `/workspaces` active header/tabs stay synchronized with persisted state, all touched files remain `<= 300` lines, and `fr`/`en` i18n Gates 1–3 stay at `0`.

---

### Story 28.2: Canonical 5-Tab Workspace Container, De-Duplication of 3-Tab vs 5-Tab Panels & Direction C `total == 0` Sobriety on Tab 1 (`Accostage & Vue d'ensemble`) (`WX-01`, `WX-05`)

As an ORCIA User (`Hélène UJ-1`, `Marc UJ-5`),
I want `/workspaces` to expose a **single canonical 5-tab bar** (`1. Accostage & Vue d'ensemble` | `2. Documents & Sources` | `3. Livrables & Artefacts` | `4. Glossaire & Règles Métiers` | `5. Membres & Paramètres de l'espace`) — deleting the duplicate 3-tab `WorkspaceDetailTabsPanel` — and to obey Direction C `total == 0` sobriety on Tab 1 without displaying `0 / 0 / 0` KPI cards on an empty workspace,
So that every workspace capability lives in one obvious place with zero visual noise at Day-0.

**Lot:** 1 — Container & Tab 1 Consolidation. **Dependencies:** `28.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `WX-01`, `WX-05`.
**CAPs covered:** `CAP-061`, `CAP-080`.
**Impacted files:** `apps/web/src/features/workspaces/index.tsx`, `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx`, `apps/web/src/features/workspaces/WorkspaceDetailTabsPanel.tsx` (removed/merged), `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/28-2-canonical-five-tab-container-deduplication-and-tab1-sobriety-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the `/workspaces` page
**When** rendered for any active workspace
**Then** the DOM contains **strictly one** workspace `[role="tablist"]` with the **5 canonical Direction C tabs** (`Accostage & Vue d'ensemble`, `Documents & Sources`, `Livrables & Artefacts`, `Glossaire & Règles Métiers`, `Membres & Paramètres de l'espace`), eliminating the competing 3-tab `WorkspaceDetailTabsPanel` (`SOURCES`, `GLOSSARY`, `MEMBERS`) completely.

**Given** Tab 1 (`Accostage & Vue d'ensemble`) on a workspace with `total == 0` (zero attached sources, zero pending glossary candidates, and zero active waivers)
**When** rendered
**Then** KPI summary cards with `0` counters are hidden (`DESIGN.md:L198`) and external-rebase clutter is hidden when `rebasedChunks.length === 0`, replaced by a single clear pedagogical empty-state sentence alongside local adaptations / exception waivers (`workspace_exception_waivers` Lock V1) and sanitized deliverable destination info (editable destination `PUT` tracked in `ACTION_ITEM-28.1`), cleanly presented with `<= 300` lines per modified file and zero dead buttons.

---

### Story 28.3: Scoped PG18 Consolidation of Tab 2 (`Documents & Sources`), Tab 3 (`Livrables & Artefacts`) & Tab 5 (`Membres & Paramètres de l'espace`) (`WX-01`, `WX-04`, `WX-05`)

As an ORCIA Workspace Member or Lead (`Yanis UJ-3`, `Marc UJ-5`, `Lucas UJ-7`),
I want Tab 2 (`Documents & Sources`), Tab 3 (`Livrables & Artefacts`), and Tab 5 (`Membres & Paramètres de l'espace`) to host the real, single-source-of-truth PG18 views scoped to the active workspace ID — hiding empty-state filter pills when `0` sources exist —
So that there is only one place to attach/probe sources, manage deliverables, and configure workspace members and parameters.

**Lot:** 2 — Functional Tabs Consolidation. **Dependencies:** `28.2`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `WX-01`, `WX-04`, `WX-05`.
**CAPs covered:** `CAP-067`, `CAP-080`, `CAP-180`.
**Impacted files:** `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx`, `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, `apps/web/src/features/workspaces/WorkspaceMembersAndSettingsTab.tsx` (extracted `<= 300` L), `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/28-3-scoped-pg18-sources-deliverables-and-members-tabs-consolidation-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Tab 2 (`Documents & Sources`) active for `activeWorkspaceId`
**When** the workspace has `0` attached sources
**Then** category filter pills (`Toutes`, `Connaissances`, `Modèles & Trames`, `Code & Contrats`, `Schémas SQL`) are hidden (`total == 0`) while `+ Rattacher une source` and pedagogical 1-sentence empty-state guidance remain accessible; when `>= 1` source exists, `WorkspaceSourcesRagTab` loads exclusively from `listWorkspaceDatasources(activeWorkspaceId)` (eliminating the unscoped `datasources` duplicate list from `WorkspaceDnaAndWaiversSection`) with freshness probe and `[STALE_WARNING]` waiver support intact.

**Given** Tab 3 (`Livrables & Artefacts`) and Tab 5 (`Membres & Paramètres de l'espace`)
**When** selected and modified by an authorized user
**Then** Tab 3 renders the workspace deliverables summary (`orcia://` sanitized CAS URI, `ExternalEditRebaser` Lock V2 `rebasedChunks` list when present, and clean empty state when `0` exist — full PG18 artifact store, diff preview, download CTA & `POST /artifacts/external-rebase` deferred cleanly under `ACTION_ITEM-28.1`) without repeating header chrome, and Tab 5 displays the consolidated organization team roster, read-only workspace governance summary badges (without duplicating interactive controls from the compact header), and PG18-persisted workspace instructions (`@orcia/api-client`, `F5` cold survival verified; per-workspace member add/remove, role/tool toggles & non-admin workspace `PATCH` persistence tracked under `ACTION_ITEM-28.1`).

---

### Story 28.4: Encapsulation of DNA Starlark Compiler & PG18 Glossary Candidate Queue Inside Tab 4 (`Glossaire & Règles Métiers`), Anti-Stacking Guard & Playwright E2E Verification (`WX-03`, `WX-04`)

As a Business Lead or Ontology Referent (`Nadia UJ-4`, `ONTOLOGY_LEAD`),
I want the DNA Starlark Rule Compiler (`🛡️ Directive ➔ 📏 Norme ➔ ⚙️ Mécanisme`), `Top-3` in-flow promotions (`Lock V4`), and the `✨ À valider` glossary candidate queue to live strictly inside Tab 4 (`Glossaire & Règles Métiers`) backed by PostgreSQL 18 — never permanently pinned at the bottom of the page or backed by `useState([])` — and locked by automated anti-stacking and Playwright E2E tests,
So that `/workspaces` remains clean, consistent, and regression-proof across both French and English sessions.

**Lot:** 2 — Glossary/DNA Tab & Verification Closure. **Dependencies:** `28.3`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory `bmad-architect-worker` (`pro`) closure gate.
**Findings covered:** `WX-03`, `WX-04`, full `WX-01`..`WX-06` verification.
**CAPs covered:** `CAP-010`, `CAP-080`, `CAP-081`, `CAP-084`, `CAP-180`.
**Impacted files:** `apps/web/src/features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx`, `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, `packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx`, `apps/web/src/__tests__/workspaces-single-tabs-anti-stacking-audit.test.tsx` (new), `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts`, `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/28-4-tab4-glossary-dna-starlark-encapsulation-and-e2e-lock-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Tab 1, Tab 2, Tab 3, or Tab 5 is active on `/workspaces`
**When** rendered
**Then** `DnaStarlarkCompilerAndGlossaryLifecycleView` is **not mounted** anywhere outside Tab 4 (`Glossaire & Règles Métiers`).

**Given** Tab 4 (`Glossaire & Règles Métiers`) is active
**When** the user compiles a DNA Starlark gate rule, inspects `Top-3` in-flow proposals, or accepts/adjusts/discards a candidate in `✨ À valider`
**Then** all candidate state hydrates from and persists to PostgreSQL 18 via `@orcia/api-client` (zero ephemeral `useState([])` business store) and survives `F5` cold reload (`reloadColdFromPg`).

**Given** full `AD-17` verification and `bmad-architect-worker` (`pro`) closure review
**When** closing Epic 28
**Then** `workspaces-single-tabs-anti-stacking-audit.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `e2e-testids-sync-audit.test.ts`, i18n Gates 1–4 (`0` baseline), `pnpm turbo run lint typecheck test`, `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts` & `17-workspace-sources-codegraph-dna-and-ontology.spec.ts` (`env -u ORCIA_E2E_SEED_FIXTURES`, `fr` & `en`), `scripts/check_implementation_docs.py`, and `pnpm site:sync && pnpm site:check` all pass, `CAP-080` / `CAP-081` / `CAP-084` remain `runtime`, and `epic-28` becomes `done`.

---

## Epic 29: Canonical Page Headers (`<OrciaPageHeader />`), Multi-Workspace Scope & `CONFIDENTIAL_RESTRICTED` Hardening, Visual Grammar & Cross-Screen Consistency (`Stories 29.1`..`29.7`)

Standardize every primary and secondary ORCIA screen onto a single two-tier `<OrciaPageHeader />` primitive, resolve global `Espace actif` (`"Tous mes espaces"` / `scope-global`) runtime 404/403 bugs, enforce strict explicit-membership isolation for `CONFIDENTIAL_RESTRICTED` (`"Confidentiel isolé"`) workspaces via a real `PATCH /api/v1/workspaces/{id}` endpoint with optimistic rollback and single aligned alert banners, separate Primary Cobalt CTAs from tabs and filters, and align Zone 4 Contextual Help, monochrome `<OrciaIcon />` usage, and bilingual `fr`/`en` copy (`UH-01`..`UH-15`, tracked in `docs/planning-artifacts/sprint-change-proposal-2026-11-24-epic-29-ui-headers-scope-and-screen-consistency.md`).

### Story 29.1: Multi-Workspace Scope Resolution (`Mes Processus` 404 & `FinOps` 403/Scope-Pill Fixes) & Error-vs-Empty Mutual Exclusion (`UH-01`, `UH-02`)

As a Team Lead or Business User (`Claire UJ-8`, `Marc UJ-5`) browsing ORCIA with `"Tous mes espaces"` (`scope-global`) or a BU node selected in the left sidebar,
I want `Mes Processus` (`"Exécutions automatisées sous contrat"`) and `FinOps` to resolve authorized scopes cleanly without triggering false HTTP 404/403 banners, unselected scope pills, or contradictory empty states underneath error alerts,
So that global and delegated views show accurate, RBAC-scoped telemetry on first load.

**Lot:** 1 — P0 Runtime & Scope Fixes. **Dependencies:** `Epic 28`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-01`, `UH-02`.
**CAPs covered:** `CAP-140`, `CAP-200`, `CAP-201`.
**Impacted files:** `apps/web/src/features/processes/AutonomousRunsSupervisionPanel.tsx`, `packages/api-client/src/domains/autonomousSupervision.ts`, `apps/api/src/orcia_api/routers/autonomous_supervision.py`, `apps/web/src/features/finops/useFinopsDashboardController.ts`, `packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx`, `apps/api/src/orcia_api/routers/_finops_scope_guards.py`, `apps/web/src/i18n/locales/{fr,en}.ts`, `tests/integration/`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-1-multi-workspace-scope-resolution-processes-404-finops-403-and-error-empty-guard-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authenticated user opening `Mes Processus` with `"Tous mes espaces"` (`scope-global`) or any non-UUID workspace scope selected
**When** `AutonomousRunsSupervisionPanel` loads autonomous runs
**Then** the frontend never calls `GET /api/v1/workspaces/{non-uuid}/autonomous-runs` (supporting an authorized multi-workspace aggregation query or scoped workspace prompt cleanly), zero HTTP `404 ERR_RESOURCE_NOT_FOUND` banner is rendered, and whenever an API error banner is visible (`error !== null`), the contradictory `"Aucune exécution automatisée..."` empty-state block is suppressed.

**Given** a `TEAM_LEAD` (without global platform audit rights) opening `FinOps` under `"Tous mes espaces"` (`scope-global`) or a `BU` node
**When** `useFinopsDashboardController` initializes scope and renders `FinopsGovernanceDashboardView`
**Then** it defaults automatically to the caller's highest authorized FinOps scope (`TEAM` for `TEAM_LEAD`, `BU` for `BU_DIRECTOR`, `GLOBAL` only for `PLATFORM_ADMIN`/`OBSERVER`), hides or disables unauthorized scope pills (`Plateforme entière`), properly maps `"BU"` scopes so **exactly one** scope pill is selected at all times, suppresses the `"Aucune consommation..."` white card when an error banner is shown, and removes misleading `"demandez l'habilitation dans Mon Organisation"` instructions (`AD-21` / `AD-17` Layer 2 PG18 integration verified).

---

### Story 29.2: Scoped `PATCH /api/v1/workspaces/{id}`, Strict `CONFIDENTIAL_RESTRICTED` Isolation Enforcement, Optimistic Rollback & Single Error Banner (`UH-03`, `UH-04`)

As an ORCIA Team Lead, Workspace Member, or SecOps Reviewer (`Marc UJ-5`, `Sophie UJ-6`),
I want workspace updates to persist through a dedicated `ScopeAccessGuard`-protected `PATCH /api/v1/workspaces/{id}` endpoint with strict `CONFIDENTIAL_RESTRICTED` explicit-membership enforcement across all backend surfaces, zero corrupted `localStorage`/UI state on error, and a single properly aligned alert banner,
So that authorized workspace updates succeed cleanly, failed mutations roll back truthfully, and `"Confidentiel isolé"` truly isolates sensitive workspaces.

**Lot:** 1 — P0 Security & Persistence Integrity. **Dependencies:** `Epic 28` (resolves `ACTION_ITEM-28.1` item 1). **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) security check.
**Findings covered:** `UH-03`, `UH-04`.
**CAPs covered:** `CAP-050`, `CAP-067`, `CAP-080`, `CAP-010`, `CAP-062`.
**Impacted files:** `apps/api/src/orcia_api/routers/org_and_workspaces.py`, `apps/api/src/orcia_api/schemas/org_and_workspaces.py`, `packages/orcia-core/src/orcia_core/permissions/evaluator.py`, `packages/orcia-core/src/orcia_core/ontology/permissions.py`, `apps/api/src/orcia_api/routers/ontology_and_rag.py`, `apps/api/src/orcia_api/routers/workspace_governance.py`, `apps/api/src/orcia_api/routers/workspace_datasources.py`, `packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py`, `packages/api-client/src/generated/`, `apps/web/src/components/platformSetupContextTypes.ts`, `apps/web/src/components/usePlatformSetupHydrationEffect.ts`, `apps/web/src/components/ShellAuthFallbackView.tsx`, `apps/web/src/features/workspaces/index.tsx`, `apps/web/src/features/workspaces/WorkspaceCompactHeader.tsx`, `tests/security/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-2-scoped-workspace-patch-confidential-isolation-rollback-and-single-banner-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authorized `TEAM_LEAD`, `BU_DIRECTOR`, or `PLATFORM_ADMIN` updating a non-personal workspace via `@orcia/api-client`
**When** `PATCH /api/v1/workspaces/{id}` is invoked (replacing admin-only `PUT /api/v1/bootstrap/platform-setup-state`)
**Then** `ScopeAccessGuard` authorizes mutations on owned team workspaces (rejecting `READ_ONLY_OBSERVER`, cross-team users, and in-place visibility transitions on `PRIVATE_USER` / `personal-*` spaces with RFC 9457 `HTTP 403`), regenerates OpenAPI 3.1 SDK (`0-diff`), persists changes in PG18, and guarantees that if any workspace mutation fails, React state and `localStorage` roll back completely without mutating `Espace personnel` into `Équipe`, while rendering **at most one** `<OrciaAlertBanner />` (eliminating `"Synchronisation plateforme"` duplicate throws, the `"⚠️ "` prefix colliding with `<OrciaIcon name="cross" />`, and the `32px` `px-4` width mismatch).

**Given** a workspace configured as `CONFIDENTIAL_RESTRICTED` (`"Confidentiel isolé"`)
**When** accessed by a same-team member without explicit `workspace_memberships`, a parent `BU_DIRECTOR`, or a non-member `PLATFORM_ADMIN` across `evaluator.py`, `ontology/permissions.py`, `POST /api/v1/ontology-rag/rag/search`, `workspace_governance.py`, `workspace_datasources.py`, and `⌘K` Federated Search (`sql_federated_search.py`)
**Then** all business content (documents, Blackboard, Runs, `3_WORKSPACE` ontology items, datasources, governance, and search results) is strictly denied/filtered (`architecture.md:L692`), reserving visibility strictly to explicit `workspace_memberships` while retaining aggregate FinOps counters (`finops_cost_usd`) for authorized parents/admins (`tests/security/` + real PG18 `testcontainers` verified).

---

### Story 29.3: `Mon Assistant` Prompt & Jargon Sanitization, Speed/Tier Alignment & RBAC-Gated Composer Notices (`UH-05`)

As an ORCIA Team Lead or Business User (`Hélène UJ-1`, `Lucas UJ-7`) conversing with `Mon Assistant`,
I want assistant greetings and system framing to hide raw workspace UUIDs, internal `SPEED_1_FAST` constants, hardcoded `"PM"` fallbacks, and nonexistent `orcia://sources/*` URIs, align displayed model/effort metadata with the active speed mode, and gate admin-only settings links by RBAC,
So that `Mon Assistant` speaks in accurate business language without leaking technical plumbing or broken navigation links.

**Lot:** 1 — P0 Assistant Coherence & RBAC. **Dependencies:** `Epic 26`, `Epic 27`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-05`.
**CAPs covered:** `CAP-070`, `CAP-071`, `CAP-075`, `CAP-190`.
**Impacted files:** `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_preview.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py`, `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`, `packages/ui/src/primitives/AssistantStickyPromptFooter.tsx`, `apps/web/src/features/inbox/InboxDisabledBanner.tsx`, `apps/web/src/features/inbox/AssistantNoEmbeddingBanner.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `tests/unit/`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-3-assistant-prompt-sanitization-speed-tier-alignment-and-rbac-notices-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authenticated user (such as `TEAM_LEAD`) chatting in `Mon Assistant` on a workspace with `0` attached sources and no embedding model configured
**When** a turn executes and the response renders
**Then** the assistant context uses the workspace human-readable name (or active multi-workspace label, never raw UUIDv7), localized human-readable speed labels (never `SPEED_1_FAST`), the user's real active role/hat (never hardcoded `"PM (Product Manager)"`), and **only** genuinely attached sources (omitting unattached `orcia://sources/repo-main` defaults and nonexistent `@spec-architect` / `@security-reviewer` handles), while response footer metadata matches the active speed/tier/effort selection without contradiction.

**Given** the composer notice area above the `Mon Assistant` input when embedding or tools are unavailable
**When** rendered for a non-`PLATFORM_ADMIN` user (`TEAM_LEAD`, `MEMBER`)
**Then** the clickable `Configurer dans Administration › Modèles IA →` action link is hidden or replaced by plain administrator-contact guidance (`AD-21`), and informational notices collapse cleanly into a compact non-stacked status line preserving vertical chat height.

---

### Story 29.4: Canonical `<OrciaPageHeader />`, `<OrciaTabStrip />`, `<OrciaDataCard />`, Strict Cobalt Visual Grammar & Disabled Secondary Button Tokens (`UH-06`, `UH-07`)

As a Frontend Developer or UX Designer implementing ORCIA screens under Direction C,
I want `@orcia/ui` to provide a single canonical `<OrciaPageHeader />` primitive, a dedicated `<OrciaTabStrip />`, an `<OrciaDataCard />` surface wrapper, strict three-tier visual distinction between Primary CTAs, Tabs, and Filters, and proper disabled opacity tokens for `.orcia-ds-btn-secondary`,
So that every screen shares one unmistakable structural grammar and disabled buttons are never visually mistaken for active controls.

**Lot:** 2 — P1 Shared Design System Primitives. **Dependencies:** `Epic 28`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-06`, `UH-07`.
**CAPs covered:** `CAP-060`, `CAP-100`.
**Impacted files:** `packages/ui/src/primitives/OrciaPageHeader.tsx` (new), `packages/ui/src/primitives/OrciaTabStrip.tsx` (new), `packages/ui/src/primitives/OrciaDataCard.tsx` (new), `packages/ui/src/index.ts`, `packages/ui/src/styles/tokens-palette.css`, `packages/ui/src/styles/tokens-components.css`, `apps/web/src/components/ModuleWorkspaceView.tsx`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md`, `packages/ui/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-4-canonical-page-header-tab-strip-data-card-and-visual-grammar-tokens-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the `@orcia/ui` component library (`packages/ui/src/index.ts`)
**When** `<OrciaPageHeader />`, `<OrciaTabStrip />`, and `<OrciaDataCard />` are exported and tested in isolation
**Then** `<OrciaPageHeader />` enforces the two-tier `.orcia-bento-card` anatomy (Tier 1: monochrome `<OrciaIcon />`, `<h1>` at `var(--font-size-h2)`, optional context badge, 1-line subtitle, right-aligned Secondary + at-most-one Primary Cobalt CTA; Tier 2 optional: `<OrciaTabStrip />` + Scope Bar; aligned alert slot strictly beneath the header card) while `<OrciaTabStrip />` renders underline/segmented tabs visually distinct from solid Cobalt primary buttons and neutral filter/scope pills.

**Given** disabled secondary/ghost buttons and `ModuleWorkspaceView`
**When** `.orcia-ds-btn-secondary:disabled` and `.orcia-ds-btn-ghost:disabled` are rendered in CSS (`tokens-components.css`) and `ModuleWorkspaceView` wraps module routes
**Then** disabled secondary/ghost buttons apply `opacity: 0.48; cursor: not-allowed; pointer-events: none;` matching primary (`0.48`) and danger (`0.50`) tokens, `ModuleWorkspaceView` uses semantic `<h1>` via `<OrciaPageHeader />` instead of `16px <strong>`, and `packages/ui` preserves zero forbidden imports (`@tanstack/react-router`, `@orcia/api-client`, zero raw hex outside `tokens*.css`).

---

### Story 29.5: Header & Layout Convergence — `Mon Assistant`, `Mes Processus`, `Mes Agents` & `FinOps` (`UH-06`, `UH-09`, `UH-11`, `UH-12`)

As an ORCIA User navigating across `Mon Assistant`, `Mes Processus`, `Mes Agents`, and `FinOps`,
I want all four operational screens to adopt `<OrciaPageHeader />`, `<OrciaTabStrip />`, and `<OrciaDataCard />` cleanly — removing tab-switch header wrapping, misplaced MCP/IDE cards, competing solid-blue CTAs, and bare canvas headers/tables,
So that every screen exhibits predictable hierarchy, zero layout jump across tabs, and clean card framing on `#EAF2FB`.

**Lot:** 3 — P1 Screen Convergence (Batch A). **Dependencies:** `29.1`, `29.3`, `29.4`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-06`, `UH-09`, `UH-11`, `UH-12`.
**CAPs covered:** `CAP-071`, `CAP-090`, `CAP-091`, `CAP-140`, `CAP-200`.
**Impacted files:** `apps/web/src/features/inbox/AssistantTopToolbar.tsx`, `apps/web/src/features/inbox/index.tsx`, `apps/web/src/features/processes/ProcessesHubPage.tsx`, `apps/web/src/features/processes/ProcessesActiveDossiersCard.tsx`, `packages/ui/src/components/AgentsAndSkillsHeaderAndToolbar.tsx`, `packages/ui/src/components/AgentsAndSkillsManagerView.tsx`, `packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-5-header-layout-convergence-assistant-processes-agents-and-finops-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `Mon Assistant` and `Mes Processus`
**When** rendered
**Then** both mount `<OrciaPageHeader />` with semantic `<h1>`, monochrome icon, 1-line subtitle, and separated Tier-2 navigation/primary CTA (`+ Nouvelle conversation` vs `Conversations` / `Dossiers` on `Mon Assistant`; max 1 solid Cobalt `+ Nouveau processus` header CTA on `Mes Processus` while repeated `Lancer ce processus` card actions use secondary/outline Cobalt styling, and `"Mon Compte"` titles no longer leak under global `"Tous mes espaces"` scope).

**Given** `Mes Agents` (`Mes Agents` | `Compétences` | `Serveurs d'outils & MCP`) and `FinOps`
**When** switching tabs or viewing `FinOps`
**Then** `Mes Agents` unwraps the outer mega-card, moves the 3 tabs into Tier 2 (`<OrciaTabStrip />`) eliminating the Tab-3 header wrap jump (`CLS = 0`), scopes the Agent/Skill KPIs and filter bar strictly to tabs 1–2 (hidden on `Serveurs d'outils & MCP`), and separates outbound MCP Server management from the inbound IDE access card (replacing raw `assistant.ask` / `agent.invoke` / `agent.list_exposed` RPC jargon with human-readable capability labels); `FinOps` wraps its header in `<OrciaPageHeader />` (with non-truncated `Journal d'activité` and distinct scope pills) and wraps its data table inside `<OrciaDataCard />` (`<= 300` lines per modified file).

---

### Story 29.6: Header & Layout Convergence — `Mes Espaces`, `Mon Organisation`, `Aide` & Secondary Routes (`UH-06`, `UH-08`, `UH-10`, `UH-13`)

As an ORCIA User navigating `Mes Espaces`, `Mon Organisation`, `Aide`, and secondary views (`/cockpit`, `/settings`, `/settings/packs`, `/profile`, `/activity`),
I want `Mes Espaces` stripped of its dead `Phase` dropdown, duplicate workspace switcher, and numbered `1.`–`5.` tabs, `Mon Organisation` actions unified in `<OrciaPageHeader />` with accurate sibling badges, and `Aide` expanded cleanly across the full workspace width,
So that workspace configuration, org hierarchy, help resources, and secondary routes match the exact same Direction C layout grammar.

**Lot:** 3 — P1 Screen Convergence (Batch B). **Dependencies:** `29.2`, `29.4`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-06`, `UH-08`, `UH-10`, `UH-13`.
**CAPs covered:** `CAP-058`, `CAP-060`, `CAP-064`, `CAP-067`, `CAP-080`, `CAP-203`.
**Impacted files:** `apps/web/src/features/workspaces/WorkspaceCompactHeader.tsx`, `apps/web/src/features/workspaces/WorkspaceMembersAndSettingsTab.tsx`, `apps/web/src/routes/organization.tsx`, `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx`, `apps/web/src/routes/SettingsOrganizationUnitRow.tsx`, `apps/web/src/routes/help.tsx`, `packages/ui/src/primitives/HelpCenterCatalogView.tsx`, `apps/web/src/components/ShellContainer.tsx`, `apps/web/src/features/cockpit/index.tsx`, `apps/web/src/routes/settings.tsx`, `apps/web/src/features/settings/packs/PacksRegistryPage.tsx`, `packages/ui/src/primitives/UserProfileOverviewPage.tsx`, `packages/ui/src/primitives/ActivityLogExplorerView.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-6-header-layout-convergence-workspaces-organization-help-and-secondary-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `Mes Espaces`
**When** rendered for a personal or team workspace
**Then** the screen uses `<OrciaPageHeader />` + `<OrciaTabStrip />` without the duplicate `workspaces-active-switcher-select`, without the dead `Phase : Construction / Exploitation / Évolution` `<select>` and header badge, without the duplicate `Glossaire métier` header button, and without numeric `1.`–`5.` tab prefixes (`Accostage & Vue d'ensemble` | `Documents & Sources` | `Livrables & Artefacts` | `Glossaire & Règles Métiers` | `Membres & Paramètres de l'espace`), while team-workspace visibility settings (with plain-language mode explanations, powered by `PATCH /api/v1/workspaces/{id}` from `Story 29.2`) live inside Tab 5 (`Membres & Paramètres`) and remain locked on `PRIVATE_USER` spaces.

**Given** `Mon Organisation`, `Aide`, and secondary routes (`/cockpit`, `/settings`, `/settings/packs`, `/profile`, `/activity`)
**When** rendered
**Then** `Mon Organisation` moves `+ Inviter un utilisateur` & `+ Nouvelle unité` into `<OrciaPageHeader />` actions, removes the redundant inline `Repères` box, distinguishes ancestor units (`Contexte parent`) from sibling teams (`Autre équipe — lecture seule`), and hides `Modifier`/`Supprimer` write buttons on read-only rows; `Aide` mounts `<OrciaPageHeader title="Centre d'Aide" />` (putting the Showcase link as a secondary action or card instead of stealing the header slot), removes the `max-w-4xl` half-screen void, and marks/disables the TopBar `Aide` toggle when active on `/help`; and secondary routes standardize onto `<OrciaPageHeader />`.

---

### Story 29.7: Monochrome Icon Purge, Copy/Jargon Hygiene, Zone 4 Contextual Help Alignment, Automated Header CI Guard & Epic 29 Closure (`UH-14`, `UH-15`)

As an ORCIA Product Owner & Maintainer (`Hélène UJ-1`, `Sally`, `Winston`),
I want raw Unicode emojis purged from headers/tabs in favor of `<OrciaIcon />`, remaining FR/EN jargon, pluralization defects, and test fixtures cleaned up, Zone 4 Contextual Help synchronized with `DESIGN.md`, and an automated test gate locking header & visual grammar compliance,
So that all screens remain visually cohesive, bilingual, jargon-free, and immune to header drift regressions.

**Lot:** 4 — P2 Polish, Anti-Drift Lock & Closure. **Dependencies:** `29.5`, `29.6`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory `bmad-architect-worker` (`pro`) closure gate.
**Findings covered:** `UH-14`, `UH-15` (and full `UH-01`..`UH-15` closure verification).
**CAPs covered:** `CAP-060`, `CAP-064`, `CAP-090`, `CAP-100`, `CAP-203`.
**Impacted files:** `apps/web/src/i18n/locales/governance_and_packs_labels_fr.ts`, `apps/web/src/i18n/locales/{fr,en}.ts`, `packages/ui/src/components/iconRegistry.ts`, `docs/help/{fr,en}/*.md`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md`, `apps/web/src/__tests__/page-header-structure-and-visual-grammar-audit.test.tsx` (new), `apps/web/e2e/`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-7-icon-purge-copy-hygiene-contextual-help-ci-guard-and-epic-29-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `apps/web` headers, tabs, buttons, and Zone 4 Contextual Help (`docs/help/{fr,en}/*.md`)
**When** inspected in both French (`fr`) and English (`en`) sessions
**Then** zero raw Unicode emojis (`🤖`, `🛠️`, `🔌`, `🔒`, `📁`, `📦`) appear in page headers, tabs, or primary action labels (replaced by `<OrciaIcon />`), zero technical jargon (`Temp 0.2 · 4096 tok`, `Skills`, `(/SKILLS)`), FR pluralization bugs (`1 actifs`, `1 réutilisables`), or seeded E2E fixtures (`Story 26.1 Regression Agent`) appear in UI text, and Zone 4 Contextual Help follows `DESIGN.md`'s 4-block structure accurately (fixing stale `Mes Espaces` filter copy, `Mon Organisation` Admin-help bleed, removed-`ⓘ` instructions in `Aide`, and `DESIGN.md` TopBar vs Bottom-Left `Mon Compte` spec alignment).

**Given** the automated anti-drift guard `page-header-structure-and-visual-grammar-audit.test.tsx` and full `AD-17` closure verification with `bmad-architect-worker` (`pro`)
**When** closing Epic 29
**Then** the CI audit confirms every routed main screen mounts `<OrciaPageHeader />` with a single semantic `<h1>` and at most one primary solid-Cobalt header CTA, `ruff check`, `ruff format --check`, `mypy --strict`, `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`), `export_openapi.py --check` (`0-diff`), full `tests/unit` + `tests/security` + impacted PG18+Redis `testcontainers` suites (`>= 90%` coverage), `pnpm turbo run lint typecheck test`, Desktop Playwright E2E across all 8 audited screens (`env -u ORCIA_E2E_SEED_FIXTURES`, `fr` & `en`), `scripts/check_implementation_docs.py`, and `pnpm site:sync && pnpm site:check` all pass, `CAP-xxx` entries remain `runtime`, GitNexus index refreshes cleanly, and `epic-29` transitions to `done`.

---

## Epic 30: Honest Save Semantics, Clean Conversational Prompts, Real PG18 Process Runs & Focus Review, and Agent Lifecycle Hardening (`Stories 30.1`..`30.6`)

Eliminate broken auto-save + explicit Save hybrids across `"Réglages de Mon Assistant"` and `"Mes Agents & Compétences"`, decouple `Mon Assistant`'s conversational LLM prompt from UI governance preview cards with conditional provenance and an explicit empty-evidence anti-hallucination guard, replace hardcoded `Mes Processus` pending validations and cassette fallbacks with real PostgreSQL 18 runs behind a tabbed hub and a clear 3-zone Focus Review (`/processes/runs/$runId`), and enforce PG18 persistence, inline modal alerts, and real `DRAFT` vs `ACTIVE` lifecycle gating for agents (`UX30-01`..`UX30-16`, tracked in `docs/planning-artifacts/sprint-change-proposal-2026-11-25-epic-30-assistant-processes-and-agents-ux-hardening.md`).

### Story 30.1: `Mon Assistant` Settings Explicit Save, Honest Dirty Guard, Inline Modal Errors & Empty Personal Instructions (`UX30-01`, `UX30-02`, `UX30-03`)

As an ORCIA User configuring `"Réglages de Mon Assistant"` (`Hélène UJ-1`, `Lucas UJ-7`),
I want an explicit bottom-right `Enregistrer` button (`Annuler` / `Fermer` + primary Cobalt `Enregistrer`), baseline-diff `isDirty` tracking without keystroke auto-save storms, honest `✓ Enregistré` feedback shown only after PostgreSQL 18 confirms, inline error alerts inside the modal, and the ability to leave `"Mes consignes personnelles permanentes"` empty,
So that `"Annuler"` genuinely discards unsubmitted changes without false `"Modifications non enregistrées"` warnings after saving, and personal instructions stay free of forced default `[S1]` boilerplate.

**Lot:** 1 — `Mon Assistant` Settings & Prompt Hardening. **Dependencies:** `Epic 29`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UX30-01`, `UX30-02`, `UX30-03`.
**CAPs covered:** `CAP-070`, `CAP-100`.
**Impacted files:** `packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx`, `packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx`, `packages/ui/src/primitives/AssistantGovernanceTypes.ts`, `apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx`, `apps/web/src/features/inbox/useServerAssistantGovernance.ts`, `apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts`, `apps/api/src/orcia_api/schemas/assistant_governance_and_three_speed.py`, `packages/orcia-core/src/orcia_core/orchestration/_assistant_locales.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py`, `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_governance.py`, `packages/api-client/src/generated/`, `packages/ui/src/__tests__/rgaa-modals-escape-unsaved-guard.test.tsx`, `apps/web/e2e/22-assistant-tool-loop-approval-and-reattach.spec.ts`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-1-assistant-settings-explicit-save-dirty-guard-and-empty-instructions-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authenticated user editing dropdowns or `"Mes consignes personnelles permanentes"` / `"Réglages de l'Espace"` inside `"Réglages de Mon Assistant"`
**When** typing or switching values before clicking `Enregistrer`
**Then** zero auto-save `PUT` calls fire on keystroke or selection changes, `isDirty` is computed strictly by comparing Tab 1 and Tab 2 drafts against hydrated server baselines, clicking `Annuler` or pressing `Escape` opens `<RgaaUnsavedChangesAlert />` where `"Quitter sans enregistrer"` discards only unsubmitted React edits without touching PostgreSQL 18, and the 3-column select width displays `"Équilibré & Structuré (Recommandé)"` without clipping.

**Given** the user clicks the bottom-right primary Cobalt `Enregistrer` button (`<RgaaDialogFooterActions />`)
**When** `PUT /api/v1/assistant/governance/mode-a/user` and/or `/workspace` succeeds (or fails with HTTP `4xx`/`5xx`)
**Then** on success `await onSave*` completes before showing `"✓ Enregistré"`, resets `isDirty` to `false`, refreshes Tab 3 (`Consignes actives`), keeps the modal open so `Fermer` / `Escape` exits with zero false warning, and removes all 4 hidden `display: none` Save buttons, 3 legacy duplicate `<select>` nodes, and the E2E `.evaluate()` click workaround; on failure, `✓ Enregistré` never appears, `isDirty` stays `true`, and a localized `[role="alert"]` renders **inside** the modal body; and empty (`""`) `personal_instructions` (`min_length=0` in `UpdateUserLayerPreferencesRequest`, empty backend default, `0-diff` OpenAPI SDK) persists cleanly to PG18 (`AD-17` Layer 2 verified).

---

### Story 30.2: `Mon Assistant` Clean Conversational System Prompt, Single Layer Injection & Empty-Evidence Anti-Hallucination Guard (`UX30-04`, `UX30-05`)

As an ORCIA User conversing with `Mon Assistant` (`Hélène UJ-1`, `Lucas UJ-7`),
I want the live conversational LLM system prompt strictly decoupled from UI governance preview cards, stripped of raw internal tags and duplicate layers, given a natural-speech confidentiality directive, and protected by a conditional empty-evidence guard when zero sources match,
So that simple greetings and everyday replies sound natural and never invent `orcia://system/status/ready`, `[Citation non vérifiée]`, or `SHA-256("")` proofs.

**Lot:** 1 — `Mon Assistant` Settings & Prompt Hardening. **Dependencies:** `30.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UX30-04`, `UX30-05`.
**CAPs covered:** `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-074`.
**Impacted files:** `apps/api/src/orcia_api/routers/_assistant_context_assembly.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_builder.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_preview.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py`, `packages/orcia-core/src/orcia_core/orchestration/_assistant_profile_locales.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_evidence_table.py`, `packages/orcia-core/src/orcia_core/orchestration/_assistant_citations_verifier.py`, `tests/unit/`, `tests/evals/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-2-assistant-conversational-prompt-cleanup-and-empty-evidence-guard-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `_assistant_context_assembly.py` assembling the system prompt for a live `/api/v1/assistant/turns` request
**When** building the conversational prompt in French (`fr`) or English (`en`)
**Then** `build_five_layers_preview_items` remains strictly for Tab 3 UI preview while live turns receive a dedicated conversational system prompt with single (non-duplicated) Workspace and User instructions, the real active `pack_key`, human-readable `PROFILE_LABELS_LOCALES` (removing `"Topologie DAG, Dépendances, Hashes SHA-256 & Exécution N3"` and `"DAG Steps & Verrous run-lock.json"` plumbing), zero raw internal tags (`[CONSTITUTIONAL_IMMUTABLE_LAYER_1]`, `[NO_HUMAN_ANCHOR_WRITE]`, `human_authored_required: true`, `[EXPLICIT_PROVENANCE_URI]`, `[ACTIVE_DOMAIN_PACK: ...]`, `[ADAPTATION_RUNTIME_METADATA]`), and an explicit prompt-confidentiality / natural-speech rule forbidding repeating system instructions or internal tokens.

**Given** an Assistant turn whose `EvidenceTable` contains `0` sources and `0` ontology glossary items (e.g., greeting or RAG inactive)
**When** assembling the prompt and finalizing the streamed response
**Then** citation/URI/SHA-256 rules activate **only** when `EvidenceTable` is non-empty; when empty, `format_evidence_table_for_layer_4` / `AssistantPromptBuilder` injects an explicit localized (`fr`/`en`) empty-evidence guard instructing the model to answer conversationally without citing `[S#]`, `orcia://`, or `sha256:`, and post-stream `CitationGuard` + golden evals verify zero fabricated `orcia://` URIs, `SHA-256("")` digests, or `[Citation non vérifiée]` leaks.

---

### Story 30.3: `Mes Processus` Real PG18 Pending Validations, Live Workspace LLM Execution & Coalesced Reasoning Trace (`UX30-06`, `UX30-07`, `UX30-08`)

As an ORCIA Team Lead or Contributor (`Marc UJ-5`, `Nadia UJ-4`) opening `Mes Processus` (`/processes`),
I want pending validations hydrated strictly from real workspace-scoped PostgreSQL 18 runs (`0` on clean Day-0), zero `localStorage` auto-launched cassette traces referencing `docs/product/capabilities.yaml`, and cleanly coalesced reasoning blocks,
So that `Mes Processus` never fabricates leftover test validations or splits thoughts mid-token every 64 characters.

**Lot:** 2 — `Mes Processus` Real Persistence & Focus Review. **Dependencies:** `Epic 29`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UX30-06`, `UX30-07`, `UX30-08`.
**CAPs covered:** `CAP-020`, `CAP-021`, `CAP-140`, `CAP-160`.
**Impacted files:** `apps/web/src/features/processes/ProcessesHubPage.tsx`, `apps/web/src/features/processes/ProcessesActiveDossiersCard.tsx`, `apps/web/src/features/processes/execution/useInteractiveProcessRunController.ts`, `apps/api/src/orcia_api/routers/workflows.py`, `apps/api/src/orcia_api/routers/executions_trace.py`, `packages/orcia-core/src/orcia_core/agents/process_dispatcher.py`, `packages/orcia-core/src/orcia_core/agents/llm_adapter.py`, `packages/ui/src/components/AgentExecutionTrace.tsx`, `packages/ui/src/components/AgentExecutionTraceItems.tsx`, `packages/api-client/src/generated/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-3-processes-real-pg18-pending-runs-live-llm-and-coalesced-trace-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a workspace (or global `"Tous mes espaces"`) with `0` active/pending process runs in PostgreSQL 18 (`workflow_runs` / `reflexive_execution_sessions`)
**When** opening `Mes Processus` (`/processes`)
**Then** `ProcessesActiveDossiersCard` / `ProcessesHubPage` hydrates pending validations strictly from a workspace-scoped PG18 endpoint (`0-diff` OpenAPI SDK), never renders the hardcoded `"1 validation en attente de votre décision"` badge or promotes `workflows[0]` (`wf-generate-orcia-documentation`), removes `localStorage["orcia.processes.active_run_workflow_id.v1"]` sticky auto-launch on mount, and reflects truthful backend run status (`RUNNING`, `WAITING_SUBSTEP_HITL`, `WAITING_FINAL_ANCHOR`, `WAITING_WRITE_PREVIEW`, `COMPLETED`, `PAUSED`).

**Given** a user explicitly launching a goal-driven process run in production
**When** `ProcessExecutionDispatcher` and `GatewayReflexiveLlmAdapter` execute and stream the run
**Then** production execution strictly uses the workspace's configured LLM and real attached workspace datasources (returning a clear localized RFC 9457 error when no LLM/datasource is configured, with zero fallback to `DeterministicCassetteLLM` or `_DEFAULT_FALLBACK_RESOURCE = "docs/product/capabilities.yaml"`, keeping cassettes strictly under `tests/`), and `AgentExecutionTrace` / `AgentExecutionTraceItems` coalesce consecutive `THOUGHT_DELTA` chunks within each phase group into a single continuous thought block instead of rendering separate `"Réflexion en cours"` headers every 64 characters (`AD-17` Layer 2 PG18 verified).

---

### Story 30.4: `Mes Processus` Tabbed Hub (`<OrciaTabStrip />`), Dedicated Focus Review (`/processes/runs/$runId`) & Single State-Gated Decision Bar (`UX30-09`, `UX30-10`)

As an ORCIA Team Lead or Reviewer (`Marc UJ-5`, `Sophie UJ-6`) managing workflows and reviewing deliverables,
I want `Mes Processus` organized into distinct `<OrciaTabStrip />` tabs (`Validations & Exécutions` | `Processus métiers` | `Chaîne de valeur`) and individual run reviews moved onto a dedicated 3-zone Focus Review route (`/processes/runs/$runId`),
So that I can see available business processes cleanly, immediately identify the single expected decision, read the formatted deliverable without scrolling past trace logs, and consult agent reasoning on demand.

**Lot:** 2 — `Mes Processus` Real Persistence & Focus Review. **Dependencies:** `30.3`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UX30-09`, `UX30-10`.
**CAPs covered:** `CAP-020`, `CAP-021`, `CAP-140`, `CAP-160`, `CAP-200`.
**Impacted files:** `apps/web/src/router.tsx`, `apps/web/src/features/processes/ProcessesHubPage.tsx`, `apps/web/src/features/processes/ProcessesActiveDossiersCard.tsx`, `apps/web/src/features/processes/ProcessesValueStreamOverviewCard.tsx`, `apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx`, `apps/web/src/features/processes/execution/InteractiveRunDeliverableAndHitlPanels.tsx`, `apps/web/src/features/processes/processStudioV2StructuralVsm.ts`, `apps/web/src/i18n/locales/process_catalog_vsm_p1_{fr,en}.ts`, `apps/web/src/i18n/locales/process_studio_ui_labels_{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-4-processes-tabbed-hub-and-focus-review-action-artifact-reasoning-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `Mes Processus` (`/processes`)
**When** rendered inside `<OrciaPageHeader />`
**Then** Tier-2 `<OrciaTabStrip />` separates **`Validations & Exécutions (N)`** | **`Processus métiers`** | **`Chaîne de valeur`** (omitting the `(N)` badge and defaulting to `Processus métiers` when `N === 0`), removing the inline run drawer from the catalog page, integrating autonomous runs supervision cleanly into Tab 1 without unrelated 403/empty clutter, and removing hardcoded `"Mon Compte"` VSM titles/slugs from `process_catalog_vsm_p1_{fr,en}.ts` and `processStudioV2StructuralVsm.ts`.

**Given** a user inspecting a run on `/processes/runs/$runId` (navigated from `Validations & Exécutions`, Cockpit, or launch)
**When** rendered on Desktop (`>= 1280px`) and Laptop (`< 1280px`)
**Then** the Focus Review view displays: (1) **Zone 1 — Sticky Expected Action Banner** (semantic Amber `#D97706` for validation/arbitration, Violet `#6D28D9` exclusively for mandatory human anchors) with **strictly ONE primary Cobalt CTA** state-gated between substep approval and final publication (eliminating the stacked duplicate Bar 1/Bar 2 and duplicate Edit button, and hiding correction step/comment controls inside a `"Demander une correction"` popover until clicked); (2) **Zone 2 — Primary Artifact Consultation** (~65% width left pane) rendering formatted Markdown, clickable source chips, and a clean `Lecture` / `Édition` toggle; and (3) **Zone 3 — Secondary Reasoning Rail** (~35% width right pane, switching to 2 sub-tabs below `1280px`) with `defaultCollapsedWhenCompleted={true}` once waiting/completed and live-expanded only while `RUNNING`.

---

### Story 30.5: `Mes Agents` PG18 Pack-Agent Governance Sync, Clean 6-Block Modal Save/Errors & Real `DRAFT` vs `ACTIVE` Lifecycle Gating (`UX30-11`..`UX30-15`)

As an ORCIA Team Lead or Agent Author (`Karim UJ-9`, `Marc UJ-5`) configuring agents in `"Mes Agents & Compétences"`,
I want Pack agents persisted/synced in PostgreSQL 18 so `"Exposer en outil externe"` never throws 404, errors displayed inline inside the modal, a single non-duplicated 6-block editor with an honest explicit Save footer, and a real `DRAFT` vs `ACTIVE` lifecycle enforced across `Mon Assistant`, `Mes Processus`, and MCP exposure,
So that configuring and governing agents behaves reliably and `"Validé au Banc de Test"` is never faked.

**Lot:** 3 — `Mes Agents` PG18 Persistence, Modal & Lifecycle Hardening. **Dependencies:** `Epic 29`. **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) review on lifecycle & MCP exposure contract.
**Findings covered:** `UX30-11`, `UX30-12`, `UX30-13`, `UX30-14`, `UX30-15`.
**CAPs covered:** `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`.
**Impacted files:** `apps/api/src/orcia_api/routers/agents_and_skills.py`, `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`, `packages/orcia-core/src/orcia_core/orchestration/_agents_and_skills_executor.py`, `packages/orcia-core/src/orcia_core/bootstrap/seeder.py`, `apps/web/src/features/catalog/packAgentsCatalog.ts`, `apps/web/src/features/catalog/useManagedAgentActions.ts`, `apps/web/src/features/catalog/index.tsx`, `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts`, `packages/ui/src/components/AgentDetailAndSandboxModal.tsx`, `packages/ui/src/components/AgentStudioCardItem.tsx`, `packages/ui/src/components/AgentTestBenchSection.tsx`, `packages/api-client/src/generated/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-5-agents-pg18-mcp-sync-clean-modal-save-and-draft-active-lifecycle-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authorized user toggling `"Exposer en outil externe"` or editing a Pack or custom agent in `AgentDetailAndSandboxModal`
**When** `PATCH /api/v1/agents-and-skills/agents/{agent_id}/governance` or `POST /api/v1/agents-and-skills/agents` runs
**Then** active Pack agents exist in PostgreSQL 18 (via idempotent seeding / workspace activation sync) and `update_agent_governance_endpoint` calls `await _sync_from_postgres18_if_enabled(request, svc)`, eliminating the HTTP `404 ERR_RESOURCE_NOT_FOUND` (`Exposition MCP`) across cold worker restarts; any API failure rolls back optimistic checkbox state and renders an inline `[role="alert"]` **inside** `AgentDetailAndSandboxModal` (never hidden behind the dimmed backdrop); duplicated `<AgentIdentityAndSkillsFields />` summary fields above `<AgentSixBlocksEditorBody />` are removed; and clicking explicit bottom-right `Enregistrer` (`<RgaaDialogFooterActions />` + `useUnsavedChangesDialogGuard`) awaits real API persistence without `useEffect([agent])` wiping `"Modifications enregistrées"` feedback.

**Given** an agent's lifecycle and test-bench state across `Mes Agents`, `Mon Assistant`, `Mes Processus`, and external MCP exposure
**When** inspecting cards, opening the modal, mentioning `@agent`, selecting workflow delegates, or enabling external MCP exposure
**Then** cosmetic hardcoded `"Validé au Banc de Test"` (`|| isPack` in `AgentStudioCardItem`, `testBenchValidated: true` in `packAgentsCatalog.ts` and `.catch()` in `useManagedAgentActions.ts`, and forced `True` in `_agents_and_skills_executor.py`) is replaced by explicit **`lifecycle_status` (`DRAFT` vs `ACTIVE`)** and factual **`test_bench_status` (`UNTESTED` | `PASSED` | `FAILED`)**; `DRAFT` agents are strictly blocked (both UI and backend) from `@agent` Assistant selection/invocation, Process execution, and external MCP exposure (`HTTP 422`), whereas `ACTIVE` agents are selectable and executable (`AD-17` Layer 2 PG18 `create_app()` verified).

---

### Story 30.6: Epic 30 Anti-Regression CI Guards, Bilingual FR/EN Playwright E2E Lock, Contextual Help & Doc Sync, and Closure (`UX30-16`)

As an ORCIA Maintainer and Product Owner (`Sally`, `Winston`, `Hélène UJ-1`),
I want automated CI audits locking every Epic 30 guarantee, synchronized Zone 4 help & UX specs, full 5-layer `AD-17` verification including bilingual (`fr`/`en`) Desktop Playwright E2E, and formal `bmad-architect-worker` (`pro`) sign-off,
So that save-state contradictions, prompt leaks, cassette fallbacks, and fake validation states can never regress.

**Lot:** 4 — Regression Lock & Epic 30 Closure. **Dependencies:** `30.2`, `30.4`, `30.5`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory `bmad-architect-worker` (`pro`) closure gate.
**Findings covered:** `UX30-16` (and full `UX30-01`..`UX30-15` end-to-end verification).
**CAPs covered:** `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-160`.
**Impacted files:** `apps/web/src/__tests__/`, `tests/evals/`, `tests/security/`, `apps/web/e2e/`, `docs/help/{fr,en}/*.md`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/{DESIGN,EXPERIENCE}.md`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-6-epic-30-anti-regression-audits-bilingual-e2e-and-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the Epic 30 automated CI guardrails and documentation updates
**When** running static audits, golden evals, and Zone 4 contextual help checks
**Then** automated tests lock: (a) inline `[role="alert"]` error rendering on every edit modal (`AssistantGovernanceModalAndStudio`, `AgentDetailAndSandboxModal`), (b) single primary decision CTA in `/processes/runs/$runId` Focus Review, (c) zero raw internal markers (`[CONSTITUTIONAL_IMMUTABLE_LAYER_1]`, `[NO_HUMAN_ANCHOR_WRITE]`, `human_authored_required`) and zero `SHA-256("")` / `orcia://` fabrication in empty-evidence Assistant golden evals, and (d) strict `DRAFT` agent exclusion across Assistant/Processes/MCP; and `docs/help/{fr,en}/{assistant,processes,agents}.md` plus `DESIGN.md`/`EXPERIENCE.md` reflect the updated UI flows accurately.

**Given** full `AD-17` 5-layer closure verification and `bmad-architect-worker` (`pro`) review
**When** closing Epic 30
**Then** all production files remain `<= 300` lines, `.venv/bin/ruff check .`, `ruff format --check .`, `mypy --strict`, `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`), `export_openapi.py --check` (`0-diff`), i18n Gates 1–4 (`0` baseline), full `tests/unit` + `tests/evals` + `tests/security` + `tests/contract` + impacted PG18+Redis `testcontainers` (`>= 90%` branch coverage), `pnpm turbo run lint typecheck test`, bilingual (`fr` & `en`) Desktop Playwright E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, zero `.evaluate()` hidden-button workarounds), `scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, and `npx gitnexus analyze` all pass, `CAP-xxx` entries remain `runtime`, and `epic-30` becomes `done`.

---

## Epic 31: Declarative APM-Compatible Business Packs, Unified Workspace Activation, Qualified Namespacing & Pack Composer (`Stories 31.1`..`31.7`)

Eliminate disk-to-memory pack silos and hardcoded TypeScript pack catalogs (`packs/` vs `packAgentsCatalog*.ts` vs `processStudioV2StructuralVsm.ts` vs orphan `declarative_pack_bundles` / `sql_declarative_packs.py`), replace dual runtime/draft sources with an **APM-Superset PostgreSQL 18 + SeaweedFS CAS bundle engine** (`declarative_pack_bundles` v2 + `pack_bundle_id` lineage across agents, skills, instructions, VSM/DAG workflows, ontology terms, DNA Starlark mechanisms, and policies), enforce **Workspace-only pack activation (`workspace_pack_activations`) with connector slot bindings (`workspace_pack_slot_bindings`) and `run_lock_manifests` SHA-256 pinning**, introduce **strict `{pack_slug}:{entity_slug}` qualified namespacing** with flat priority-ordered ontology resolution, and ship an **Authoring Pack Composer** (`CUSTOM` draft membership, anti-hostage unlink, dependency closure gate, PII/infra scrubbing) plus full bilingual Direction C UI (`Mes Packs`, Slot Binding Drawer, Composer Modal, `@pack:agent` / `/pack:skill` autocomplete), tracked in `docs/planning-artifacts/sprint-change-proposal-2026-11-25-epic-31-declarative-apm-packs-import-export.md` and `docs/implementation-artifacts/epic-31-decisions-grill-2026-11-25.md`.

### Story 31.1: `declarative_pack_bundles` v2 DDL & Native APM-Superset Manifest/Archive Codec (`D1`, `D3`, `D4`, `D6`)

As an ORCIA Platform Architect (`Winston`, `Karim UJ-9`),
I want an immutable PostgreSQL 18 schema v2 for declarative pack bundles (`declarative_pack_bundles` v2, `pack_bundle_id` FKs `ON DELETE CASCADE`, `pack_dna_mechanisms`, `pack` connector scheme + `orcia://packs/`, `pack_draft_memberships` `ON DELETE RESTRICT`, `workspace_pack_activations`, `workspace_pack_slot_bindings`) and a dependency-free YAML+Markdown frontmatter codec (`ApmPackCodec`),
So that ORCIA and GitHub APM packs parse, validate, canonicalize, and fail-closed on executable hooks in Python without any external Node runtime or new third-party dependency.

**Lot:** 1 — PG18 Schema v2 & Native APM Codec. **Dependencies:** `Epic 30`. **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) architecture contract review.
**Findings covered:** `D1`, `D3`, `D4`, `D6`, `A1`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-082`, `CAP-090`.
**Impacted files:** `infra/migrations/versions/20261126_311_declarative_packs_v2.py` (new), `infra/scripts/maintenance/_first_boot_reset_guards.py`, `packages/orcia-core/src/orcia_core/packs/` (domain models, ports, `errors.py`, `_internal/apm_codec.py`, `_internal/sql_declarative_packs.py`), `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-1-pack-bundles-v2-ddl-and-native-apm-codec-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Alembic migration `20261126_311_declarative_packs_v2.py` (`upgrade()` and tested `downgrade()`)
**When** applied on PostgreSQL 18 and checked against `first_boot_reset_guards` and `test_migrations.py`
**Then** `declarative_pack_bundles` v2 includes `bundle_kind` (`SYSTEM` | `ORG` | `IMPORTED` | `CUSTOM`), `archive_sha256`, `cas_object_key`, `manifest_yaml`, `source_origin`, `declared_slots_jsonb`, and `UNIQUE uq_pack_bundle_scope_slug_ver (scope_type, scope_id, slug, version)`; child tables (`catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_*`, `permission_broker_policies`) carry nullable `pack_bundle_id` FK `ON DELETE CASCADE`; `pack_dna_mechanisms`, `pack_draft_memberships` (`ON DELETE RESTRICT`), `workspace_pack_activations` (`WORKSPACE` scope check + `DEFERRABLE INITIALLY DEFERRED` priority uniqueness), `workspace_pack_slot_bindings`, and `pack` scheme (`orcia://packs/`) in `connector_schemes` are created cleanly via raw SQL `op.execute(sa.text(...))`.

**Given** an incoming APM-Superset `.zip` archive or directory (`apm.yml`, optional `apm.lock.yaml`, `agents/*.agent.md`, `skills/<slug>/SKILL.md`, `instructions/*.instructions.md`, `workflows/{vsm-*,wf-*}.yaml`, `ontology/glossary.yaml`, `ontology/mechanisms/*.star`, `gates/*.yaml`, `policies/*.policy.md`, `help/{fr,en}/*.md`)
**When** parsed by `ApmPackCodec` (`orcia_core/packs`)
**Then** valid archives produce deterministic canonical `PackManifestV2` structures (`CAP-055` zero new third-party dependencies, `PyYAML` + `Pydantic v2` + stdlib `zipfile`/`ast`), reject zip-slip path traversal / oversize bombs, fail-closed with `HTTP 422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN` (`AD-11` / `A1`) on any hook/script payload (`scripts/`, `hooks:`, executable extensions), and validate Starlark `.star` mechanisms against `AST` constraints (`AD-17` Layer 1/2 PG18 verified).

---

### Story 31.2: Transactional Pack Import Service, Day-0 System Pack Seeding & Purge of Disk/TS Pack Hardcoding (`D1`, `D2`, `D6`, `R1`)

As an ORCIA Platform Engineer and Workspace Lead (`Marc UJ-5`, `Karim UJ-9`),
I want a single transactional `PackImportService` (CAS upload to SeaweedFS + atomic PostgreSQL 18 upsert/version check + Day-0 seeding of `packs/sdlc` & `packs/orcia-docs`) and complete removal of runtime disk/TS pack catalogs (`packAgentsCatalog*.ts`, `_load_all_pack_definitions()`),
So that PostgreSQL 18 + SeaweedFS CAS is the single source of truth for packs, imports reject duplicate `(slug, version)` with `409 ERR_PACK_VERSION_CONFLICT`, and deleting/replacing pack bundles safely respects `run_lock_manifests`.

**Lot:** 2 — Transactional Import, Day-0 Seed & Single PG18 Source of Truth. **Dependencies:** `31.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `D1`, `D2`, `D6`, `R1`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-082`, `CAP-090`, `CAP-140`, `CAP-200`.
**Impacted files:** `packages/orcia-core/src/orcia_core/packs/`, `packages/orcia-core/src/orcia_core/bootstrap/seeder.py`, `infra/scripts/maintenance/09_reset_db_first_boot.py`, `apps/api/src/orcia_api/routers/packs.py`, `apps/api/src/orcia_api/routers/_workflows_helpers.py`, `apps/api/src/orcia_api/schemas/`, `apps/web/src/features/catalog/packAgentsCatalog*.ts` (deleted), `apps/web/src/features/processes/processStudioV2StructuralVsm.ts`, `packages/api-client/src/generated/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-2-transactional-pack-import-day0-seed-and-purge-disk-ts-hardcoding-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `PackImportService` invoked during Day-0 bootstrap (`seeder.py` / `09_reset_db_first_boot.py`) or `POST /api/v1/packs/import` (`.zip` upload or JSON/YAML bundle)
**When** importing a validated bundle inside a single PostgreSQL 18 transaction (paired with SeaweedFS CAS storage of the archive)
**Then** all constituent entities (`agents`, `skills`, `instructions`, `workflows_v2`, `vsm_v2`, `ontology_terms`, `dna_mechanisms`, `policies`, bilingual `help`) upsert idempotently with `pack_bundle_id` set; re-uploading the same `(scope, slug, version)` with a different `archive_sha256` fails with `HTTP 409 ERR_PACK_VERSION_CONFLICT` (unless `replace_draft=true` on a `CUSTOM` draft); deleting an unused bundle cascades cleanly (`ON DELETE CASCADE`), whereas deleting a bundle pinned by an active run fails with `HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` (`R1`).

**Given** a clean Day-0 reset (`pnpm db:reset`) and runtime boot of `apps/api` and `apps/web`
**When** querying pack agents, skills, processes, and VSM definitions
**Then** `packs/sdlc` and `packs/orcia-docs` are served exclusively from PostgreSQL 18 (`packAgentsCatalog.ts`, `packAgentsCatalogData.ts`, and runtime disk scans `_load_all_pack_definitions()` are purged, leaving zero TypeScript-hardcoded pack agent definitions or fallback VSM arrays in `apps/web` or `apps/api`) (`AD-17` Layer 2 PG18 + SeaweedFS verified).

---

### Story 31.3: Qualified `{pack_slug}:{entity_slug}` Namespacing & Flat Priority-Ordered Workspace Pack Ontology (`R3`, `R4`)

As an ORCIA User or Agent Author (`Hélène UJ-1`, `Karim UJ-9`) activating multiple packs in the same workspace,
I want canonical `{pack_slug}:{entity_slug}` identity across agents, skills, workflows, VSMs, and ontology keys (`@pack:agent`, `/pack:skill`) plus flat workspace pack resolution ordered by activation `priority_order` (with `workspace_overrides > priority_order ASC > SYSTEM`),
So that two packs with overlapping entity slugs never collide or silently overwrite each other, while local edits cleanly override without modifying upstream immutable bundles.

**Lot:** 2 — Qualified Namespacing & Flat Pack Resolution. **Dependencies:** `31.2`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `R3`, `R4`.
**CAPs covered:** `CAP-070`, `CAP-082`, `CAP-090`, `CAP-100`, `CAP-140`, `CAP-200`.
**Impacted files:** `packages/orcia-core/src/orcia_core/packs/`, `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`, `packages/orcia-core/src/orcia_core/ontology/`, `apps/api/src/orcia_api/routers/agents_and_skills.py`, `apps/api/src/orcia_api/routers/ontology.py`, `apps/api/src/orcia_api/routers/assistant_workspace_governance.py`, `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-3-qualified-pack-namespacing-and-flat-workspace-pack-ontology-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** two packs installed/activated in a workspace (`sdlc` and `legal-audit`) both declaring an agent or skill named `@reviewer` / `/compliance-check`
**When** persisting, listing, resolving `@` mentions / `/` skills, or executing agent/workflow references
**Then** backend resolution parses canonical `{pack_slug}:{entity_slug}` (`sdlc:reviewer`, `legal-audit:reviewer`), resolves ambiguous unqualified short names deterministically according to flat workspace priority (`workspace_overrides > priority_order ASC > SYSTEM`) or surfaces structured disambiguation candidates without crashing or mutating upstream `pack_bundle_id` rows (`R3`).

**Given** ontology glossary terms, business rules, DNA mechanisms, and pack instructions contributed by activated packs in a workspace
**When** resolving the effective workspace knowledge graph & ontology (`OntologyGovernanceService`, Assistant Layer 2, VSM/Process execution)
**Then** resolution evaluates strictly flat per-workspace activated packs in priority order (`workspace_overrides > priority_order ASC > SYSTEM`) using `DEFERRABLE` priority ordering without pack-to-pack inheritance graphs (`R4`, `AD-17` Layer 2 PG18 verified).

---

### Story 31.4: Workspace-Only Pack Activation, Connector Slot Bindings, `422 ERR_PACK_SLOT_UNBOUND` Gate & `run_lock_manifests` Pinning (`D2`, `D5`, `R2`, `R5`, `A3`)

As an ORCIA Workspace Lead (`Marc UJ-5`, `Sophie UJ-6`),
I want single-truth Workspace Pack Activation (`workspace_pack_activations` at `WORKSPACE` scope only), interactive binding of pack-declared logical connector slots (`git_repo`, `issue_tracker`, `wiki_space`, etc.) to concrete `workspace_datasources` / `enterprise_connectors`, a fail-closed `422 ERR_PACK_SLOT_UNBOUND` guard on activation/run start, and immutable SHA-256 + `resolved_pack_slots` pinning in `run_lock_manifests`,
So that activating or running a pack is deterministic, fail-closed on missing required integrations, and immune to background pack upgrades mid-run.

**Lot:** 3 — Workspace Activation, Slot Bindings & Run Pinning. **Dependencies:** `31.2`, `31.3`. **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) activation/lock contract review.
**Findings covered:** `D2`, `D5`, `R2`, `R5`, `A3`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-082`, `CAP-140`, `CAP-160`.
**Impacted files:** `packages/orcia-core/src/orcia_core/packs/`, `packages/orcia-core/src/orcia_core/orchestration/`, `packages/orcia-core/src/orcia_core/workflows/`, `apps/api/src/orcia_api/routers/packs.py`, `apps/api/src/orcia_api/routers/workflows.py`, `apps/api/src/orcia_api/schemas/packs.py`, `apps/api/src/orcia_api/errors/`, `packages/api-client/src/generated/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-4-workspace-pack-activation-slot-bindings-422-guard-and-run-lock-pinning-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a pack declaring `slots` (required or optional logical capabilities, `connector_types`, `scheme`) and a Workspace Lead enabling or binding slots on a workspace (`POST /api/v1/workspaces/{id}/packs/{slug}/activate`, `PUT /api/v1/workspaces/{id}/packs/{slug}/slots`, `PUT /api/v1/workspaces/{id}/packs/reorder`)
**When** activating a pack or triggering a pack workflow run (`POST /api/v1/workflows-v2/runs`)
**Then** activating a pack or starting a workflow with any **required** slot unbound fails with `HTTP 422 ERR_PACK_SLOT_UNBOUND` listing exact `missing_slots`; successful slot binding writes `workspace_pack_slot_bindings`, emits `audit_ledger` `PACK_SLOTS_BOUND`, allows optional slots (`required: false`) to remain `optional_unbound`, and enforces `ScopeAccessGuard` (`READ_ONLY_OBSERVER` -> `403`, workspace role RBAC).

**Given** a workflow run started inside a workspace with active bound packs (`run_lock_manifests`)
**When** persisting the run lock manifest and later upgrading/deactivating the pack bundle in the workspace
**Then** `run_lock_manifests` records pinned `(bundle_id, slug, version, archive_sha256, resolved_pack_slots)` (`R5`), subsequent workspace pack upgrades/reorders do not mutate already running/paused workflow executions, and `PackBundle` deletion checks reject deleting bundles referenced by live pinned runs (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`, `AD-17` Layer 2 PG18 verified).

---

### Story 31.5: Pack Composer (`CUSTOM` Drafts), Anti-Hostage Unlink Guard, Dependency Closure Gate & PII/Infra-Scrubbed `.zip` Export (`D1`, `D4`, `A2`)

As an ORCIA Team Lead or Pack Author (`Karim UJ-9`, `Marc UJ-5`),
I want to compose custom packs (`CUSTOM` bundles) in PG18 from selected agents, skills, workflows, VSMs, ontology terms, DNA rules, and policies, enforce an anti-hostage guard when deleting member entities, block incomplete exports with `422 ERR_PACK_CLOSURE_INCOMPLETE`, and export deterministic, PII/infra-scrubbed APM `.zip` + `apm.lock.yaml` bundles,
So that teams can package, share, and safely re-import reusable ORCIA business packs without leaking workspace secrets, personal instructions, or broken dependencies.

**Lot:** 4 — Pack Composer, Anti-Hostage & Scrubbed Export. **Dependencies:** `31.1`, `31.4`. **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) export sanitizer & deletion-guard review.
**Findings covered:** `D1`, `D4`, `A2`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-090`, `CAP-140`, `CAP-200`.
**Impacted files:** `packages/orcia-core/src/orcia_core/packs/`, `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`, `apps/api/src/orcia_api/routers/packs.py`, `apps/api/src/orcia_api/routers/agents_and_skills.py`, `apps/api/src/orcia_api/routers/workflows.py`, `apps/api/src/orcia_api/schemas/packs.py`, `packages/api-client/src/generated/`, `tests/integration/`, `tests/security/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-5-pack-composer-anti-hostage-unlink-closure-gate-and-scrubbed-zip-export-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a `CUSTOM` draft pack with selected entities recorded in `pack_draft_memberships` (`ON DELETE RESTRICT`)
**When** a user attempts to delete a member agent, skill, workflow, or VSM via standard entity `DELETE` endpoints
**Then** `DELETE` rejects with `HTTP 409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` listing referencing draft packs; passing explicit confirmation `?unlink_from_draft_packs=true` detaches the draft memberships, logs `PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE` in `audit_ledger`, and completes deletion cleanly (`A2`).

**Given** a pack export request (`POST /api/v1/packs/{bundle_id}/export`)
**When** computing the transitive dependency closure and generating the downloadable APM `.zip` archive (`application/zip` + `apm.yml` + `apm.lock.yaml` + clean asset files)
**Then** any missing cross-reference (`agent` -> missing `skill` / `workflow` -> missing `agent` / missing `ontology` or `policy`) blocks export with `HTTP 422 ERR_PACK_CLOSURE_INCOMPLETE` listing exact missing entities (or includes transitive dependencies when `auto_include_dependencies=true`); PII (`email`, personal instructions), `SecretRef`s, datasource URLs, workspace UUIDs, and model provider keys are strictly scrubbed (`422 ERR_PACK_PII_OR_INFRA_LEAK` if un-scrubbable secret/PII patterns remain in authored text); and re-importing the exported `.zip` into an isolated workspace round-trips `100%` faithfully (`AD-17` Layer 2 PG18 verified).

---

### Story 31.6: Direction C Bilingual FR/EN UI (`Mes Packs`, Slot Binding Drawer, Composer Modal & `@pack:agent` / `/pack:skill` Autocomplete) (`D1`, `D2`, `D5`, `R3`)

As an ORCIA End User and Workspace Lead (`Hélène UJ-1`, `Marc UJ-5`, `Karim UJ-9`),
I want a sober Direction C bilingual (`fr`/`en`) UI for discovering/importing/exporting packs, activating packs per workspace with priority ordering, binding logical connector slots via an interactive Drawer, composing `CUSTOM` packs via a step-by-step Composer modal (including anti-hostage unlink confirmation), and using qualified `@pack:agent` / `/pack:skill` autocomplete cleanly across `Mon Assistant` and `Mes Agents`,
So that the entire declarative APM pack lifecycle works smoothly in the browser, passes `F5` cold reload from PG18, and shows zero raw HTTP errors or dead buttons.

**Lot:** 5 — Direction C Bilingual UI & Full Frontend Wiring. **Dependencies:** `31.4`, `31.5`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `D1`, `D2`, `D5`, `R3`, `A2`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-070`, `CAP-082`, `CAP-090`, `CAP-100`, `CAP-140`, `CAP-200`.
**Impacted files:** `packages/ui/src/components/` (Pack registry table/cards, Slot Binding Drawer, Pack Composer Modal, Unlink confirmation dialog), `apps/web/src/features/packs/` or `settings/` & `workspaces/` & `catalog/`, `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts`, `apps/web/src/i18n/locales/{fr,en}.ts`, `packages/api-client/src/generated/`, `apps/web/src/__tests__/`, `packages/ui/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-6-direction-c-bilingual-pack-registry-composer-slot-drawer-and-autocomplete-ui-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `"Mes Packs"` (Settings Registry & Workspace Tab / Activation view) rendered in `fr` and `en`
**When** importing a `.zip` / YAML pack, activating/reordering workspace packs, binding slots in the Slot Binding Drawer, or creating/exporting a `CUSTOM` pack in the Pack Composer Modal
**Then** all flows strictly use `@orcia/api-client` (zero client business stores or hardcoded TypeScript packs), display inline `[role="alert"]` errors inside drawers/modals (highlighting missing required slots on `422 ERR_PACK_SLOT_UNBOUND` or closure gaps on `422 ERR_PACK_CLOSURE_INCOMPLETE` and prompting explicit unlink confirmation on `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT`), survive full `F5` reload from PG18, obey `@orcia/ui` tokens & `<= 300`-line file modularity, and enforce `READ_ONLY_OBSERVER` read-only disabled controls.

**Given** `@` agent and `/` skill autocomplete in `Mon Assistant` and `Mes Processus` / `Mes Agents` cards
**When** packs with overlapping entity slugs are active in a workspace
**Then** UI badges display clear origin pack attribution + qualified `@pack:agent` / `/pack:skill` insertion on collision (concise friendly display when unique) with `0` console warnings or dead callbacks (`AD-17` Layer 1/3 Vitest + Playwright ready).

---

### Story 31.7: Epic 31 Security Red-Team, Export→Fresh-Workspace Round-Trip E2E, Contextual Help Sync & Closure (`D1`..`D6`, `A1`..`A4`)

As an ORCIA Maintainer, SecOps Reviewer & Product Owner (`Sophie UJ-6`, `Winston`, `Hélène UJ-1`),
I want full security red-team tests (zip-slip, executable hooks, PII/infra leaks, `ScopeAccessGuard` observer/cross-tenant isolation), clean bilingual Playwright Desktop E2E covering import → workspace activate → slot bind → compose → export → fresh-workspace re-import, updated Zone 4 help & architecture spine alignment, and formal `bmad-architect-worker` (`pro`) closure sign-off,
So that Epic 31's declarative APM pack platform ships verified across all 5 `AD-17` layers with zero regressions and `0` debt.

**Lot:** 6 — Security Lock, Round-Trip E2E & Epic 31 Closure. **Dependencies:** `31.6`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory `bmad-architect-worker` (`pro`) final `VALIDATE` gate.
**Findings covered:** `D1`..`D6`, `R1`..`R5`, `A1`..`A4`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-070`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-160`, `CAP-200`, `CAP-260`.
**Impacted files:** `tests/security/`, `tests/evals/`, `apps/web/e2e/31-epic-31-declarative-apm-packs-roundtrip.spec.ts` (new), `docs/help/{fr,en}/*.md`, `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-7-epic-31-red-team-security-roundtrip-e2e-help-sync-and-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the Epic 31 security red-team & bilingual E2E suite (`env -u ORCIA_E2E_SEED_FIXTURES`)
**When** executed against real PostgreSQL 18 + Redis + SeaweedFS containers and running SPA + FastAPI Composition Root
**Then** zip-slip traversal, `.sh`/`.py`/hook executable payloads (`422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN`), PII/secret leaks in export (`422 ERR_PACK_PII_OR_INFRA_LEAK`), cross-workspace pack activation leaks, and `READ_ONLY_OBSERVER` `403` guards all fail closed; Day-0 `pnpm db:reset` boots `packs/sdlc` & `packs/orcia-docs` cleanly from PG18; and bilingual (`fr` & `en`) Desktop Playwright proves end-to-end compose -> export `.zip` -> fresh-workspace import -> slot bind -> `@pack:agent` execution -> `F5` cold reload.

**Given** full `AD-17` 5-layer verification and `bmad-architect-worker` (`pro`) `VALIDATE` review
**When** closing Epic 31
**Then** all production files remain `<= 300` lines, `.venv/bin/ruff check .`, `ruff format --check .`, `mypy --strict`, `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`), `export_openapi.py --check` (`0-diff`), i18n Gates 1–4 (`0`), full `tests/unit` + `tests/evals` + `tests/security` + `tests/contract` + PG18+Redis+SeaweedFS integration (`>= 90%` branch coverage), `pnpm turbo run lint typecheck test`, Playwright Desktop E2E, `scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, and `npx gitnexus analyze` all pass, `CAP-xxx` entries remain `runtime`, `ACTION_ITEM-31.1..31.2` are tracked cleanly, and `epic-31` transitions to `done`.
