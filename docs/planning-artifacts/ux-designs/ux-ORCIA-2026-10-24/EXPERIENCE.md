---
name: ORCIA
title: ORCIA — Interaction Design & Experience Specification (Direction C)
status: final
created: 2026-10-24
updated: 2026-10-24
sources:
  - ../../product-brief.md
  - ../../prds/prd-ORCIA-2026-10-24/prd.md
---

# ORCIA — Experience Spine

> Spécification comportementale et d'architecture de l'information d'ORCIA, appairée avec [`DESIGN.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md) (Direction C : Sidebar Sombre Explicite + Espace Central Haut-Contraste + Dock Agent Assistant Persistant). En cas de conflit avec une maquette exploratoire, `DESIGN.md` et `EXPERIENCE.md` font foi.

---

## 1. Foundation

- **Form-factor** : Application Web Responsive **Desktop-First** (poste de pilotage complet, rédaction d'**Ancrages Humains Obligatoires**, co-édition d'**Artefacts**, **Validation par Découpage** et administration) doublée d'une expérience **Mobile Companion à périmètre volontairement restreint** (triage et *Claim* des notifications, réponse aux **Arbitrages Humains**, lecture des **Briefings de Revue**, validation par découpage et suivi des **Workflow Runs** en mode *Consultation seule*).
- **Système UI** : **shadcn/ui (Radix Primitives + Tailwind CSS)**. `DESIGN.md` définit les tokens identitaires (`{colors.sidebar-bg}`, `{colors.primary}`, `{colors.human-led}`, `{colors.arbitration-amber}`, `{colors.gate-pass}`, `{colors.ontology-cyan}`, `{colors.stale-danger}`) et les 7 composants métiers d'ORCIA.
- **Paradigme d'interaction** : **"Chat-First + Canvas avec Menu Global Explicite (Direction C)"**. L'utilisateur entre par défaut dans le Cockpit conversationnel, mais dispose en permanence à gauche du **Menu Global à 7 Modules** (filtré selon ses droits RBAC) et conserve à droite dans tous les modules (2 à 7) le **Dock Persistant de l'Agent Assistant & Permission Broker**.

### 1.1 Les Règles Fondamentales de l'UX (Expérience Utilisateur — 6 Piliers Invariants)

L'UX désigne le parcours, la fluidité et la logique de navigation du portail ORCIA. Toute conception ou évolution d'écran doit respecter ces **6 règles fondamentales** :

