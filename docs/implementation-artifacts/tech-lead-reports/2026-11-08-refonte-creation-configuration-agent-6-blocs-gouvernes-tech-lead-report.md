# 2026-11-08 — Refonte de la Création, Configuration et Gouvernance des Agents LLM en 6 Blocs (`🤖 Mes Agents`)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - `docs/implementation-artifacts/tech-lead-reports/2026-11-08-refonte-creation-configuration-agent-6-blocs-gouvernes-tech-lead-report.md`

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-refonte-creation-configuration-agent-6-blocs-gouvernes` (`Ajustement Transverse UX/UI Direction C + Noyau Hexagonal + E2E Playwright`)
- **Capacité(s)** : `CAP-091` & `CAP-090` (`FR-24`, `FR-36` — Gestion, création, configuration 6 blocs et gouvernance d'exécution des Agents LLM et Compétences) — classification : `feature` + `ux`
- **Auteur / Contexte** : Refonte complète du Studio de création et de configuration d'un **Agent LLM ORCIA** (`/agents`, `@orcia/ui`, `@orcia/api-client`, `orcia_api`, `orcia_core`) pour passer d'un simple formulaire 4 champs (avec fond semi-transparent défaillant) à un **Studio de Gouvernance en 6 Blocs** reflétant la nature exacte d'un Agent ORCIA (*capacité d'exécution bornée, cloisonnée cognitivement et subordonnée à l'humain*) et ses **6 conditions d'invocation dans `💬 Mon Assistant`**.
- **Branche dédiée** : `feat/agents-6-blocks-governance-studio`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Diagnostic du besoin et de la capture d'écran de création d'agent** :
  1. **Défaillances visuelles et ergonomiques sur le screenshot** :
     - Le voile et la surface de la modale utilisaient des variables CSS non résolues (`--orcia-surface-primary` non définie dans `tokens.css`, qui définit `--color-surface` et `--color-surface-elevated`), rendant le fond de la boîte de dialogue **transparent** et laissant transparaître le texte de l'état vide situé derrière (*Text Bleed*).
     - L'en-tête supérieur de `ModuleWorkspaceView` (*« Répertoire des agents, compétences et services connectés »*) faisait doublon avec l'en-tête de `AgentsAndSkillsManagerView` (*« 🤖 Mes Agents & Compétences (Skills) »*).
  2. **Écart fonctionnel entre le formulaire actuel (4 champs) et la définition d'un Agent LLM ORCIA (6 blocs + 6 pré-requis)** :
     - Dans ORCIA, un Agent LLM n'est ni un prompt partagé ni un robot autonome : c'est un **rôle métier spécialisé (*Persona*)** borné et gouverné par l'humain.
     - Sa création et sa configuration doivent structurer la saisie autour des **6 blocs fondamentaux** :
       - **Bloc A — Identité & Rôle métier (*Persona*)** : Nom, identifiant `@handle`, visibilité, **Posture** (`PRODUCER` producteur/co-constructeur vs `EVALUATOR_GATE` évaluateur/contradicteur *Blind/Edge/Compliance Hunter*), et **Rôle humain binôme** qui arbitre ses propositions (*PO/PM*, *Architecte*, *Tech Lead*, *RSSI/QA*).
       - **Bloc B — Moteur Cognitif (Modèle LLM, Effort & Budget)** : Sélection du modèle (`team_default` Par défaut équipe, `fast` Rapide, `deep` Profond, `discovery` Discovery), niveau d'effort cognitif (`default`, `simple`, `medium`, `complex`), **Température** (`0.0` imposé/recommandé pour un agent d'audit/Gate) et **Plafond de consommation de tokens (`max_tokens`)**.
       - **Bloc C — Instructions Système & Modes d'interaction** : Invite système saisie directement ou référencée via un fichier Markdown versionné (`prompt_ref`), **Modes d'invocation** supportés (`generer`, `corrections`, `section`) et **Mécanisme de dialogue** (`questionnaire_prealable`, `pause_par_bloc`, `direct`).
       - **Bloc D — Périmètre de Connaissance (*Ressources Internes / RAG & Ontologie*)** : Cloisonnement cognitif par sélection des **Sources documentaires autorisées** et rattachement au **Glossaire métier & Vues du graphe de connaissances** (`apis_adr`, `prd_regles_metier`, `securite_conformite`, `code_composants`).
       - **Bloc E — Boîte à Outils (*Toolbox MCP*) & Compétences (*Skills*)** : Sélection des *Skills* réutilisables et attribution des **Outils et connecteurs MCP** (*SearchTool*, *Jira*, *Confluence*, *Git*) avec droits d'action granulaires (`READ_ONLY` Lire uniquement vs `WRITE_PREVIEW` Écrire sous réserve de prévisualisation).
       - **Bloc F — Garde-fous (*Guardrails*) & Contrat de Sortie** : Règles de sécurité/conformité (*Citations vérifiables obligatoires*, *Aucun fait inventé*, *Lecture seule sur le code*, *Filtrage DCP/PII*, *Anti-Prompt Injection : le texte lu est une donnée*) et **Document & Gabarit de sortie** (`markdown_structure`, `confluence_draft`, `jira_draft`, `gate_risk_json`) + **Checklist des 6 conditions d'employabilité conversationnelle** (incluant la validation au Banc de Test).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `AgentsAndSkillsManagerView` (`packages/ui/src/components/AgentsAndSkillsManagerView.tsx`) : `impactedCount: 16`, `risk: LOW`, appelé directement (`d=1`) par `CatalogFeaturePanel` (`apps/web/src/features/catalog/index.tsx`).
  - `AgentsAndSkillsManagementService` (`packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`) : `impactedCount: 1`, `risk: LOW`.
  - `persist_agent_to_postgres18` (`packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py`) : `impactedCount: 1`, `risk: LOW`, appelé par `apps/api/src/orcia_api/routers/agents_and_skills.py`.
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 350–450` lignes par fichier)** :
  1. **Correction systémique des tokens de surface CSS (`packages/ui/src/styles/tokens.css`)** :
     - Définir les alias sémantiques `--orcia-surface-primary`, `--orcia-surface-secondary`, `--orcia-border-subtle`, `--orcia-text-primary`, `--orcia-text-secondary`, `--orcia-action-primary`, `--orcia-text-on-action` mappés sur les tokens Direction C (`--color-surface`, `--color-surface-elevated`, `--color-border`, `--color-foreground`, `--color-muted-foreground`, `--color-primary`, `--color-primary-foreground`) en modes Clair et Sombre. Cela élimine définitivement tout fond transparent (*Text Bleed*) sur l'ensemble des modales et cartes.
  2. **Découpage modulaire des 6 blocs UI dans `packages/ui/src/components/`** :
     - `AgentGovernanceTypesAndDefaults.ts` (`204` lignes) : Types stricts des 6 blocs, presets par posture (`PRODUCER` vs `EVALUATOR_GATE`), calcul déterministe des **6 conditions d'activation conversationnelle (`computeAgentReadinessChecklist`)**.
     - `AgentSixBlocksFormSections.tsx` (`438` lignes) : Rendu modulaire des Blocs A, B, C et de la jauge **Passeport de Gouvernance (6/6 conditions)**.
     - `AgentSixBlocksKnowledgeToolsGuardrailsSections.tsx` (`335` lignes) : Rendu modulaire des Blocs D, E et F.
     - `AgentAndSkillCreateForms.tsx` (`390` lignes) : Modale de création d'Agent en 6 blocs + barre d'outils `AgentsAndSkillsHeaderAndToolbar`.
     - `AgentDetailAndSandboxModal.tsx` (`405` lignes) : Modale d'édition complète des 6 blocs + **Banc de Test intégré (`Dry-Run`)** permettant de certifier l'agent (`test_bench_validated: true`).
     - `AgentStudioCardItem.tsx` (`338` lignes) : Carte d'agent affichant le Passeport Métier ORCIA (Posture, Binôme humain, Modèle/Température, Sources/Ontologie, Outils MCP Write-Preview, Gabarit de sortie, Statut Banc de Test).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Persistance PostgreSQL 18 (`sql_agents_and_skills.py`)
