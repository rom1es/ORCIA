## Epic 25: Sobriété Cockpit Jour 0, Coquille 9 Entrées (Mon Organisation & Administration), Espace Personnel Automatique PG18, Hub Modèles IA Fiable & Découplage Mon Assistant / RAG (AD-24)

Corriger les frictions UX et architecturales constatées post-Epic 24 lors de l'utilisation réelle Jour 0 : provisionner automatiquement un Espace Personnel privé (`PRIVATE_USER` PG18) pour chaque utilisateur sans rompre la vérité terrain `0` user / `0` workspace après `pnpm db:reset`, unifier le Guide d'Accostage (`6` jalons dont `4. Premier Espace d'équipe`, non repliable tant que `< 6/6`), dégriser `Mes Processus` dès `1` modèle IA actif, aligner la coquille sur **9 entrées fixes** (`Mon Organisation` ouvert à tous sous `Mes Espaces`, `Administration` strictement `5` onglets réservée `PLATFORM_ADMIN` / `SECOPS`, logo cliquable `[O] ORCIA › <Écran>` unique en `TopHeaderBar`, sélecteur unique d'`Espace actif` groupé par `Personnel` + `Équipe / BU`, retrait des `ⓘ` et `Active context`), purger les résidus démo RAM (`marc.lead@orcia.io`, `DEFAULT_ARBITRATION_OPTIONS`) et blocs d'attente à vide du `Cockpit`, fiabiliser la suppression PG18 et le retour d'erreur localisé dans le Hub des Modèles IA (`<OrciaSpinner />`, masquage réindexation à `0` document indexé), et découpler `Mon Assistant` (actif dès `1` modèle `chat` sans modèle `embedding`) tout en bloquant dès `POST /datasources` et l'UI l'ajout de sources RAG vectorielles (`source_nature != 'SOURCE_CODE'`) selon l'amendement `AD-8` / `AD-16` / `AD-24`.

---

### Story 25.1: Provisionnement Automatique de l'Espace Personnel (`PRIVATE_USER` PG18), Guide d'Accostage Unifié & Dégrisage `Mes Processus`

As a Utilisateur / Administrateur Plateforme (`Thomas`, `Claire`, `Lucas`),
I want recevoir automatiquement et de manière idempotente un **Espace Personnel privé** (`visibility_mode = 'CONFIDENTIAL_RESTRICTED'` en SQL + `settings_jsonb.ui_visibility_mode = 'PRIVATE_USER'` + `settings_jsonb.personal_owner_user_id`) lors de l'initialisation du 1er Admin Jour 0, de la création d'un compte IAM ou de ma première connexion (tout en conservant `0` workspace après `pnpm db:reset` tant que `0` user existe), disposer d'un **Guide d'Accostage unifié** à `6` jalons (incluant `4. Premier Espace d'équipe`, avec coches vertes et flèches alignées verticalement proche du texte, non repliable tant que `< 6/6`) et voir **`Mes Processus`** dégrisé dès `1` modèle IA configuré,
So that chaque utilisateur dispose immédiatement d'un espace personnel isolé en PG18 sans fuite inter-admins, que la progression d'accostage reste claire et stable jusqu'à `6/6` et que la création/exécution de processus démarre dès le premier modèle `chat` (`AD-16` amendé Epic 25, `AD-21`).

**Dépendances :** Clôture Epic 24 (`epic-24: done`), amendement `AD-16` Epic 25.
**CAP couvertes :** `CAP-004`, `CAP-005`, `CAP-061`, `CAP-067`, `CAP-020`.
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/bootstrap/`, `packages/orcia-core/src/orcia_core/permissions/`, `apps/api/src/orcia_api/routers/bootstrap.py`, `apps/api/src/orcia_api/routers/bootstrap_accostage.py`, `apps/api/src/orcia_api/routers/org_and_workspaces.py`, `apps/web/src/components/platformSetupAccostage.ts`, `apps/web/src/components/platformSetupWorkspaces.ts`, `apps/web/src/features/cockpit/PlatformOnboardingChecklistCard.tsx`, `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx`, `apps/web/src/components/ShellContainer.tsx`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-1-espace-personnel-auto-pg18-accostage-unifie-et-degrisage-processus-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une base réinitialisée au Jour 0 via `pnpm db:reset` (`0` utilisateur en PG18)
**When** aucun compte administrateur n'a encore été créé, puis que le 1er `PLATFORM_ADMIN` s'initialise (ou qu'un nouvel utilisateur est créé via IAM / effectue sa première connexion)
**Then** avant création du 1er admin la table `workspaces` contient strictement `0` ligne, puis lors de l'initialisation / création IAM / première connexion un Espace Personnel privé unique est provisionné transactionnellement et de manière idempotente en PostgreSQL 18 (`visibility_mode = 'CONFIDENTIAL_RESTRICTED'`, `settings_jsonb.ui_visibility_mode = 'PRIVATE_USER'`, `settings_jsonb.personal_owner_user_id = <user_id>`), strictement accessible à son propriétaire (aucun accès implicite par un autre `PLATFORM_ADMIN`).

**Given** un utilisateur connecté sur `/cockpit` avec moins de `6/6` jalons d'accostage complétés et `1` modèle IA `chat` actif configuré
**When** il consulte le Guide d'Accostage unifié et la barre latérale de navigation
**Then** le Guide d'Accostage affiche les `6` jalons dont `4. Premier Espace d'équipe`, ses coches vertes et flèches d'action sont alignées verticalement à proximité immédiate du texte, le bloc demeure **non repliable** tant que la complétion est `< 6/6`, et l'entrée **`Mes Processus`** est immédiatement dégrisée et navigable dès `1` modèle IA actif (sans attendre un second modèle ou un modèle d'embedding).

