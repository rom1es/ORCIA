## Epic 9: Coquille Ergonomique 4 Zones (Style Portals / EXEMPLE), Recherche Fédérée `⌘K` à 2 Vitesses (*Zero Layout Shift*), Compte Utilisateur (`UserSettingsModal`), Accostage Jour 0 (`Accostage 1/6`) & Aide Contextuelle Hybride (`❓`)

Permettre à tous les utilisateurs d'ORCIA de bénéficier dès la première seconde d'une **Coquille Globale à 4 Zones** auto-descriptive (`TopHeaderBar 52px`, `Sidebar 240px/68px` aux **8 menus fixes non numérotés** `Cockpit | Mon Assistant | Mes Processus | Mes Agents | Mes Espaces | FinOps | Configuration | Aide` avec terminologie invariante **`Espace`**, `Zone Centrale 1fr` et `Colonne d'Aide Contextuelle ? 340px` auto-repliée sur `< 1440px`), d'un **Cockpit épuré** (extinction automatique des compteurs `0/0/0/0` quand `total == 0` et séparation entre décisions courtes `Tie-Break` et **Vue Fokus de Revue `Run #ID`** avec verrou Redis `AD-4`), d'un **Parcours d'Accostage Progressif Jour 0 (`Accostage 1/6`)** protégé contre le *First-User Takeover* (`LOCK TABLE users` + `ORCIA_BOOTSTRAP_TOKEN`) et débloquant l'essai dès `1 modèle LLM` ($\rightarrow \ge 2$ familles `AD-10`), d'une **Recherche Fédérée & Contextuelle `⌘K` à 2 vitesses sans saut visuel** (3 portées, 7 familles, lexical `< 30 ms` `0 $` en tête + vectoriel HNSW sur pause `450 ms` en bas avec *Deep-Linking Auto-Focus*), d'un **Menu Login (`UserAccountDropdown`) & Modale « Paramètres de mon compte » (`UserSettingsModal` à 4 onglets)** à double persistance `0 ms` anti-FOUC, et d'un **Système d'Aide Hybride (`HelpArticle` factorisé dans `catalog_items` + `cas/<sha256>`)** servi en `< 10 ms` via Redis (`Principes A, A.2, A.3, C, D, D.4, E, F, G`, `Section 2`).

### Story 9.1: Coquille 4 Zones Direction C (8 Menus Non Numérotés, Terminologie Fixe `Espace`, Cockpit Épuré avec Extinction `0/0/0/0` & Séparation Cockpit vs Vue Fokus de Revue `Run #ID`)

