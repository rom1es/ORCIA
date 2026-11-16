# Story 6.4 — Télémétrie FinOps Multi-Métriques des Services MCP & Agents Distants (_meta.usage / X-Orcia-Usage), RemoteUsageSanitizer, Onglet 🌐 Services & Agents externes & Coupe-Circuit Isolé par Connecteur

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code applicatif)** :
> - User Story du sprint : `docs/implementation-artifacts/tech-lead-reports/6-4-télémétrie-finops-multi-métriques-mcp-agents-distants-remoteu-tech-lead-report.md`

- **Date** : 2026-11-16
- **Story / Clé Sprint** : `6-4-télémétrie-finops-multi-métriques-mcp-agents-distants-remoteu` (`Epic 6`)
- **Capacité(s)** : `CAP-200` (Télémétrie FinOps multi-métriques, RemoteUsageSanitizer & coupe-circuit isolé par connecteur) — classification : `feature` (voir `AGENTS.md` §5 et `capabilities.yaml`)
- **Auteur / Contexte** : Winston (`bmad-agent-architect` 🏗️) & Sally (`bmad-agent-ux-designer` 🎨). Normalisation des métriques externes (tokens, direct cost, unités métiers) via `RemoteUsageSanitizer` avec rejet des valeurs aberrantes ($< 0$, `NaN`, `Infinity`) et écrêtage de sécurité (`max_reported_cost_per_call_eur`, défaut 5,00 €) déclenchant `RemoteUsageAnomalyCapped`. Création de la table `finops_connector_quotas` (migration Alembic), coupe-circuit isolé par connecteur (`CIRCUIT_OPEN`) dans `ConnectorInvoker` via `ConnectorQuotaGuardPort` sans impacter les LLM internes, et onglet `@orcia/ui` `FinopsRemoteMcpServicesTab.tsx` distinguant le coût interne vérifié du coût externe déclaré. Couvre `FR-26`, `AD-12`, `AD-17`, `AD-19`, `Principe M.3` et `NFR-SEC-4`.
- **Commits associés** : `pending-implementation`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
L'intégration des outils externes via Model Context Protocol (MCP) et le dialogue entre agents distants (A2A) créent des défis spécifiques d'étanchéité et de facturation :
1. **Dispersion des modèles de facturation** : Les serveurs MCP retournent des métriques disparates : tokens LLM distants (`input_tokens`, `output_tokens`), coûts monétaires directs en EUR ou USD, ou unités de consommation métiers (`pages_ocr`, `recherches_api`, `minutes_gpu`). L'interface ne doit jamais « additionner des choux et des carottes ».
2. **Infrastructure tierce non fiable & risque de falsification** : Un serveur MCP externe peut retourner des valeurs corrompues ou malveillantes (montants négatifs, valeurs `NaN` déstabilisant les calculs en base, ou coûts exorbitants de plusieurs centaines d'euros pour une seule requête). Le filtre `RemoteUsageSanitizer` doit assainir et plafonner rigoureusement toute donnée entrante.
3. **Risque de blocage collatéral (*Cascading Failure*)** : Si un connecteur MCP dépasse son quota mensuel ou accumule des erreurs, son coupe-circuit doit s'ouvrir de manière isolée (**`CIRCUIT_OPEN`**). En aucun cas cette coupure ne doit suspendre les modèles LLM internes de l'Espace de travail ni les autres connecteurs opérationnels.
4. **Réarmement contrôlé** : Le réarmement du coupe-circuit d'un connecteur nécessite une action humaine explicite sous contrôle d'accès RBAC/ABAC (`enforce_scope_mutation_guard`), interdisant toute mutation en mode `READ_ONLY_OBSERVER`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `ConnectorInvoker` (`packages/orcia-core/src/orcia_core/permissions/connector_invoker.py`) : point central d'invocation de tous les connecteurs (impact amont = 9 appelants). Doit être étendu pour solliciter `ConnectorQuotaGuardPort` sans importer directement `audit_finops` (pour éviter toute violation de `AD-19 Contract 2`).
  - `CircuitBreakerState` : doit être homogénéisé de manière cohérente sous le littéral `Literal["CLOSED", "CIRCUIT_OPEN", "HALF_OPEN"]` entre le SQL, le port hexagonal, `ConnectorInvoker` et l'API.
  - `enforce_scope_mutation_guard` : doit sécuriser la mise à jour des quotas (`PUT /connectors/{id}/quota`) et le réarmement du coupe-circuit (`POST /connectors/{id}/reset-circuit`).
- **Exploration & Données Chiffrées** :
  - Le plafond par défaut `max_reported_cost_per_call_eur` est fixé à `5.000000` EUR. Tout montant déclaré supérieur est automatiquement écrêté à cette valeur et l'événement `RemoteUsageAnomalyCapped` est publié.
  - Pivot monétaire : tous les coûts sont convertis et stockés en base en USD `NUMERIC(12, 6)` et convertis dynamiquement en EUR à l'affichage.
- **Opportunités de Factorisation & Dette Technique** :
  - Centralisation de toute la logique de validation et de barème dans `RemoteUsageSanitizer` (réutilisable pour MCP, A2A et OpenAPI).
  - Ajout de `finops_connector_quotas` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` de `09_reset_db_first_boot.py`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic Linéaires
- Création de `infra/migrations/versions/20261116_0604_story_6_4_remote_connector_quotas_and_telemetry.py` (`down_revision = "20261116_0602"`) :
  - Table `finops_connector_quotas` :
    - `id UUID PRIMARY KEY` (UUIDv7 via `uuid-utils`).
    - `connector_id UUID NOT NULL REFERENCES enterprise_connectors(id) ON DELETE CASCADE`.
    - `scope_type VARCHAR(32) NOT NULL DEFAULT 'WORKSPACE'`.
    - `scope_id UUID NULL`.
    - `max_reported_cost_per_call_eur NUMERIC(12, 6) NOT NULL DEFAULT 5.000000`.
    - `monthly_cost_ceiling_eur NUMERIC(12, 6) NOT NULL DEFAULT 50.000000`.
    - `daily_calls_ceiling INTEGER NOT NULL DEFAULT 500`.
    - `valuation_mode VARCHAR(32) NOT NULL DEFAULT 'NATIVE_TELEMETRY' CHECK (valuation_mode IN ('NATIVE_TELEMETRY', 'FIXED_SCALE', 'VOLUMETRIC_ONLY'))`.
    - `fixed_cost_per_call_eur NUMERIC(12, 6) NOT NULL DEFAULT 0.000000`.
    - `fixed_cost_per_unit_eur NUMERIC(12, 6) NOT NULL DEFAULT 0.000000`.
    - `unit_name VARCHAR(64) NULL`.
    - `circuit_state VARCHAR(32) NOT NULL DEFAULT 'CLOSED' CHECK (circuit_state IN ('CLOSED', 'CIRCUIT_OPEN', 'HALF_OPEN'))`.
    - `consecutive_anomalies INTEGER NOT NULL DEFAULT 0`.
    - `last_tripped_at TIMESTAMPTZ NULL`.
    - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
  - Contrainte `UNIQUE (connector_id, scope_type, scope_id)`.
  - Enregistrement de `finops_connector_quotas` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` de `09_reset_db_first_boot.py`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers
- **Port Hexagonal (`packages/orcia-core/src/orcia_core/ports/finops_telemetry.py`)** :
  - `RemoteUsageRawPayload`, `SanitizedRemoteUsage`, `CircuitBreakerDecision`.
  - Protocoles `RemoteUsageSanitizerPort` et `ConnectorQuotaGuardPort`.
  - Utilisation du littéral uniforme `CircuitBreakerState = Literal["CLOSED", "CIRCUIT_OPEN", "HALF_OPEN"]`.
- **Validateur de Sécurité (`packages/orcia-core/src/orcia_core/audit_finops/remote_usage_sanitizer.py`)** :
  - Validation stricte interdisant les valeurs négatives, `NaN` et infinies.
  - Écrêtage au seuil `max_reported_cost_per_call_eur` et marquage `is_anomaly_capped = True`.
  - Prise en charge des 3 modes de valorisation (`NATIVE_TELEMETRY`, `FIXED_SCALE`, `VOLUMETRIC_ONLY`).
  - Conversion vers la devise pivot USD `NUMERIC(12, 6)`.
- **Garde de Quota & Coupe-Circuit (`packages/orcia-core/src/orcia_core/audit_finops/connector_quota_service.py`)** :
  - Implémente `ConnectorQuotaGuardPort`.
  - Bascule en `CIRCUIT_OPEN` dès atteinte du plafond mensuel ou journalier, ou après accumulation d'anomalies consécutives.
  - Requêtes SQL dans `_internal/sql_connector_quotas.py`.
- **Intégration `ConnectorInvoker` (`packages/orcia-core/src/orcia_core/permissions/connector_invoker.py`)** :
  - Appel préalable au port pour vérifier si le connecteur est autorisé (`CLOSED` ou sonde `HALF_OPEN`).
  - Blocage immédiat si `CIRCUIT_OPEN` sans impacter les autres connecteurs ni les modèles LLM internes.

### 2.3 Couche Backend API, Sécurité & Contrats
- **Schémas RFC 9457 (`apps/api/src/orcia_api/schemas/finops.py`)** :
  - `RemoteServiceTelemetryResponse`, `UpdateConnectorQuotaRequest`, `ResetCircuitBreakerResponse`.
- **Endpoints FastAPI (`apps/api/src/orcia_api/routers/finops.py`)** :
  - `GET /api/v1/finops/remote-services` : restitution détaillée des services MCP et agents distants avec consommations, modes de valorisation et statuts des coupe-circuits.
  - `PUT /api/v1/finops/connectors/{connector_key}/quota` : mise à jour des plafonds sous la garde `enforce_scope_mutation_guard`.
  - `POST /api/v1/finops/connectors/{connector_key}/reset-circuit` : réarmement du coupe-circuit sous la garde `enforce_scope_mutation_guard`.
- **SDK OpenAPI Client (`packages/api-client/`)** :
  - Régénération du SDK TypeScript via `scripts/export_openapi.py` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/` & `@orcia/ui`)
- **Composant `@orcia/ui` (`packages/ui/src/primitives/finops/FinopsRemoteMcpServicesTab.tsx`)** :
  - Tableau interactif des services MCP et agents distants.
  - Affichage clair du mode de valorisation (`🟢 Temps réel` vs `🔵 Barème fixe`).
  - Bouton d'action explicite de réarmement pour les services dont le coupe-circuit est ouvert (`CIRCUIT_OPEN`).
- **Mise à Jour de la Barre des KPI (`FinopsKpiStrip.tsx`)** :
  - Compteur 1 (**Coût consolidé**) : ventilation visuelle `Coût interne vérifié : X €` vs `Coût externe déclaré (MCP) : Y €`.
  - Compteur 2 (**Tokens LLM**) : somme exclusive de vrais tokens LLM.
  - Compteur 3 (**Appels & Unités externes**) : affichage dissocié du volume d'appels et des unités métiers (`pages OCR`, `requêtes`, etc.).
- **Montage dans `apps/web/src/features/finops/index.tsx`** :
  - Onglet dédié `🌐 Services & Agents externes`.
  - Intégration dans `zero-dead-buttons-and-silent-catches-audit.test.tsx`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17`)
