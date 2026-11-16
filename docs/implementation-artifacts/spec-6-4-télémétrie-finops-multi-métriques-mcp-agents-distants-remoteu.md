---
story_key: "6-4-télémétrie-finops-multi-métriques-mcp-agents-distants-remoteu"
status: "ready-for-dev"
epic: "epic-6"
title: "Story 6.4 : Télémétrie FinOps Multi-Métriques des Services MCP & Agents Distants (_meta.usage / X-Orcia-Usage), RemoteUsageSanitizer, Onglet 🌐 Services & Agents externes & Coupe-Circuit Isolé par Connecteur"
date: "2026-11-16"
authors:
  - "Winston (bmad-agent-architect 🏗️)"
  - "Sally (bmad-agent-ux-designer 🎨)"
capabilities:
  - "CAP-200"
---

# Spécification d'Implémentation — Story 6.4 : Télémétrie FinOps Multi-Métriques des Services MCP & Agents Distants (`_meta.usage` / `X-Orcia-Usage`), `RemoteUsageSanitizer`, Onglet `🌐 Services & Agents externes` & Coupe-Circuit Isolé par Connecteur (`AD-12`, Principe M.3)

- **Story Key** : `6-4-télémétrie-finops-multi-métriques-mcp-agents-distants-remoteu`
- **Epic** : Epic 6 — Gouvernance Exécutive, Provenance Auditable Immuable, FinOps Consolidé & Réversibilité Humaine
- **Capacité rattachée** : `CAP-200` (Consolidation FinOps multi-fournisseurs & protection des connecteurs tiers)
- **Références architecturales** : `FR-26`, `AD-12`, `AD-17`, `AD-19`, `Principe M.3`, `NFR-SEC-4`

---

## 1. Intent & Boundaries

### 1.1 Problem & Approach
L'ouverture vers les serveurs MCP et les agents distants (A2A) introduit une diversité de modèles de facturation non harmonisés (tokens LLM tiers, coût monétaire direct en EUR/USD, unités métiers comme les pages OCR, crédits ou secondes GPU). Les données télémétriques provenant de services externes ne peuvent être considérées comme fiables par défaut (risque d'erreurs, valeurs négatives, montants astronomiques déclarés ou pannes en boucle). De plus, l'épuisement du quota d'un connecteur MCP ne doit en aucun cas bloquer les LLM internes de l'Espace.
Cette story implémente :
1. Le validateur de sécurité **`RemoteUsageSanitizer`** (`packages/orcia-core/src/orcia_core/audit_finops/remote_usage_sanitizer.py`) :
   - Traite les 3 formats de métriques : Tokens distants, Coût direct, Unités métiers.
   - Rejette immédiatement les valeurs aberrantes ($< 0$, `NaN`, `Infinity`).
   - Applique le plafond de sécurité par appel **`max_reported_cost_per_call_eur`** (configurable, défaut : `5,00 €`), écrêtant tout dépassement et émettant l'événement `RemoteUsageAnomalyCapped`.
   - Convertit les montants vers la devise pivot USD `NUMERIC(12, 6)` en base et marque les entrées `reported_by_remote = True`, `cost_source = 'EXTERNAL_REPORTED'`.
2. La table `finops_connector_quotas` (migration Alembic `20261116_0604_story_6_4_remote_connector_quotas_and_telemetry.py`) gérant les plafonds, les 3 modes de valorisation (`NATIVE_TELEMETRY`, `FIXED_SCALE`, `VOLUMETRIC_ONLY`) et l'état du coupe-circuit unifié (`Literal["CLOSED", "CIRCUIT_OPEN", "HALF_OPEN"]`).
3. L'isolation stricte du coupe-circuit dans `ConnectorInvoker` via `ConnectorQuotaGuardPort` : si un connecteur dépasse son plafond ou accumule des anomalies, seul son état bascule en **`CIRCUIT_OPEN`** ; les modèles LLM internes et les autres connecteurs restent opérationnels.
4. L'onglet `@orcia/ui` `FinopsRemoteMcpServicesTab.tsx` dans `/finops` avec mise à jour de la barre KPI (`FinopsKpiStrip.tsx`) distinguant visuellement le `Coût interne vérifié` du `Coût externe déclaré (MCP)` et séparant les vrais tokens des unités et appels métiers.

