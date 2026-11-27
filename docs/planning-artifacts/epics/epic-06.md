## Epic 6: Gouvernance Exécutive, Provenance Auditable Immuable, FinOps Consolidé (LLM Internes + Télémétrie MCP/Agents Distants) & Réversibilité Humaine

Permettre aux Directeurs de BU, Responsables Produit et Auditeurs (`Claire UJ-8`, `Sophie UJ-6`) de piloter dans **📊 FinOps** l'équation économique consolidée de leurs processus (*Coût de Setup + Coût de Run interne vérifié + Coût externe déclaré MCP/A2A vs gain de TTM*) protégée par le validateur **`RemoteUsageSanitizer`** (`_meta.usage` / `X-Orcia-Usage`), les coupe-circuits budgétaires et anti-boucles (`PAUSED_BUDGET_EXCEEDED`, `PAUSED_MAX_RETRIES`) et les coupe-circuits isolés par connecteur (`CIRCUIT_OPEN`, `AD-12`), d'inspecter et d'exporter la *Provenance Auditable* immuable de chaque Step, Gate et test de connexion à chaud (`audit_ledger`, `ADMIN_CONNECTION_TEST`), et de suivre les 3 contre-métriques de gouvernance cognitive (*Ratio Cadrage Actif $\ge 40\%$*, *Taux de Rubber-Stamping $< 5\%$*, *Indice de Pattern Drift / Réversibilité Humaine $0\%$*) avec recommandations automatiques d'ajustement des Gates.

> **Réconciliation du 2026-11-08 (`CAP-ACT-3`)** : constat dans le code — aucune migration Alembic ne crée `audit_ledger`, `packages/orcia-core/.../audit_finops/` ne contient que `errors.py`, `/finops` n'est qu'une coquille `ModuleWorkspaceView` et le **Journal d'activité** (`/activity`, `CAP-065`, livré hors epic le 2026-11-05) lit `auditEvents` issus du snapshot d'accostage (`bootstrap_accostage.py`), **sans** registre append-only. Les Stories 6.1 à 6.4 restent donc **intégralement `backlog`**. Rebasage : (a) Story 6.1 doit **remplacer la source** de `/activity` par `audit_ledger` (le composant `ActivityLogExplorerView` et ses filtres sont réutilisés, pas recréés) ; (b) les statuts d'avancement figurent dans `capabilities.yaml` (`CAP-065` partial, `CAP-200` planned).

### Story 6.1: Registre de Provenance Auditable Immuable (`audit_ledger` Append-Only), Traçabilité des Tests à Chaud (`ADMIN_CONNECTION_TEST`) & Export de Conformité JSON/Markdown

As a Ingénieur SecOps ou Auditeur Interne (`Sophie UJ-6`, `Claire UJ-8`),
I want enregistrer de manière immuable dans `audit_ledger` la provenance complète de chaque Step, Gate, appel MCP/Agent distant (avec la nature des métriques déclarées) et essai à chaud du banc de test (`ADMIN_CONNECTION_TEST`), et l'exporter en JSON/Markdown,
So that nous puissions prouver réglementairement à 100% quelles ressources exactes, quels modèles internes ou services distants et quels experts humains ont produit et validé chaque livrable sans polluer les runs de production (`FR-25`, `AD-12`, `AD-19`, `NFR-SEC-3`, `Principe M.2`).

**Acceptance Criteria:**

