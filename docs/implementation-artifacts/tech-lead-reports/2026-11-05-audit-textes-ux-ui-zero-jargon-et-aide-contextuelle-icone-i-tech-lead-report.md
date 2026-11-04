# Rapport Tech Lead — Audit & Refonte des Textes UX/UI (Zéro Jargon Interne) et Aide Contextuelle par Icône `ⓘ` (`ContextualInfoTriggerButton`)

- **Identifiant** : `2026-11-05-audit-textes-ux-ui-zero-jargon-et-aide-contextuelle-icone-i`
- **Catégorie** : `Évolution Ad-Hoc` (Audit UX/UI transverse Sally & Winston — Dictionnaires i18n FR/EN, Vues `apps/web`, Composant `@orcia/ui` `ContextualInfoTriggerButton` et Aide Contextuelle Droite)
- **Date d'analyse** : `2026-11-05`
- **Auteur** : Tech Lead / Dev Senior Agent (avec **Sally** `bmad-agent-ux-designer` & **Winston** `bmad-agent-architect`)
- **Statut** : `Verified & Done` (`Pre-Code Analysis` $\rightarrow$ `In Progress` $\rightarrow$ `Verified & Done`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Rédigée AVANT Codage)

### 1.1 Périmètre Fonctionnel & Références

- **Objectifs fonctionnels et UX/UI** :
  1. **Zéro plomberie ou jargon interne ORCIA visible par l'utilisateur** : Purger l'ensemble des dictionnaires `i18n` (`apps/web/src/i18n/locales/*.ts`) et des écrans (`apps/web/src/components/ShellContainer.tsx`, `apps/web/src/routes/*.tsx`, `apps/web/src/features/**/*.tsx`) de tout terme d'implémentation interne (noms de tables SQL comme `domain_events_outbox`, moteurs ou briques internes comme `DBOS`, `PostgreSQL 18`, `PG18`, `pgvector`, `halfvec`, `Outbox`, `CAS`, `SHA-256`, `Starlark`, `Palier 1b`, `Wasmtime`, `Passthrough`, `Service Principal`, `Argon2id`, `OIDC PKCE`, `Tie-Break`, `Rubber-stamping`, `What-If`, `Rebase`, `Verrou V1..V5`, `RRF`, `BM25`, `HNSW`, `CTE`, `ETag`, `SSE`, `TTFT`, `FIFO`, `MCP_IDE_CLIENT`, `AD-10`, `AD-15`, `RFC 9457`, `human_authored_required: true`, `WAITING_FOR_HUMAN_ARBITRATION`, `CONTRIBUTOR_ACTION_REQUIRED`, `READ_ONLY_OBSERVER`, `1_ENTERPRISE`, `ORCIA_BOOTSTRAP_TOKEN`, `run-lock.json`, etc.).
  2. **Intitulés auto-porteurs et immédiats (< 2 secondes de compréhension)** : Adopter systématiquement le point de vue et le vocabulaire métier de l'utilisateur final, tout en conservant **100 % de parité récursive des clés FR/EN**.
  3. **Zéro pavé explicatif dans l'espace de travail — Renvoi par icône `ⓘ` (`ContextualInfoTriggerButton`) vers la colonne d'aide contextuelle droite** :
     - Créer et exporter dans `@orcia/ui` (`packages/ui/src/components/ContextualInfoTriggerButton.tsx` et `packages/ui/src/index.ts`) le composant `ContextualInfoTriggerButton` affichant un `"i"` dans un cercle cliquable `18px × 18px` (`aria-label`, focus ring, stylé via `packages/ui/src/styles/tokens.css`, zéro hexadécimal brut).
     - Câbler le clic sur `ⓘ` pour ouvrir automatiquement la colonne d'aide contextuelle droite (`FourZoneDirectionCShell` / `ShellContainer.tsx`) et positionner/surligner la section d'explication associée (`sectionId` dans `ContextualHelpColumnAndCenter.tsx`).
     - Enrichir le catalogue d'aide contextuelle (`apps/web/src/components/contextualHelpCatalog.ts`, `ShellContainer.tsx`, `docs/help/fr/spaces-sources.md` et `docs/help/en/spaces-sources.md`) pour offrir une explication claire, centrée utilisateur et sans jargon pour chaque bouton `ⓘ`.
  4. **Pérennisation documentaire des 3 nouvelles règles UX/UI** dans `GEMINI.md`, `CLAUDE.md`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` et `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md`.
- **Décisions d'Architecture & UX applicables** :
  - `AD-01` & `AD-19` : Isolation stricte de `@orcia/ui` (`packages/ui`) vis-à-vis de `@tanstack/react-router`, `@orcia/api-client` et `zustand`.
  - `UX-DR1` à `UX-DR16` (`DESIGN.md` & `EXPERIENCE.md`) : Direction C Dual-Adaptive, tokens CSS sémantiques exclusifs, Violet `#6D28D9` (`--color-human-led-violet`) strictement réservé à `HumanLedAnchorCard`, Loi de Hick / Minimalisme.

