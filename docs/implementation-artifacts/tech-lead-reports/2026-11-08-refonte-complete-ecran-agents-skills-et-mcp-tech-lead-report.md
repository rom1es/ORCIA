# 2026-11-08 — Refonte Complète de l'Écran « 🤖 Mes Agents, Compétences & Serveurs MCP » (`EXPERIENCE.md` §2.2 & Principe M)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - `docs/implementation-artifacts/tech-lead-reports/2026-11-08-refonte-complete-ecran-agents-skills-et-mcp-tech-lead-report.md`

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-refonte-complete-ecran-agents-skills-et-mcp` (`Ajustement Transverse UX/UI Direction C + Noyau Hexagonal`)
- **Auteur / Contexte** : Refonte complète de l'écran `🤖 Mes Agents` (`/agents`, `CatalogFeaturePanel` & `@orcia/ui`) suite à la revue critique avec Sally (`🎨 UX Designer`) et Winston (`🏗️ System Architect`). Repart du besoin métier fondamental des agents dans ORCIA (`FR-1`, `FR-3`, `FR-10`, `FR-11`, `AD-6`, `AD-12`, `AD-14`, `AD-15`, `AD-21`, `EXPERIENCE.md` §2.2, `DESIGN.md` Principe C / Principe M).
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
       - Action primaire : **`💬 Discuter dans Mon Assistant`** (pré-remplit `@handle ` et ouvre `Mon Assistant`).
       - Action secondaire : **`⚙️ Configurer & Tester`** (ouvre la **Modale / Tiroir d'Inspection, d'Édition & de Bac à sable Dry-Run** de l'agent ou de la compétence).
       - Gouvernance selon l'origine :
         - Pour un agent/skill **issu d'un Pack Métier (`PACK`)** : **aucun bouton `Supprimer`** ; boutons **`📋 Dupliquer / Personnaliser`** (crée une copie/surcharge éditable dans l'Espace) et **`⏸️ Désactiver sur l'espace` / `▶️ Réactiver`**.
         - Pour un agent/skill **créé par l'utilisateur ou l'équipe (`PRIVATE` / `TEAM`)** : édition complète, bascule de visibilité (`🔒 Privé` $\leftrightarrow$ `👥 Équipe`), duplication et suppression.
  4. **Création, Édition et Bac à Sable (`Dry-Run`) en Modale / Tiroir dédié** :
     - Cliquer sur **`+ Nouvel agent`** ou **`+ Nouvelle compétence`** ouvre une **Modale dédiée** (fermable via `Escape` ou `Annuler`).
     - Cliquer sur **`⚙️ Configurer & Tester`** sur une carte ouvre la **Modale / Fiche détaillée** de l'agent (ou de la compétence) permettant de : (a) consulter/modifier le nom, le rôle, le palier cognitif, la visibilité, les instructions complètes et les compétences rattachées, (b) configurer l'exposition MCP (`🔌 Exposer en MCP`), et (c) exécuter un **Essai à chaud (`▷ Bac à sable / Dry-Run`)** avec trace des compétences mobilisées et rendu Markdown structuré.
  5. **3ᵉ Onglet `🔌 Serveurs d'outils & MCP` actif et intégré** :
     - Intègre directement le **Banc de Test & Découverte Automatique en 4 étapes (`🔌`)** (`1. Réseau/TLS/Anti-SSRF`, `2. Authentification`, `3. Découverte tools/list & qualification Lecture seule vs Action Staged`, `4. Essai à chaud Dry-Run & télémétrie FinOps`) ainsi que le panneau d'**Exposition MCP Gouvernée vers les IDE externes** (Cursor, VS Code, Claude Code, Antigravity) avec copie en 1 clic du snippet JSON IDE.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `AgentsAndSkillsManagementService` (`packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`, **475 lignes** $\rightarrow$ dépasse le seuil de `300–400` lignes !) : `impactedCount: 2` (`orchestration/__init__.py`, `sql_agents_and_skills.py`) + `apps/api/src/orcia_api/routers/agents_and_skills.py` (**370 lignes**).
  - `AgentsAndSkillsManagerView` (`packages/ui/src/components/AgentsAndSkillsManagerView.tsx`, **332 lignes**) : `impactedCount: 16` (`CatalogFeaturePanel` dans `apps/web/src/features/catalog/index.tsx` à `d=1`, `ModuleWorkspaceView` à `d=2`, routes TanStack Router `/agents` et `/catalog` à `d=3`).
  - `useManagedAgentsAndSkills` (`apps/web/src/features/catalog/useManagedAgentsAndSkills.ts`, **349 lignes**).