**Given** la migration Alembic créant la table `audit_ledger` protégée par un trigger PostgreSQL `BEFORE UPDATE OR DELETE RAISE EXCEPTION` (`NFR-SEC-3`) et l'abonné Outbox idempotent de `packages/orcia-core/audit_finops` (`AD-19`)
**When** un appel LLM, une exécution de *Skill*/*MCP*/*Agent distant A2A*, un essai à chaud du banc de test (`actor_type: ADMIN_CONNECTION_TEST`, isolé hors run de production), une mutation *Jira*, un passage de *Gate*, une action humaine ou une modification de paramètre système (`SettingsChanged`, `AD-21`) se produit
**Then** `packages/orcia-core/audit_finops` consomme les événements de `domain_events_outbox` (`StepCompleted`, `GateEvaluated`, `ArtifactProduced`, `RunTerminated`, `SettingsChanged`) sans couplage entrant depuis `orchestration/engine.py` et écrit sans doublon (idempotence par `event_id`) une entrée horodatée UTC ISO-8601 contenant `run_id` (nullable pour `ADMIN_CONNECTION_TEST`), `step_execution_id`, `actor_type`, `actor_id`, `event_type`, `model_id`, `inference_tier`, `effort`, `input_tokens`, `output_tokens`, `cost_usd`, `native_metric_type`, `native_metric_value`, `reported_by_remote`, `latency_ms`, `trace_id`, `run_lock_sha256`, les hashes `SHA-256` du *Pré-prompt IA* et du *Contrat du workflow*, et les références CAS (`SeaweedFS`) des prompts/chunks KB injectés (`FR-25`, `AD-12`, `AD-19`, `AD-21`)
**And** toute tentative de `UPDATE` ou `DELETE` sur `audit_ledger` lève une exception PostgreSQL immédiate.

