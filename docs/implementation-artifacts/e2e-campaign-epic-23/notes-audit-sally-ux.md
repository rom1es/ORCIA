# 🎨 Audit Visuel & UX/UI Exhaustif `23.7-sally` — Campagne E2E Figée Epic 23 (`desktop-cockpit`, `1440×900`)

- **Auditrice** : 🎨 **Sally** — UX Designer & Spécialiste UI Direction C (`bmad-agent-ux-designer`)
- **Branche / Commit figé** : `feat/epic-23-remediation-pg18-sse-direction-c` (`dd2d382` — zéro modification de code applicatif)
- **Périmètre inspecté** : **100 % des `58` captures PNG** générées sous `./screenshots/` (`55` entrées de `manifest.jsonl` couvrant `24` specs = `44` `passed`, `7` `failed`, `1` `timedOut`, `3` `skipped` `mobile-only`, plus `3` captures jalons `milestone-*.png`) en résolution Desktop `1440×900` (et pleines pages `1440×1056..1563`).
- **Référentiels appliqués** :
  - [`DESIGN.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md) (Direction C Sobriété — 4 Zones, tokens sémantiques, 5 piliers UI, 19 composants identitaires)
  - [`EXPERIENCE.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md) (6 règles UX, 3 invariants microcopy zéro jargon, Mobile Companion)
  - [`bilan-execution-tests-e2e-epic-23.md`](./bilan-execution-tests-e2e-epic-23.md) & [`manifest.jsonl`](./manifest.jsonl)
  - Audit précédent : [`notes-audit-sally-ux.md` (Epic 22)](../e2e-campaign-epic-22/notes-audit-sally-ux.md)

---

## 1. Synthèse exécutive & décompte par sévérité (`P0` / `P1` / `P2` / `P3`)

### 1.1 Couverture d'inspection visuelle

| Indicateur | Volume campagne | Inspectés par Sally (`read_file`) | Taux d'inspection |
| --- | ---: | ---: | ---: |
| **Scénarios `passed`** (`18` specs 100 % vertes + succès partiels) | `44` | `44` | **100 %** |
| **Scénarios `failed` + `timedOut`** (`6` specs en échec/timeout) | `8` (`7` failed + `1` timedOut) | `8` | **100 %** |
| **Scénarios `skipped` (`mobile-only`)** | `3` | `3` | **100 %** |
| **Captures jalons (`milestone-*.png`)** | `3` | `3` | **100 %** |
| **Total PNG sur disque** | **`58`** | **`58`** | **`100 %`** |

