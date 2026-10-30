# Story 8.1 — Modèle d'Habilitations Hiérarchique à 6 Verbes (`RBAC/ABAC`), Délégation Bornée & Anti-Lockout (`AD-21`)

- **Date** : 2026-10-30
- **Story / Clé Sprint** : `8-1-modele-habilitations-rbac-abac-actions-hierarchie` (`Epic 8`)
- **Auteur / Contexte** : Gouvernance d'entreprise à 6 verbes atomiques (`create, read, update, delete, execute, grant`), clôture des tickets `ACTION_ITEM-8.1` (`DENY` prioritaire & `inheritance_block`), `ACTION_ITEM-8.2` (conditions ABAC sur `execute`) et `ACTION_ITEM-8.3` (`hidden_when_unauthorized` `HTTP 404` vs découverte passive `locked: true`), confinement de délégation (`grant`), anti-lockout (`422`) et révocation en frontière de `@DBOS.step` (`AD-6`, `AD-19`, `AD-21`).
- **Commits associés** : `Epic 8`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Le modèle initial à 5 permissions catalogue couvrait la découverte et l'exécution de base, mais la gouvernance post-Jour 0 (`/settings/*`) exigeait un modèle unifié à 6 verbes (`create, read, update, delete, execute, grant`) évalué hiérarchiquement le long de `org -> bu -> team -> workspace -> pack -> resource`.
- Il fallait également garantir l'isolation stricte entre `execute` et `read` sur les secrets, le confinement mathématique de la délégation ($\text{Droits délégués} \subseteq \text{Droits détenus}$), la prévention de tout auto-verrouillage administrateur (`ERR_ADMIN_LOCKOUT_PREVENTED`), et la révocation effective à la frontière de chaque `@DBOS.step`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - Analyse effectuée sur `orcia_core.permissions` (`evaluator.py`, `errors.py`, `service.py`) avec `repo: "ORCIA"` ; extension non cassante via `hierarchical_rbac.py`.
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Table `role_permission_grants` indexée sur `(subject_type, subject_id, scope_path)` et index partiel sur `effect = 'DENY' OR inheritance_block = TRUE`.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Clôture intégrale de `ACTION_ITEM-8.1`, `ACTION_ITEM-8.2` et `ACTION_ITEM-8.3` dans `HierarchicalRbacService`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- `infra/migrations/versions/0022_epic_8_settings_rbac_llm_tiers_and_wizards.py` :
  - Table `role_permission_grants` (`UUIDv7`, `subject_type`, `subject_id`, `scope_path`, `verb`, `effect`, `inheritance_block`, `conditions_jsonb`, `hidden_when_unauthorized`, `granted_by_user_id`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/src/orcia_core/permissions/hierarchical_rbac.py` :
  - `HierarchicalRbacService` (`resolve_effective_verbs`, `evaluate_resource_access`, `delegate_grant`, `revoke_grant`, `enforce_step_boundary_execution_guard`, `request_access`).
  - Événements Outbox `PermissionGranted`, `PermissionRevoked` et `AccessRequested` dans `packages/orcia-kernel/src/orcia_kernel/events.py`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/settings_and_studio.py` :
  - `POST /api/v1/settings/iam/evaluate` et `POST /api/v1/settings/iam/grants` avec enveloppes RFC 9457 (`403 ERR_GRANT_ESCALATION_FORBIDDEN`, `403 ERR_SECRET_CONFIG_READ_DENIED`, `404 ERR_RESOURCE_NOT_FOUND`, `422 ERR_ADMIN_LOCKOUT_PREVENTED`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `packages/ui/src/primitives/PermissionGuard.tsx` :
  - Garde déclarative supportant `hiddenWhenUnauthorized` et l'état verrouillé passif avec déclenchement de demande d'accès Outbox.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/0022_epic_8_settings_rbac_llm_tiers_and_wizards.py` | Création | Table `role_permission_grants` et index |
| `packages/orcia-core/src/orcia_core/permissions/hierarchical_rbac.py` | Création | Moteur RBAC/ABAC 6 verbes, délégation bornée, anti-lockout |
| `packages/ui/src/primitives/PermissionGuard.tsx` | Création | Primitive UI `<PermissionGuard />` |
| `tests/unit/test_epic_8_settings_rbac_llm_studio_and_wizards.py` | Création | Tests unitaires, Hypothesis et HTTP Story 8.1 |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `91.48 %` ($\ge 90\%$ requis).
- **Qualité statique & Architecture** : `ruff` (`0 warning`), `mypy --strict` (`0 error`), `lint-imports` (`5 kept, 0 broken`), `lint_spine.py` (`0 findings`).

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couches 1 à 5** : Invariants de précédence `DENY` / `inheritance_block` prouvés par Hypothesis, contrats OpenAPI 3.1 `0-diff` + Schemathesis validés, tests Vitest sur `<PermissionGuard />` passants.
