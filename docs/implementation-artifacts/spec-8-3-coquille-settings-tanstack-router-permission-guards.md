# Spécification d'Implémentation — Story 8.3 : Coquille `/settings/*`, Paramètres Versionnés (`ETag`/`If-Match`), Protocole Write-Only des Secrets & Replay Outbox (`AD-21`, `DEC-SEC-01`)

- **Story Key** : `8-3-coquille-settings-tanstack-router-permission-guards`
- **Epic** : `Epic 8` (`AD-21`, `DEC-SEC-01`, `UX-DR17`)

## 1. Critères d'Acceptation & Invariants
1. **Concurrence Optimiste sur `platform_settings` (`If-Match` / `ETag`)** :
   - Toute mutation `PATCH /api/v1/settings/entries` sans en-tête `If-Match` est rejetée avec `HTTP 428 ERR_PRECONDITION_REQUIRED`.
   - Toute mutation avec un `ETag` obsolète est rejetée avec `HTTP 412 ERR_SETTINGS_VERSION_CONFLICT`.
   - Toute mutation valide incrémente `version`, calcule le nouvel `ETag` et publie `SettingsChanged` dans `domain_events_outbox`.
2. **Protocole Write-Only `SecretInput` / `SecretStatus` & Test Canari (`DEC-SEC-01`)** :
   - Mutations de secrets via `SecretInputSpec(action="keep" | "set" | "clear", plaintext_value=...)`.
   - Lecture via `SecretStatusView(configured: bool, fingerprint: "sha256:<8-hex salé par id>", updated_at, updated_by)` — aucun secret en clair n'est jamais retourné ni journalisé.
3. **Coquille `/settings` & Primitives `@orcia/ui`** :
   - Route `/settings` avec onglets `iam`, `connectors`, `ai-models`, `packs`, `workflows`, `audit`, protégés par `<PermissionGuard />` et utilisant `<SecretField />`.
4. **Replay Outbox Borné (`/api/v1/admin/outbox/replays`)** :
   - Limité à `max_events <= 500`, `dry_run: true` par défaut, restreint aux consommateurs idempotents enregistrés.
