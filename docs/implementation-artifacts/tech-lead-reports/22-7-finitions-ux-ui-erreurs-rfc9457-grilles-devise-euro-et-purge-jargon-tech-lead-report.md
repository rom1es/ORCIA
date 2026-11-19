# Story 22.7 — Finitions UX/UI (Compteurs `0`/Modales, Erreurs RFC 9457 Actionnables, Grilles, Studio V2, Assistant/`⌘K`, Devise `€`/Dates FR, Contraste `(!)`) & Purge Intégrale du Jargon Technique

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-7-finitions-ux-ui-erreurs-rfc9457-grilles-devise-euro-et-purge-jargon` (`Epic 22` — Vague 2/3)
- **Capacité(s)** : Amélioration UX/UI transverse (classification `ux`) impactant `CAP-002`, `CAP-003`, `CAP-010`, `CAP-023`, `CAP-030`, `CAP-051`, `CAP-052`, `CAP-054`, `CAP-060`, `CAP-062`, `CAP-065`, `CAP-069`, `CAP-073`, `CAP-075`, `CAP-080`, `CAP-082`, `CAP-083`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-150`, `CAP-160`, `CAP-200`, `CAP-201`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-22`**, **`REM-23`**, **`REM-26`**, **`REM-27`**, **`REM-28`**, **`REM-29`**, **`REM-30`**, **`REM-31`** et **`REM-32`** (`synthese-remediation-sally-winston-epic-21.md`, `notes-audit-sally-ux.md`). Couvre `FR-25`, `FR-26`, `FR-32..FR-36`, `NFR-A11Y-1`, `NFR-OBS-1`, `UX-DR1`, `UX-DR11`, `UX-DR12`, `UJ-1`..`UJ-20`.
- **Commits associés** : `fix(epic-22): story 22.7 - ux polish, actionable rfc9457 banners, euro currency, grids and jargon purge` (sur `feat/epic-22-remediation-pg18-direction-c`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Compteurs `0` & formulaires ouverts en permanence (`REM-22`)** : `/processes`, `/gates`, `/agents`, `/spaces` et `/profile` affichent `Publiés : 0`, `0 Sources`, `0.00 $`, `Total des tokens: 0` et déploient de grands formulaires permanents au-dessus des listes (captures `06-gates`, `07-spaces`, `11-screens-smoke`, `18-catalog`, `19-orchestration` #2).
- **Erreurs HTTP silencieuses ou génériques (`REM-23`)** : `16-ai-models` #3 (`404`), `19-orchestration` #2 (`403`) et `20-process-studio` #2 (`422`) n'affichent aucun bandeau d'erreur actionnable, et `17-workspace` #1 affiche un 404 générique sans nommer la ressource ni proposer de remédiation.
- **Fuites massives de jargon technique & constantes internes (`REM-26`)** : `SYNTHESIS_READY` (`8×` dans `12-epic16`), `OAUTH2_PASSTHROUGH`, `TECH_LEAD`, `IMMUTABLE`, `PAUSE_AND_ESCALATE`, `OPT_A_SPOT_15M`, `OPT_B_LOCK_48H`, `PENDING`, `⚡ Vitesse 2 (450 ms)`, `DeclarativePackLoader`, `orcia-connectors`, `WritePreviewCard`, `packs/<domaine>/`, `YAML + Markdown`, `Agents (.md)`, `Skills (.md)`, `generate-orcia-documentation`, `orcia-pack-builder`, `Tier cognitif`, `Guardrails`, `Anti-Prompt Injection`, `Dry-Run`, `DCP / PII`, `Bloc F`, `AES-256-GCM`, `1024-dim RAG`, `endpoint API`, `demande_source`, `(published)`/`(draft)`, `[STALE_WARNING]`, `human_authored_required`, `Staged`, et routes brutes `/settings`, `/workspaces/$wsId/sources`.
- **Incohérence monétaire `$` / `USD` vs `€` & dates US (`REM-27`)** : `/spaces` affiche `0.00 $` et `19-orchestration` `0.02 USD / run` alors que `/finops` est en `€` ; `/activity` affiche `mm/dd/yyyy` en français.
- **Grilles asymétriques & mises en page Studio / Assistant / `⌘K` (`REM-28`, `REM-29`, `REM-30`, `REM-31`)** :
  - `/finops` KPIs en `3+1` + 4e onglet à la ligne ; `/profile` 4 KPIs en 1 colonne ; `/ontology` grille `3+2`.
  - Studio V2 (`09-pack-builder`, `20-process-studio`) : bouton `Demander` sortant hors carte gauche et version dupliquée (`v1.0.1 v1.0.1`). Sur `/agents` onglet MCP : grand vide blanc à gauche.
  - `/assistant` : `+ Nouvelle conversation` ressemble à du texte brut ; pavé explicatif numéroté en bas de vue ; `⌘K` affiche des titres de catégories vides sous `Aucun résultat trouvé`.
  - Titres numérotés manuels (`1. Annuaire...`, `2. Exceptions...`, `1..4`) et double bordure bleue `||` + Markdown brut monospace dans `12-epic16`.
- **Pastilles rouges `(!)` dans les boutons bleus & troncatures (`REM-32`)** : `DisabledButtonAlertIndicator` rend un rond rouge `(!)` dans les boutons primaires bleus (`00-stack-smoke`, `07-spaces`, `10-command-palette`, `18-catalog` #5 — échec contraste WCAG AA) et sur l'onglet actif de la sidebar ; troncatures `@agent-e2e-conformit` et `<select> Plateforme entière...`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `DisabledButtonAlertIndicator.tsx` (`packages/ui/src/components/`) : `impactedCount=82` (`25` directs, `35` d=2, `22` d=3, `risk=CRITICAL`, `8` modules affectés dont `Primitives`, `Components`, `Inbox`, `Catalog`, `Shell`) — impact transversal sur tous les formulaires à bouton primaire désactivé.
  - `AssistantThinkingSubWindow.tsx` (`packages/ui/src/primitives/`) : `impactedCount=5` (`2` directs, `risk=LOW`, modules `Primitives`, `Inbox`) — point unique de filtrage des événements de trace côté UI (`REM-26`).
  - `WorkflowStudioHeaderBar.tsx` (`apps/web/src/features/processes/studio/`) : `impactedCount=2` (`1` direct `WorkflowFiveBlocksCanvas`, `risk=LOW`).
  - `AgentExecutionTrace.tsx` (`packages/ui/src/components/`) : `impactedCount=24` (`4` directs, `risk=CRITICAL`, `6` modules dont `Routes`, `Primitives`, `Inbox`, `Studio`, `Catalog`, `Execution`).
  - `FinopsGovernanceDashboardView.tsx` (`packages/ui/src/primitives/finops/`) : `impactedCount=16` (`1` direct, `risk=LOW`, modules `Routes`, `Primitives`).
  - Dictionnaires `apps/web/src/i18n/locales/*.ts` (`finops_labels.ts`, `workflow_triggers_labels.ts`, `ai_models_hub_labels.ts`, `epic10_labels.ts`, `epic11_labels.ts`) & `packs/*/help/**/*.md`.
- **Opportunités de Factorisation & Volumétrie** :
  - Créer un formateur partagé `formatCurrency(amount, locale, currency = "EUR")` (`Intl.NumberFormat`) et `formatShortDate(iso, locale)` (`Intl.DateTimeFormat`) dans `packages/ui` ou `apps/web/src/lib/formatters.ts`.
  - Créer un helper centralisé `formatRfc9457ErrorToBanner(error, locale)` traduisant les codes RFC 9457 (`ERR_*`) en message actionnable pour `<OrciaAlertBanner>`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration de schéma requise (lot UX/UI, formatage, dictionnaires `i18n` et gestion d'erreurs).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Vérifier côté flux SSE d'orchestration et trace réflexive (`orcia_core/agents/`) qu'un libellé utilisateur propre accompagne chaque statut interne ou qu'il est mappé côté UI sans fuite `SYNTHESIS_READY`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Vérifier que chaque code RFC 9457 retourné par les routeurs (`403`, `404`, `422`, `409`, `503`) possède une entrée claire en FR/EN dans le catalogue d'erreurs localisé (`Accept-Language`) incluant une piste d'action pour l'utilisateur (`REM-23`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- **Compteurs `0` & Modales (`REM-22`)** : masquer tout badge/compteur tant que `total === 0` (`ProcessesHubPage`, `SpacesFeatureView`, `AgentsAndSkillsManagerView`, `UserProfileOverviewPage`) et déplacer les formulaires permanents de création de processus / d'espace dans des `<OrciaDialog>` déclenchés par `+ Nouveau processus` / `+ Nouvel espace`.
- **Erreurs RFC 9457 (`REM-23`)** : relier toutes les mutations `@orcia/api-client` au helper `formatRfc9457ErrorToBanner` rendant `<OrciaAlertBanner>` (zéro échec API silencieux).
- **Purge Jargon (`REM-26`)** : nettoyer intégralement `i18n/locales/*.ts`, `packs/*/help/**/*.md`, `WorkflowStudioHeaderBar.tsx` et étendre le filtre d'états de `AssistantThinkingSubWindow.tsx` pour traduire `SYNTHESIS_READY`, `PENDING`, `TECH_LEAD`, `IMMUTABLE`, `PAUSE_AND_ESCALATE`, `OPT_A_*`/`OPT_B_*`, `OAUTH2_PASSTHROUGH`, etc. ; supprimer les chemins bruts `/settings`, `packs/<domaine>/`, `YAML + Markdown`, `Tier cognitif`, `Guardrails`, `Dry-Run`, `AES-256-GCM`, `1024-dim RAG`.
- **Devise & Dates (`REM-27`)** : unifier sur `€` (`EUR`) et `Intl.DateTimeFormat(locale)` (`jj/mm/aaaa` en FR) sur `/spaces`, `/activity`, `/finops` et l'arbitrage.
- **Grilles & Mises en page (`REM-28`, `REM-29`, `REM-30`, `REM-31`)** :
  - `FinopsKpiStrip` & `UserProfileOverviewPage` en `grid-cols-1 sm:grid-cols-2 xl:grid-cols-4` ; 4 onglets `/finops` en `flex-nowrap overflow-x-auto` ; `/ontology` en `grid-cols-1 md:grid-cols-2`.
  - Studio V2 : `min-w-0` + wrap propre du bouton `Demander` dans `StudioCopilotSidebar`, suppression du doublon `v1.0.1` dans `WorkflowStudioHeaderBar.tsx`, pleine largeur pour `RemoteServiceTestBenchAndMcpExposureView` sur `/agents`.
  - `/assistant` : style bouton secondaire Direction C pour `+ Nouvelle conversation`, suppression du pavé explicatif central (déporté en fiche `ⓘ`), masquage des catégories vides dans `CommandPaletteModal` (`⌘K`).
  - Suppression des préfixes numériques manuels (`/settings?tab=iam`, `/ontology`), suppression de la double barre `||` et rendu typographique `FormattedMarkdownContent` dans `AgentExecutionTrace` (`12-epic16`).
- **Contraste `(!)` & RGAA (`REM-32`)** : retirer la pastille rouge `(!)` de l'intérieur des boutons primaires et de l'onglet actif sidebar (`DisabledButtonAlertIndicator.tsx` $\rightarrow$ aide sobre sous le bouton ou tooltip), et élargir les conteneurs des badges / `<select>` avec `title` complet.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : tests Vitest vérifiant `€` / dates FR, masquage des compteurs `0`, traduction des statuts dans `AssistantThinkingSubWindow`, absence de `(!)` rouge dans `.orcia-ds-btn-primary`, rendu Markdown dans `AgentExecutionTrace`, et bannières RFC 9457 sur erreurs `403`/`404`/`422`.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`)** : zéro violation `@orcia/ui` isolée.
- **Couche 5 (Playwright E2E)** : vérification visuelle de non-régression sur `00`, `02`, `06`, `07`, `08`, `09`, `10`, `12-epic16`, `12-finops`, `15-org`, `17-workspace`, `18-catalog`, `19-orchestration`, `20-process-studio`, `21-assistant`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/src/lib/formatters.ts` | Création | Formateurs partagés `formatCurrency` (`€`/`EUR`), `formatShortDate` (`jj/mm/aaaa` en FR) et `formatShortDateTime` (`REM-27`). |
| `apps/web/src/lib/formatRfc9457ErrorToBanner.ts` | Création | Traduction structurée de tout `OrciaProblemError` (`ERR_*`) et HTTP `401/403/404/409/422/503` en message métier actionnable FR/EN + remédiation (`REM-23`). |
| `apps/web/src/components/CreateProcessFormDialog.tsx` | Création / Refactoring | Extraction de la modale `<OrciaDialog testId="create-process-modal">` depuis `SimplifiedProcessBuilderSection.tsx` (`REM-22`). |
| `apps/web/src/components/SimplifiedProcessBuilderSection.tsx`, `ProcessCatalogCardGrid.tsx`, `ProcessesHubPage.tsx` | Modification | Masquage des compteurs `0`, bouton `+ Nouveau processus` ouvrant `CreateProcessFormDialog` et bannière `<OrciaAlertBanner role="alert">` sur `/processes` (`REM-22`, `REM-23`). |
| `apps/web/src/features/workspaces/{index,WorkspaceStudioCardsAndDetailView,WorkspaceDnaAndWaiversSection}.tsx` | Modification | Modale `<OrciaDialog testId="create-workspace-modal">` (`+ Nouvel espace`), masquage des compteurs `0`, montants en `€`, bannières RFC 9457 (`REM-22`, `REM-23`, `REM-27`). |
| `apps/web/src/components/{ShellContainer,platformSetupStore,platformSetupGovernanceActions}.tsx/.ts` | Modification | Formatage RFC 9457 de `lastSyncError` et affichage `<OrciaAlertBanner role="alert" testId="platform-sync-error-banner">` dans le Shell (`REM-23`). |
| `apps/web/src/features/{catalog,finops,gates,ontology,cockpit,inbox,processes,shared}/*`, `apps/web/src/routes/SettingsPacksSection.tsx`, `activityFormatters.ts`, `ShellFederatedSearchModal.tsx` | Modification | Câblage RFC 9457 `<OrciaAlertBanner role="alert">` sur toutes les mutations, devise `€` & dates FR, masquage double bordure `||`, `<FormattedMarkdownContent>`, suppression du doublon `v1.0.1` et humanisation trace SSE (`REM-23`, `REM-26`, `REM-27`, `REM-29`, `REM-30`, `REM-31`). |
| `apps/web/src/i18n/locales/*.ts` & `packs/sdlc/help/{fr,en}/spaces-sources.md` | Modification | Purge du jargon technique (`TECH_LEAD`, `[STALE_WARNING]`, `human_authored_required`, `Staged`, `Dry-Run`, `Guardrails`, `Tier cognitif`, etc.) et suppression des numérotations manuelles (`REM-26`, `REM-31`). |
| `packages/ui/src/{components,primitives,shell,styles}/*` | Modification | Retrait du badge rouge `(!)` dans `DisabledButtonAlertIndicator` / `FourZoneSidebarRail`, élargissement des badges/`<select>`, grilles `xl:grid-cols-4` / `md:grid-cols-2` / `flex-nowrap`, masquage des `0` sur `/agents` et `/profile`, masquage des groupes vides `⌘K`, Markdown dans `AgentExecutionTraceItems` et humanisation `AssistantThinkingSubWindow` (`REM-22`, `REM-26`, `REM-28`..`REM-32`). |
| `apps/web/src/__tests__/ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx`, `packages/ui/src/__tests__/*`, `apps/web/src/__tests__/*`, `apps/web/e2e/{support/orgAndWorkspace.ts,06-*,14-*,19-*}` | Création / Réalignement | Nouvelle suite dédiée `ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx` (`5/5` tests), réalignement de `4` tests `@orcia/ui`, `9` suites `@orcia/web` et `4` fichiers E2E Playwright (`toggle-create-workspace-form-btn`, `data-status` + libellés FR Gates, `Alerte d'obsolescence`, `profile-kpis-empty-state`). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests TypeScript / Vitest (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches vertes (`303/303` tests passés)** :
  - `@orcia/api-client` : **`2/2` fichiers (`13/13` tests)**
  - `@orcia/ui` : **`26/26` fichiers (`110/110` tests)**
  - `@orcia/web` : **`45/45` fichiers (`180/180` tests)** dont `ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx` (`5/5` tests).
  - Build production `@orcia/web` (`vite build`) : **OK (`✓ built in 6.05s`, 598 modules)** et `tsc --noEmit --strict` sur les `4` fichiers E2E modifiés : **OK (`0` erreur)**.
- **Tests Python (`timeout --kill-after=5s 300s .venv/bin/pytest tests/unit tests/security tests/evals -q`)** : **`878/878` tests passés (`0` échec, `100 %` vert)**.
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` : **OK (`All checks passed!`)** & `.venv/bin/ruff format --check .` : **OK (`1231 files already formatted`)**.
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : **OK (`Success: no issues found in 511 source files`)**.
  - `.venv/bin/lint-imports` : **OK (`Contracts: 5 kept, 0 broken`)**.
  - `.venv/bin/python scripts/export_openapi.py --check` : **OK (`0-diff`)**.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **OK (`total_findings: 0`, `ok: true`)**.
  - `pnpm site:sync && pnpm site:check` : **OK (`184` rapports, `28` routes, `133` primitives UI, `65/65` capacités live, `62/62` E2E fonctionnels, `20/20` UJ)**.
  - `.venv/bin/python scripts/check_implementation_docs.py` : **OK (`All 184 Tech Lead report(s) comply with standards and are indexed in README.md`)**.
  - `gitnexus_detect_changes({scope: "all", repo: "/home/romain/Documents/Projects/ORCIA"})` : `changed_count: 88`, `affected_count: 0`, `changed_files: 100`, `risk_level: "low"` (index `36,434` nœuds / `63,351` arêtes).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a / 1b (Unitaires & UI Vitest)** :
  - `pnpm turbo run lint typecheck test` (`9/9` tâches, `303/303` tests JS/TS verts) incluant `ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx` (`formatRfc9457ErrorToBanner` sur `403`/`404`/`409`/`422`/`503` + `ERR_*`, rendu `<OrciaAlertBanner role="alert">` sur `/spaces`, `formatCurrency` `€`, `formatShortDate` `jj/mm/aaaa`, modales `<OrciaDialog>`, masquage `0`, purge jargon `AssistantThinkingSubWindow`, Markdown sans `||` dans `AgentExecutionTrace`, masquage groupes vides `⌘K`, absence `(!)` dans `DisabledButtonAlertIndicator`, grille `xl:grid-cols-4`, unicité version Studio V2) et `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
- **Couche 2 (`HTTP ➔ PG18`)** : Pas de nouveau contrat SQL ou route HTTP dans cette Story purement UX/UI ; non-régression vérifiée par les tests PG18 existants de `tests/unit` (`test_story_3_*`, `4_*`, `5_1_*`, `878/878` verts).
- **Couche 3 (Contrats & Architecture)** : `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5 kept`), `ruff`, `mypy --strict`, `lint_spine.py` (`0 findings`), `tsc --noEmit` sur `apps/web/e2e/{support/orgAndWorkspace.ts,06-*,14-*,19-*}` (`0` erreur).
- **Couche 4 & Sécurité** : Couverte par `tests/unit tests/security tests/evals` (`878/878` verts) et vérifications anti-fuite d'enums/codes techniques (`ERR_*`, `READ_ONLY_OBSERVER`, `[STALE_WARNING]`) dans `formatRfc9457ErrorToBanner` et `AssistantThinkingSubWindow`.
- **Couche 5 (Playwright E2E)** : Réalignement complet de `apps/web/e2e/support/orgAndWorkspace.ts` (`toggle-create-workspace-form-btn`), `06-gates-review-and-anti-rubber-stamping.spec.ts` (`data-status` + libellés FR sans jargon), `19-orchestration-whatif-replay-and-gates.spec.ts` (`Alerte d'obsolescence` + `data-status`), et `14-auth-2fa-account-and-profile.spec.ts` (`profile-kpis-empty-state` vs KPIs après F5) ; exécution intégrale de la campagne E2E en Vague 4 dans `Story 22.9`.