> **Note factuelle sur `CAP-042` & Mobile Companion (`390×844`)** :
> Conformément à `ACTION_ITEM-23.6` ([`sprint-status.yaml`](../../sprint-status.yaml)) et au [bilan d'exécution](./bilan-execution-tests-e2e-epic-23.md), le projet `--project=mobile-companion` (`390×844`) et la capacité `CAP-042` sont **explicitement reportés hors du périmètre Epic 23** (`3` tests ignorés sur Desktop : `#14`, `#25`, `#27`). Aucune surface authentifiée mobile (barre basse à 3 onglets, contrôle de débordement horizontal sur `/finops`, `/processes`, `/assistant`, redirections Desktop) n'a donc été exécutée ni inspectée visuellement dans cette campagne.

### 1.2 Verdict global Direction C (Epic 22 → Epic 23)

Le bond fonctionnel et visuel entre Epic 22 et Epic 23 est considérable : la suppression de la cascade `resetDay0()` et des erreurs `HTTP 401` a enfin permis d'inspecter les **24 specs complètes** sur Desktop (`44 / 52` scénarios exécutés en `passed`, `84,6 %`), y compris la vue Fokus de revue, les cartes `#6D28D9` / `#D97706`, `Mon Assistant` en streaming SSE, le Studio v2, `Configuration` (6 onglets), `/finops`, `/catalog`, `/ontology`, `/showcase` et `/wizards`.

**Les grandes victoires vérifiées visuellement :**
- **Disparition des fantômes Jour 0 pré-admin** : plus de profil fantôme `AP Administrateur de la ...`, plus de badge `Notifications 4` avant création admin, plus de doublon `Annuler (Esc)` dans la modale Jour 0 (remplacé par un unique `Fermer`), plus de faux masque `••••••••••••••` dans les mots de passe (`OrciaPasswordInput` vide avec œil).
- **Coquille 4 Zones & `/login` Direction C** : le logo `O ORCIA` a réintégré le haut de Zone 1, la `TopHeaderBar` n'a plus de pilule `Espace` dupliquée ni de placeholder tronqué (`Rechercher... (⌘K)`), le splash de session affiche le logo + spinner, et `/login` (`milestone-login-screen-and-password-eye.png`) est propre, sobre et conforme.
- **`Accostage 0/6 → 4/6` & Sobriété Cockpit à vide** : l'échelle unifiée en `6` jalons progresse réellement (`0/6`, `1/6`, `2/6`, `4/6`), et le Cockpit post-admin (`01 #5`, `shell #52`) tient désormais dans **2 cartes** (`<= 3` blocs ✅).
- **`Mon Assistant` épuré & Zone 4 structurée** : disparition des `(0)` sur `Conversations sauvegardées` / `Dossiers`, remplacement d'`embedding` par `Modèle de recherche sémantique requis`, et mise en place des **4 blocs `DESIGN.md`** dans Zone 4 (`À quoi sert cet écran ?`, `EN N GESTES`, encadré ambre `UN EXEMPLE RÉEL`, `CE QUI COINCE SOUVENT`) avec tiroir replié `▸ Détails techniques` et indicateur `Défiler pour voir la suite ↓`.

**En contrepartie, l'inspection des `24` specs met en évidence `17` défauts UX/UI résiduels** répartis ainsi :

| Sévérité | Décompte | Identifiants |
| --- | ---: | --- |
| **`P0` — Bloquant** | **`1`** | `UX23-01` |
| **`P1` — Majeur** | **`9`** | `UX23-02`, `UX23-03`, `UX23-04`, `UX23-05`, `UX23-06`, `UX23-07`, `UX23-08`, `UX23-09`, `UX23-10` |
| **`P2` — Modéré** | **`5`** | `UX23-11`, `UX23-12`, `UX23-13`, `UX23-14`, `UX23-15` |
| **`P3` — Mineur** | **`2`** | `UX23-16`, `UX23-17` |
| **Total écarts `UX23-*`** | **`17`** | *(+ note hors périmètre `CAP-042` / `ACTION_ITEM-23.6`)* |

---

## 2. Tableau consolidé des écarts `UX23-*` (`P0` / `P1` / `P2` / `P3`)

| ID | Sévérité | Composant(s) concerné(s) | Capture(s) PNG exacte(s) | Constat visuel & ergonomique précis | Recommandation UX / UI |
| --- | :---: | --- | --- | --- | --- |
| **`UX23-01`** | **`P0`** | `GatesAdaptiveHumanReviewSection` (`apps/web/src/features/gates/GatesAdaptiveHumanReviewSection.tsx`) | `06-gates-review-and-anti-rubber-stamping/...--failed.png` (`#15`), `19-orchestration-whatif-replay-and-gates/...--failed.png` (`#47`) | Après F5 à froid sur `/gates`, le statut `Point de contrôle : Validé`, le briefing 4 blocs (`Hypothèses relues`) et la Section 1 (`Approuvé`) reviennent, mais **toute la carte / pastille de suivi d'action externe Jira (`EXECUTED`) disparaît de l'écran et du DOM** : l'utilisateur n'a plus aucune preuve visuelle d'exécution post-validation. | Réhydrater l'état et la carte d'action Jira échelonnée depuis PostgreSQL via `GET` au montage de `/gates` et l'afficher de façon persistante sous `Validation Section par Section`. |
| **`UX23-02`** | **`P1`** | `UserSettingsModalDialog`, `UserSettingsMcpTokensTab` (`packages/ui/src/primitives/UserSettingsModalDialog.tsx`, `UserSettingsMcpTokensTab.tsx`) | `14-auth-2fa-account-and-profile/...--popup-mon-compte-parametres-5-onglets...--passed.png` (`#30`), `16-ai-models-reindex-connectors-and-broker/...--connecteur-socle-secret-write-only...--passed.png` (`#36`) | Dans la modale `Paramètres du compte`, la barre verticale des 5 onglets (`Général` à `Clés IDE & MCP`) laisse un **grand vide blanc inutile à sa droite** car le contenu de l'onglet actif démarre *en dessous* du menu au lieu d'être côte à côte en 2 colonnes. Cela tasse la liste des clés (`VSCode E2E`) et le bouton rouge **`Révoquer`** tout en bas contre la bordure inférieure (coupure imminente dès 2 clés). | Passer le corps de `UserSettingsModalDialog` en grille/flex 2 colonnes (`200px` navigation latérale gauche + `1fr` contenu scrollable à droite) pour récupérer ~220 px verticaux et dégager le bouton `Révoquer`. |
| **`UX23-03`** | **`P1`** | `AgentDetailAndSandboxModal`, `AgentSixBlocksKnowledgeToolsGuardrailsSections` (`packages/ui/src/components/AgentDetailAndSandboxModal.tsx`, `AgentSixBlocksKnowledgeToolsGuardrailsSections.tsx`) | `08-agents-skills-persistence/...--un-agent-configure-sur-les-6-blocs...--passed.png` (`#17`) | La modale `⚙ Agent E2E Conformité` occupe quasiment toute la hauteur (`900px`) : l'en-tête **`■ Bloc E — Boîte à Outils (Toolbox MCP) & Compétences (Skills)`** est **coupé horizontalement sous la barre sticky supérieure**, le slug **`@agent-e2e-conformit`** est tronqué à 19 caractères, et `Banc de Test Intégré` + `⚡ ▶ Exécuter l'Agent` touchent le bord bas sans pied de modale fixe pour enregistrer. | Ajouter du `padding-top` sous le header sticky de la modale, contraindre `max-h-[82vh]` avec zone scrollable interne dédiée et pied sticky fixe pour l'enregistrement, et ne pas tronquer le `@slug` dans le badge. |
| **`UX23-04`** | **`P1`** | `FinopsGovernanceDashboardView` (`packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx`) | `12-finops-and-audit-provenance/...--bureau-activity-et-finops-etat-vide...--passed.png` (`#24`) | Sur `/finops` à l'état vide, l'onglet sélectionné **`Par Modèle et Niveau d'effort`** affiche un **texte bleu moyen sur fond bleu pastel/moyen** (ratio visuel `< 3:1`, quasiment illisible — non conforme WCAG 2.2 AA), alors qu'en `13 #26` l'onglet actif `Maîtrise humaine et Qualité` utilise bien le fond `#2563EB` avec texte `#FFFFFF`. | Aligner l'état actif/désactivé des onglets `/finops` à vide sur le jeton `#2563EB` / `#FFFFFF` (`>= 4,5:1`) ou un état désactivé clairement différencié et lisible. |
| **`UX23-05`** | **`P1`** | `TopHeaderSearchCommand`, `TopHeaderSearchResultsPane` (`packages/ui/src/primitives/TopHeaderSearchCommand.tsx`, `TopHeaderSearchResultsPane.tsx`) & `docs/help/en/` | `10-command-palette-search/...--la-recherche-federee-vitesse-2-aboutit-cote-api--passed.png` (`#20`) | Dans la palette `⌘K`, chaque résultat d'aide affiche un bouton bleu `#2563EB` contenant l'émoji rouge **`❓`** (`Ouvrir ❓ Aide`) au **contraste rouge-sur-bleu très faible**, en rupture avec les icônes filaires du design system. De plus, les résultats mélangent la fiche française (`Catalogue Fédéré...`) et son **doublon anglais** (`Federated Catalog: resources, versions, and reuse`). | Remplacer l'émoji rouge `❓` par une icône SVG filaire blanche (`OrciaIcon`) héritant de `currentColor`, et filtrer les résultats de recherche `HelpArticle` selon la langue active (`fr` / `en`). |
| **`UX23-06`** | **`P1`** | `WorkspaceDnaAndWaiversSection`, `WorkspaceStudioCardsAndDetailView` (`apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, `WorkspaceStudioCardsAndDetailView.tsx`) | `11-screens-smoke-without-server-errors/...--chaque-ecran-authentifie-se-charge-au-jour-0...--passed.png` (`#21`) | Sur `/spaces` au Jour 0 (`0` espace créé), sous l'état vide *"Aucun Espace de Travail ne correspond à ce filtre..."*, **tout un panneau fantôme s'affiche néanmoins** avec le slug technique **`default-ws`**, la ligne `Emplacement d'enregistrement des livrables :: orcia://workspaces/default-ws/artifacts` et les 5 sous-onglets (`1. Vue d'ensemble`..`5. Membres & Équipe`). | Masquer intégralement le panneau de détail d'espace (`WorkspaceDetailTabsPanel` / `WorkspaceDnaAndWaiversSection`) tant qu'aucun espace réel n'existe ou n'est sélectionné (zéro repli `default-ws`). |
| **`UX23-07`** | **`P1`** | `ProgressiveDay0AccostageBanner`, `PlatformOnboardingChecklistCard` (`packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx`, `apps/web/src/features/cockpit/PlatformOnboardingChecklistCard.tsx`) | `14-auth-2fa-account-and-profile/...--mot-de-passe-temporaire-d-un-compte-invite...--passed.png` (`#29`), `15-organization-iam-secops-inbox-and-observer/...--bu-equipe-invitation-scopee...--passed.png` (`#31`) | Connecté en tant que **`Claire Invitée` (`Contributeur`)** ou **`Marc Lead BU` (`Responsable de Direction (BU)`)**, la carte `Étape 1 : Compte Administrateur de la plateforme` affiche **`Administrateur de plateforme initialisé ✓ Claire Invitée`** (ou `Marc Lead BU`), attribuant le titre d'administrateur au collaborateur connecté ; de plus, l'étape `2. Connexion des Modèles IA` reste affichée à des rôles sans droit d'administration. | Afficher le vrai nom de l'administrateur plateforme (ou un libellé générique sans nom personnel trompeur) et adapter les étapes d'accostage Cockpit aux droits réels du rôle connecté. |
| **`UX23-08`** | **`P1`** | `AiModelReindexPanel`, `ArbitrationTieBreakCard`, `CockpitUpstreamChallengePanel`, `RemoteServiceTestBenchAndMcpExposureView`, `PermissionBrokerCard`, `GatesAdaptiveHumanReviewSection`, `InboxNotificationsCenterView`, `CatalogExplorerPanel`, `WorkflowStudioSection` | `03 milestone-human-led-anchor-violet.png`, `03 milestone-arbitration-tiebreak-amber.png`, `06 #15`, `15 #34`, `16 #35`, `16 #37`, `18 #41`, `18 #45`, `19 #47` | **Fuites d'architecture, enums bruts, Markdown non rendu et métriques NFR en UI** :<br>- `/settings?tab=models` (`16 #35`) : **`(AD-24.7)`**, **`COMPLETED (100%)`**.<br>- `/cockpit` (`03` jalons) : **`PENDING`**, **`RUNNING`**, **`PAUSE_AND_ESCALATE`**, **`(OPT_A_SPOT_15M)`**, **`(OPT_B_LOCK_48H)`**, `frame-architecture-intent`, `PM_BUSINESS`, `axiom-l1-strategic-asset-immutable-schema`.<br>- `/agents` (`18 #45`) : **`1_NETWORK_TLS_ANTI_SSRF`**, **`2_AUTHENTICATION`**, **`3_CONTRACT_DISCOVERY`**, **`4_HOT_DRY_RUN`**, **`PASS`**.<br>- `/assistant` (`16 #37`) : Markdown brut (`###`, `` ` ``, `**`), **`HTTP 403`**, `(Step 1 • fetch_repo)`, URI URL-encodée `jira://IAM/...%3A%2F%2F...`.<br>- `/gates` (`06 #15`, `19 #47`) : **`Garde-fou < 15 s`**, `step-architecture-gate`, **`persistance PostgreSQL 18`**, `PASS de la Gate`.<br>- `/inbox` (`15 #34`) : `'inbox-review-step'`, **`Synchronisation : 0.5 ms`**.<br>- `/catalog` (`18 #41`) : encadré pointillé avec **`0`** nu, **`depth=0 :`**, **`depth=1 :`**. | Traduire 100 % des enums/statuts en français métier via les dictionnaires `i18n`, purger `(AD-24.7)`, `PostgreSQL 18`, `< 15 s`, `0.5 ms` et `depth=*`, passer les conseils du `PermissionBrokerCard` dans `FormattedMarkdownContent`, et afficher une phrase d'état vide lisible à la place du `0` isolé sur `/catalog`. |
| **`UX23-09`** | **`P1`** | `ShellContainer`, `ShellContextualHelpColumn`, `FourZoneDirectionCShell` (`apps/web/src/components/ShellContainer.tsx`, `ShellContextualHelpColumn.tsx`, `packages/ui/src/primitives/FourZoneDirectionCShell.tsx`) | `15-organization-iam-secops-inbox-and-observer/...--centre-de-notifications...--passed.png` (`#34`), `21-assistant-citations-v5-audit-help-showcase/...--centre-d-aide-contextuelle...--passed.png` (`#51`), `15-...--mode-observateur...--passed.png` (`#33`) | **Désynchronisation navigation / fil d'Ariane / Zone 4** :<br>- Sur `/inbox` (`15 #34`), le fil d'Ariane affiche **`ORCIA > Mon Assistant > Décisions`**, la Sidebar active **`Mon Assistant`**, et Zone 4 charge la fiche d'aide **`Mon Assistant`** au lieu d'une fiche Boîte de Réception.<br>- Sur `/showcase` (`21 #51`), le fil dit `ORCIA > Aide > Présentation ORCIA`, mais la Sidebar surligne **`Cockpit`** au lieu d'`Aide`.<br>- Sur `/organization` (`15 #33` observateur), le fil indique `ORCIA > Configuration > Mon Organisation` alors que `Configuration` est absente de la Sidebar.<br>- Globalement, le segment `[Espace]` manque dans le fil d'Ariane `TopHeaderBar` (`DESIGN.md` §2.1). | Aligner le routeur de Zone 4 et la surbrillance Sidebar sur les routes `/inbox` et `/showcase`, rattacher `/organization` en mode lecture sous un chemin cohérent hors menu masqué, et injecter l'Espace actif dans le fil d'Ariane quand un espace est sélectionné. |
| **`UX23-10`** | **`P1`** | `PacksRegistryPage` (`apps/web/src/features/settings/packs/PacksRegistryPage.tsx`), `WorkspaceStudioCardsAndDetailView` | `18-catalog-packs-wizards-and-mcp-bench/...--registre-des-packs-declaratifs...--passed.png` (`#43`), `17-workspace-sources...--rattachement-source-code...--passed.png` (`#38`) | Dans `/settings/packs` (`18 #43`), la 2e mini-carte KPI de `Pack Ingénierie Logicielle & SDLC` coupe brutalement le mot `Compétences` en **`4 Compéte`** contre sa bordure droite. En outre, les singulars prennent un `s` fautif (`1 Chaînes`, `1 Agents`, `1 Compétences`, `1 Validations` sur `#43` ; `1 Sources rattachées` sur `#38`), et les connecteurs/agents exposent des noms bruts (`mcp:atlassian-jira (read, write_preview)`, `crl-etude-archi`). | Élargir la grille des 5 mini-compteurs (`grid-cols-2 sm:grid-cols-3` ou padding réduit + texte `Compétences` non tronqué), corriger la pluralisation `n <= 1`, et afficher des libellés métiers pour les connecteurs et agents. |
| **`UX23-11`** | **`P2`** | `StudioCopilotSidebar`, `WorkspaceStudioCardsAndDetailView`, `IamSecopsExceptionForm` (`apps/web/src/features/processes/studio/StudioCopilotSidebar.tsx`, `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx`, `apps/web/src/features/admin/iam/IamSecopsExceptionForm.tsx`) | `09 #18`, `20 #48`, `20 #49` (`/processes/studio/...`) ; `07 #16`, `11 #21`, `17 #38`, `17 #40` (`/spaces`) ; `15 #32` (`/settings?tab=iam`) | **Troncatures de champs et sélecteurs à `1440×900`** :<br>- Studio (`09 #18`, `20 #48/#49`) : placeholder **`Ex : Ajouter un contrôle de p`** coupé net dans l'input à côté de `Demander`.<br>- Espaces (`07 #16`, `11 #21`, `17 #38/#40`) : placeholder **`Rechercher un espace ou une équ`** coupé net dans la barre de filtre.<br>- IAM SecOps (`15 #32`) : libellé **`Plateforme entière (toutes les directi`** coupé dans le `<select>` `Périmètre cible (« Sur quoi ? »)`. | Raccourcir les placeholders (`Ex : Ajouter un contrôle...`, `Rechercher un espace...`) ou donner une largeur minimale suffisante (`min-w`) / empiler `input` + bouton dans le panneau latéral du Studio et élargir les colonnes de formulaire IAM. |
| **`UX23-12`** | **`P2`** | `docs/help/fr/agents.md`, `docs/help/fr/ontology.md` / `ShellContextualHelpColumn` | `08 #17`, `18 #45` (`/agents`), `17 #39` (`/ontology`) | Sur `/agents`, l'encadré ambre `UN EXEMPLE RÉEL` de Zone 4 affiche un **backtick littéral** non formaté : ``puis l'appelle directement depuis Mon Assistant via `@`.`` Sur `/ontology` (`17 #39`), le titre de la fiche d'aide affiche **`promotions L4 → L1`**, jargon d'architecture interne peu lisible pour un utilisateur métier. | Remplacer `` `@` `` par `« @ »` (ou `<code>@</code>`) dans `docs/help/fr/agents.md` (et vérifier tous les `.md` d'aide), et reformuler `promotions L4 → L1` en `de l'Espace à l'Entreprise`. |
| **`UX23-13`** | **`P2`** | `FourZoneDirectionCShell` (`packages/ui/src/primitives/FourZoneDirectionCShell.tsx`) | `01 #5`, `10 #19`, `10 #20`, `11 #22`, `15 #31`, `16 #37`, `18 #43`, `shell #52`, `shell #54` (`1440×1056` à `1440×1563`) | Sur les 9 captures dépassant `900 px` de hauteur (`fullPage`), Zone 1 (Sidebar) et Zone 4 (Aide) s'interrompent net à `y = 900 px` et Zone 3 tronque son bloc inférieur (`Accès rapides` sur Cockpit, `Processus du Pack ORCIA` sur `/settings/packs`), tandis qu'une **zone vide `#EAF2FB` de `156` à `663 px` de haut** s'étend inutilement sous `y = 900 px`. | Corriger le modèle de hauteur/overflow du conteneur racine de `FourZoneDirectionCShell` (`h-screen overflow-hidden` sur le shell vs `min-h-screen` d'un wrapper interne) afin d'éviter le double contexte de scroll / hauteur fantôme. |
| **`UX23-14`** | **`P2`** | `FinopsKpiStrip`, `StreamlinedCockpitView` (`packages/ui/src/primitives/finops/FinopsKpiStrip.tsx`, `packages/ui/src/primitives/StreamlinedCockpitView.tsx`) | `13 #26` (`/finops`), `03 #10`, `03 milestone-human-led-anchor-violet.png`, `19 #46` (`/cockpit`) | Sur `/finops` (`13 #26`), les 4 cartes KPI (`COÛT CONSOLIDÉ`..`ÉCONOMIES`) sont **empilées verticalement en 1 colonne pleine largeur**, repoussant les 4 onglets tout en bas (`~850–900 px`) et cachant le contenu de l'onglet actif sous le pli. Sur `/cockpit` en activité (`03 #10`, `19 #46`), le `Guide de Démarrage` reste déployé en pleine hauteur au-dessus des compteurs et décisions, repoussant et coupant à moitié le CTA **`Ouvrir l'atelier de relecture →`** au bord `900 px`. | Disposer les 4 KPIs de `FinopsKpiStrip` en grille `grid-cols-2 xl:grid-cols-4`, et replier/compacter automatiquement la carte d'accostage Cockpit sur 1 ligne dès qu'une décision active ou un run est présent. |
| **`UX23-15`** | **`P2`** | `FourZoneSidebarRail`, `FirstBootAdminSetupModal`, `admin/index.tsx`, `SettingsPacksSection`, `WorkspaceStudioCardsAndDetailView` | `00 #2`, `01 #6`, `shell #53`, `shell #55` (Jour 0) ; `14 #28`, `15 #32`, `18 #42` (`/settings`) ; `07 #16`, `17 #38` (`/spaces`) | **Incohérences structurelles mineures de coquille et sous-navigation** :<br>- Au Jour 0 pré-admin, **`Mes Espaces`** reste active/noire dans Zone 1 alors que `Mon Assistant`, `Mes Processus`, `Mes Agents` et `FinOps` sont grisés, et la modale obligatoire de création admin expose un bouton **`Fermer`** ambigu.<br>- Sur `/settings`, le 6e onglet **`Mon Organisation`** passe seul à la 2e ligne ; dans `Packs Métiers` (`18 #42`), le pack actif est affiché deux fois (grille + ligne du bas).<br>- Sur `/spaces`, un 2e fil d'Ariane interne redouble celui de la `TopHeaderBar`. | Griser uniformément `Mes Espaces` avant création admin et clarifier l'absence de fermeture (ou verrouillage explicite) sur la modale Jour 0 ; ajuster l'espacement des 6 onglets `/settings` sur 1 rangée ; supprimer le récapitulatif redondant des packs actifs et le 2e fil d'Ariane interne de `/spaces`. |
| **`UX23-16`** | **`P3`** | `apps/web/src/features/ontology/index.tsx`, `OrciaProductShowcaseSiteView`, `DurableWizardRunnerView`, `AiModelsMasterTable`, `WorkspaceStudioCardsAndDetailView`, cassette LLM | `17 #39` (`/ontology`), `21 #51` (`/showcase`), `18 #44` (`/wizards`), `02 #7` (`/assistant`), `16 #35` (`/settings?tab=models`), `07 #16` (`/spaces`) | **Polissage textuel & microcopy** :<br>- `/ontology` (`17 #39`) : option `<select>` `Organisation (Global) · Organisation (Global)` dupliquée.<br>- `/showcase` (`21 #51`) : texte annonce `3 espaces strictement séparés` face à **`4` onglets** en dessous, et bouton exposant `(docs/site-catalog/index.html)`.<br>- `/wizards` (`18 #44`) : libellé bouton `Créer un espace d'exemple prêt à l'emploi` vs aide `« Provisionner un espace de démonstration »`.<br>- `/spaces` (`07 #16`, `11 #21`) : double espace visible dans le badge `Mes  Espaces`.<br>- `/settings?tab=models` (`16 #35`) : `4 tiers cognitifs` (anglicisme vs `paliers`).<br>- `/assistant` (`02 #7`) : réponse cassette démarrant par une minuscule (`synthèse conforme pour...`). | Dédupliquer le libellé d'option `/ontology`, aligner `4` espaces sur `/showcase` sans chemin technique, harmoniser `/wizards` et Zone 4, corriger l'espace double `Mes Espaces` et employer `paliers`. |
| **`UX23-17`** | **`P3`** | Couverture captures E2E finales (`00`, `04`, `07`, `17`, `20`) | `00 #3`, `00 #4`, `04 #12`, `07 #16`, `17 #40`, `20 #48`, `20 #49` | - `00 #3`, `00 #4` et `04 #12` capturent l'écran de chargement `Chargement de la session...` (qui affiche désormais proprement le logo `O ORCIA` et un spinner ✅, mais ne montre pas de surface métier).<br>- Dans `07 #16`, le test échoue car `getByText('Espace E2E Comptabilité').first()` cible l'`<option>` cachée du `<select>` de Zone 1 alors que la carte est bien visible.<br>- Dans `20 #48`, la capture finale reste sur le Studio et ne montre ni la carte VSM 11 étapes ni le tiroir HITL ; dans `17 #40`, le bas de page (dérogations / graphe tripartite) n'est pas visible dans la capture. | Ajouter des captures jalons (`milestone-*.png`) sur la carte VSM 11 étapes, le tiroir HITL et le graphe tripartite ; scoper les locators E2E sur `<main>` plutôt que `.first()` global. |

---

## 3. Fiches détaillées écran par écran (`00`–`21` + `shell.spec.ts`)

### 3.1 Specs `00` & `01` — Smoke Stack, Splash Session & Amorçage Jour 0 (`#1`–`#6`)
- **Captures inspectées (`6 / 6`)** :
  - `00-stack-smoke/...--l-api-fastapi-repond...--passed.png` (`#1`, `1440×900`, `/cockpit`)
  - `00-stack-smoke/...--apres-reset-jour-0...--passed.png` (`#2`, `1440×900`, `/`)
  - `00-stack-smoke/...--story-16-1...--passed.png` (`#3`, `1440×900`, `/cockpit`)
  - `00-stack-smoke/...--story-16-2...--passed.png` (`#4`, `1440×900`, `/cockpit`)
  - `01-day0-boot-and-f5-persistence/...--le-premier-administrateur-cree-survit-a-un-f5...--passed.png` (`#5`, `1440×1487`, `/`)
  - `01-day0-boot-and-f5-persistence/...--apres-reset-jour-0...--passed.png` (`#6`, `1440×900`, `/`)
- **Progrès validés** :
  - Écran de transition `#3` & `#4` enrichi avec logo `O ORCIA` + spinner `Chargement de la session...` (fini le texte nu Epic 22).
  - Modale Jour 0 (`#1`, `#2`, `#6`) : disparition complète de `AP Administrateur de la ...`, de `Notifications 4`, du doublon `Annuler (Esc)` (remplacé par un seul `Fermer`) et du faux masque `••••••••••••••` (champs vides avec œil `OrciaPasswordInput`).
  - Cockpit post-admin (`#5`) : **2 blocs principaux** (`<= 3` ✅), `Accostage 1/6` cohérent avec `Étape 1 ✓ Alice Admin E2E`, 6 jalons lisibles sans troncature, `TopHeaderBar` épurée (`ORCIA > Cockpit`, `Rechercher... (⌘K)` entier), Zone 4 dotée des 4 blocs `DESIGN.md` et de l'accordéon `▸ Détails techniques`.
- **Écarts relevés** : `UX23-13` (bande vide `#EAF2FB` sous `y = 900px` sur `#5` `1440×1487` coupant le bas des 3 tuiles d'accès rapides et de Zone 4), `UX23-15` (`Mes Espaces` non grisée en pré-admin et bouton `Fermer` ambigu sur modale Jour 0), `UX23-17` (`#3`, `#4` sur splash).

### 3.2 Spec `02` — `Mon Assistant` (Streaming SSE & Dossiers) (`#7`–`#9`)
- **Captures inspectées (`3 / 3`)** :
  - `02-assistant-streaming-and-folders/...--un-tour-d-assistant...--passed.png` (`#7`, `1440×900`, `/assistant`)
  - `02-assistant-streaming-and-folders/...--un-dossier-cree-dans-un-espace...--passed.png` (`#8`, `1440×900`, `/assistant`)
  - `02-assistant-streaming-and-folders/...--un-dossier-survit-au-redemarrage...--passed.png` (`#9`, `1440×900`, `/assistant`)
- **Progrès validés** :
  - Disparition totale de la fausse alerte `HTTP 401` (`#7` passe avec flux SSE réel, `Réflexion pendant 0s >`, réponse + barre d'actions sous la réponse).
  - En-tête épuré sans `(0)` (`Conversations sauvegardées`, `Dossiers`, `Dossiers (1)`).
  - Zone 4 fidèle à `/assistant` (`Mon Assistant : questions, dossiers et citations vérifiées`, mention alignée sur `Polyvalent · Standard`).
  - Remplacement de `embedding` par `Modèle de recherche sémantique requis` (`#8`, `#9`).
- **Écarts relevés** : `UX23-16` (cassette démarrant par une minuscule `synthèse conforme pour...` en `#7`), et léger décalage de contexte en `#9` où le sélecteur gauche indique `Tous les espaces` alors que `Dossier E2E PostgreSQL` est actif en bas (carte inférieure touchant le bord bas `900px`).

### 3.3 Spec `03` — Gouvernance Human-Led : Ancrage Violet, Rewind & Arbitrage Ambre (`#10` + `2` jalons)
- **Captures inspectées (`3 / 3`)** :
  - `03-human-led-anchor-and-arbitration/...--milestone-human-led-anchor-violet.png` (`1440×900`, `/cockpit`)
  - `03-human-led-anchor-and-arbitration/...--milestone-arbitration-tiebreak-amber.png` (`1440×900`, `/cockpit`)
  - `03-human-led-anchor-and-arbitration/...--survie-au-f5--passed.png` (`#10`, `1440×900`, `/cockpit`)
- **Progrès validés** :
  - Les 2 jalons montrent nettement la différenciation chromatique Direction C : carte **`✍️ RÉDACTION PERSONNELLE OBLIGATOIRE`** en Violet `#6D28D9` / fond `#F5F3FF` avec compteur `(0/30)` et zéro bouton IA ; carte **`⚖️ ARBITRAGE REQUIS`** en Ambre `#D97706` / fond `#FFFBEB` avec Option A recommandée vs Option B, coûts estimés et champ de justification.
  - En `#10`, `Accostage 4/6` reflète fidèlement les 4 jalons accomplis.
- **Écarts relevés** :
  - `UX23-08` (**P1**, fort impact) : badges `PENDING` / `RUNNING`, `Règle de départage: PAUSE_AND_ESCALATE`, boutons `Retenir cette option (OPT_A_SPOT_15M)` / `(OPT_B_LOCK_48H)`, et fuite de slugs techniques (`frame-architecture-intent`, `delegate-remediation-subworkflow`, `axiom-l1-strategic-asset-immutable-schema`, `PM_BUSINESS`) dans la carte de challenge amont.
  - `UX23-14` (**P2**) : empilement Cockpit en phase d'exécution active (`#10`) qui coupe à moitié le bouton `Ouvrir l'atelier de relecture →` à `y = 900px`.

### 3.4 Spec `04` — Multi-acteurs `Claim` & Diffusion SSE (`#11`–`#12`)
- **Captures inspectées (`2 / 2`)** :
  - `04-multi-actor-claim-sse/...--a-prend-en-charge-une-tache...--passed.png` (`#11`, `1440×900`, `/cockpit` — rendue sur `/login` pour le 2e acteur/contexte)
  - `04-multi-actor-claim-sse/...--le-flux-sse-d-un-acteur-connecte...--passed.png` (`#12`, `1440×900`, `/cockpit` — splash `Chargement de la session...`)
- **Constat** : `/login` (`#11`) propre avec logo `O ORCIA` et œil mot de passe ; `#12` capture le splash de chargement (`UX23-17`).

### 3.5 Spec `05` — Garde `isDirty` Escape & Mobile Companion (`#13`–`#14`)
- **Captures inspectées (`2 / 2`)** :
  - `05-mobile-companion-and-rgaa/...--escape-sur-un-formulaire-modifie...--passed.png` (`#13`, `1440×900`, `/`)
  - `05-mobile-companion-and-rgaa/...--aucun-debordement-horizontal-sur-mobile...--skipped.png` (`#14`, `1440×900`, `/cockpit` — splash)
- **Constat** : `#13` démontre un excellent encart d'alerte ambre RGAA dans la modale Jour 0 (`⚠ Modifications non enregistrées` + `Continuer l'édition` / `Quitter sans enregistrer` rouge `#DC2626`) ; `#14` est `skipped` (`ACTION_ITEM-23.6` / `CAP-042`).

### 3.6 Spec `06` & `19` — Gates, Briefing 4 Blocs, Anti-Rubber-Stamping & Actions Jira (`#15`, `#46`, `#47`)
- **Captures inspectées (`3 / 3`)** :
  - `06-gates-review-and-anti-rubber-stamping/...--failed.png` (`#15`, `1440×900`, `/gates`)
  - `19-orchestration-whatif-replay-and-gates/...--instanciation-depuis-le-cockpit...--passed.png` (`#46`, `1440×900`, `/cockpit`)
  - `19-orchestration-whatif-replay-and-gates/...--validation-deterministe-sandbox...--failed.png` (`#47`, `1440×900`, `/gates`)
- **Progrès validés** : La grille `Synthèse de Relecture avant Validation (4 Points Clés)` (`1. Résumé Exécutif`, `2. Points Clés & Vérifications Croisées`, `3. Décisions Proposées`, `4. Hypothèses Retenues`) + pastille verte `✓ Hypothèses relues` + `Validation Section par Section` (`Alt + ↑ / ↓`, `Section 1 Approuvé`) sont propres, aérées et lisibles.
- **Écarts relevés** :
  - **`UX23-01` (`P0`)** sur `#15` et `#47` : disparition visuelle et DOM de l'état/badge `EXECUTED` de l'action Jira après F5 à froid.
  - **`UX23-08` (`P1`)** : titre exposant `(Briefing 4 Blocs, Découpage & Garde-fou < 15 s)`, `step-architecture-gate`, `persistance PostgreSQL 18`, `PASS de la Gate`.
  - **`UX23-14` (`P2`)** sur `#46` : même rognage du bouton `Ouvrir l'atelier de relecture →` à `y = 900px` sur `/cockpit`.

### 3.7 Spec `07` — Espaces, Organisation & Persistance F5 (`#16`)
- **Capture inspectée (`1 / 1`)** :
  - `07-spaces-org-and-workspace-persistence/...--failed.png` (`#16`, `1440×900`, `/spaces`)
- **Constat** : La carte `Espace E2E Comptabilité` (`Équipe de facturation : Equipe E2E`, sélecteurs `Phase : Construction`, `Collectif d'équipe`, bouton primaire `Travailler dans cet Espace`) est bien affichée et lisible dans `<main>`, confirmant visuellement que l'échec E2E vient d'un sélecteur Playwright ambigu (`UX23-17`).
- **Écarts relevés** : `UX23-11` (placeholder `Rechercher un espace ou une équ` tronqué), `UX23-15` (double fil d'Ariane interne), `UX23-16` (double espace `Mes  Espaces`).

### 3.8 Spec `08` — Agents en 6 Blocs & Skills (`#17`)
- **Capture inspectée (`1 / 1`)** :
  - `08-agents-skills-persistence/...--passed.png` (`#17`, `1440×900`, `/agents`)
- **Constat** : Formulaire riche (outils lecture seule vs `Écrire (Write-Preview)`, règles de sécurité, banc de test intégré `Conditions réunies : 6/6`).
- **Écarts relevés** : **`UX23-03` (`P1`)** (titre `■ Bloc E...` coupé sous le header de la modale, `@agent-e2e-conformit` tronqué, modale pleine hauteur sans bouton de sauvegarde visible en bas), `UX23-12` (backtick `` `@` `` dans Zone 4).

### 3.9 Spec `09` & `20` — Process Studio v2, Chaîne de valeur VSM, Autonomie & FinOps (`#18`, `#48`, `#49`)
- **Captures inspectées (`3 / 3`)** :
  - `09-pack-builder-and-contextual-help/...--passed.png` (`#18`, `1440×900`, `/processes/studio/wf-01-qualification-prd`)
  - `20-process-studio-v2-finops-and-log-sink/...--catalogue-agents-avec-pont-assistant...--failed.png` (`#48`, `1440×900`, `/processes/studio/wf-01-qualification-prd`)
  - `20-process-studio-v2-finops-and-log-sink/...--contrat-d-autonomie...--failed.png` (`#49`, `1440×900`, `/processes/studio/wf-01-qualification-prd`)
- **Progrès validés** : Le Studio v2 est visuellement clair et hiérarchisé : barre supérieure `← Retour à Mes Processus`, `Voir l'Étape 01 dans la chaîne de valeur`, badge `En préparation · v1.0.0-draft` / `Actif · v1.0.1`, badge cyan **`Autonomie signée`** (respect strict d'`UX-DR17` : pas de violet sur l'autonomie ✅), sélecteur `Processus piloté par l'objectif` vs `par les jalons`, et bannière verte `Déclencheur enregistré et activé pour ce processus.` en `#49`.
- **Écarts relevés** : `UX23-11` (`Ex : Ajouter un contrôle de p` tronqué dans `StudioCopilotSidebar` sur les 3 captures), `demande_source` snake_case sur `#18`/`#48` (corrigé en `Demande initiale` sur `#49`), `UX23-17` (capture finale de `#48` ne montre pas VSM 11 étapes ni tiroir HITL).

### 3.10 Spec `10` — Palette de Recherche Fédérée `⌘K` (`#19`–`#20`)
- **Captures inspectées (`2 / 2`)** :
  - `10-command-palette-search/...--ctrl-k-ouvre-la-palette...--passed.png` (`#19`, `1440×1487`, `/cockpit`)
  - `10-command-palette-search/...--la-recherche-federee-vitesse-2...--passed.png` (`#20`, `1440×1487`, `/cockpit`)
- **Progrès validés** : La palette flottante est bien centrée, claire (`🔍`, 3 pilules `📍 Cet écran` / `📦 Cet Espace` / `🌐 Tous mes Espaces`, section `PASSAGES PROCHES PAR LE SENS`, barre raccourcis `Tab / ↵ / ⌘↵` et lien de secours `💬 Poser la question « agents » à Mon Assistant →`).
- **Écarts relevés** : **`UX23-05` (`P1`)** (bouton `Ouvrir ❓ Aide` rouge-sur-bleu + doublon anglais `Federated Catalog...` dans la liste FR) et `UX23-13` (fond vide sous `900px` sur `1440×1487`).

### 3.11 Spec `11` — Smoke des écrans sans erreur & Mire `/login` (`#21`–`#22` + jalon)
- **Captures inspectées (`3 / 3`)** :
  - `11-screens-smoke-without-server-errors/...--chaque-ecran-authentifie...--passed.png` (`#21`, `1440×900`, `/spaces`)
  - `11-screens-smoke-without-server-errors/...--la-mire-login...--passed.png` (`#22`, `1440×1487`, `/`)
  - `11-screens-smoke-without-server-errors/...--milestone-login-screen-and-password-eye.png` (`1440×900`, `/login`)
- **Progrès validés** : La mire `/login` est irréprochable (`O ORCIA`, `Connexion à ORCIA`, champs sans masque pré-rempli, icône œil `OrciaPasswordInput`, bouton plein largeur `#2563EB`).
- **Écarts relevés** : **`UX23-06` (`P1`)** (panneau fantôme `default-ws` visible sous l'état vide de `/spaces` en `#21`), `UX23-11` (`Rechercher un espace ou une équ`), `UX23-13` (`1440×1487` en `#22`).

### 3.12 Spec `12` (`epic16`) — Trace Réflexive & Inspecteur Chirurgical (`#23`)
- **Capture inspectée (`1 / 1`)** :
  - `12-epic16-reflexive-trace-and-line-inspector/...--passed.png` (`#23`, `1440×900`, `/processes`)
- **Constat** : Rendu très propre et pédagogique de la trace réflexive (`Délégation à @analyste-metier`, `Préparation de l'aperçu d'écriture gouvernée`, `Consolidation du livrable final`, pastille `[S1] docs/product/capabilities.yaml #L1-35` en monospace, `Zone 4` synchronisée sur `/processes`). Aucun écart critique relevé.

### 3.13 Spec `12` (`finops`) & `13` (`epic-7`) — Gouvernance FinOps & Autonomie (`#24`–`#27`)
- **Captures inspectées (`4 / 4`)** :
  - `12-finops-and-audit-provenance/...--bureau-activity-et-finops...--passed.png` (`#24`, `1440×900`, `/finops`)
  - `12-finops-and-audit-provenance/...--mobile-finops...--skipped.png` (`#25`, `1440×900`, `/cockpit` — splash)
  - `13-epic-7-autonomous-governance-and-supervision/...--bureau-publication-v2...--passed.png` (`#26`, `1440×900`, `/finops`)
  - `13-epic-7-autonomous-governance-and-supervision/...--mobile-processes...--skipped.png` (`#27`, `1440×900`, `/cockpit` — splash)
- **Écarts relevés** : **`UX23-04` (`P1`)** (contraste illisible de l'onglet actif `Par Modèle et Niveau d'effort` à vide en `#24`), **`UX23-14` (`P2`)** (empilement vertical des 4 KPIs en `#26` repoussant les onglets tout en bas du viewport), et position flottante du bouton `Journal d'Activité →` au-dessus du titre `h1`.

### 3.14 Spec `14` — Authentification, 2FA, Mot de passe temporaire & `Paramètres du compte` (`#28`–`#30`)
- **Captures inspectées (`3 / 3`)** :
  - `14-auth-2fa-account-and-profile/...--politique-d-authentification...--passed.png` (`#28`, `1440×900`, `/settings`)
  - `14-auth-2fa-account-and-profile/...--mot-de-passe-temporaire...--passed.png` (`#29`, `1440×900`, `/`)
  - `14-auth-2fa-account-and-profile/...--popup-mon-compte-parametres...--passed.png` (`#30`, `1440×900`, `/profile`)
- **Progrès validés** : Écran `Politique d'Authentification de la Plateforme` (`#28`) clair avec cartes radio nettes et bandeau vert de confirmation ; en `#29`, l'entrée `Configuration` est bien masquée dans la Sidebar pour un `Contributeur`.
- **Écarts relevés** : **`UX23-02` (`P1`)** (vide blanc et bouton `Révoquer` repoussé en bas de `UserSettingsModalDialog` en `#30`), **`UX23-07` (`P1`)** (`Claire Invitée` affichée comme `Administrateur de plateforme initialisé` en `#29`), `UX23-15` (6e onglet `Mon Organisation` isolé en 2e ligne dans `#28`), plus `(/LOGIN)` dans un sous-titre de `#28`.

### 3.15 Spec `15` — Organisation, IAM SecOps, Mode Observateur & `/inbox` (`#31`–`#34`)
- **Captures inspectées (`4 / 4`)** :
  - `15-organization-iam-secops-inbox-and-observer/...--bu-equipe-invitation...--passed.png` (`#31`, `1440×1558`, `/`)
  - `15-organization-iam-secops-inbox-and-observer/...--annuaire-iam...--passed.png` (`#32`, `1440×900`, `/settings?tab=iam`)
  - `15-organization-iam-secops-inbox-and-observer/...--mode-observateur...--passed.png` (`#33`, `1440×900`, `/organization`)
  - `15-organization-iam-secops-inbox-and-observer/...--centre-de-notifications...--passed.png` (`#34`, `1440×900`, `/inbox`)
- **Progrès validés** : Bandeau clair de mot de passe temporaire (`#31`, `#33`), annuaire des comptes lisible (`#32`), blocage propre lecture seule sur `/organization` pour `Oscar Observateur` (`#33`).
- **Écarts relevés** : **`UX23-07` (`P1`)** (`Marc Lead BU` nommé comme admin initialisé en `#31`), **`UX23-09` (`P1`)** (`/inbox` `#34` affiche fil d'Ariane + Sidebar + Zone 4 de `Mon Assistant`, et `/organization` `#33` affiche `Configuration` dans le fil d'Ariane sans entrée `Configuration` dans la Sidebar), **`UX23-08` (`P1`)** (`'inbox-review-step'` et `Synchronisation : 0.5 ms` en `#34`), `UX23-11` (`Plateforme entière (toutes les directi` tronqué en `#32`), `UX23-13` (`1440×1558` en `#31`).

### 3.16 Spec `16` — Modèles IA, Réindexation, Connecteurs & Permission Broker (`#35`–`#37`)
- **Captures inspectées (`3 / 3`)** :
  - `16-ai-models-reindex-connectors-and-broker/...--jour-0-sans-embedding...--passed.png` (`#35`, `1440×900`, `/settings?tab=models`)
  - `16-ai-models-reindex-connectors-and-broker/...--connecteur-socle...--passed.png` (`#36`, `1440×900`, `/settings`)
  - `16-ai-models-reindex-connectors-and-broker/...--interception-permission-broker...--passed.png` (`#37`, `1440×1056`, `/assistant`)
- **Écarts relevés** : **`UX23-08` (`P1`)** (`(AD-24.7)` + `COMPLETED (100%)` en `#35` ; Markdown brut `###` / `` ` `` / `**`, `HTTP 403`, `(Step 1 • fetch_repo)` et URI URL-encodée en `#37`), **`UX23-02` (`P1`)** (`UserSettingsModalDialog` onglet `Connexions aux outils` avec vide supérieur de ~220 px en `#36`), `UX23-13` (`1440×1056` en `#37`), `UX23-16` (`4 tiers cognitifs` en `#35`).

### 3.17 Spec `17` — Sources d'espace, Glossaire / Ontologie & ADN Tripartite (`#38`–`#40`)
- **Captures inspectées (`3 / 3`)** :
  - `17-workspace-sources-codegraph-dna-and-ontology/...--rattachement-source-code...--passed.png` (`#38`, `1440×900`, `/workspaces/$wsId/sources`)
  - `17-workspace-sources-codegraph-dna-and-ontology/...--glossaire-d-espace...--passed.png` (`#39`, `1440×900`, `/ontology`)
  - `17-workspace-sources-codegraph-dna-and-ontology/...--chaine-adn-starlark...--failed.png` (`#40`, `1440×900`, `/workspaces/$wsId`)
- **Progrès validés** : Grille à 4 niveaux sur `/ontology` (`#39`) très claire, badge rouge `Règle verrouillée` sur `Axiome Qualité Globale`, boutons `Estimer l'impact` / `Proposer au niveau supérieur` lisibles.
- **Écarts relevés** : `UX23-11` (`Rechercher un espace ou une équ` en `#38`, `#40`), `UX23-10` (`1 Sources rattachées` en `#38`), `UX23-12` (`promotions L4 → L1` dans Zone 4 de `#39`), `UX23-16` (`Organisation (Global) · Organisation (Global)` en `#39`), `UX23-17` (`#40` reste en haut de page sans montrer le bloc dérogations / graphe tripartite).

### 3.18 Spec `18` — Catalogue, Packs, Wizards & Banc de Test MCP (`#41`–`#45`)
- **Captures inspectées (`5 / 5`)** :
  - `18-catalog-packs-wizards-and-mcp-bench/...--explorateur-du-catalogue...--timedOut.png` (`#41`, `1440×900`, `/catalog`)
  - `18-catalog-packs-wizards-and-mcp-bench/...--activation-de-pack...--passed.png` (`#42`, `1440×900`, `/settings`)
  - `18-catalog-packs-wizards-and-mcp-bench/...--registre-des-packs-declaratifs...--passed.png` (`#43`, `1440×1563`, `/settings/packs`)
  - `18-catalog-packs-wizards-and-mcp-bench/...--parcours-guide...--passed.png` (`#44`, `1440×900`, `/wizards`)
  - `18-catalog-packs-wizards-and-mcp-bench/...--banc-de-test-connecteur...--failed.png` (`#45`, `1440×900`, `/agents`)
- **Écarts relevés** :
  - **`UX23-10` (`P1`)** sur `#43` : **`4 Compéte`** rogné dans la mini-tuile, `1 Chaînes` / `1 Agents` / `1 Compétences`, codes bruts `mcp:atlassian-* (read, write_preview)` et `crl-*`.
  - **`UX23-08` (`P1`)** sur `#41` & `#45` : **`0`** isolé dans un cadre vide + `depth=0` / `depth=1` (`/catalog`) et `1_NETWORK_TLS_ANTI_SSRF`..`4_HOT_DRY_RUN` + `PASS` (`/agents`).
  - `UX23-12` (backtick `` `@` `` dans Zone 4 de `#45`), `UX23-13` (`1440×1563` en `#43` coupant `Processus du Pack ORCIA`), `UX23-15` (pack actif doublé en `#42`), `UX23-16` (libellé bouton vs aide en `#44`).

### 3.19 Spec `21` — Aide Contextuelle, Vitrine `/showcase` & Citations (`#50`–`#51`)
- **Captures inspectées (`2 / 2`)** :
  - `21-assistant-citations-v5-audit-help-showcase/...--creation-de-dossier...--passed.png` (`#50`, `1440×900`, `/assistant`)
  - `21-assistant-citations-v5-audit-help-showcase/...--centre-d-aide-contextuelle...--passed.png` (`#51`, `1440×900`, `/showcase`)
- **Progrès validés** : `/assistant` (`#50`) épuré et réactif ; `/showcase` (`#51`) présente une mise en page Direction C élégante (cartes structurées, encart violet pédagogique `Ancrages de Rédaction Humaine`, pastille `Synchronisé : 2026-11-19`).
- **Écarts relevés** : **`UX23-09` (`P1`)** (Sidebar garde `Cockpit` actif sur `/showcase` au lieu d'`Aide`) et `UX23-16` (`3 espaces strictement séparés` face à `4` onglets, et chemin `(docs/site-catalog/index.html)` dans le bouton).

### 3.20 `shell.spec.ts` — Coquille 4 Zones, Rail `[` & Modale Accessible Jour 0 (`#52`–`#55`)
- **Captures inspectées (`4 / 4`)** :
  - `shell/...--presente-les-4-zones...--passed.png` (`#52`, `1440×1487`, `/`)
  - `shell/...--grise-les-entrees-de-menu...--passed.png` (`#53`, `1440×900`, `/`)
  - `shell/...--le-raccourci-replie-et-deplie...--passed.png` (`#54`, `1440×1487`, `/`)
  - `shell/...--la-modale-jour-0-est-un-dialogue-accessible...--passed.png` (`#55`, `1440×900`, `/`)
- **Constat** : Les 4 zones sont structurées et lisibles après création admin (`#52`, `#54`), l'accessibilité modale est respectée (`#55`). Subsistent `UX23-13` (`1440×1487` sur `#52`, `#54`) et `UX23-15` (`Mes Espaces` non grisée en `#53` + bouton `Fermer` en `#53`, `#55`).

---

## 4. Bilan comparatif Epic 22 → Epic 23 des points `P0-UX` à `P3-UX`

| Point Epic 22 | Sujet initial (`notes-audit-sally-ux.md` Epic 22) | Statut Epic 23 (`dd2d382`) | Preuve & détail d'évolution |
| --- | --- | :---: | --- |
| **`P0-UX-1`** | Diagnostic erroné `401` sur `Mon Assistant` + jargon HTTP + impasse | ✅ **Résolu** | `02 #7` traverse le streaming SSE réel sans bannière `401`. |
| **`P0-UX-2`** | Angle mort visuel écrans `04`–`21` + Mobile Companion suite à `resetDay0()` | ⚠️ **Partiel** | Les écrans Desktop `04`–`21` + `shell.spec.ts` sont désormais **100 % visibles** (`58/58` PNG inspectés). **Mobile Companion (`390×844` / `CAP-042`) reporté** hors Epic 23 (`ACTION_ITEM-23.6`). |
| **`P1-UX-3`** | Cockpit surchargé (`6`–`7` blocs > `3` max) & redondances | ⚠️ **Partiel** | Réduit à **2 cartes** à vide post-admin (`01 #5`, `shell #52` ✅). En activité (`03 #10`, `19 #46`), l'accostage reste ouvert au-dessus des KPIs/décisions et coupe le CTA sous `900px` (`UX23-14`). |
| **`P1-UX-4`** | Modale Jour 0 : doublon `Annuler (Esc)`, CTA fade, masque `••••••••••••••` | ✅ **Résolu** *(réserve `P2`)* | Doublon supprimé (un seul `Fermer`), masque `••••••••` remplacé par `OrciaPasswordInput` vide avec œil (`00 #2`, `shell #55`). Réserve mineure `UX23-15` sur `Fermer`. |
| **`P1-UX-5`** | Zone 4 désynchronisée de la route, coupée en bas, sans les 4 blocs `DESIGN.md` | ✅ **Largement résolu** | Les 4 blocs structurés + `▸ Détails techniques` replié + `Défiler pour voir la suite ↓` sont en place sur quasi toutes les routes ✅. Subsistent `/inbox` affiché avec la fiche `Mon Assistant` (`UX23-09`) et `` `@` `` sur `/agents` (`UX23-12`). |
| **`P1-UX-6`** | `Accostage 0/5` dupliqué, Étape 1 ignorée, doublon Étape 2/3, troncatures | ✅ **Résolu** *(réserve `P1`)* | Échelle unifiée `0/6`→`1/6`→`4/6`, 6 jalons sans troncature ✅. Anomalie nominative résiduelle `UX23-07` (`Claire Invitée` / `Marc Lead BU` affichés sous `Administrateur de plateforme initialisé`). |
| **`P1-UX-7`** | Fantômes Jour 0 : `AP Administrateur...`, `Notifications 4`, `Mes Espaces` actif | ⚠️ **Partiel** | `AP` et `Notifications 4` pré-admin totalement purgés ✅. `Mes Espaces` reste non grisée avant admin (`UX23-15`) et `default-ws` fantôme s'affiche à vide sur `/spaces` (`UX23-06`). |
| **`P2-UX-8`** | Jargon technique (`embedding`, `BASE -> PACK`, `(Esc)`) | ⚠️ **Déplacé sur nouveaux écrans** | Anciennes occurrences corrigées ✅, mais les écrans `04`–`21` dévoilent `AD-24.7`, `PAUSE_AND_ESCALATE`, `OPT_A_SPOT_15M`, `1_NETWORK_TLS_ANTI_SSRF`, `PostgreSQL 18`, `0.5 ms`, `depth=0`, Markdown brut (`UX23-08`). |
| **`P2-UX-9`** | Troncatures `TopHeaderBar` (`Espace : ...`, `Rechercher...`) | ✅ **Résolu en Header** *(autrement `UX23-11`)* | `TopHeaderBar` propre sans troncature ✅. Nouvelles troncatures identifiées sur Studio (`Ex : Ajouter un contrôle de p`), `/spaces`, IAM et `/settings/packs` (`4 Compéte`, `UX23-10`, `UX23-11`). |
| **`P2-UX-10`** | Logo `ORCIA` dans Zone 2, splash nu, `/login` sans logo ni œil, fil sans Équipe | ✅ **Largement résolu** | `O ORCIA` en tête de Zone 1 ✅, splash avec logo+spinner ✅, `/login` avec logo+œil ✅. Reste désynchronisation `/inbox`, `/showcase` et absence `[Espace]` dans le fil (`UX23-09`). |
| **`P2-UX-11`** | Vérification WCAG AA des états désactivés et alertes | ❌ **Non clôturé** | Deux non-conformités nettes relevées sur les écrans `10` et `12` : onglet actif `Par Modèle et Niveau d'effort` sur `/finops` à vide (`UX23-04`) et bouton `Ouvrir ❓ Aide` rouge-sur-bleu en `⌘K` (`UX23-05`). |
| **`P3-UX-12`** | Captures E2E finales manquantes sur jalons (`HumanLedAnchorCard`, etc.) | ✅ **Largement résolu** | `3` captures `milestone-*.png` ajoutées (ancrage violet, arbitrage ambre, `/login`), à étendre pour VSM/HITL et traces API (`UX23-17`). |
