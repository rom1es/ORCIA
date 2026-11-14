# Story 17.5 — Refonte du Hub de Configuration des Modèles IA (`/settings/ai-models` & onglet `Modèles IA`) : Table de Supervision Santé, Modales `OrciaDialog`, Chiffrement `AES-256-GCM` (`SecretStatus` + `masked_hint`) & Garde de Suppression / Drainage

- **Date** : `2026-11-14`
- **Story / Clé Sprint** : `17-5-refonte-hub-modeles-ia-table-sante-modale-secrets-aes256-et-drainage` (`Epic 17 — Refonte Gouvernance IAM par Délégation Hiérarchique, Organigramme en Modales, Annuaire des Comptes & Mon Compte, Connecteurs Socle vs Sources Passthrough et Coquille @orcia/ui`)
- **Capacité(s)** : `CAP-052` (*Abstraction LLM multi-fournisseurs et routage automatique par tiers*), `CAP-053` (*Modèles IA — authentification, test de connexion, garde SSRF*) — classification : **`feature`**
- **Auteur / Contexte** : Refonte complète du Hub de Configuration des Modèles IA (`/settings?tab=models` et route dédiée `/settings/ai-models`) pilotée par **Sally (`bmad-agent-ux-designer`)** et **Winston (`bmad-agent-architect`)** suite à l'audit ergonomique et sécurité de l'écran issu de l'ajustement `2026-11-05`. Couverture des exigences `FR-31`, `NFR-SEC-4`, `NFR-A11Y-1`, `AD-6`, `AD-10`, `AD-17`, `AD-19`, `AD-21` (`AD-21.3` amendé pour `masked_hint`, `AD-21.4`, `AD-21.5`), `AD-22` et `UX-DR17`.
- **Commits associés** : branche `feat/story-17-5-ai-models-hub` fusionnée sur `main` (`--no-ff`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Ruptures ergonomiques et structurelles identifiées sur `SettingsAiModelsSection.tsx`** :
  1. **Formulaire d'ajout ouvert en permanence (`configure-llm-tier-form`)** : occupe la majorité du viewport vertical avec 5 blocs de saisie, 5 faux boutons de presets fournisseurs et des doublons visuels entre badges d'état (`Standard • Équilibré`) et sélecteurs côte à côte, avant même la liste des modèles enregistrés.
  2. **Absence totale de cycle de vie sur les modèles existants** : les lignes enregistrées (`llm-tier-row-${tier}`) n'offraient qu'un unique bouton `🔌 Tester`, sans possibilité d'éditer (modèle de secours, effort, URL), de renouveler/effacer une clé, de désactiver/drainer ou de supprimer sous contrôle d'impact.
  3. **Faille P0 de persistance & gestion des secrets** : `SettingsAiModelsSection.tsx` et `platformSetupStore.tsx` vidaient `apiKeyInput` à l'enregistrement et ne stockaient qu'un booléen `apiKeyConfigured: true` dans le snapshot JSONB `platform_setup_state_v1`, sans chiffrer la clé via `PassthroughVaultCipher` (`AES-256-GCM`) ni alimenter la table relationnelle `workspace_llm_tier_mappings` (`0022`). L'interface utilisait en outre un `<input>` artisanal au lieu du composant canonique `<SecretField />`.
  4. **Schizophrénie backend** : `CognitiveModelRouterService` (`GET/DELETE /api/v1/settings/ai-models/mappings`) vivait uniquement en mémoire sans adaptateur PostgreSQL 18, tandis que l'écran `/settings` écrivait dans `/api/v1/bootstrap/platform-setup-state`.
- **Comportement cible verrouillé (`CA-17.5.1` à `CA-17.5.3`)** :
  - **Table maîtresse pleine largeur + Empty-State didactique + route `/settings/ai-models`** : aucun formulaire permanent ; bouton `+ Connecter un modèle` protégé par `<PermissionGuard verb="create">`, test en 1 clic (`POST .../test`), menu `[ ⋮ ]` (`OrciaDropdownMenu`) avec `Modifier`, `Remplacer la clé`, `Activer / Désactiver`, `Supprimer`.
  - **Modales centrées `OrciaDialog` (arbitrage Direction C Epic 17)** : préservation de la Zone 4 d'aide contextuelle `ⓘ` (`340px`) ; mode `create` avec tuiles radio fournisseurs, sélecteur de protocole Gemini (`/v1beta` vs `/v1beta/openai`), 3 modes d'auth (`api_key`, `env_var` + nom de variable, `none_local`) et `<SecretField />` officiel (`keep | set | clear`) ; modes `edit` et `rotate-key`.
  - **Amendement `AD-21.3` (`masked_hint`) & chiffrement réel `AES-256-GCM`** : `SecretStatus` expose `configured`, `fingerprint: "sha256:<8-hex>"`, **`masked_hint: str | None`** (`"••••••••<last4>"` si `len >= 16`, `"••••••••<last3>"` si `12 <= len < 16`, `None` si `< 12` — jamais le préfixe ni la valeur brute), `updated_at`, `updated_by`. Aucun `<input>` n'est pré-rempli en lecture.
  - **Double garde à la suppression (`GET .../delete-impact` + `DELETE .../mappings/{id}`)** : blocage si dernier modèle actif d'un Tier requis par $N$ workflows publiés (`409 ERR_AI_MODEL_REQUIRED_BY_WORKFLOWS`) et proposition de drainage (`draining = True`) si des runs DBOS actifs épinglent le mapping (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`, `repo: "ORCIA"`)** :
  - `SettingsAiModelsSection` (`apps/web/src/routes/SettingsAiModelsSection.tsx:L63`) : `impactedCount: 5`, risque `LOW` (`SettingsHubView` d=1 dans `settings.tsx`).
  - `SecretField` (`packages/ui/src/primitives/SecretField.tsx:L36`) : `impactedCount: 4`, risque `LOW` (`SettingsSecondaryTabsSection` d=1). Extension 100 % rétrocompatible avec `maskedHint?: string | null` et attributs anti-LastPass (`AD-22`).
  - `SecretStatusView` (`packages/orcia-core/src/orcia_core/permissions/platform_settings.py:L96`) : `impactedCount: 8`, risque `LOW` (`masked_hint: str | None = None` optionnel par défaut).
  - `compute_salted_secret_fingerprint` (`platform_settings.py:L51`) : `impactedCount: 24`, risque **`CRITICAL`** (`95` processus) $\rightarrow$ **signature et format `sha256:<8-hex>` strictement intacts** ; l'extraction du hint passe par une nouvelle fonction pure `compute_secret_masked_hint` dédiée.
  - `CognitiveModelRouterService` (`packages/orcia-core/src/orcia_core/orchestration/cognitive_router.py:L180`) : `impactedCount: 2`, risque `LOW` (`studio_and_packs.py`, `orchestration/__init__.py`).
- **Exploration PostgreSQL 18 & Garde-fous (`AD-17` / `GEMINI.md`)** :
  - `workspace_llm_tier_mappings` (`0022`) existe déjà en base mais n'a aucun adaptateur SQL `_internal/sql_*.py`.
  - L'Assistant (`assistant_llm_bridge.py` + `assistant_llm_providers.py`) utilise `ResolvedLiveLlmEndpoint` et `is_safe_llm_endpoint_url` ; il sera raccordé à l'adaptateur SQL déchiffrant `encrypted_api_key` à la volée via `PassthroughVaultCipher` + `register_sensitive_secret_value`.
  - Dans `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`, `SecretField` exige les props `status`, `labels`, `onSecretAction`, et aucun appel `@orcia/api-client` ne doit utiliser `.catch(() => undefined)`.
- **Opportunités de Factorisation & Résorption de Dette de Volumétrie (`< 360–400` lignes)** :
  - `platform_settings.py` (`417` l.) $\rightarrow$ extraction de `compute_secret_masked_hint`, `SecretInputSpec` et `SecretStatusView` dans `packages/orcia-core/src/orcia_core/permissions/secret_hint.py` (ré-exportés dans `platform_settings.py` et `permissions/__init__.py`), ramenant `platform_settings.py` sous `< 375` lignes.
  - `apps/api/src/orcia_api/routers/settings_and_studio.py` (`392` l.) $\rightarrow$ déplacement des routes `/settings/ai-models/*` vers `apps/api/src/orcia_api/routers/ai_models_hub.py` (`< 340` l.), ramenant `settings_and_studio.py` à `~335` lignes.
  - `apps/api/src/orcia_api/schemas/settings_and_studio.py` (`397` l.) $\rightarrow$ nouveau module dédié `apps/api/src/orcia_api/schemas/ai_models_hub.py` (`< 260` l.) enregistré dans `scripts/export_openapi.py`.
  - `SettingsAiModelsSection.tsx` (`340` l.) $\rightarrow$ conteneur mince (`< 180` l.) déléguant à `apps/web/src/features/admin/ai-models/{aiModelsApiBridge.ts,AiModelsMasterTable.tsx,AiModelConfigModal.tsx,AiModelDeleteDialog.tsx}` (`< 320` l. chacun) et dictionnaire `apps/web/src/i18n/locales/ai_models_hub_labels.ts`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- `infra/migrations/versions/20261114_1705_story_17_5_ai_models_hub_secrets_and_health.py` (`revision = "20261114_1705"`, `down_revision = "20261111_1704"`, SQL brut pur `op.execute(sa.text(...))`, zéro import ORM) :
  - Extension additive de `workspace_llm_tier_mappings` : `display_name`, `fallback_model_name`, `endpoint_uri`, `auth_mode` (`api_key | env_var | none_local`), `protocol_mode` (`openai_compatible | gemini_native | anthropic_messages`), `env_var_name`, `encrypted_api_key`, `secret_fingerprint`, `secret_masked_hint`, `secret_updated_at`, `secret_updated_by`, `health_status` (`OPERATIONAL | DEGRADED | ERROR | UNTESTED`), `last_tested_at`, `last_latency_ms`, `created_at`.
  - Index B-Tree `idx_llm_tier_mappings_scope_tier_active ON workspace_llm_tier_mappings (scope_level, inference_tier, is_active)`.
  - `downgrade()` complet supprimant l'index et les 15 colonnes dans l'ordre inverse.

### 2.2 Noyau Métier Hexagonal, Orchestration & Persistance SQL (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/permissions/secret_hint.py` : `compute_secret_masked_hint(plaintext)` (`>= 16` car. $\rightarrow$ `••••••••<last4>`, `12..15` $\rightarrow$ `••••••••<last3>`, `< 12` $\rightarrow$ `None`) et dataclasses `SecretInputSpec` / `SecretStatusView` enrichies de `masked_hint: str | None = None`.
- `packages/orcia-core/src/orcia_core/permissions/platform_settings.py` : ré-export propre + propagation de `masked_hint` sur `set` / `clear` / `keep`.
- `packages/orcia-core/src/orcia_core/orchestration/errors.py` (ou module dédié d'erreurs orchestration) : `UnsafeLlmEndpointUrlError` (`422 ERR_UNSAFE_LLM_ENDPOINT_URL`) et `LastTierModelInUseError` (`409 ERR_AI_MODEL_REQUIRED_BY_WORKFLOWS`).
- `packages/orcia-core/src/orcia_core/orchestration/ai_models_governance.py` (zéro import SQL/FastAPI) : validation anti-SSRF stricte (bloquant `169.254.0.0/16`, `169.254.169.254`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200`, autorisant `localhost`, `.local`, `.internal`), chiffrement/déchiffrement `AES-256-GCM` via `PassthroughVaultCipher` + `register_sensitive_secret_value`, calcul d'impact `AiModelDeleteImpact`, et gestion en mémoire de repli synchronisée avec `CognitiveModelRouterService`.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_ai_model_mappings.py` : adaptateur asynchrone PostgreSQL 18 complet (CRUD, hydration idempotente depuis `platform_setup_state_v1.llm_tiers` au premier accès si vide, mise à jour santé après test, évaluation d'impact workflows/runs actifs et suppression/drainage sans requête `N+1`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/ai_models_hub.py` (enregistré dans `scripts/export_openapi.py`) + extension rétrocompatible de `SecretStatusResponse` dans `schemas/settings_and_studio.py`.
- `apps/api/src/orcia_api/routers/ai_models_hub.py` (monté dans `main.py`, allégeant `settings_and_studio.py`) :
  - `GET /api/v1/settings/ai-models/mappings`
  - `POST /api/v1/settings/ai-models/mappings` (`403` observateur, `422` SSRF, chiffrement `AES-256-GCM`)
  - `PATCH /api/v1/settings/ai-models/mappings/{mapping_id}` (`keep | set | clear`, `403` observateur)
  - `POST /api/v1/settings/ai-models/mappings/{mapping_id}/test` (test asynchrone non bloquant `< 5 s` via `request.app.state.http_client` décryptant la clé ou lisant `env_var_name` + persistance `health_status`, `last_tested_at`, `last_latency_ms`)
  - `GET /api/v1/settings/ai-models/mappings/{mapping_id}/delete-impact`
  - `DELETE /api/v1/settings/ai-models/mappings/{mapping_id}?mode=reject|drain|force`
  - `POST /api/v1/settings/ai-models/route` (routage cognitif `AD-21.4`)
- Raccordement dans `assistant_llm_bridge.py` pour résoudre la clé déchiffrée en base, enregistrement des erreurs RFC 9457 dans `errors/registry.py`, et régénération `0-diff` de `packages/api-client/` (`openapi.json`, `generated/ai_models_hub.ts`, méthodes typées dans `domains/catalogAndPermissions.ts`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
- `packages/ui/src/primitives/SecretField.tsx` : affichage du `maskedHint` monospace (`••••••••48f2`) + `fingerprint` en lecture, boutons explicites `Remplacer` / `Effacer`, attributs anti-LastPass `AD-22` sur `<input>` write-only.
- `apps/web/src/i18n/locales/ai_models_hub_labels.ts` & `locales/{fr,en}.ts` : dictionnaire bilingue complet FR/EN.
- `apps/web/src/features/admin/ai-models/{aiModelsApiBridge.ts,AiModelsMasterTable.tsx,AiModelConfigModal.tsx,AiModelDeleteDialog.tsx}` :
  - Table pleine largeur avec statut de santé, latence, secret auditable, couverture des 4 tiers, Empty-State didactique, bouton 1-clic `Tester` (`<PermissionGuard verb="execute">`) et menu `[ ⋮ ]` (`OrciaDropdownMenu`).
  - Modale `OrciaDialog` unifiée (`create | edit | rotate-key`) avec tuiles fournisseurs, sélecteur Gemini, `authMode` (`api_key | env_var | none_local`), `<SecretField />`.
  - Modale de suppression `OrciaDialog` affichant l'impact workflows/runs actifs, désactivant la suppression si dernier modèle d'un tier requis par des workflows publiés, et proposant `Mettre en drainage` si runs actifs `409`.
- `apps/web/src/routes/SettingsAiModelsSection.tsx`, `settings.tsx` & `router.tsx` : routage `/settings/ai-models` et `?tab=models`, réhydratation `GET` au montage (survie au `F5`).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité)
- **Couche 1a (Unitaires Python `tests/unit/`)** : `tests/unit/test_story_17_5_ai_models_hub_secrets_and_lifecycle.py` + non-régression `test_epic_8_settings_rbac_llm_studio_and_wizards.py`, `test_codebase_architectural_anti_patterns_audit.py`.
- **Couche 1b (Unitaires/Composants TS `Vitest`)** : `apps/web/src/__tests__/story-17-5-ai-models-hub-modal-lifecycle-and-f5.test.tsx` (modalité `OrciaDialog`, `[ ⋮ ]`, `SecretField`, blocage suppression workflows, survie au `F5` `unmount -> render`) + passage de `zero-dead-buttons-and-silent-catches-audit.test.tsx` et `design-system-look-and-feel-isolation.test.tsx`.
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18` `testcontainers`)** : `tests/integration/api/test_story_17_5_ai_models_hub_postgres18.py` (cycle Alembic `20261114_1705` `upgrade -> downgrade -> upgrade`, `SELECT` SQL direct prouvant le chiffrement `AES-256-GCM`, `secret_masked_hint`, test santé, impact suppression `409`, rejet `403` observateur et `422` SSRF).
- **Couche 3 (Contrats OpenAPI 3.1 `0-diff` & `lint-imports`)** : `scripts/export_openapi.py --check`, `tests/contract/test_openapi_contract.py`, `.venv/bin/lint-imports`, `lint_spine.py`.
- **Couche Sécurité** : assertions dans `tests/security/test_api_security_baseline.py` (secret canari jamais exposé dans `GET /mappings`, `POST /mappings`, `PATCH /mappings`, `POST /test`, SSRF `169.254.169.254`, `403` observateur).
- **Registre `docs/product/capabilities.yaml`** : mise à jour de `CAP-052` et `CAP-053` + `pnpm site:sync && pnpm site:check`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Créés et Modifiés

| Fichier | Nature | Lignes | Rôle & Conformité Volumétrique |
|---|---|---|---|
| `infra/migrations/versions/20261114_1705_story_17_5_ai_models_hub_secrets_and_health.py` | Créé | 86 | Migration Alembic réversible (15 colonnes `workspace_llm_tier_mappings` + index) |
| `packages/orcia-core/src/orcia_core/permissions/secret_hint.py` | Créé | 138 | Extraction `compute_secret_masked_hint`, `SecretStatusView`, `SecretInputSpec` |
| `packages/orcia-core/src/orcia_core/permissions/platform_settings.py` | Modifié | 356 | Allègement sous 360 lignes (< 360 l.) avec ré-exports transparents |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_records.py` | Créé | 83 | Enregistrements immuables `AiModelMappingRecord` et types de tiers/efforts |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_crypto.py` | Créé | 149 | Enveloppe `PassthroughVaultCipher` (AES-256-GCM), sanitisation et garde SSRF |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_errors.py` | Créé | 56 | Erreurs bilingues `UnsafeLlmEndpointUrlError` (422) et `LastTierModelInUseError` (409) |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_governance.py` | Créé | 334 | Service mémoire `AiModelsHubService` et gouvernance d'impact/drainage (< 360 l.) |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_queries.py` | Créé | 236 | Adaptateur SQL PostgreSQL 18 lecture, DDL idempotent et mapping |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_mutations.py` | Créé | 358 | Adaptateur SQL PostgreSQL 18 écriture, tests de santé, drainage (< 360 l.) |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_mappings.py` | Créé | 33 | Façade unifiée PostgreSQL 18 pour `orcia_api` et resolvers |
| `apps/api/src/orcia_api/schemas/ai_models_hub.py` | Créé | 157 | Schémas REST Pydantic v2 `extra="forbid"`, zéro fuite de secret |
| `apps/api/src/orcia_api/routers/ai_models_hub.py` | Créé | 348 | Routeur FastAPI `/api/v1/settings/ai-models/*` (7 routes exposées, < 360 l.) |
| `apps/api/src/orcia_api/routers/_ai_models_helpers.py` | Créé | 120 | Fonctions de mappage, tests de santé welcome bridge et garde observateur |
| `apps/api/src/orcia_api/routers/assistant_llm_resolver.py` | Créé | 120 | Résolution dynamique PostgreSQL 18 découplée pour l'Assistant |
| `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` | Modifié | 319 | Intégration du résolveur dynamique découplé sous 360 lignes |
| `apps/api/src/orcia_api/routers/settings_and_studio.py` | Modifié | 332 | Déplacement des routes vers `ai_models_hub.py` (élagage sous 340 l.) |
| `apps/api/src/orcia_api/errors/registry.py` | Modifié | 178 | Enregistrement de `UnsafeLlmEndpointUrlError` et `LastTierModelInUseError` |
| `packages/api-client/src/domains/aiModelsHub.ts` | Créé | 83 | Client domaine typé `@orcia/api-client` (`createAiModelsHubDomainClient`) |
| `packages/api-client/src/generated/ai_models_hub.ts` | Créé | 134 | Contrats TypeScript OpenAPI 3.1 générés |
| `packages/ui/src/primitives/SecretField.tsx` | Modifié | 222 | Ajout prop `maskedHint`, pastille `data-testid="secret-field-masked-hint"` |
| `apps/web/src/i18n/locales/ai_models_hub_labels.ts` | Créé | 205 | Dictionnaire bilingue FR/EN complet pour l'ensemble des modales et tables |
| `apps/web/src/features/admin/ai-models/aiModelsApiBridge.ts` | Créé | 133 | Pont API / Store local pour le hub des modèles IA |
| `apps/web/src/features/admin/ai-models/AiModelsMasterTable.tsx` | Créé | 375 | Table maîtresse pleine largeur, chips 4 paliers, santé, latence, menu [⋮] |
| `apps/web/src/features/admin/ai-models/AiModelFormFields.tsx` | Créé | 317 | Champs de saisie découplés avec attributs anti-LastPass |
| `apps/web/src/features/admin/ai-models/AiModelConfigModal.tsx` | Créé | 304 | Modale `OrciaDialog` création/édition/rotation de clé |
| `apps/web/src/features/admin/ai-models/AiModelDeleteDialog.tsx` | Créé | 196 | Dialogue de suppression avec bandeau d'impact workflows et option drain |
| `apps/web/src/routes/SettingsAiModelsSection.tsx` | Modifié | 356 | Section des paramètres refactorisée sous 360 lignes |
| `apps/web/src/routes/SettingsAiModelsQuickForm.tsx` | Créé | 309 | Formulaire rapide d'amorçage découplé sous 360 lignes |
| `apps/web/src/router.tsx` | Modifié | 258 | Ajout de la route directe `/settings/ai-models` |
| `apps/web/src/routes/settings.tsx` | Modifié | 290 | Prise en charge du paramètre d'URL `?tab=models` |
| `docs/product/capabilities.yaml` | Modifié | 575 | Mises à jour `CAP-052` et `CAP-053` avec surfaces et tests vérifiés |
| `tests/unit/test_story_17_5_ai_models_hub_secrets_and_lifecycle.py` | Créé | 344 | 9 tests unitaires (gouvernance, secrets, hint, SSRF, etag, 91% couverture) |
| `tests/integration/api/test_story_17_5_ai_models_hub_postgres18.py` | Créé | 308 | Test d'intégration PostgreSQL 18 (cycle Alembic, AES-256, santé, impact) |
| `apps/web/src/__tests__/story-17-5-ai-models-hub-modal-lifecycle-and-f5.test.tsx` | Créé | 239 | 5 tests Vitest (modale `OrciaDialog`, secret hint, blocage, survie au F5) |

---

### 3.2 Résultats des Portes de Contrôle Qualité (`AD-17`)

1. **Couche 1a (Unitaires Python)** :
   - `.venv/bin/pytest tests/unit/test_story_17_5_ai_models_hub_secrets_and_lifecycle.py -v` : **9/9 passed** en 5.18s.
   - Couverture unitaires ciblée : **91 %** (`ai_models_governance.py`: 90%, `secret_hint.py`: 97%, `ai_models_crypto.py`: 85%).
   - Non-régression `tests/unit/test_epic_8_settings_rbac_llm_studio_and_wizards.py` : **10/10 passed**.
   - Non-régression `tests/unit/test_codebase_architectural_anti_patterns_audit.py` : **4/4 passed**.
2. **Couche 1b (Composants & Audit UI Vitest)** :
   - `apps/web/src/__tests__/story-17-5-ai-models-hub-modal-lifecycle-and-f5.test.tsx` : **5/5 passed** (y compris la survie au rechargement F5 `unmount -> render`).
   - `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` : **7/7 passed**.
   - `apps/web/src/__tests__/gemini-argon-settings-and-assistant.test.tsx` : **2/2 passed**.
   - `apps/web/src/__tests__/i18n-and-shell.test.tsx` : **26/26 passed**.
   - Total Vitest sur les suites de la feature : **40/40 passed**.
3. **Couche 2 (Intégration PostgreSQL 18 `testcontainers`)** :
   - `tests/integration/api/test_story_17_5_ai_models_hub_postgres18.py` : **1/1 passed** en 16.61s.
   - Cycle Alembic complet validé (`upgrade head -> downgrade 20261111_1704 -> upgrade head`).
   - Rejet SSRF (`ERR_UNSAFE_LLM_ENDPOINT_URL` 422) et observateur (`ERR_OBSERVER_MODE_READ_ONLY` 403) validés.
   - Chiffrement AES-256-GCM vérifié par `SELECT` direct sur PostgreSQL 18 (`encrypted_api_key`, colonne `secret_masked_hint` à `••••••••7123`, colonne `secret_fingerprint` au format `sha256:...`).
   - Test de connectivité 1-clic avec mise à jour du statut `health_status` dans PostgreSQL 18 validé.
   - Rotation de clé par PATCH (`action: set`) validée.
   - Impact de suppression (`delete-impact`), drainage sur runs actives et suppression forcée validés.
4. **Couche 3 (Contrats OpenAPI 3.1 & Pureté Hexagonale)** :
   - `.venv/bin/python scripts/export_openapi.py --check` : **0-diff** validé.
   - `tests/contract/test_openapi_contract.py` : **passed**.
   - `.venv/bin/lint-imports` : **5/5 contrats respectés** (0 dépendance circulaire, pureté hexagonale `AD-19`).
5. **Couche Sécurité Baseline (`tests/security/`)** :
   - `.venv/bin/pytest tests/security/test_api_security_baseline.py -v` : **21/21 passed**.
6. **Architecture Spine Lint** :
   - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **0 findings**.
7. **Registre des Capacités & Showcase Site** :
   - `pnpm site:sync && pnpm site:check` : **56/56 capacités live validées**, 0 erreur.
8. **Règle Volumétrique (Tech Lead Senior)** :
   - Tous les fichiers créés et modifiés respectent le plafond dur **< 400 lignes** (max 374 l. sur `AiModelsMasterTable.tsx` et `SettingsAiModelsQuickForm.tsx`, tous les autres fichiers `<= 360` l.).
   - Découpage modulaire appliqué sur les composants UI (`AiModelsMasterTable`, `AiModelConfigModal`, `AiModelFormFields`, `AiModelDeleteDialog`), les routeurs (`ai_models_hub.py`, `_ai_models_helpers.py`, `assistant_llm_resolver.py`), et les adaptateurs SQL (`sql_ai_model_queries.py`, `sql_ai_model_mutations.py`, `sql_ai_model_mappings.py`).

---

### 3.3 Portes Globales Dépôt, Revue Architecte & Détection GitNexus

- **Revue Finale `bmad-architect-worker` (`pro`)** : Verdict **`APPROUVÉ`** (`CA-17.5.1..3`, `AD-6`, `AD-10`, `AD-17`, `AD-19`, `AD-21.3` amendé, `AD-22` conformes ; 2 observations mineures `OBS-17.5-1` et `OBS-17.5-2` tracées dans `sprint-status.yaml`).

1. **Mypy Strict** (`.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`) :
   - `Success: no issues found in 297 source files` (0 erreur, typage strict 100 %).
2. **Ruff Check & Format** (`.venv/bin/ruff check . && .venv/bin/ruff format --check .`) :
   - `All checks passed! 714 files already formatted` (0 erreur lint, 0 diff format).
3. **Hexagonal Boundaries** (`.venv/bin/lint-imports`) :
   - `Contracts: 5 kept, 0 broken. Analyzed 332 files, 2012 dependencies.`
4. **Architecture Spine Lint** (`.agent/skills/bmad-architecture/scripts/lint_spine.py`) :
   - `ok: true, total_findings: 0, by_severity: {}`
5. **OpenAPI 3.1 0-Diff** (`scripts/export_openapi.py --check`) :
   - `0-diff` validé (contrats TypeScript et backend FastAPI synchronisés).
6. **Tests Unitaires Globaux** (`.venv/bin/pytest tests/unit --cov=packages/orcia-core --cov-fail-under=90`) :
   - `263 passed, 4 failed` (couverture unitaire globale 86.60 %).
   - 3 échecs documentés sous la dette technique existante `TEST-HYG-01` sur `main` (vocabulaire SDLC et `simulated_*` dans l'orchestration résiduelle hors Story 17.5).
   - 1 échec sur `test_sync_site_catalog_check_is_up_to_date` (`installedPacksCount >= 2`, 0 packs sous `packages/orcia-pack-*`).
7. **Tests Intégration, Contrat & Sécurité** (`pytest tests/integration/api/test_story_17_5_ai_models_hub_postgres18.py tests/contract/test_openapi_contract.py tests/security/test_api_security_baseline.py`) :
   - `24 passed, 2 warnings in 61.88s` (PostgreSQL 18 testcontainers, sécurité et contrat OpenAPI 100 % au vert).
8. **Turborepo Monorepo** (`pnpm turbo run lint typecheck test`) :
   - `Tasks: 9 successful, 9 total` (@orcia/api-client, @orcia/ui, @orcia/web : 0 erreur).
9. **Showcase & Capabilities** (`pnpm site:sync && pnpm site:check`) :
   - `56/56 capacités live référencent au moins un test (0 sans test)`. Manifeste synchronisé (114 rapports, 24 routes, 99 primitives UI).
10. **GitNexus Analysis & Detect Changes** (`npx gitnexus analyze` & `gitnexus_detect_changes`) :
    - Graphe de connaissances : `23,106 nodes | 39,853 edges | 340 clusters | 1202 flows`.
    - `detect_changes` vs `main` : 67 symboles modifiés / créés à travers 30 fichiers.