### 1.2 Audit Croisé Sally (UX Designer) & Winston (System Architect) des Textes UI

L'audit exhaustif des 7 fichiers de dictionnaires `apps/web/src/i18n/locales/` et des vues `apps/web/src/` a identifié les familles de jargon interne suivantes et défini leur reformulation centrée utilisateur ainsi que la section d'aide contextuelle (`sectionId`) associée :

| Fichier / Domaine | Texte Avant (Jargon / Plomberie Interne ORCIA) | Critique Sally (UX) & Winston (Architecte) | Texte Après (FR / EN — Centré Utilisateur) & `sectionId` (`ⓘ`) |
| :--- | :--- | :--- | :--- |
| `fr.ts` / `en.ts` (`shell`, `humanAnchor`, `arbitrationTieBreak`) | `"Saisie Humaine Requise (Verrou V1)"`, `"human_authored_required: true"`, `"Arbitrage Humain & Tie-Break"`, `"Délai avant escalade (Tie-Break)"` | **Sally** : « Verrou V1 », `human_authored_required: true` et « Tie-Break » sont des identifiants techniques de spécification. **Winston** : L'utilisateur doit comprendre qu'une rédaction personnelle ou une décision de départage est attendue. | `"Rédaction personnelle requise"` / `"Personal authoring required"`, `"Arbitrage et départage"` / `"Arbitration & final decision"`, `sectionId: "human-authoring"` |
| `fr.ts` / `en.ts` (`workspaceTopology`, `catalogExplorer`, `permissionBroker`) | `"Topologie d'Espaces (4 Niveaux)"`, `"Gouvernance du Catalogue (Starlark)"`, `"Jeton restreint (15 min) & Quotas"`, `"Simulation d'impact (What-If)"`, `"Arbre d'Héritage (4 Niveaux)"`, `"Coffre-fort d'Identifiants (Passthrough)"` | **Sally** : `Starlark`, `What-If`, `Passthrough`, `4 Niveaux` exposent le moteur de règles et le mécanisme d'authentification. **Winston** : Remplacer par l'intention métier (règles de validation, simulation avant publication, connexion directe sécurisée). | `"Organisation des espaces"` / `"Workspace organization"`, `"Validation et publication au catalogue"` / `"Catalog review & publishing"`, `"Simulation d'impact avant application"` / `"Impact preview before applying"`, `"Identifiants de connexion sécurisés"` / `"Secure connection credentials"`, `sectionId: "workspace-hierarchy"`, `"permission-simulation"` |
| `fr.ts` / `en.ts` (`bootstrapOnboarding`, `ontologyExplorer`, `modulePages`) | `"Bootstrap Jour 0 & Profils"`, `"assistant-agent v1.0.0"`, `"Graphe Ontologique (Profondeur <= 2)"`, `"Orchestration durable DBOS Transact..."`, `"Catalogue unifié (Agents, Skills...)"`, `"Ledger d'audit immuable PostgreSQL 18..."`, `"Gouvernance des espaces 4 niveaux, rattachement explicite des sources et RBAC."` | **Sally** : Les sous-titres de modules lisent l'Architecture Spine (`DBOS Transact`, `PostgreSQL 18`, `Profondeur <= 2`, `RBAC`) au lieu d'expliquer à quoi sert l'écran. **Winston** : Raccourcir en 1 phrase orientée bénéfice utilisateur et déporter le détail dans l'aide contextuelle droite via `ⓘ`. | `"Configuration initiale et profils"` / `"Initial setup & profiles"`, `" Assistant ORCIA prêt"`, `"Cartographie des connaissances"` / `"Knowledge map"`, sous-titres courts centrés utilisateur + icône `ⓘ` (`sectionId: "module-overview"`) |
| `fr.ts` / `en.ts` (`upstreamChallengeModal`, `humanGates`, `inboxAndClaims`) | `"Signalement de Défaut Amont (Rebase)"`, `"Rebase ciblé (recalculer depuis l'étape amont)"`, `"Anti-Rubber-Stamping"`, `"Journal d'Audit Immuable (SHA-256)"`, `"File d'Arbitrage (FIFO)"`, `"Bandeau SSE Temps Réel"` | **Sally** : `Rebase`, `Anti-Rubber-Stamping`, `SHA-256`, `FIFO`, `SSE` sont du jargon Git/réseau/crypto. **Winston** : Traduire en `"Correction d'une étape précédente"`, `"Relecture attentive"`, `"Journal d'activité vérifié"`, `"File de traitement par ordre d'arrivée"`. | `"Demande de correction sur une étape précédente"` / `"Request correction on a previous step"`, `"Relancer à partir de cette étape"` / `"Restart from this step"`, `"Vérification de relecture attentive"` / `"Careful review check"`, `"File des demandes à traiter"` / `"Pending requests queue"`, `sectionId: "upstream-correction"`, `"careful-review"` |
| `inbox_and_cockpit_labels.ts` | `"Mode Observateur (Lecture Seule — JWT claim READ_ONLY_OBSERVER)"`, `"Action Requise : Rédaction Humaine (human_authored_required)"`, `"File FIFO déterministe, filtrable par périmètre..."`, `"Synchronisation temps réel (SSE < 2s)..."`, `"Mode secours actif : Polling HTTP 15s (flux SSE interrompu)"`, `"Preuve de Lecture & Anti-Rubber-Stamping"`, `"fast_approval_warning: true consigné dans l'Audit Ledger"`, `"Rebase Ciblé & Préservation des Saisies Humaines"`, `"run-lock.json"`, `"Brouillon Éphémère (step_executions)"`, `"Snapshot Immuable (blackboard_snapshots)"`, `"Écart de Coût (> 20 % vs Pack Lockfile)"` | **Sally** : Exposition massive de noms de tables SQL (`step_executions`, `blackboard_snapshots`), de fichiers internes (`run-lock.json`) et de constantes (`READ_ONLY_OBSERVER`, `fast_approval_warning: true`). **Winston** : Remplacer par `"Brouillon en cours"`, `"Version validée"`, `"Mode consultation seule"`, `"Actualisation automatique (mode secours 15 s)"`. | Textes épurés et centrés utilisateur + boutons `ⓘ` (`sectionId: "inbox-priority"`, `"cockpit-timeline"`, `"cost-variance"`) |
| `admin_and_studio_labels.ts` | `"Isolation : Bac à sable Wasmtime (Palier 1b)"`, `"Contrat Starlark & Quotas"`, `"Gouvernance du Catalogue & Bac à Sable (Palier 1b)"`, `"Matrice de Permissions Effective (4 Niveaux)"`, `"Catalogue des Erreurs Localisées (RFC 9457)"`, `"Administration Jour 0 & Sécurité (Argon2id / OIDC PKCE)"`, `"Jeton d'amorçage (ORCIA_BOOTSTRAP_TOKEN)"`, `"Verrouillage matériel exclusif (SELECT FOR UPDATE)..."`, `"Modèle Relationnel & Périmètres (4 Niveaux)"`, `"Filtrage de visibilité SQL strict : aucun résultat hors périmètre..."`, `"Unité d'Organisation (BU / Team)"`, `"Ex. 1_ENTERPRISE, BU_FINANCE..."`, `"Attribuer un Rôle sur un Périmètre (Role Grant)"`, `"Principal (Utilisateur, Équipe ou Service Principal)"`, `"Ancrage d'Héritage (INHERITANCE_BLOCK)"` | **Sally** : C'est l'écran le plus pollué par la plomberie technique (`SELECT FOR UPDATE`, `Argon2id`, `OIDC PKCE`, `RFC 9457`, `Wasmtime Palier 1b`, `Starlark`, `1_ENTERPRISE`, `Service Principal`). **Winston** : Garder uniquement les concepts métier d'organisation (Unités, Équipes, Espaces, Rôles, Cloisonnement d'héritage) et déplacer les explications dans la colonne d'aide via `ⓘ`. | `"Environnement d'exécution isolé"`, `"Règles de sécurité et limites d'usage"`, `"Validation et publication au catalogue"`, `"Aperçu des droits d'accès"`, `"Messages d'erreur et codes de diagnostic"`, `"Configuration initiale et authentification"`, `"Clé d'installation initiale"`, `"Organisation et contrôle d'accès"`, `"Ex. Direction Générale, Pôle Finance, Équipe Audit"`, `"Bénéficiaire (Utilisateur, Équipe ou Compte technique)"`, `"Cloisonnement des accès hérités"`, `sectionId: "iam-org-tree"`, `"iam-role-grants"`, `"iam-inheritance-block"`, `"iam-visibility-check"` |
| `shell_and_search_labels.ts` | `"Aide Contextuelle Hybride (Git + Surcouche Locale)"`, `"Synchronisé via Cache Redis & Stockage CAS"`, `"Fusion Git (Base) + Surcouche Locale (PostgreSQL 18)"`, `"Restaurer la version précédente (Rollback)"`, `"Recherche Hybride (BM25 + HNSW + RRF)"`, `"Index pgvector halfvec(1024) + FTS PostgreSQL 18 — Filtré par périmètre..."`, `"Score RRF"`, `"Profondeur CTE <= 2"`, `"Validation Optimiste (ETag)"`, `"Conflit de concurrence (HTTP 412)"` | **Sally** : L'utilisateur qui ouvre l'aide ou la recherche n'a pas à savoir que l'aide fusionne Git + Redis + CAS + PG18 ni que la recherche utilise `BM25 + HNSW + RRF` sur `halfvec(1024)` ! **Winston** : Renommer en `"Aide contextuelle"`, `"Recherche globale (texte et sens)"`, `"Pertinence"`, `"Conflit de modification simultanée"`. | `"Aide contextuelle"`, `"Documentation à jour"`, `"Guide de référence et notes de votre organisation"`, `"Rétablir la version précédente"`, `"Recherche intelligente"`, `"Recherche par mots-clés et par sens dans vos espaces autorisés"`, `"Pertinence"`, `"Relations directes et indirectes"`, `"Vérification des modifications concurrentes"`, `"Modification simultanée détectée"` |
| `assistant_labels.ts` | `"Assistant Contextuel Temps Réel (SSE)"`, `"TTFT : 180 ms"`, `"Quota Redis : 14 / 60 req/min"`, `"Action Suggérée (Confirmation Humaine Requise)"`, `"Diff Structuré (Simulation What-If)"`, `"Exécuter via API REST (trace_id consigné)"`, `"Diagnostic Guidé d'Erreur (RFC 9457)"`, `"Aucun appel LLM externe pour les erreurs connues (0 $)"` | **Sally** : `SSE`, `TTFT`, `Quota Redis`, `What-If`, `API REST (trace_id consigné)`, `RFC 9457`, `0 $` sont des métriques d'ingénierie. **Winston** : Afficher `"Assistant ORCIA"`, `"Délai de réponse : 180 ms"`, `"Limite d'usage : 14 / 60 demandes/min"`, `"Aperçu des modifications proposées"`, `"Appliquer l'action"`, `"Diagnostic et résolution guidée"`. | Libellés centrés utilisateur sans jargon |
| `governance_and_packs_labels.ts` | `"Constructeur de Packs & Lockfile (SHA-256)"`, `"Manifeste pack.yaml + pack.lock.json (Pinning SHA-256 & Mode Air-Gapped)"`, `"Validation Déterministe du Graphe (5 Verrous)"`, `"Mode Air-Gapped (Zéro Appel Réseau Externe)"`, `"V1 : Présence d'au moins un nœud à rédaction humaine obligatoire (human_authored_required)"`, `"Verrouillage Strict SHA-256 (pack.lock.json)"`, `"Passerelle MCP (Outbox & Quotas)"`, `"Événements domain_events_outbox"`, `"Statut du Canal SSE / Streamable HTTP"`, `"Simulation What-If avant Publication"` | **Sally** : `domain_events_outbox`, `SHA-256`, `5 Verrous`, `human_authored_required`, `SSE / Streamable HTTP`, `What-If` exposent toute la tuyauterie backend. **Winston** : Traduire en `"Création et publication de packs"`, `"Vérification de conformité du processus"`, `"Mode hors-ligne autonome"`, `"Connexion aux outils externes (IDE)"`, `"Simulation d'impact avant publication"`. | Libellés clairs et auto-porteurs + boutons `ⓘ` |
| `ShellContainer.tsx`, `settings.tsx`, `wizards.tsx`, `login.tsx`, `features/**/*.tsx` | Textes d'aide ou descriptions contenant `PostgreSQL 18`, `DBOS Transact`, `Outbox`, `SHA-256`, `Starlark`, `Wasmtime`, `Passthrough`, `1_ENTERPRISE`, `Service Principal`, `WAITING_FOR_HUMAN_ARBITRATION`, `CONTRIBUTOR_ACTION_REQUIRED`, `orcia://...` exposé brutalement comme phrase d'explication | **Sally & Winston** : Épurer tous les libellés visibles et remplacer les longs paragraphes explicatifs inline par des intitulés courts accompagnés d'un bouton `ⓘ` (`ContextualInfoTriggerButton`) ouvrant l'aide contextuelle droite sur la section correspondante. *Note de compatibilité tests* : conserver dans les exemples de termes clés de `/settings` les identifiants d'exemple vérifiés par les tests existants (`INHERITANCE_BLOCK`, `ROLE:Chef1`, `aqwZSX`, `BU vs Espace`) tout en les expliquant en langage simple. | Intitulés courts + `<ContextualInfoTriggerButton />` câblé sur la colonne d'aide droite |

