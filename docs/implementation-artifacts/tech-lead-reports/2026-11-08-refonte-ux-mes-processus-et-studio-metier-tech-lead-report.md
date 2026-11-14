# Rapport Tech Lead — Refonte UX « Mes Processus », Séparation Exécution/Studio & Éradication du Jargon Technique

- **Date** : 2026-11-08
- **Auteur** : Antigravity (Tech Lead / Sally UX & Winston Architect)
- **Branche Git** : `feat/processes-ux-cleanup-and-usages`
- **Classification** : `ux`
- **Capacité(s)** : `CAP-140`, `CAP-150`
- **Périmètre** : `apps/web/src/router.tsx`, `apps/web/src/features/processes/ProcessesHubPage.tsx`, `apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx`, `apps/web/src/features/processes/studio/WorkflowFiveBlocksCanvas.tsx`, `apps/web/src/features/processes/studio/StudioCopilotSidebar.tsx`, `apps/web/src/features/processes/vsm/ValueStreamMapView.tsx`, `apps/web/src/features/processes/vsm/StepDetailSheet.tsx`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Diagnostic UX & Architecture sur les 3 écrans (« Sapin de Noël »)
1. **Empilement de 2 écrans contradictoires sur `/processes`** :
   - `apps/web/src/router.tsx` montait simultanément `<ProcessesHubPage />` ET `<ModuleWorkspaceView moduleKey="gates" />` (`GatesWorkspacePage`) sur la route `/processes`.
   - Cela produisait un écran vertical de **11 blocs hétérogènes** mélangeant : la Chaîne de Valeur (VSM), les workflows unitaires, un ancien formulaire manuel de création de processus, l'atelier de création de Packs Métiers et le générateur de fiches d'aide contextuelle.