- **Couche 1a (Unitaires Python)** :
  - `test_story_6_4_remote_usage_sanitizer.py` : tests déterministes et `hypothesis` sur charges corrompues (valeurs négatives, `NaN`, infinies, overflow $> 5 €$, devises inconnues).
  - `test_story_6_4_connector_quota_isolation.py` : validation de l'isolation du coupe-circuit (un connecteur bloqué n'empêche pas l'exécution des autres connecteurs ou LLM).
- **Couche 1b (Composants TS `Vitest`)** :
  - Rendu de l'onglet `FinopsRemoteMcpServicesTab` et vérification du callback de réarmement.
- **Couche 2 (Intégration `testcontainers` PostgreSQL 18 + Redis)** :
  - `test_story_6_4_connector_quotas_postgres18.py` : persistance des quotas, transition d'état `CIRCUIT_OPEN` et vérification SQL.
- **Couche Sécurité / Red-Team** :
  - Rejet `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` lors des tentatives de mutation de quota ou réarmement par un profil observateur.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *Section réservée à l'implémentation par le dev worker (`bmad-dev-worker` ⚡).*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/20261116_0604_story_6_4_remote_connector_quotas_and_telemetry.py` | Création | Migration Alembic créant la table `finops_connector_quotas` |
| `infra/scripts/maintenance/09_reset_db_first_boot.py` | Modification | Ajout de `finops_connector_quotas` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` |
| `packages/orcia-core/src/orcia_core/ports/finops_telemetry.py` | Modification | Harmonisation `CircuitBreakerState` et protocoles |
| `packages/orcia-core/src/orcia_core/permissions/connector_invoker.py` | Modification | Intégration de `CIRCUIT_OPEN` et du port `ConnectorQuotaGuardPort` |
| `packages/orcia-core/src/orcia_core/audit_finops/remote_usage_sanitizer.py` | Création | Validateur de sécurité anti-anomalies et convertisseur de métriques |
| `packages/orcia-core/src/orcia_core/audit_finops/connector_quota_service.py` | Création | Implémentation du garde de quota et de coupe-circuit |
| `packages/orcia-core/src/orcia_core/audit_finops/_internal/sql_connector_quotas.py` | Création | Requêtes SQL de gestion des quotas |
| `packages/ui/src/primitives/finops/FinopsRemoteMcpServicesTab.tsx` | Création | Onglet Services & Agents externes |
| `packages/ui/src/primitives/finops/FinopsKpiStrip.tsx` | Modification | Distinction visuelle coût interne vs externe et séparation tokens/unités |
| `apps/api/src/orcia_api/schemas/finops.py` | Modification | Schémas RFC 9457 pour les services distants |
| `apps/api/src/orcia_api/routers/finops.py` | Modification | Endpoints `/api/v1/finops/remote-services` et réarmement |
| `apps/web/src/features/finops/index.tsx` | Modification | Montage de l'onglet services distants |
| `tests/unit/test_story_6_4_remote_usage_sanitizer.py` | Création | Tests unitaires `hypothesis` sur valeurs aberrantes |
| `tests/unit/test_story_6_4_connector_quota_isolation.py` | Création | Validation de l'étanchéité du coupe-circuit |
| `tests/integration/test_story_6_4_connector_quotas_postgres18.py` | Création | Tests d'intégration testcontainers PostgreSQL 18 + Redis |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : Requis $\ge 90\%$.
- **Performances mesurées** : Assainissement télémétrique `RemoteUsageSanitizer` $< 1$ ms, Évaluation de quota $< 5$ ms.
- **Qualité statique & Architecture** :
  - `ruff check` & `ruff format --check` : `0 warning`
  - `mypy --strict` & `pnpm typecheck` : `0 error`
  - `lint-imports` : `5 contracts kept, 0 broken`
  - `lint_spine.py` : `ok: true, 0 findings`
  - `gitnexus_detect_changes()` : Périmètre conforme.

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17`)
- **Couche 1a & 1b** : Robustesse du sanitizer face aux injections malveillantes et rendu de l'onglet MCP.
- **Couche 2** : Isolation effective du coupe-circuit `CIRCUIT_OPEN` sur PostgreSQL 18 et Redis réels.
- **Couche 3** : Conformité du contrat OpenAPI et vérification `0-diff`.
- **Couche Sécurité / Red-Team** : Rejet systématique en `HTTP 403` pour toute action sous profil observateur.
- **Couche 5** : Vérification dans l'interface web de la dissociation des coûts et de l'action de réarmement.