### 1.2 Boundaries & Constraints
- **Toujours (`Always`)** :
  - Utiliser la nomenclature unifiée `Literal["CLOSED", "CIRCUIT_OPEN", "HALF_OPEN"]` pour `CircuitBreakerState` dans le SQL (`CHECK circuit_state IN ('CLOSED', 'CIRCUIT_OPEN', 'HALF_OPEN')`), dans le port `finops_telemetry.py`, dans `ConnectorInvoker` et dans les schémas d'API.
  - Rejeter sans exception toute valeur négative ($< 0$), `NaN` ou `Infinity` avec levée de `ValidationDomainError`.
  - Écrêter tout montant déclaré supérieur à `max_reported_cost_per_call_eur` et émettre l'événement `RemoteUsageAnomalyCapped` dans `domain_events_outbox`.
  - Garantir l'étanchéité absolue du coupe-circuit : l'ouverture du coupe-circuit d'un connecteur externe ne doit **jamais** bloquer l'orchestration interne ni les modèles LLM configurés.
  - Séparer strictement dans les KPI d'en-tête les tokens LLM des unités métiers (zéro somme deGrandeurs physiques incompatibles).
  - Protéger les mutations de quotas et les réarmements de coupe-circuit (`POST /connectors/{id}/reset-circuit`) par `enforce_scope_mutation_guard` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`).
  - Ajouter `finops_connector_quotas` dans `ORDERED_MUTABLE_TABLES_TO_CLEAR` de `09_reset_db_first_boot.py`.
- **Jamais (`Never`)** :
  - Ne jamais faire confiance aveuglément aux métadonnées déclarées par un serveur distant sans passer par `RemoteUsageSanitizer`.
  - Ne jamais additionner directement des tokens LLM et des unités métiers (ex. pages OCR ou requêtes d'API) dans un même compteur numérique.
  - Ne jamais introduire de dépendance cyclique entre `permissions` et `audit_finops` (injection via `ConnectorQuotaGuardPort`).

### 1.3 I/O & Edge-Case Matrix

| Type d'Appel / Métrique | Entrée déclarée | Résultat du Sanitizer | Impact Quota & Coupe-Circuit |
| :--- | :--- | :--- | :--- |
| MCP Tokens standard | `input: 1200`, `output: 300` | Extrait tel quel, valorisé au barème | Inscription audit avec `tokens` |
| Coût direct valide | `cost: 0.15`, `currency: 'EUR'` | Converti en USD pivot, vérifié $< 5,00 €$ | Cumul dans la consommation du mois |
| Montant astronomique | `cost: 250.00`, `currency: 'EUR'` | Écrêté à `5,00 €`, `RemoteUsageAnomalyCapped` émis | Incrément anomalies, coupe-circuit surveillé |
| Valeur négative / frauduleuse | `cost: -10.00` ou `cost: NaN` | Rejet immédiat, exception de validation | Appel échoué, anomalie tracée |
| Absence de métriques | `_meta.usage: None` | Application du barème fixe du connecteur | Valorisation forfaitaire par appel |
| Dépassement plafond mensuel | Cumul mensuel $> 50,00 €$ | Blocage de l'appel | Connecteur passe en `CIRCUIT_OPEN` |
| Autre connecteur ou LLM interne | Invocations concurrentes | Appels autorisés | Zéro blocage collatéral (Isolation) |
| Réarmement manuel autorisé | `POST /connectors/{id}/reset-circuit` | Passage en `HALF_OPEN` / `CLOSED` | Connecteur réarmé |

---

## 2. Acceptance Criteria (Given / When / Then)

### Critère 1 : Migration Alembic & Table `finops_connector_quotas`
- **Given** la migration Alembic `20261116_0604_story_6_4_remote_connector_quotas_and_telemetry.py` (down_revision = `"20261116_0602"`),
- **When** la migration est appliquée,
- **Then** la table `finops_connector_quotas` est créée avec la contrainte CHECK `circuit_state IN ('CLOSED', 'CIRCUIT_OPEN', 'HALF_OPEN')`, le plafond par défaut `max_reported_cost_per_call_eur = 5.000000` et les 3 modes de valorisation,
- **And** la table est ajoutée en tête de `ORDERED_MUTABLE_TABLES_TO_CLEAR` dans `09_reset_db_first_boot.py`.

### Critère 2 : Validation Robuste & Écrêtage `RemoteUsageSanitizer`
- **Given** un appel vers un serveur MCP ou agent distant retournant une charge `_meta.usage` ou un en-tête `X-Orcia-Usage`,
- **When** `RemoteUsageSanitizer.sanitize(...)` inspecte les métriques déclarées,
- **Then** il rejette formellement toute valeur négative ($< 0$), `NaN` ou `Infinity`,
- **And** si le coût déclaré dépasse `max_reported_cost_per_call_eur` (5,00 €), il écrête le montant au plafond maximal, positionne `is_anomaly_capped = True` et publie l'événement `RemoteUsageAnomalyCapped` dans `domain_events_outbox`,
- **And** il normalise le montant en USD pivot `NUMERIC(12, 6)` et renseigne `cost_source = 'EXTERNAL_REPORTED'`.

### Critère 3 : Isolation du Coupe-Circuit par Connecteur (`CIRCUIT_OPEN`)
- **Given** un connecteur MCP dont la consommation atteint le plafond mensuel ou journalier,
- **When** `ConnectorInvoker` sollicite le service injecté implémentant `ConnectorQuotaGuardPort`,
- **Then** le statut du coupe-circuit de ce connecteur bascule en **`CIRCUIT_OPEN`** et l'appel externe est suspendu,
- **And** les invocations vers d'autres connecteurs et l'ensemble des modèles LLM internes poursuivent leur exécution sans aucune perturbation.

### Critère 4 : Réarmement de Coupe-Circuit & Sécurité RBAC/ABAC
- **Given** un connecteur distant dont le coupe-circuit est ouvert (`CIRCUIT_OPEN`),
- **When** un responsable autorise la réactivation via `POST /api/v1/finops/connectors/{connector_key}/reset-circuit`,
- **Then** le statut bascule en `HALF_OPEN` ou `CLOSED`,
- **And** toute tentative par un utilisateur en mode `READ_ONLY_OBSERVER` est rejetée avec un code `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`.

### Critère 5 : Visualisation Découplée dans l'Interface `@orcia/ui`
- **Given** l'écran `/finops` (`apps/web/src/features/finops/`),
- **When** l'utilisateur consulte les KPI et l'onglet `🌐 Services & Agents externes`,
- **Then** le compteur de coût consolidé distingue visuellement **`Coût interne vérifié`** et **`Coût externe déclaré (MCP)`**,
- **And** les vrais tokens LLM sont sommés séparément des unités et appels métiers,
- **And** le tableau liste chaque service avec son type, ses consommations natives, son mode de valorisation et l'état de son coupe-circuit avec bouton de réarmement.

---

## 3. Code Map

```
ORCIA/
├── infra/
│   ├── migrations/versions/
│   │   └── 20261116_0604_story_6_4_remote_connector_quotas_and_telemetry.py [CRÉATION - Migration Alembic]
│   └── scripts/maintenance/
│       └── 09_reset_db_first_boot.py                                        [MODIFICATION - Ajout finops_connector_quotas]
├── packages/
│   ├── orcia-core/src/orcia_core/
│   │   ├── ports/
│   │   │   └── finops_telemetry.py                                          [MODIFICATION - Intégration CIRCUIT_OPEN et DTOs]
│   │   ├── permissions/
│   │   │   └── connector_invoker.py                                         [MODIFICATION - Utilisation CIRCUIT_OPEN & Port]
│   │   └── audit_finops/
│   │       ├── remote_usage_sanitizer.py                                    [CRÉATION - Validateur et filtre anti-anomalies]
│   │       ├── connector_quota_service.py                                   [CRÉATION - Implémentation ConnectorQuotaGuardPort]
│   │       └── _internal/
│   │           └── sql_connector_quotas.py                                  [CRÉATION - Requêtes SQL de gestion des quotas]
│   └── ui/src/
│       ├── index.ts                                                         [MODIFICATION - Exports briques télémétrie MCP]
│       └── primitives/finops/
│           ├── FinopsRemoteMcpServicesTab.tsx                               [CRÉATION - Onglet Services & Agents externes]
│           └── FinopsKpiStrip.tsx                                           [MODIFICATION - Distinction vérifié vs déclaré]
├── apps/
│   ├── api/src/orcia_api/
│   │   ├── dependencies/
│   │   │   └── orchestration_and_settings.py                                [MODIFICATION - Injection ConnectorQuotaGuardPort]
│   │   ├── schemas/
│   │   │   └── finops.py                                                    [MODIFICATION - Schémas services distants]
│   │   └── routers/
│   │       └── finops.py                                                    [MODIFICATION - Endpoints /api/v1/finops/remote-services]
│   └── web/src/
│       └── features/finops/
│           └── index.tsx                                                    [MODIFICATION - Câblage onglet services distants]
└── tests/
    ├── unit/
    │   ├── test_story_6_4_remote_usage_sanitizer.py                         [CRÉATION - Hypothesis sur valeurs NaN/négatives/overflow]
    │   └── test_story_6_4_connector_quota_isolation.py                      [CRÉATION - Vérification étanchéité du coupe-circuit]
    └── integration/
        └── test_story_6_4_connector_quotas_postgres18.py                    [CRÉATION - Testcontainers PG18 + Redis]
