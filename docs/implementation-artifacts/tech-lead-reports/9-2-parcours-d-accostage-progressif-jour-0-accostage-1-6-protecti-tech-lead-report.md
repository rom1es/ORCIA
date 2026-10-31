# Story 9.2 — Parcours d'Accostage Progressif Jour 0 (`Accostage 1/6`), Protection Anti-*First-User Takeover* & Palier Progressif `1 Modèle → ≥ 2 Familles AD-10`

- **Date** : 2026-10-31
- **Story / Clé Sprint** : `9-2-parcours-d-accostage-progressif-jour-0-accostage-1-6-protecti` (`Epic 9`)
- **Auteur / Contexte** : Sécurisation du premier accès `/welcome-setup` contre les prises de contrôle concurrentes (*First-User Takeover*) par verrou exclusif `LOCK TABLE users IN EXCLUSIVE MODE` (`COUNT(*) FROM users == 0`) et jeton d'amorçage `ORCIA_BOOTSTRAP_TOKEN` (`HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN` pour `ORCIA_ENV != "local"`), activation du **Mode Essai Rapide** dès le 1er modèle LLM configuré puis déblocage automatique des **Gates Agentiques (`AD-10`)** dès la 2e famille orthogonale, et bandeau interactif de progression `Accostage 1/6` (`Section 2`, `AD-10`, `AD-16`, `AD-19`).
- **Commits associés** : `Story 9.2`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Au Jour 0 sur une instance vierge d'ORCIA (`COUNT(*) FROM users == 0`), deux risques opposés menacent l'adoption :
  1. **Risque de sécurité (*First-User Takeover*)** : Si deux requêtes concurrentes atteignent `/welcome-setup` simultanément ou si une instance exposée hors `local` (`ORCIA_ENV != "local"`) ne vérifie pas le jeton d'amorçage `ORCIA_BOOTSTRAP_TOKEN`, un attaquant pourrait créer le premier compte `PLATFORM_ADMIN`.
  2. **Risque de friction cognitive au Jour 0** : Exiger d'emblée $\ge 2$ familles de modèles LLM orthogonales avant même de pouvoir tester `Mon Assistant` bloque l'administrateur qui ne dispose que d'une clé API ou d'un `Ollama local`. Le système doit permettre un **Mode Essai Rapide** dès `1` modèle configuré (avec avertissement ambre non bloquant `⚠️ 1 seule famille de modèles configurée — Ajoutez une 2e famille dans Configuration › Modèles IA pour activer les Gates Agentiques AD-10`), puis déverrouiller les **Gates Agentiques (`AD-10`)** dès qu'une 2e famille distincte est validée, tout en guidant l'opérateur via le bandeau interactif **`Accostage 1/6`**.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_impact` sur `repo: "ORCIA"`)** :
  - `ModelRouterService.evaluate_orthogonality` (`packages/orcia-core/src/orcia_core/bootstrap/models.py`) : `risk: LOW`, `impactedCount: 1` (`enforce_orthogonality_gate`).
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 300 lignes`)** :
  - Création d'un module dédié `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` (`< 250 lignes`) encapsulant :
    - `InvalidBootstrapTokenError` (`HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN`) et `FirstUserAlreadyInitializedError` (`HTTP 409 ERR_FIRST_USER_ALREADY_INITIALIZED`) enregistrés dans le catalogue RFC 9457 (`orcia_kernel.errors`).
    - `ProgressiveDay0AccostageService` gérant :
      - La création atomique du premier `PLATFORM_ADMIN` (`LOCK TABLE users IN EXCLUSIVE MODE` + vérification `COUNT(*) FROM users == 0` + comparaison en temps constant `hmac.compare_digest` de `ORCIA_BOOTSTRAP_TOKEN` si `ORCIA_ENV != "local"`).
      - L'évaluation du palier progressif LLM (`UNCONFIGURED` $\rightarrow$ `QUICK_TRIAL_SINGLE_FAMILY` avec badge ambre $\rightarrow$ `FULL_ORTHOGONAL_AD10` avec Gates Agentiques débloquées).
      - La progression interactive `Accostage 1/6` à `6/6` (6 jalons Jour 0).
  - Création de la primitive `@orcia/ui` `ProgressiveDay0AccostageBanner.tsx` (`< 260 lignes`) pour `/welcome-setup` (Assistant de Bienvenue en 3 étapes) et le bandeau `Accostage 1/6` dans le `Cockpit`.