- Enrichissement 100 % rétrocompatible de `catalog_items.metadata_jsonb` (`item_type = 'USER_AGENT'`) avec les attributs des 6 blocs :
  - **Bloc A** : `posture` (`PRODUCER | EVALUATOR_GATE`), `human_partner_role` (`PO_PM | ARCHITECT | TECH_LEAD | SECURITY_QA | ALL`).
  - **Bloc B** : `llm_model_tier` (`team_default | fast | deep | discovery`), `temperature` (`float`, ex. `0.0` à `1.0`), `max_tokens` (`int`, ex. `4096`).
  - **Bloc C** : `prompt_ref` (`str | None`), `invocation_modes` (`tuple[str, ...]`), `dialogue_mechanism` (`questionnaire_prealable | pause_par_bloc | direct`).
  - **Bloc D** : `allowed_rag_sources` (`tuple[str, ...]`), `ontology_views` (`tuple[str, ...]`).
  - **Bloc E** : `mcp_tool_permissions` (`dict[str, str]`, ex. `{"jira": "WRITE_PREVIEW", "git": "READ_ONLY"}`).
  - **Bloc F & Activation** : `guardrails` (`tuple[str, ...]`), `output_contract_format` (`markdown_structure | confluence_draft | jira_draft | gate_risk_json`), `write_preview_required` (`bool`), `test_bench_validated` (`bool`).

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/`)
- Mise à jour de `ManagedAgentRecord` et `build_managed_agent_record` dans `agents_and_skills_models.py` et `AgentsAndSkillsManagementService` dans `agents_and_skills_manager.py` :
  - Prise en charge de tous les attributs des 6 blocs avec des valeurs par défaut saines et déterministes.
  - Lors de `execute_agent` (Banc de Test / Dry-Run), marquage automatique `test_bench_validated = True` sur l'agent et inclusion dans la synthèse de la posture, du binôme humain, du contrat de sortie, des sources RAG/Ontologie et du garde-fou `Write-Preview`.

### 2.3 Couche Backend API & Contrats OpenAPI (`apps/api/` & `packages/api-client/`)
- Enrichissement rétrocompatible de `AgentItemResponse`, `UpsertAgentRequest` et `ToggleAgentGovernanceRequest` dans `apps/api/src/orcia_api/schemas/agents_and_skills.py` et `apps/api/src/orcia_api/routers/agents_and_skills.py`.
- Régénération `0-diff` du schéma OpenAPI 3.1 (`scripts/export_openapi.py`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
- Correction des variables CSS dans `packages/ui/src/styles/tokens.css` pour garantir une opacité 100 % solide et un contraste optimal sur toutes les modales et cartes.
- Suppression du double en-tête redondant dans `ModuleWorkspaceView.tsx` lorsque `currentModule === "catalog"` (`/agents`).
- Refonte de `AgentCreateFormDrawer` et `AgentDetailAndSandboxModal` autour des **6 blocs gouvernés (A à F)** et de la **Jauge des 6 conditions d'utilisation dans Mon Assistant**.
- Enrichissement de `AgentStudioCardItem` et `PACK_AGENTS_BY_PACK_KEY` (`packAgentsCatalog.ts`) pour que les agents des Packs (`@architecte-solution`, `@analyste-metier`, `@reviseur-qualite`) exposent nativement leur configuration 6 blocs exemplaire.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5)
- **Couche 1a (Pytest)** : `tests/unit/test_agents_and_skills_router_and_service.py` enrichi pour tester la création, la persistance JSONB, la duplication et la validation au Banc de Test des 6 blocs.
- **Couche 1b (Vitest)** : `packages/ui/src/__tests__/agents-and-skills.test.tsx` enrichi pour tester la navigation dans les 6 blocs, les pré-réglages de posture (`EVALUATOR_GATE` $\rightarrow$ température `0.0`), les outils MCP (`WRITE_PREVIEW`), les garde-fous et la checklist 6/6.
- **Couche 2 (Intégration PostgreSQL 18)** : `tests/integration/test_http_vertical_day0_and_agents_postgres18.py`.
- **Couche 3 (Contrats OpenAPI `0-diff` & `lint-imports`)** : Vérification complète.
- **Couche 5 (Playwright E2E `apps/web/e2e/08-agents-skills-persistence.spec.ts`)** : Parcours E2E complet testant l'ouverture du studio 6 blocs, le paramétrage des blocs (Identité/Posture, Moteur cognitif, Instructions/Modes, Périmètre RAG/Ontologie, Toolbox MCP Write-Preview, Garde-fous & Contrat de sortie), la persistance PostgreSQL 18 après vidage du stockage local et vrai rechargement `F5`, ainsi que la validation au Banc de Test.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Créés & Modifiés

| Fichier | Action | Lignes | Responsabilité |
| :--- | :--- | :---: | :--- |
| `packages/ui/src/styles/tokens.css` | Modifié | `~310` | Alias CSS `--orcia-surface-primary`, `--orcia-surface-secondary`, `--orcia-border-subtle`, `--orcia-text-primary`, `--orcia-text-secondary` et classes utilitaires `.bg-[var(--orcia-surface-primary)]`, `.w-[960px]`, `.max-h-[680px]` éliminant toute transparence de modale (*Text Bleed*). |
| `packages/ui/src/components/AgentGovernanceTypesAndDefaults.ts` | Créé | `204` | Types stricts des 6 blocs ORCIA (`UiAgentPosture`, `UiAgentHumanPartnerRole`, `UiAgentLlmModelTier`, `UiAgentDialogueMechanism`, `UiAgentOutputContractFormat`), valeurs par défaut et `computeAgentReadinessChecklist` (6 conditions d'invocation dans `💬 Mon Assistant`). |
| `packages/ui/src/components/AgentSixBlocksFormSections.tsx` | Créé | `438` | Barre de navigation des 6 blocs (`🅰 Identité` $\rightarrow$ `🅵 Garde-fous`), checklist interactive des 6 conditions d'employabilité conversationnelle, et rendu des Blocs A, B et C (avec passage automatique `temperature = 0.0` sur posture `EVALUATOR_GATE`). |
| `packages/ui/src/components/AgentSixBlocksKnowledgeToolsGuardrailsSections.tsx` | Créé | `335` | Rendu modulaire des Blocs D (Cloisonnement RAG & Ontologie), E (Compétences `/skills` & Outils MCP `NONE \| READ_ONLY \| WRITE_PREVIEW`) et F (Garde-fous & Contrat de sortie). |
| `packages/ui/src/components/AgentAndSkillCreateForms.tsx` | Modifié | `390` | Modale de création d'Agent en 6 blocs (`w-[960px] max-h-[680px]`, surface 100 % opaque `--color-surface-card`) + barre d'outils `AgentsAndSkillsHeaderAndToolbar` avec bouton `📦 Charger les Agents des Packs`. |
| `packages/ui/src/components/AgentDetailAndSandboxModal.tsx` | Modifié | `405` | Modale d'inspection/édition des 6 blocs + **Banc de Test intégré (`Dry-Run`)** validant l'agent (`🧪 Validé au Banc de Test` / `test_bench_validated = true`). |
| `packages/ui/src/components/AgentStudioCardItem.tsx` | Modifié | `338` | Carte d'agent affichant le **Passeport de Gouvernance 6 Blocs** (Posture Producteur vs Évaluateur Gate, Binôme humain, Modèle/Température/Plafond tokens, Sources RAG & Vues Ontologiques, Outils MCP Write-Preview, Gabarit de sortie, Statut Banc de Test). |
| `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` | Modifié | `494` | Orchestration des 3 onglets, transmission complète des attributs des 6 blocs lors de la création et de la mise à jour d'un agent. |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_models.py` | Modifié | `445` | Enrichissement de `ManagedAgentRecord` et `build_managed_agent_record` avec les 14 attributs des 6 blocs gouvernés. |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py` | Modifié | `312` | Support complet des 6 blocs dans `create_agent`, `duplicate_agent`, `update_agent_governance` et certification automatique `test_bench_validated = True` lors de `execute_agent`. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py` | Modifié | `434` | Persistance et réhydratation PostgreSQL 18 des 6 blocs dans `catalog_items.metadata_jsonb`. |
| `apps/api/src/orcia_api/schemas/agents_and_skills.py` | Modifié | `204` | Schémas Pydantic v2 `AgentItemResponse`, `UpsertAgentRequest` et `ToggleAgentGovernanceRequest` exposant les 6 blocs. |
| `apps/api/src/orcia_api/routers/agents_and_skills.py` | Modifié | `346` | Câblage des routes `GET/POST/PATCH /api/v1/agents-and-skills/agents` et persistance `test_bench_validated=True` sur `POST /agents/{id}/execute`. |
| `scripts/export_openapi.py` & `packages/api-client/` | Modifiés | `256` | Régénération `0-diff` du schéma OpenAPI 3.1 et des types TypeScript (`@orcia/api-client`). |
| `apps/web/src/components/ModuleWorkspaceView.tsx` | Modifié | `92` | Suppression du double en-tête redondant sur `/agents` (`currentModule === "catalog"`). |
| `apps/web/src/features/catalog/packAgentsCatalog.ts` & `useManagedAgentsAndSkills.ts` | Modifiés | `~290` / `~580` | Enrichissement des agents des Packs (`@architecte-solution`, `@analyste-metier`, `@reviseur-qualite`) et synchronisation API/cache des 6 blocs. |
| `apps/web/e2e/08-agents-skills-persistence.spec.ts` | Modifié | `194` | Test End-to-End Playwright complet validant le Studio 6 Blocs, l'opacité de la modale, le passage en posture `EVALUATOR_GATE` (`temperature = 0`), la persistance PostgreSQL 18 après vrai `F5`, et la validation au Banc de Test. |