---

### Story 25.2: Coquille 9 Entrées (`Mon Organisation` & `Administration` 5 Onglets), TopBar `[O] ORCIA › Écran`, Sélecteur d'Espace Unique & Retrait `ⓘ` / `Active context`

As a UX Designer (`Sally`) & Utilisateur Authentifié (`Claire`, `Marc`, `Lucas`, `Thomas`),
I want naviguer via une barre latérale à **9 entrées fixes** (incluant **`Mon Organisation`** sous `Mes Espaces` visible par tous les utilisateurs authentifiés — lecture seule pour les membres simples, édition/invitation selon `can_*` pour Leads/Admins — et le renommage de `Configuration` en **`Administration`** strictement réservé `PLATFORM_ADMIN` / `SECOPS` à `5` onglets : `Comptes & Habilitations`, `Authentification`, `Modèles IA`, `Connecteurs`, `Packs Métiers`), cliquer sur **`[O] ORCIA › <Écran>`** tout en haut à gauche de la `TopHeaderBar` pour revenir à `/cockpit` (sans doublon `[O] ORCIA` dans la Sidebar), basculer grâce à un **sélecteur unique d'`Espace actif`** groupé (`Personnel` + `Équipe / BU`) câblé sur tous les écrans, et bénéficier d'en-têtes dépourvus d'icônes flottantes `ⓘ` et de badge `Active context`,
So that l'architecture d'information soit cohérente entre la Sidebar, la `TopHeaderBar` et l'ensemble des écrans métiers sans duplication de sélecteurs ni bruit visuel (`DESIGN.md`, `EXPERIENCE.md`).

