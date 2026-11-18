# Story 22.2 — Portals Modales `OrciaDialog`, Compilation Tailwind v4, Purge `display: none`, Découplage `/catalog`/`/agents`/`/help`, Bouton Invitation & Alignement `data-testid`/Contrats

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-2-portals-orciadialog-tailwind-purge-display-none-decouplage-routes-et-contrats` (`Epic 22` — Vague 0)
- **Capacité(s)** : `CAP-001`, `CAP-002`, `CAP-010`, `CAP-041`, `CAP-051`, `CAP-052`, `CAP-053`, `CAP-054`, `CAP-058`, `CAP-063`, `CAP-064`, `CAP-066`, `CAP-069`, `CAP-081`, `CAP-082`, `CAP-084`, `CAP-092`, `CAP-140`, `CAP-190`, `CAP-200`, `CAP-203` (ancrages `failed_e2e` sur `22-2`) — classification : `feature`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-03`**, **`REM-04`**, **`REM-05`**, **`REM-06`**, **`REM-16`**, **`REM-24`** et **`REM-25`** (`synthese-remediation-sally-winston-epic-21.md`). Couvre `FR-1`, `FR-3`, `FR-8`, `FR-20`, `FR-21`, `FR-29`, `FR-31`, `FR-32`, `FR-34`, `FR-35`, `AD-22`, `UX-DR1`, `UX-DR16`, `UJ-5`, `UJ-9`, `UJ-10`, `UJ-11`, `UJ-12`, `UJ-13`, `UJ-14`, `UJ-15`, `UJ-16`, `UJ-18`, `UJ-19`, `UJ-20`.
- **Commits associés** : `En attente d'implémentation (initialisé sur 575cf4a)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Absence de React Portal, Tailwind CSS v4 non compilé & footer coupé (`REM-03`, `3` timeouts + modale `AI` coupée)** :
  - `apps/web/vite.config.ts:11` ne déclare que `[react()]` sans `@tailwindcss/vite` ni PostCSS ; `main.tsx:1` n'importe que `@orcia/ui/styles/tokens.css` (dont les `z-*` s'arrêtent à `.z-40`). Toutes les classes `.z-50`, `.h-[580px]`, `.max-w-[820px]`, `.w-52` de `UserSettingsModalDialog.tsx:138-186` sont des no-ops CSS.
  - `UserSettingsModalDialog` rend un `<div role="dialog">` inline à l'intérieur de `<aside data-testid="four-zone-sidebar">` (`ShellSidebarAccountControl.tsx:73` $\rightarrow$ `FourZoneSidebarRail.tsx:210`) au lieu de passer par `OrciaDialog` (`DialogPrimitive.Portal`). Sur Desktop `1440×900`, Zone 4 (`four-zone-contextual-help-column` en `position: sticky`) se peint **par-dessus** la modale et coupe son bouton `X` et ses contrôles droits (`14-auth` #2 et `16-ai-models` #2 expirent à `35 s`, alors que Mobile où Zone 4 est fermée passe en `9,8 s`).
  - `AiModelConfigModal` déborde verticalement hors de `900 px` sans zone scrollable interne ni footer sticky (`tokens.css:829-847`), et affiche une erreur rouge de clé API avant même toute saisie ou soumission.
- **Purge des `4` wrappers toxiques `style={{ display: "none" }}` (`REM-04`, `2` fails + masquages)** :
  - Pour contourner l'audit `zero-dead-buttons-and-silent-catches-audit.test.tsx:170-194`, `4` fichiers masquent des vues via `display: none` (`features/catalog/index.tsx:176-229`, `features/workspaces/index.tsx:194-409`, `InboxAuxiliaryPanels.tsx:141-214`, `FourZoneSidebarRail.tsx:189-198`), rendant `dna-starlark-glossary-view` `hidden` (`17-workspace` #3) et conservant `activeWaivers` en `useState` local.
- **Découplage `/catalog` vs `/agents` & suppression du doublon DOM `remote-service-test-bench` (`REM-05`, `4` fails)** :
  - `router.tsx:85-92` pointe `/catalog` et `/agents` sur le même `CatalogFeaturePanel` qui affiche `Mes Agents` en premier et cache `catalog-explorer-panel` (`18-catalog` #1 `hidden`).
  - `/agents` onglet `Serveurs d'outils & MCP` monte deux instances de `RemoteServiceTestBenchAndMcpExposureView` (`18-catalog` #5 strict mode violation `2 elements`).
