# Story 8.3 — Coquille `/settings/*`, Paramètres Versionnés (`ETag`/`If-Match`), Protocole Write-Only des Secrets & Replay Outbox (`AD-21`, `DEC-SEC-01`)

- **Date** : 2026-10-30
- **Story / Clé Sprint** : `8-3-coquille-settings-tanstack-router-permission-guards` (`Epic 8`)
- **Auteur / Contexte** : Table versionnée `platform_settings` protégée par concurrence optimiste (`If-Match` / `ETag` `428`/`412`), protocole write-only `SecretInput` (`keep | set | clear`) et `SecretStatus` (`sha256:<8-hex salé par id>`), événement Outbox `SettingsChanged`, test canari `DEC-SEC-01`, coquille `/settings` TanStack Router et replay Outbox borné (`<= 500`, `dry_run: true` par défaut).
- **Commits associés** : `Epic 8`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Les paramètres post-Jour 0 (`/settings/*`) nécessitaient une protection contre les écrasements concurrents entre administrateurs (`ETag` / `If-Match`) et une garantie absolue qu'aucun secret en clair ne puisse jamais être relu par l'API ou fuiter dans `platform_settings`, `domain_events_outbox` ou les logs (`DEC-SEC-01`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - Intégration directe avec `SecretProviderPort` et `SecretRef` (`orcia_kernel.secret_ports`, `repo: "ORCIA"`).
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Table `platform_settings` avec contrainte `UNIQUE (scope_level, scope_id, category, key)` et empreinte salée `sha256:<8-hex>`.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Factorisation de `SecretInputSpec`, `SecretStatusView` et `compute_salted_secret_fingerprint` réutilisés par le Hub des Connecteurs (`Story 8.4`) et les Wizards durables (`Story 8.6`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- `infra/migrations/versions/0022_epic_8_settings_rbac_llm_tiers_and_wizards.py` :
  - Table `platform_settings` (`UUIDv7`, `scope_level`, `scope_id`, `category`, `key`, `value_jsonb`, `secret_ref`, `secret_fingerprint`, `version`, `etag`, `updated_by`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/src/orcia_core/permissions/platform_settings.py` :
  - `PlatformSettingsService` (`list_settings`, `get_setting`, `upsert_initial_setting`, `patch_setting`, `replay_outbox_events`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/settings_and_studio.py` :
  - `GET /api/v1/settings/entries`, `PATCH /api/v1/settings/entries` (en-tête `If-Match` obligatoire -> `428`, conflit -> `412`), `POST /api/v1/admin/outbox/replays`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `packages/ui/src/primitives/SecretField.tsx` et `apps/web/src/routes/settings.tsx` :
  - Composant write-only `<SecretField />` et coquille `/settings` à 6 onglets (`iam`, `connectors`, `ai-models`, `packs`, `workflows`, `audit`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/permissions/platform_settings.py` | Création | Service `platform_settings`, `ETag`/`If-Match`, `SecretInput`/`SecretStatus` & replay Outbox |
| `packages/ui/src/primitives/SecretField.tsx` | Création | Primitive write-only `<SecretField />` |
| `apps/web/src/routes/settings.tsx` | Création | Route `/settings` TanStack Router |
| `tests/unit/test_epic_8_settings_rbac_llm_studio_and_wizards.py` | Création | Tests `428`/`412`, test canari `DEC-SEC-01` et replay Outbox |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `91.48 %` ($\ge 90\%$ requis).
- **Qualité statique & Architecture** : `ruff` (`0 warning`), `mypy --strict` (`0 error`), `lint-imports` (`5 kept, 0 broken`), `lint_spine.py` (`0 findings`).

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couches 1 à 5** : Test canari `DEC-SEC-01` vérifiant `0` fuite de secret en clair dans les réponses HTTP, les enregistrements `platform_settings` et les événements `SettingsChanged`.
