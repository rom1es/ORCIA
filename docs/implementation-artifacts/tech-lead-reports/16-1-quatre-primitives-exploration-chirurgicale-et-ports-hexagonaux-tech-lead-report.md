# Story 16.1 — Ports Hexagonaux & Les 4 Primitives d'Exploration Chirurgicale (`packages/orcia-connectors` & `/api/v1/sources/inspect-lines`)

- **Date** : 2026-11-11
- **Story / Clé Sprint** : `16-1-quatre-primitives-exploration-chirurgicale-et-ports-hexagonaux` (`Epic 16`)
- **Capacité(s)** : `CAP-160` — classification : `feature`
- **Auteur / Contexte** : Core Platform & AI Runtime Team — Implémentation du socle d'exploration chirurgicale par tranches de lignes (`#Lstart-end`, plafond strict `<= 250` lignes) derrière un port hexagonal pur `SurgicalExplorerPort` (`AD-19`, `AD-20`), avec gouvernance anti-*Confused Deputy* `READ_SOURCE` (`FR-20`, `FR-22`), protection Path Traversal / SSRF (`NFR-SEC-1`, `NFR-SEC-4`) et exposition HTTP `/api/v1/sources/inspect-lines` + `/api/v1/sources/surgical-explore` (`CAP-160`).
- **Commits associés** : *(à compléter en Section 3 après commit atomique)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Opportunité métier & technique** : Dans le cadre de l'Epic 16 (*Orchestration Réflexive*), `Mon Assistant`, `Mes Agents` et les *Processus pilotés par l'objectif* doivent pouvoir explorer les sources documentaires, packs déclaratifs et référentiels de l'Espace de manière chirurgicale (vérification d'état, structure hiérarchique, recherche d'extraits, lecture ciblée `#L1-200`) sans saturer la fenêtre de contexte LLM par des fichiers entiers, tout en permettant à l'utilisateur d'inspecter exactement les lignes lues dans `<SourceLineInspectorDrawer />` (Story 16.4).
- **Comportement attendu vs comportement actuel** :
  - Actuellement, les lectures de catalogue ou RAG retournent soit des documents complets, soit des chunks vectoriels fixes sans adressage interactif `#Lstart-end` borné ni primitives d'exploration structurelle unifiées.
  - Le comportement attendu introduit **4 primitives en lecture seule** (`check_resource_state`, `outline_resource_structure`, `search_workspace_snippets`, `inspect_resource_lines`) exposées derrière un port hexagonal pur `SurgicalExplorerPort` dans `packages/orcia-core/src/orcia_core/ports/surgical_explorer_port.py`, implémentées par `SurgicalContextExplorer` dans `packages/orcia-connectors/src/orcia_connectors/surgical.py`, et servies par FastAPI (`GET /api/v1/sources/inspect-lines` et `POST /api/v1/sources/surgical-explore`).