- **Suppression du double montage `/help` & accordéon mobile (`REM-06`, `2` fails)** :
  - Sur `/help`, `routes/help.tsx:45` monte `HELP_MENU_CENTER` pendant que `ShellContainer.tsx:250` garde Zone 4 (`COLUMN_340PX`) active (`21-assistant` #2 Desktop strict mode violation `2` `contextual-help-hybrid-panel`), et sur Mobile `help-accordion-steps-btn` n'ouvre pas `help-accordion-steps-content` (avec puces `•` rognées à gauche).
- **Bouton d'invitation masqué sur `/organization` (`REM-16`, `4` timeouts `35 s`)** :
  - `SettingsOrganizationUnitsBlock.tsx:56-58,86` masque complètement `open-invite-org-user-modal-btn` tant que `invitableUnits.length === 0`.
- **Désalignement `data-testid` (`REM-24`, `4` timeouts `35 s`) & contrat JSON `SecretInputPayload` (`REM-25`, `2` fails `422`)** :
  - `settingsAiModelsPresets.ts:50` utilise `id: "local-ollama"` (`llm-provider-preset-local-ollama` vs attendu `llm-provider-preset-ollama`), `WorkflowStudioHeaderBar.tsx:153,162` utilise `key: "what_if"` (`studio-view-mode-what_if` vs attendu `studio-view-mode-whatif`), et `20-process-studio.spec.ts:153` envoie `value` au lieu de `plaintext_value` sur `SecretInputPayload` (`extra="forbid"`, `HTTP 422`).
- **Échecs E2E associés & captures PNG archivées (`21` échecs/timeouts E2E couverts)** :
  - `14-auth` #1 & #2 (`4` timeouts) : [Invite Desktop](../e2e-campaign-epic-21/screenshots/14-auth-2fa-account-and-profile/desktop-cockpit--mot-de-passe-temporaire-d-un-compte-invite-force-le-renouvellement-et-persiste-dans-user--timedOut.png) · [Invite Mobile](../e2e-campaign-epic-21/screenshots/14-auth-2fa-account-and-profile/mobile-companion--mot-de-passe-temporaire-d-un-compte-invite-force-le-renouvellement-et-persiste-dans-user--timedOut.png) · [Account Desktop](../e2e-campaign-epic-21/screenshots/14-auth-2fa-account-and-profile/desktop-cockpit--popup-mon-compte-parametres-5-onglets-cle-ide-mcp-et-page-profil-survivent-a-un-f5--timedOut.png) · [Account Mobile](../e2e-campaign-epic-21/screenshots/14-auth-2fa-account-and-profile/mobile-companion--popup-mon-compte-parametres-5-onglets-cle-ide-mcp-et-page-profil-survivent-a-un-f5--timedOut.png)
  - `15-org` #3 (`2` timeouts) : [Desktop](../e2e-campaign-epic-21/screenshots/15-organization-iam-secops-inbox-and-observer/desktop-cockpit--mode-observateur-en-lecture-seule-rejette-toute-mutation-en-http-403-err-observer-mode-r--timedOut.png) · [Mobile](../e2e-campaign-epic-21/screenshots/15-organization-iam-secops-inbox-and-observer/mobile-companion--mode-observateur-en-lecture-seule-rejette-toute-mutation-en-http-403-err-observer-mode-r--timedOut.png)
  - `16-ai-models` #1 & #2 (`3` timeouts) : [Models Desktop](../e2e-campaign-epic-21/screenshots/16-ai-models-reindex-connectors-and-broker/desktop-cockpit--jour-0-sans-embedding-garde-ssrf-modeles-chat-embedding-1024-et-reindexation-survivent-a--timedOut.png) · [Models Mobile](../e2e-campaign-epic-21/screenshots/16-ai-models-reindex-connectors-and-broker/mobile-companion--jour-0-sans-embedding-garde-ssrf-modeles-chat-embedding-1024-et-reindexation-survivent-a--timedOut.png) · [Connectors Desktop](../e2e-campaign-epic-21/screenshots/16-ai-models-reindex-connectors-and-broker/desktop-cockpit--connecteur-socle-secret-write-only-et-jeton-passthrough-personnel-persistent-apres-f5--timedOut.png)
  - `17-workspace` #3 (`2` fails) : [Desktop](../e2e-campaign-epic-21/screenshots/17-workspace-sources-codegraph-dna-and-ontology/desktop-cockpit--chaine-adn-starlark-derogations-d-espace-et-graphe-tripartite-rag-persistent-en-base-apr--failed.png) · [Mobile](../e2e-campaign-epic-21/screenshots/17-workspace-sources-codegraph-dna-and-ontology/mobile-companion--chaine-adn-starlark-derogations-d-espace-et-graphe-tripartite-rag-persistent-en-base-apr--failed.png)
  - `18-catalog` #1 & #5 (`4` fails) : [Catalog Desktop](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/desktop-cockpit--explorateur-du-catalogue-federe-droits-granulaires-et-definitions-persistent-en-base-apr--failed.png) · [Catalog Mobile](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/mobile-companion--explorateur-du-catalogue-federe-droits-granulaires-et-definitions-persistent-en-base-apr--failed.png) · [Bench Desktop](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/desktop-cockpit--banc-de-test-connecteur-distant-trace-audit-ledger-et-exposition-gouvernee-mcp-survivent--failed.png) · [Bench Mobile](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/mobile-companion--banc-de-test-connecteur-distant-trace-audit-ledger-et-exposition-gouvernee-mcp-survivent--failed.png)
  - `20-process-studio` #1 & #2 (`4` fails/timeouts) : [WhatIf Desktop](../e2e-campaign-epic-21/screenshots/20-process-studio-v2-finops-and-log-sink/desktop-cockpit--catalogue-agents-avec-pont-assistant-chaine-de-valeur-studio-cinq-blocs-tiroir-hitl-et-s--timedOut.png) · [WhatIf Mobile](../e2e-campaign-epic-21/screenshots/20-process-studio-v2-finops-and-log-sink/mobile-companion--catalogue-agents-avec-pont-assistant-chaine-de-valeur-studio-cinq-blocs-tiroir-hitl-et-s--timedOut.png) · [Trigger Desktop](../e2e-campaign-epic-21/screenshots/20-process-studio-v2-finops-and-log-sink/desktop-cockpit--contrat-d-autonomie-alerte-applicative-dedupliquee-arret-d-urgence-et-gouvernance-finops--failed.png) · [Trigger Mobile](../e2e-campaign-epic-21/screenshots/20-process-studio-v2-finops-and-log-sink/mobile-companion--contrat-d-autonomie-alerte-applicative-dedupliquee-arret-d-urgence-et-gouvernance-finops--failed.png)
  - `21-assistant` #2 (`2` fails) : [Help Desktop](../e2e-campaign-epic-21/screenshots/21-assistant-citations-v5-audit-help-showcase/desktop-cockpit--centre-d-aide-contextuelle-lien-organisationnel-colonne-laterale-et-vitrine-produit-surv--failed.png) · [Help Mobile](../e2e-campaign-epic-21/screenshots/21-assistant-citations-v5-audit-help-showcase/mobile-companion--centre-d-aide-contextuelle-lien-organisationnel-colonne-laterale-et-vitrine-produit-surv--failed.png)

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `OrciaDialog` (`packages/ui/src/primitives/RadixDesignSystemPrimitives.tsx:86-126`) : **`impactedCount: 281`**, risque **`CRITICAL`** (`direct: 118`, `d=2: 122`, `d=3: 41`, `processes_affected: 33`, `modules_affected: 18`).
  - `UserSettingsModalDialog` (`packages/ui/src/primitives/UserSettingsModalDialog.tsx:71-278`) : **`impactedCount: 366`**, risque **`CRITICAL`** (`direct: 188`, `d=2: 137`, `d=3: 41`, `processes_affected: 51`, `modules_affected: 20`).
  - `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx:137-339`) : **`impactedCount: 281`**, risque **`CRITICAL`** (`direct: 118`, `d=2: 122`, `d=3: 41`).