- **Opportunités de Factorisation & Résorption de Dette Technique (Découpage `< 350` lignes)** :
  1. **Backend Core (`packages/orcia-core/src/orcia_core/orchestration/`)** :
     - Découper `agents_and_skills_manager.py` (`475` lignes) en :
       - `agents_and_skills_models.py` : dataclasses immuables (`ManagedSkillRecord`, `ManagedAgentRecord`, `SkillExecutionOutcome`, `InvokedSkillTraceItem`, `AgentExecutionOutcome`, types `AgentThinkingLevel`, `AgentSkillOriginScope`, `AgentKindType`, helpers `normalize_identifier_slug`, `compute_payload_sha256`).
       - `agents_and_skills_manager.py` (`< 320` lignes) : service métier `AgentsAndSkillsManagementService` enrichi de la gouvernance des origines (`PRIVATE`, `TEAM`, `PACK`), de l'état d'activation par espace (`enabled_in_workspace: bool`), de l'exposition MCP (`mcp_exposed: bool`), de l'interdiction de suppression d'une ressource `PACK` (`ValidationDomainError` / `ERR_PACK_RESOURCE_IMMUTABLE`), et de l'action `duplicate_agent()` / `toggle_agent_enabled()`.
  2. **UI Design System (`packages/ui/src/components/`)** :
     - Découper proprement les composants de `🤖 Mes Agents` pour qu'aucun fichier ne dépasse `300` lignes :
       - `WorkspaceAssistantPinnedCard.tsx` : Carte n°1 épinglée `🤖 Assistant de l'Espace (@assistant)`.
       - `AgentStudioCardItem.tsx` : Carte sobre d'Agent spécialisé (pastilles de skills en lecture seule, badges d'origine/palier/MCP, actions `💬 Discuter`, `⚙️ Configurer & Tester`, `📋 Dupliquer`, `⏸️ Activer/Désactiver` ou `Supprimer`).
       - `SkillStudioCardItem.tsx` : Carte sobre de Compétence (`/skill`) avec actions `💬 Utiliser dans Mon Assistant`, `⚙️ Configurer & Tester`, `📋 Dupliquer` / `Supprimer`.
       - `AgentDetailAndSandboxModal.tsx` : Modale / Tiroir unifié de création, d'édition complète, d'attachement 1-clic des compétences, d'exposition MCP et de **Bac à sable Dry-Run** d'un Agent.
       - `SkillDetailAndSandboxModal.tsx` : Modale / Tiroir unifié de création, d'édition et de **Bac à sable Dry-Run** d'une Compétence.
       - `AgentsAndSkillsManagerView.tsx` : Orchestrateur des 3 onglets (`🤖 Agents (@)`, `🛠️ Compétences (/skills)`, `🔌 Serveurs d'outils & MCP`), des compteurs KPI sobres (masqués si `total == 0`), des filtres pilules et des modales.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Persistance PostgreSQL 18 (`sql_agents_and_skills.py`)
