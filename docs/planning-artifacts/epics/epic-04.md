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