1. **Centrer sur l'utilisateur** : Concevoir exclusivement pour les besoins réels des utilisateurs cibles (selon leur **Profil Humain** : Direction/BU, PM/Métier, Architecte/Tech Lead/Dev, SecOps/Auditeur), jamais pour le goût personnel des équipes internes ni en exposant de la plomberie technique hors contexte.
2. **Viser la simplicité (Loi de Hick / Minimalisme)** : Éliminer les éléments superflus pour éviter de surcharger cognitivement l'utilisateur. Un module = une intention principale claire ; ne jamais empiler simultanément sur un même écran des panneaux appartenant à d'autres modules (divulgation progressive, onglets ou tiroirs à la demande).
3. **Respecter les standards du web** : Utiliser des schémas de navigation familiers et prévisibles (identité/logo en haut à gauche ramenant à l'accueil/Cockpit, barre d'en-tête claire avec fil d'Ariane/périmètre actif, navigation principale structurée et états actifs explicites).
4. **Assurer un bon feedback immédiat** : Chaque action de l'utilisateur (clic, validation, changement de périmètre, erreur, *Claim*, pause ou *Replay*) doit entraîner une réponse visuelle et/ou textuelle immédiate (états `loading`, `disabled`, toast/bannière contextualisée, mise à jour optimiste `< 500ms`).
5. **Offrir des sorties de secours** : L'utilisateur doit toujours pouvoir annuler une action, fermer une modale/tiroir (`Escape` ou bouton explicite), replier un panneau latéral (`[` / `]`) ou revenir en arrière facilement sans perte de contexte ni blocage dans une impasse.
6. **Optimiser la performance et le Mobile-First** : Privilégier la rapidité de chargement et de rendu (`< 1,5s` premier token, bascule `< 1s` entre runs) et concevoir d'abord la clarté structurelle sur petits écrans (Mobile Companion épuré sans débordement horizontal) avant d'enrichir la disposition multi-colonnes Desktop.

---

## 2. Information Architecture (Sélecteur de Périmètre Hiérarchique `⌘W` & Menu Global à 7 Modules)

La barre latérale gauche (`{spacing.sidebar-expanded}` = `235px` dépliée, `{spacing.sidebar-collapsed}` = `68px` repliée) affiche en en-tête un **Sélecteur de Périmètre Hiérarchique (`⌘W` : `🌐 Plateforme Globale → 🏢 BU / Tribu → 👥 Équipe → 🗂️ Workspace Solution Logicielle`)** qui filtre dynamiquement les vues selon un modèle fractal (*Roll-up* ascendant et *Drill-down* descendant), et structure toute l'application autour de **7 surfaces principales** :

| # | Surface (Menu Global) | Raccourci | Accès / Visibilité RBAC | Rôle & Comportement de l'Espace Central + Dock IA |
| :-: | :--- | :---: | :--- | :--- |
| **1** | **💬 Cockpit & Chat** *(Défaut)* | `g c` | Tous les utilisateurs | Vue Split-View : Conversation principale avec l'**Agent Assistant** + **Canvas Dynamique** (affichage de l'**Artefact** actif, du **Briefing de Revue**, des **Ancrages Humains Obligatoires** et de la **Gate** en cours). |
| **2** | **🔔 Boîte, Runs & Workspaces** | `g i` / `g w` | Tous les utilisateurs (filtré selon périmètre `⌘W`) | **Centre de Notifications Unifié** (*À moi* vs *À mon équipe* avec *Claim* `< 500ms`) + **Centre de Pilotage Unifié des Workspaces (`/workspaces` & `/workspaces/[workspaceId]`)** structuré en **4 onglets consolidés** (opérant aussi bien au niveau d'un `Workspace` solution qu'en consolidation `Équipe`, `BU` pour un Directeur de BU ou `Plateforme Globale` pour un Admin Plateforme) : **1. Instances de `Workflow Runs` & Artefacts** (*Contributeur* vs *Consultation seule*), **2. Sources Dédiées & Partagées (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://` + fraîcheur)**, **3. Workflows, Agents & Surcharges (`Base → Team → Workspace → User`)**, et **4. Équipes, Membres & Gouvernance (`TEAM_LEAD`)**. Dock IA à droite. |
| **3** | **📦 Catalogue Fédéré** | `g f` | Selon droits `DISCOVER` | Explorateur des **Workflows**, **Agents**, **Skills**, **Gabarits d'Artefact** et **Ontologies** résolus depuis `db://`, `git://`, `nexus://`, `confluence://` et `jira://` (badges `{components.uri-badge}`, empreintes `SHA-256`, cycle de publication et surcharges à 4 niveaux). Dock IA + **Permission Broker** à droite. |
| **4** | **🧬 Ontologie & KB** | `g o` | Tous (`EDIT` selon rôle) | Explorateur à 4 colonnes des strates de l'**Ontologie** (*1. Entreprise $\rightarrow$ 2. BU $\rightarrow$ 3. Équipe & Workspace $\rightarrow$ 4. Run*) avec boutons de promotion gouvernée, simulation *What-If* + gestion du **Graphe Tripartite (`Confluence ↔ Jira ↔ Git`)** et résolution des alertes `[STALE_WARNING]` (`{colors.stale-danger}`). Dock IA à droite. |
| **5** | **🛡️ Gates & Habilitations** | `g g` | SecOps, Leads, Managers | Configuration des **Politiques de Gates Adaptatives** (`mandatory_full`, `risk_or_exception_based`, `sampling`), gestion des délégations temporaires, et portail interactif du **Permission Broker** (procédures d'accès et demandes Jira). Dock IA à droite. |
| **6** | **📊 FinOps & Audit** | `g a` | Directeurs BU, Leads, Audit | Tableaux de bord d'optimisation budgétaire consolidés par Workspace / Équipe / BU / Entreprise (Coût Setup + Run vs TTM), quotas, journal immuable de **Provenance Auditable**, et indicateurs cognitifs (*Ratio Human-Led Think*, alertes *Rubber-Stamping*, indice de **Pattern Drift** / **Réversibilité Humaine**). Dock IA à droite. |
| **7** | **⚙️ Administration & Settings Hub (`/settings/*`)** | `g s` | Selon droits `read`/`update`/`grant` sur l'arbre `scope_path` | **Hub de Paramétrage Post-Jour 0 (`/settings/{iam,connectors,ai-models,packs,workflows,audit}`)** : gouvernance IAM à **6 verbes (`create, read, update, delete, execute, grant`)** et délégation bornée, instances de connecteurs (`<SecretField />` write-only, test de connexion DBOS, classification `C0–C3`, arbitrage PII, test de réciprocité RAG), mapping abstrait des **Tiers LLM (`simple €, medium €€, complex €€€, auto ⚡`)** & niveaux d'**Effort**, registre des **Packs Métier** par périmètre, **Studio Visuel de Workflows** (5 onglets de cycle de vie, `Pré-prompt`, `Contrat`, `Déclencheurs`, `▷ Tester`, inspecteur `COUCHES · N`), journal `SettingsChanged` & rejeu Outbox borné (`--dry-run`), et **3 Wizards d'Initialisation Durables (`/wizards/*`)**. Dock IA + `<GuidanceDrawer />` à droite. |

→ Références visuelles promues : [`mockups/visual-explorations-2.html`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/mockups/visual-explorations-2.html), [`mockups/visual-explorations-1.html`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/mockups/visual-explorations-1.html) et étude comparative [`rework-from-exemple-2026-10-30.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/research/rework-from-exemple-2026-10-30.md).

---

## 3. Voice and Tone (Adaptation Dynamique au Profil Humain via l'Ontologie)

Contrairement aux interfaces statiques qui parlent de la même manière à tous les utilisateurs, l'**Agent Assistant** d'ORCIA adapte son registre et son vocabulaire au **Profil Humain** connecté en s'appuyant sur l'**Ontologie Dynamique Multi-Niveaux** (`FR-1`, `FR-10`) :

| Profil Humain Cible | Ton & Niveau de Synthèse | Exemple de Microcopy (Do) | Anti-pattern (Don't) |
| :--- | :--- | :--- | :--- |
| **Direction / BU Lead** (`Claire UJ-8`) | Exécutif, chiffré, orienté budget, risque métier, SLA et gouvernance (Ontologie Niveau 1/2). | *"Coût complet en baisse de 28% sur la BU Paiement. 1 alerte de validation trop rapide détectée sur l'équipe Core Ledger."* | *"142 890 tokens consommés sur claude-3-7-sonnet avec exit code 0 sur le container sandbox."* |
| **Product Manager / Métier** (`Hélène UJ-1`, `Nadia UJ-4`) | Structuré, orienté règles de gestion, parcours client, conformité CGV et impact produit. | *"Antoine (Architecte SI) signale que la garantie de taux 48h impacte 3 systèmes centraux et propose une alternative à 15 min."* | *"Erreur de contrainte de clé étrangère sur le schéma YAML du microservice Treasury."* |
| **Architecte / Tech Lead / Dev** (`Antoine UJ-2`, `Yanis UJ-3`, `Lucas UJ-7`) | Précis, technique, citant les URI exactes, les schémas OpenAPI, les diffs et les hashes `SHA-256` (Ontologie Niveau 3). | *"Incompatibilité détectée sur `POST /fx-refund` (OpenAPI v3 vs `kb://partner-fx-spec-v2.pdf`). Déclencher un Rewind vers Step 1 ?"* | *"Il semble y avoir un petit souci technique avec le partenaire, voulez-vous qu'on regarde ?"* |
| **SecOps / Auditeur** (`Sophie UJ-6`) | Factuel, axé sur les preuves de **Gates**, l'**Orthogonalité des Modèles**, les hypothèses et la **Provenance Auditable**. | *"Gate 1.2 validée par modèle indépendant (Gemini Pro vs exécuteur Claude). 0 Pattern Drift. 1 hypothèse de sécurité (H-2) à vérifier."* | *"Tout a l'air super sécurisé, vous pouvez cliquer sur Valider ! 🚀"* |

---

## 4. Component Patterns (Comportements Cognitifs & Gouvernance)

| Composant | Surface(s) | Règles Comportementales |
| :--- | :--- | :--- |
| **Human-Led Anchor Card** (`{components.human-led-anchor-card}`) | Cockpit (Canvas) | Affiché en amont d'un **Step** comportant des champs `human_authored_required: true`. Tant que l'humain n'a pas saisi et validé son texte (minimum 30 caractères significatifs), le bouton *Lancer la génération de l'étape* reste verrouillé. Le copier-coller d'un prompt générique ou la demande *"Remplis-le pour moi"* dans le chat déclenche une relance socratique de l'agent. |
| **Cognitive Review Briefing** (`{components.review-briefing-grid}`) | Cockpit (Canvas), Gates, Mobile | S'affiche automatiquement en haut de tout **Artefact** $> 1\,500$ mots ou $> 3$ sections. Le bloc *4. Hypothèses retenues* reste surligné en `{colors.arbitration-amber}` jusqu'à ce que le valideur ait fait défiler ou pointé les hypothèses. |
| **Chunked Validation Card** (`{components.chunk-validation-card}`) | Cockpit (Canvas), Gates | Segmente l'**Artefact** selon les sections de son **Gabarit d'Artefact**. Chaque section possède un état indépendant (`PENDING`, `APPROVED`, `CHALLENGED`, `EDITING`). La **Gate Humaine** globale ne s'active en vert (`{colors.gate-pass}`) que lorsque toutes les sections obligatoires sont à l'état `APPROVED`. |
| **Arbitration Tie-Break Matrix** (`{components.arbitration-tiebreak-card}`) | Chat, Inbox, Mobile | Affiché dès qu'un **Agent Exécuteur** rencontre $\ge 2$ options équivalentes (`FR-5`). Présente les options côte à côte avec un bouton de sélection explicite et un champ optionnel *"Justification / Autre orientation"*. Le clic débloque immédiatement le **Workflow Run** en arrière-plan. |
| **Upstream Challenge & Rewind Modal** | Cockpit (Canvas & Chat) | Permet à un contributeur aval (`UJ-2`, `UJ-3`) de sélectionner un passage d'un **Artefact** amont ou de signaler une `[STALE_WARNING]` sur une **Base de Connaissances**, de formuler son challenge, et de notifier les acteurs amont pour arbitrage avant **Replay** ciblé (`FR-16`). |
| **Presence & Claim Pill** (`{components.presence-claim-pill}`) | Boîte & Mes Runs, Cockpit | Sur toute notification adressée à une équipe/groupe : un clic sur `Prendre (Claim)` assigne l'item à l'utilisateur et diffuse en `< 500 ms` via WebSocket l'état `🔒 En cours : {Prénom}` aux autres membres de l'équipe. Si l'utilisateur reste inactif pendant 15 minutes sans valider, le verrou peut être repris (*Force Unclaim*). |
| **Anti-Rubber-Stamping Guard** | Gates Humaines | Si l'utilisateur clique sur *Approuver la Gate* en moins de `15 secondes` sur un **Artefact** volumineux sans avoir interagi avec le **Briefing de Revue** ni les sections découpées, une modale de friction positive s'ouvre : *"Validation rapide détectée — Confirmez-vous avoir vérifié les {N} hypothèses retenues par l'Agent Évaluateur ?"* |
| **Autonomous Execution Badge & Kill-Switch** (`AutonomousExecutionBadge`, `UX-DR17`) | Cockpit, Boîte & Mes Runs, Centre de Pilotage `/workspaces` | Affiché en Cyan/Cobalt (`#0284C7`, jamais en Violet `#6D28D9`) sur tout **Workflow Run** ou **Artefact** exécuté sous `AUTONOMOUS_CONTRACT` (`UJ-11`, `UJ-12`). Dans **🔔 2. Boîte & Mes Runs**, les runs autonomes nominaux sont regroupés dans un filtre replié par déclencheur (Loi de Hick), seules les escalades, ouvertures de coupe-circuit (`CIRCUIT_OPEN`) et tirages d'audit post-hoc (`POST_HOC_AUDIT_SAMPLE`) remontant en priorité. Expose deux sorties de secours immédiates : `🛑 Kill-Switch` et `⏪ Invalider & Rollback`. |
| **Permission Guard & Passive Discovery** (`PermissionGuard`, `AD-21`) | `/settings/*`, Catalogue, Studio, `/workspaces` | Applique le modèle à **6 verbes (`create, read, update, delete, execute, grant`)**. Lorsqu'un utilisateur dispose de `execute` sans `read` sur un connecteur ou un modèle IA, il peut le sélectionner et l'exécuter dans un workflow mais voit les champs de configuration verrouillés (`🔒 Non habilité`). S'il n'a aucun droit et que `hidden_when_unauthorized` est `false`, la carte reste visible en découverte passive avec le bouton *Demander l'accès* (`AccessRequested` Outbox). |
| **Write-Only Secret Field** (`SecretField`, `AD-21`) | `/settings/connectors`, `/settings/ai-models`, `/settings/iam` | Affiche l'état `Configuré (empreinte sha256:8-hex)` ou `Non configuré` sans jamais charger ni soumettre de masque `••••••••`. Le remplacement ou la suppression passe par une action explicite (`SecretInput: keep \| set \| clear`) protégée par concurrence optimiste `If-Match` (`412` en cas de conflit). |
| **Studio Top Governance Bar & Layers Inspector (`COUCHES · N`)** | `/studio/$workflowId` | En haut du Studio : `Bibliothèque`, `Pré-prompt IA` (versionné `SHA-256`), `Contrat du workflow` (paramètres typés `p_1..p_n` + sections Markdown obligatoires), `Déclencheurs`, `▷ Tester` (dry-run *What-If*) et `Publier` (toute édition d'une version `PUBLISHED` crée automatiquement une branche `vX.Y.Z-draft`). Sur chaque macro-étape (`SUB_WORKFLOW`), le badge **`COUCHES · N`** ouvre un popover listant les sous-couches en 3 zones (*Entrées*, *Capacités*, *Livrables*) avec icône `👁️` pour désactiver une couche (`enabled: false -> SKIPPED`) sans casser le graphe. |
| **Methodological Guidance Drawer (`5 étapes`) & Ingestion Gates** | `/workspaces` (Sources), `/settings/connectors`, `/studio` | Tiroir latéral `<GuidanceDrawer />` expliquant en 5 étapes l'écran actif. Lors de l'ajout d'un document RAG : sélection obligatoire de la classification `C0–C2` vs `C3`, scan automatique de PII avec modale d'arbitrage (*Pseudonymiser* / *Indexer tel quel* / *Annuler*), rejet immédiat des PDF scannés vides (`0 char`) et bouton *« Vérifier qu'il répond »* (Test de Réciprocité RAG avec citation obligatoire). |

---

## 5. State Patterns

| État Système | Surface Concernée | Traitement Comportemental & Visuel |
| :--- | :--- | :--- |
| **Mode Consultation Seule (`READ_ONLY_OBSERVER`)** | Cockpit, Boîte & Mes Runs | Bandeau supérieur explicite `👁️ Mode Consultation Seule — Vous suivez ce Workflow Run en tant qu'Observateur`. Tous les boutons d'approbation de **Gate**, d'édition d'**Artefact** et d'arbitrage sont masqués ou remplacés par un état informatif non cliquable. |
| **Mode Contributeur Actif (`CONTRIBUTOR_ACTION_REQUIRED`)** | Cockpit, Boîte & Mes Runs | Bandeau `{colors.primary}` ou `{colors.arbitration-amber}` indiquant l'action précise attendue (*Rédiger l'Ancrage Humain*, *Trancher l'Arbitrage*, *Valider les 4 sections de la Gate 1.2*). |
| **Blocage d'Habilitation (`PERMISSION_DENIED_STEP`)** | Cockpit, Catalogue, Gates | Au lieu d'une erreur générique, le **Dock Agent Assistant & Permission Broker** s'ouvre automatiquement avec une carte `{colors.arbitration-amber}` détaillant : le droit manquant, la procédure d'entreprise extraite de la KB (ex: `#IAM-PROD-12`), le valideur cible, et un bouton *Mettre le Step en pause & Préparer la demande* (suivi d'un bouton **Replay Step $N$** dès l'accès obtenu). |
| **Obsolescence Documentaire (`STALE_WARNING`)** | Ontologie & KB, Cockpit | Badge rouge `!` (`{colors.stale-danger}`) sur l'entrée **🧬 4. Ontologie & KB** de la Sidebar. Les **Workflow Runs** en cours ayant consommé le document obsolète affichent une bannière d'alerte invitant à arbitrer et à lancer un **Replay** ciblé après mise à jour de la KB. |
| **Verrouillage Concurrent d'Équipe (`CLAIMED_BY_PEER`)** | Boîte & Mes Runs, Cockpit | La carte de notification passe en opacité `85%` avec la pastille `{colors.gate-pass}` `🔒 En cours : {Prénom}`. Cliquer dessus ouvre le **Workflow Run** en mode *Consultation temporaire* avec un bouton secondaire *Rejoindre en co-édition* ou *Reprendre la main*. |
| **Exécution Autonome sous Contrat (`AUTONOMOUS_CONTRACT` / `CIRCUIT_OPEN`)** | Cockpit, Boîte & Mes Runs, `/workspaces` | Bandeau Cyan/Cobalt `🤖 Exécuté sous Contrat d'Autonomie` (ou Rouge `{colors.stale-danger}` `🚨 Coupe-Circuit Ouvert / Rollback Automatique Exécuté` si la vérification post-action `POST_ACTION_VERIFICATION` échoue) avec boutons d'arrêt d'urgence (`🛑 Kill-Switch`) et d'annulation (`⏪ Invalider & Rollback`). |

---

## 6. Interaction Primitives

**Clavier & Productivité (Power-User Ready) :**
- `⌘K` / `Ctrl+K` : Palette de commandes universelle (changer de **Workflow Run** en `< 1s`, chercher dans le **Catalogue Fédéré**, interroger un concept de l'**Ontologie**, sauter à une notification).
- `⌘W` / `Ctrl+W` (ou sélecteur d'en-tête) : Changer de périmètre organisationnel (`🌐 Plateforme Globale` $\leftrightarrow$ `🏢 BU / Tribu` $\leftrightarrow$ `👥 Équipe` $\leftrightarrow$ `🗂️ Workspace Solution`).
- `g c`, `g i` (ou `g w` pour le Centre de Pilotage Workspaces), `g f`, `g o`, `g g`, `g a`, `g s` : Navigation directe vers les **7 Modules du Menu Global**.
- `[` : Replier / Déplier la Sidebar gauche (`235px` $\leftrightarrow$ `68px`).
- `]` : Replier / Déplier le **Dock Agent Assistant** à droite dans les modules 2 à 7.
- `Alt + ↑ / ↓` : Naviguer de section en section lors d'une **Validation par Découpage** dans le **Canvas**.

**Interdictions ergonomiques strictes (Banned Everywhere) :**
- **Interdiction du bouton "Générer avec l'IA"** à l'intérieur d'un composant **Human-Led Anchor Card**.
- **Interdiction du bouton "Tout Approuver en 1 clic"** en haut d'un **Artefact** volumineux tant que les sections du découpage n'ont pas été parcourues.
- **Interdiction d'éditer des Workflows YAML ou de co-éditer de gros dossiers d'architecture sur Mobile** (redirigé vers l'ouverture sur Desktop).

---

## 7. Accessibility Floor

- Conformité **WCAG 2.2 AA** sur l'ensemble des surfaces (contraste vérifié entre la Sidebar `#0F172A` et son texte `#F8FAFC`, ainsi que sur l'espace central clair `#F8FAFC`/`#FFFFFF`).
- Les états critiques (**Gates**, **Ancrages Humains Obligatoires**, **Arbitrages**, `[STALE_WARNING]`) n'utilisent jamais la couleur seule : ils combinent systématiquement **Couleur sémantique + Icône dédiée + Libellé textuel explicite** (`✍️ Ancrage Humain`, `⚖️ Arbitrage IA`, `🛡️ Gate`, `🚨 Obsolète`).
- Annonces `aria-live="polite"` sur l'arrivée de nouvelles notifications d'équipe, les changements d'état de *Claim* en temps réel et le streaming de l'**Agent Assistant**.

---

## 8. Responsive & Platform (Desktop vs Mobile Companion)

| Breakpoint | Surface & Grille | Capacités Actives | Capacités Restreintes / Désactivées |
| :--- | :--- | :--- | :--- |
| **Desktop Large (`≥ 1280px`)** | Sidebar dépliée (`235px`) + Espace Central (`1fr`) + Dock IA (`360px`). | 100% des 7 modules, création/édition de Workflows, co-édition complète d'**Artefacts**, **Validation par Découpage**, administration. | Aucune restriction. |
| **Laptop / Tablet Landscape (`768px – 1279px`)** | Sidebar repliée en icônes (`68px`) par défaut + Split-View ou tiroir Dock IA. | 100% des capacités fonctionnelles. | Dock IA superposé en `Sheet` sur les écrans `< 1024px`. |
| **Mobile Companion (`< 768px`)** | Vue mono-colonne avec barre d'onglets basse à 3 entrées (`🔔 Inbox`, `💬 Arbitrage/Chat`, `📄 Briefing`). | Triage et *Claim* des notifications, réponse aux **Arbitrages Humains**, réponse aux questions humaines, lecture du **Briefing de Revue (4 volets)**, approbation par découpage, suivi des runs en *Consultation seule*. | Co-édition lourde d'**Artefacts** multi-pages, édition YAML **Workflow-as-Code**, et module **7. Administration** (bannière : *"Fonctionnalité réservée au poste Desktop"*). |

---

## 9. Key Flows (Ancrés sur les User Journeys `UJ-1` à `UJ-9`)

### Flow 1 — Triage Matinal Multi-Workflows & Prise en Charge d'Équipe (`Nadia, UJ-4`)
1. Nadia ouvre ORCIA sur son Desktop. La Sidebar gauche (Direction C) affiche un badge ambre `3` sur **🔔 2. Boîte & Mes Runs** et un badge rouge `!` sur **🧬 4. Ontologie & KB**.
2. Elle clique sur **🔔 2. Boîte & Mes Runs**. L'espace central affiche en haut ses **3 Actions Requises (Mode Contributeur)** et en bas ses **5 Runs suivis (Mode Consultation Seule)**.
3. Elle survole d'abord *Migration Base Europe* en mode *Consultation seule* (60%, Step 3/5), vérifie que tout est nominal, puis clique sur `Prendre (Claim)` sur la notification d'équipe *Remboursement Multi-Devises*.
4. En `< 500 ms`, la pastille passe à `🔒 Pris par vous` (et affiche `🔒 En cours : Nadia` chez son collègue Thomas).
5. L'application bascule dans le **💬 1. Cockpit** sur le Run #108 : Nadia tranche l'**Arbitrage Humain** dans le Chat et valide la Section 2 révisée du PRD dans le **Canvas** par découpage.

### Flow 2 — Chaîne "Human-Led" PM $\rightarrow$ Challenge Architecte $\rightarrow$ Alerte d'Obsolescence Tech Lead (`Hélène UJ-1`, `Antoine UJ-2`, `Yanis UJ-3`)
1. **Hélène (PM)** lance le Run #108 dans **💬 1. Cockpit**. Le **Canvas** affiche la carte violette **Human-Led Anchor Card** (`human_authored_required: true`). Elle rédige la justification métier et le risque à ne pas faire ; l'**Agent Exécuteur** génère ensuite le `PRD v1.0`.
2. **Antoine (Architecte SI)** ouvre le Run #108 au Step 2. Après analyse d'impact avec son agent, il clique sur `Challenger / Rewind amont` sur la règle de garantie de taux à 48h. L'agent traduit l'impact SI en vocabulaire métier via l'**Ontologie** ; Hélène accepte l'ajustement (`PRD v1.1`). Antoine rédige son **Ancrage Humain Obligatoire** d'architecture et publie le `Dossier d'Architecture v1.0`.
3. **Yanis (Tech Lead)** inspecte le `Dossier d'Architecture` au Step 3. Son **Skill** **MCP** OpenAPI détecte que l'API partenaire est passée en `v3` et contredit le document `kb://paiement/partner-fx-spec-v2.pdf`.
4. Yanis clique sur **Signaler Obsolescence KB & Demander Arbitrage**. Le système marque le document `[STALE_WARNING]`, allume le badge `!` sur **🧬 4. Ontologie & KB**, et soumet la matrice d'**Arbitrage Humain** (Option A : adapter le besoin au taux spot vs Option B : demander évolution au partenaire).
5. Une fois l'Option A tranchée et le contrat `OpenAPI v3.1` publié dans **🧬 4. Ontologie & KB**, Yanis clique sur **Replay à partir du Step 1 (Delta)** : seules les sections impactées sont rejouées et validées.

### Flow 3 — Résolution d'un Blocage d'Habilitation via le Catalogue Fédéré & le Permission Broker (`Lucas UJ-7`, `Karim UJ-9`)
1. **Lucas (Développeur)** consulte **📦 3. Catalogue Fédéré** ou exécute un Step appelant `nexus://bundles/prod-deploy-mcp@3.0.0`.
2. La carte affiche le badge ambre `🔒 Habilitation EXECUTE requise`.
3. Dans la colonne de droite, le **Dock Agent Assistant & Permission Broker** affiche automatiquement les instructions extraites de la KB des procédures d'accès (`#IAM-PROD-12` : groupe `ORCIA-Release-Managers`, valideur `Claire`).
4. Une fois l'habilitation accordée, Lucas clique sur **Replay Step 3** : l'exécution repart immédiatement du Step 3 grâce au cache `SHA-256` et au **Blackboard** épinglé.