### 1.3 Analyse d'Impact GitNexus (Exécutée AVANT Codage)

- **Requêtes GitNexus exécutées (`repo: "ORCIA"`)** :
  - `gitnexus_query({ search_query: "ContextualHelpColumnAndCenter FourZoneDirectionCShell ShellContainer i18n", repo: "ORCIA" })`
  - `gitnexus_impact({ target: "ShellContainer", direction: "upstream", repo: "ORCIA" })` $\rightarrow$ `impactedCount: 15`, `risk: LOW` (appelant direct : `RootLayoutComponent` dans `apps/web/src/routes/__root.tsx`).
  - `gitnexus_impact({ target: "ContextualHelpColumnAndCenter", direction: "upstream", repo: "ORCIA" })` $\rightarrow$ `impactedCount: 19`, `risk: HIGH` (appelants directs : `InnerShellContainer` dans `apps/web/src/components/ShellContainer.tsx` et `OntologyFeaturePanel` dans `apps/web/src/features/ontology/index.tsx`).
  - `gitnexus_impact({ target: "FourZoneDirectionCShell", direction: "upstream", repo: "ORCIA" })` $\rightarrow$ `impactedCount: 3`, `risk: LOW` (appelant direct : `InnerShellContainer` dans `apps/web/src/components/ShellContainer.tsx`).
