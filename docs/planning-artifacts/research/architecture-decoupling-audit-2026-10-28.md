# Audit d'architecture ORCIA : découplage, extensibilité et maturité entreprise

> **Rôle** : architecte principal, revue contradictoire « Blind Hunter ».
> **Version du code auditée** : `fb7d460` (stories 3.2a, 3.2s et 3.2b livrées), le 28/10/2026.
> **Méthode** : lecture du code, recherches de motifs, import réel de `orcia_core.orchestration` dans `.venv`, `lint-imports` (3 contrats respectés), lecture des migrations `0001` à `0012`.
> **Convention** : toutes les références `fichier:Lnn` sont relatives à `packages/orcia-core/src/orcia_core/` sauf mention contraire.

> [!NOTE]
> Plusieurs termes du cahier des charges **n'existent pas dans le code** : « Sanctum », Spec-Kit, et des verrous propres à DBOS. Je l'indique à chaque fois au lieu de supposer.

---

## 1. Isolation entre la plateforme et le domaine SDLC

### Note de découplage : **2 / 5**

| Ce qui fonctionne (✅) | Ce qui pose problème (❌) |
|---|---|
| `orcia_kernel` ne dépend d'aucun framework. Ses ports sont génériques (`LLMPort`, `ObjectStoragePort`, `OutboxRelayPort`, `SandboxPort`, `BlackboardPort`, `ClockPort`). | Le vocabulaire SDLC est présent **dans le kernel**, dans **le modèle de workflow**, dans **son validateur** et dans **le moteur d'exécution**. |
| `import-linter` vérifie 3 contrats (couches, absence de cycles, kernel sans framework) : **0 violation**. | Les schémas de connecteurs sont des **listes fermées**, recopiées à 5 endroits du code et dans 4 contraintes `CHECK` de la base. |
| Plugins `entry_points` amorcés (`orcia.uri_resolvers`, `orcia.llm_gateways`). | Importer `orcia_core.orchestration` charge **l'adaptateur BMAD** et le **Permission Broker branché sur Jira**. |
| Outbox `domain_events_outbox` et `OutboxRelayPort` indépendants du moteur (Q2 = 2A). | Le moteur exécute encore des **étapes simulées**, avec des chaînes de démonstration SDLC écrites en dur. |

### 1.1 Fuites de vocabulaire métier, avec preuves