**Dépendances :** Dépend de `Story 25.1` (Espace Personnel disponible dans le groupe `Personnel` du sélecteur).
**CAP couvertes :** `CAP-058`, `CAP-060`, `CAP-064`, `CAP-067`, `CAP-203`.
**Fichiers impactés :** `packages/ui/src/primitives/FourZoneDirectionCShell.tsx`, `packages/ui/src/primitives/FourZoneSidebarRail.tsx`, `packages/ui/src/shell/AppShellTopbar.tsx`, `packages/ui/src/shell/GlobalSidebar.tsx`, `packages/ui/src/shell/ScopeSwitcher.tsx`, `apps/web/src/components/ShellContainer.tsx`, `apps/web/src/components/shellPresets.ts`, `apps/web/src/components/shellBreadcrumbAndScope.ts`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/features/admin/`, `apps/web/src/features/organization/`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-2-coquille-9-entrees-mon-organisation-administration-topbar-orcia-et-selecteur-espace-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un utilisateur authentifié (membre simple, Lead ou `PLATFORM_ADMIN` / `SECOPS`) sur l'application Desktop
**When** il inspecte la barre latérale gauche et la `TopHeaderBar` sur `/cockpit`, `/assistant`, `/processes`, `/agents`, `/spaces`, `/organization`, `/finops` et `/settings`
**Then** la Sidebar affiche exactement **`9` entrées fixes** (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `Mon Organisation`, `FinOps`, `Administration`, `Aide`), `Mon Organisation` (`/organization`) est accessible à tous les utilisateurs authentifiés (en lecture seule de l'organigramme pour un membre simple, avec actions d'édition/invitation conditionnées par `can_*` pour Leads/Admins), `Administration` est visible uniquement pour `PLATFORM_ADMIN` / `SECOPS` avec strictement **`5` onglets** (`Comptes & Habilitations`, `Authentification`, `Modèles IA`, `Connecteurs`, `Packs Métiers`), la `TopHeaderBar` affiche tout en haut à gauche le logo cliquable **`[O] ORCIA › <Écran>`** ramenant à `/cockpit`, et aucun doublon `[O] ORCIA` n'apparaît dans la Sidebar.

**Given** le sélecteur unique d'`Espace actif` en haut de la Sidebar et les en-têtes de cartes principales des écrans métiers
**When** l'utilisateur change d'espace (entre `Personnel` et `Équipe / BU`) puis navigue entre `Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces` et `FinOps`
**Then** un seul sélecteur d'espace groupé (`Personnel` + `Équipe / BU`) remplace l'ancien double sélecteur empilé, l'espace sélectionné reste synchronisé et actif sur `100 %` des 6 écrans cibles (avec survie au `F5`), aucune icône flottante `ⓘ` n'apparaît dans les en-têtes de cartes principales (l'aide étant pilotée par `? Aide` de la `TopHeaderBar`), et aucun badge `Active context` / `Contexte actif` n'est affiché.

---

### Story 25.3: Sobriété Cockpit Jour 0, Purge du Run Démo RAM (`marc.lead@orcia.io`) & Retrait des Blocs d'Attente à Vide

As a Architecte (`Winston`) & UX Designer (`Sally`),
I want purger définitivement le run démo en mémoire RAM (`marc.lead@orcia.io`) et la constante `DEFAULT_ARBITRATION_OPTIONS`, supprimer le bandeau `"Aucune décision en attente"`, le prompt rapide `"Accès rapide à Mon Assistant"` et le badge `"Contexte actif"` du `Cockpit`, et n'afficher des cartes d'ancrage ou d'arbitrage que lorsqu'une action réelle est effectivement en attente en PostgreSQL 18,
So that le `Cockpit` respecte strictement la sobriété Jour 0 (`<= 3` blocs, zéro donnée fictive RAM) tout en affichant instantanément les vraies décisions humaines persistées en PG18 (`AD-17`, `DESIGN.md`, `EXPERIENCE.md`).

**Dépendances :** Parallélisable après `Story 25.1` (coordonnée avec `Story 25.2` sur le `Cockpit`).
**CAP couvertes :** `CAP-005`, `CAP-023`, `CAP-060`, `CAP-100`.
**Fichiers impactés :** `apps/web/src/features/cockpit/index.tsx`, `apps/web/src/features/cockpit/cockpitGovernanceHelpers.ts`, `apps/web/src/features/cockpit/CockpitHumanLedGovernanceSection.tsx`, `apps/web/src/features/cockpit/CockpitRunsSection.tsx`, `apps/web/src/features/cockpit/useCockpitGovernanceController.ts`, `packages/ui/src/primitives/StreamlinedCockpitView.tsx`, `packages/ui/src/primitives/CockpitDecisionsCard.tsx`, `packages/ui/src/primitives/CockpitOrientationCards.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-3-sobriete-cockpit-jour0-purge-run-demo-ram-et-retrait-blocs-attente-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** le code source `apps/web/src/**` et `packages/ui/src/**` audité après purge et redémarrage sur une base Jour 0
**When** un utilisateur ouvre `/cockpit` avec `0` exécution / arbitrage en base PG18
**Then** aucune référence à `marc.lead@orcia.io` ni à `DEFAULT_ARBITRATION_OPTIONS` n'existe dans le code de production, le bandeau `"Aucune décision en attente"`, le bloc prompt rapide `"Accès rapide à Mon Assistant"` et le badge `"Contexte actif"` ne sont jamais rendus sur `/cockpit`, et aucune carte factice d'ancrage humain ou d'arbitrage ne s'affiche tant qu'aucune action réelle n'est en attente en PostgreSQL 18.

