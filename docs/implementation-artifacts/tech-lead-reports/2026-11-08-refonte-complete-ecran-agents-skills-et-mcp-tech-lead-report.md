# 2026-11-08 — Refonte Complète de l'Écran « 🤖 Mes Agents, Compétences & Serveurs MCP » (`EXPERIENCE.md` §2.2 & Principe M)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - `docs/implementation-artifacts/tech-lead-reports/2026-11-08-refonte-complete-ecran-agents-skills-et-mcp-tech-lead-report.md`

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-refonte-complete-ecran-agents-skills-et-mcp` (`Ajustement Transverse UX/UI Direction C + Noyau Hexagonal`)
- **Capacité(s)** : `CAP-091` (`FR-36` — Refonte complète de l'écran Agents, Skills et MCP, en complément de `CAP-090` et `CAP-082`)
- **Classification** : `feature` + `ux`
- **Auteur / Contexte** : Refonte complète de l'écran `🤖 Mes Agents` (`/agents`, `CatalogFeaturePanel` & `@orcia/ui`) suite à la revue critique avec Sally (`🎨 UX Designer`) et Winston (`🏗️ System Architect`). Repart du besoin métier fondamental des agents dans ORCIA (`FR-1`, `FR-3`, `FR-10`, `FR-11`, `FR-36`, `AD-6`, `AD-12`, `AD-14`, `AD-15`, `AD-21`, `EXPERIENCE.md` §2.2, `DESIGN.md` Principe C / Principe M).
- **Branche dédiée** : `feat/agents-skills-mcp-screen-overhaul`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Diagnostic de l'écran précédent (`AgentsAndSkillsManagerView`)** :
  1. **Formulaire de création ouvert en permanence en haut de page** (`isCreateAgentOpen = true`, `isCreateSkillOpen = true`), en violation directe du **Principe C de `DESIGN.md`** (*« création d'entités exclusivement par Modale dédiée au clic sur `+ Nouvel agent`, jamais de formulaire géant ouvert en permanence sur un écran de liste »*).
  2. **Surcharge visuelle $N \times M$ sur chaque carte d'agent** : toutes les compétences (`Skills`) de l'espace étaient affichées sous forme de cases à cocher (`checkbox`) directement sur chaque carte de la liste, et un champ de saisie « mini-chat » (`Saisissez une demande concrète... [⚡ Exécuter l'Agent]`) était dupliqué sur chaque carte alors que l'utilisation conversationnelle quotidienne se déroule dans **`💬 Mon Assistant`** (`@agent`) et l'exécution de processus dans **`☍ Mes Processus`**.
  3. **Absence de gouvernance des ressources issues des Packs Métiers (`📦 Pack`)** : un bouton artificiel `📦 Charger les Agents & Compétences des Packs Métiers` encombrait la barre de filtre (au lieu d'exposer d'office les agents/compétences des Packs actifs de l'Espace), et les cartes des agents de Pack affichaient un bouton destructif `Supprimer` au lieu de protéger les ressources de Pack (`ERR_PACK_RESOURCE_IMMUTABLE` — uniquement activables/désactivables sur l'Espace ou duplicables/personnalisables).
  4. **Absence de la Carte n°1 épinglée `🤖 Assistant de l'Espace` et du 3ᵉ onglet `🔌 Serveurs d'outils & MCP`** : pourtant requis par `EXPERIENCE.md` §2.2 (`Carte n°1 épinglée 🤖 Assistant de l'Espace`, onglets `Agents (@)` | `Compétences (/skills)` | `Serveurs d'outils & MCP` avec le Banc de Test en 4 étapes `🔌` et l'exposition MCP vers les IDE).
- **Comportement cible validé (Sally 🎨 & Winston 🏗️)** :
  1. **Structure en 3 onglets visibles** : `🤖 Agents (@)` | `🛠️ Compétences (/skills)` | `🔌 Serveurs d'outils & MCP` + Recherche et pilules de filtre (`Tous`, `📦 Packs Métiers`, `👥 Équipe / Espace`, `🔒 Privés`) sans bouton parasite de chargement manuel des packs.
  2. **Carte n°1 épinglée `🤖 Assistant de l'Espace` (`@assistant`)** : toujours affichée en tête de l'onglet `Agents (@)`, présentant le chef d'orchestre par défaut de l'Espace avec ses actions rapides (`💬 Ouvrir Mon Assistant`, `⚙ Réglages de l'assistant`, `🔌 Exposer en MCP` avec copie de la configuration IDE).
  3. **Cartes d'Agents et de Compétences sobres (Loi de Hick)** :
     - Affichent en lecture rapide (< 2s) : Nom, `@handle` (ou `/commande`) copiables en 1 clic, badge d'origine (`📦 Pack Métier`, `👥 Équipe`, `🔒 Privé`, `🌐 Distant MCP/A2A`), badge d'état (`🟢 Actif sur l'espace` / `⏸️ Désactivé sur l'espace`), badge de palier de réflexion (`⚡ Rapide`, `⚖️ Équilibré`, `🧠 Approfondi`, `✨ Auto`), mission métier en 1–2 lignes, et **pastilles de compétences rattachées en lecture seule** (`🛠️ /revue-architecture`, etc., sans checkboxes envahissantes).
     - **Actions claires sur chaque carte** :
       - Action primaire : **`💬 Utiliser dans Mon Assistant`** (pré-remplit `@handle ` et ouvre `Mon Assistant`).
       - Action secondaire : **`⚙️ Configurer & Tester`** (ouvre la **Modale d'Inspection, d'Édition & de Bac à sable Dry-Run** de l'agent ou de la compétence).
       - Gouvernance selon l'origine :
         - Pour un agent/skill **issu d'un Pack Métier (`PACK`)** : **aucun bouton `Supprimer`** ; boutons **`📋 Dupliquer & Personnaliser`** (crée une copie/surcharge éditable dans l'Espace) et **`⏸️ Désactiver sur l'espace` / `▶️ Activer sur l'espace`**.
         - Pour un agent/skill **créé par l'utilisateur ou l'équipe (`PRIVATE` / `TEAM`)** : édition complète, bascule de visibilité (`🔒 Privé` $\leftrightarrow$ `👥 Équipe`), duplication et suppression.
  4. **Création, Édition et Bac à Sable (`Dry-Run`) en Modale dédiée** :
     - Cliquer sur **`+ Nouvel Agent`** ou **`+ Nouvelle Compétence`** ouvre une **Modale dédiée** (fermable via `Escape` ou `Annuler`).
     - Cliquer sur **`⚙️ Configurer & Tester`** sur une carte ouvre la **Modale / Fiche détaillée** de l'agent (ou de la compétence) permettant de : (a) consulter/modifier le nom, le rôle, le palier cognitif, la visibilité, les instructions complètes et les compétences rattachées, (b) configurer l'exposition MCP (`🔌 Exposer cet agent en MCP`), et (c) exécuter un **Essai à chaud (`▷ Bac à sable / Dry-Run`)** avec trace des compétences mobilisées et rendu Markdown structuré.
  5. **3ᵉ Onglet `🔌 Serveurs d'outils & MCP` actif et intégré** :
     - Intègre directement le **Banc de Test & Découverte Automatique en 4 étapes (`🔌`)** (`1. Réseau/TLS/Anti-SSRF`, `2. Authentification`, `3. Découverte tools/list & qualification Lecture seule vs Action Staged`, `4. Essai à chaud Dry-Run & télémétrie FinOps`) ainsi que le panneau d'**Exposition MCP Gouvernée vers les IDE externes** (Cursor, VS Code, Claude Code, Antigravity) avec copie en 1 clic du snippet JSON IDE.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `AgentsAndSkillsManagementService` (`packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`, **475 lignes** $\rightarrow$ dépassait le seuil de `300–400` lignes !) : `impactedCount: 2` (`orchestration/__init__.py`, `sql_agents_and_skills.py`) + `apps/api/src/orcia_api/routers/agents_and_skills.py` (**370 lignes**).
  - `AgentsAndSkillsManagerView` (`packages/ui/src/components/AgentsAndSkillsManagerView.tsx`, **332 lignes**) : `impactedCount: 16` (`CatalogFeaturePanel` dans `apps/web/src/features/catalog/index.tsx` à `d=1`, `ModuleWorkspaceView` à `d=2`, routes TanStack Router `/agents` et `/catalog` à `d=3`).
  - `useManagedAgentsAndSkills` (`apps/web/src/features/catalog/useManagedAgentsAndSkills.ts`, **349 lignes**).
- **Opportunités de Factorisation & Résorption de Dette Technique (Découpage `< 350` lignes)** :
  1. **Backend Core (`packages/orcia-core/src/orcia_core/orchestration/`)** :
     - Découper `agents_and_skills_manager.py` (`475` lignes) en :
       - `agents_and_skills_models.py` (`319` lignes) : dataclasses immuables (`ManagedSkillRecord`, `ManagedAgentRecord`, `SkillExecutionOutcome`, `InvokedSkillTraceItem`, `AgentExecutionOutcome`, types `AgentThinkingLevel`, `AgentSkillVisibilityScope`, `AgentKindType`, helpers `normalize_identifier_slug`, `compute_payload_sha256`).
       - `agents_and_skills_manager.py` (`319` lignes) : service métier `AgentsAndSkillsManagementService` enrichi de la gouvernance des origines (`PRIVATE`, `TEAM`, `PACK`), de l'état d'activation par espace (`enabled_in_workspace: bool`), de l'exposition MCP (`mcp_exposed: bool`), de l'interdiction de suppression d'une ressource `PACK` (`ValidationDomainError`), et des actions `duplicate_agent()`, `set_agent_enabled()` et `set_agent_mcp_exposure()`.
  2. **UI Design System (`packages/ui/src/components/`)** :
     - Découper proprement les composants de `🤖 Mes Agents` pour qu'aucun fichier ne dépasse `320` lignes :
       - `WorkspaceAssistantPinnedCard.tsx` (`73` lignes) : Carte n°1 épinglée `🤖 Assistant de l'Espace (@assistant)`.
       - `AgentStudioCardItem.tsx` (`283` lignes) : Carte sobre d'Agent spécialisé (pastilles de skills en lecture seule, badges d'origine/palier/MCP, actions `💬 Utiliser dans Mon Assistant`, `⚙️ Configurer & Tester`, `📋 Dupliquer & Personnaliser`, `⏸️ Activer/Désactiver` ou `Supprimer`).
       - `SkillStudioCardItem.tsx` (`171` lignes) : Carte sobre de Compétence (`/skill`) avec actions `💬 Utiliser dans Mon Assistant`, `⚙️ Configurer & Tester` et `Supprimer` (uniquement hors `PACK`).
       - `AgentDetailAndSandboxModal.tsx` (`262` lignes) : Modale unifiée d'édition complète, d'attachement 1-clic des compétences, d'exposition MCP et de **Bac à sable Dry-Run** d'un Agent.
       - `SkillDetailAndSandboxModal.tsx` (`175` lignes) : Modale unifiée d'inspection et de **Bac à sable Dry-Run** d'une Compétence.
       - `AgentsAndSkillsManagerView.tsx` (`317` lignes) : Orchestrateur des 3 onglets (`🤖 Mes Agents`, `🛠️ Compétences (Skills)`, `🔌 Serveurs d'outils & MCP`), des compteurs KPI sobres (masqués si `total == 0`), des filtres pilules et des modales.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Persistance PostgreSQL 18 (`sql_agents_and_skills.py`)
- Aucune nouvelle table hors des 18 tables de l'ERD (`ARCHITECTURE-SPINE.md`) : la persistance dans `catalog_items` (`item_type IN ('USER_SKILL', 'USER_AGENT')`, `metadata_jsonb`) est enrichie de manière 100 % rétrocompatible avec les champs `visibility_scope` (`PRIVATE | TEAM | PACK`), `source_pack_key`, `enabled_in_workspace` (`bool`), `mcp_exposed` (`bool`), `agent_kind` (`LOCAL | REMOTE_MCP_A2A`) et `remote_endpoint_url`.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/`)
- Extraction de `agents_and_skills_models.py` et enrichissement de `AgentsAndSkillsManagementService` :
  - Support natif de `visibility_scope` (`PRIVATE | TEAM | PACK`), `source_pack_key`, `enabled_in_workspace`, `mcp_exposed`, `agent_kind` (`LOCAL | REMOTE_MCP_A2A`), `remote_endpoint_url`.
  - Protection matérielle contre la suppression d'un agent ou d'une compétence d'origine `PACK` (`delete_agent` / `delete_skill` lève `ValidationDomainError` si `visibility_scope == "PACK"`).
  - Méthodes `duplicate_agent(agent_id, new_name=..., visibility_scope=...)` (permettant de cloner un agent de Pack en agent `TEAM` ou `PRIVATE` personnalisable), `set_agent_enabled(agent_id, enabled=...)` et `set_agent_mcp_exposure(agent_id, mcp_exposed=...)`.

### 2.3 Couche Backend API & Contrats OpenAPI (`apps/api/` & `packages/api-client/`)
- Mise à jour rétrocompatible de `apps/api/src/orcia_api/schemas/agents_and_skills.py` (`202` lignes) et `apps/api/src/orcia_api/routers/agents_and_skills.py` (`328` lignes) :
  - Ajout des champs optionnels avec valeurs par défaut (`visibility_scope`, `source_pack_key`, `enabled_in_workspace`, `mcp_exposed`, `agent_kind`, `remote_endpoint_url`) dans `AgentItemResponse`, `UpsertAgentRequest`, `SkillItemResponse`, `UpsertSkillRequest`.
  - Ajout des endpoints `POST /api/v1/agents-and-skills/agents/{agent_id}/duplicate` (`DuplicateAgentRequest`) et `PATCH /api/v1/agents-and-skills/agents/{agent_id}/governance` (`ToggleAgentGovernanceRequest`), régénération `0-diff` du SDK OpenAPI 3.1 (`scripts/export_openapi.py`) et câblage dans `packages/api-client/src/domains/agentsAndSkills.ts`.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
- Refonte de `AgentsAndSkillsManagerView` et de ses sous-composants dans `packages/ui` :
  - **En-tête conforme au Principe C** : Titre + phrase d'intention + **3 onglets visibles** (`🤖 Mes Agents`, `🛠️ Compétences (Skills)`, `🔌 Serveurs d'outils & MCP`) + bouton primaire contextuel (`+ Nouvel Agent`, `+ Nouvelle Compétence`, `🔌 Tester & Découvrir un serveur MCP`).
  - **Bandeau de 3 compteurs KPI sobres** (`agents-kpi-strip`, affiché uniquement dès que `agents.length + skills.length >= 1`, masqué à vide `total == 0`).
  - **Barre de recherche & Pilules de filtrage** (`Tous`, `📦 Packs Métiers`, `👥 Équipe`, `🔒 Privés`) — suppression visuelle du bouton manuel « Charger les Packs », les agents et compétences des Packs actifs sur l'Espace étant exposés automatiquement.
  - **Carte n°1 épinglée `🤖 Assistant de l'Espace`** (`WorkspaceAssistantPinnedCard.tsx`) en haut de l'onglet `Agents (@)`.
  - **Cartes d'Agents et de Compétences épurées** (`AgentStudioCardItem.tsx`, `SkillStudioCardItem.tsx`) + **Modales dédiées** (`role="dialog"`, `aria-modal="true"`, fermeture `Escape` / `Annuler`) pour la création (`+ Nouvel Agent`, `+ Nouvelle Compétence`) et pour la configuration/test (`⚙️ Configurer & Tester` $\rightarrow$ `AgentDetailAndSandboxModal.tsx`, `SkillDetailAndSandboxModal.tsx`).
  - **3ᵉ onglet `🔌 Serveurs d'outils & MCP` visible et câblé** sur `RemoteServiceTestBenchAndMcpExposureView` dans `CatalogFeaturePanel`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Créés et Modifiés

| Fichier | Nature | Lignes | Description des modifications |
| :--- | :--- | :---: | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_models.py` | **Créé** | `319` | Extraction des types (`AgentThinkingLevel`, `AgentSkillVisibilityScope`, `AgentKindType`), des dataclasses immuables (`ManagedSkillRecord`, `ManagedAgentRecord`, `SkillExecutionOutcome`, `InvokedSkillTraceItem`, `AgentExecutionOutcome`) et des constructeurs déterministes. |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py` | **Modifié** | `319` | Découpage sous `320` lignes, protection matérielle des ressources `PACK` contre la suppression (`ValidationDomainError`), et ajout de `duplicate_agent()`, `set_agent_enabled()` et `set_agent_mcp_exposure()`. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py` | **Modifié** | `315` | Sérialisation et hydratation PostgreSQL 18 de `visibility_scope`, `source_pack_key`, `enabled_in_workspace`, `mcp_exposed`, `agent_kind` et `remote_endpoint_url` dans `catalog_items.metadata_jsonb`. |
| `apps/api/src/orcia_api/schemas/agents_and_skills.py` | **Modifié** | `202` | Enrichissement rétrocompatible des schémas Pydantic v2 (`SkillItemResponse`, `AgentItemResponse`, `UpsertSkillRequest`, `UpsertAgentRequest`) et ajout de `DuplicateAgentRequest` et `ToggleAgentGovernanceRequest`. |
| `apps/api/src/orcia_api/routers/agents_and_skills.py` | **Modifié** | `328` | Ajout des routes `POST /api/v1/agents-and-skills/agents/{agent_id}/duplicate` et `PATCH /api/v1/agents-and-skills/agents/{agent_id}/governance` avec persistance PostgreSQL 18. |
| `packages/api-client/src/domains/agentsAndSkills.ts` & `src/generated/*` | **Modifié** | `120` | Régénération `0-diff` du contrat OpenAPI 3.1 (`DuplicateAgentRequest`, `ToggleAgentGovernanceRequest`) et ajout de `duplicateAgent()` et `updateAgentGovernance()` dans le SDK typé `@orcia/api-client`. |
| `packages/ui/src/components/WorkspaceAssistantPinnedCard.tsx` | **Créé** | `73` | Carte n°1 épinglée `🤖 Assistant de l'Espace (@assistant)` avec bascule `🔌 Exposer en MCP`, bouton `⚙ Réglages de l'assistant` et CTA `💬 Ouvrir Mon Assistant →`. |
| `packages/ui/src/components/AgentDetailAndSandboxModal.tsx` | **Créé** | `262` | Modale accessible (`role="dialog"`, `Escape`) d'inspection/édition d'Agent, de rattachement 1-clic des compétences, d'exposition MCP et de Bac à sable d'essai à chaud (`Dry-Run`). |
| `packages/ui/src/components/SkillDetailAndSandboxModal.tsx` | **Créé** | `175` | Modale accessible (`role="dialog"`, `Escape`) d'inspection et de Bac à sable d'essai à chaud (`Dry-Run`) d'une Compétence (`/skill`). |
| `packages/ui/src/components/AgentAndSkillCreateForms.tsx` & `SkillCreateFormDrawer.tsx` | **Modifié** | `245` / `250` | En-tête Direction C à **3 onglets visibles** (`🤖 Mes Agents`, `🛠️ Compétences (Skills)`, `🔌 Serveurs d'outils & MCP`), bandeau de 3 compteurs KPI sobres et modales de création fermées par défaut (`isCreateAgentOpen = false`, `isCreateSkillOpen = false`). |
| `packages/ui/src/components/AgentStudioCardItem.tsx` & `SkillStudioCardItem.tsx` | **Modifié** | `283` / `171` | Cartes épurées (pastilles de skills en lecture seule, badges d'origine `📦 Pack Métier` / `👥 Équipe` / `🔒 Privé`, absence de `Supprimer` sur `PACK`, boutons `📋 Dupliquer & Personnaliser`, `⏸️ Désactiver sur l'espace` et `⚙️ Configurer & Tester`). |
| `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` | **Modifié** | `317` | Orchestration des 3 onglets, de la carte épinglée `WorkspaceAssistantPinnedCard`, des modales de création/détail et du panneau `connectionsContent`. |
| `apps/web/src/features/catalog/useManagedAgentsAndSkills.ts` & `index.tsx` | **Modifié** | `317` / `318` | Chargement automatique des agents/compétences des Packs actifs, câblage SDK de `duplicateAgent` / `updateAgentGovernance`, et intégration du Banc de Test MCP en 4 étapes dans le 3ᵉ onglet `🔌 Serveurs d'outils & MCP`. |
| `tests/unit/test_agents_and_skills_router_and_service.py` & `packages/ui/src/__tests__/agents-and-skills.test.tsx` | **Modifié** | `235` / `310` | Tests unitaires et d'intégration couvrant l'immuabilité des ressources `PACK` (`422`), la duplication 1-clic, la gouvernance (`enabled_in_workspace`, `mcp_exposed`), les modales RGAA (`Escape`), la carte épinglée `@assistant` et les 3 onglets visibles. |

### 3.2 Métriques, Validation des 5 Couches (`AD-17`) & Garde-Fous
- **Qualité & Typage Python** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **0 erreur**.
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : **0 erreur (`220` fichiers vérifiés)**.
  - `.venv/bin/lint-imports` : **5 contrats respectés, 0 contrat brisé**.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **0 finding**.
- **Tests Backend & Registre des Capacités (`CAP-091`)** :
  - `test_agents_and_skills_router_and_service.py`, `test_codebase_architectural_anti_patterns_audit.py`, `test_capabilities_registry.py` : **100 % PASS**.
  - `pnpm site:sync` & `pnpm site:check` : **OK (`CAP-091` vérifié)**.
- **Qualité, Typage & Tests Frontend (`pnpm turbo run lint typecheck test`)** :
  - `@orcia/ui` (`29` fichiers de tests, `agents-and-skills.test.tsx` `9/9`), `@orcia/api-client`, `@orcia/web` (`13` fichiers de tests, `40/40` dans `i18n-and-shell.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` `4/4`) : **9/9 tâches Turborepo PASS (`0` erreur)**.