**Given** un auditeur habilité dans **📊 FinOps** (`g f`, `apps/web/src/features/finops/`)
**When** il inspecte un *Workflow Run* ou appelle `GET /api/v1/audit/ledger/{run_id}/export?format=json|md`
**Then** le système génère le dossier complet de **Provenance Auditable** attestant qu'aucune étape n'a consommé une ressource absente de `run-lock.json`
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`) et d'intégration (`testcontainers` PG18 vérifiant le trigger append-only + SeaweedFS) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

### Story 6.2: Comptabilité FinOps Complète (Coût de Setup + Coût de Run vs TTM) & Coupe-Circuits Budgétaires / Anti-Boucles

As a Directrice de BU ou Responsable d'Équipe (`Claire UJ-8`, `Marc UJ-5`),
I want comptabiliser en temps réel le coût complet d'un processus (amortissement du Setup + coût des tokens LLM + temps humain de cadrage/revue) comparé au gain de Time-to-Market, et suspendre automatiquement tout Run qui dépasse son plafond budgétaire ou son nombre maximal de tentatives,
So that nous mesurions la réduction de $\ge 25\%$ du coût complet (`SM-1`) tout en éliminant tout risque de dérive financière par boucle d'agents infinie (`FR-26`, `AD-12`, `AD-19`).

**Acceptance Criteria:**

**Given** un *Workflow*, un *Workflow Run* et la hiérarchie de périmètres (`GLOBAL -> BU -> TEAM -> WORKSPACE`, `AD-21`) configurés avec `max_cost_usd`, quotas hiérarchiques et `max_agent_retries` (défaut : `3`), ainsi qu'une baseline déclarée de coût et de TTM manuel
**When** un Step accumule des appels LLM (y compris les escalades du routeur `auto` enregistrées dans `inference_attempts`) ou des boucles de correction suite à un rejet de Gate
**Then** le coupe-circuit vérifie à chaque appel LLM coûteux et à chaque transition les seuils du Run et du périmètre : s'ils sont atteints, il suspend immédiatement l'étape en statut `PAUSED_BUDGET_EXCEEDED` ou `PAUSED_MAX_RETRIES`, émet une alerte SSE via `domain_events_outbox` au responsable du Run, et exige un arbitrage humain ou une extension explicite (`POST /api/v1/runs/{run_id}/budget-override`) pour reprendre (`FR-26`, `AD-12`, `AD-19`, `AD-21`).

**Given** une Directrice de BU (`Claire, UJ-8`) qui consulte **📊 FinOps** ou interroge `Mon Assistant`
**When** le tableau de bord FinOps est affiché
**Then** il ventile par *Step*, par *Tier cognitif (`simple | medium | complex | auto`)* et *niveau d'Effort (`default | fast | balanced | deep`)*, par *Workflow Run*, par *Workflow* et par *Équipe/BU* le **Coût de Setup** (temps de conception/maintenance du workflow), le **Coût de Run** (tokens LLM en `numeric(12, 6)` USD + temps humain valorisé) et l'écart de **Time-to-Market (TTM)** par rapport à la baseline (`SM-1`, `SM-5`, `AD-21`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`hypothesis` sur les calculs de coûts et coupe-circuits) et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du service FinOps (`AD-17`, `AD-19`).

### Story 6.3: Tableau de Bord Exécutif d'Impact Cognitif, Anti-Rubber-Stamping & Indice de Réversibilité Humaine

As a Directrice de BU, Tech Lead ou SecOps (`Claire UJ-8`, `Marc UJ-5`, `Sophie UJ-6`),
I want suivre par Workflow et par Équipe/BU les 3 contre-métriques de gouvernance humaine et technique (Ratio Cadrage Actif $\ge 40\%$, Taux de Rubber-Stamping $< 5\%$, Indice de Pattern Drift / Réversibilité Humaine $0\%$) et recevoir des recommandations automatiques d'ajustement des Gates,
So that l'accélération par l'IA ne transforme jamais nos experts humains en simples tamponneurs passifs ni notre codebase en boîte noire non maintenable (`FR-27`, `AD-19`, `SM-C1`, `SM-C2`, `SM-C3`).

**Acceptance Criteria:**

**Given** les données agrégées depuis `human_anchor_signatures`, `human_arbitration_requests`, `gate_evaluations` (`review_duration_ms`, `fast_approval_warning`) et `audit_ledger`
**When** l'utilisateur ouvre l'onglet Gouvernance & Réversibilité de **📊 FinOps** (`g f`, `apps/web/src/features/finops/`)
**Then** le système calcule et affiche par *Workflow*, *Équipe* et *BU* les **3 indicateurs de maîtrise humaine (`FR-27`)** :
1. **Ratio Cadrage Actif ("Human-Led Think") vs Simple Relecture (`SM-C2`)** : $\frac{\text{Temps Ancrages Humains} + \text{Arbitrages} + \text{Challenges}}{\text{Temps Humain Total}}$ (alerte ambre si $< 40\%$).
2. **Taux de Validation Aveugle / Rubber-Stamping (`SM-C1`)** : pourcentage d'approbations aux Gates Humaines avec `fast_approval_warning: true` ou sans ouverture du *Briefing de Revue* (alerte rouge si $\ge 5\%$).
3. **Indice de Pattern Drift & Réversibilité Humaine (`SM-C3`)** : taux d'écarts architecturaux détectés par rapport à `ARCHITECTURE-SPINE.md` (cible $0\%$ hors dérogation signée).

**Given** un *Workflow* présentant un taux d'approbation aux *Gates Humaines* $> 98\%$ avec un temps médian de revue inférieur au seuil minimal et `0` modification/commentaire sur une période donnée
**When** l'analyseur de gouvernance évalue le *Workflow*
**Then** il génère une alerte et une recommandation actionnable proposant soit de basculer la *Gate* en politique `risk_or_exception_based` / `sampling`, soit de renforcer les *Ancrages Humains Obligatoires* (`FR-27`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`), d'évaluation (`orcia-evals`) et E2E (`Playwright`) couvrent $\ge 90\%$ du tableau de bord et des règles d'alerte (`AD-17`, `AD-19`).

### Story 6.4: Télémétrie FinOps Multi-Métriques des Services MCP & Agents Distants (`_meta.usage` / `X-Orcia-Usage`), `RemoteUsageSanitizer`, Onglet `🌐 Par Service MCP & Agent Distant` & Coupe-Circuit Isolé par Connecteur (`AD-12`, Principe M.3)