**Given** une exécution réelle persistée en PostgreSQL 18 requérant un ancrage humain (`human_authored_required`) ou un arbitrage (`WAITING_FOR_HUMAN_ARBITRATION`) sur l'espace actif
**When** l'utilisateur ouvre `/cockpit`
**Then** la carte d'ancrage ou d'arbitrage correspondant à l'enregistrement réel PG18 s'affiche dans la limite de sobriété (`<= 3` blocs) et disparaît dès traitement ou résolution en base.

---

### Story 25.4: Hub Modèles IA — Suppression PG18 Fiable sans Fallback RAM (`settingsAiModelsFallback.ts`), `<OrciaSpinner />` Unifié, Erreur Locale & Masquage Réindexation

As a Administrateur Plateforme (`Thomas`) & Tech Lead (`Amelia`),
I want supprimer tout fallback mémoire RAM (`settingsAiModelsFallback.ts`) sur le Hub des Modèles IA afin que l'ajout et la suppression soient `100 %` fiables en PostgreSQL 18 (avec propagation immédiate vers `F5` et l'état réel), unifier les états de chargement sur `<OrciaSpinner />`, afficher toute erreur ou timeout de test/connexion localisée directement sous la carte du modèle concerné, et masquer le bloc de réindexation vectorielle tant que `0` document est indexé,
So that la gestion des modèles IA dans `Administration › Modèles IA` (`/settings/ai-models`) reflète fidèlement PostgreSQL 18 sans faux succès RAM ni bruit visuel (`AD-24`, `AD-17`).

**Dépendances :** Parallélisable avec `Story 25.2` et `Story 25.3`.
**CAP couvertes :** `CAP-053`, `CAP-100`, `CAP-190`.
**Fichiers impactés :** `apps/web/src/features/admin/ai-models/AiModelConfigModal.tsx`, `apps/web/src/features/admin/ai-models/AiModelDeleteDialog.tsx`, `apps/web/src/features/admin/ai-models/AiModelsMasterTable.tsx`, `apps/web/src/features/admin/ai-models/AiModelReindexPanel.tsx`, `apps/web/src/features/admin/ai-models/aiModelsApiBridge.ts`, `apps/web/src/features/admin/ai-models/useAiModelConfigModalState.ts`, `apps/api/src/orcia_api/routers/ai_models_hub.py`, `apps/api/src/orcia_api/routers/_ai_models_test_and_reindex_routes.py`, `packages/ui/src/primitives/`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-4-hub-modeles-ia-suppression-fiable-spinner-unifie-erreur-locale-et-masquage-reindexation-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** un administrateur connecté sur `Administration › Modèles IA` (`/settings/ai-models`)
**When** il supprime un modèle IA existant puis recharge la page (`F5`), et qu'il lance un test de connexion provoquant un timeout ou une erreur fournisseur (`401`/`404`/`5xx`)
**Then** le modèle supprimé est effectivement supprimé en PostgreSQL 18 sans aucun recours à `settingsAiModelsFallback.ts` (absent du bundle/runtime) et ne réapparaît plus après `F5`, l'action en cours affiche le composant unifié `<OrciaSpinner />`, et le message d'erreur ou de timeout s'affiche localisé directement sous la carte/ligne du modèle testé (`[role="alert"]`) sans effacer l'état des autres modèles.

**Given** un environnement comportant `0` document indexé dans `kb_documents` / `kb_chunks` en PostgreSQL 18
**When** l'administrateur consulte `Administration › Modèles IA` (y compris après configuration ou changement du modèle d'embedding)
**Then** le bloc/panneau de réindexation vectorielle reste strictement masqué tant que `0` document indexé existe en base, et n'apparaît que lorsque `>= 1` document indexé nécessite une réindexation.

---

### Story 25.5: Découplage `Mon Assistant` sans Modèle d'Embedding, Blocage Ciblé des Sources RAG (`POST /datasources` + UI) & Clôture Epic 25