- **Contraintes spécifiques de `ARCHITECTURE-SPINE.md` & Invariants** :
  - **Isolation Hexagonale (`AD-19` Contrats 1..3 & `AD-20` Contrat 4)** : `orcia_core` n'importe jamais `orcia_connectors`, `fastapi`, `sqlalchemy`, `dbos`, `redis`, `dramatiq` ou `litellm`.
  - **Isolation Domaine (`CA-9.1.1` / `test_core_domain_isolation.py`)** : Zéro occurrence des mots-clés SDLC (`jira`, `confluence`, `git_branch`, `wsjf`, `rovo`, `copilot`, `safe`, `prd`) dans `packages/orcia-core/src/orcia_core/`.
  - **Gouvernance `READ_SOURCE` (`CA-16.1.2`)** : Si l'appelant ne dispose pas de l'habilitation `READ_SOURCE` sur la ressource ou l'espace (ou si la ressource est `CONFIDENTIAL_RESTRICTED` / masquée par le *Permission Broker*), aucune ligne source ne fuite (`lines=[]`, `snippets=[]`, `outline=[]`) ; l'explorateur retourne une observation gouvernée avec `redacted=True`, `redacted_reason="READ_SOURCE_REQUIRED"` et `permission_request_hint`.
  - **Sécurité Path Traversal & SSRF** : Interdiction stricte de `..`, octets nuls `\x00`, chemins absolus hors racines autorisées (`packs/`, `docs/`, `specs/` ou schémas virtuels enregistrés `pack://`, `catalog://`, `orcia://`), et rejet systématique des cibles SSRF Cloud Metadata (`169.254.169.254`, `169.254.0.0/16`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200`) via `ValidationDomainError` / `PolicyDeniedError` (enveloppe **RFC 9457 Problem Details** avec `trace_id`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `gitnexus_query("PermissionBroker READ_SOURCE is_safe_llm_endpoint_url ports connectors dependencies")` : identifie les chaînes d'inspection existantes `proc_1002_inspect_catalog_reso` (`inspect_catalog_resource` dans `org_and_workspaces.py:L91-116`) et `proc_995_get_catalog_resource` (`get_catalog_resource_source` dans `org_and_workspaces.py:L125-147`), ainsi que le garde-fou SSRF `is_safe_llm_endpoint_url` (`assistant_llm_providers.py:L57-77`).
  - `gitnexus_context({name: "is_safe_llm_endpoint_url"})` : confirme les hôtes bloqués (`169.254.169.254`, `100.100.100.200`, `metadata.google.internal`, IPv4/IPv6 link-local `fe80::/10`). Nous implémentons un garde SSRF/URI autonome sans dépendance `orcia_api` dans `orcia_connectors/surgical.py`.
  - `gitnexus_impact({target: "MatrixPermissionEvaluator", direction: "upstream"})` : `impactedCount: 17` (`d=1: 8`, `d=2: 5`, `d=3: 4`), risque `MEDIUM` — nous consommons `MatrixPermissionEvaluator` et `PermissionBrokerService` en lecture seule via injection de callback/politique dans `apps/api/src/orcia_api/dependencies/workspace_and_packs.py`, sans modifier la signature de `MatrixPermissionEvaluator`.
- **Exploration & Chiffres Clés (Volumétrie des fichiers touchés)** :
  - `packages/orcia-core/src/orcia_core/ports/__init__.py` : `18` lignes.
  - `packages/orcia-connectors/src/orcia_connectors/__init__.py` : `97` lignes.
  - `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` : `385` lignes $\rightarrow$ **ne pas alourdir ce fichier** ; nous plaçons le fournisseur `get_surgical_explorer_service` dans `apps/api/src/orcia_api/dependencies/workspace_and_packs.py` (`106` lignes actuellement).
  - `apps/api/src/orcia_api/main.py` : `106` lignes.
  - Tous les nouveaux fichiers créés respecteront strictement la limite `< 350` lignes par fichier.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Factorisation du badge normalisé par extension (`M↓`, `Y`, `TS`, `PY`, `JSON`, `SQL`, `DOC`) et du formatage `Analyzed {badge} {filename} #L{start}-{end}` directement dans l'adaptateur `orcia_connectors/surgical.py` avec contrat typé `SurgicalFileBadgeCode` dans `orcia_core/ports/surgical_explorer_port.py`, afin que `NonDeterministicReflexiveRuntime` (Story 16.2) et `<SourceLineInspectorDrawer />` (Story 16.4) consomment exactement la même structure sans re-parsing côté UI.
  - Enregistrement explicite de `PolicyDeniedError` dans `DOMAIN_ERROR_CLASSES` (`apps/api/src/orcia_api/errors/registry.py`) pour garantir une résolution HTTP `403 ERR_POLICY_DENIED` directe et homogène en RFC 9457.
  - Aucun ticket de dette technique supplémentaire requis : le découpage modulaire `< 350` lignes est respecté nativement sur chaque couche.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- **Aucune migration Alembic requise pour la Story 16.1** : les 4 primitives d'exploration chirurgicale opèrent en lecture seule gouvernée sur les référentiels déclaratifs (`packs/`, `docs/`, `specs/`) et les ressources résolues (`pack://`, `catalog://`, `orcia://`), sans écriture transactionnelle SQL additionnelle.

### 2.2 Noyau Métier Hexagonal & Connecteurs (`packages/orcia-core/`, `packages/orcia-connectors/`)
- **`packages/orcia-core/src/orcia_core/ports/surgical_explorer_port.py`** (et ré-export dans `orcia_core/ports/__init__.py`) :
  - `MAX_SURGICAL_LINES: Final[int] = 250`.
  - `SurgicalPrimitiveName(StrEnum)` : `CHECK_RESOURCE_STATE = "check_resource_state"`, `OUTLINE_RESOURCE_STRUCTURE = "outline_resource_structure"`, `SEARCH_WORKSPACE_SNIPPETS = "search_workspace_snippets"`, `INSPECT_RESOURCE_LINES = "inspect_resource_lines"`.
  - `SurgicalFileBadgeCode = Literal["M↓", "Y", "TS", "PY", "DOC", "JSON", "SQL"]`.
  - Modèles Pydantic v2 (`ConfigDict(extra="forbid")`) :
    - `SurgicalLineEntry(line_number: int, content: str)`
    - `SurgicalOutlineNode(kind: str, title: str, line_number: int, level: int = 1)`
    - `SurgicalSnippetMatch(resource_uri: str, display_filename: str, file_badge_code: SurgicalFileBadgeCode, start_line: int, end_line: int, excerpt: str)`
    - `SurgicalObservation` regroupant `kind`, `resource_uri`, `display_filename`, `file_badge_code`, `formatted_badge`, `exists`, `start_line`, `end_line`, `total_lines`, `lines`, `outline`, `snippets`, `check_label`, `summary`, `sha256`, `redacted: bool = False`, `redacted_reason: str | None = None`, `permission_request_hint: str | None = None`.
  - `@runtime_checkable class SurgicalExplorerPort(Protocol)` exposant `async def execute_primitive(...) -> SurgicalObservation` et `async def inspect_lines(...) -> SurgicalObservation`.
  - Zéro dépendance externe interdite et zéro terme métier interdit par `test_core_domain_isolation.py`.
- **`packages/orcia-connectors/src/orcia_connectors/surgical.py`** (+ sous-module d'extraction/sécurité si nécessaire pour rester `< 350` lignes, et export dans `orcia_connectors/__init__.py`) :
  - `SurgicalContextExplorer` implémentant `SurgicalExplorerPort` :
    1. **Validation URI, Anti-Traversal & Anti-SSRF** : rejet de `..`, `\x00`, URLs `http(s)://` vers IP link-local / Cloud Metadata (`169.254.169.254`, `169.254.0.0/16`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200`), `file://` arbitraires et chemins absolus hors racines autorisées (`packs/`, `docs/`, `specs/`, ou racines injectées, ainsi que `pack://<slug>/...`, `catalog://...`, `orcia://...`). Lève `ValidationDomainError` (`422`) ou `PolicyDeniedError` (`403`).
    2. **Gouvernance `READ_SOURCE`** : accepte à la fois un flag d'appel `has_read_source: bool` et un callback de politique optionnel `read_source_authorizer(uri, workspace_id, actor_id) -> tuple[bool, str | None]`. En cas de refus, retourne immédiatement un `SurgicalObservation` masqué (`redacted=True`, `redacted_reason="READ_SOURCE_REQUIRED"`, `lines=[]`, `outline=[]`, `snippets=[]`, `sha256=None`, `permission_request_hint=...`).
    3. **`check_resource_state`** : vérifie l'existence, calcule `sha256` et `total_lines`, et peuple `check_label` + `summary`.
    4. **`outline_resource_structure`** : extrait sans regex catastrophique les titres Markdown (`#`..`####`), les clés YAML/JSON de 1er et 2e niveau, et les déclarations `class`/`def`/`async def`/`function`/`export` Python/TypeScript avec numéros de lignes exacts (1-indexés).
    5. **`search_workspace_snippets`** : recherche littérale / sous-chaîne insensible à la casse (zéro ReDoS, complexité linéaire $O(N)$, résultats plafonnés par `max_results <= 50`) sur les fichiers texte autorisés du périmètre, retournant des `SurgicalSnippetMatch` numérotés `#Lstart-end`.
    6. **`inspect_resource_lines`** : lecture 1-indexée inclusive plafonnée à `MAX_SURGICAL_LINES = 250` (`actual_end = min(total_lines, start_line + 249, end_line)`), calcul du badge (`M↓`, `Y`, `TS`, `PY`, `JSON`, `SQL`, `DOC`) et `formatted_badge = f"Analyzed {badge} {filename} #L{actual_start}-{actual_end}"`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **`apps/api/src/orcia_api/schemas/reflexive_execution.py`** :
  - DTOs HTTP Pydantic v2 (`ConfigDict(extra="forbid")`) : `SurgicalLineEntrySchema`, `SurgicalOutlineNodeSchema`, `SurgicalSnippetMatchSchema`, `SurgicalInspectLinesResponse`, `SurgicalExploreRequest`, `SurgicalExploreResponse`.
  - Ajout de `"reflexive_execution"` dans `SCHEMA_DOMAIN_MODULES` de `scripts/export_openapi.py`.
- **`apps/api/src/orcia_api/dependencies/workspace_and_packs.py` & `__init__.py`** :
  - Fournisseur `get_surgical_explorer_service(request: Request) -> SurgicalExplorerPort` attaché à `request.app.state.surgical_explorer_service` (zéro singleton d'import `_DEFAULT_*`).
- **`apps/api/src/orcia_api/routers/sources_surgical.py`** (monté dans `apps/api/src/orcia_api/main.py`) :
  - `GET /api/v1/sources/inspect-lines` (`uri`, `start_line: int = 1`, `end_line: int = 200`, `workspace_id: str | None = None`, `persona_key: str | None = None`) : résout le contexte d'habilitation `READ_SOURCE` (utilisateur authentifié / ACL catalogue `evaluate_catalog_resource` / workspace `CONFIDENTIAL_RESTRICTED` / en-tête de simulation ou restriction `X-Orcia-Read-Source: denied` en test/local), appelle `explorer.inspect_lines(...)` et renvoie `SurgicalInspectLinesResponse` avec `trace_id`.
  - `POST /api/v1/sources/surgical-explore` : exécute l'une des 4 primitives en lecture seule via `explorer.execute_primitive(...)` et renvoie `SurgicalExploreResponse`.
  - Enregistrement de `PolicyDeniedError` dans `apps/api/src/orcia_api/errors/registry.py`.
- **`packages/api-client/`** :
  - Régénération déterministe via `.venv/bin/python scripts/export_openapi.py` produisant `openapi.json`, `src/generated/schema.ts` et le nouveau shard `src/generated/reflexive_execution.ts` (`--check` à `0-diff`).
- **`docs/product/capabilities.yaml`** :
  - Mise à jour de `CAP-160` (`status: partial`, ajout de `api: "/api/v1/sources/inspect-lines + /api/v1/sources/surgical-explore (sources_surgical.py)"` dans `surfaces` et référencement des suites de tests).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Pas de nouveau composant React dans la Story 16.1 (`<AgentExecutionTrace />` et `<SourceLineInspectorDrawer />` sont planifiés en Story 16.4).
- Enrichissement de `apps/web/e2e/00-stack-smoke.spec.ts` pour valider de bout en bout à travers le proxy Vite $\rightarrow$ FastAPI de la pile E2E réelle (`PG18 + Redis + FastAPI`) l'inspection chirurgicale `GET /api/v1/sources/inspect-lines?uri=docs/product/capabilities.yaml&start_line=1&end_line=40` (`200 OK`, `40` lignes, badge `Y`) et le blocage RFC 9457 de `../`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Unitaires Python `tests/unit/`)** :
  - `tests/unit/connectors/test_surgical_context_explorer.py` : test des 4 primitives, plafonnement strict à `250` lignes, badges `M↓`/`Y`/`TS`/`PY`/`JSON`/`SQL`/`DOC`, conformité `isinstance(explorer, SurgicalExplorerPort)`, masquage `READ_SOURCE` (`redacted=True`, `0` ligne fuitée) et rejets Path Traversal / SSRF.
  - `tests/unit/core/test_core_domain_isolation.py` & `tests/unit/test_codebase_architectural_anti_patterns_audit.py` : non-régression stricte d'isolation domaine et AST.
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18` `tests/integration/`)** :
  - `tests/integration/api/test_story_16_1_sources_surgical_api.py` : test vertical `AsyncClient` + conteneur réel PostgreSQL 18 (`testcontainers-python`) sur `GET /api/v1/sources/inspect-lines` (`docs/product/capabilities.yaml` `#L1-50`, `packs/sdlc/pack.yaml`), `POST /api/v1/sources/surgical-explore`, vérification SQL `SELECT` sur PostgreSQL 18, enveloppes RFC 9457 (`application/problem+json` + `trace_id`) et masquage `READ_SOURCE` sur ressource boîte noire (`res-blackbox-security-agent` / `READ_SOURCE` refusé).
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff`, `lint-imports` & `lint_spine.py`)** :
  - `.venv/bin/python scripts/export_openapi.py --check`, `.venv/bin/lint-imports` (`5 contracts kept, 0 broken`), `lint_spine.py` (`0 findings`).
- **Couche 4 (Evals IA)** : Aucune régression LLM (`0 $` appel externe).
- **Couche Sécurité / Red-Team** : Validation anti-*Confused Deputy* (`READ_SOURCE`), rejet Path Traversal (`../`, octets nuls, chemins absolus externes) et rejet SSRF (`169.254.169.254`, `fe80::1`, `metadata.google.internal`, `100.100.100.200`).
- **Couche 5 (E2E Navigateur Playwright Bi-Serveur)** :
  - Exécution réelle de `apps/web/e2e/00-stack-smoke.spec.ts` (`--project=desktop-cockpit`) vérifiant `GET /api/v1/sources/inspect-lines` via le proxy Vite $\rightarrow$ FastAPI sur la pile E2E réelle.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/ports/surgical_explorer_port.py` | Création (`135` lignes) | Port hexagonal pur `@runtime_checkable class SurgicalExplorerPort(Protocol)`, constante `MAX_SURGICAL_LINES = 250`, énumération `SurgicalPrimitiveName` et modèles Pydantic v2 stricts (`ConfigDict(extra="forbid")`) `SurgicalLineEntry`, `SurgicalOutlineNode`, `SurgicalSnippetMatch`, `SurgicalObservation`. |
| `packages/orcia-core/src/orcia_core/ports/__init__.py` | Modification (`37` lignes) | Ré-export public de `SurgicalExplorerPort` et des contrats de l'exploration chirurgicale. |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_models.py` | Modification (correctif isolation) | Remplacement de clés d'outils MCP par défaut par des identifiants agnostiques afin de maintenir `0` fuite de vocabulaire métier dans `orcia_core`. |
| `packages/orcia-connectors/src/orcia_connectors/_surgical_parsers.py` | Création (`264` lignes) | Garde-fous de sécurité URI (rejet octets nuls, `..`, `file://`, SSRF `169.254.169.254` / `fe80::/10` / `metadata.google.internal` / `100.100.100.200`), résolution de badges (`M↓`, `Y`, `TS`, `PY`, `JSON`, `SQL`, `DOC`) et extracteurs d'outline structurel (`MD`, `YAML`, `JSON`, `PY` AST + fallback, `TS`). |
| `packages/orcia-connectors/src/orcia_connectors/_surgical_observations.py` | Création (`185` lignes) | Constructeurs purs de `SurgicalObservation` (état SHA-256, outline, tranche 1-indexée plafonnée à `250` lignes, extraits contextualisés `#Lstart-end` et observation masquée `READ_SOURCE_REQUIRED`). |
| `packages/orcia-connectors/src/orcia_connectors/surgical.py` | Création (`322` lignes) | Adaptateur gouverné `SurgicalContextExplorer` implémentant les 4 primitives en lecture seule non bloquante (`asyncio.to_thread`) sur les racines autorisées (`packs`, `docs`, `specs` + URI virtuelles `pack://` / Catalogue). |
| `packages/orcia-connectors/src/orcia_connectors/__init__.py` | Modification | Export public de `SurgicalContextExplorer` et de ses utilitaires de parsing/sécurité. |
| `apps/api/src/orcia_api/schemas/reflexive_execution.py` | Création (`88` lignes) | DTOs OpenAPI 3.1 stricts (`SurgicalExploreRequest`, `SurgicalObservationResponse`, `SurgicalLineResponse`, `SurgicalOutlineNodeResponse`, `SurgicalSnippetResponse`). |
| `apps/api/src/orcia_api/routers/sources_surgical.py` | Création (`156` lignes) | Routeur FastAPI exposant `GET /api/v1/sources/inspect-lines` et `POST /api/v1/sources/surgical-explore` avec vérification d'authentification et propagation `READ_SOURCE`. |
| `apps/api/src/orcia_api/dependencies/workspace_and_packs.py` & `__init__.py` | Modification (`176` lignes) | Injection Composition Root `get_surgical_explorer_service` branchée sur le Catalogue fédéré et la matrice RBAC (`CONFIDENTIAL_RESTRICTED`, `READ_SOURCE`). |
| `apps/api/src/orcia_api/errors/registry.py` & `apps/api/src/orcia_api/main.py` | Modification | Enregistrement de `PolicyDeniedError` dans le registre RFC 9457 et montage de `sources_surgical_router`. |
| `scripts/export_openapi.py`, `packages/api-client/src/generated/reflexive_execution.ts`, `packages/api-client/src/domains/reflexiveExecution.ts`, `packages/api-client/src/index.ts` | Modification / Création | Shard OpenAPI `reflexive_execution` régénéré (`0-diff`) et client TypeScript typé (`inspectSourceLines`, `executeSurgicalPrimitive`). |
| `tests/unit/connectors/test_surgical_context_explorer.py` & `tests/unit/core/test_core_domain_isolation.py` | Création (`367` lignes) / Modification | Tests unitaires exhaustifs des 4 primitives, du plafond `250` lignes, du masquage `READ_SOURCE`, des garde-fous Path Traversal/SSRF et ajout de `orcia_core/ports` au périmètre d'isolation domaine. |
| `tests/integration/api/test_story_16_1_sources_surgical_api.py` | Création (`253` lignes) | Tests d'intégration verticaux FastAPI + PostgreSQL 18 (`testcontainers`) vérifiant `GET /inspect-lines`, `POST /surgical-explore`, enveloppes RFC 9457 (`trace_id`) et masquage `READ_SOURCE`. |
| `apps/web/e2e/00-stack-smoke.spec.ts` & `docs/product/capabilities.yaml` | Modification | Validation E2E Playwright réelle via le proxy Vite $\rightarrow$ FastAPI sur la pile complète et mise à jour de `CAP-160` (`status: partial`, `surfaces.api` et `tests`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie maîtrisée** : tous les fichiers applicatifs créés sont strictement `< 350` lignes (`surgical_explorer_port.py`: `135` l., `_surgical_observations.py`: `185` l., `_surgical_parsers.py`: `264` l., `surgical.py`: `322` l., `reflexive_execution.py`: `88` l., `sources_surgical.py`: `156` l.).
- **Couverture unitaire Story 16.1** : **`92.44 %`** (`>= 90 %` requis ; `surgical_explorer_port.py` : `100 %`, `_surgical_observations.py` : `100 %`, `_surgical_parsers.py` : `95 %`).
- **Analyse statique & frontières hexagonales** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **`0` erreur** (`670` fichiers conformes).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : **`0` erreur** sur `273` fichiers sources.
  - `.venv/bin/lint-imports` : **`5 contracts kept, 0 broken`**.
  - `.venv/bin/python scripts/export_openapi.py --check` : **`0-diff`**.
  - `lint_spine.py` : **`0` finding** (`ok: true`).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a & 1b (Unitaires Python & TypeScript/Vitest)** :
  - Python : `13 passed` sur les suites d'isolation domaine (`test_core_domain_isolation.py`), anti-patterns AST (`test_codebase_architectural_anti_patterns_audit.py`) et exploration chirurgicale (`test_surgical_context_explorer.py`, couverture `92.44 %`).
  - TypeScript Monorepo (`pnpm turbo run lint typecheck test`) : **`9/9` tâches vertes** (`53 passed` dans `@orcia/web`).
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18`)** :
  - `.venv/bin/pytest tests/integration/api/test_story_16_1_sources_surgical_api.py` : **`2 passed`** contre un conteneur éphémère réel `pgvector/pgvector:pg18` (`SELECT current_setting('server_version_num') >= 180000`), validant le plafonnement à `250` lignes, les 4 primitives, le masquage `READ_SOURCE` (`redacted=True`, `lines=[]`) et les rejets RFC 9457 (`422 ERR_VALIDATION_FAILED`, `403 ERR_POLICY_DENIED`).
- **Couche 3 & Sécurité** : Contrats OpenAPI 3.1 `0-diff`, `lint-imports` (`5/5`) et blocage systématique des vecteurs Path Traversal (`../`, `%2e%2e`, `\x00`, `/etc/passwd`, `file://`) et SSRF (`169.254.169.254`, `fe80::1`, `metadata.google.internal`, `100.100.100.200`).
- **Couche 5 (Playwright E2E Réel Bi-Serveur)** :
  - `pnpm --filter @orcia/web exec playwright test e2e/00-stack-smoke.spec.ts --project=desktop-cockpit` : **`3 passed (26.1s)`** sur la pile réelle PostgreSQL 18 + Redis 7.4 + Alembic `head` + FastAPI + Vite + Chromium, confirmant `200 OK` (`40` lignes, badge `Y`) sur `/api/v1/sources/inspect-lines` et `422 application/problem+json` sur `../pyproject.toml`.
- **Audit GitNexus Post-Implémentation** :
  - `npx gitnexus analyze` (`21,006` nœuds, `35,681` arêtes).
  - `gitnexus_impact({target: "SurgicalContextExplorer", direction: "upstream"})` : `impactedCount = 4` (`>= 1` hors `tests/`, zéro adaptateur orphelin).
  - `gitnexus_detect_changes({scope: "all"})` : `changed_files = 16`, `changed_count = 26`, `affected_count = 112` (montage propre dans `create_app`).