```

---

## 4. Ordered Tasks (Dependencies First)

### Tâche 1 : Migration Alembic & Table `finops_connector_quotas`
- Créer `infra/migrations/versions/20261116_0604_story_6_4_remote_connector_quotas_and_telemetry.py` avec `down_revision = "20261116_0602"`.
- Définir la table `finops_connector_quotas` avec contrainte CHECK `circuit_state IN ('CLOSED', 'CIRCUIT_OPEN', 'HALF_OPEN')`.
- Mettre à jour `ORDERED_MUTABLE_TABLES_TO_CLEAR` dans `infra/scripts/maintenance/09_reset_db_first_boot.py`.

### Tâche 2 : Alignement du Port `finops_telemetry.py` & `ConnectorInvoker`
- Vérifier que `CircuitBreakerState = Literal["CLOSED", "CIRCUIT_OPEN", "HALF_OPEN"]` est homogène dans `orcia_core/ports/finops_telemetry.py` et `packages/orcia-core/src/orcia_core/permissions/connector_invoker.py`.
- Intégrer l'appel au port `ConnectorQuotaGuardPort` dans le cycle de vie de `ConnectorInvoker`.

### Tâche 3 : Moteur `RemoteUsageSanitizer` & Service de Quota
- Développer `packages/orcia-core/src/orcia_core/audit_finops/remote_usage_sanitizer.py`.
- Implémenter le parsing des 3 formats (`tokens`, `cost`, `units`), le rejet des valeurs aberrantes et l'écrêtage à `max_reported_cost_per_call_eur` avec émission de `RemoteUsageAnomalyCapped`.
- Développer `packages/orcia-core/src/orcia_core/audit_finops/connector_quota_service.py` et `_internal/sql_connector_quotas.py`.

### Tâche 4 : Routeur FastAPI, Schémas RFC 9457 & OpenAPI SDK
- Enrichir `apps/api/src/orcia_api/schemas/finops.py` avec les DTOs des services externes.
- Ajouter dans `apps/api/src/orcia_api/routers/finops.py` :
  - `GET /api/v1/finops/remote-services`
  - `PUT /api/v1/finops/connectors/{connector_key}/quota` (sous `enforce_scope_mutation_guard`)
  - `POST /api/v1/finops/connectors/{connector_key}/reset-circuit` (sous `enforce_scope_mutation_guard`).
- Régénérer le SDK OpenAPI client via `scripts/export_openapi.py` (`0-diff`).

### Tâche 5 : Composants `@orcia/ui` & Câblage de l'Onglet Services Distants
- Développer `packages/ui/src/primitives/finops/FinopsRemoteMcpServicesTab.tsx`.
- Mettre à jour `FinopsKpiStrip.tsx` pour afficher les sous-totaux `Coût interne vérifié` et `Coût externe déclaré (MCP)`.
- Monter l'onglet dans `apps/web/src/features/finops/index.tsx` et enregistrer les props requises dans `zero-dead-buttons-and-silent-catches-audit.test.tsx`.

### Tâche 6 : Pyramide des Tests `AD-17` & Red-Team
- Couche 1a : Tests unitaires Python avec `hypothesis` éprouvant `RemoteUsageSanitizer` sur valeurs négatives, `NaN`, infinies, chaînes corrompues et devises exotiques.
- Couche 1b : Tests composants Vitest vérifiant le tableau des services et l'action de réarmement.
- Couche 2 : Test d'intégration `testcontainers` PostgreSQL 18 + Redis simulant l'ouverture isolée du coupe-circuit d'un connecteur distant et la non-régression des LLM internes.
- Couche Sécurité / Red-Team : Vérification du rejet `HTTP 403` pour tout réarmement tenté par `READ_ONLY_OBSERVER`.