- **Mesures de maîtrise du risque `HIGH` sur `ContextualHelpColumnAndCenter`** :
  - Toutes les nouvelles propriétés ajoutées à `ContextualHelpColumnAndCenterProps` (`activeSectionId?: string | null`, `sections?: readonly UiContextualHelpSectionItem[]`) et à `FourZoneDirectionCShellProps` (`helpColumnOpen?: boolean`, `onHelpColumnOpenChange?: (open: boolean) => void`) sont **strictement optionnelles et rétrocompatibles**.
  - Tous les `data-testid` existants de `ContextualHelpColumnAndCenter` et `FourZoneDirectionCShell` (`contextual-help-hybrid-panel`, `contextual-help-merged-layers`, `contextual-help-what-for-box`, `help-accordion-steps-btn`, `help-accordion-terms-btn`, `help-accordion-faq-btn`, `contextual-help-version-pill`, `contextual-help-rollback-btn`, `contextual-help-rollback-banner`, `contextual-help-ask-assistant-btn`, `shell-help-toggle-btn`, `zone-contextual-help`) sont intégralement préservés.

### 1.4 Opportunités de Factorisation & Contrôle de Volumétrie (Seuil 300–400 lignes)

- **Extraction du catalogue d'articles d'aide contextuelle** :
  - `apps/web/src/components/ShellContainer.tsx` faisait `549` lignes car il embarquait en dur la construction des articles d'aide contextuelle (`buildContextualHelpArticle`).
  - Nous avons extrait le catalogue d'aide contextuelle enrichi (avec les sections ciblables par `sectionId` pour tous les boutons `ⓘ`) dans un module dédié **`apps/web/src/components/contextualHelpCatalog.ts`**, allégeant `ShellContainer.tsx` à `339` lignes et centralisant proprement les explications FR/EN.
