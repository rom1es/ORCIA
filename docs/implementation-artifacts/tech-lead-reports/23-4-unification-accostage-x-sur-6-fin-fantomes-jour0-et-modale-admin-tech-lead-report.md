# Story 23.4 — Unification Accostage `X/6` PG18, Suppression des Fantômes Jour 0 (`AP`, `Notifications 4`) & Ergonomie Modale Premier Administrateur

- **Date** : 2026-11-20
- **Story / Clé Sprint** : `23-4-unification-accostage-x-sur-6-fin-fantomes-jour0-et-modale-admin` (`Epic 23` — Vague 1 `P1`)
- **Capacité(s)** : `CAP-005`, `CAP-060`, `CAP-061` — classification : `feature` + `ux` + `hygiène` (`REM23-06`, `REM23-07`, `REM23-08` / `ARCH23-05`, `P1-UX-4`, `P1-UX-6`, `P1-UX-7`, `P2-UX-8`, `P2-UX-9`, `P2-UX-11`)
- **Auteur / Contexte** : `22.10-impl` (cadrage) / `23.4-impl` + `23.4-test` + `23.4-validate` (`APPROVED` Round 2). Aligne le parcours d'accostage Jour 0 sur une source de vérité PostgreSQL 18 unique **`Accostage X/6`**, supprime l'identité fantôme `AP` et les `Notifications 4` avant la création du premier utilisateur, élimine les requêtes pré-auth `401` Cluster A, homogénéise la coquille sous modale Jour 0 et corrige les défauts ergonomiques de `FirstBootAdminSetupModal`.
- **Commits associés** : `feat(epic-23): unify accostage 0-6/6, eliminate Day 0 phantoms & Cluster A 401s (story 23.4)` (sur `feat/epic-23-remediation-pg18-sse-direction-c`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Preuves E2E & Captures (`e2e-campaign-epic-22`)** :
  1. **Split-brain Accostage `X/5` vs `6` jalons (`REM23-06` / `P1-UX-6`, `ARCH23-05`)** :
     - Sur [`#5` (`01-day0-boot` F5)](../e2e-campaign-epic-22/screenshots/01-day0-boot-and-f5-persistence/desktop-cockpit--le-premier-administrateur-cree-survit-a-un-f5-sans-localstorage-rehydratation-postgresql--passed.png) et [`#10` (`03-human-led`)](../e2e-campaign-epic-22/screenshots/03-human-led-anchor-and-arbitration/desktop-cockpit--signature-de-l-ancrage-violet-30-car-rejet-agent-422-arbitrage-motive-et-survie-au-f5--passed.png), `Accostage 0/5` s'affiche deux fois alors que l'Étape 1 (`Alice Admin E2E ✓`) est validée (`2/5` en `#10` ignore toujours Étape 1) ; l'Étape 3 recommence par `1. Modèles IA` (doublon de l'Étape 2) et tronque 3 libellés sur 5 (`2. Structure Organisationnel...`, `4. Sources Documentaires &...`, `5. Packs Métiers & Atelier de...`).
     - Cause code : [`progressive_accostage.py#L146`](../../../packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py#L146) pré-remplit `self._completed_keys = {"first-admin"}` sur `ACCOSTAGE_SIX_MILESTONES` (`6` jalons, `L54-L97`), tandis que [`platformSetupStore.tsx#L451-L466`](../../../apps/web/src/components/platformSetupStore.tsx#L451-L466) recalcule `/5` sans `adminCreated`, et [`platformSetupHydration.ts#L191`](../../../apps/web/src/components/platformSetupHydration.ts#L191) ignore `workspace_llm_tier_mappings`.
  2. **Fantômes pré-admin Jour 0 & props mortes (`REM23-07` / `P1-UX-7`, `P2-UX-11`, `ARCH23-05`)** :
     - À `0` utilisateur en base ([`#2` modal](../e2e-campaign-epic-22/screenshots/00-stack-smoke/desktop-cockpit--apres-reset-jour-0-la-modale-de-premier-administrateur-est-presentee--passed.png), [`#4` 16.2](../e2e-campaign-epic-22/screenshots/00-stack-smoke/desktop-cockpit--story-16-2-moteur-reflexif-asyncio-survie-f5-waiting-write-preview-approbation-writeprev--failed.png), [`#6` reset](../e2e-campaign-epic-22/screenshots/01-day0-boot-and-f5-persistence/desktop-cockpit--apres-reset-jour-0-la-modale-revient-0-utilisateur-en-base--passed.png)), [`ShellContainer.tsx#L119-L125`](../../../apps/web/src/components/ShellContainer.tsx#L119-L125) retombe sur [`DEFAULT_HUMAN_PROFILE`](../../../apps/web/src/components/shellPresets.ts#L26-L32) (`AP Administrateur de la ... Contributeur`), `buildShellNotificationItems` (`shellScopeOptions.ts#L252-L336`) injecte `Notifications 4`, `hiddenMenuKeys` (`L263-L264`) masque `Configuration` (`7` menus vs `8`), et `buildShellDisabledMenuKeys` (`shellScopeOptions.ts#L189-L221`) laisse `Mes Espaces` et `Aide` noirs/actifs pendant que les autres sont grisés sans infobulle explicative. En outre, `ShellContainer.tsx#L202-L204,L278-L287` conserve `5` props mortes (`showOrganizationMenu`, `organizationMenuActive`, `activityMenuActive`, `onSelectOrganizationMenu`, `onSelectActivityMenu`).
  3. **Modale Premier Administrateur (`REM23-08` / `P1-UX-4`, `P2-UX-8`)** :
     - Dans [`FirstBootAdminSetupModal.tsx`](../../../apps/web/src/components/FirstBootAdminSetupModal.tsx), `closeLabel="Annuler (Esc)"` (`L105`) et `first-boot-admin-cancel-btn` (`L221-L228`) rendent deux boutons identiques `Annuler (Esc)` (avec anglicisme `Esc` et bordure noire dominante en haut à droite), le champ mot de passe affiche `placeholder="••••••••••••"` sur `WebkitTextSecurity: "disc"` (`L193,L199`), et le CTA principal `Créer le compte Administrateur` (`L233-L244`) manque de hiérarchie `#2563EB`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `ProgressiveDay0AccostageService` (`packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py:L130-L335`) : `impactedCount: 590`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 3` (`bootstrap/__init__.py`, `sql_first_user_guard.py`), `d=2: 404`, `d=3: 183`, `processes_affected: 195`, `modules_affected: 20`.
  - `ProgressiveDay0AccostageBanner` (`packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx`) : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`.
  - `InnerShellContainer` (`apps/web/src/components/ShellContainer.tsx`) : `impactedCount: 131`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 91`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 20` (`ShellContainer` comporte `6` homonymes dans l'index, max `impactedCount: 562`).
  - `FirstBootAdminSetupModal` : affecté par la latence d'index GitNexus (`2 commitsBehind`), vérifié par lecture directe (`L80-L260`).
- **Volumétrie & Découpages Obligatoires (`> 300–400` L)** :
  - `apps/web/src/components/platformSetupStore.tsx` (`521` L > `400` L) : extraire les types/dérivations d'accostage `Accostage6Milestones` dans `platformSetupAccostage.ts` (`< 200` L) et ramener `platformSetupStore.tsx` sous `< 380` L.
  - `apps/web/src/components/ShellContainer.tsx` (`403` L > `400` L) : supprimer les `5` props mortes Epic 21 et extraire les helpers de garde pré-admin dans `shellPresets.ts` / `shellScopeOptions.ts` pour descendre sous `< 350` L.
  - `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` (`335` L) : conserver sous `< 350` L.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration requise : toutes les tables PG18 (`users`, `workspace_llm_tier_mappings`, `org_units`, `workspaces`, `workspace_datasources`, `workflow_definitions_v2`) existent déjà.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
1. **`packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py`** :
   - Supprimer le hardcode `self._completed_keys = {"first-admin"}` à `L146` : calculer le premier jalon (`first-admin`) dynamiquement depuis le compte réel en PG18 (`users_count > 0` / `admin_created`).
   - Harmoniser `ACCOSTAGE_SIX_MILESTONES` (`L54-L97`) avec les 6 jalons non redondants : `1. Compte Admin`, `2. Modèles IA`, `3. Organisation`, `4. Premier Espace`, `5. Première Source`, `6. Premier Processus`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Vérifier que l'endpoint d'état d'amorçage/accostage reflète également `workspace_llm_tier_mappings` (`modelsCount > 0`) lors de l'hydratation après `F5`.
- Régénérer `@orcia/api-client` si un champ DTO d'accostage est ajusté (`0-diff` OpenAPI).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `packages/ui/`)
1. **Unification `Accostage X/6` (`platformSetupStore.tsx`, `platformSetupHydration.ts`, `cockpit/index.tsx`, `ProgressiveDay0AccostageBanner.tsx`)** :
   - Supprimer le calcul divergent `/5` et aligner sur les `6` jalons PG18 (`adminCreated` inclus dès création du premier admin → `1/6`, puis `workspace_llm_tier_mappings`, `orgUnits`, `workspaces`, `datasources`, `workflows`).
   - Afficher **un seul** badge `Accostage X/6` en en-tête de carte (retirer le doublon externe dans `cockpit/index.tsx#L181-L243`).
   - Corriger l'Étape 3 pour ne plus dupliquer `1. Modèles IA` (Étape 2) et agrandir les largeurs/colonnes de liste afin qu'aucun libellé ne soit tronqué à `1440px`.
2. **Suppression fantômes Jour 0 pré-admin (`ShellContainer.tsx`, `shellScopeOptions.ts`, `FourZoneSidebarRail.tsx`)** :
   - Quand `platformAdmin === null` (`0` utilisateur en base) :
     - Ne **pas** retomber sur `DEFAULT_HUMAN_PROFILE` (`AP`) : afficher un état anonyme neutre (ou aucune carte profil utilisateur).
     - Ne **pas** générer les `4` notifications synthétiques `SETUP_PREREQUISITE` (`Notifications 4` -> `0` / masqué tant qu'aucun utilisateur n'est créé).
     - Verrouiller uniformément les entrées de menu bloquées au Jour 0 avec contraste WCAG AA lisible et infobulle explicative au survol/focus.
     - **Alerte compatibilité E2E (`shell.spec.ts#L55-L56,L94-L102`)** : `shell.spec.ts` vérifie actuellement l'absence de `eight-menu-item-configuration` sans `PLATFORM_ADMIN` et inspecte `disabledReasons` (`aria-disabled="true"`). Préserver ce contrat explicite ou synchroniser `shell.spec.ts` en cohérence avec la politique `RBAC` Direction C (`Configuration` réservée aux rôles `PLATFORM_ADMIN`).
     - Supprimer les `5` props mortes `showOrganizationMenu`, `organizationMenuActive`, `activityMenuActive`, `onSelectOrganizationMenu`, `onSelectActivityMenu` dans `ShellContainer.tsx`.
3. **Ergonomie Modale Jour 0 (`FirstBootAdminSetupModal.tsx`, `RadixDesignSystemPrimitives.tsx`, `fr.ts`)** :
   - Supprimer le double bouton `Annuler (Esc)` (`first-boot-admin-cancel-btn` `L221-L228`) ; conserver uniquement la fermeture accessible cohérente avec la nature obligatoire de la création d'admin Jour 0 (pas d'annulation ambiguë ni d'anglicisme `(Esc)`, libellé `(Échap)` si fermeture présente).
   - Retirer `placeholder="••••••••••••"` (`L193`) au profit d'un champ vide (`placeholder=""` + bouton œil afficher/masquer le mot de passe).
   - Donner au CTA primaire `Créer le compte Administrateur` un style plein `#2563EB` net (et un état désactivé clairement différencié tant que les champs requis sont incomplets).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (`pytest`)** : tests unitaires de `progressive_accostage.py` vérifiant `0/6` sans utilisateur, `1/6` dès création admin (sans `{"first-admin"}` en dur), et progression réelle `1/6 -> 6/6`.
- **Couche 1b (`Vitest`)** : mise à jour/ajout de tests dans `apps/web/src/__tests__/` (`day0-modal-and-settings-auth-token-wiring.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`) vérifiant : zéro `AP`, zéro `Notifications 4` à `0` utilisateur, un seul badge `Accostage X/6`, absence de double bouton `Annuler`, présence bouton œil mot de passe.
- **Couche 2 (`testcontainers` PG18)** : extension de `test_contextual_help_and_accostage_postgres18.py` vérifiant `Accostage 0/6 -> 1/6 -> 2/6` après création admin et modèle IA dans `workspace_llm_tier_mappings`.
- **Couche 5 (E2E)** : `01-day0-boot-and-f5-persistence.spec.ts` et `shell.spec.ts` verts en Desktop + Mobile.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` | Modification | Suppression de l'initialisation en dur `{"first-admin"}` ; `0/6` par défaut et synchronisation PG18 dynamique `0/6..6/6` via `sync_from_pg18_counts`. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_accostage_counts.py` & `sql_platform_setup_store.py` | Modification | Comptage PG18 complet des 6 jalons (`users`, `org_units`, `workspaces`, `workspace_llm_tier_mappings`/`llm_model_endpoints`, `workspace_datasources`, `workflow_definitions_v2`/`workflow_runs`) et hydratation de `llm_tiers` depuis `workspace_llm_tier_mappings WHERE is_active = TRUE` quand `platform_settings` est vide. |
| `apps/api/src/orcia_api/routers/bootstrap_accostage.py` & `schemas/bootstrap.py` (+ SDK `packages/api-client/`) | Modification | Exposition des compteurs PG18 et `workflows_count` dans `AccostageStatusResponse` + régénération OpenAPI `0-diff`. |
| `apps/web/src/components/platformSetupStore.tsx`, `platformSetupContextTypes.ts`, `platformSetupAccostage.ts`, `platformSetupHydration.ts` | Refactoring / Création | Extraction modulaire (`platformSetupStore.tsx` < 350 L) ; unification stricte `Accostage 0/6..6/6` sans requêtes pré-auth protégées (`401` Cluster A éliminés). |
| `apps/web/src/components/ShellContainer.tsx`, `ShellAuthFallbackView.tsx`, `shellPresets.ts`, `shellScopeOptions.ts`, `shellNotificationBuilder.ts` | Refactoring / Création | Suppression de `DEFAULT_HUMAN_PROFILE` (`AP`), suppression des `Notifications 4` avant création d'admin, suppression des 5 props mortes Epic 21, verrouillage uniforme du menu Jour 0 (`spaces`, `help`, etc.) avec infobulles WCAG AA. |
| `packages/ui/src/primitives/OrciaPasswordInput.tsx`, `RadixDesignSystemPrimitives.tsx`, `FourZoneDirectionCShell.tsx`, `ProgressiveDay0AccostageBanner.tsx`, `tokens.css` | Création / Modification | Composant réutilisable `<OrciaPasswordInput />` (`maskMode="masked-text" | "password"`, toggle œil i18n, zéro `placeholder="••••"`), `aria-modal="true"` explicite sur `OrciaDialog`, garde raccourci `[` quand un dialogue `aria-modal="true"` est ouvert, hiérarchie `#2563EB` + correction Étape 3 sans troncature. |
| `apps/web/src/components/FirstBootAdminSetupModal.tsx`, `apps/web/src/features/cockpit/index.tsx`, `apps/web/src/i18n/locales/shell_and_search_labels.ts` | Modification | Suppression du double bouton `Annuler (Esc)`, champs mot de passe + confirmation via `OrciaPasswordInput` avec `autoFocus`, CTA primaire `#2563EB` net, suppression du badge doublon `/5` sur le Cockpit. |
| `infra/scripts/e2e/reset_day0.py` | Modification | Re-synchronisation idempotente de `declarative_pack_bundles` après `TRUNCATE CASCADE` lors du reset Jour 0 E2E. |
| `tests/unit/test_epic_9_story_9_2_accostage_and_first_user.py`, `tests/integration/test_contextual_help_and_accostage_postgres18.py`, `tests/integration/test_e2e_reset_day0_postgres18_and_redis.py`, `packages/ui/src/__tests__/orcia-password-input.test.tsx` + audits Vitest/E2E | Création / Modification | Couverture complète des 5 couches `AD-17`, progression PG18 `0/6 -> 6/6` avec éviction RAM `create_app()`, `declarative_pack_bundles >= 1`, `OrciaPasswordInput`, `OrciaDialog aria-modal="true"`, garde `[`, et stabilisation `createWorkspaceViaUi`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests (brique bootstrap Story 23.4)** : **`96.75 %`** (`progressive_accostage.py` `99 %`, `sql_platform_setup_store.py` `93 %`, `sql_accostage_counts.py` `91 %`) — exigence $\ge 90\%$ satisfaite.
- **Suite unitaire Python complète** : `.venv/bin/pytest tests/unit/ -q` (`100 %` vert, exit code `0`).
- **Intégration PostgreSQL 18 + Redis 7.4 (`testcontainers`, Composition Root réel `create_app()` sans override)** : `test_contextual_help_and_accostage_postgres18.py` + `test_e2e_reset_day0_postgres18_and_redis.py` — **`2 passed`** (`0` skip, `0` fail).
- **Qualité statique, Contrats & Architecture** :
  - `.venv/bin/ruff check` & `ruff format --check` : `0` erreur (`850` fichiers conformes).
  - `.venv/bin/mypy --strict` : `0` erreur (`551` fichiers Python + `infra/scripts/e2e/reset_day0.py`).
  - `.venv/bin/lint-imports` : **`Contracts: 5 kept, 0 broken`** (`597` fichiers).
  - `.venv/bin/python scripts/export_openapi.py --check` : **`0-diff`**.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : **`0` findings**.
  - `pnpm turbo run lint typecheck test` : **`9/9` tâches réussies** (`@orcia/api-client`, `@orcia/ui` `29` suites / `97` tests, `@orcia/web` `53` suites / `203` tests, incluant tous les audits AST `no-hidden-legacy-panels`, `e2e-testids-sync`, `anti-jargon-and-secrets-ui`, `zero-dead-buttons-and-silent-catches`).
- **Dette technique consignée** : ajout de `ACTION_ITEM-23.4` (`status: open`, `priority: P3`) dans `docs/implementation-artifacts/sprint-status.yaml` pour le découpage futur de `apps/web/src/components/platformSetupGovernanceActions.ts` (`502` L) et `apps/web/src/i18n/locales/shell_and_search_labels.ts` (`628` L) relevés par `23.4-validate`.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Chaîne Canari E2E Desktop (`--project=desktop-cockpit --retries=0 --timeout=35000`, sans `ORCIA_E2E_SEED_FIXTURES`)** : **`19 passed, 3 skipped (mobile-only), 0 failed`** sur les 9 specs (`00-stack-smoke`, `01-day0-boot-and-f5-persistence`, `02-assistant-streaming-and-folders`, `03-human-led-anchor-and-arbitration`, `05-mobile-companion-and-rgaa`, `11-screens-smoke-without-server-errors`, `12-finops-and-audit-provenance`, `13-epic-7-autonomous-governance-and-supervision`, `shell.spec.ts`), avec **`7/7` captures PNG Desktop validées visuellement** par `23.4-validate` (verdict **`APPROVED`**).
- **Cohérence documentaire & catalogue** : `pnpm site:sync && pnpm site:check` (`0` erreur), `scripts/check_implementation_docs.py` et `test_epic22_to_epic23_traceability.py` validés avant commit.