As a Utilisateur Métier, Chef d'Équipe ou Administrateur (`Hélène UJ-1`, `Marc UJ-5`, `Karim UJ-9`),
I want naviguer dans une coquille à 4 zones dotée de 8 entrées fixes non numérotées (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`), d'une terminologie invariante `Espace`, d'un Cockpit qui masque automatiquement les compteurs vides `0/0/0/0` et distingue les décisions courtes (`Tie-Break`) de la Vue Fokus de Revue (`Run #ID`),
So that l'interface reste immédiatement lisible sans surcharge visuelle (Loi de Hick) et que les revues d'artefacts complexes disposent de tout l'espace central et d'un verrou de présence exclusif (`Principes A, C, E, F, G`, `AD-4`, `AD-19`, `UX-DR1`, `UX-DR2`).

**Acceptance Criteria:**

**Given** un utilisateur connecté sur Desktop (`>= 1280px`) ou Laptop (`768px - 1279px`)
**When** la coquille applicative `AppShell` est affichée
**Then** elle structure l'écran en **4 zones strictes** : (1) `TopHeaderBar` (`52px`) contenant le sélecteur fixe **`Espace : [Nom] ⌄`** (`⌘W`), la barre de recherche fédérée `⌘K`, le bouton `? Aide`, le tiroir `🔔 Notifications` (`420px`) et le bouton `👤 Login` avec badge de Casquette métier ; (2) `Sidebar` (`240px` / `68px` Rail via `[`) présentant exactement les **8 entrées non numérotées** (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`) avec en pied le sélecteur de Pack Métier ; (3) `Zone Centrale` (`1fr`) ; et (4) `Colonne d'Aide Contextuelle ?` (`340px` à droite, qui se replie automatiquement par défaut sur les écrans `< 1440px` dès que `total >= 1` décision est en attente).

**Given** l'écran d'accueil **`Cockpit`** (`/`)
**When** le nombre total d'actions requises (`Ancrages Humains + Arbitrages + Revues + Alertes`) vaut `total == 0` **OU** `total >= 1`
**Then** :
1. Si `total == 0`, les 4 compteurs KPI (`0/0/0/0`) et la barre de filtres sont **automatiquement masqués** au profit d'une bannière sobre `✅ Aucune décision en attente` suivie de l'Accès Rapide à `Mon Assistant` et des 3 cartes d'orientation ;
2. Si `total >= 1`, les décisions courtes (**`Arbitrage Tie-Break`** à 2–3 options) se tranchent directement sur place en 1 clic dans le `Cockpit`, tandis que les actions lourdes (**`Ancrage Humain Violet`**, **`Briefing de Revue 4 blocs`**, **`Validation par Découpage`** et **`Challenge Amont What-If`**) affichent un résumé compact et un bouton **`Ouvrir l'atelier de revue →`** qui bascule vers la **Vue Fokus de Revue (`Mes Processus › Exécutions & Décisions › Run #ID`)** en acquérant automatiquement le verrou de présence Redis (`SET lock:step:<step_execution_id> <user_id> NX EX 900`, `AD-4`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`Vitest`) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 9.2: Parcours d'Accostage Progressif Jour 0 (`Accostage 1/6`), Protection Anti-*First-User Takeover* & Palier Progressif `1 Modèle → ≥ 2 Familles AD-10`

As a Administrateur Plateforme ou Premier Utilisateur au Jour 0 (`Karim UJ-9`, `Marc UJ-5`),
I want initialiser une instance vierge d'ORCIA sans risque de prise de contrôle concurrente (*First-User Takeover*), débloquer l'essai de `Mon Assistant` dès le 1er modèle LLM configuré puis les Gates Agentiques dès la 2e famille orthogonale, et suivre ma progression via le bandeau interactif `Accostage 1/6`,
So that l'installation initiale soit à la fois sécurisée cryptographiquement et praticable en moins de 5 minutes sans blocage bureaucratique (`Section 2`, `AD-10`, `AD-16`, `AD-19`).

**Acceptance Criteria:**

**Given** une base PostgreSQL 18 vierge (`COUNT(*) FROM users == 0`) lors du premier accès à `/welcome-setup`
**When** la création du premier compte `PLATFORM_ADMIN` est soumise
**Then** la transaction acquiert `LOCK TABLE users IN EXCLUSIVE MODE` (garantissant qu'un seul premier administrateur peut être créé même sous requêtes concurrentes) et, pour tout `ORCIA_ENV != "local"`, exige la validation du jeton d'amorçage **`ORCIA_BOOTSTRAP_TOKEN`** généré au démarrage (rejet `HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN` sinon).

**Given** l'**Assistant de Bienvenue en 3 étapes** et le bandeau de progression **`Accostage 1/6`** dans le `Cockpit`
**When** l'administrateur configure un **seul modèle LLM** (ex. `Ollama local` ou `OpenAI`) à l'étape 2
**Then** le système active immédiatement le **Mode Essai Rapide** (`Mon Assistant` et le `Cockpit` deviennent utilisables avec un badge ambre non bloquant `⚠️ 1 seule famille de modèles configurée — Ajoutez une 2e famille dans Configuration › Modèles IA pour activer les Gates Agentiques AD-10`), et déverrouille automatiquement les Gates Agentiques dès qu'une **2e famille de modèles distincte** est validée
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration sous concurrence (`testcontainers` PG18 vérifiant le `LOCK TABLE users`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 9.3: Recherche Fédérée & Contextuelle `⌘K` à 2 Vitesses (*Zero Layout Shift*, 3 Portées, 7 Familles & Deep-Linking Auto-Focus)

As a Utilisateur Métier, Architecte ou Tech Lead (`Hélène UJ-1`, `Antoine UJ-2`, `Yanis UJ-3`),
I want rechercher instantanément depuis la barre supérieure (`⌘K`) n'importe quel dossier, discussion, processus, livrable, source, terme du glossaire, agent ou fiche d'aide selon 3 portées (`📍 Cet écran`, `📦 Cet Espace`, `🌐 Tous mes Espaces`) avec un affichage en 2 vitesses sans aucun saut visuel (*Zero Layout Shift*) et une ouverture profonde au clic,
So that je retrouve n'importe quelle connaissance ou action en moins d'une seconde sans que la liste ne saute sous mon curseur ni que les coûts d'embeddings n'explosent à la frappe (`Principe A.2`, `AD-8`, `AD-19`, `AD-21`, Composant 17 `top-header-search-command`).

**Acceptance Criteria:**

**Given** le composant `@orcia/ui` **`top-header-search-command`** (`680px × max 480px`) ouvert via `⌘K` / `Ctrl+K` et l'endpoint `GET /api/v1/search` filtré par `PermissionGuard` (`AD-21`)
**When** l'utilisateur saisit une requête et choisit l'une des **3 pilules de portée** (`📍 Cet écran` | `📦 Cet Espace` par défaut | `🌐 Tous mes Espaces`)
**Then** :
1. **Vitesse 1 (`As-You-Type`, `< 30 ms`, `0 $` d'appel LLM)** : à chaque frappe (`debounce 80 ms`), une requête SQL unique (`UNION ALL` sur `PostgreSQL tsvector` + trigrammes `pg_trgm`) retourne les résultats exacts/préfixes groupés parmi les **7 familles** (`📁 Dossiers & 💬 Discussions`, `☍ Processus & ▶ Exécutions`, `📄 Livrables & Artefacts`, `🗄️ Sources & Extraits`, `📖 Glossaire & Règles Métier`, `🤖 Agents & Compétences`, `❓ Fiches d'Aide & Actions`) et **verrouille leur position en tête** de chaque catégorie ;
2. **Vitesse 2 (`Pause de frappe 450 ms`, uniquement si $\ge 3$ mots ou clic sur `✨ Recherche sémantique`)** : la recherche vectorielle `pgvector halfvec(1024)` HNSW + `RRF` (`AD-8`, cachée 5 min dans Redis par `(workspace_id, sha256(query_norm))`) ajoute ses trouvailles **exclusivement en bas** de chaque catégorie avec le badge `✨ Passage proche`, sans jamais déplacer la ligne actuellement sélectionnée au clavier (`↑`/`↓`).

**Given** un résultat sélectionné dans `top-header-search-command`
**When** l'utilisateur appuie sur `Entrée ↵` (ou `⌘+Entrée` / `Ctrl+Entrée`, ou clique sur le pied de liste `💬 Poser la question « ... » à Mon Assistant →`)
**Then** `Entrée ↵` exécute le **Deep-Linking + Auto-Focus** vers l'élément exact (avec surlignage temporaire Ambre/Cobalt `2 s`, ou ouverture directe de la Colonne `❓` sans quitter l'écran pour une fiche d'aide), `⌘+Entrée` ouvre l'aperçu dans le panneau latéral droit sans quitter l'écran courant, et le bouton de pied bascule vers `Mon Assistant` en pré-attachant les meilleurs extraits trouvés
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis) couvrent $\ge 90\%$ du moteur de recherche à 2 vitesses (`AD-17`, `AD-19`).

### Story 9.4: Menu Déroulant du Login (`UserAccountDropdown`), Modale « Paramètres de mon compte » (`UserSettingsModal` à 4 Onglets) & Double Persistance `0 ms` Anti-FOUC

As a Utilisateur Connecté (`Hélène UJ-1`, `Yanis UJ-3`, `Lucas UJ-7`),
I want ouvrir au clic sur mon login dans la `TopHeaderBar` un menu rapide (`UserAccountDropdown`) permettant de basculer en 1 clic le thème ou la langue et de me déconnecter, ou d'ouvrir la modale `⚙️ Paramètres de mon compte` (`UserSettingsModal` à 4 onglets) en fermant automatiquement le menu rapide,
So that je gère mes préférences d'affichage sans clignotement (`0 ms` anti-FOUC), ma sécurité (`Argon2id`/`TOTP`), mes jetons personnels `Passthrough` et mes clés IDE MCP dans un espace personnel clairement séparé de la configuration d'entreprise (`Principe A.3`, `AD-6`, `AD-19`, `AD-21`, Composant 18).

**Acceptance Criteria:**

**Given** le bouton **`👤 Login · [Casquette]`** à l'extrême droite de la `TopHeaderBar`
**When** l'utilisateur clique sur son login, actionne un switch rapide (`🌓 Apparence` ou `🌐 Langue`) ou clique sur **`🚪 Se déconnecter`**
**Then** :
1. Le menu déroulant **`UserAccountDropdown` (`280px`)** s'ouvre avec l'identité/rôle, le sélecteur de Casquette métier, les 2 bascules 1-clic (`☀️ Clair / 🌙 Sombre`, `FR / EN`), les entrées `⚙️ Paramètres de mon compte...` (`g u`) et `🔗 Mes accès aux sources...`, et le bouton **`🚪 Se déconnecter`** ;
2. Tout changement de thème ou de langue est écrit **instantanément (`0 ms`) dans `localStorage`** (`orcia_theme`, `orcia_locale`, lu dès `index.html` avant le premier rendu React pour garantir **zéro FOUC**) ET synchronisé en arrière-plan via `PATCH /api/v1/users/me/preferences` ;
3. Le clic sur **`🚪 Se déconnecter`** appelle `POST /api/v1/auth/logout`, révoque immédiatement le JWT et le Refresh Token `HttpOnly` dans Redis (`AD-6`), purge les caches sensibles du navigateur et redirige vers `/login`.

**Given** le menu `UserAccountDropdown` ouvert
**When** l'utilisateur clique sur **`⚙️ Paramètres de mon compte...`** (ou tape `g u`)
**Then** `UserAccountDropdown` **se ferme automatiquement** et la modale centrée **`UserSettingsModal` (`720px × max 600px`)** s'ouvre sur ses **4 onglets** :
1. **`🎨 Préférences & Affichage`** : Mode Clair/Sombre/Auto, Langue FR/EN, Casquette métier par défaut, ouverture auto de l'Aide `❓`, notifications `🔔`, et lien de renvoi `💬 Personnaliser le comportement de Mon Assistant →` (sans dupliquer la zone de saisie Couche 5) ;
2. **`👤 Profil & Sécurité`** : Identité, changement de mot de passe local `Argon2id`, `MFA TOTP`, révocation des sessions actives ;
3. **`🔗 Accès aux sources (Passthrough)`** : gestion par `<SecretField />` write-only des jetons personnels Git/Jira/Confluence/Notion chiffrés `AES-256-GCM` (`user_passthrough_credentials`, `AD-6`) avec bouton `🔌 Tester mon jeton` ;
4. **`💻 Clés IDE & MCP`** : génération et révocation instantanée (`< 10 ms` Redis) des jetons personnels scopés (`pat_mcp_*` hachés `SHA-256` en base, expiration obligatoire `30j/90j`, plafond `RPM`, sélection des Espaces autorisés et des capacités exposées : `Mon Assistant`, `Agents publiés de l'Espace`, `Recherche KB & Glossaire`, `Brouillons Staged`) pour `/api/v1/mcp`, avec sélecteur de cible (**Tout l'Espace `/api/v1/mcp/spaces/<ws_slug>`** ou **Un agent précis `/api/v1/mcp/agents/<agent_slug>`**) et extrait JSON prêt à copier pour **VS Code / Cursor / Claude Code / Antigravity / JetBrains** (`Principe M.4`)
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et E2E (`Playwright`) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).

### Story 9.5: Système d'Aide Contextuelle Hybride (`HelpArticle` dans `catalog_items` + `cas/<sha256>`), Colonne `❓` (`340px`), Menu `Aide` & Seeder Git-Seeded

As a Utilisateur Métier ou Administrateur (`Hélène UJ-1`, `Karim UJ-9`),
I want consulter à tout moment dans la Colonne `❓` (`340px`) ou dans le menu `Aide` une documentation contextuelle bilingue (`fr`/`en`) liée dynamiquement à l'écran actif, servie en `< 10 ms` depuis la base PostgreSQL (`catalog_items`), le stockage CAS S3 (`cas/<sha256>`) et Redis, et initialisée automatiquement au démarrage depuis Git,
So that chaque écran d'ORCIA soit auto-documenté en langage clair et que de nouvelles fiches d'aide puissent être rattachées à chaud ou restaurées (`⏪ Rollback`) sans créer de 19e table SQL ni redéployer l'application (`Principes D & D.4`, `AD-5`, `AD-14`, `AD-19`).

**Acceptance Criteria:**

**Given** la table existante `catalog_items` (`AD-5`), une migration Alembic ajoutant l'index GIN `idx_catalog_help_routes` sur `(metadata_jsonb->'bound_routes') WHERE item_type = 'HELP_ARTICLE'`, le stockage CAS `SeaweedFS` (`cas/<sha256>`) et `workspace_customization_overrides` (`AD-14`)
**When** le seeder de démarrage (`packages/orcia-core/bootstrap/seeder.py`) s'exécute
**Then** il charge par `INSERT ... ON CONFLICT DO UPDATE` idempotent toutes les fiches Markdown à frontmatter YAML déclaratif situées dans `docs/help/{fr,en}/` et `packages/orcia-pack-*/help/{fr,en}/` sous `item_type = "HELP_ARTICLE"`, stocke leur corps Markdown dans `cas/<sha256>`, et ne écrase jamais une version `@v(N+1)` plus récente publiée à chaud.

**Given** un utilisateur qui navigue vers une route TanStack Router (ex. `/mes-espaces/$id/sources`) avec la **Colonne d'Aide Contextuelle `❓` (`340px`)** ouverte ou qui consulte le menu **`Aide`**
**When** l'interface appelle `GET /api/v1/help/resolve?route=/mes-espaces/$id/sources&pack=orcia-pack-sdlc&lang=fr`
**Then** le service résout en `< 10 ms` (via le cache Redis `help:route:<route>:<pack>:<lang>`) la fiche active en appliquant la fusion à 4 niveaux (`Base -> Pack -> Team/Workspace -> User`, `AD-14`), affiche dans la Colonne `❓` le résumé *« À quoi sert cet écran ? »*, les accordéons *Pas-à-pas*, *Termes clés* et *Questions fréquentes*, ainsi que le bouton **`Poser une question à l'assistant sur cet écran →`**, et permet à un administrateur d'effectuer un **`⏪ Rollback` en 1 clic** vers `@v(N-1)`
**And** `lint-imports` passe à `0` violation et les tests unitaires (`pytest`, `Vitest`) et d'intégration (`testcontainers` PG18 + Redis + SeaweedFS) couvrent $\ge 90\%$ du périmètre (`AD-17`, `AD-19`).
