# Story 20.3 — Suppression du Login Top-Right, Popup « Mon Compte » en Bas à Gauche (Style ChatGPT) & Modale Unifiée « Paramètres » Persistée en PG18

- **Date** : 2026-11-17
- **Story / Clé Sprint** : `20-3-suppression-login-top-right-popup-mon-compte-bas-gauche-et-modale-parametres-pg18` (`Epic 20`, résout `UX-AUTH-DOUBLE-ICON-01`)
- **Capacité(s)** : `CAP-060`, `CAP-063`, `CAP-064`, `CAP-100` (mises à jour dans `docs/product/capabilities.yaml`) — classification : `feature | ux | sécurité`
- **Auteur / Contexte** : Simplification de la coquille globale suite aux retours visuels sur le doublon entre le contrôle utilisateur en haut à droite (`ShellHeaderAccountControl`) et l'entrée `Mon Compte` en bas à gauche (`ShellSidebarFooter`), au faux sélecteur `Rôle` (`dropdown-hat-selector`) qui provoquait une confusion entre rôle RBAC et casquette métier IA (ex. Martin Pecheur affiché « Responsable d'Équipe »), et à l'absence de persistance PostgreSQL 18 des préférences utilisateur et clés IDE/MCP (`UserPreferencesAndMcpTokenService` en RAM, jeton `"pat_mcp_9a8b7c6d5e4f3a2b1c0d"` codé en dur). Alignement sur le modèle ergonomique ChatGPT en bas à gauche. Couvre `FR-32`, `AD-17`, `AD-19`, `UX-DR1`, `UX-DR2`.
- **Commits associés** : *(en cours d'implémentation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
1. **Redondance Top-Right / Bas-Gauche & Faux Sélecteur `Rôle` (`dropdown-hat-selector`)** :
   - `FourZoneTopHeaderSection.tsx:L162-L241` et `ShellHeaderAccountControl.tsx` affichent un bouton Login/Compte et son menu déroulant en haut à droite, faisant double emploi avec `ShellSidebarFooter.tsx` (`sidebar-open-my-account-btn`).
   - `UserAccountDropdownMenu.tsx:L60-L81` propose un sélecteur `Rôle` qui mélange rôles RBAC et casquettes métier (`activeHat`) et modifie `authSessionStore.activeHat`, altérant visuellement le rôle affiché et les droits RBAC (`settingsRbacResolver.ts`).
   - De plus, `UserAccountDropdownMenu` et `TemporaryPasswordWarningBanner` présentent des préfixes emojis résiduels à côté d'icônes SVG (`UX-AUTH-DOUBLE-ICON-01`).
2. **Modale Paramètres partiellement câblée et non persistée en PostgreSQL 18** :
   - `UserPreferencesAndMcpTokenService` (`packages/orcia-core/src/orcia_core/permissions/user_preferences_and_mcp_tokens.py:L121-L261`) stocke toutes les préférences (`theme`, `locale`, `default_hat`, `auto_open_help`, `notifications_enabled`) et les jetons MCP uniquement en RAM (`_preferences_by_user`, `_tokens_by_id`), perdus à chaque redémarrage.
   - `ShellHeaderAccountControl.tsx:L181-L188` n'appelle pas `PATCH /api/v1/users/me/preferences`, et `UserAccountDropdownAndSettingsModal.tsx` émet un jeton hardcodé `"pat_mcp_9a8b7c6d5e4f3a2b1c0d"` en `useState` local au lieu de `/api/v1/users/me/mcp-tokens`.
   - Les réglages personnels de l'assistant (casquette IA par défaut, ton, instructions personnelles) étaient éclatés hors de la modale compte.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`, `direction: "upstream"`, `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`) : `impactedCount: 3`, `risk: LOW`.
  - `ShellHeaderAccountControl` / `UserAccountDropdownAndSettingsModal` : impact direct sur `ShellContainer.tsx`, `story-17-4`, `story-17-1`, `i18n-and-shell`, `rgaa-modals-escape-unsaved-guard`, `e2e/support/firstAdmin.ts`.
- **Contrôle de Volumétrie (`< 350` L par fichier)** :
  - `ShellContainer.tsx` (`403` L) redescendra sous `350` L grâce au retrait de `ShellHeaderAccountControl` du header.
  - `UserAccountDropdownAndSettingsModal.tsx` (`358` L) et `portal_and_help.py` (`327` L) ne doivent pas dépasser `350` L :
    1. Créer le composant pur `@orcia/ui` `SidebarAccountPopover.tsx` (`< 240 L`) pour le bouton bas-gauche et le popup style ChatGPT.
    2. Découper la modale unifiée 5 onglets dans `packages/ui/src/primitives/` (`UserSettingsModalDialog.tsx`, `UserSettingsGeneralTab.tsx`, `UserSettingsPersonalizationTab.tsx`, `UserSettingsMcpTokensTab.tsx` `< 220 L` chacun).
    3. Créer `packages/orcia-core/src/orcia_core/permissions/_internal/sql_user_preferences.py` (`< 260 L`) et `apps/api/src/orcia_api/routers/user_account_settings.py` (`< 220 L`) pour le câblage PG18 sans alourdir `portal_and_help.py`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/20261117_2003_story_20_3_user_preferences_and_mcp_tokens_pg18.py`)
- `down_revision = "20261117_2002"` (SQL brut `op.execute(sa.text(...))`, zéro import ORM, `upgrade()` et `downgrade()` réversibles) :
  - Table `user_preferences` :
    - `user_id VARCHAR(128) PRIMARY KEY`, `theme VARCHAR(16) NOT NULL DEFAULT 'light' CHECK (theme IN ('light','dark','system'))`, `locale VARCHAR(8) NOT NULL DEFAULT 'fr' CHECK (locale IN ('fr','en'))`, `default_assistant_hat VARCHAR(64) NOT NULL DEFAULT 'ANALYST_PM_PO'`, `assistant_tone VARCHAR(32) NOT NULL DEFAULT 'balanced'`, `personal_instructions TEXT NOT NULL DEFAULT ''`, `auto_open_help BOOLEAN NOT NULL DEFAULT TRUE`, `notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
  - Table `user_mcp_tokens` :
    - `id UUID PRIMARY KEY`, `user_id VARCHAR(128) NOT NULL`, `label VARCHAR(128) NOT NULL`, `token_prefix VARCHAR(24) NOT NULL`, `token_sha256 VARCHAR(64) NOT NULL UNIQUE`, `scopes_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb`, `expires_at TIMESTAMPTZ NULL`, `revoked_at TIMESTAMPTZ NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
    - Index `ix_user_mcp_tokens_user_id ON user_mcp_tokens (user_id, created_at DESC)`.
  - Ajout de `user_mcp_tokens` et `user_preferences` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` de `infra/scripts/maintenance/09_reset_db_first_boot.py`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- `permissions/user_preferences_and_mcp_tokens.py` : extension du modèle `UserPreferences` (`default_assistant_hat`, `assistant_tone`, `personal_instructions`) et génération cryptographique des jetons `pat_mcp_` (`secrets.token_urlsafe(24)` + hachage `SHA-256`).
- `permissions/_internal/sql_user_preferences.py` (nouveau) : adaptateur PostgreSQL 18 `SqlUserPreferencesAndMcpService` (`get_preferences`, `upsert_preferences`, `list_mcp_tokens`, `create_mcp_token`, `revoke_mcp_token`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/portal_and_help.py` (ou `user_account.py`) & `routers/user_account_settings.py` (ou `portal_and_help.py` déléguant au service PG18) :
  - `GET /api/v1/users/me/preferences` & `PATCH /api/v1/users/me/preferences` persistés en PG18 (`OBSERVER` autorisé pour ses propres préférences UI, ou contrôlé proprement sur MCP tokens).
  - `GET /api/v1/users/me/mcp-tokens`, `POST /api/v1/users/me/mcp-tokens` (retourne le jeton en clair une seule fois à la création), `DELETE /api/v1/users/me/mcp-tokens/{token_id}` (révocation bornée au `user_id` authentifié — rejet `403/404` sur token d'autrui, rejet `403` si `OBSERVER` tente de créer une clé MCP d'écriture).
- Régénération SDK `@orcia/api-client` (`scripts/export_openapi.py`, `0-diff`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- **Top-Right épuré (`FourZoneTopHeaderSection.tsx`, `ShellContainer.tsx`)** : suppression totale du contrôle Login/Compte et de son menu déroulant du haut-droite (conservation de `[❓ Aide]` et `[🔔 Notifications]`), et suppression définitive du faux sélecteur `Rôle` (`dropdown-hat-selector`). `authSessionStore.ts` et `settingsRbacResolver.ts` reposent uniquement sur l'union complète `session.roles`.
- **Pied de Sidebar & Popup « Mon Compte » style ChatGPT (`SidebarAccountPopover.tsx` + `ShellSidebarFooter.tsx`)** :
  - Pied de menu : Avatar initiales + Nom complet + rôle principal lisible (Avatar seul en mode replié `72px`).
  - Popup flottant au-dessus du pied : En-tête identité cliquable ($\rightarrow$ `/profile`), `Personnalisation` ($\rightarrow$ modale Paramètres onglet `Personnalisation`), `Profil` ($\rightarrow$ `/profile`), `Paramètres` ($\rightarrow$ modale Paramètres onglet `Général`), `Aide ›` (accès `/help` et `/showcase`), `Se déconnecter`. Zéro double icône/emoji (`UX-AUTH-DOUBLE-ICON-01` corrigé aussi sur `TemporaryPasswordWarningBanner`).
- **Modale unifiée « Paramètres du compte » à 5 onglets** (`Général`, `Personnalisation`, `Compte & Sécurité`, `Connexions aux outils`, `Clés IDE & MCP`) : 100 % câblée sur `/api/v1/users/me/preferences`, `/api/v1/users/me/passthrough-tokens`, `/api/v1/users/me/mcp-tokens` et `/api/v1/auth/change-password` — suppression de la chaîne en dur `pat_mcp_9a8b7c6d5e4f3a2b1c0d` et survie au `F5`.
- Adapter `story-17-1`, `story-17-4`, `i18n-and-shell`, `rgaa-modals-escape-unsaved-guard`, `e2e/support/firstAdmin.ts`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a & 1b (`pytest` $\ge 90\%$ & `Vitest`)** : tests unitaires de `SqlUserPreferencesAndMcpService` / `UserPreferencesAndMcpTokenService`, génération aléatoire `pat_mcp_*` ; Vitest sur `SidebarAccountPopover`, disparition du login top-right et `dropdown-hat-selector`, 5 onglets modale Paramètres + survie `F5` (`unmount()` + `render()`).
- **Couche 2 (`HTTP FastAPI ➔ PostgreSQL 18 SELECT` via `testcontainers`)** : réversibilité migration `20261117_2003`, `PATCH /users/me/preferences` + `POST/DELETE /users/me/mcp-tokens` vérifiés en SQL PG18 + vérification `pnpm db:reset`.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`, `mypy --strict`, `ruff`)** & **Couche Sécurité** : isolation inter-utilisateur sur les clés MCP (un utilisateur ne peut révoquer le token d'un autre) + `403` `OBSERVER` sur création de jeton MCP.
- **Couche 5 (`Playwright E2E`)** : mise à jour `e2e/support/firstAdmin.ts` sur le nouveau déclencheur bas-gauche `sidebar-open-my-account-btn`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés & Modifiés

| Couche | Fichier | Action | Lignes (`wc -l`) | Détail / Responsabilité |
| :--- | :--- | :--- | :---: | :--- |
| **Alembic & Maintenance** | [`infra/migrations/versions/20261117_2003_story_20_3_user_preferences_and_mcp_tokens_pg18.py`](../../../infra/migrations/versions/20261117_2003_story_20_3_user_preferences_and_mcp_tokens_pg18.py) | Créé | `85` | Migration SQL brut réversible (`user_preferences`, `user_mcp_tokens`, index `ix_user_mcp_tokens_user_id`), `down_revision = "20261117_2002"`. |
| **Maintenance Jour 0** | [`infra/scripts/maintenance/09_reset_db_first_boot.py`](../../../infra/scripts/maintenance/09_reset_db_first_boot.py) | Modifié | `286` | Ajout de `user_mcp_tokens` et `user_preferences` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR`. |
| **Noyau Hexagonal** | [`packages/orcia-core/src/orcia_core/permissions/user_preferences_and_mcp_tokens.py`](../../../packages/orcia-core/src/orcia_core/permissions/user_preferences_and_mcp_tokens.py) | Modifié | `250` | Extension `UserAccountPreferences` (`default_assistant_hat`, `assistant_tone`, `personal_instructions`), isolation `ResourceNotFoundError`. |
| **Noyau Hexagonal** | [`packages/orcia-core/src/orcia_core/permissions/_mcp_token_helpers.py`](../../../packages/orcia-core/src/orcia_core/permissions/_mcp_token_helpers.py) | Créé | `152` | Génération cryptographique `pat_mcp_<secrets.token_urlsafe(24)>`, hachage `SHA-256` et encodage JSONB scopes. |
| **Adaptateur PG18** | [`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_user_preferences.py`](../../../packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_user_preferences.py) | Créé | `219` | `SqlUserPreferencesAndMcpService` async PG18 (placé sous `bootstrap/_internal/` pour respecter la pureté hexagonale 0-SQLAlchemy de `permissions/`). |
| **Adaptateur PG18** | [`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_user_preferences_queries.py`](../../../packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_user_preferences_queries.py) | Créé | `149` | Requêtes SQL brutes paramétrées et mappeurs de lignes `user_preferences` / `user_mcp_tokens`. |
| **API FastAPI & SDK** | [`apps/api/src/orcia_api/routers/user_account_settings.py`](../../../apps/api/src/orcia_api/routers/user_account_settings.py) | Créé | `181` | Endpoints `GET/PATCH /users/me/preferences` et `GET/POST(201)/DELETE /users/me/mcp-tokens` avec garde `403 ERR_OBSERVER_MODE_READ_ONLY` et isolation `user_id`. |
| **API FastAPI & SDK** | [`apps/api/src/orcia_api/routers/portal_and_help.py`](../../../apps/api/src/orcia_api/routers/portal_and_help.py) | Modifié | `192` | Extraction des routes compte vers `user_account_settings.py` (`< 200` L). |
| **API & Composition Root** | [`apps/api/src/orcia_api/schemas/auth_and_org.py`](../../../apps/api/src/orcia_api/schemas/auth_and_org.py), [`dependencies/portal_and_assistant.py`](../../../apps/api/src/orcia_api/dependencies/portal_and_assistant.py), [`main.py`](../../../apps/api/src/orcia_api/main.py) | Modifiés | — | Schémas OpenAPI mis à jour + câblage `SqlUserPreferencesAndMcpService` dans la Composition Root + régénération `@orcia/api-client` (`0-diff` + `listMcpTokens`/`createMcpToken`/`revokeMcpToken`). |
| **Design System `@orcia/ui`** | [`FourZoneTopHeaderSection.tsx`](../../../packages/ui/src/primitives/FourZoneTopHeaderSection.tsx), [`FourZoneDirectionCShell.tsx`](../../../packages/ui/src/primitives/FourZoneDirectionCShell.tsx) | Modifiés | — | Suppression totale du contrôle Login/Compte et de `topbar-hat-badge` en haut à droite (conservation exclusive `[❓ Aide]` et `[🔔 Notifications]`). |
| **Design System `@orcia/ui`** | [`SidebarAccountPopover.tsx`](../../../packages/ui/src/primitives/SidebarAccountPopover.tsx), [`UserRoleDisplayLabels.ts`](../../../packages/ui/src/primitives/UserRoleDisplayLabels.ts) | Créés | `250` / `51` | Popup style ChatGPT en bas à gauche (`@radix-ui/react-dropdown-menu`), initiales + nom + rôle, en-tête `/profile`, `Personnalisation`, `Profil`, `Paramètres`, `Aide ›` (`/help`, `/showcase`), `Se déconnecter` (0 double icône/emoji). |
| **Design System `@orcia/ui`** | [`UserSettingsModalDialog.tsx`](../../../packages/ui/src/primitives/UserSettingsModalDialog.tsx), [`UserSettingsGeneralTab.tsx`](../../../packages/ui/src/primitives/UserSettingsGeneralTab.tsx), [`UserSettingsPersonalizationTab.tsx`](../../../packages/ui/src/primitives/UserSettingsPersonalizationTab.tsx), [`UserSettingsMcpTokensTab.tsx`](../../../packages/ui/src/primitives/UserSettingsMcpTokensTab.tsx), [`UserSettingsProfileAndPassthroughTabs.tsx`](../../../packages/ui/src/primitives/UserSettingsProfileAndPassthroughTabs.tsx) | Créés / Modifiés | `282` / `178` / `183` / `278` / `186` | Modale unifiée à 5 onglets verticaux (`GENERAL`, `PERSONALIZATION`, `ACCOUNT_SECURITY`, `PASSTHROUGH_SOURCES`, `IDE_MCP_KEYS`), suppression totale de `dropdown-hat-selector` et du faux jeton `"pat_mcp_9a8b7c6d5e4f3a2b1c0d"`. |
| **SPA `apps/web/`** | [`ShellContainer.tsx`](../../../apps/web/src/components/ShellContainer.tsx), [`ShellSidebarFooter.tsx`](../../../apps/web/src/components/ShellSidebarFooter.tsx), [`ShellSidebarAccountControl.tsx`](../../../apps/web/src/components/ShellSidebarAccountControl.tsx), [`useSidebarAccountSettings.ts`](../../../apps/web/src/components/useSidebarAccountSettings.ts), [`sidebarAccountMappers.ts`](../../../apps/web/src/components/sidebarAccountMappers.ts) | Créés / Modifiés | `317` / `70` / `112` / `289` / `109` | Câblage vertical complet vers `@orcia/api-client`, synchronisation `localStorage` Anti-FOUC + `assistantFoldersAndPrefsStore`, suppression de `ShellHeaderAccountControl.tsx`. |
| **SPA `apps/web/`** | [`authSessionStore.ts`](../../../apps/web/src/stores/authSessionStore.ts), [`settingsRbacResolver.ts`](../../../apps/web/src/stores/settingsRbacResolver.ts), [`TemporaryPasswordWarningBanner.tsx`](../../../apps/web/src/components/TemporaryPasswordWarningBanner.tsx), [`routes/profile.tsx`](../../../apps/web/src/routes/profile.tsx), [`router.tsx`](../../../apps/web/src/router.tsx) | Créés / Modifiés | — | Évaluation RBAC strictement sur l'union `session.roles` (suppression `setActiveHat`), suppression icône SVG dupliquée dans `TemporaryPasswordWarningBanner`, stub `/profile` pour Story 20.4. |

### 3.2 Couverture de Tests, Métriques & Validation des 5 Couches (`AD-17`)

- **Couche 1a & 1b (Tests Unitaires Python $\ge 90\%$ & Vitest)** :
  - `tests/unit/test_story_20_3_user_preferences_and_mcp_tokens.py` + `tests/unit/test_epic_9_story_9_4_user_preferences_and_mcp_tokens.py` + `tests/security/test_story_20_3_mcp_tokens_isolation.py` + `tests/integration/api/test_story_20_3_user_preferences_and_mcp_postgres18.py` : **97 %** de couverture combinée (`user_preferences_and_mcp_tokens.py`: `100 %`, `_mcp_token_helpers.py`: `100 %`, `sql_user_preferences.py`: `97 %`, `sql_user_preferences_queries.py`: `88 %`).
  - `@orcia/ui` (`26` fichiers, `110` tests), `@orcia/api-client` (`2` fichiers), `@orcia/web` (`37` fichiers, `151` tests dont `story-20-3-sidebar-account-popover-and-settings-f5.test.tsx` avec survie `F5` `unmount()` + `render()` et zéro bouton muet / zéro `.catch(() => undefined)`).
- **Couche 2 (`HTTP FastAPI ➔ PostgreSQL 18 SELECT` via `testcontainers`)** :
  - `tests/integration/api/test_story_20_3_user_preferences_and_mcp_postgres18.py` : réversibilité Alembic `20261117_2003` (`upgrade head` $\rightarrow$ `downgrade 20261117_2002` $\rightarrow$ `upgrade head`), `PATCH/GET /users/me/preferences` et `POST/GET/DELETE /users/me/mcp-tokens` vérifiés par `SELECT` direct PG18, et remise à zéro complète via `09_reset_db_first_boot.py`.
- **Couche 3 (Qualité Statique & Contrats)** :
  - `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, `.venv/bin/mypy --strict` (`471` fichiers Python, `0` erreur), `.venv/bin/lint-imports` (`5/5` contrats `AD-19` conservés), `.venv/bin/python scripts/export_openapi.py --check` (`0-diff`), `pnpm site:sync` & `pnpm site:check` (`0` erreur).
- **Couche Sécurité** :
  - Isolation inter-utilisateurs sur `DELETE /users/me/mcp-tokens/{id}` (`404`), rejet `OBSERVER` / `READ_ONLY_OBSERVER` (`403 ERR_OBSERVER_MODE_READ_ONLY`), aucun secret en clair exposé dans `GET /users/me/mcp-tokens`, suppression complète du jeton hardcodé `"pat_mcp_9a8b7c6d5e4f3a2b1c0d"`.
- **Couche 5 (Playwright E2E)** :
  - `apps/web/e2e/support/firstAdmin.ts` mis à jour vers `sidebar-open-my-account-btn`.
