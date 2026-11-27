## Epic 10: `Mon Assistant` Tout-en-Un (Style EXEMPLE) — Personnalisation à 4 Niveaux (Mode A & Mode B), Routage à 3 Vitesses (`TTFT < 1,2 s`), Citations Déterministes (`[S1]/[G1]/[O1]`) & Dossiers Thématiques Collaboratifs (`📁 Dossiers`)

Permettre aux équipes métiers et techniques de disposer dans **`Mon Assistant`** d'un espace de travail conversationnel complet : personnalisable à 4 niveaux (`USER`, `WORKSPACE`, `TEAM`, `PLATFORM`) soit en **Mode A (Formulaire Rapide à 3 onglets)** soit en **Mode B (Studio Graphique `@xyflow/react`)** à l'intérieur des bornes inaltérables `🔒 AssistantHarness` (`AD-15`), garantissant un **`TTFT < 1,2 s`** grâce au cache Redis du prompt assemblé à 5 couches et au **Routage à 3 Vitesses (`⚡ Rapide`, `🔍 Agent & Outils MCP`, `🧠 Approfondi`)**, ancrant chaque affirmation par des **Citations Déterministes (`[S1]`, `[G1]`, `[O1]`)** résolues via `citation_map` SSE avec filtrage `READ_SOURCE` par lecteur (`AD-21`) et garde-fou anti-citation fantôme `< 5 ms`, et structurant le travail au long cours dans des **Dossiers Thématiques (`📁 Dossiers`)** dotés d'une continuité mémoire en Couche 5, d'un partage collaboratif à 3 niveaux (`🔒 Privé | 👥 Partagé | 📦 Espace`), d'un verrou de tour Redis léger (`SET NX EX 60`) et d'une identité `Passthrough` individuelle par message (`Principes B, H, K, K.4, K.5, K.6`).

### Story 10.1: Gouvernance & Personnalisation à 4 Niveaux de `Mon Assistant` (Bornes `🔒 AssistantHarness`, Mode A Formulaire Rapide à 3 Onglets & Mode B Studio Graphique)

As a Contributeur Métier, Chef d'Équipe ou Architecte (`Hélène UJ-1`, `Marc UJ-5`, `Antoine UJ-2`),
I want personnaliser le comportement de `Mon Assistant` selon mes droits à 4 niveaux (`USER`, `WORKSPACE`, `TEAM`, `PLATFORM`) soit via la modale simple `⚙ Réglages de l'assistant` à 3 onglets (**Mode A**), soit via l'éditeur graphique `@xyflow/react` (**Mode B** `☍ Personnaliser dans le Studio`), tout en garantissant que les bornes de sécurité `🔒 AssistantHarness` restent inaltérables,
So that chaque utilisateur et chaque équipe adapte le ton, les sources prioritaires et le raisonnement de son assistant sans jamais pouvoir contourner les règles de sécurité ou d'Ancrage Humain (`Principes B, H, K`, `AD-14`, `AD-15`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** le workflow système `orcia://system/workflows/assistant-agent` (5 nœuds orientés : `1. Routeur d'Intention`, `2. Query Planner & Expansion Ontologique`, `3. Fan-Out Parallèle`, `4. Tri Critique & Vérification d'Axiomes`, `5. Synthétiseur Adaptatif`) encadré par les bornes d'entrée/sortie Python **`🔒 AssistantHarness`** (`AD-15`)
**When** un utilisateur ouvre `Mon Assistant › ⚙ Réglages de l'assistant` (**Mode A**)
**Then** la modale affiche **3 onglets** adaptés à ses droits :
1. **`👤 Mes préférences (Couche 5 — USER)`** : ton/concision, format de réponse favori, Casquette métier par défaut et instructions personnelles permanentes ;
2. **`📦 Réglages de l'Espace (Couche 4 — WORKSPACE)`** (éditable par `TEAM_LEAD`, lecture seule sinon) : instructions métier de l'Espace, sources cochées par défaut, agents `@` recommandés, politique d'arbitrage et interrupteur **`🔌 Exposer l'Assistant de l'Espace en MCP (`/api/v1/mcp` — outil `assistant.ask`)`** (soumis à la Règle de l'Entonnoir `Principe G` si gelé par l'Équipe ou le Socle, avec bouton `📋 Copier la config MCP` — `Principe M.4`) ;
3. **`👁️ Assemblage complet (Lecture seule)`** : visualisation transparente des **5 couches de prompt actives** (`1. 🔒 Constitution`, `2. Pack Métier`, `3. Équipe`, `4. Espace`, `5. Utilisateur`).

