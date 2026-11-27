## Epic 8: Hub de Paramétrage Post-Jour 0 (`/settings/*`), Gouvernance d'Entreprise à 6 Verbes (`RBAC/ABAC`), Routage Cognitif Abstrait (`simple|medium|complex|auto` & Effort), Studio Visuel Avancé (`Couches`, `Contrat`, `Pré-prompt`) & Wizards d'Initialisation Durables

Permettre aux Administrateurs Plateforme (`Karim UJ-9`), Ingénieurs SecOps (`Sophie UJ-6`), Directeurs de BU (`Claire UJ-8`) et Chefs d'Équipe / Tech Leads (`Marc UJ-5`, `Yanis UJ-3`) d'administrer ORCIA après le Jour 0 sans redéploiement via le **Hub de Paramétrage (`/settings/{iam,connectors,ai-models,packs,workflows,audit}`)** protégé par concurrence optimiste (`ETag`/`If-Match` `412`) et contrat de secret en écriture seule (`SecretInput`/`SecretStatus`), d'appliquer un modèle d'habilitations hiérarchique **RBAC/ABAC à 6 verbes (`create, read, update, delete, execute, grant`)** distinguant l'utilisation (`execute`) de la lecture des secrets (`read`) avec délégation bornée (`grant`), d'abstraire les modèles LLM en **Tiers Cognitifs (`simple €, medium €€, complex €€€, auto ⚡`)** et **niveaux d'Effort** avec escalade déterministe rejouable sous DBOS, d'enrichir le **Studio Visuel de Workflows** (5 onglets de cycle de vie, immutabilité des versions publiées, `Pré-prompt IA`, `Contrat du workflow`, `Déclencheurs`, `▷ Tester`, inspecteur **`COUCHES · N`** et moindre privilège connecteur par étape), et d'embarquer toute nouvelle équipe sans page blanche grâce à **3 Wizards d'Initialisation Durables DBOS (`/wizards/*`)**.

### Story 8.1: Modèle d'Habilitations Hiérarchique RBAC/ABAC à 6 Verbes (`create, read, update, delete, execute, grant`), Délégation Bornée & Invariants Anti-Verrouillage

As a Ingénieur SecOps, Administrateur Plateforme ou Chef d'Équipe (`Sophie UJ-6`, `Karim UJ-9`, `Marc UJ-5`),
I want évaluer toutes les permissions selon une matrice hiérarchique à 6 verbes atomiques (`create, read, update, delete, execute, grant`) sur l'arbre `Organisation -> BU -> Équipe -> Workspace -> Pack -> Ressource -> Action`, permettre à un `TEAM_LEAD` titulaire du verbe `grant` de déléguer localement un sous-ensemble de ses droits sans escalade de privilèges, et empêcher tout verrouillage administratif accidentel,
So that un contributeur ou un agent puisse exécuter (`execute`) un connecteur, un modèle IA ou un workflow sans jamais lire (`read`) ses secrets, que les ressources non autorisées restent découvrables passivement (`🔒 Non habilité` + demande d'accès), et que le dernier administrateur ou IdP ne puisse jamais être désactivé (`FR-27`, `AD-6`, `AD-19`, `AD-21`, `NFR-SEC-3`).

**Acceptance Criteria:**

**Given** la migration Alembic créant/étendant les tables d'habilitations hiérarchiques (`role_permission_grants` avec `scope_path`, `verb IN ('create','read','update','delete','execute','grant')`, ainsi que les colonnes préparatoires `effect DEFAULT 'ALLOW'`, `inheritance_block DEFAULT FALSE`, `conditions_jsonb DEFAULT '{}'` et `hidden_when_unauthorized DEFAULT FALSE` pour `ACTION_ITEM-8.1..8.3`)
**When** le *Permission Broker* (`packages/orcia-core/permissions`) évalue une requête d'accès ou d'exécution sur une ressource
**Then** un sujet disposant de `execute` sans `read` peut invoquer la ressource via `ConnectorInvoker` / `LLMPort` mais se voit refuser (`HTTP 403`) tout accès en lecture aux paramètres secrets ou à la configuration détaillée
**And** si le sujet ne dispose ni de `read` ni de `execute`, l'API retourne les métadonnées publiques de découverte passive (`locked: true`, `reason: "MISSING_PERMISSION"`, bouton *Demander l'accès* émettant `AccessRequested` dans `domain_events_outbox`), sauf si `hidden_when_unauthorized: true` auquel cas l'API retourne `HTTP 404` (`AD-21`).