### 3.2 Validation des 5 Couches de Tests (`AD-17`) & Garde-Fous CI

1. **Couche 1a — Tests Unitaires Python & Couverture ($\ge 90\%$)** :
   - `.venv/bin/pytest tests/unit/test_agents_and_skills_router_and_service.py tests/unit/test_codebase_architectural_anti_patterns_audit.py tests/unit/test_capabilities_registry.py --cov=orcia_core.orchestration.agents_and_skills_models --cov=orcia_core.orchestration.agents_and_skills_manager --cov-fail-under=90` : **`18 passed`**, couverture **`98.45 %`** (`agents_and_skills_models.py` : `100 %`, `agents_and_skills_manager.py` : `97 %`).
2. **Couche 1b — Tests Composants & Intégration Frontend (`Vitest`)** :
   - `pnpm turbo run lint typecheck test` : **`9/9` tâches vertes** (`@orcia/api-client`, `@orcia/ui` `17/17` fichiers / `73/73` tests passés dont `agents-and-skills.test.tsx`, `@orcia/web` `9/9` fichiers / `53/53` tests passés).
3. **Couche 2 — Intégration Verticale HTTP $\rightarrow$ FastAPI $\rightarrow$ PostgreSQL 18 (`testcontainers`)** :
   - `.venv/bin/pytest tests/integration/test_http_vertical_day0_and_agents_postgres18.py -k test_agent_creation_http_persists_in_catalog_items` : **`1 passed`** (vérifie par `SELECT metadata_jsonb FROM catalog_items` que `posture="EVALUATOR_GATE"`, `output_contract_format="gate_risk_json"` et `test_bench_validated=True` sont persistés dans PostgreSQL 18).
4. **Couche 3 — Contrats d'Architecture & Qualité Statique** :
   - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **`0` erreur**.
   - `.venv/bin/mypy --strict packages/orcia-core/src apps/api/src apps/worker/src` : **`Success: no issues found in 243 source files`**.
   - `.venv/bin/lint-imports` : **`5 kept, 0 broken`**.
5. **Couche 5 — Parcours End-to-End Playwright (`apps/web/e2e/08-agents-skills-persistence.spec.ts`)** :
   - `pnpm --filter @orcia/web exec playwright test e2e/08-agents-skills-persistence.spec.ts` : **`1 passed (7.3s)`** sur conteneurs éphémères PostgreSQL 18 + Redis 7.4.