**Given** un `TEAM_LEAD` ou `PLATFORM_ADMIN` qui clique sur **`☍ Personnaliser dans le Studio`** (**Mode B**)
**When** il modifie les sous-couches (`COUCHES · N`), ajoute un sous-agent ou ajuste le `Pré-prompt IA`, teste dans `▷ Tester` puis clique sur **`Enregistrer pour cet Espace / cette Équipe`** (ou **`↺ Réinitialiser à la configuration par défaut`**)
**Then** les bornes `🔒 AssistantHarness` (Entrée/Sortie Couche 1) sont verrouillées et impossibles à supprimer ou court-circuiter (`HTTP 422 ERR_IMMUTABLE_HARNESS_BOUNDARY` en cas de tentative via API), la personnalisation est enregistrée comme surcharge scopée (`TEAM` ou `WORKSPACE`) dans `workspace_customization_overrides` sans altérer le workflow socle, et le bouton `↺ Réinitialiser` restaure en 1 clic le comportement standard
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 10.2: Garantie de Latence (`TTFT < 1,2 s`), Cache Redis du Prompt Assemblé & Routage Conversationnel à 3 Vitesses (`⚡ Rapide`, `🔍 Agent & Outils`, `🧠 Approfondi`)

As a Utilisateur de `Mon Assistant` (`Hélène UJ-1`, `Yanis UJ-3`, `Lucas UJ-7`),
I want que `Mon Assistant` affiche le premier mot de sa réponse en moins de `1,2 seconde` (`TTFT < 1,2 s`) grâce au cache Redis du prompt assemblé et à l'exécution déterministe `< 80 ms` des nœuds 1 à 4, et pouvoir basculer entre 3 vitesses d'exécution (`⚡ Rapide`, `🔍 Agent & Outils MCP`, `🧠 Approfondi`),
So that la conversation quotidienne soit aussi fluide qu'un chat instantané tout en permettant de mobiliser des outils MCP ou un audit multi-étapes lorsque la question l'exige (`Principe K.4`, `AD-8`, `AD-15`, `AD-19`, `NFR-PERF-1`).

**Acceptance Criteria:**

**Given** un utilisateur qui envoie un message dans `Mon Assistant`
**When** le pipeline d'exécution démarre en **`⚡ Vitesse 1 (Rapide / Directe — défaut)`**
**Then** :
1. Le prompt système fusionné des 5 couches est lu en **`< 5 ms`** depuis le cache Redis (`assistant:prompt:<workspace_id>:<user_id>:<hat>`, `ttl=300s`, invalidé automatiquement sur événement Outbox `SettingsChanged`, modification de surcharge ou promotion au Glossaire) ;
2. Les nœuds 1 à 4 s'exécutent en Python/SQL déterministe en **`< 80 ms` avec `0` appel LLM intermédiaire**, via une seule requête SQL parallèle (`UNION ALL` combinant `pgvector` HNSW + `tsvector` RRF sur les sources cochées et le Glossaire actif) ;
3. Un **seul appel LLM** est déclenché au nœud 5 en **streaming SSE direct** (`text/event-stream`), délivrant le premier token en **`TTFT < 1,2 s`** (`NFR-PERF-1`).