| # | Gravité | Emplacement | Fuite constatée |
|---|---|---|---|
| L1 | 🔴 | `packages/orcia-kernel/src/orcia_kernel/enums.py:L54-L61` | `MemlogMarkerType` contient `BUG_CODE_SUSPECTED` et `DOC_OBSOLETE_SUSPECTED` : du vocabulaire SDLC **dans le kernel universel**. |
| L2 | 🔴 | `orchestration/models.py:L22` | `WorkflowEngineeringMode = Literal["standard", "brownfield_bootstrap"]` : un mode d'ingénierie logicielle dans le modèle générique de workflow. |
| L3 | 🔴 | `orchestration/models.py:L71-L73` | `WorkflowStepSpec.declares_intention`, `writes_code`, `reverse_doc_from_code` : des attributs SDLC sur **chaque étape**, quel que soit le métier. Exposés dans l'API (`apps/api/.../routers/orchestration.py:L92-L94`). |
| L4 | 🔴 | `orchestration/yaml_validator.py:L158-L185` | La règle FR-13 « intention → code » et la restriction au mode `brownfield_bootstrap` sont **écrites en dur dans le validateur du Core**. |
| L5 | 🔴 | `orchestration/engine.py:L258-L275` | L'exécution produit un livrable factice (`"artifact"`, `"adr"`, `"report"`). En mode tâche de fond, elle injecte « Divergence … Confluence (seuil 500€) et git://core-engine (seuil 350€) ». |
| L6 | 🔴 | `orchestration/engine.py:L349-L370`, `L380-L388` | `_build_fast_path_markers` fabrique des marqueurs `BUG_CODE_SUSPECTED` et `DOC_OBSOLETE_SUSPECTED`. `run_background_fast_path_audit` a pour valeur par défaut « Confluence v12 … vs Codebase git:// ». |
| L7 | 🟠 | `orchestration/seeds.py:L29-L158` | Workflows de démonstration `claims-engineering-delivery` (avec `git://`, `confluence://`, `jira_key`) placés dans le package de domaine. Ils sont utilisés par `build_default_orchestration_setup_service`. |
| L8 | 🟠 | `rag/__init__.py:L49-L95` | Données de démonstration (`ws-claims-alpha`, `ds-jira-claims`, `git://claims/core-engine`) dans le `__init__` du domaine RAG. |
| L9 | 🟠 | `rag/models.py:L11-L15`, `L57`, `L155` | Modes d'indexation fermés (`CODE_AST_GRAPH`, `UNIFIED_JIRA`, `AST_SYMBOL`), `source_scheme` limité à `confluence`, `jira`, `git` et `db`, et marqueur `[BUG_CODE_SUSPECTED]`. |
| L10 | 🟠 | `permissions/broker.py:L202-L209` et migration `0004:L72` (`jira_request_url TEXT NOT NULL`) | Le circuit de demande d'accès passe **obligatoirement par Jira** (`jira://IAM/...`). |
| L11 | 🟡 | `catalog/models.py:L16` (`CatalogSourceFormat = "ORCIA" \| "BMAD_PACK"`) et `catalog/bmad_adapter.py` | Le format BMAD (`SKILL.md`, `steps/*.md`) fait partie du catalogue du Core. |

> Les mots `commit` et `branch` présents dans `orchestration` et `blackboard` désignent des **commits de base de données** et des **branches de snapshots** : ce sont des termes techniques légitimes, pas des fuites.

### 1.2 Peut-on exécuter un processus non SDLC sans aucun outillage de développement ?

**Pas aujourd'hui.** Trois preuves :

1. **Ce que charge l'import** : `import orcia_core.orchestration` charge 43 modules, dont `orcia_core.catalog.bmad_adapter`, `orcia_core.permissions.broker` (branché sur Jira) et `orcia_core.ontology`.
2. **Le modèle** : un workflow de rapprochement de factures porterait quand même les champs `writes_code`, `declares_intention` et `mode` (L2, L3). Il passerait le validateur FR-13, mais en restant sémantiquement pollué.
3. **L'exécution** : aucune étape `AGENT` ou `SKILL` n'appelle réellement un agent ou un outil. `engine.py` simule le livrable (L5), et l'étape durable DBOS écrit un contenu figé (`orchestration/_internal/dbos_engine.py:L231-L251` : `{"engine": "dbos-transact-pg18"}`). **Aucun processus, SDLC ou non, ne s'exécute donc réellement de bout en bout.**

### 1.3 Couplages forts

