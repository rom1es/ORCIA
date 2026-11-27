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
