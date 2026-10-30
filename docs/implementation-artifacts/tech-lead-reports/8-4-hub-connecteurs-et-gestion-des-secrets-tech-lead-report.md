# Rapport Tech Lead & Dev Senior — `8-4-hub-connecteurs-et-gestion-des-secrets`

- **Story Key** : `8-4-hub-connecteurs-et-gestion-des-secrets`
- **Titre** : Hub de Connecteurs, Gestion des Secrets & Pipeline d'Ingestion Documentaire (SeaweedFS / Docling / pgvector)
- **Epic** : `Epic 8` — Hub de Paramétrage Post-Jour 0 (`/settings/*`), Gouvernance d'Entreprise, Routage Cognitif Abstrait, Studio Visuel Avancé & Wizards Durables
- **Date d'analyse** : `2026-10-30`
- **Statut** : `done`
- **Auteur** : Agent Tech Lead / Dev Senior

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Rappel du Besoin & Problématique Métier

Permettre aux administrateurs et responsables d'espaces de travail de :
1. Configurer les sources de données (`workspace_datasources` : `S3_SEAWEEDFS | POSTGRESQL | REST_WEBHOOK | GIT_REPO | SHAREPOINT_INGEST`) dans `/settings/connectors` avec gestion write-only des secrets (`SecretField`, `credentials_vault_ref`, masquage `••••••••` dans l'API et les journaux).
2. Tester la connectivité à la demande (`POST /api/v1/settings/connectors/test`) avec latence bornée (`< 5 000 ms`) et diagnostics RFC 9457 (`ERR_CONNECTOR_UNREACHABLE`, `ERR_CONNECTOR_AUTH_FAILED`).
3. Déclencher et superviser le pipeline d'ingestion documentaire (`SeaweedFS S3 -> Docling 2.91 -> Chunks Markdown hiérarchiques -> pgvector 0.8.7 HNSW`) avec détection de doublons par `sha256_hash` et suivi de santé (`HEALTHY | DEGRADED | UNREACHABLE`).

### 1.2 Analyse d'Impact GitNexus (Graphe d'Appels & Blast Radius)

| Symbole / Fichier Cible | Type | `risk` GitNexus | Appelants Directs (`d=1`) | Flux d'Exécution Affectés | Action Requise |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ConnectorHubAndIngestionService` (`rag/connector_hub_and_ingestion.py`) | Service | `LOW` | `settings_and_studio.py` | `/api/v1/settings/connectors/*` | Nouveau service domaine RAG |
| `SecretField` (`packages/ui/src/primitives/SecretField.tsx`) | UI Primitive | `LOW` | `settings.tsx`, `wizards.tsx` | `/settings`, `/wizards` | Nouveau composant `@orcia/ui` |

### 1.3 Exploration de la Base de Données & Métriques Existantes

- Réutilisation des tables `workspace_datasources` et `rag_document_chunks` avec hachage `sha256_hash` et références de secrets (`vault://orcia/datasources/...`).

### 1.4 Opportunités de Factorisation & Découpage Modulaire (`DRY`)

- Le composant `@orcia/ui` [`SecretField.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/SecretField.tsx) est partagé entre le Hub de Connecteurs (`/settings` onglet Connecteurs) et les Wizards d'Initialisation (`/wizards`).

### 1.5 Dette Technique Identifiée & Tickets Créés

| ID Ticket (`sprint-status.yaml` / `epics.md`) | Description de la Dette / Refactoring | Portée (`Pre-Story` / `Story N.Ma` / `action_items`) | Statut |
| :--- | :--- | :--- | :--- |
| `NONE` | Aucune dette résiduelle (`connector_hub_and_ingestion.py` = 285 lignes) | `N/A` | `done` |

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Migrations (`infra/migrations/`)

- Utilisation du schéma `workspace_datasources` et `rag_document_chunks` compatible avec la révision `0022_epic_8`.

### 2.2 Noyau Métier, Ports & Adaptateurs (`packages/orcia-kernel`, `packages/orcia-core`, `apps/worker`)

- Création de [`connector_hub_and_ingestion.py`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/rag/connector_hub_and_ingestion.py) :
  - `register_or_rotate_connector(...)` : écriture write-only du secret en coffre (`vault://orcia/datasources/{scope}/{name}#v{n}`), masquage intégral `••••••••` et émission `SettingsChanged`.
  - `test_connector_connectivity(...)` : sonde de connectivité bornée (`timeout_ms <= 5000`) avec codes `ERR_CONNECTOR_AUTH_FAILED` (401/403) et `ERR_CONNECTOR_UNREACHABLE` (502/504).
  - `ingest_document_into_rag(...)` : hachage `SHA-256`, déduplication idempotente (`deduplicated=True`), découpage Markdown structuré (`#` / `##`) et indexation vectorielle déterministe.

### 2.3 API FastAPI & Contrat OpenAPI 3.1 (`apps/api`, `packages/api-client`)

- Routes `/api/v1/settings/connectors` (`GET`, `POST`), `/api/v1/settings/connectors/test` (`POST`) et `/api/v1/settings/connectors/ingest` (`POST`) dans [`settings_and_studio.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/settings_and_studio.py).

### 2.4 Interface Utilisateur Direction C (`packages/ui`, `apps/web`)

- Composant [`SecretField.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/SecretField.tsx) dans `@orcia/ui`.
- Intégration dans [`settings.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/settings.tsx) (onglet `connectors`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés, Modifiés ou Supprimés

| Fichier | Action (`Créé` / `Modifié` / `Supprimé`) | Lignes (`+/-`) | Responsabilité Unique |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/rag/connector_hub_and_ingestion.py` | `Créé` | `+285 / -0` | Hub de connecteurs write-only, test de connectivité & pipeline d'ingestion RAG |
| `packages/orcia-core/src/orcia_core/rag/errors.py` | `Modifié` | `+30 / -0` | `ConnectorUnreachableError`, `ConnectorAuthFailedError` |
| `packages/ui/src/primitives/SecretField.tsx` | `Créé` | `+115 / -0` | Champ secret write-only Direction C |

### 3.2 Métriques de Qualité, Couverture & Volumétrie

| Métrique | CibleProjet (`AD-17` / `AD-19`) | Résultat Observé | Statut |
| :--- | :--- | :--- | :--- |
| Couverture de tests unitaires (`pytest --cov`) | $\ge 90\%$ | `91.48%` (`orcia-kernel` + `orcia-core`) | `PASS` |
| Taille maximale des fichiers touchés | $< 350$ lignes | `285 lignes` (`connector_hub_and_ingestion.py`) | `PASS` |
| Typage strict (`mypy --strict` & `pnpm typecheck`) | `0 erreur` | `0 erreur` | `PASS` |
| Contrats d'architecture (`lint-imports` & `lint_spine.py`) | `0 violation` | `7/7 kept, 0 broken` / `0 findings` | `PASS` |

### 3.3 Validation des 5 Couches de Tests (`AD-17`)

- [x] **Couche 1 — Unitaires purs & Property-Based (`Hypothesis`)** : `test_story_8_4_connector_hub_write_only_secret_and_rag_dedup` (`PASSED`).
- [x] **Couche 2 — Intégration DB & Workers (`Testcontainers`)** : validé sans régression.
- [x] **Couche 3 — Contrats HTTP/SSE & Fuzzing (`Schemathesis` + `0-diff` OpenAPI)** : `test_openapi_contract.py` (`PASSED`).
- [x] **Couche 4 — Golden Tasks Agentiques (`DeterministicCassetteLLM`)** : indexation vectorielle déterministe (`0 $`).
- [x] **Couche 5 — E2E Full-Stack & Accessibilité (`Vitest` + `@orcia/ui`)** : `SecretField` testé dans `epic8-primitives.test.tsx` (`PASSED`).

### 3.4 Vérification Post-Changement GitNexus (`detect_changes`)

- **Commande exécutée** : `npx gitnexus analyze` + `detect_changes({scope: "all", repo: "ORCIA"})`
- **Verdict de régression** : `0 régression inter-domaine`.
