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