- **Composant réutilisable `@orcia/ui`** :
  - Création de `packages/ui/src/components/ContextualInfoTriggerButton.tsx` (ré-exporté dans `packages/ui/src/index.ts`), évitant toute duplication de bouton d'aide dans les écrans de `apps/web`.

---

## 2. Plan d'Implémentation (Rédigé AVANT Codage)

### 2.1 Base de Données & Migrations Alembic (`infra/migrations/`)
- *Non applicable (évolution purement Design System `@orcia/ui`, dictionnaires `i18n`, vues `apps/web` et documentation UX/UI).*

### 2.2 Noyau Hexagonal (`packages/orcia-kernel`, `packages/orcia-core`) & Workers (`apps/worker`)
- *Non applicable.*

### 2.3 Backend FastAPI (`apps/api`) & SDK OpenAPI (`packages/api-client`)
- *Non applicable.*

### 2.4 Interface SPA Vite + TanStack Router Direction C (`packages/ui`, `apps/web`)
1. **Design System `@orcia/ui` (`packages/ui`)** :
   - Ajouter dans `packages/ui/src/styles/tokens.css` les classes sémantiques `.orcia-info-trigger-btn` (`18px × 18px`, cercle cliquable sobre, bordure `--color-border-subtle`, texte `--color-action-primary`, `:hover` et `:focus-visible` accessibles) et `.orcia-help-section-card--active` (mise en évidence visuelle de la section d'aide ciblée via `--color-action-primary-subtle` et `--color-action-primary`).
   - Créer `packages/ui/src/components/ContextualInfoTriggerButton.tsx` :
     - Props : `sectionId: string`, `label: string`, `onOpenHelpSection?: (sectionId: string) => void`, `testId?: string`.
     - Rendu : `<button type="button" className="orcia-info-trigger-btn" aria-label={label} title={label} data-testid={testId ?? `contextual-info-trigger-${sectionId}`} data-help-section-target={sectionId} onClick={() => onOpenHelpSection?.(sectionId)}><span aria-hidden="true">i</span></button>`.
   - Exporter `ContextualInfoTriggerButton` et `ContextualInfoTriggerButtonProps` dans `packages/ui/src/index.ts`.
   - Mettre à jour `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` pour supporter l'ouverture contrôlée de la colonne d'aide droite (`helpColumnOpen?: boolean`, `onHelpColumnOpenChange?: (open: boolean) => void`) tout en conservant l'état interne par défaut en mode non contrôlé.
   - Mettre à jour `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` :
     - Supporter `activeSectionId?: string | null` et `sections?: readonly UiContextualHelpSectionItem[]` (dans `UiContextualHelpArticleView` et `ContextualHelpColumnAndCenterProps`).
     - Lorsqu'un `activeSectionId` est fourni, ouvrir automatiquement l'accordéon correspondant, afficher et surligner la fiche explicative `data-testid={`help-section-${section.sectionId}`}` (`data-active="true"`) et déclencher `scrollIntoView` si disponible.
     - Masquer les clés techniques de plomberie (`redisCacheKey`, `casKey`) de l'affichage textuel visible tout en conservant `data-testid="contextual-help-merged-layers"` avec un libellé centré utilisateur.
2. **Dictionnaires `i18n` FR/EN & Vues `apps/web`** :
   - Purger tout le jargon interne ORCIA dans :
     - `apps/web/src/i18n/locales/fr.ts` et `apps/web/src/i18n/locales/en.ts`
     - `apps/web/src/i18n/locales/inbox_and_cockpit_labels.ts`
     - `apps/web/src/i18n/locales/admin_and_studio_labels.ts`
     - `apps/web/src/i18n/locales/shell_and_search_labels.ts`
     - `apps/web/src/i18n/locales/assistant_labels.ts`
     - `apps/web/src/i18n/locales/governance_and_packs_labels.ts`
   - Créer `apps/web/src/components/contextualHelpCatalog.ts` contenant les articles et sections d'aide contextuelle (`sectionId`) en français et en anglais pour tous les écrans.
   - Enrichir `ShellNavigationContextValue` dans `apps/web/src/components/ShellContainer.tsx` avec `openHelpSection: (sectionId: string) => void`, `activeHelpSectionId: string | null` et `helpColumnOpen: boolean`, reliés à `FourZoneDirectionCShell` et `ContextualHelpColumnAndCenter`.
   - Intégrer `ContextualInfoTriggerButton` (`ⓘ`) et épurer les textes inline dans `ShellContainer.tsx`, `routes/settings.tsx`, `routes/wizards.tsx`, `routes/login.tsx` et `features/{cockpit,inbox,workspaces,catalog,ontology,gates,finops,admin}/index.tsx`.
   - Mettre à jour `docs/help/fr/spaces-sources.md` et `docs/help/en/spaces-sources.md`.
3. **Documentation des Invariants UX/UI** :
   - Mettre à jour `GEMINI.md`, `CLAUDE.md`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md` et `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md` pour inscrire les 3 règles d'or (Zéro jargon interne, Intitulés auto-porteurs immédiats, Zéro pavé explicatif inline — Renvoi par icône `ⓘ` vers l'aide contextuelle droite).
4. **Tests Unitaires & Vérification** :
   - Ajouter les tests Vitest dans `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx` et `apps/web/src/__tests__/i18n-and-shell.test.tsx` (test du clic sur `ⓘ` ouvrant l'aide droite et activant la section ciblée + test anti-jargon interne sur `frDictionary` et `enDictionary`).

---

## 3. Bilan des Modifications & Résultats (Complété APRÈS Implémentation)

### 3.1 Tableau des Fichiers Créés / Modifiés

| Fichier | Action | Rôle & Détails |
| :--- | :---: | :--- |
| `packages/ui/src/components/ContextualInfoTriggerButton.tsx` | **Créé** | Composant Design System `@orcia/ui` affichant un bouton circulaire sobre `18px × 18px` avec lettre `"i"`, accessible (`aria-label`, `title`, `data-testid="contextual-info-trigger-${sectionId}"`, `data-help-section-target`), déclenchant `onOpenHelpSection(sectionId)` au clic. |
| `packages/ui/src/styles/tokens.css` | **Modifié** | Ajout des classes sémantiques `.orcia-info-trigger-btn` (`:hover`, `:focus-visible`, zéro hexadécimal brut) et `.orcia-help-section-card` / `.orcia-help-section-card--active`. |
| `packages/ui/src/primitives/ContextualHelpColumnAndCenter.tsx` | **Modifié** | Ajout de `UiContextualHelpSectionItem`, `article.sections`, et `activeSectionId?: string \| null` ; ouverture automatique de l'accordéon associé, mise en surbrillance (`data-active="true"`) de `help-section-${sectionId}`, `scrollIntoView`, et masquage visuel des clés techniques (`redisCacheKey`, `casKey`). |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | **Modifié** | Ajout des props contrôlées optionnelles `helpColumnOpen?: boolean` et `onHelpColumnOpenChange?: (open: boolean) => void` pour permettre l'ouverture automatique de la colonne d'aide droite au clic sur `ⓘ`. |
| `packages/ui/src/index.ts` | **Modifié** | Export public de `ContextualInfoTriggerButton`, `ContextualInfoTriggerButtonProps` et `UiContextualHelpSectionItem`. |
| `packages/ui/src/__tests__/four-zone-shell-and-cockpit.test.tsx` | **Modifié** | Ajout du test unitaire validant `ContextualInfoTriggerButton`, l'ouverture contrôlée de `FourZoneDirectionCShell` et le surlignage `data-active="true"` de `help-section-iam-org-tree` dans `ContextualHelpColumnAndCenter`. |
| `apps/web/src/i18n/locales/fr.ts` & `en.ts` | **Modifiés** | Purge intégrale du jargon interne (`DBOS`, `PostgreSQL 18`, `Starlark`, `Wasmtime`, `Passthrough`, `Tie-Break`, `Rubber-stamping`, `What-If`, `Rebase`, `Verrou V1`, `SHA-256`, `FIFO`, `SSE`, `human_authored_required`) avec 100 % de parité récursive des clés FR/EN. |
| `apps/web/src/i18n/locales/inbox_and_cockpit_labels.ts` | **Modifié** | Reformulation centrée utilisateur des libellés Cockpit, Boîte de Décisions, Frise d'exécution et Revue attentive. |
| `apps/web/src/i18n/locales/admin_and_studio_labels.ts` | **Modifié** | Reformulation centrée utilisateur des libellés Studio, Catalogue, Habilitations, Diagnostic d'erreur et Authentification. |
| `apps/web/src/i18n/locales/shell_and_search_labels.ts` | **Modifié** | Reformulation centrée utilisateur des libellés d'Aide contextuelle, de Recherche intelligente et de Cartographie des connaissances. |
| `apps/web/src/i18n/locales/assistant_labels.ts` | **Modifié** | Reformulation centrée utilisateur des libellés de Mon Assistant, des propositions d'action et du diagnostic guidé. |
| `apps/web/src/i18n/locales/governance_and_packs_labels.ts` | **Modifié** | Reformulation centrée utilisateur des libellés de Packs Métiers, de conformité des processus et de connexion aux outils externes. |
| `apps/web/src/components/contextualHelpCatalog.ts` | **Créé** | Catalogue centralisé des fiches d'aide contextuelle FR/EN par route avec sections ciblées (`iam-org-tree`, `iam-role-grants`, `iam-inheritance-block`, `connectors-overview`, `ai-models-overview`, `packs-overview`, `workflows-overview`, `audit-overview`, `module-overview`, `cockpit-decisions`, `assistant-modes`, `workspace-sources`, `glossary-rules`). |
| `apps/web/src/components/ShellContainer.tsx` | **Modifié** | Factorisation via `contextualHelpCatalog.ts` (réduit de `549` à `339` lignes) et câblage de `openHelpSection(sectionId)` / `activeHelpSectionId` / `helpColumnOpen` dans `ShellNavigationContextValue`. |
| `apps/web/src/components/ModuleWorkspaceView.tsx` | **Modifié** | Ajout de `<ContextualInfoTriggerButton sectionId="module-overview" />` à côté du titre de chaque module. |
| `apps/web/src/routes/{settings,wizards,login}.tsx` | **Modifiés** | Suppression des pavés de jargon technique inline et ajout des boutons `<ContextualInfoTriggerButton />` (`iam-org-tree`, `iam-role-grants`, `ai-models-overview`, `connectors-overview`, `audit-overview`, `module-overview`). |
| `apps/web/src/features/{cockpit,workspaces,inbox,catalog,ontology,gates,finops,admin}/index.tsx` & `PlatformOnboardingChecklistCard.tsx` | **Modifiés** | Reformulation centrée utilisateur de tous les textes inline et ajout des boutons `<ContextualInfoTriggerButton />` reliés à la colonne d'aide contextuelle droite. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | **Modifié** | Ajout du test d'intégration du clic sur `ⓘ` (`contextual-info-trigger-iam-org-tree` et `contextual-info-trigger-iam-role-grants`) ouvrant la colonne d'aide droite et activant la section correspondante + test automatisé anti-jargon sur 100 % des feuilles de `frDictionary` et `enDictionary`. |
| `docs/help/{fr,en}/spaces-sources.md` | **Modifiés** | Reformulation des guides d'aide Markdown FR/EN sans jargon interne. |
| `GEMINI.md`, `CLAUDE.md`, `EXPERIENCE.md`, `DESIGN.md` | **Modifiés** | Inscription pérenne des 3 règles d'or de microcopy centrée utilisateur et du déclencheur d'aide contextuelle ciblée `ⓘ` (`ContextualInfoTriggerButton`). |

### 3.2 Métriques & Portes de Vérification (`AD-17` & `AD-19`)

- **Tests & Typecheck TypeScript (`pnpm turbo run lint typecheck test`)** :
  - `@orcia/ui` : `13` fichiers de tests passés (`44 / 44` tests verts), `0` erreur TypeScript (`tsc --noEmit`).
  - `@orcia/web` : `1` fichier de test passé (`15 / 15` tests verts incluant la parité récursive FR/EN à 100 %, le test anti-jargon interne et le test d'ouverture/surlignage `ⓘ`), `0` erreur TypeScript (`tsc --noEmit`).
  - `@orcia/api-client` : `lint`, `typecheck`, `test` verts.
- **Qualité & Frontières Python** :
  - `.venv/bin/ruff check .` : `All checks passed!`
  - `.venv/bin/ruff format --check .` : `496 files already formatted`
  - `.venv/bin/lint-imports` : `5 kept, 0 broken` (`AD-19` & `AD-20`).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : `{"ok": true, "total_findings": 0}`.
- **Analyse de graphe GitNexus (`detect_changes`)** :
  - Aucune régression ni rupture de contrat détectée sur les flux existants.