- **Tables PostgreSQL 18 associées** : `workspace_exception_waivers`, `kb_documents`, `tripartite_trace_edges`, `catalog_items`, `catalog_acl_entries`, `workflow_definitions`, `workflow_triggers`, `iam_accounts`, `org_units`, `users`, `user_preferences`, `user_mcp_tokens`, `llm_model_endpoints`, `workspace_llm_tier_mappings`, `enterprise_connectors`.
- **Opportunités de Factorisation & Volumétrie** :
  - Unifier 100 % des dialogues sur `OrciaDialog` (`header / scrollable body / sticky footer`) avec tokens `--z-overlay: 1000` et `--z-dialog: 1010` ; supprimer les styles inline de modale faits à la main.
  - Découper `features/workspaces/index.tsx` et `features/catalog/index.tsx` sous `< 350` lignes en séparant `/catalog` (`/agents` vs `/catalog`).
  - Réaligner `zero-dead-buttons-and-silent-catches-audit.test.tsx` pour tester les vraies routes TanStack plutôt que d'obliger les devs à cacher des doublons `display: none`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune nouvelle table requise (`workspace_exception_waivers` `0026`, `workflow_triggers` `20261117_0702`, `catalog_*` `0003` existent déjà). Vérifier la compatibilité des routes PG18 pour les waivers (`dna_and_glossary.py` / `workspace_governance.py`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucune logique UI dans `orcia_core` ; pour `REM-04` (`workspace_exception_waivers`), vérifier que le service d'acquittement de dérogations d'espace est bien relié au repository SQL `0026` dans le Composition Root.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/settings_and_studio.py` (`SecretInputPayload`) : conserver `plaintext_value` (`extra="forbid"`) comme contrat canonique ; aligner `20-process-studio.spec.ts` et vérifier que les appels frontend passent par les types `@orcia/api-client`.