**Given** un responsable local (`TEAM_LEAD` ou `BU_DIRECTOR`) disposant du verbe `grant` sur son périmètre ou un administrateur modifiant les accès dans `/settings/iam`
**When** il délègue un rôle/droit à un membre ou Service Principal **OU** tente de retirer le dernier `PLATFORM_ADMIN` actif / désactiver la dernière méthode d'authentification active
**Then** le moteur vérifie l'invariant de confinement $\text{Droits délégués} \subseteq \text{Droits détenus}$ (rejetant toute escalade avec `HTTP 403 ERR_GRANT_ESCALATION_FORBIDDEN`), rejette toute tentative de verrouillage avec `HTTP 422 ERR_ADMIN_LOCKOUT_PREVENTED`, et publie chaque octroi/révocation dans `domain_events_outbox` (`PermissionGranted`, `PermissionRevoked`, `SettingsChanged`) consommé par `audit_ledger`
**And** toute révocation de Service Principal ou de droit `execute` prend effet au plus tard à la **prochaine frontière de `@DBOS.step`** des runs en cours (`AD-21`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest` + `hypothesis` sur l'arbre d'héritage et l'invariant de confinement `grant`) et d'intégration (`testcontainers` PG18) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

### Story 8.2: Abstraction Cognitive des Modèles LLM (`simple, medium, complex, auto`), Niveaux d'Effort (`default, fast, balanced, deep`), Budgets Hiérarchiques & Escalade Déterministe DBOS (`PROC-01`)

As a Architecte IA, Directrice de BU ou Concepteur de Workflow (`Karim UJ-9`, `Claire UJ-8`, `Yanis UJ-3`),
I want que les étapes de workflows référencent exclusivement des tiers cognitifs abstraits (`simple €, medium €€, complex €€€, auto ⚡`) et des niveaux d'effort (`default, fast, balanced, deep`) mappés par Workspace dans `/settings/ai-models` vers les fournisseurs/modèles physiques LiteLLM, avec escalade automatique déterministe en mode `auto` et protection `HTTP 409` des modèles épinglés par des runs actifs,
So that nous puissions changer de modèle ou de fournisseur IA à chaud sans éditer aucun workflow, optimiser automatiquement les coûts FinOps via le tier `auto` sans briser le déterminisme du rejeu DBOS, et respecter l'Orthogonalité des Modèles (`FR-19`, `FR-24`, `AD-10`, `AD-12`, `AD-19`, `AD-21`, `PROC-01`).

**Acceptance Criteria:**

**Given** la migration Alembic créant `workspace_llm_tier_mappings` (associant par `scope_id` chaque `InferenceTier: simple | medium | complex | auto` et niveau d'`effort: default | fast | balanced | deep` à un fournisseur/modèle `LiteLLM`, un `secret_ref`, des paramètres d'inférence, un budget de tokens et un ordre de fallback) et la table `inference_attempts`
**When** un `@DBOS.step` exécute un appel LLM avec `inference_tier: auto` (ou un tier explicite, défaut `medium`)
**Then** le routeur cognitif résout le mapping actif du Workspace, vérifie que l'invariant d'**Orthogonalité des Modèles (`AD-10`)** entre Agent Exécuteur et Agent Évaluateur est respecté, démarre en mode `auto` sur le tier `simple` et, uniquement si la *Gate Déterministe* (schéma JSON/Pydantic ou assertion Sandbox) échoue, escalade vers `medium` puis `complex` en enregistrant chaque tentative comme sous-étape idempotente dans `inference_attempts` (garantissant qu'un rejeu DBOS après crash ne ré-exécute pas les paliers déjà tentés) (`AD-21`).

**Given** un administrateur dans `/settings/ai-models` qui modifie un plafond budgétaire hiérarchique (`GLOBAL -> BU -> TEAM -> WORKSPACE`) ou tente de supprimer un modèle physique actuellement épinglé dans le `run-lock.json` d'un *Workflow Run* actif
**When** la requête est soumise à l'API
**Then** tout abaissement de budget s'applique immédiatement au **prochain appel LLM coûteux** sans faire échouer rétroactivement les étapes déjà validées, tandis que la suppression d'un modèle épinglé est refusée avec `HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` exposant la liste des runs actifs et les options explicites **Drainer** (bloquer les nouveaux runs) ou **Forcer** (`PLATFORM_ADMIN` uniquement)
**And** conformément à **`PROC-01`**, un *Workflow Run* réel de bout en bout traverse l'API (`instanciation -> exécution avec tier auto -> pause -> redémarrage -> reprise`) avec `0` contenu simulé et $\ge 90\%$ de couverture (`AD-17`, `AD-19`, `AD-21`).

### Story 8.3: Socle Settings Versionnés (`platform_settings`, `ETag`/`If-Match` `412`), Contrat Secret Write-Only (`SecretInput`/`SecretStatus`), Coquille `/settings/*`, Primitives `<PermissionGuard>` / `<SecretField>` & Console Rejeu Outbox

As a Administrateur Plateforme ou Ingénieur SecOps (`Karim UJ-9`, `Sophie UJ-6`),
I want disposer du socle relationnel versionné `platform_settings` protégé par `ETag`/`If-Match` (`HTTP 412`), du contrat de secret en écriture seule (`SecretInput`/`SecretStatus`) couplé au composant `<SecretField />`, de la coquille `/settings/{iam,connectors,ai-models,packs,workflows,audit}` gardée par `<PermissionGuard />`, et d'une console `/settings/audit` permettant le rejeu borné (`--dry-run`) des événements Outbox,
So that tout paramétrage post-Jour 0 soit versionné sans conflit d'édition concurrente, qu'aucun secret ne puisse jamais fuiter ni être écrasé par son masque visuel, et que le backlog Outbox soit gouvernable en toute sécurité (`AD-6`, `AD-12`, `AD-19`, `AD-21`, `NFR-SEC-4`).

**Acceptance Criteria:**

**Given** la migration Alembic créant `platform_settings` (`id` UUIDv7, `scope_level`, `scope_id`, `category`, `key`, `value_jsonb` sans secret, `secret_ref` UUIDv7 nullable, `version`, `etag`, `updated_at`, `updated_by`) et les schémas Pydantic v2 `SecretInput` (`action: "keep" | "set" | "clear"`) et `SecretStatus` (`configured`, `fingerprint: "sha256:<8-hex salé par resource_id>"`, `updated_at`, `updated_by`) dans `apps/api/src/orcia_api/schemas/settings.py`
**When** un client appelle `PATCH /api/v1/settings/...`
**Then** l'API exige l'en-tête `If-Match` (`HTTP 428 ERR_PRECONDITION_REQUIRED` si absent, `HTTP 412 ERR_SETTINGS_VERSION_CONFLICT` si périmé), rejette tout `READ_ONLY_OBSERVER` avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`, applique `SecretInput` via `SecretProviderPort` sans jamais retourner la valeur du secret, et émet exactement un événement `SettingsChanged` dans `domain_events_outbox`
**And** le **test du secret témoin (`DEC-SEC-01`)** prouve que la valeur secrète n'apparaît dans aucune réponse API, aucun log `structlog`, ni dans `platform_settings`, `domain_events_outbox`, `audit_ledger`, `step_executions` ou `dbos.*` (`NFR-SEC-4`, `AD-21`).

**Given** l'arborescence TanStack Router `/settings/{iam,connectors,ai-models,packs,workflows,audit}` et les composants `@orcia/ui` **`<PermissionGuard />`** et **`<SecretField />`**
**When** un utilisateur consulte `/settings/*` ou déclenche un rejeu depuis `/settings/audit` (`POST /api/v1/admin/outbox/replays`)
**Then** chaque route vérifie les permissions en `beforeLoad`, `<SecretField />` affiche uniquement l'empreinte `sha256` et les actions *Remplacer* / *Effacer* (sans jamais pré-remplir `••••••••`), et l'endpoint de rejeu Outbox borne le lot à $\le 500$ événements, cible un consommateur déclaré idempotent et s'exécute en mode `dry_run: true` par défaut
**And** `lint-imports` passe à `0` violation, le SDK OpenAPI `@orcia/api-client` est régénéré à `0-diff`, et les tests unitaires (`pytest`, `Vitest`), de contrat (`schemathesis`) et d'intégration (`testcontainers` PG18) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`, `AD-21`).

### Story 8.4: Hub des Connecteurs (`/settings/connectors`), Test de Connexion Fail-Fast DBOS, Garde-fous d'Ingestion (`C0–C3`, Arbitrage PII, Linter OCR `0 char`) & Test de Réciprocité RAG

As a Chef d'Équipe, Responsable Produit ou Ingénieur SecOps (`Marc UJ-5`, `Hélène UJ-1`, `Sophie UJ-6`),
I want administrer dans `/settings/connectors` les instances de sources de données par périmètre avec test de connectivité fail-fast DBOS, imposer à l'ingestion documentaire la classification `C0–C2` vs `C3`, la détection automatique de PII avec modale d'arbitrage humain, le rejet immédiat des PDF scannés vides (`0 char`), et vérifier en 1 clic la réciprocité RAG avec citation obligatoire,
So that aucune source mal configurée, aucun document `C3` non autorisé, aucune donnée personnelle non arbitrée ni aucune coquille PDF vide ne pollue le Graphe Tripartite ou les prompts des agents (`FR-10`, `FR-16`, `FR-17`, `AD-5`, `AD-8`, `AD-10`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** l'écran `/settings/connectors` (accompagné du `<GuidanceDrawer />` en 5 étapes) et un connecteur enregistré dans `orcia.connectors` (`git://`, `jira://`, `confluence://`, `db://`, `nexus://`, `s3://`, `mcp://`)
**When** un utilisateur habilité crée ou met à jour une instance dans `workspace_datasources` via `<SecretField />` et clique sur **`Tester la connexion`** (`POST /api/v1/settings/connectors/{id}/test-connection`)
**Then** un `@DBOS.step` de healthcheck à timeout court (`< 5 s`) vérifie l'authentification et la portée réelle auprès du système cible, persiste le statut (`HEALTHY` / `DEGRADED` / `UNREACHABLE`) et retourne un diagnostic RFC 9457 actionnable en cas d'échec (`AD-21`).

**Given** un utilisateur qui téléverse ou synchronise un document dans une source RAG du Workspace
**When** le pipeline d'ingestion pré-analyse le fichier
**Then** :
1. **Classification de sécurité obligatoire** : l'utilisateur doit qualifier la source en `C0–C2 (Interne / Standard)` ou `C3 (Confidentiel Restreint — exigeant un Workspace habilité C3)` ;
2. **Linter anti-coquille vide (`0 char` OCR fail-fast)** : tout PDF scanné ou document dont l'extraction texte produit `0` caractère exploitable est rejeté immédiatement avec l'erreur `HTTP 422 ERR_EMPTY_OR_UNREADABLE_DOCUMENT` avant toute vectorisation ;
3. **Garde-fou PII avec Arbitrage Humain** : si le scanner détecte des données personnelles (emails, nir, téléphones, IBAN), l'indexation se met en pause et affiche une modale d'arbitrage humain proposant **3 choix explicites** : *Pseudonymiser avant indexation* (via `PiiReversibleScrubber`), *Indexer tel quel (dérogation auditée dans `audit_ledger`)* ou *Annuler l'import* ;
4. **Test de Réciprocité RAG en 1 clic (*« Vérifier qu'il répond »*)** : une fois indexé, un bouton déclenche une micro-requête de contrôle sur le document et vérifie que l'agent restitue une réponse citant explicitement l'URI et le chunk du document (`AD-8`, `AD-21`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + SeaweedFS) couvrent $\ge 90\%$ du module (`AD-17`, `AD-19`).

### Story 8.5: Studio Visuel de Workflows Enrichi (5 Onglets de Cycle de Vie, Barre de Gouvernance `Pré-prompt`/`Contrat`/`Déclencheurs`/`Tester`, Inspecteur `COUCHES · N`, Moindre Privilège Connecteur) & Registre des Packs (`/settings/packs`)

As a Architecte, Tech Lead ou Product Manager (`Antoine UJ-2`, `Yanis UJ-3`, `Hélène UJ-1`),
I want gérer mes workflows dans un Studio structuré en 5 onglets de cycle de vie (`Publiés`, `Brouillons`, `Corbeille`, `Exécutions actives`, `Suspendus en arbitrage`) où toute édition d'une version publiée crée automatiquement une branche brouillon (`vX.Y.Z-draft`), configurer en barre supérieure le `Pré-prompt IA`, le `Contrat du workflow` (paramètres typés `p_1..p_n` + sections Markdown obligatoires), les `Déclencheurs` et le bac à sable `▷ Tester`, inspecter et désactiver à la volée les sous-couches d'une macro-étape via le popover **`COUCHES · N`**, borner chaque connecteur en `Lire` vs `Écrire` par étape, et activer les Packs Métier par périmètre dans `/settings/packs`,
So that le Workflow Studio offre une gouvernance industrielle complète de la conception jusqu'au test à blanc (*What-If*) sans jamais compromettre l'immutabilité des versions en production (`FR-1`, `FR-11`, `FR-14`, `FR-26`, `FR-30`, `AD-2`, `AD-5`, `AD-18`, `AD-19`, `AD-20`, `AD-21`).

**Acceptance Criteria:**

**Given** le Hub des Workflows (`/studio` et `/settings/workflows`) structuré en **5 onglets avec compteurs temps réel** (`Publiés`, `Brouillons`, `Corbeille`, `Exécutions actives`, `Suspendus en arbitrage`)
**When** un utilisateur clique sur **`Modifier`** sur un workflow à l'état `PUBLISHED` (ex. `v1.0.0`)
**Then** la version `v1.0.0` reste strictement immuable pour les `run-lock.json` existants et le système crée automatiquement une révision `v1.1.0-draft` éditable dans le Canvas `@xyflow/react` (`AD-14`, `AD-21`).

**Given** un workflow ouvert dans l'éditeur visuel `/studio/$workflowId`
**When** le concepteur utilise la **Barre Supérieure de Gouvernance (`<WorkflowTopGovernanceBar />`)**, les nœuds du graphe et le popover **`<LayersInspectorPopover />` (`COUCHES · N`)**
**Then** :
1. **`Pré-prompt IA`** : permet d'éditer les instructions système globales du workflow, épinglées par empreinte `SHA-256` dans `run-lock.json` ;
2. **`Contrat du workflow`** : définit les paramètres d'entrée typés (`p_1..p_n`, liés aux concepts de l'Ontologie) et la liste des sections Markdown obligatoires attendues en sortie (vérifiées automatiquement par une *Gate Déterministe* de structure) ;
3. **`▷ Tester` (Dry-Run *What-If*)** : génère dynamiquement un formulaire de test à partir du `Contrat du workflow` et lance une exécution en mode simulation isolée sans écriture externe ;
4. **Distinction bimodale & Moindre Privilège par étape** : chaque nœud distingue visuellement un `Program Executor` (déterministe) d'un `Agent Executor` (sélecteurs de `InferenceTier` et d'`Effort`), affiche les Gates sur les arêtes, et borne chaque connecteur attaché à l'étape au mode **`Lire` (`READ_ONLY`)** ou **`Écrire` (`READ_WRITE_STAGED`)** ;
5. **Inspecteur `COUCHES · N` sur les macro-étapes (`SUB_WORKFLOW`)** : affiche les sous-couches regroupées en 3 zones (*1. Entrées & Contexte*, *2. Capacités & Raisonnement*, *3. Livrables & Pré-Gates*), permet de réordonner, supprimer ou basculer l'icône œil `👁️` (`enabled: false`), ce qui marque la sous-étape `SKIPPED` dans le checkpoint DBOS sans rompre le graphe (`AD-21`).

**Given** l'écran `/settings/packs` listant les Packs Métier découverts via `entry_points` (`AD-20`, ex. `orcia-pack-sdlc`)
**When** un administrateur active, configure (via le JSON Schema exposé par le pack) ou désactive un pack sur un périmètre (`GLOBAL | BU | TEAM | WORKSPACE`)
**Then** la désactivation d'un pack utilisé par des runs actifs est protégée par `HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` (*Drainer* / *Forcer*), un pack désinstallé mais référencé en base s'affiche en statut `ORPHANED` sans crash au démarrage, et les tests unitaires (`pytest`, `Vitest`), d'intégration (`testcontainers` PG18) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`, `AD-20`, `AD-21`).

### Story 8.6: Parcours d'Initialisation Guidés par Profil (3 Wizards Durables DBOS `wizard_sessions`), Espace Démo Pré-rempli (*Zero Empty-State*) & Validation Bout-en-Bout

As a Nouvel Administrateur, Tech Lead SDLC ou Manager Métier (`Karim UJ-9`, `Yanis UJ-3`, `Hélène UJ-1`),
I want être guidé lors de la création ou de la configuration d'un espace par l'un des 3 Wizards Durables DBOS adaptés à mon Profil Humain (`Tech Lead SDLC`, `Business/Ops Manager`, `Platform/SecOps Admin`) avec sauvegarde automatique de ma progression (`wizard_sessions`), test fail-fast à chaque étape et option d'Espace Démo pré-rempli (*Zero Empty-State*),
So that n'importe quelle équipe puisse configurer ses sources, ses tiers IA, ses politiques de Gates et lancer son premier Workflow Run validé en moins de 10 minutes sans jamais faire face à une page blanche ni perdre sa saisie en cas d'interruption (`FR-28`, `AD-2`, `AD-16`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** la migration Alembic créant la table `wizard_sessions` (`id` UUIDv7, `wizard_type IN ('sdlc_tech_lead', 'ops_manager', 'secops_admin')`, `user_id`, `scope_id`, `current_step_index`, `state_jsonb`, `dbos_workflow_id`, `status`) et la route `/wizards/$wizardType`
**When** un utilisateur démarre un Wizard d'initialisation, ferme son navigateur à l'étape 3 sur 5, puis se reconnecte
**Then** le workflow durable DBOS restaure exactement l'état `wizard_sessions` à l'étape 3 (en ne stockant que des `secret_ref` via `SecretProviderPort`), permet de tester en 1 clic chaque connecteur ou modèle configuré avant de passer à l'étape suivante, et exécute en étape finale une micro-requête de réciprocité RAG prouvant que l'espace est opérationnel (`AD-16`, `AD-21`).

**Given** un nouvel utilisateur qui choisit l'option **« Démarrer avec l'Espace de Démonstration Pré-rempli (*Zero Empty-State*) »**
**When** le seeder idempotent (`packages/orcia-core/bootstrap/seeder.py`) provisionne l'espace de démonstration
**Then** l'utilisateur accède immédiatement à un Workspace pré-câblé avec une ontologie de référence, un corpus documentaire indexé, un workflow publié prêt à être testé dans le Studio ou le Cockpit, et `0` secret en clair
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`), d'intégration (`testcontainers` PG18 + Redis + SeaweedFS avec test de reprise après interruption du Wizard) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`, `AD-21`).
