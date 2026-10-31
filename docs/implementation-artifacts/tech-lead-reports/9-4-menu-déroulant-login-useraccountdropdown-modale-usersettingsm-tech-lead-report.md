# Rapport Tech Lead — Story 9.4 : Menu Déroulant du Login (`UserAccountDropdown`), Modale « Paramètres de mon compte » (`UserSettingsModal` à 4 Onglets) & Double Persistance `0 ms` Anti-FOUC

- **Clé de Story** : `9-4-menu-déroulant-login-useraccountdropdown-modale-usersettingsm`
- **Epic** : Epic 9 — Coquille Ergonomique 4 Zones (Portals/KORE), Recherche `⌘K` 2 Vitesses, Compte `UserSettingsModal`, Accostage `1/6` & Aide Contextuelle Hybride `❓`
- **Date** : 2026-10-31
- **Auteur** : Équipe Tech Lead / Dev Senior ORCIA
- **Statut** : `done`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte & Problématique Métier / Technique
La **Story 9.4** sépare strictement la configuration personnelle de chaque utilisateur (`UserAccountDropdown` `280px` + modale centrée `UserSettingsModal` `720px × max 600px` à 4 onglets) de la configuration globale d'entreprise (`/settings`). Elle répond à quatre exigences d'architecture et d'UX (`Principe A.3`, `Principe M.4`, `AD-6`, `AD-19`, `AD-21`) :
1. **Menu rapide `UserAccountDropdown` (`280px`)** : ouvert au clic sur `👤 Login · [Casquette]` en haut à droite, avec sélecteur de Casquette métier, switches 1-clic (`☀️ Clair / 🌙 Sombre`, `FR / EN`), entrées `⚙️ Paramètres de mon compte...` (`g u`) et `🔗 Mes accès aux sources...`, et bouton `🚪 Se déconnecter` (`POST /api/v1/auth/logout`).
2. **Fermeture automatique et ouverture de `UserSettingsModal` (`720px × max 600px`)** : le clic sur `⚙️ Paramètres de mon compte...` (ou le raccourci `g u`) ferme automatiquement `UserAccountDropdown` et ouvre la modale à **4 onglets** :
   - **Onglet 1 (`🎨 Préférences & Affichage`)** : Thème (`light | dark | system`), Langue (`fr | en`), Casquette métier par défaut, ouverture auto de l'Aide `❓`, notifications `🔔`, et lien `💬 Personnaliser le comportement de Mon Assistant →` (sans dupliquer la zone de saisie Couche 5).
   - **Onglet 2 (`👤 Profil & Sécurité`)** : Identité, changement de mot de passe local `Argon2id`, `MFA TOTP`, révocation des sessions actives.
   - **Onglet 3 (`🔗 Accès aux sources (Passthrough)`)** : Jetons personnels Git/Jira/Confluence/Notion chiffrés `AES-256-GCM` (`AD-6`) via `<SecretField />` write-only et bouton `🔌 Tester mon jeton`.
   - **Onglet 4 (`💻 Clés IDE & MCP`)** : Génération et révocation instantanée (`< 10 ms` Redis) de jetons personnels scopés (`pat_mcp_*` hachés `SHA-256` en base, expiration obligatoire `30j` ou `90j`, plafond `RPM`, sélection des Espaces autorisés et des capacités exposées : `ASSISTANT`, `PUBLISHED_AGENTS`, `KB_GLOSSARY_SEARCH`, `STAGED_DRAFTS`) pour `/api/v1/mcp`, avec sélecteur de cible (**Tout l'Espace `/api/v1/mcp/spaces/<ws_slug>`** ou **Un agent précis `/api/v1/mcp/agents/<agent_slug>`**) et extrait JSON prêt à copier pour **VS Code / Cursor / Claude Code / Antigravity / JetBrains** (`Principe M.4`).
3. **Double Persistance `0 ms` Anti-FOUC** : tout changement de thème ou de langue écrit immédiatement (`0 ms`) dans `localStorage` (`orcia_theme`, `orcia_locale`), lu par un script synchrone dans `apps/web/index.html` avant le premier rendu React, et synchronise en arrière-plan via `PATCH /api/v1/users/me/preferences`.

### 1.2 Analyse d'Impact GitNexus
- **Symboles inspectés** :
  - `get_two_speed_search_service` (`apps/api/src/orcia_api/dependencies.py`) — `risk: LOW` (1 appelant direct dans `epic9_portal.py`).
  - `apps/api/src/orcia_api/routers/auth.py` — expose déjà `POST /api/v1/auth/logout` révoquant le JWT et le Refresh Token `HttpOnly` dans Redis (`AD-6`).

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (`< 300-400` lignes)
- Création d'un module dédié `packages/orcia-core/src/orcia_core/permissions/user_preferences_and_mcp_tokens.py` (`< 260` lignes) gérant la persistance des préférences utilisateur et le cycle de vie des jetons `pat_mcp_*` hachés `SHA-256`.
- Création d'une primitive dédiée `@orcia/ui` `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` (`< 350` lignes) isolée dans `packages/ui`.

### 1.4 Tickets de Dette Technique / Refactoring Proactifs
- Aucun ticket de dette technique supplémentaire requis.

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Migrations Alembic (`infra/migrations/versions/`)
- Réutilisation des tables et schémas existants (`users`, `user_passthrough_credentials`, `workspace_customization_overrides`).

### 2.2 Noyau Hexagonal Python (`packages/orcia-core/src/orcia_core/permissions/`)
- Création de `packages/orcia-core/src/orcia_core/permissions/user_preferences_and_mcp_tokens.py` :
  - `UserAccountPreferences` & `UserPreferencesAndMcpTokenService.update_preferences(...)`.
  - `ScopedMcpPersonalTokenRecord`, `IssuedScopedMcpTokenResult`, `build_ide_mcp_json_snippet(...)`, `issue_mcp_token(...)` (préfixe `pat_mcp_`, hachage `SHA-256` en base, expiration obligatoire `30` ou `90` jours, plafond `RPM`, cible `/api/v1/mcp/spaces/<ws_slug>` ou `/api/v1/mcp/agents/<agent_slug>`) et `revoke_mcp_token(...)` (`< 10 ms` Redis).

### 2.3 API FastAPI (`apps/api`) & SDK OpenAPI (`packages/api-client`)
- Ajout des schémas Pydantic v2 (`UserPreferencesUpdateRequest`, `UserPreferencesResponse`, `McpPersonalTokenCreateRequest`, `McpPersonalTokenIssuedResponse`, `McpPersonalTokenMetadataItem`, `McpPersonalTokenRevokeResponse`) dans `apps/api/src/orcia_api/schemas/auth_and_org.py`.
- Ajout des routes `GET /api/v1/users/me/preferences`, `PATCH /api/v1/users/me/preferences`, `GET /api/v1/users/me/mcp-tokens`, `POST /api/v1/users/me/mcp-tokens` et `DELETE /api/v1/users/me/mcp-tokens/{token_id}` dans `apps/api/src/orcia_api/routers/epic9_portal.py`.

### 2.4 Interface SPA Vite + TanStack Router (`@orcia/ui` & `apps/web`)
- Ajout du script synchrone Anti-FOUC (`0 ms`) dans `apps/web/index.html` lisant `localStorage.getItem("orcia_theme")` et `localStorage.getItem("orcia_locale")` avant le premier rendu React.
- Création de `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` (`UserAccountDropdown` `280px` + `UserSettingsModal` `720px × max 600px` à 4 onglets avec fermeture automatique du dropdown).

---

## 3. Bilan des Modifications & Résultats (Après Implémentation)

### 3.1 Fichiers Créés ou Modifiés
| Fichier | Action | Lignes | Description |
| :--- | :--- | :---: | :--- |
| `packages/orcia-core/src/orcia_core/permissions/user_preferences_and_mcp_tokens.py` | Créé | ~250 | Préférences utilisateur & jetons MCP scopés `pat_mcp_*` hachés `SHA-256` |
| `apps/api/src/orcia_api/schemas/auth_and_org.py` | Modifié | ~295 | Schémas Pydantic v2 pour préférences et jetons MCP |
| `apps/api/src/orcia_api/routers/epic9_portal.py` | Modifié | ~220 | Endpoints `/api/v1/users/me/preferences` et `/api/v1/users/me/mcp-tokens` |
| `apps/web/index.html` | Modifié | ~30 | Script synchrone Anti-FOUC (`orcia_theme`, `orcia_locale`) |
| `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` | Créé | ~340 | `UserAccountDropdown` (`280px`) & `UserSettingsModal` (`720px`, 4 onglets) |
| `tests/unit/test_epic_9_story_9_4_user_preferences_and_mcp_tokens.py` | Créé | ~195 | Tests unitaires Python et API |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Garde-fous (`AD-19`)
- **Couche 1 (Unitaires `pytest` & `Vitest`)** : `100 %` verts, couverture $\ge 90 \%$.
- **Garde-fous d'architecture** : `ruff check`, `mypy --strict`, `lint-imports` (`5 kept, 0 broken`), `pnpm turbo run lint typecheck test` (`0` erreur).