- `POST /api/v1/org-units/invite-user` : autoriser l'invitation sur l'unité racine (`ENTREPRISE`) si l'admin n'a pas encore créé d'équipe fille (`REM-16`), en conservant strictement la garde anti-escalade et le scope `BU_LEAD`/`TEAM_LEAD`.
- Câbler `POST /api/v1/workspaces/{ws_id}/waivers` (ou route gouvernance `workspace_governance.py`) sur PG18 pour remplacer le `useState` local `activeWaivers` (`REM-04`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- **Tailwind CSS v4 + Portals `OrciaDialog` (`REM-03`)** :
  - Activer `@tailwindcss/vite` dans `apps/web/vite.config.ts` avec `@source "../../packages/ui/src"` dans l'entrée CSS ; définir `--z-overlay: 1000`, `--z-dialog: 1010`, `--z-popover: 1020`, `--z-tooltip: 1030` dans `packages/ui/src/styles/tokens.css`.
  - Structurer `.orcia-ds-dialog-content` en colonne flex (`max-height: min(90vh, 760px); overflow: hidden;`) avec `.orcia-ds-dialog-body` scrollable (`flex: 1 1 auto; min-height: 0; overflow-y: auto;`) et `.orcia-ds-dialog-footer` sticky (`flex-shrink: 0;`).
  - Migrer `UserSettingsModalDialog`, `FirstBootAdminSetupModal`, `AiModelConfigModal` et `UpstreamChallengeRewindModal` sur `<OrciaDialog>` (`DialogPrimitive.Portal` vers `document.body`).
  - Supprimer la validation rouge prématurée sur `AiModelConfigModal` avant interaction (`touched` ou clic Enregistrer).
- **Purge `display: none` (`REM-04`)** :
  - Supprimer les 4 blocs `style={{ display: "none" }}` dans `features/catalog/index.tsx`, `features/workspaces/index.tsx`, `InboxAuxiliaryPanels.tsx` et `FourZoneSidebarRail.tsx`.
  - Monter `WorkspaceFiveTabsAndExternalRebaseView` (5 sous-onglets canoniques visibles) et `DnaStarlarkCompilerAndGlossaryLifecycleView` visible dans l'onglet Glossaire & Règles Métiers de `/spaces` et `/workspaces/$wsId`, en câblant `onRegisterWaiver` sur PG18.
- **Découplage `/catalog` vs `/agents` & `/help` (`REM-05`, `REM-06`)** :
  - Séparer `router.tsx` : `/catalog` rend une vue dédiée affichant `CatalogExplorerPanel` visible (`catalog-explorer-panel`), tandis que `/agents` rend `AgentsAndSkillsManagerView` avec **1 seule** instance de `RemoteServiceTestBenchAndMcpExposureView` (suppression de `remote-service-test-bench-wrapper`).
  - Dans `ShellContainer.tsx`, ne pas monter `<ShellContextualHelpColumn>` lorsque `pathname.startsWith("/help")` (`REM-06`) ; corriger l'accordéon `help-accordion-steps-btn` / `help-accordion-steps-content` sur `< 768 px` et ajouter `pl-5` aux listes à puces de `Repères & notions utiles`.
- **Bouton invitation & `data-testid` (`REM-16`, `REM-24`, `REM-25`)** :
  - Toujours afficher `open-invite-org-user-modal-btn` dans `SettingsOrganizationUnitsBlock.tsx` (invitation racine autorisée ou état `disabled` avec texte explicatif + bouton `+ Nouvelle unité` à côté).
  - Aligner `settingsAiModelsPresets.ts` (`llm-provider-preset-ollama`), `WorkflowStudioHeaderBar.tsx` (`studio-view-mode-whatif` + libellés distincts `Simuler l'impact` vs `Tester l'exécution`) et `20-process-studio-v2-finops-and-log-sink.spec.ts` (`plaintext_value`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : audit `zero-dead-buttons-and-silent-catches-audit.test.tsx` réaligné sur les vraies routes ; tests `@orcia/ui` vérifiant le rendu en `Portal` dans `document.body`, la visibilité du footer de `AiModelConfigModal`, l'accordéon `/help` mobile et l'unicité des `data-testid`.
- **Couche 2 (`HTTP ➔ PG18`)** : persistance `workspace_exception_waivers`, invitation depuis `/organization` vers `users` / `iam_accounts`.
- **Couche 3 (`OpenAPI 0-diff`)** : vérification du contrat `SecretInputPayload.plaintext_value` utilisé par le SDK `@orcia/api-client`.
- **Couche Sécurité** : maintien des gardes d'anti-escalade sur `invite-user` et rejet `422` sur `SecretInputPayload` invalide.
- **Couche 5 (Playwright E2E)** : passage au vert visé de `14-auth` #1/#2, `15-org` #3, `16-ai-models` #1/#2, `17-workspace` #3, `18-catalog` #1/#5, `20-process-studio` #1/#2 et `21-assistant` #2.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[En attente d'implémentation de la Story 22.2]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/vite.config.ts` & `packages/ui/src/styles/tokens.css` | Modification | *[À compléter après implémentation]* |
| `packages/ui/src/primitives/UserSettingsModalDialog.tsx` & `RadixDesignSystemPrimitives.tsx` | Modification | *[À compléter après implémentation]* |
| `apps/web/src/features/catalog/*`, `workspaces/*`, `routes/help.tsx` | Modification | *[À compléter après implémentation]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[$\ge 90\%$ requis à mesurer après implémentation]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `pnpm typecheck`, `lint-imports`, `lint_spine.py`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après exécution des 5 couches `AD-17` et Playwright Desktop/Mobile]*