- Aucune nouvelle table hors des 18 tables de l'ERD (`ARCHITECTURE-SPINE.md`) : la persistance dans `catalog_items` (`item_type IN ('USER_SKILL', 'USER_AGENT')`, `metadata_jsonb`) est enrichie de manière 100 % rétrocompatible avec les champs `visibility_scope` (`PRIVATE | TEAM | PACK`), `source_pack_key`, `enabled_in_workspace` (`bool`), `mcp_exposed` (`bool`) et `agent_kind` (`LOCAL | REMOTE_MCP_A2A`).

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/`)
- Extraction de `agents_and_skills_models.py` et enrichissement de `AgentsAndSkillsManagementService` :
  - Support natif de `visibility_scope` (`PRIVATE | TEAM | PACK`), `source_pack_key`, `enabled_in_workspace`, `mcp_exposed`, `agent_kind` (`LOCAL | REMOTE_MCP_A2A`), `remote_endpoint_url`.
  - Protection matérielle contre la suppression d'un agent ou d'une compétence d'origine `PACK` (`delete_agent` / `delete_skill` lève `ValidationDomainError` si `visibility_scope == "PACK"`).
  - Méthodes `duplicate_agent(agent_id, new_name=...)` (permettant de cloner un agent de Pack en agent `TEAM` ou `PRIVATE` personnalisable) et `set_agent_enabled(agent_id, enabled=...)`.

### 2.3 Couche Backend API & Contrats OpenAPI (`apps/api/`)
- Mise à jour rétrocompatible de `apps/api/src/orcia_api/schemas/agents_and_skills.py` et `apps/api/src/orcia_api/routers/agents_and_skills.py` :
  - Ajout des champs optionnels avec valeurs par défaut (`visibility_scope`, `source_pack_key`, `enabled_in_workspace`, `mcp_exposed`, `agent_kind`, `remote_endpoint_url`) dans `AgentItemResponse`, `UpsertAgentRequest`, `SkillItemResponse`, `UpsertSkillRequest`.
  - Ajout de l'endpoint `POST /api/v1/agents-and-skills/agents/{agent_id}/duplicate` pour cloner/personnaliser en 1 clic un agent (notamment issu d'un Pack Métier) et persister la copie dans PostgreSQL 18.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
- Refonte de `AgentsAndSkillsManagerView` et de ses sous-composants dans `packages/ui` :
  - **En-tête conforme au Principe C** : Titre + phrase d'intention + **3 onglets visibles** (`🤖 Agents (@)`, `🛠️ Compétences (/skills)`, `🔌 Serveurs d'outils & MCP`) + bouton primaire contextuel (`+ Nouvel Agent`, `+ Nouvelle Compétence`, `+ Tester un serveur MCP`).
  - **Bandeau de 3 compteurs KPI sobres** (affiché uniquement dès que `agents.length + skills.length >= 1`, masqué à vide `total == 0`).
  - **Barre de recherche & Pilules de filtrage** (`Tous`, `📦 Packs Métiers`, `👥 Équipe / Espace`, `🔒 Privés`) — suppression visuelle du bouton parasite « Charger les Packs », les agents et compétences des Packs actifs sur l'Espace étant exposés nativement dès qu'un Pack est actif (et avec un pack SDLC actif par défaut dès qu'un espace de travail ou pack est initialisé, tout en préservant l'état vide au Jour 0 strict).
  - **Carte n°1 épinglée `🤖 Assistant de l'Espace`** en haut de l'onglet `Agents (@)`.
  - **Cartes d'Agents et de Compétences épurées** + **Modales/Tiroirs dédiés** pour la création (`+ Nouvel Agent`, `+ Nouvelle Compétence`) et pour la configuration/test (`⚙️ Configurer & Tester`).
  - **3ᵉ onglet `🔌 Serveurs d'outils & MCP` visible et câblé** sur `RemoteServiceTestBenchAndMcpExposureView` dans `CatalogFeaturePanel`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

*(À compléter après exécution des sous-agents et passage des 5 couches de vérification `AD-17`)*