**Given** la pilule de vitesse **`⚡ Standard ⌄ / 🧠 Approfondi`** dans la barre de saisie de `Mon Assistant` et la détection d'intention du Nœud 1
**When** l'utilisateur invoque `@Agent` / `/Compétence` (**`🔍 Vitesse 2`**) ou sélectionne **`🧠 Approfondi`** (**`🧠 Vitesse 3`**)
**Then** `Vitesse 2` affiche un indicateur d'étape temps réel (`🔍 Interrogation de Jira...`) pendant l'appel `ConnectorInvoker` (`TTFT < 2,5 s`), tandis que `Vitesse 3` active la planification LLM intermédiaire et la vérification multi-lentilles (`AD-10`) avec barre de progression étape par étape
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis mesurant le cache hit `< 5 ms` et l'invalidation Outbox) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 10.3: Citation Déterministe & Vérification des Sources (`[S1]`, `[G1]`, `[O1]`), Filtrage `READ_SOURCE` par Lecteur & Garde-Fou Anti-Citation Fantôme

As a Utilisateur Métier, Architecte ou Auditeur (`Hélène UJ-1`, `Antoine UJ-2`, `Sophie UJ-6`),
I want que chaque réponse de `Mon Assistant` s'appuie sur une Table de Preuves Numérotées (`[S1]`, `[G1]`, `[O1]`), affiche des pastilles de citation cliquables ouvrant l'extrait exact surligné (tout en masquant l'extrait si un co-lecteur n'a pas le droit `READ_SOURCE`), et neutralise automatiquement toute citation inventée,
So that aucune URI ni aucun numéro de ligne ne puisse être halluciné et qu'aucun partage de discussion ne provoque de fuite documentaire (`Principe K.5`, `AD-5`, `AD-8`, `AD-15`, `AD-19`, `AD-21`).

**Acceptance Criteria:**

**Given** les extraits récupérés en `< 60 ms` aux nœuds 2–4 (avec métadonnées `source_uri`, `title`, `section_or_symbol`, `page_or_lines`, `version_sha256`, `authority_role: REFERENCE | ACTIVE` et `freshness_status: FRESH | STALE_WARNING`)
**When** le `AssistantHarness` assemble le contexte du nœud 5 et ouvre le flux SSE
**Then** :
1. Il injecte une **Table de Preuves Numérotées** à identifiants courts (`[S1..Sn]` Sources RAG où `RÉFÉRENCE` prime sur `ACTIF`, `[G1..Gn]` Glossaire/Axiomes, `[O1..On]` Outils MCP) et émet dès `t = 80 ms` l'événement SSE `citation_map` ;
2. Lorsqu'un utilisateur consulte la discussion, l'API filtre dynamiquement chaque entrée de `citation_map` via `PermissionGuard` (`AD-21`) : si le lecteur ne possède pas `READ_SOURCE` sur la source sous-jacente, le `snippet` est purgé côté serveur et la pastille s'affiche en **`[S1 · 🔒 Source restreinte — Demander l'accès]`** ;
3. En post-stream (`< 5 ms`), le vérificateur déterministe contrôle que chaque balise `[S1]`/`[G1]`/`[O1]` produite appartient à la `citation_map` et remplace toute balise hors bornes par un badge d'alerte **`[Citation non vérifiée]`** tracé dans `audit_ledger`.

**Given** une réponse contenant des pastilles `[S1]`, `[G1]`, `[O1]` ou une Carte Artefact dans `Mon Assistant`
**When** un utilisateur habilité survole ou clique sur une pastille, déplie le bandeau **`📚 N sources citées`** ou clique sur **`📤 Publier vers une source...` / `📌 Officialiser dans le Coffre (@v1)`**
**Then** un Popover affiche le titre, le badge **`📚 RÉFÉRENCE`** / **`🛠️ ACTIF`** (ou **`⚠️ STALE_WARNING`**), la section/lignes exactes, le passage surligné et le bouton **`Ouvrir le document complet →`**, tandis que toute action d'officialisation `@v1` ou d'écriture vers le SI externe (`git://`, `confluence://`, `jira://`) est matériellement bloquée en écriture directe (`HTTP 422 ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE`, **Verrou V5 `AD-15`**) et déclenche obligatoirement le passage par la **Gate de Validation & Publication du Processus**
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 vérifiant le masquage `READ_SOURCE`, le garde-fou anti-citation fantôme et le Verrou V5) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 10.4: Dossiers Thématiques (`📁 Dossiers`), Continuité Mémoire Couche 5, Partage Collaboratif (`🔒 Privé | 👥 Partagé | 📦 Espace`) & Verrou de Tour Redis