| Type | Preuve |
|---|---|
| **Liste fermée de schémas recopiée à 5 endroits** | `catalog/cas_resolver.py:L24` (`ALLOWED_SCHEMES`), `catalog/models.py:L14`, `permissions/models.py:L23`, `permissions/broker_models.py:L16`, `rag/models.py:L57` |
| **Schéma de base rigide** | `CHECK (scheme IN ('git','jira','confluence','db','nexus'))` dans `0002:L98`, `0002:L174`, `0004:L25`, `0004:L61` ; colonnes `jira_issue_key` et `justifying_jira_key` (`0009:L41`, `L59`) ; table `code_graph_edges` (`0008:L78`) |
| **Types d'étape fermés et définis en double** | `WorkflowStepType` défini à la fois dans `orcia_kernel/enums.py:L14` **et** dans `orchestration/models.py:L23` (`AGENT`, `SKILL`, `SUB_WORKFLOW`, `POST_ACTION_VERIFICATION`), avec un `if step_type == "SUB_WORKFLOW"` dans `engine.py:L223` |
| **État global de processus** | `orchestration/_internal/dbos_engine.py:L26-L32` (`_ACTIVE_ENGINE` global) et `L105` (appel de l'**API privée** `DBOS._recover_pending_workflows()`) |
| **Deux moteurs en parallèle** | `DurableOrchestrationEngine` (`engine.py:L119`, simulé) et `DbosDurableWorkflowEngine` (`_internal/dbos_engine.py`). Aucun des deux n'est branché dans `apps/api/src/orcia_api/dependencies.py`. |

---

## 2. Extensibilité et connecteurs

### 2.1 Ce que coûte aujourd'hui l'ajout d'un connecteur (exemple : `sap://`)

| Étape obligatoire | Fichier | Remarque |
|---|---|---|
| 1. Ajouter `sap` à `ALLOWED_SCHEMES` | `catalog/cas_resolver.py:L24` | Sinon `parse_federated_uri` rejette l'URI (`L41`) |
| 2-5. Ajouter `sap` aux 4 autres types `Literal` | `catalog/models.py`, `permissions/models.py`, `permissions/broker_models.py`, `rag/models.py` | 4 modifications du **Core** |
| 6. Nouvelle migration qui modifie 4 contraintes `CHECK` | `infra/migrations/versions/0013_*` | Schéma Expand → Contract |
| 7. Déclarer un plugin `orcia.uri_resolvers` | `pyproject.toml` du plugin | ⚠️ Le descripteur actuel (`bootstrap/plugin_registry.py`, `UriSchemePluginDescriptor`) ne contient **que des métadonnées** (`scheme`, `description`). Il n'existe **aucun contrat de récupération, d'action ni de vérification de santé**. |
| 8. Écrire la récupération réelle | — | **Impossible sans modifier le Core** : `FederatedUriResolver` ne sait que relire du contenu enregistré à la main (`register_upstream_payload`, `cas_resolver.py:L193`). Le registre de plugins **n'est pas branché** sur le résolveur. |
| 9. Ajouter un circuit de demande d'accès autre que Jira | `permissions/broker.py` | Écrit en dur pour Jira |

**Bilan** : environ 7 fichiers du Core et 1 migration à modifier, sans même obtenir d'exécution réelle. **L'objectif d'une demi-journée est hors d'atteinte**, et l'ajout casse le principe « le Core ne change pas quand on ajoute une extension ».

### 2.2 Ce qui facilite déjà les extensions

| Brique | Emplacement | Ce qu'elle apporte | Maturité |
|---|---|---|---|
| `LLMPort` et plugins `orcia.llm_gateways` | `orcia_kernel/ports.py:L73`, `bootstrap/plugin_registry.py` | Changer de fournisseur LLM sans toucher au Core | 🟢 Fonctionne |
| `OutboxRelayPort` et `DomainEvent` | `orcia_kernel/ports.py:L136`, `orcia_kernel/events.py` | Les connecteurs s'abonnent aux événements (`StepCompleted`, `GateEvaluated`…) sans toucher au moteur | 🟢 Fonctionne ; relais avec `SKIP LOCKED` (`_internal/outbox_repository.py:L65-L86`) |
| `ObjectStoragePort` et stockage par empreinte SHA-256 | `orcia_kernel/ports.py:L106`, `catalog/cas_resolver.py` | Format d'entrée-sortie binaire universel, immuable, vérifié par empreinte | 🟢 |
| Épinglage des versions (`run-lock.json`) | `orchestration/run_lock_service.py` | Toute ressource externe est figée par son empreinte : un run est reproductible quel que soit le vertical | 🟢 |
| Workflow-as-Code, `input_mapping` et `output_mapping` | `orchestration/models.py`, `yaml_loader.py` | Contrat d'entrées-sorties déclaratif entre étapes | 🟡 Générique, mais pollué par L2 et L3 |
| `SUB_WORKFLOW` (profondeur ≤ 3) | `engine.py:L223` | Réutiliser un processus d'un vertical dans un autre | 🟡 |
| Idempotence par `SetWorkflowID` | `_internal/dbos_engine.py:L178-L181` | Pas de doublon pour les déclencheurs (webhook, cron) | 🟢 Côté moteur |
| Déclencheurs (`WEBHOOK`, `CRON`, `LOG_SINK_ALERT`) et `webhook_secret_vault_ref` | `orchestration/models.py:L24`, `L255-L264` | Démarrer un processus par un événement externe ; secret **passé par référence** | 🟡 Modèle seul |
| `SandboxPort` | `orcia_kernel/ports.py:L175` | Exécution isolée de contrôles déterministes, quel que soit le métier | 🟡 Port seul |
| Ontologie à 4 niveaux | `ontology/` | **Atout majeur pour Legal et Finance** : vocabulaire métier, synonymes, axiomes par vertical | 🟢 |
| Gabarits de documents multi-audience | `orchestration/template_compiler.py` | Livrables Markdown pour l'humain, JSON Schema pour les agents, dans n'importe quel domaine | 🟢 |
| Erreurs RFC 9457 (`OrciaDomainError`) | `orcia_kernel/errors.py:L155` | Enveloppe d'erreur uniforme et traduite | 🟢 Côté HTTP seulement (voir §3.1) |
| Passthrough et coffre chiffré par utilisateur | `permissions/crypto.py:L121` (`PassthroughVaultCipher`, AES-256-GCM) | Le connecteur agit avec l'identité de l'utilisateur | 🟢 |
| Contrats `import-linter` | `pyproject.toml:L72-L103` | Frontières vérifiées en CI | 🟢 |
| OpenTelemetry et `trace_id` | `observability/` | Traçabilité de bout en bout des appels | 🟡 |

### 2.3 Ce qui empêche d'ajouter un connecteur en moins d'une demi-journée
1. Aucun **port de connecteur** avec un contrat comportemental (récupération, action, santé, capacités, correspondance des erreurs).
2. Schémas en **listes fermées**, recopiées et figées en base (§1.3).
3. Registre de plugins **qui ne sert qu'à décrire** les connecteurs, sans être branché.
4. **Types d'étape fermés** : impossible d'ajouter un type `HTTP_ACTION` ou `HUMAN_TASK` par plugin.
5. Pas de **classement des erreurs**, ni de mécanisme de relance commun (§3.1).
6. Le circuit de demande d'accès est **branché sur Jira**.
7. Pas de **kit de test de conformité** à fournir aux auteurs de connecteurs.

---

## 3. Questions transverses

### 3.1 Erreurs et relances : distinguer une panne passagère d'une erreur métier

**Ce que fait le code aujourd'hui : rien ne les distingue.**
- `orcia_kernel/errors.py` ne définit que des erreurs **métier ou HTTP** (`ValidationDomainError`, `ScopeAccessDeniedError`…). Il n'existe aucune classe `Transient…`, ni notion de `retry_after` ou de « erreur rejouable ».
- `bootstrap/_internal/litellm_adapter.py:L82`, `L91` : `raise_for_status()` laisse remonter l'erreur brute de `httpx`. Une réponse 429 ou un dépassement de délai n'est pas reconnu comme tel.
- `_internal/dbos_engine.py:L231` : `@DBOS.step()` est utilisé **sans paramètre de relance**. Le champ `max_agent_retries` existe (`L144`) mais n'est relié à aucun mécanisme.
- Chaque connecteur devrait donc réécrire sa propre logique de relance, exactement ce que l'audit veut éviter.

**Recommandation** :
1. Dans `orcia_kernel`, une **taxonomie d'erreurs commune** :
   - `TransientInfraError(retry_after_s: float | None)`, avec les sous-classes `RateLimitedError` et `UpstreamTimeoutError` ;
   - `FunctionalConnectorError(code, retriable=False)` ;
   - `PolicyDeniedError` (pour le Permission Broker) ;
   - `PermanentInfraError`.
2. Un **`ConnectorInvoker` commun**, exécuté comme une étape durable DBOS. Il gère à lui seul :
   - les relances sur les seules erreurs `TransientInfraError` (backoff exponentiel avec aléa, respect de `Retry-After`) ;
   - la clé d'idempotence `(run_id, step_key, attempt)` ;
   - un **coupe-circuit par connecteur** ;
   - un budget de relances relié à AD-12 ;
   - le passage en `FAILED`, puis en arbitrage humain ou en replis, en cas d'erreur `FunctionalConnectorError`.
3. Le connecteur se contente de **convertir** ses exceptions (HTTP 429, 503, codes métier SAP) vers cette taxonomie, en 20 à 40 lignes. Les tests de conformité vérifient cette conversion.

### 3.2 Secrets : séparés des descripteurs de processus, et sans fuite dans l'audit ?

| Aspect | État | Preuve |
|---|---|---|
| Secrets lus depuis des fichiers (`_FILE`) | ✅ | `config.py:L81-L94` |
| Identifiants utilisateur chiffrés (AES-256-GCM, clé dérivée par utilisateur) | ✅ | `permissions/crypto.py:L121-L160` |
| Secret de webhook passé **par référence** (`*_vault_ref`) | ✅ | `orchestration/models.py:L264` |
| Valeur de secret **écrite en dur** comme valeur par défaut | ❌ | `bootstrap/_internal/litellm_adapter.py:L31` (`api_key="sk-orcia-local"`) |
| Type `SecretRef` et `SecretProviderPort` (Vault, KMS) | ❌ Absent | L'`action_item` `SEC-03` est encore ouvert |
| Masquage des secrets dans les logs (structlog) | ❌ Aucun processeur de masquage | `observability/logging.py:L153-L157` |
| Contrôle du contenu de l'outbox et de l'audit (liste blanche de champs) | ❌ `payload_jsonb` libre | `0012_story_3_2c_domain_events_outbox.py` |
| Tables système DBOS | ⚠️ DBOS **conserve les arguments et les résultats des étapes et workflows** dans ses tables système. Un secret passé en argument d'une étape y resterait, sans contrôle. Ce ne sont pas les tables d'audit en ajout seul d'ORCIA, mais elles sont tout aussi persistantes. | `_internal/dbos_engine.py:L254-L262` (`run_id`, `steps` en argument) |
| Pseudonymisation des données personnelles (`PiiReversibleScrubber`) | ⏳ Prévue en Story 4.2, absente du code | — |
| mTLS des connecteurs | ❌ Non prévu | — |

**Réponse** : la séparation est **partielle**. Les descripteurs YAML ne contiennent pas de secrets en clair (références `vault_ref`), mais **rien ne garantit techniquement** qu'aucun secret ne fuite.

**Recommandation** :
1. Un type `SecretRef` dans `orcia_kernel`, **non sérialisable** (`__repr__` masqué, `__reduce__` interdit), et un port `SecretProviderPort` (Vault, Infisical ou KMS ; certificats mTLS fournis en mémoire).
2. Règle : **seules des `SecretRef` circulent entre les étapes**. Le secret est résolu à l'intérieur du `ConnectorInvoker`, au moment de l'appel, et jamais renvoyé.
3. Un processeur structlog de masquage, plus une **liste blanche de champs** (schéma Pydantic par `event_type`) pour l'outbox et `audit_ledger`.
4. Un **test « secret témoin »** en CI : injecter une valeur témoin, exécuter un run, puis vérifier qu'on ne la retrouve dans aucune table (`dbos.*`, `audit_ledger`, `domain_events_outbox`, `step_executions`) ni dans aucun log.
5. Supprimer la valeur par défaut écrite en dur dans `LiteLLMAdapter`.

### 3.3 Mémoire et contexte : dépendance au Markdown local ou non ?

- **« Sanctum » n'existe pas dans le code**, et aucune hydratation au réveil ne s'appuie sur des fichiers locaux.
- **Hydratation actuelle** : `JitStepHydrator` (`orchestration/engine.py:L34-L95`) remplit `resolved_inputs` à partir des **snapshots JSON du Blackboard** (`artifact_payload`, `content_type="application/json"`, `blackboard/store.py:L83`) et collecte les URIs déclarées. Le contexte persistant est donc **du JSON en base**, pas du Markdown.
- **Le Markdown n'apparaît qu'à deux endroits** : l'import de packs BMAD (`catalog/bmad_adapter.py:L84-L125`) et les gabarits. Les deux sont acceptables, à condition de sortir BMAD du Core (§4).
- **Limites** :
  - pas de `ContextSourcePort` : les URIs sont **collectées, mais leur contenu n'est pas récupéré** ;
  - un PDF ne peut entrer que par l'indexation RAG (Docling, côté worker), pas comme entrée directe d'une étape ;
  - le seul stockage vectoriel est pgvector, sans port permettant de le remplacer ;
  - les régimes d'indexation sont fermés et orientés SDLC (L9).

**Recommandation** : un `ContextSourcePort` (`fetch(uri) -> ContextItem{content_type, cas_sha256, text|bytes|json, metadata}`), relié au registre de connecteurs, avec trois implémentations JSON, CAS et document, et un `VectorStorePort` (pgvector par défaut). Les régimes d'indexation deviennent des plugins (`orcia.indexers`).

### 3.4 Concurrence : deux processus sur la même ressource

- **DBOS ne fournit pas de verrou de ressource entre workflows.** Ce qu'il garantit :
  - une exécution unique par identifiant de workflow ;
  - des étapes rejouables avec mémorisation de leur résultat ;
  - des files avec limite de concurrence.

  La question « comment les verrous DBOS évitent-ils les interblocages » part donc d'un postulat faux.
- **Dans le code aujourd'hui** :
  - ✅ le relais de l'outbox utilise `FOR UPDATE SKIP LOCKED`, sans interblocage ni goulot (`_internal/outbox_repository.py:L86`) ;
  - ⚠️ les seuls autres verrous sont des `threading.Lock` **en mémoire** (`catalog/cas_resolver.py:L117`, `L143`, `L189`), inopérants entre plusieurs processus ;
  - ❌ aucun mécanisme pour une **ressource partagée** (un même ticket Jira, une même facture, un quota d'API, un « agent partagé ») ;
  - ❌ le verrou de prise en charge (AD-4) n'est pas encore implémenté (Story 5.1) ;
  - ⚠️ des risques d'interblocage logique existent par construction : un workflow parent qui attend (`DBOS.recv`) un enfant qui attend le parent, ou des sous-workflows imbriqués qui se disputent une ressource.
- **Un « agent partagé » n'a pas d'état** : il n'y a pas d'exclusion à gérer, seulement une **limite de débit et de quota**.

**Recommandation** :
1. Un `ResourceLeasePort` adossé à PostgreSQL : une table `resource_leases(resource_key, holder_run_id, fencing_token, expires_at)` avec bail à durée limitée et **jeton de fencing** vérifié par le connecteur au moment de l'écriture. Ne **jamais** garder un verrou PostgreSQL pendant une pause humaine ou entre deux étapes (au besoin, `pg_advisory_xact_lock` dans une transaction courte uniquement).
2. Des **files DBOS par classe de ressource** (`concurrency` et limiteur de débit) pour sérialiser ou plafonner, sans goulot global.
3. Des **règles contre les interblocages** :
   - acquisition des ressources dans un ordre canonique (tri des `resource_key`) ;
   - délai d'expiration sur chaque `recv` et chaque bail ;
   - interdiction des attentes cycliques entre un parent et ses enfants (vérifiée par le validateur) ;
   - surveillance des runs bloqués au-delà d'une durée donnée.
4. Un quota par connecteur et par workspace dans le `ConnectorInvoker`, relié aux coupe-circuits FinOps d'AD-12.

---

## 4. Risques de couplage et plan de refactorisation

### 4.1 Matrice des risques

| ID | Risque | Probabilité | Impact | Criticité |
|---|---|---|---|---|
| K1 | Vocabulaire SDLC dans le kernel, le modèle, le validateur et le moteur (L1 à L6) | Certaine | Élevé : bloque les verticaux hors IT | 🔴 |
| K2 | Schémas fermés recopiés en 5 endroits du code et dans 4 contraintes de base | Certaine | Élevé : coût et risque à chaque connecteur | 🔴 |
| K3 | Aucune exécution réelle des étapes ; deux moteurs ; étape DBOS figée ; API privée DBOS ; état global | Certaine | Critique : la plateforme n'exécute rien de réel | 🔴 |
| K4 | Pas de taxonomie d'erreurs ni de relance commune | Élevée | Élevé : relances incohérentes, coûts | 🔴 |
| K5 | Secrets : pas de `SecretRef`, pas de masquage, persistance DBOS non contrôlée | Moyenne | Critique : conformité, fuite | 🟠 |
| K6 | BMAD, Jira (broker) et RAG orienté code embarqués dans le Core | Certaine | Moyen | 🟠 |
| K7 | Pas de bail ni de fencing sur les ressources partagées | Moyenne | Élevé : écritures concurrentes | 🟠 |
| K8 | Pas de `ContextSourcePort` ni de `VectorStorePort` | Moyenne | Moyen | 🟡 |
| K9 | Données de démonstration dans les `__init__` et `seeds` des domaines | Certaine | Faible à moyen | 🟡 |

### 4.2 Plan d'action par priorité

| Priorité | Action | Résout | Effort | Critère de sortie vérifiable |
|---|---|---|---|---|
| **P0-1** | **Sortir le pack SDLC** dans `packages/orcia-pack-sdlc` : `writes_code` et équivalents deviennent des `tags` ou `policies` d'étape génériques ; la règle FR-13 devient un plugin `orcia.workflow_policies` ; `WorkflowEngineeringMode` est supprimé du Core ; les marqueurs du memlog deviennent des **chaînes avec espace de noms** (`sdlc.bug_code_suspected`) validées par un registre ; les chaînes de démonstration du moteur sont supprimées | K1, K6 | 3 à 4 j | Nouveau contrat `import-linter` : `orcia_kernel` et `orcia_core` n'importent jamais `orcia_pack_sdlc`. `grep -riE "writes_code\|BUG_CODE\|brownfield\|confluence\|git://" orcia_kernel orcia_core/orchestration` ne trouve rien. |
| **P0-2** | **Une interface de connecteur unique (`ConnectorPort`)** : `capabilities()`, `fetch(uri)`, `invoke(action, payload, idempotency_key)`, `health()`, `map_error(exc)` ; un registre `orcia.connectors` branché sur `FederatedUriResolver` ; schéma = chaîne validée par le registre, avec **une seule source de vérité** ; les `CHECK` en base sont remplacés par une table `connector_schemes` et une clé étrangère (migration Expand → Contract) ; kit de tests de conformité | K2 | 4 à 5 j | Un connecteur factice `sap://` ajouté **sans modifier aucun fichier du Core**, en moins de 150 lignes, et qui passe le kit de conformité |
| **P0-3** | **Exécution réelle** : registre d'exécuteurs d'étape `orcia.step_executors` (`AGENT`, `SKILL`, `SUB_WORKFLOW`, `HUMAN_TASK`, `HTTP_ACTION`) ; l'étape DBOS appelle l'exécuteur ; suppression du moteur simulé ; suppression de `_ACTIVE_ENGINE` et de `DBOS._recover_pending_workflows()` (assemblage par injection et configuration DBOS) ; branchement dans `dependencies.py` | K3 | 4 à 5 j | Run réel de bout en bout via l'API, reprise après redémarrage, 0 contenu simulé |
| **P0-4** | **Taxonomie d'erreurs et `ConnectorInvoker`** : relances sur erreurs passagères seulement, `Retry-After`, coupe-circuit, idempotence, budget AD-12 | K4 | 2 j | Tests : 429 → relances puis succès ; erreur fonctionnelle → 0 relance et arbitrage ; coupe-circuit ouvert après N échecs |
| **P1-1** | **Secrets** : `SecretRef` non sérialisable, `SecretProviderPort` (SEC-03), masquage structlog, liste blanche pour l'outbox et l'audit, **test du secret témoin**, suppression de la valeur par défaut écrite en dur | K5 | 2 à 3 j | Le secret témoin n'apparaît dans aucune table ni aucun log |
| **P1-2** | **Circuit de demande d'accès** : `AccessRequestChannelPort` (Jira devient un adaptateur, avec ServiceNow et e-mail en option) ; colonne `jira_request_url` remplacée par `request_url` générique (migration Expand → Contract) | K6 | 1 à 2 j | Broker testé avec un canal factice, sans Jira |
| **P1-3** | **Baux de ressources** : `ResourceLeasePort` (bail PostgreSQL et fencing), files DBOS par classe de ressource, ordre d'acquisition canonique, délais d'expiration, détection des attentes cycliques parent-enfant | K7 | 2 à 3 j | Test de concurrence (2 workflows sur la même ressource) : 0 interblocage, 0 écriture concurrente |
| **P1-4** | **Contexte générique** : `ContextSourcePort` (JSON, CAS, document) et `VectorStorePort` ; régimes d'indexation en plugins `orcia.indexers` (les régimes code et Jira passent dans le pack SDLC) | K8, K6 | 2 à 3 j | Une étape reçoit un PDF et un JSON comme entrées typées |
| **P2-1** | **Données de démonstration** : `rag/__init__` et `orchestration/seeds.py` déplacés vers `bootstrap` (amorçage) ou vers les fixtures de test | K9 | 0,5 j | Aucune donnée de démonstration dans les packages de domaine |
| **P2-2** | **Preuve sur un vertical** : workflow « Rapprochement de factures » (Finance) avec un connecteur factice ERP, exécuté en CI **avec le pack SDLC désinstallé** | Tous | 1 à 2 j | Job CI `core-without-sdlc` au vert |

### 4.3 Où placer ce travail dans le plan
- **P0-1 à P0-4** doivent passer **avant la Story 3.3** (Assistant) et avant l'Epic 7 (autonomie). Ce sont les fondations de toutes les fonctionnalités à venir. Proposition : une story intercalaire **`3.2e` « Séparation Core et pack SDLC, interface de connecteur unique, exécution réelle des étapes »**. `3.2c` (outbox) est déjà en place.
- **P1-x** : en `action_items`, à rattacher à `4.1` et `4.2` (sandbox, PII), `5.1` (prise en charge et verrous) et `SEC-03`.
- **P2-2** devient le **critère d'acceptation de l'Epic 3** : sans lui, le positionnement « plateforme agnostique » n'est pas démontré.

> [!IMPORTANT]
> En l'état, ORCIA est une **plateforme SDLC dotée de bonnes fondations génériques** (kernel sain, outbox, stockage par empreinte, ontologie, épinglage des versions), **pas encore une plateforme agnostique**. Les quatre actions P0 suffisent à basculer, pour environ 13 à 16 jours de travail. Plus on attend, plus le coût augmente : chaque nouvelle story (3.3, 4.x) ajoute des dépendances vers les champs SDLC et les listes fermées.