2. **Inversion des usages (le Studio mis au premier plan au lieu de l'Exécution opérationnelle)** :
   - Dans « Mes Processus », cliquer sur **« Exécuter »** redirigeait vers `/processes/studio/$workflowId` (l'atelier de conception Studio) au lieu de permettre à l'utilisateur de **suivre, reprendre, lancer et arbitrer ses dossiers en cours** directement depuis son espace opérationnel « Mes Processus ».
3. **Exposition brute de la plomberie technique dans l'interface métier** :
   - Omniprésence d'identifiants et concepts d'infrastructure réservés au moteur backend : `NIVEAU 1 — CHAÎNE DE VALEUR INTERACTIVE (MACRO-VSM)`, `packs/sdlc/workflows/vsm-mon-compte-idea-to-prod.yaml`, `Niveau 2 — Workflows Exécutables Unitaires Bornés (DBOS Transact)`, `Checkpoint Humain DBOS.recv`, `DBOS.send`, `Sortie S3 Claim-Check`, `ClaimCheckPointer S3 : s3://...`, `SHA-256: ...`, `WritePreviewCard Requise`, `packages/orcia-connectors`, `markdown_contract_runner · retries=3`, `0 Token LLM • Auto-Heal max 3x`, `WAITING_SUBSTEP_HITL`, `run-wf-01-qualification-prd-01:qualification:iter-1`.

### 1.2 Hiérarchie des usages cibles dans « Mes Processus » (`/processes`)
1. **Usage 1 (Principal — 80 % du temps) : Suivre, reprendre, arbitrer et lancer mes processus métiers**
   - Voir immédiatement le dossier en cours ou lancer un processus directement sur place (avec ouverture immédiate de l'espace de suivi & validation du livrable `InteractiveRunDrawer` directement dans `/processes`, sans basculer dans le Studio).
2. **Usage 2 (Secondaire — 15 % du temps) : Comprendre la Chaîne de Valeur de bout en bout (VSM)**
   - Parcourir les 4 phases (*01 Émergence & Cadrage*, *02 Priorisation & Engagement*, *03 Réalisation*, *04 Livraison*) et explorer la carte interactive des 11 étapes (`/processes/vsm/$vsmId`).
3. **Usage 3 (Adaptation — 5 % du temps) : Adapter un processus dans le Studio (`/processes/studio/$workflowId`)**
   - Bouton secondaire discret (*« Adapter dans le Studio »*) menant à un atelier épuré en langage métier clair.

### 1.3 Analyse d'Impact GitNexus & Contrôle de Volumétrie
- `apps/web/src/router.tsx` (167 lignes) : retrait de `<ModuleWorkspaceView moduleKey="gates" />` de `processesRoute` (`/gates` conserve son montage dédié pour `GatesWorkspacePage`).
- `apps/web/src/features/processes/ProcessesHubPage.tsx` (~326 lignes) : refonte autour des 3 usages (1. Dossiers en cours & Lancement direct sur place avec `InteractiveRunDrawer` intégré, 2. Catalogue des processus métiers par étape, 3. Bandeau synthétique de la Chaîne de Valeur) + déclencheurs d'aide contextuelle `ⓘ`.
- `apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx` (~540 lignes $\rightarrow$ allégé sous 400 lignes) : transformation en **Espace de Suivi & Validation de Livrable** 100 % métier (suppression visuelle des URI `s3://`, `ClaimCheckPointer`, `DBOS.send`, `WAITING_SUBSTEP_HITL`).
- `apps/web/src/features/processes/studio/WorkflowFiveBlocksCanvas.tsx` (~769 lignes $\rightarrow$ allégé) & `StudioCopilotSidebar.tsx` (~253 lignes) : remplacement des titres `BLOC 1..5` techniques par des intitulés métiers clairs et des étiquettes lisibles pour les outils (Jira, Confluence, Git) et les savoir-faire.

---

## 2. Plan d'Implémentation

### 2.1 Migrations Alembic & Schéma SQL
- Aucune migration SQL requise (refonte UX/UI purement frontend sur les surfaces existantes `CAP-140` et `CAP-150`).

### 2.2 Noyau Hexagonal & Workers
- Aucun changement backend requis ; tous les contrats API v2 (`/api/v1/packs`, `/api/v1/workflows/vsm`, `/api/v1/workflows/bounded`) restent intacts.

### 2.3 Backend FastAPI & SDK OpenAPI
- Aucun changement de contrat OpenAPI.

### 2.4 Interface SPA Vite + TanStack Router (Direction C)
1. **`apps/web/src/router.tsx`** :
   - Sur `/processes`, rendre uniquement `<ProcessesHubPage />` (suppression de l'empilement `<ModuleWorkspaceView moduleKey="gates" />`).
2. **`apps/web/src/features/processes/ProcessesHubPage.tsx`** :
   - **Section 1 (Priorité 1) : « Dossiers en cours & Lancement rapide »** — permet de reprendre en 1 clic le dossier actif ou de lancer n'importe quel processus directement dans « Mes Processus » via `InteractiveRunDrawer` sans quitter la page.
   - **Section 2 : « Processus métiers disponibles »** — cartes claires en français métier avec libellés d'agents lisibles (*Agent Product Owner*, *Agent Architecte*, *Agent Business Analyst*, *Sas Développement & Revue*, *Agent Rédacteur Documentaire*), bouton principal **« ▷ Lancer ce processus »** (exécution directe sur place) et bouton secondaire discret **« Adapter dans le Studio »**.
   - **Section 3 : « Chaîne de valeur — De l'idée à la production (4 phases · 11 étapes) »** — vue synthétique des 4 phases et accès à la carte interactive complète.
3. **`apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx`** :
   - Remplacement des badges bruts (`WAITING_SUBSTEP_HITL`, `ClaimCheckPointer S3`, `DBOS.send`, `Anchor Card Souveraine — 4 Actions d'Arbitrage sur Diff S3`) par des libellés métiers clairs (*« En attente de validation »*, *« Livrable produit »*, *« Valider cette étape »*, *« Décision finale sur le livrable »*) tout en préservant les `data-testid` requis par les tests d'intégration et de bout-en-bout.
4. **`apps/web/src/features/processes/studio/WorkflowFiveBlocksCanvas.tsx` & `StudioCopilotSidebar.tsx`** :
   - Remplacement du jargon technique (`BLOC 1..5`, `DBOS.recv`, `Sortie S3 Claim-Check`, `markdown_contract_runner`, `mcp:atlassian-jira (write_preview)`) par un vocabulaire métier destiné aux Product Owners et Architectes.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Fichiers Modifiés
| Fichier | Action | Description |
| :--- | :--- | :--- |
| `apps/web/src/router.tsx` | Modifié | Suppression de l'empilement `<ModuleWorkspaceView moduleKey="gates" />` sous `<ProcessesHubPage />` sur la route `/processes`. |
| `apps/web/src/features/processes/ProcessesHubPage.tsx` | Modifié | Hiérarchisation autour des 3 usages réels : **1. Mes dossiers en cours & validations à traiter** (ouverture directe de `InteractiveRunDrawer` sur place), **2. Processus métiers disponibles par étape** (langage 100 % métier, bouton primaire *« ▷ Lancer ce processus »*, bouton secondaire *« Adapter dans le Studio »*), **3. Vue d'ensemble de la chaîne de valeur (4 phases · 11 étapes)**. |
| `apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx` | Modifié | Transformation en espace métier de suivi et validation de livrable : stepper visuel par sous-étape, suppression visuelle des URI `s3://`, `ClaimCheckPointer`, `DBOS.send`, `WAITING_SUBSTEP_HITL`, et actions de décision en français clair. |
| `apps/web/src/features/processes/studio/WorkflowFiveBlocksCanvas.tsx` | Modifié | Remplacement du jargon technique (`BLOC 1..5`, `DBOS`, `S3 Claim-Check`, `markdown_contract_runner`, `0 Token LLM • Auto-Heal max 3x`) par des intitulés métiers destinés aux Product Owners et Architectes. |
| `apps/web/src/features/processes/studio/StudioCopilotSidebar.tsx` | Modifié | Remplacement des identifiants techniques bruts (`mcp:atlassian-jira (write_preview)`, `pack://sdlc/skills/...`) par des libellés métiers explicites (*Jira — Création de ticket (sous validation)*, *Rédaction du PRD & priorisation WSJF*, etc.). |
| `apps/web/src/__tests__/epics-14-15-process-studio-v2-and-declarative-packs.test.tsx` | Modifié | Ajout d'assertions vérifiant l'absence des anciens panneaux empilés sur `/processes`, l'absence du jargon `DBOS Transact` et l'ouverture directe d'un dossier dans `/processes` sans redirection vers le Studio. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modifié | Mise à jour de la vérification de navigation `/processes` (vue épurée `ProcessesHubPage`) et `/gates` (`GatesWorkspacePage`). |

### 3.2 Résultats des Tests & Gates Qualité
- **Vitest (`epics-14-15`, `i18n-and-shell`, `zero-dead-buttons-and-silent-catches-audit`, `design-system-look-and-feel-isolation`)** : `4 test files passed, 40 tests passed`.
- **`pnpm lint` & `pnpm typecheck`** : `0 erreur`.
- **`pnpm site:sync` & `pnpm site:check`** : `OK`.
