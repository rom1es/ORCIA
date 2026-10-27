# ORCIA : où et comment rendre le code plus modulaire

> Analyse faite sur le code du 27/10/2026 (16 stories terminées sur 39, environ 16 500 lignes de Python, logique métier stockée en mémoire).
> But : garder **une seule application** (un « monolithe modulaire »), mais dont chaque partie est vraiment séparée et peut être remplacée. **Pas de microservices.**

---

## 0. L'état actuel

### 0.1 Trois paires de modules qui s'importent mutuellement

| Cycle | Où ça se produit | Cause |
|---|---|---|
| `blackboard` ↔ `orchestration` | [blackboard/models.py:L11](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/blackboard/models.py#L11) importe `orchestration.models` ; [orchestration/engine.py:L10-L17](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/engine.py#L10-L17) importe `blackboard` | Les deux modules partagent leurs classes de données au lieu de passer par une interface |
| `catalog` ↔ `bootstrap` | [catalog/\_\_init\_\_.py:L8](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/catalog/__init__.py#L8) importe `bootstrap.seeder` ; `bootstrap/models.py` et `engine.py` importent `catalog.models` | Les **données initiales (seeds)** sont rangées dans `bootstrap`, mais d'autres modules en ont besoin |
| `permissions` ↔ `bootstrap` | [permissions/broker.py:L13](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/permissions/broker.py#L13) importe `bootstrap.permission_broker_seeds` ; `bootstrap/__init__` importe `permissions` | Même cause |

### 0.2 Code rangé au mauvais endroit
- **`schemas/` (environ 2 100 lignes)** : ce sont les formats de requête et de réponse de l'API (OpenAPI), mais ils sont dans le noyau. Ce dossier importe presque tous les modules du noyau.
- **`domain/exceptions.py` (377 lignes)** : un seul fichier d'erreurs pour tout le noyau. Chaque nouvelle erreur oblige à le modifier.
- **3 singletons créés au chargement des modules** dans `apps/api` (par exemple [orchestration.py:L39](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/orchestration.py#L39)). Conséquences : services difficiles à remplacer en test, état partagé entre requêtes, et impossibilité de brancher la vraie base de données sans modifier les routeurs.
- **Packaging** : un seul `pyproject` regroupe le noyau, l'API et le worker. Aucune frontière n'est vérifiée par un outil.

---

## 1. Les pistes de modularité

Pour chaque piste : **ce que c'est**, **ce que ça donne concrètement dans ORCIA**, les ✅ avantages, les ⚠️ inconvénients, puis un verdict.

### M1. Supprimer les imports mutuels (sens unique des dépendances)
**Ce que c'est.** Les dépendances ne vont que dans un sens. Les données initiales (`seeds`) reviennent dans leur propre module, et `bootstrap` devient un simple **module d'assemblage** que personne n'importe.

**Concrètement.**
- `catalog/seeds.py` et `permissions/seeds.py` : `bootstrap` les importe, plus l'inverse.
- `blackboard` ne connaît plus `orchestration`. Il expose ses propres types, par exemple `SnapshotRef` ou `StepKey` (des identifiants génériques), et `orchestration` le pilote via un port `BlackboardPort`.

✅ Avantages
- Modules testables seuls, plus d'erreur d'import circulaire.
- Condition nécessaire à toutes les autres pistes.
- Refactorisation courte (quelques heures à 1 jour).

⚠️ Inconvénients
- Il faut quelques types intermédiaires ou des identifiants à la place des objets partagés.
- `blackboard` touche à 2 flux sensibles (relance à partir d'une étape, versions figées) : à faire avec une analyse d'impact GitNexus et des tests de non-régression.

**Verdict : 🟢 À faire tout de suite.**

---

### M2. Un package par domaine métier
**Ce que c'est.** Chaque domaine métier devient un package `uv` distinct, avec une **API publique** explicite (`__init__.py` ou `api.py`). Tout le reste est privé (`_internal/`).

**Découpage proposé, à partir du code actuel.**

| Package | Contient | Dépend de |
|---|---|---|
| `orcia-kernel` | `domain/identifiers`, erreurs de base, types FinOps, port d'horloge | rien |
| `orcia-permissions` | authentification, RBAC/ABAC, Permission Broker | kernel |
| `orcia-catalog` | résolution des URI fédérées, cache CAS, surcharges à 4 niveaux | kernel, permissions (port) |
| `orcia-ontology` | 4 niveaux, simulation d'impact, promotion | kernel, permissions (port) |
| `orcia-rag` | indexation, RRF, graphe tripartite, contrôle de fraîcheur | kernel, ontology (port) |
| `orcia-blackboard` | snapshots en ajout seul, brouillons, versions | kernel |
| `orcia-gates` | contrôles déterministes, par IA, humains | kernel, ports LLM et sandbox |
| `orcia-orchestration` | moteur, validation YAML, run-lock, déclencheurs, sous-workflows | tous les précédents, **par leurs ports** |
| `orcia-audit-finops` | journal d'audit, coûts, coupe-circuits | kernel (abonné aux événements, voir M6) |

✅ Avantages
- Frontières **physiques** : on ne peut plus importer ce qui n'est pas déclaré.
- Responsabilités claires, plus facile pour plusieurs développeurs (ou agents IA) de travailler en parallèle.
- Tests et couverture par package, CI incrémentale (Turborepo pour le TS, filtres `uv` pour Python).
- **Prépare un éventuel découpage en services**, sans l'imposer.

⚠️ Inconvénients
- Plus de `pyproject.toml` à maintenir, et des versions internes à gérer (dans un monorepo `uv`, tout reste en `workspace = true`).
- Le risque de **découper trop fin** : 9 packages, c'est la limite haute pour une petite équipe.
- Les imports changent partout : gros diff, en concurrence avec les stories en cours.
- Le mypy strict devra résoudre plusieurs packages.

**Verdict : 🟡 Oui, mais progressivement.** Commencer avec 4 packages (`kernel`, `core-domains`, `api`, `worker`), puis séparer un domaine quand il atteint une taille ou une équipe qui le justifie.

---

### M3. Faire vérifier les frontières par l'outillage (`import-linter`)
**Ce que c'est.** Des règles d'architecture vérifiées en CI.
- **Couches** : `apps` → `orchestration` → domaines → `kernel`.
- **Indépendance** : `ontology` et `rag` ne s'importent pas entre eux sans passer par un port.
- **Interdits** : `fastapi`, `sqlalchemy`, `dramatiq`, `redis` et `litellm` sont interdits dans `domain/` et `ports/`, exactement comme le demande AGENTS.md.

✅ Avantages
- Coût quasi nul, retour immédiat.
- Applique automatiquement la règle d'AGENTS.md, qui n'est aujourd'hui vérifiée par rien.
- **Fonctionne même sans M2** : on peut l'activer tout de suite sur l'arborescence actuelle.

⚠️ Inconvénients
- Une dépendance d'outillage de plus, à inscrire dans la spine.
- Les règles doivent évoluer avec le découpage.
- Les cycles actuels feront échouer la CI tant que M1 n'est pas fait (on peut tolérer temporairement les exceptions connues).

**Verdict : 🟢 À faire tout de suite, juste après M1.**

---

### M4. Remettre chaque chose à sa place (`schemas`, erreurs)
**Concrètement.**
- `schemas/` part dans `apps/api/src/orcia_api/schemas/`. Le noyau ne doit pas connaître le format de l'API.
- `domain/exceptions.py` est éclaté : chaque domaine a son `errors.py`, et seule la classe de base `OrciaDomainError` reste dans `kernel`. La correspondance entre erreurs et réponses RFC 9457 (`error_code` → HTTP) se fait dans `apps/api`, par un registre.

✅ Avantages
- Le noyau devient réutilisable sans HTTP (worker, CLI, serveur MCP).
- On peut faire évoluer l'API sans toucher au domaine, et le SDK OpenAPI ne dépend que de `apps/api`.
- Fin du fichier d'erreurs commun que tout le monde modifie.

⚠️ Inconvénients
- Il faut écrire des conversions entre objets du domaine et objets d'API (un peu de code répétitif).
- Il faut vérifier que la génération du SDK donne toujours **0 différence**.

**Verdict : 🟢 À faire tout de suite.**

---

### M5. Un seul point d'assemblage (injection de dépendances)
**Ce que c'est.** Plus aucun `build_default_*()` exécuté au chargement d'un module. Les services sont assemblés **une seule fois** :
- dans `apps/api` : `lifespan`, puis `app.state`, puis `Depends()` ;
- dans `apps/worker` : `on_startup` du broker.

Les adaptateurs (en mémoire, SQLAlchemy, cassette, LiteLLM, sandbox locale ou distante) sont **choisis par la configuration**.

✅ Avantages
- C'est **la condition pour brancher la vraie infrastructure** (P1) sans modifier les routeurs.
- Tests isolés, sans état global.
- Même code en dev (mémoire), en CI (testcontainers) et en prod.
- Préparation directe de M10 (modules activables).

⚠️ Inconvénients
- Un peu de code d'assemblage ; il faut résister à l'envie d'ajouter un framework d'injection (`Depends` plus une fabrique suffisent).
- Les tests actuels qui comptent sur les singletons devront être adaptés.

**Verdict : 🟢 À faire tout de suite, dans la `Story 3.1a`.**

---

### M6. Communication entre domaines par événements (table outbox)
**Ce que c'est.** Au lieu de s'appeler directement, les domaines **publient des événements métier**, par exemple :
- `run.step.completed`, `gate.agentic.completed`, `ontology.term.extracted`, `trigger.fired`.

Ces événements sont écrits dans une **table outbox PostgreSQL**, dans la même transaction que le changement d'état. Un relais les distribue ensuite aux abonnés :
- `audit_finops` (journal d'audit, coûts) ;
- `ontology` (extraction des nouveaux concepts) ;
- les notifications temps réel (SSE) ;
- les déclencheurs de sous-workflows.

✅ Avantages
- **Couplage minimal** : l'orchestration ne connaît ni l'audit, ni les coûts, ni les notifications.
- Pas d'événement perdu si l'application plante entre l'écriture en base et l'envoi : c'est le rôle de l'outbox.
- **Correspond bien aux exigences de non-duplication** (`audit_ledger` sans doublon, workers Dramatiq qui relancent les tâches).
- Ajouter une fonction (une nouvelle métrique, une intégration Slack) ne demande plus de modifier le moteur.
- Les noms d'événements suivent déjà la convention SSE de la spine (`<domaine>.<entité>.<verbe_passé>`).

⚠️ Inconvénients
- **Les abonnés sont mis à jour avec un léger décalage** : l'interface ou les coûts peuvent être en retard de quelques millisecondes.
- Plus difficile à déboguer : il faut tracer par `trace_id` et `run_id` (OpenTelemetry indispensable).
- Il faut gérer l'évolution du format des événements (`event_version`).
- Une table, un relais et une supervision de plus.
- **Ne pas en abuser** : les contrôles et l'arbitrage humain restent des appels **synchrones**, car ils conditionnent la suite du run.

**Verdict : 🟡 Oui, avant l'Epic « autonomie / déclencheurs » (AD-18)**, et seulement pour les effets secondaires (audit, coûts, notifications, extraction de concepts).
> Si DBOS ou Temporal est retenu (P2), ils fournissent déjà une partie de cette mécanique : à arbitrer en même temps.

---

### M7. Points d'extension (plugins par `entry_points`)
**Ce que c'est.** Chaque type d'extension a une **interface stable** (un `Protocol`) et un **registre** alimenté par les `entry_points` Python. Un plugin est un package qu'on installe ; on n'a plus à modifier le noyau.

| Point d'extension | Interface | Exemples |
|---|---|---|
| Connecteurs d'URI | `UriResolverPlugin` | `git://`, `jira://`, `confluence://`, plus tard `sharepoint://`, `gdrive://` (lots 2 et 3) |
| Adaptateurs LLM | `LlmGatewayPort` (existe déjà) | LiteLLM, cassette, SDK direct, modèle souverain |
| Grilles de lecture des contrôles par IA | `EvaluationLensPlugin` | `fact_verification`, sécurité, conformité métier |
| Sandboxes | `SandboxRuntimePort` | WASM, conteneur isolé, binaire Rust |
| Déclencheurs | `TriggerSourcePlugin` | webhook Jira/Git, cron, puits de logs |
| Types d'étape | `StepExecutorPlugin` | `agent`, `skill`, `sub_workflow`, `human_task` |
| Indexeurs RAG | `IndexerPlugin` | Docling, AST tree-sitter, schéma de base |

✅ Avantages
- **Correspond au positionnement « catalogue fédéré »** d'ORCIA.
- Les lots 2 et 3 (nouveaux connecteurs) n'ont plus besoin de modifier le noyau.
- Des équipes clientes peuvent écrire leurs propres connecteurs.
- Chaque plugin est testé seul avec des **tests de contrat** communs.
- Permet un déploiement à la carte (sans Docling, par exemple).

⚠️ Inconvénients
- **Les interfaces publiques deviennent un engagement** : versionnement, compatibilité, dépréciations.
- Surface de sécurité : un plugin s'exécute dans le processus (à réserver aux plugins de confiance, signés et listés explicitement).
- Le chargement dynamique gêne un peu l'analyse statique (mypy, GitNexus voit moins bien les appels).
- Risque de figer trop tôt une interface encore instable.

**Verdict : 🟡 Oui, en commençant par 2 interfaces qui ont déjà plusieurs implémentations** (connecteurs d'URI et adaptateurs LLM). Les autres ensuite, quand une 2ᵉ implémentation réelle apparaît (règle des trois cas).

---

### M8. MCP et sidecars pour les extensions hors processus
**Ce que c'est.** Pour tout ce qui n'est **pas de confiance**, **pas en Python** (Rust, Go…) ou **lourd** : le brancher **hors du processus**, comme serveur MCP ou sidecar gRPC. ORCIA a déjà un client et un serveur MCP (FR, AD-6).

✅ Avantages
- **Isolation réelle** : un plantage ou une compromission reste confiné.
- **N'importe quel langage** : c'est la bonne manière d'introduire du Rust (sandbox-runner).
- Mise à l'échelle et déploiement indépendants ; protocole standard, aussi utilisable par les IDE.

⚠️ Inconvénients
- Latence réseau et sérialisation ; gestion des pannes (timeouts, relances, coupe-circuit).
- Plus de composants à déployer et surveiller ; authentification entre services à gérer.
- Débogage distribué.

**Verdict : 🟡 Uniquement pour le sandbox-runner (AD-9)** et les outils tiers. Ne pas l'appliquer aux domaines internes.

---

### M9. Déploiement par rôles (une image, plusieurs processus)
**Ce que c'est.** Un seul build, plusieurs rôles lancés par variable d'environnement :
- `api` ;
- `worker-orchestration` (rapide, nombreux) ;
- `worker-indexing` (Docling : lourd, CPU/GPU, peu nombreux) ;
- `trigger-dispatcher` (cron et webhooks) ;
- `sandbox-runner` (isolé, sans réseau).

Une **file Dramatiq par rôle**.

✅ Avantages
- Les bons avantages des microservices (mise à l'échelle et isolation des ressources) **sans leur complexité** : un seul code, une seule version.
- Une indexation lourde ne ralentit plus l'exécution des runs.
- Les engagements chiffrés (SSE < 500 ms, cache < 50 ms) sont protégés.

⚠️ Inconvénients
- Une image unique plus lourde (Docling) : on peut faire deux variantes `slim` et `full`.
- Plus de configurations Compose ou Kubernetes, et une supervision par rôle.

**Verdict : 🟢 À faire dès que les workers réels existent** (peu coûteux, gain fort en exploitation).

---

### M10. Modules activables par configuration
**Ce que c'est.**
- Activer ou désactiver un module par configuration : `ontology`, `rag`, `finops`, `jira`, `confluence`, `autonomy`.
- Les modules désactivés sont remplacés par des adaptateurs neutres.
- Le front masque les écrans correspondants (le manifeste de modules est exposé par `/api/v1/shell`).

✅ Avantages
- Permet un déploiement **« ORCIA Lite »** (pilote, petite équipe, démo) et une adoption progressive.
- Moins de surface en production.
- Facilite l'onboarding et les essais.

⚠️ Inconvénients
- **Explosion des combinaisons à tester** : il faut restreindre à quelques profils (`lite`, `standard`, `full`).
- Risque de comportements surprenants si l'ontologie est désactivée, car le PRD la place au cœur des contrôles (FR-10).
- Dette si les drapeaux s'accumulent sans être nettoyés.

**Verdict : 🟠 Plus tard (après le MVP)**, avec 2 à 3 profils figés, pas des drapeaux libres.

---

### M11. Front organisé par fonctionnalité
**Ce que c'est.**
- `apps/web/src/features/<domaine>/` (cockpit, inbox, gates, ontology, catalog, finops), chacun avec ses hooks TanStack Query, ses stores Zustand et ses routes.
- `@orcia/ui` reste la bibliothèque de composants partagée (déjà isolée).
- SDK `@orcia/api-client` découpé par tag OpenAPI.

✅ Avantages
- Correspond aux domaines du back ; écrans chargés à la demande.
- Plusieurs personnes (ou agents IA) peuvent travailler en parallèle sur des écrans différents.
- Des écrans isolés sont plus simples à tester en E2E.

⚠️ Inconvénients
- Il faut une règle d'import entre fonctionnalités (ESLint `boundaries`, ou `dependency-cruiser`).
- Risque de dupliquer des hooks : mutualiser dans `features/shared`.

**Verdict : 🟢 À poser dès l'Epic UI** (l'arborescence `app/` actuelle s'y prête déjà).

---

### Ce qu'il ne faut **pas** faire

| Piste | Pourquoi non |
|---|---|
| **Microservices par domaine** | Transactions distribuées, intégrité du Blackboard en ajout seul, versions figées et relance à partir d'une étape deviennent très difficiles ; coût d'exploitation sans commune mesure avec une petite équipe. |
| **Une base de données par domaine** | Casse les jointures dont l'ontologie, le RAG et les permissions ont besoin (requêtes récursives, filtrage RBAC dans le RAG). Préférer **un schéma PostgreSQL par domaine** dans la même base, si une séparation est souhaitée. |
| **Un framework d'injection de dépendances** | `Depends` plus une fabrique suffisent ; ce serait de la magie en plus. |
| **Des plugins partout dès maintenant** | Interfaces figées trop tôt, coût de compatibilité. |

---

## 2. Ce que la modularité apporte et ce qu'elle coûte

| Dimension | Aujourd'hui | Avec M1 à M7 |
|---|---|---|
| Ajouter un connecteur (`sharepoint://`) | Modifier `catalog` et `bootstrap` | Un plugin installé |
| Brancher la vraie base de données | Modifier tous les routeurs | Choisir l'adaptateur dans la configuration |
| Tester un domaine seul | Difficile (cycles, singletons) | Natif |
| Travail en parallèle (humains ou agents IA) | Conflits fréquents (`schemas/`, `exceptions.py`) | Par package ou fonctionnalité |
| Introduire du Rust | Pas de point d'entrée | Port, plus sidecar ou MCP |
| Charge mentale ou cognitive | Un seul gros bloc | **Plus élevée au début** : plus de packages, d'interfaces et d'événements |
| Débogage | Appels directs | Plus difficile côté événements (OpenTelemetry indispensable) |

---

## 3. Recommandations et ordre de mise en œuvre

| Phase | Pistes | Moment | Effort | Ticket |
|---|---|---|---|---|
| **A. Assainir** | **M1** (cycles), **M4** (`schemas` et erreurs), **M5** (point d'assemblage), **M3** (`import-linter`) | Tout de suite, dans le squelette de bout en bout | ~3 à 5 jours | `Story 3.1a` (Étape 0, refactorisation préalable) |
| **B. Structurer** | **M2** en 4 packages (`kernel`, `core`, `api`, `worker`), migration vers `uv` | Avec P3/P4 (alignement de la stack) | ~2 à 3 jours | `action_item` |
| **C. Exploiter** | **M9** (rôles et files), **M11** (front par fonctionnalité) | Dès que les workers réels et l'Epic UI démarrent | ~2 jours chacun | Intégré aux stories concernées |
| **D. Ouvrir** | **M6** (événements outbox), **M7** (plugins connecteurs et LLM) | Avant l'Epic autonomie et déclencheurs (AD-18), après le choix du moteur durable (P2) | ~1 semaine | `Story N.Ma` dédiée |
| **E. Isoler** | **M8** (sandbox-runner, éventuellement en Rust) | Refonte d'AD-9 | ~1 à 2 semaines | `Story N.Ma` dédiée |
| **F. Décliner** | **M10** (profils `lite`, `standard`, `full`) | Après le MVP | — | Backlog |

> [!IMPORTANT]
> Les phases **A** et **B** ont le meilleur rapport gain/effort et **conditionnent** tout le reste : il faut les faire avant d'ajouter de nouvelles fonctionnalités.

> [!WARNING]
> M1 touche à `orchestration/engine.py` et `blackboard/` (flux critiques : relance à partir d'une étape, versions figées). Lancer `gitnexus impact` en amont (`direction: upstream`) et **avertir si le risque est HIGH ou CRITICAL**, comme l'exige AGENTS.md.

## 4. Décisions à prendre
1. Granularité de départ : **4 packages** (recommandé) ou découpage complet en 9 ?
2. Événements entre domaines : **outbox maison** ou mécanique du moteur durable retenu (DBOS ou Temporal, voir P2) ?
3. Plugins : **dans le processus** (`entry_points`, plugins de confiance) et **hors processus** (MCP, plugins tiers ou non Python), comme proposé ?
4. Séparation des données : **un schéma PostgreSQL par domaine** dans la même base, ou tout dans `public` ?