As a Utilisateur (`Lucas`, `Hélène`), Architecte (`Winston`) & Tech Lead (`Amelia`),
I want rendre **`Mon Assistant`** immédiatement utilisable dès qu'au moins `1` modèle `chat` actif est configuré — même sans modèle d'`embedding` actif GLOBAL (`AssistantHarness` en mode conversationnel direct + Rôle/Casquette + Glossaire/Ontologie SQL sans interroger `pgvector`, avec indicateur UI non-bloquant signalant l'inactivité de la recherche documentaire) —, appliquer le blocage **`HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL`** dès l'ajout (`POST /datasources`), la synchronisation et l'UI pour toute source RAG (`source_nature != 'SOURCE_CODE'`) tout en préservant les sources `SOURCE_CODE` (GitNexus AST sans embedding), puis clôturer l'Epic 25 avec mise à jour de `capabilities.yaml` et `pnpm site:sync && pnpm site:check`,
So that les utilisateurs puissent échanger avec `Mon Assistant` dès la configuration d'un premier LLM `chat` sans friction artificielle, tout en conservant une frontière matérielle stricte contre toute ingestion RAG dégradée (`AD-8`, `AD-16`, `AD-24` amendés Epic 25).

**Dépendances :** Dépend de `Stories 25.1`..`25.4`. Clôture l'Epic 25.
**CAP couvertes :** `CAP-011`, `CAP-022`, `CAP-074`, `CAP-075`, `CAP-076`, `CAP-180`, `CAP-190` (+ vérification transverse et clôture `capabilities.yaml`).
**Fichiers impactés :** `packages/orcia-core/src/orcia_core/orchestration/assistant_harness.py`, `packages/orcia-core/src/orcia_core/rag/`, `apps/api/src/orcia_api/routers/assistant.py`, `apps/api/src/orcia_api/routers/assistant_llm_bridge.py`, `apps/api/src/orcia_api/routers/workspace_datasources.py`, `apps/web/src/features/assistant/`, `apps/web/src/features/workspaces/sources/`, `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`.
**Rapport Tech Lead :** `docs/implementation-artifacts/tech-lead-reports/25-5-decouplage-assistant-sans-modele-semantique-blocage-sources-rag-et-cloture-epic-25-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** une instance ORCIA disposant d'au moins `1` modèle `chat` actif configuré et de `0` modèle d'`embedding` actif GLOBAL
**When** un utilisateur ouvre `/assistant` et envoie un message à `Mon Assistant`
**Then** la saisie et l'envoi ne sont pas bloqués, `AssistantHarness` répond en streaming SSE réel en exploitant le mode conversationnel direct + Rôle/Casquette + Glossaire/Ontologie SQL (sans appel `pgvector`), et un indicateur UI non-bloquant informe l'utilisateur que la recherche documentaire est inactive tant qu'aucun modèle d'indexation sémantique n'est configuré (avec lien vers `Administration › Modèles IA`).

**Given** une instance ORCIA avec `0` modèle d'`embedding` actif GLOBAL et un utilisateur tentant d'ajouter ou synchroniser une source documentaire RAG (`source_nature != 'SOURCE_CODE'`) vs une source `SOURCE_CODE`
**When** la requête est soumise via l'UI (`Mes Espaces › Documents & Sources`) ou l'API (`POST /api/v1/workspaces/{workspace_id}/datasources` et endpoint de synchronisation)
**Then** l'ajout ou la synchronisation d'une source RAG (`source_nature != 'SOURCE_CODE'`) est explicitement bloqué côté UI (indication claire + redirection vers `Administration › Modèles IA`) et rejeté côté API avec `HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL` (RFC 9457), tandis que l'ajout et la synchronisation d'une source `SOURCE_CODE` (GitNexus AST sans embedding) réussissent et restent persistés en PG18.

**Given** l'ensemble des Stories `25.1`..`25.5` validées à `100 %` vert sur les 5 couches `AD-17`
**When** la clôture de l'Epic 25 met à jour `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml` et exécute `pnpm site:sync && pnpm site:check`
**Then** toutes les vérifications Python (`ruff`, `mypy --strict`, `lint-imports`, `pytest --cov-fail-under=90`), TypeScript (`pnpm turbo run lint typecheck test`), `lint_spine.py` (`0 findings`) et `pnpm site:check` passent sans erreur, et `epic-25` passe à `done`.

---
