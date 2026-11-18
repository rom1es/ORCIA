# Story 22.5 — Persistance PG18 Packs Déclaratifs (`declarative_pack_bundles`) & Parcours Wizards Durables (`wizard_sessions`)

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`

- **Date** : 2026-11-18
- **Story / Clé Sprint** : `22-5-persistance-pg18-packs-declaratifs-et-wizards-durables` (`Epic 22` — Vague 1)
- **Capacité(s)** : `CAP-055`, `CAP-056`, `CAP-057`, `CAP-150` (ancrages `failed_e2e` sur `22-5`) — classification : `feature`
- **Auteur / Contexte** : `bmad-architect-worker` (initialisation pré-implémentation Story 21.9) — Résolution des chantiers **`REM-14`** et **`REM-15`** (`synthese-remediation-sally-winston-epic-21.md`). Couvre `FR-11`, `FR-13`, `FR-14`, `FR-28`, `FR-31`, `FR-34`, `FR-35`, `AD-1`, `AD-2`, `AD-16`, `AD-20`, `NFR-REL-1`, `UJ-19`.
- **Commits associés** : `En attente d'implémentation (initialisé sur 575cf4a)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Silo RAM `declarative_pack_bundles` (`REM-14`, `2` échecs)** :
  - `routers/packs.py:38-43` et `core_and_lifespan.py:291-294` chargent les manifests YAML depuis `packs/<domaine>/` dans la liste en mémoire `app.state.declarative_pack_bundles` **sans jamais synchroniser ni écrire en PostgreSQL 18**. Lors du test `18-catalog` #3, la table `declarative_pack_bundles` compte `0` ligne.