---

## 2. Plan d'Implémentation

### 2.1 Noyau Métier & Concurrence SQL (`packages/orcia-core/src/orcia_core/bootstrap/`)
- `packages/orcia-core/src/orcia_core/bootstrap/errors.py` :
  - Ajout de `InvalidBootstrapTokenError` (`HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN`) et `FirstUserAlreadyInitializedError` (`HTTP 409 ERR_FIRST_USER_ALREADY_INITIALIZED`).
- `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` :
  - `ProgressiveDay0AccostageService` (mémoire + exécution transactionnelle PostgreSQL 18 `LOCK TABLE users IN EXCLUSIVE MODE`).

### 2.2 Couche Backend FastAPI & Contrats OpenAPI (`apps/api/`)
- `apps/api/src/orcia_api/schemas/bootstrap.py` & `apps/api/src/orcia_api/routers/bootstrap.py` :
  - `GET /api/v1/bootstrap/accostage-status`
  - `POST /api/v1/bootstrap/welcome-setup/first-admin`
  - `POST /api/v1/bootstrap/welcome-setup/progressive-llm`
- Régénération du SDK OpenAPI 3.1 (`scripts/export_openapi.py` `0-diff`).

### 2.3 Design System (`@orcia/ui`) & Frontend (`apps/web/`)
- `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx` :
  - Bandeau interactif `Accostage 1/6` (`Cockpit`), badge ambre Mode Essai Rapide (`1 seule famille`) vs badge émeraude Gates Agentiques (`>= 2 familles AD-10`), et Assistant de Bienvenue en 3 étapes (`/welcome-setup`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/errors.py` | Modification | Ajout de `InvalidBootstrapTokenError` (`403 ERR_INVALID_BOOTSTRAP_TOKEN`) & `FirstUserAlreadyInitializedError` (`409`) |
| `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` | Création | Service `ProgressiveDay0AccostageService` (`LOCK TABLE users IN EXCLUSIVE MODE`, `ORCIA_BOOTSTRAP_TOKEN`, palier `1 Modèle -> >= 2 Familles AD-10` & `Accostage 1/6`) |
| `apps/api/src/orcia_api/schemas/bootstrap.py` | Modification | Schémas HTTP/OpenAPI pour `/welcome-setup` et `Accostage 1/6` |
| `apps/api/src/orcia_api/routers/bootstrap.py` | Modification | Endpoints `GET /accostage-status`, `POST /welcome-setup/first-admin` et `POST /welcome-setup/progressive-llm` |
| `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx` | Création | Primitive `@orcia/ui` du bandeau `Accostage 1/6` et de l'Assistant de Bienvenue 3 étapes |
| `tests/unit/test_epic_9_story_9_2_accostage_and_first_user.py` | Création | Tests unitaires & d'intégration PG18 sous concurrence (`LOCK TABLE users IN EXCLUSIVE MODE`) |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `>= 90 %` sur `progressive_accostage.py` et `ProgressiveDay0AccostageBanner.tsx`.
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/mypy --strict` : `0 error`
  - `.venv/bin/lint-imports` : `0 broken`
  - `pnpm turbo run lint typecheck test` : `0 error`

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 (`pytest` + `Vitest`)** : Validation de `ORCIA_BOOTSTRAP_TOKEN` (`ORCIA_ENV != "local"` -> `403 ERR_INVALID_BOOTSTRAP_TOKEN`), du Mode Essai Rapide (`1` modèle -> badge ambre) puis du déblocage automatique des Gates Agentiques (`>= 2` familles `AD-10`), et du bandeau `Accostage 1/6`.
- **Couche 2 (`testcontainers` PostgreSQL 18)** : Test de requêtes concurrentes sur table `users` vierge avec `LOCK TABLE users IN EXCLUSIVE MODE` garantissant qu'un seul premier administrateur `PLATFORM_ADMIN` est créé.
- **Couche 3 (`OpenAPI 0-diff`)** : `scripts/export_openapi.py --check` (`0 diff`).