As a Directrice de BU, Administrateur Plateforme ou Chef d'Équipe (`Claire UJ-8`, `Karim UJ-9`, `Marc UJ-5`),
I want collecter et normaliser les métriques de consommation retournées par les serveurs MCP et agents distants (`Tokens LLM distants`, `Coût monétaire €/$`, `Unités/Crédits métiers` + barème de conversion en fallback), les protéger contre toute donnée corrompue via `RemoteUsageSanitizer`, ventiler clairement le coût interne vérifié et le coût externe déclaré dans `📊 FinOps`, et isoler le coupe-circuit de chaque connecteur,
So that nous suivions le coût consolidé réel sans jamais additionner des choux et des carottes ni laisser un serveur MCP tiers bogué épuiser le budget global ou bloquer les LLM internes (`FR-26`, `AD-12`, `AD-19`, `Principe M.3`).

**Acceptance Criteria:**

**Given** un appel exécuté via `ConnectorInvoker` vers un serveur MCP ou un agent distant A2A retournant un bloc `CallToolResult._meta.usage` ou un en-tête `X-Orcia-Usage` (ou ne retournant aucune métrique)
**When** le **`RemoteUsageSanitizer`** (`packages/orcia-core/audit_finops`) inspecte la télémétrie reçue avant publication dans `domain_events_outbox` (`StepCompleted`)
**Then** :
1. Il extrait les 3 formats de métriques (`input_tokens`/`output_tokens` distants, `cost`/`currency`, ou `units`/`unit_name` tels que `pages_ocr`, `recherches_api`, `minutes_gpu`) ou applique le **barème de conversion par défaut** configuré sur le connecteur (`coût fixe par appel` ou `coût par unité × taux de change €`) ;
2. Il rejette toute valeur négative (`< 0`), `NaN` ou `Infinity`, applique le plafond de sécurité par appel **`max_reported_cost_per_call`** (défaut `5,00 €`) en écrêtant la valeur au-delà et en émettant `REMOTE_USAGE_ANOMALY_CAPPED`, et convertit `native_currency` vers le pivot `numeric(12, 6)` USD en base (`AD-12`) pour un affichage unifié en `€` ;
3. Si un service distant dépasse son sous-plafond mensuel ou journalier dédié (ex. `max 50 € / mois` ou `500 appels / jour`), seul le coupe-circuit de ce connecteur passe à **`CIRCUIT_OPEN`** dans `ConnectorInvoker` (`AD-12`), sans bloquer les modèles LLM internes de l'Espace.

**Given** l'écran **`📊 FinOps`** (`apps/web/src/features/finops/`)
**When** l'utilisateur consulte les **4 compteurs KPI d'en-tête** et l'onglet **`🌐 Par Service MCP & Agent Distant`**
**Then** :
1. Le compteur 1 (**`COÛT CONSOLIDÉ (€)`**) affiche le total en `€` en distinguant visuellement **`Coût interne vérifié : X €`** et **`Coût externe déclaré (MCP) : Y €`** ;
2. Le compteur 2 (**`TOKENS LLM (INTERNES & DISTANTS)`**) additionne uniquement de vrais tokens LLM, tandis que le compteur 3 (**`APPELS & UNITÉS EXTERNES (MCP)`**) affiche séparément le nombre d'appels et les unités métiers (`pages OCR`, `requêtes API`, `crédits`) ;
3. L'onglet **`🌐 Par Service MCP & Agent Distant`** affiche la table détaillée (*Service / Agent*, *Type*, *Appels*, *Métrique native consommée*, *Mode de valorisation `🟢 Temps réel (_meta.usage)` vs `🔵 Barème fixe`*, *Coût consolidé (€)* et *Quota / Plafond*)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest` + `hypothesis` sur `RemoteUsageSanitizer` avec valeurs négatives/`NaN`/overflow, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).