- **Double silo RAM sur `/wizards` & défauts d'ergonomie (`REM-15`, `2` échecs)** :
  - Côté frontend, `apps/web/src/routes/wizards.tsx:52-103` (`WizardsRouteComponent`) conserve `currentStep` et `status` en pur `useState` React sans jamais invoquer `@orcia/api-client` (`GET`/`POST` `/api/v1/wizards`). Au rafraîchissement `F5`, l'état est perdu et `wizard-completed-badge` n'apparaît pas.
  - Côté backend, `core_and_lifespan.py:291-294` instancie `DurableOnboardingWizardService()` sans `AsyncEngine`, laissant `wizard_sessions` vide en base PG18.
  - Visuellement (constat Sally sur `18-catalog` #4), l'écran `/wizards` affiche l'identifiant brut `sdlc_tech_lead · Étape 1/5`, une triple numérotation redondante `1. #1/5 1. Organisation & Équipe`, et pousse le formulaire de l'étape active sous la ligne de flottaison.
- **Échecs E2E associés & captures PNG archivées (`4` échecs E2E)** :
  - `18-catalog-packs-wizards-and-mcp-bench.spec.ts` #3 (`declarative_pack_bundles`, Desktop + Mobile ×2) : [Desktop Packs](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/desktop-cockpit--registre-des-packs-declaratifs-et-export-zip-persistent-dans-declarative-pack-bundles-ap--failed.png) · [Mobile Packs](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/mobile-companion--registre-des-packs-declaratifs-et-export-zip-persistent-dans-declarative-pack-bundles-ap--failed.png)
  - `18-catalog-packs-wizards-and-mcp-bench.spec.ts` #4 (`wizard_sessions` / `wizard-completed-badge`, Desktop + Mobile ×2) : [Desktop Wizards](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/desktop-cockpit--parcours-guide-d-initialisation-avec-retour-arriere-survit-a-f5-et-persiste-dans-wizard---failed.png) · [Mobile Wizards](../e2e-campaign-epic-21/screenshots/18-catalog-packs-wizards-and-mcp-bench/mobile-companion--parcours-guide-d-initialisation-avec-retour-arriere-survit-a-f5-et-persiste-dans-wizard---failed.png)

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `DurableOnboardingWizardService` (`packages/orcia-core/src/orcia_core/bootstrap/durable_wizards.py:136-297`) : **`impactedCount: 1`** (`direct: 1` — `bootstrap/__init__.py`), risque **`LOW`**, `epistemic: exact`.
- **Tables PostgreSQL 18 concernées** : `declarative_pack_bundles` (`20261108_0910_declarative_packs_and_workflows_v2.py`), `wizard_sessions` (`0022`).
- **Opportunités de Factorisation & Volumétrie** :
  - Réutiliser le patron d'upsert idempotent (`INSERT ... ON CONFLICT DO UPDATE`) de `bootstrap/seeder.py` pour synchroniser `packs/*/pack.yaml` dans `declarative_pack_bundles` au démarrage de FastAPI et lors de l'export/publication (`packs.py`).
  - Factoriser les libellés métier des profils de wizard (`sdlc_tech_lead` $\rightarrow$ libellé `i18n` FR/EN « Parcours Responsable Technique ») dans `apps/web/src/i18n/locales/*.ts`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Les tables `declarative_pack_bundles` (`20261108_0910`) et `wizard_sessions` (`0022`) existent déjà. Aucune migration destructive requise ; vérifier uniquement l'index/clé unique (`pack_id` / `version`) permettant l'upsert idempotent des bundles et `session_id` / `wizard_key` sur `wizard_sessions`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- **`declarative_pack_bundles` (`REM-14`)** :
  - Créer `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_declarative_packs.py` (ou dans `catalog/_internal/`) exposant `upsert_declarative_pack_bundles_sql(engine, bundles)` et `list_declarative_pack_bundles_sql(engine)` avec empreinte `SHA-256`.
- **`DurableOnboardingWizardService` (`REM-15`)** :
  - Créer `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_wizard_sessions.py` (`SqlWizardSessionRepository`) implémentant `start_or_resume_wizard`, `get_session`, `save_step_and_advance` (avec `step_back` préservant les saisies et transition `COMPLETED`).
  - Injecter ce repository dans `DurableOnboardingWizardService` sans importer SQLAlchemy dans `durable_wizards.py` (`AD-19`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` :
  - Synchroniser idempotemment les manifests chargés de `packs/` dans `declarative_pack_bundles` au lifespan (sans `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`).
  - Instancier `DurableOnboardingWizardService` avec son repository SQLAlchemy Asyncio sur PG18.
- `apps/api/src/orcia_api/routers/packs.py` : lire/écrire dans `declarative_pack_bundles` lors de la liste, publication et export ZIP (`GET`/`POST` `/api/v1/packs*`).
- `apps/api/src/orcia_api/routers/studio_and_wizards.py` : vérifier que `GET /api/v1/wizards`, `POST /api/v1/wizards/{type}/start`, `POST /api/v1/wizards/{id}/step` (avancer/reculer) retournent l'état persisté PG18 avec contrôle observateur `403`.
- Régénérer `@orcia/api-client` (`0-diff`) si des champs de réponse sont ajustés.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `apps/web/src/routes/wizards.tsx` :
  - Supprimer le `useState` éphémère de progression ; charger l'état initial via `@orcia/api-client` (`GET /api/v1/wizards`) au montage et persister chaque avancée/retour arrière par `POST` API, afin que `page.reload()` (`F5`) réaffiche exactement l'étape courante ou `wizard-completed-badge`.
- `DurableWizardRunnerView` (`packages/ui`) :
  - Remplacer `sdlc_tech_lead` par son libellé métier traduit (`i18n`).
  - Supprimer la triple numérotation `1. #1/5 1.` au profit d'un indicateur unique sobre (`Étape 1 sur 5`).
  - Remonter l'étape active et son formulaire au-dessus de la ligne de flottaison (`order`/layout compact).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a / 1b** : tests unitaires de `DurableOnboardingWizardService` (retour arrière sans perte, completion), tests Vitest `wizards.tsx` avec `unmount()` + `render()` prouvant la survie au `F5` sans `useState` local.
- **Couche 2 (`HTTP ➔ PG18`)** : bootstrap/export packs $\rightarrow$ `SELECT COUNT(*) FROM declarative_pack_bundles >= 1` ; parcours wizard `POST` + `step_back` + `complete` $\rightarrow$ `SELECT status, current_step FROM wizard_sessions`.
- **Couche 3 (`OpenAPI 0-diff`, `lint-imports`)** : validation `5 contracts kept, 0 broken`.
- **Couche Sécurité** : rejet `403 ERR_OBSERVER_MODE_READ_ONLY` sur mutations `/api/v1/packs` et `/api/v1/wizards/*`.
- **Couche 5 (Playwright E2E)** : passage au vert visé de `18-catalog` #3 et #4 (Desktop & Mobile, `F5` + `SELECT` PG18).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[En attente d'implémentation de la Story 22.5]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_wizard_sessions.py` | Création | *[À compléter après implémentation]* |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_declarative_packs.py` | Création | *[À compléter après implémentation]* |
| `apps/api/src/orcia_api/routers/packs.py` & `studio_and_wizards.py` | Modification | *[À compléter après implémentation]* |
| `apps/web/src/routes/wizards.tsx` & `@orcia/ui` | Modification | *[À compléter après implémentation]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[$\ge 90\%$ requis à mesurer après implémentation]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `pnpm typecheck`, `lint-imports`, `lint_spine.py`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- *[À compléter après exécution des 5 couches `AD-17` et Playwright Desktop/Mobile]*
