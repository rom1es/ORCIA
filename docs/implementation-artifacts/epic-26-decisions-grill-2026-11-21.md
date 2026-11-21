# Arbitrages Architecture & Gouvernance — Epic 26 (« Mon Assistant » Unifié, Gouverné & Persistant)

- **Date :** 2026-11-21
- **Branche :** `feat/epic-26-assistant-harness-debt-remediation` (renommée depuis `chore/assistant-harness-debt-remediation`)
- **Commit de référence :** `bc4bff0`
- **Méthode :** Session interactive `/grill-me` (Phase 1) suivie d'un rebasage `bmad-correct-course` (Phase 2)
- **Documents sources & cibles :**
  - Plan directeur : [`sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md`](../planning-artifacts/sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md)
  - Audit source : [`2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md`](./tech-lead-reports/2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md) (`H-01..H-38`)
  - Backlog : [`epics.md` — Epic 26](../planning-artifacts/epics.md#L3048)
  - Suivi de sprint : [`sprint-status.yaml`](./sprint-status.yaml#L275)

---

> [!IMPORTANT]
> **Révision de simplification `R1–R4` (2026-11-21 09:00, validée par l'utilisateur après analyse critique du plan).** Elle **remplace** `D1.a` (→ `R3`), `D1.b` (→ `R2`), l'hébergement Dramatiq de `D2` et `D2.a` (→ `R1`), ainsi que le calendrier d'étrangleur de `D8` et la phase de dépréciation de `D6` (→ `R4`). Voir la section finale « Révision R ». Les autres décisions (`D1` cœur, `D2` protocole, `D3` à `D7`, `D9` à `D11`) restent inchangées.

## Synthèse des 14 arbitrages ratifiés (état avant révision R)

| # | Sujet | Option retenue | Écart vs défaut initial | Stories & AD impactés |
| :---: | :--- | :--- | :--- | :--- |
| **`D1`** | Architecture du moteur unique | Hybride `AssistantTurnEngine` (fast-path Speed 1 + profil `ASSISTANT` réflexif Speed 2/3, 5 nœuds → phases `N1–N5`) | Conforme au défaut | `26.0`, `26.4b`, `26.6b`, `26.7`, `26.9` — `AD-25` + amendement `AD-15` |
| **`D1.a`** | Escalade `Speed 1 → Speed 2` | Escalade auto **100 % pré-LLM** (`N1` + seuil d'évidence post-préfetch `N3 < 50 ms` si `supports_tools=true`), SSE `speed_escalated` + badge localisé | **Divergence** (ajout fonctionnel encadré) | Rebasage `26.0`, `26.7`, `26.9` — `AD-25`, `AD-15`, `AD-24` |
| **`D1.b`** | Périmètre Studio Mode B | Topologie `N1–N5` fixe & verrous scellés (Couche 1, `N1`, V5, `CitationGuard`) ; paramétrage déclaratif `N2–N5` uniquement | Précise le défaut | `26.0`, `26.4b`, `26.7`, `26.9` — `AD-25`, `AD-15`, `AD-3` |
| **`D2`** | Protocole & hébergement des tours | `POST /turns` (`202`) + `GET /turns/{id}/stream?after=cursor` (Redis Streams) ; Speed 1 en `asyncio.Task` bornée (`apps/api`) ; Speed 2/3 (+ escalades `D1.a`) en acteur Dramatiq idempotent (`apps/worker`) | Conforme au défaut (+ bascule `D1.a`) | `26.0`, `26.3`, `26.7`, `26.9` — `AD-25`, `AD-2` |
| **`D2.a`** | Panne `apps/worker` & tests | Fail-fast explicite via heartbeat Redis + timeout `<= 3 s` → `503 ERR_ASSISTANT_WORKER_UNAVAILABLE` RFC 9457 (zéro repli silencieux) ; vrai worker Dramatiq en Couche 2 & E2E | Précise le défaut | Rebasage léger `26.0`, `26.3`, `26.10` — `AD-25`, `AD-17` |
| **`D3`** | Politique SSRF & `platform-setup-state` | Allowlist administrée (`localhost` uniquement en `local`/`test`) + blocage permanent métadonnées/link-local/ports internes + *pinning* DNS ; projection publique Jour 0 `{is_initialized, step}` (`0` secret) et détail réservé à `PLATFORM_ADMIN` | Conforme au défaut + protection Jour 0 | `26.0`, `26.1`, `26.10` — amendements `AD-21` & `AD-24` |
| **`D4`** | Persistance des messages de fil | Table dédiée `assistant_thread_messages` (`UUIDv7`, `role IN ('user','assistant')`, `citation_map JSONB`, `token_count`) + trace d'outils liée par `turn_id` dans `reflexive_execution_sessions` | Conforme au défaut | `26.0` (ERD), `26.5`, `26.7`, `26.9` — `architecture.md` |
| **`D5`** | Modèles sans *function calling* | `supports_tools` découvert à 0 token (+ override `PLATFORM_ADMIN`), Speed 2/3 désactivées en UI, refus serveur `422 ERR_MODEL_TOOLS_UNSUPPORTED` (zéro émulation XML/ReAct) | Conforme au défaut | `26.0`, `26.6a`, `26.7`, `26.9` — `AD-24`, `AD-25` |
| **`D6`** | `save_and_launch_workflow` vs `CONTINUE_IN_PROCESS` | Raccorder `approve` + `launch-process` à DBOS + PG18 (`WAITING_FOR_HUMAN_ANCHOR`) ; **déprécier (`26.8`) puis supprimer (`26.10`)** `POST /workflows/save-and-launch` et l'exécution RAM | Tranche l'alternative ouverte | Rebasage `26.0`, `26.8`, `26.10` — `AD-2`, `AD-3`, `AD-25` |
| **`D7`** | Sort de l'outil MCP `assistant.ask` | Raccorder `assistant.ask` à `AssistantTurnEngine` en Speed 1 synchrone lecture seule (7 verrous MCP + `QuotaGuard` + `ScopeAccessGuard` + `CitationGuard`) | Tranche l'alternative ouverte | Rebasage léger `26.0`, `26.7`, `26.10` — `AD-12`, `AD-25` |
| **`D8`** | Routes historiques & façade v1 | Façade étrangleur `/three-speed/*` maintenue jusqu'en `26.9` ; migration UI + E2E vers `/assistant/turns*` (`feedback` inclus) + `GET /threads/{id}/messages` en `26.9` ; purge totale en `26.10` (y compris `/three-speed/*` et doublon `POST /threads/{id}/turns`) | **Divergence / précision** | Rebasage `26.0`, `26.7`, `26.9`, `26.10` — `AD-25`, OpenAPI v2 |
| **`D9`** | Registre `capabilities.yaml` & `CAP-260` | Abaisser `CAP-022`, `CAP-070`, `CAP-072` en `verification: api` dès `26.1` ; créer `CAP-260` (`api`) en `26.6b` ; promouvoir les 4 en `runtime` uniquement en `26.10` après preuve E2E | **Divergence de calendrier** | Rebasage léger `26.1`, `26.6b`, `26.10` + plan directeur |
| **`D10`** | Orchestration du Lot 3 (`26.3 ∥ 26.4a ∥ 26.4b`) | **3 worktrees isolés (`workspace: "share"`)** puis fusion séquentielle `26.3 → 26.4a → 26.4b` avec rechaînage linéaire du `down_revision` Alembic de `26.4b` | Corrige §3 du plan | Rebasage léger plan §3/§4, `epics.md`, `sprint-status.yaml` |
| **`D11`** | Gouvernance d'exécution & commits | Pour chaque story dev (`26.1..26.10`) : **2 `bmad-dev-worker` (`flash`) distincts** (1 Implémentation + 1 Tests & Vérifications `AD-17`) puis `bmad-architect-worker` (`pro` / `bmad-code-review`) et **1 commit local atomique par story** | Précise §4 du plan | Rebasage plan §4, `epics.md` |

---

## Détail des décisions

### `D1` — Architecture du moteur de tour unique

- **Décision & contexte :** Faire converger les trois chemins concurrents (`/three-speed/stream`, DAG `AssistantAgentService` sans appelant UI, et `POST /executions/reflexive` déclenché en double dans `useInboxPanelController`) vers un moteur unique (`H-01`, `H-02`, `H-29`, plan §2.1).
- **Option retenue :** **Hybride `AssistantTurnEngine` dans `packages/orcia-core`** :
  - **Speed 1** en fast-path *single-shot* sans boucle d'outils (pré-fetch RAG borné `< 50 ms`, streaming direct, persistance de session après le premier octet pour tenir `TTFT p95 < 1,2 s`).
  - **Speed 2 / Speed 3** portés par le profil **`ASSISTANT`** de `NonDeterministicReflexiveRuntime`, dans lequel les 5 nœuds historiques `AD-15` deviennent des phases (`N1 IntentGuard`, `N2 Planner + Ontologie`, `N3 Pré-fetch / Boucle d'outils`, `N4 EvidenceTable serveur`, `N5 Synthèse` via `AssistantPromptBuilder` puis `CitationGuard`).
  - Interdiction stricte de `ConnectorReflexiveWriteGateAdapter` dans le profil `ASSISTANT` (`H-29`) : toute écriture SI passe par `approval_required` → `CONTINUE_IN_PROCESS` (DBOS + Gate humaine).
- **Alternatives rejetées :**
  1. *100 % `NonDeterministicReflexiveRuntime` pour Speed 1, 2 et 3 (`ASSISTANT_FAST`)* : la création préalable de `reflexive_execution_sessions` en PG18 avant le premier octet menace directement l'exigence `TTFT p95 < 1,2 s`.
  2. *Refonte du DAG 5 nœuds `AssistantAgentService` (`AD-15` littéral)* : duplique à coût `XL` les budgets, `cancel`, `synthesize_now` et la diffusion Redis déjà éprouvés sur le runtime réflexif en Epic 16.
- **Justification technique & impact :** Capitalise sur l'existant mûr sans réinvention et isole `PROCESS` (défaut inchangé, gardes `test_story_16_2_*`). Crée **`AD-25`** et amende **`AD-15`** (`AD-3` et `AD-19` intacts). Stories impactées : `26.0`, `26.4b`, `26.6b`, `26.7`, `26.9`. Risque : **Moyen** (partage de runtime avec `PROCESS`, contenu par profil). Coût : **M**.

---

### `D1.a` — Escalade automatique `Speed 1 → Speed 2` avec indicateur visible

- **Décision & contexte :** Permettre à l'utilisateur resté en Speed 1 de bénéficier automatiquement de l'investigation outillée Speed 2 quand sa requête l'exige, sans violer ni le `TTFT < 1,2 s` de Speed 1 ni le critère de sortie §6 (« **1** chemin d'exécution LLM par tour utilisateur »).
- **Option retenue :** **Escalade 100 % pré-LLM avec indicateur visible** :
  - Décision prise **avant tout appel LLM** à l'issue de `N1 IntentGuard` (détection déterministe d'intention nécessitant un outil) **ou** immédiatement après le pré-fetch RAG borné `N3 < 50 ms` lorsque la preuve récupérée est insuffisante/vide pour répondre de manière fondée — et **uniquement si `supports_tools=true`** sur le modèle actif.
  - Lorsqu'elle se déclenche, `AssistantTurnEngine` bascule le tour (`turn_id`) vers l'acteur Dramatiq Speed 2 sur le **même flux Redis Streams**, émet l'événement SSE **`speed_escalated`** (`from_speed: "speed_1"`, `to_speed: "speed_2"`, `reason_code`), et l'UI affiche un badge/indicateur localisé FR/EN dans `@orcia/ui`.
- **Alternatives rejetées :**
  1. *Vitesse stricte selon le sélecteur UI sans escalade (défaut écrit initial)* : prédictible mais pénalise l'utilisateur qui omet de basculer manuellement en Speed 2.
  2. *Escalade post-LLM après un premier essai Speed 1* : **rejetée car contradictoire avec le §6 et le NFR TTFT** — provoquerait deux appels LLM pour un même tour, doublerait le coût et laisserait des jetons déjà streamés impossibles à rétracter.
- **Justification technique & impact :** Préserve l'invariant d'un unique appel/chaîne LLM par tour et n'ajoute au pire que la borne `< 50 ms` du pré-fetch avant bascule. Stories rebasées : **`26.0`** (ajout événement SSE `speed_escalated`), **`26.7`** (logique pré-LLM et passage de témoin Redis → Dramatiq), **`26.9`** (badge localisé `@orcia/ui` + i18n + E2E). AD : `AD-25`, `AD-15`, `AD-24`. Risque : **Faible**. Coût : **S**.

---

### `D1.b` — Périmètre du Studio Mode B (`@xyflow/react`) sur les phases `N1–N5`

- **Décision & contexte :** Clarifier comment le graphe Studio Mode B (`assistant_studio_graphs`, `26.4b`) paramètre le profil `ASSISTANT` dans l'amendement `AD-15` / `AD-25` (audit §2.0.2, `H-09`, `H-26`).
- **Option retenue :** **Topologie `N1–N5` fixe et verrous scellés ; paramétrage déclaratif de `N2–N5` uniquement** :
  - L'enchaînement `N1 → N2 → N3 → N4 → N5 → CitationGuard` est immuable.
  - Les gardes constitutionnelles (Couche 1, `N1 IntentGuard` / ancres `AD-3`, Verrou V5, `CitationGuard`) ne sont ni supprimables ni contournables.
  - Le Studio Mode B paramètre uniquement les réglages déclaratifs des phases `N2–N5` (pondération ontologique `N2`, top-k RAG / seuil d'escalade `D1.a` / sous-ensemble autorisé d'outils pré-validés `N3`, règles de fraîcheur `N4`, budgets et instructions d'espace `N5`), reflétés en UI `@xyflow/react` avec nœuds de garde verrouillés.
- **Alternatives rejetées :**
  1. *Topologie partiellement modulable (`N2`/`N3` désactivables par espace)* : risque de dégrader silencieusement la qualité ontologique ou documentaire par mauvaise configuration admin.
  2. *Graphe entièrement libre* : **rejetée car contraire à `FR-4`, `AD-3` et `AD-15`** (permettrait de court-circuiter Couche 1, V5 ou les ancres humaines).
- **Justification technique & impact :** Donne au Studio Mode B un effet réel et persisté en PG18 sans jamais compromettre les garanties constitutionnelles d'ORCIA. Stories impactées : `26.0`, `26.4b`, `26.7`, `26.9`. AD : `AD-25`, `AD-15`, `AD-3`. Risque : **Faible**. Coût : **S**.

---

### `D2` — Protocole HTTP/SSE v2 & hébergement d'exécution des tours

- **Décision & contexte :** Éliminer les pertes d'état en RAM (`ACTIVE_WORKSPACE_TURNS`), les écrasements multi-onglets, les coupures au F5 et l'incompatibilité `--workers > 1` (`H-10`, `H-21`, plan §2.1).
- **Option retenue :** **Protocole asynchrone `202` + Redis Streams avec hébergement hybride** :
  - `POST /api/v1/assistant/turns` retourne `HTTP 202` + `turn_id` après validation des gardes (`ScopeAccessGuard`, Observateur, rate-limit, `supports_tools`).
  - `GET /api/v1/assistant/turns/{turn_id}/stream?after=<cursor>` consomme et rejoue **Redis Streams** (rattachable au F5 et entre workers API).
  - **Speed 1** s'exécute dans une **`asyncio.Task` bornée** dans `apps/api` (registre actif + `add_done_callback` + drain gracieux sur `SIGTERM`) pour éviter la latence de file et tenir `TTFT p95 < 1,2 s`.
  - **Speed 2 / Speed 3** (ainsi que les tours Speed 1 escaladés par **`D1.a`**) s'exécutent dans un **acteur Dramatiq idempotent** (`apps/worker`, clé d'idempotence `turn_id`) publiant dans le même Redis Stream.
- **Alternatives rejetées :**
  1. *100 % acteurs Dramatiq pour Speed 1, 2 et 3* : pénalise le TTFT du fast-path conversationnel simple et rend le chat totalement indisponible si le worker est arrêté.
  2. *100 % `asyncio.Task` dans `apps/api` sans Dramatiq* : expose les boucles longues Speed 2/3 (`<= 25` itérations) à une perte brutale en cas de redémarrage/crash d'un pod API hors fenêtre `SIGTERM`, en retrait de `AD-2`.
- **Justification technique & impact :** Combine réactivité `< 1,2 s` sur le fast-path et résilience worker sur les investigations multi-étapes. Stories impactées : `26.0`, `26.3`, `26.7`, `26.9`. AD : `AD-25`, cohérence `AD-2`. Risque : **Moyen** (dépendance opérationnelle `apps/worker` pour Speed 2/3). Coût : **M**.

---

### `D2.a` — Indisponibilité de `apps/worker` (Dramatiq) en Speed 2/3 & fidélité Couche 2 / E2E

- **Décision & contexte :** Trancher le comportement si un tour Speed 2/3 (ou escaladé `D1.a`) est enfilé vers Dramatiq alors qu'aucun worker ne consomme `RedisBroker`, afin d'éviter un blocage silencieux du SSE et une divergence entre tests et production (Règle 4 de `GEMINI.md`).
- **Option retenue :** **Fail-fast explicite sans repli caché + vrai consommateur Dramatiq en Couche 2 / E2E** :
  - Présence d'un heartbeat Redis des workers assistant ; à la soumission / prise en charge, un timeout d'acquittement **`<= 3 s`** émet un événement SSE terminal **`stream_error`** (et/ou statut d'échec rattachable) portant l'enveloppe RFC 9457 **`503 ERR_ASSISTANT_WORKER_UNAVAILABLE`** + `trace_id`, journalisé via `get_logger(...)`.
  - **Aucun repli silencieux** vers `asyncio.Task` dans `apps/api`.
  - Les tests d'intégration Couche 2 (`testcontainers`) et la suite E2E démarrent un vrai worker Dramatiq raccordé au même Redis.
- **Alternatives rejetées :**
  1. *Repli automatique sur `asyncio.Task` dans `apps/api` après `2 s`* : masque les incidents d'exploitation en production et force la maintenance de deux chemins d'exécution pour Speed 2/3.
- **Justification technique & impact :** Garantit une détection immédiate des pannes de worker et une fidélité `100 %` entre tests et production (`AD-17`). Stories impactées : `26.0` (code erreur SSE v2), `26.3` (heartbeat + timeout + tests Couche 2 avec worker), `26.10` (E2E & multi-worker). AD : `AD-25`, `AD-17`. Risque : **Faible**. Coût : **S**.

---

### `D3` — Politique SSRF des LLM on-prem & exposition de `GET /bootstrap/platform-setup-state`

- **Décision & contexte :** Éliminer les failles de rebinding DNS / SSRF sur les endpoints LLM configurés en PG18 et le risque de fuite d'informations ou secrets sur la route d'accostage non authentifiée (`H-16`, `H-17`, Règle 4 de `GEMINI.md`).
- **Option retenue :** **Allowlist administrée + *pinning* DNS + projection minimale Jour 0 sans secret** :
  - **Blocage permanent non dérogable** : plages link-local et métadonnées Cloud (`169.254.0.0/16`, `fe80::/10`, `100.100.100.200`, `metadata.google.internal`), ainsi que les ports de services internes ORCIA (PostgreSQL `5432`, Redis `6379`, SeaweedFS S3).
  - **Hôtes privés / on-prem** : RFC 1918, `.local` et `.internal` soumis à une **allowlist administrée** (hôtes ou CIDR déclarés par `PLATFORM_ADMIN`) ; `localhost` / loopback pré-autorisé **uniquement** lorsque `ORCIA_ENV in ("local", "test")`.
  - **Double contrôle + *pinning* DNS** : validation à l'enregistrement/modification **et** re-validation de `endpoint_uri` lu depuis PG18 à l'ouverture de connexion avec résolution DNS épinglée (`getaddrinfo` vérifié avant `httpx`, protection contre le DNS rebinding).
  - **`GET /bootstrap/platform-setup-state`** : la route publique Jour 0 (sans authentification, indispensable au boot vierge après `pnpm db:reset`) ne renvoie qu'une projection minimale **`{is_initialized, step}`** (zéro secret, zéro `apiKey`, zéro URI interne) ; la vue détaillée reste réservée à `PLATFORM_ADMIN` authentifié, et `apiKey` est exclue de `platform_setup_snapshot` + `str(exc)` systématiquement passé au scrubber (`_REGISTERED_SECRET_VALUES` borné).
- **Alternatives rejetées :**
  1. *Blocage strict de tout RFC 1918 / loopback configurable en base* : casse le déploiement dynamique de serveurs Ollama / vLLM on-prem dans le Hub Modèles IA (`CAP-190`).
  2. *Blocage métadonnées/link-local seul en laissant tout RFC 1918 ouvert* : expose l'intranet et les services privés à une SSRF latérale.
- **Justification technique & impact :** Concilie souveraineté on-prem, sécurité SecOps et préservation du parcours Jour 0. Stories impactées : `26.0`, `26.1`, `26.10`. AD : amendements `AD-21` & `AD-24`. Risque : **Faible**. Coût : **S–M**.

---

### `D4` — Persistance des messages de fil & séparation de la trace d'outils

- **Décision & contexte :** Supprimer l'envoi d'historique depuis `localStorage` et le re-découpage fragile de `thread_summary` sur `" | "` (`H-18`), tout en empêchant l'injection de messages `role: "tool"` forgés (`H-15`).
- **Option retenue :** **Table dédiée `assistant_thread_messages` (`UUIDv7`) + liaison `turn_id` vers `reflexive_execution_sessions`** :
  - Colonnes principales : `id` (`UUIDv7` PK), `thread_id` (FK `assistant_threads` `ON DELETE CASCADE`), `turn_id`, `role CHECK IN ('user', 'assistant')`, `content`, `citation_map JSONB`, `token_count`, `created_at` ; index `(thread_id, created_at)`.
  - La trace détaillée d'investigation (`tool_call`, `tool_result`, étapes d'approbation) reste attachée à `reflexive_execution_sessions` via `turn_id` et n'est jamais réinjectée en tant que messages `role: "tool"` dans la fenêtre multi-tours.
- **Alternatives rejetées :**
  1. *Stocker aussi `role='tool'` dans `assistant_thread_messages`* : sature le budget de tokens des fils longs et rouvre une surface d'injection inter-tours (`H-15`).
  2. *Colonne `messages_jsonb` sur `assistant_threads`* : contention `UPDATE`, réécriture du blob complet à chaque tour et pagination impossible côté SQL.
- **Justification technique & impact :** Relecture à froid PG18 propre, pagination/trimming SQL performant par budget de tokens et cloisonnement structurel des sorties d'outils. Stories impactées : `26.0` (ERD `architecture.md`), `26.5` (migration Alembic + trimmer), `26.7`, `26.9`. Risque : **Faible**. Coût : **S–M**.

---

### `D5` — Gestion des modèles sans *function calling* natif (`supports_tools`)

- **Décision & contexte :** Certains modèles locaux ou anciens n'exposent pas le *tool calling* structuré natif (`H-03`, `H-27`).
- **Option retenue :** **Drapeau `supports_tools` découvert à 0 token (+ override `PLATFORM_ADMIN`), repli UI et refus serveur `422`** :
  - Persistance d'une colonne `supports_tools` en PG18 au Hub Modèles IA (`AD-24`), alimentée par découverte sans jeton (catalogue / métadonnées provider) avec possibilité de surcharge explicite par `PLATFORM_ADMIN` (cas des proxies OpenAI-compatibles opaques).
  - Quand `supports_tools=false` : aucun `tools` n'est transmis au provider, l'escalade auto `D1.a` est désactivée, les vitesses Speed 2/3 sont désactivées en UI avec message localisé `fr`/`en`, et tout appel API forçant Speed 2/3 reçoit **`422 ERR_MODEL_TOOLS_UNSUPPORTED`** (RFC 9457).
  - **Aucune émulation XML/ReAct** dans le prompt.
- **Alternatives rejetées :**
  1. *Dégradation silencieuse serveur Speed 2/3 → Speed 1* : induit l'utilisateur ou un client API en erreur sur le niveau d'investigation réellement exécuté.
  2. *Émulation ReAct / balises XML dans le prompt* : fragile selon les modèles et propice au forgeage de balises d'outils par injection.
- **Justification technique & impact :** Contrat clair, déterministe et sûr sur les 4 dialectes (`OpenAI`, `Anthropic`, `Gemini`, `Ollama`). Stories impactées : `26.0`, `26.6a`, `26.7`, `26.9`. AD : `AD-24`, `AD-25`. Risque : **Faible**. Coût : **S–M**.

---

### `D6` — Sort de `POST /assistant/workflows/save-and-launch` & continuité `CONTINUE_IN_PROCESS`

- **Décision & contexte :** `save_and_launch_workflow` s'exécute actuellement en mémoire (`WorkflowEngineService`, `commit_immediately=True`) et ignore `human_authored_required: true`, en violation directe d'`AD-2` et `AD-3` (`H-05`), sans aucun appelant UI (`H-26`).
- **Option retenue :** **Raccorder `CONTINUE_IN_PROCESS` (`POST /turns/{id}/approve` + `POST /folders/{id}/launch-process`) à DBOS + PG18 (`WAITING_FOR_HUMAN_ANCHOR`), et déprécier (`26.8`) puis supprimer (`26.10`) `POST /assistant/workflows/save-and-launch`** :
  - Toute écriture SI ou action nécessitant une signature humaine passe par `approval_required` → `POST /turns/{id}/approve` (ou lancement depuis dossier `POST /folders/{id}/launch-process`), qui démarre un `WorkflowRun` DBOS persistant (`workflow_runs`, `step_executions`, `blackboard_snapshots`, `domain_events_outbox`) et s'arrête impérativement au premier `WAITING_FOR_HUMAN_ANCHOR` / Gate (`422 ERR_HUMAN_ANCHOR_REQUIRED` en cas de tentative de commit sans signature).
  - `POST /assistant/workflows/save-and-launch` et le chemin d'exécution en mémoire associé sont marqués `deprecated` en `26.8` puis supprimés en `26.10`.
- **Alternatives rejetées :**
  1. *Conserver `/workflows/save-and-launch` en le migrant sur DBOS + PG18 et lui créer un parcours UI en `26.9`* : dupliquerait sans nécessité `approve` et `folders/{id}/launch-process` tout en alourdissant `26.9`.
  2. *Corriger uniquement `WorkflowEngineService` en mémoire* : **rejetée car contraire à `AD-2` (persistance DBOS/PG18 obligatoire) et à l'objectif « zéro RAM métier »**.
- **Justification technique & impact :** Éradique la faille `H-05` sans entretenir de route orpheline ni de duplication fonctionnelle. Stories rebasées : `26.0`, `26.8`, `26.10`. AD : `AD-2`, `AD-3`, `AD-25`. Risque : **Faible**. Coût : **S–M**.

---

### `D7` — Sort de l'outil MCP `assistant.ask` (`POST /mcp/spaces/{ws}/invoke`)

- **Décision & contexte :** `governed_mcp_exposure.py:~L251` expose un stub pour `assistant.ask`, laissé ouvert entre raccordement et dépréciation en `26.7`.
- **Option retenue :** **Raccorder `assistant.ask` à `AssistantTurnEngine` en mode Speed 1 synchrone lecture seule gouvernée** :
  - Exécuté sous les 7 verrous MCP, `QuotaGuard`, `ScopeAccessGuard` et `READ_SOURCE` / `CONFIDENTIAL_RESTRICTED` serveur.
  - Passe par le constructeur `AssistantPromptBuilder` unique (Couche 1 immuable), l'ontologie PG18, le RAG hybride et `CitationGuard`, puis retourne réponse + `citation_map`.
  - Aucune écriture SI et aucune boucle d'outils récursive (`Speed 2/3` exclue sur cette surface MCP).
- **Alternatives rejetées :**
  1. *Déprécier (`26.7`) puis retirer (`26.10`) `assistant.ask` du catalogue MCP* : prive les clients MCP externes d'un point d'interrogation documentaire gouverné et cité d'un espace ORCIA.
  2. *Autoriser Speed 2/3 (boucle d'outils imbriquée) via MCP* : risque d'amplification récursive des coûts et de dépassement des délais HTTP synchrones sur `/mcp/.../invoke`.
- **Justification technique & impact :** Aligne la surface MCP `AD-12` sur le moteur unique `AD-25` tout en bornant strictement latence, coût et surface d'attaque. Stories impactées : `26.0`, `26.7`, `26.10`. AD : `AD-12`, `AD-25`. Risque : **Faible**. Coût : **S**.

---

### `D8` — Cycle de vie des routes historiques, de la façade `/three-speed/*` & surface API cible finale

- **Décision & contexte :** Le critère de sortie §6 impose **`0` endpoint assistant sans appelant ni consommateur documenté**. Or plusieurs routes historiques v1 n'ont plus d'appelant après la bascule UI de `26.9`, et `POST /threads/{id}/turns` ferait double emploi avec `POST /assistant/turns` (acceptant `thread_id`).
- **Option retenue :** **Étrangleur `/three-speed/*` maintenu jusqu'en `26.9`, puis purge complète vers la surface canonique v2 en `26.10`** :
  - En `26.7` : `/three-speed/stream` (ainsi que `active-turn`, `stop`, `feedback`) devient une façade mince relayant `AssistantTurnEngine` + Redis Streams afin de garder les specs E2E `02`, `12`, `16` et `21` vertes sans interruption ; `/chat`, `/chat/stream`, `/three-speed/turn`, `/three-speed/invalidate-cache`, `/citations/verify-turn` et `/artifacts/action` sont marquées `deprecated` dans OpenAPI (plus `/workflows/save-and-launch` en `26.8`).
  - En `26.9` : bascule complète de `apps/web` et mise à jour des specs Playwright `02`, `12`, `16`, `21` et `22` sur la surface canonique v2 :
    - `POST /api/v1/assistant/turns` (`thread_id` optionnel inclus)
    - `GET /api/v1/assistant/turns/{turn_id}/stream?after=<cursor>`
    - `GET /api/v1/assistant/turns/active` (ou réhydratation par espace/fil)
    - `POST /api/v1/assistant/turns/{turn_id}/{stop,approve,synthesize-now,feedback}`
    - `GET /api/v1/assistant/threads/{thread_id}/messages`
    - `/api/v1/assistant/folders/*` et `/api/v1/assistant/governance/*`
  - En `26.10` : **suppression définitive** de toutes les routes `deprecated` **et** de la façade `/three-speed/*` ainsi que du doublon `POST /threads/{id}/turns`, régénération SDK OpenAPI `0-diff` et nettoyage des tests associés.
- **Alternatives rejetées :**
  1. *Conserver `/three-speed/{stream,active-turn,stop,feedback}` en alias v1 permanent après `26.10`* : maintiendrait deux schémas SSE et deux familles SDK en contradiction avec la convergence cible.
  2. *Supprimer les routes dès `26.7`* : **rejetée car contraire au principe d'étrangleur (§7)** et casserait les specs E2E avant la migration UI `26.9`.
- **Justification technique & impact :** Transition sans rupture pour l'UI et les E2E jusqu'en `26.9`, puis surface API minimale et unique en `26.10`. Stories rebasées : `26.0`, `26.7`, `26.9`, `26.10`. AD : `AD-25`, OpenAPI v2 `0-diff`. Risque : **Faible**. Coût : **S–M**.

---

### `D9` — Gouvernance de `capabilities.yaml` : `CAP-260` & requalification de `CAP-022`, `CAP-070`, `CAP-072`

- **Décision & contexte :** L'audit (§1.2.2) montre que `CAP-022`, `CAP-070` et `CAP-072` portent un statut optimiste alors que le chemin réellement servi à l'UI ne les applique pas encore.
- **Option retenue :** **Vérité terrain immédiate dès `26.1`, création de `CAP-260` en `26.6b`, promotion `runtime` en `26.10` sur preuve E2E** :
  - Dès **`26.1`** : rétrograder `CAP-022`, `CAP-070` et `CAP-072` à `verification: api` dans `docs/product/capabilities.yaml` (`pnpm site:sync && pnpm site:check`) afin de refléter immédiatement l'état réel sur `/showcase`.
  - En **`26.6b`** : créer **`CAP-260`** (« Boucle d'outils gouvernée de Mon Assistant ») en `verification: api` dès le câblage backend de `GovernedAssistantToolRouter`.
  - Au fil de `26.7`–`26.9` : tenir à jour les surfaces routes/UI de ces capacités pour conserver `pnpm site:check` vert à chaque story.
  - En **`26.10`** : promouvoir `CAP-022`, `CAP-070`, `CAP-072` et `CAP-260` en **`verification: runtime`** uniquement après passage au vert de la spec Playwright `22-assistant-tool-loop-approval-and-reattach.spec.ts` sur le moteur unique réel.
- **Alternatives rejetées :**
  1. *Attendre `26.10` pour requalifier `CAP-022`/`070`/`072`* : laisse `/showcase` afficher une couverture runtime trompeuse pendant toute la durée de l'Epic.
  2. *Ne pas créer `CAP-260` et absorber la boucle d'outils dans `CAP-022` / `CAP-160`* : mélange l'orchestration générique de processus (`CAP-160`) et la boucle d'outils assistant sans écriture SI directe.
- **Justification technique & impact :** Transparence immédiate du registre produit et respect continu de `pnpm site:check`. Stories rebasées : `26.1`, `26.6b`, `26.10`, plus mise à jour du §7 du plan directeur. Risque : **Très faible**. Coût : **XS**.

---

### `D10` — Orchestration du Lot 3 (`26.3`, `26.4a`, `26.4b`) face aux collisions de fichiers et têtes Alembic

- **Décision & contexte :** Le §3 du plan initial qualifiait `26.3 ∥ 26.4a ∥ 26.4b` de « fichiers disjoints ». Or `epics.md` met en évidence des cibles partagées (`apps/api/src/orcia_api/routers/assistant_workspace.py` entre `26.3` et `26.4b` ; `dependencies/portal_and_assistant.py` et `assistant_folders_and_sharing.py` entre `26.4a` et `26.4b`) et deux révisions Alembic (`26.4a` et `26.4b`).
- **Option retenue :** **Parallélisme en 3 worktrees isolés (`workspace: "share"`) suivi d'une fusion séquentielle contrôlée `26.3 → 26.4a → 26.4b`** :
  - Lancement des 3 stories dans des espaces de travail `share` distincts.
  - Fusion dans la branche principale `feat/epic-26-assistant-harness-debt-remediation` dans l'ordre strict **`26.3` → `26.4a` → `26.4b`**.
  - Lors de la fusion de `26.4b` : rechaînage linéaire obligatoire du `down_revision` de sa migration Alembic sur la révision produite par `26.4a` (`1` seul `alembic heads`), résolution propre des 3 fichiers partagés, puis validation des tests et revue `bmad-code-review` sur l'état fusionné avant chaque commit atomique.
- **Alternatives rejetées :**
  1. *Exécution séquentielle pure sur le workspace principal* : allonge inutilement la durée murale du Lot 3 (`×3`).
  2. *Parallélisme direct sur `workspace: "inherit"`* : **rejetée car elle produit 2 têtes Alembic concurrentes et des écrasements mutuels**.
- **Justification technique & impact :** Conserve le bénéfice du parallélisme sur le Lot 3 tout en préservant une chaîne Alembic linéaire stricte et des fusions déterministes. Artefacts mis à jour : plan directeur §3/§4, `epics.md` (en-tête Lot 3 et `26.3`–`26.4b`), `sprint-status.yaml`. Risque : **Faible**. Coût : **XS**.

---

### `D11` — Protocole d'exécution par sous-agents distincts (Implémentation vs Tests) & commit atomique par story

- **Décision & contexte :** Directive opérationnelle validée par l'utilisateur en clôture du `/grill-me` pour l'exécution de la Phase 3, en complément de [`.agents/rules/bmad-model-routing.md`](../../.agents/rules/bmad-model-routing.md) et du §4 du plan directeur.
- **Option retenue :** **Séparation stricte Implémentation / Tests + revue architecturale + commit local atomique par story** :
  - **Lot 0 (`26.0`)** : `bmad-architect-worker` (`pro`) avec ce fichier d'arbitrages en entrée → STOP et présentation à l'utilisateur (`lint_spine.py`, `npx gitnexus analyze`) avant tout code.
  - **Chaque story de développement (`26.1` à `26.10`)** :
    1. **`bmad-dev-worker` (`flash`) #1 — Implémentation** : crée/complète les Sections 1 et 2 du rapport Tech Lead (après `npx gitnexus analyze` & `gitnexus_impact`), code la story en TDD (découpage `< 300 L`, frontières `AD-19`), sans valider seul la clôture finale.
    2. **`bmad-dev-worker` (`flash`) #2 — Tests & Vérifications (distinct du #1)** : conçoit/complète et exécute de façon indépendante la batterie des 5 couches `AD-17` (`pytest --cov-fail-under=90`, `testcontainers` PG18/Redis, `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck test`, `lint_spine.py`, OpenAPI `0-diff`, `pnpm site:sync && pnpm site:check`), complète la Section 3 du rapport Tech Lead, met à jour `tech-lead-reports/README.md` et `capabilities.yaml`.
    3. **Escalade `pro`** automatique après 2 échecs consécutifs sur une même cause racine (`bmad-model-routing.md`).
    4. **Revue `bmad-code-review` / `bmad-architect-worker` (`pro`)** avant passage à `done` dans `sprint-status.yaml`.
    5. **1 commit Git local atomique par story** sur `feat/epic-26-assistant-harness-debt-remediation` (zéro `git push`, zéro altération d'autres branches).
  - **STOP de contrôle à chaque fin de lot** (`L0`, `L1`, `L2`, `L3`, `L4`, `L5`, `L6`, `L7`) avec bilan synthétique et attente du **GO** utilisateur.
- **Alternatives rejetées :**
  1. *Un unique `bmad-dev-worker` couvrant implémentation et vérification finale* : expose au biais de confirmation entre l'auteur du code et le vérificateur des 5 couches `AD-17`.
  2. *Commit groupé par lot ou en fin d'Epic* : complique le `bisect` et l'auditabilité story par story.
- **Justification technique & impact :** Renforce l'indépendance de la vérification `AD-17` et la traçabilité Git par story. Artefacts mis à jour : plan directeur §4. Risque : **Très faible**. Coût : **S** (orchestration).

---

## Révision R — Simplification de la cible (2026-11-21 09:00)

- **Déclencheur :** analyse critique du plan directeur (complexité induite par 4 voies d'exécution, 2 hébergements, une escalade avec passage de témoin en cours de tour, un Studio graphique sans usage et une façade v1 jetable).
- **Arbitrages utilisateur :**
  1. survie au crash d'un pod pour les tours longs : **non requise** ;
  2. Studio Mode B : **reporté** en `action_item` ;
  3. escalade automatique : remplacée par un **bouton « Approfondir »** ;
  4. étrangleur : **superflu**, consigné en `action_item`.

| # | Remplace | Décision révisée | Stories rebasées |
| :---: | :--- | :--- | :--- |
| **`R1`** | `D2` (hébergement Dramatiq) + `D2.a` | **Hébergement unique** : tous les tours (Speed 1, 2, 3) s'exécutent en `asyncio.Task` bornée dans `apps/api`. Le registre des tours, le flux d'événements (Redis Streams, curseur) et le signal `stop` vivent dans Redis, ce qui garantit le rattachement après F5 et le fonctionnement multi-worker. Arrêt gracieux sur `SIGTERM`, borné par le budget mural du profil. Une clé de vie par tour (TTL rafraîchi par la tâche) détecte un tour orphelin après crash : au rattachement, le client reçoit `stream_error` `ERR_ASSISTANT_TURN_INTERRUPTED` (RFC 9457), **sans reprise automatique**. Aucun acteur Dramatiq ni heartbeat de worker ; l'erreur `503 ERR_ASSISTANT_WORKER_UNAVAILABLE` disparaît. Le **protocole** de `D2` (`POST /turns` 202 + `GET …/stream?after=`) est conservé. | `26.0`, `26.3`, `26.7`, `26.10` |
| **`R2`** | `D1.b` | **Studio Mode B reporté** (`ACTION_ITEM-26.1`). Topologie `N1–N5` fixe, **aucun paramétrage graphique** dans l'Epic 26, pas de table `assistant_studio_graphs`. La gouvernance **Mode A** (consignes texte Utilisateur / Équipe / Espace sur `workspace_customization_overrides`) est maintenue. Les routes `governance/mode-b/{save,reset}` (RAM, sans appelant) sont **supprimées** en `26.4b`. | `26.0`, `26.4b`, `26.7`, `26.9` |
| **`R3`** | `D1.a` | **Pas d'escalade automatique.** Après un tour Speed 1, l'UI propose un bouton **« Approfondir »** (visible si `supports_tools=true`), qui crée un **nouveau tour** Speed 2 dans le même fil (`parent_turn_id`, même question). Le moteur ajoute à `turn_completed` un indicateur déterministe `low_evidence` (`EvidenceTable` vide) pour mettre le bouton en avant, sans heuristique ni appel LLM supplémentaire. Plus d'événement `speed_escalated` ni de passage de témoin en cours de tour. | `26.0`, `26.7`, `26.9` |
| **`R4`** | `D8` (calendrier) + `D6` (dépréciation) | **Pas d'étrangleur** (`ACTION_ITEM-26.2`) : la SPA est l'unique consommateur et elle est livrée avec l'API. **Bascule directe** du transport de tour (backend + UI + specs E2E `02`/`12`/`16`/`21`) dans **un seul commit de `26.7`**. Chaque route remplacée ou sans appelant est **supprimée dans la story qui livre son remplaçant**, sans phase `deprecated` : `/three-speed/*`, `/chat*`, `/citations/verify-turn`, `/artifacts/action` en `26.7` ; `/workflows/save-and-launch` en `26.8` ; doublon `POST /threads/{id}/turns` en `26.9`. `26.10` vérifie seulement qu'il reste 0 endpoint sans appelant. La surface canonique cible de `D8` est inchangée. | `26.7`, `26.8`, `26.9`, `26.10` |

**Effets attendus :**
- une seule voie d'exécution asynchrone (fast-path + profil `ASSISTANT` dans le même processus), plus `assistant.ask` (`D7`, inchangé) ;
- aucune dépendance à `apps/worker` pour l'assistant ;
- 1 table et 2 routes en moins (Mode B) ;
- plus aucun seuil heuristique d'escalade ni code de façade jetable.

**Risque accepté :** perte d'un tour long en cas de crash brutal d'un pod (hors déploiement). Le tour est signalé comme interrompu et l'utilisateur le relance.