As a Membre d'Équipe ou Chef d'Équipe (`Hélène UJ-1`, `Yanis UJ-3`, `Marc UJ-5`),
I want organiser mes échanges dans `Mon Assistant` au sein de `📁 Dossiers` thématiques dotés de notes épinglées, d'une mémoire partagée entre discussions du même dossier et d'un bouton de lancement de Processus en 1 clic, et pouvoir partager un dossier ou une discussion avec mes collègues de l'Espace en `👁️ Lecture seule` ou `✍️ Co-contributeur` sous identité `Passthrough` individuelle,
So that nous ne repartions jamais de zéro d'une discussion à l'autre et puissions co-construire un cadrage à plusieurs sans conflit d'écriture ni usurpation d'identité (`Principe K.6`, `AD-4`, `AD-6`, `AD-15`, `AD-19`, `AD-21`, Composant 15).

**Acceptance Criteria:**

**Given** l'en-tête sobre de `Mon Assistant` structuré en **3 onglets** (`💬 Discussion active` avec pilule `📁 Dossier ⌄` et bouton `📌 Notes du dossier`, `📁 Dossiers (N)`, `🕘 Historique & Recherche`)
**When** l'utilisateur crée ou sélectionne un `📁 Dossier` (ex. `📁 Refonte Tunnel Checkout`), épingle des décisions dans `📌 Notes du dossier` et ouvre une nouvelle discussion dans ce dossier
**Then** le `AssistantHarness` injecte automatiquement en **Couche 5 (`AD-15`)** les notes épinglées, pièces jointes/livrables de travail et résumés consolidés des discussions précédentes du dossier, et le bouton **`☍ Lancer un Processus à partir de ce dossier →`** pré-remplit les paramètres d'entrée (`Contrat du workflow`) d'un processus (notamment le **Workflow Pilote Semaine 1 `orcia://pack-sdlc/workflows/ticket-to-tech-spec`**) avec la synthèse du dossier.

**Given** un propriétaire de `📁 Dossier` ou de discussion qui clique sur **`👥 Partager`**
**When** il choisit l'un des **3 niveaux de visibilité** strictement confinés aux membres de l'Espace courant (`🔒 Privé` par défaut, `👥 Partagé avec des collègues choisis` en `👁️ Lecture seule` ou `✍️ Co-contributeur`, ou `📦 Ouvert à tout l'Espace`)
**Then** :
1. Si la discussion cite des sources restreintes, la modale affiche un avertissement préventif indiquant que leurs extraits seront masqués (`🔒 Source restreinte`) pour les collègues non habilités ;
2. Lorsqu'un **Co-contributeur (`✍️`)** envoie un message, le moteur acquiert un **verrou de tour Redis léger** (`SET lock:thread:<thread_id> <user_id> NX EX 60`), diffuse en temps réel via SSE aux pairs présents l'indicateur `✍️ {Prénom} interroge l'assistant...` puis les tokens générés, et exécute tous les connecteurs externes et outils MCP avec **l'identité `Passthrough` personnelle de l'auteur du message** (`AD-6`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis vérifiant le verrou de tour, l'isolation `Passthrough` et le confinement à l'Espace) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).
