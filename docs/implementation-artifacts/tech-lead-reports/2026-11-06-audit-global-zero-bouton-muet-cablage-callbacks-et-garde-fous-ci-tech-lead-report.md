# Rapport d'Analyse & d'Implémentation Tech Lead — Audit Global des Anomalies d'Actions Silencieuses, Câblage Vertical des Callbacks & Garde-Fous CI Anti-Régression

- **Date** : 2026-11-06
- **Périmètre** : Audit transversal de toute la codebase (`packages/ui`, `apps/web`, `packages/api-client`, `apps/api`, `packages/orcia-core`, `tests/`, `GEMINI.md` / `CLAUDE.md`)
- **Auteurs** : Tech Lead / Dev Senior (Winston — Architecte & Sally — UX/UI)
- **Statut** : Validé & Déployé (`AD-17` / `AD-19` / Garde-Fou n°5)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Pourquoi l'anomalie « Envoyer à Mon Assistant ne répond rien » n'avait-elle pas été détectée par la CI ?

L'analyse post-mortem révèle **4 angles morts structurels** dans nos tests et notre câblage entre les Epics 9, 10, 11 et 12 :

1. **Angle mort n°1 — Tests de composants `@orcia/ui` isolés (`packages/ui/src/__tests__/`) vs Montage réel dans `apps/web/src/`** :
   - Les primitives `@orcia/ui` ont été développées et testées unitairement dans `packages/ui/src/__tests__/` en leur passant des callbacks factices (`onSendTurn={vi.fn()}`, `onCreateBusinessPack={vi.fn()}`, `onRunTestBench={vi.fn()}`) et des props pré-remplies.
   - Or, lorsque `Story 12.1`, `12.2` et `12.3` ont monté ces primitives dans `apps/web/src/features/*` et `apps/web/src/components/ShellContainer.tsx`, les tests de `apps/web` ont vérifié la **présence visuelle** des composants (`getByTestId(...)`) et la **survie au `F5`** du `platformSetupStore`, **sans cliquer sur chaque bouton d'action secondaire** ni vérifier que chaque prop de callback optionnelle (`onRunTestBench?: () => void`, `onCreateBusinessPack?: ...`, `onCompileFromNorm?: ...`, `onTriggerSpeed2Now?: ...`) était effectivement renseignée par le conteneur parent dans `apps/web`.
2. **Angle mort n°2 — Court-circuit `if (isJsdom)` dans `apps/web` masquant les erreurs de contrat HTTP (`422` / `.catch(() => undefined)`)** :
   - Dans `apps/web/src/features/inbox/index.tsx` et `apps/web/src/features/catalog/index.tsx`, un bloc `if (isJsdom) { ... return; }` court-circuitait l'appel `@orcia/api-client` pendant les tests Vitest/JSDOM et mettait à jour un état local simulé (`setStreamedText("[SPEED_1_FAST] ...")`).
   - Conséquence : en test Vitest, le clic semblait réussir, tandis qu'en vrai navigateur (`!isJsdom`), l'appel partait vers FastAPI, échouait en `422 Unprocessable Entity` si le champ était vide, et tombait dans `.catch(() => undefined)` qui avalait l'erreur en silence.
3. **Angle mort n°3 — Props de callbacks optionnelles (`?:`) dans `@orcia/ui` permettant d'omettre le câblage sans erreur TypeScript (`mypy` / `tsc`)** :
   - Dans plusieurs primitives `@orcia/ui` (`PackBuilderProcessesStudioView`, `HelpArticleGeneratorAndValidatorView`, `RemoteServiceTestBenchAndMcpExposureView`, `DnaStarlarkCompilerAndGlossaryLifecycleView`, `WorkspaceFiveTabsAndExternalRebaseView`, `AssistantGovernanceModalAndStudio`, `TopHeaderSearchCommand`), les callbacks d'action étaient déclarés optionnels (`onCreateBusinessPack?: ...`).
   - TypeScript (`pnpm turbo run typecheck`) ne signalait donc aucune erreur lorsque `GatesFeaturePanel`, `WorkspacesFeaturePanel`, `CatalogFeaturePanel`, `InboxFeaturePanel` ou `ShellContainer` omettaient de passer ces callbacks.
4. **Angle mort n°4 — Services d'orchestration utilisant le port LLM par défaut au lieu du pont LLM configuré à chaud dans `Configuration -> Modèles IA`** :
   - Le pont `invoke_configured_llm_for_assistant_turn` (`assistant_llm_bridge.py`) a été branché sur `Mon Assistant` (`/api/v1/assistant/three-speed/turn`), mais **`POST /api/v1/agents-and-skills/agents/{agent_id}/execute`** et **`POST /api/v1/agents-and-skills/skills/{skill_id}/execute`** dans `apps/api/src/orcia_api/routers/agents_and_skills.py` n'utilisaient pas encore ce pont LLM à chaud lorsqu'un modèle réel (comme `gemma4:12b` sur Ollama) est configuré par l'utilisateur.

---

### 1.2 Audit Exhaustif de Toute la Codebase — Cartographie des Anomalies Identifiées

Nous avons audité **l'intégralité des 20 routes / écrans de `apps/web`**, des **46 primitives de `packages/ui/src/primitives/`** et des **24 routeurs FastAPI de `apps/api/src/orcia_api/routers/`**. Voici la liste exhaustive des anomalies de même nature détectées dans la codebase :

| # | Écran / Fichier (`apps/web` & `@orcia/ui`) | Bouton / Action Utilisateur | Anomalie Détectée lors de l'Audit | Correction Prévue |
| :- | :--- | :--- | :--- | :--- |
| **A1** | **`🤖 Mes Agents` (`/agents`, `/catalog`)**<br>`apps/web/src/features/catalog/index.tsx`<br>`apps/api/src/orcia_api/routers/agents_and_skills.py`<br>`packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py` | **1.** Tester un Agent (`🤖 Exécuter l'agent`) ou une Compétence (`🛠️ Exécuter`)<br>**2.** Banc de test MCP/A2A (`🔌 Lancer le test & découvrir`, `Activer le connecteur`, `Exposer en MCP`) | **1.** `execute_agent_endpoint` et `execute_skill_endpoint` n'appelaient pas le pont LLM configuré (`gemma4:12b` / Ollama) et `catalog/index.tsx` avalait les erreurs (`.catch(() => undefined)`).<br>**2.** `RemoteServiceTestBenchAndMcpExposureView` était monté aux lignes `455–464` **sans** `onRunTestBench` (le bouton `Lancer le test & découvrir` n'apparaissait même pas !) et **sans** `onActivateService` (cliquer sur `Activer le connecteur` ne faisait rien). | **1.** Câbler `invoke_configured_llm_for_assistant_turn` dans `agents_and_skills.py` (`execute_agent` + `execute_skill` enrichi) et afficher l'état de chargement / erreur dans `catalog/index.tsx`.<br>**2.** Câbler `onRunTestBench`, `onActivateService` et `onToggleMcpExposure` sur `@orcia/api-client` (`runRemoteServiceTestBench` + activation + retour visuel immédiat). |
| **A2** | **`☍ Mes Processus` (`/processes`, `/gates`)**<br>`apps/web/src/features/gates/index.tsx`<br>`PackBuilderProcessesStudioView.tsx`<br>`HelpArticleGeneratorAndValidatorView.tsx` | **1.** `PackBuilderProcessesStudioView` : bouton `Créer le Pack Métier` (`process1-create-pack-btn`) et `Promouvoir vers le Pack` (`process4-promote-btn`)<br>**2.** `HelpArticleGeneratorAndValidatorView` : bouton `Générer et rattacher la fiche d'aide` (`generate-and-attach-help-btn`) | **1.** Dans `GatesFeaturePanel` (`gates/index.tsx:75-81`), `PackBuilderProcessesStudioView` était monté **sans** `onCreateBusinessPack` ni `onPromoteAssetToPack` : saisir une intention de `>= 30` caractères et cliquer sur `Créer le Pack Métier` n'avait aucun effet !<br>**2.** `HelpArticleGeneratorAndValidatorView` (`gates/index.tsx:84-114`) était monté avec `passed: false` figé et **sans** `onGenerateAndAttach` : le bouton restait définitivement grisé (`disabled={!allValid}`) ou sans effet. | Câbler `onCreateBusinessPack`, `onPromoteAssetToPack` et `onGenerateAndAttach` (ainsi qu'une action de validation/génération de fiche d'aide dans `GatesFeaturePanel`) vers `@orcia/api-client` et `usePlatformSetup().registerPack`, avec retour visuel immédiat de création/validation. |
| **A3** | **`🗂️ Mes Espaces` (`/spaces`, `/workspaces`)**<br>`apps/web/src/features/workspaces/index.tsx`<br>`WorkspaceFiveTabsAndExternalRebaseView.tsx`<br>`DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` | **1.** `DnaStarlarkCompilerAndGlossaryLifecycleView` : compiler une règle métier (`generateStarlarkCta`), signer/activer (`signAndActivateCta`), promouvoir les termes du glossaire (`promoteSelectedCta`, `rejectCandidateCta`)<br>**2.** `WorkspaceFiveTabsAndExternalRebaseView` : `onRegisterWaiver`<br>**3.** `CommandPaletteModal` : sélectionner une entrée | **1.** Dans `WorkspacesFeaturePanel` (`workspaces/index.tsx:309-314`), `DnaStarlarkCompilerAndGlossaryLifecycleView` était monté avec `mechanism={null}` figé et **aucun callback** (`onCompileFromNorm`, `onSignAndActivate`, `onPromoteInFlow`, `onRejectCandidate` tous absents).<br>**2.** `WorkspaceFiveTabsAndExternalRebaseView` n'avait pas `onRegisterWaiver`.<br>**3.** `CommandPaletteModal` n'avait pas `onSelectItem` câblé sur `navigateToRoute`. | Ajouter dans `DnaStarlarkCompilerAndGlossaryLifecycleView` un bouton d'action permettant de compiler une règle métier dès l'état initial et câbler dans `WorkspacesFeaturePanel` : `onCompileFromNorm` (`client.compileDnaStarlark`), `onSignAndActivate`, `onPromoteInFlow` (`addOntologyConcept`), `onRejectCandidate`, `onRegisterWaiver` et `onSelectItem` sur `CommandPaletteModal`. |
| **A4** | **`💬 Mon Assistant` (`/assistant`, `/inbox`)**<br>`apps/web/src/features/inbox/index.tsx`<br>`AssistantGovernanceModalAndStudio.tsx`<br>`AssistantFoldersAndCollaborativeThreadView.tsx`<br>`AssistantCitationPillsAndArtifactCard.tsx` | **1.** Modale `Réglages de Mon Assistant` : boutons `Enregistrer mes préférences`, `Enregistrer les réglages de l'Espace`, `Enregistrer la personnalisation Studio`, `Réinitialiser`<br>**2.** `Dossiers thématiques 📁` : créer un premier dossier quand la liste est vide et envoyer un message collaboratif<br>**3.** `AssistantCitationPillsAndArtifactCard` : `Enregistrer en brouillon` (`onSaveDraft`) | **1.** `AssistantGovernanceModalAndStudio` (`inbox/index.tsx:73-81`) était monté sans `onSaveUserPreferences`, `onSaveWorkspaceSettings`, `onSaveStudioOverride`, `onResetStudioOverride` et ne fermait/confirmait pas l'enregistrement.<br>**2.** `AssistantFoldersAndCollaborativeThreadView` démarrait avec `folders={[]}` sans bouton `+ Nouveau dossier` pour créer un dossier (`client.createAssistantFolder`) et sans `onSendCollaborativeMessage`.<br>**3.** `AssistantCitationPillsAndArtifactCard` n'avait pas `onSaveDraft` câblé. | **1.** Câbler les callbacks de `AssistantGovernanceModalAndStudio` vers `@orcia/api-client` + confirmation visuelle.<br>**2.** Permettre la création d'un dossier thématique (`+ Nouveau dossier` $\rightarrow$ `client.createAssistantFolder`) et câbler `onSendCollaborativeMessage` dans `InboxFeaturePanel`.<br>**3.** Câbler `onSaveDraft` avec confirmation visuelle. |
| **A5** | **`ShellContainer` — Recherche `⌘K` (`TopHeaderSearchCommand`) & Sélecteur d'Espace**<br>`apps/web/src/components/ShellContainer.tsx` | **1.** Bouton `✨ Vitesse 2 (450 ms)` (`cmdk-trigger-speed2-btn`) et saisie dans `⌘K`<br>**2.** Bouton de changement d'Espace (`onOpenWorkspaceSwitcher`) | **1.** Dans `ShellContainer.tsx:530-592`, `TopHeaderSearchCommand` était monté **sans** `onQueryChange` ni `onTriggerSpeed2Now` : cliquer sur `✨ Vitesse 2 (450 ms)` dans `⌘K` ne déclenchait aucune recherche (`client.searchFederated`). | Câbler `onQueryChange` et `onTriggerSpeed2Now` dans `ShellContainer.tsx` vers `client.searchFederated` et alimenter `speed2Hits` / `speed2Loading` avec retour visuel immédiat. |

---

### 1.3 Analyse d'Impact GitNexus (Pré-Édition)

- `AgentsAndSkillsManagementService` (`packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`) : `risk: LOW`, `impactedCount: 2` (`__init__.py`, `sql_agents_and_skills.py`) + `apps/api/src/orcia_api/routers/agents_and_skills.py`.
- `RemoteServiceTestBenchAndGovernedMcpService` (`remote_test_bench_and_mcp_exposure.py`) : utilisé par `apps/api/src/orcia_api/routers/mcp_and_test_bench.py`.
- `PackBuilderSystemService` (`pack_builder_processes.py`) : utilisé par `apps/api/src/orcia_api/routers/pack_builder.py`.
- `DnaStarlarkAndGlossaryLifecycleService` (`dna_starlark_and_glossary_lifecycle.py`) : utilisé par `apps/api/src/orcia_api/routers/dna_and_glossary.py`.

---

## 2. Plan d'Implémentation & Nouveaux Garde-Fous Systémiques

### 2.1 Couche Persistance & Migrations SQL (`infra/migrations/` & `packages/orcia-core/`)
- Aucune nouvelle migration Alembic requise (les tables `catalog_items`, `assistant_folders`, `workspace_exception_waivers`, `system_bootstrap_runs` existent déjà).
- Dans `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py` :
  - Ajouter un paramètre optionnel rétrocompatible `llm_response_override: str | None = None` sur `execute_agent` et `execute_skill` (exactement comme sur `AssistantThreeSpeedRouterService`), afin que `apps/api` puisse injecter la vraie réponse du modèle IA configuré par l'utilisateur (`gemma4:12b` / Ollama / OpenAI / Anthropic) tout en respectant `AD-19` (`0` import réseau dans `orcia_core`).

### 2.2 Couche Backend API & SDK (`apps/api/`, `packages/api-client/`)
- Dans `apps/api/src/orcia_api/routers/agents_and_skills.py` :
  - Dans `execute_agent_endpoint` et `execute_skill_endpoint`, invoquer `invoke_configured_llm_for_assistant_turn` (`assistant_llm_bridge.py`) avec les instructions de l'Agent (et ses compétences rattachées) ou de la Compétence en tant que `system_instructions_override`, et passer le résultat à `svc.execute_agent(..., llm_response_override=...)` / `svc.execute_skill(..., llm_response_override=...)`.
  - Si l'utilisateur clique sur « Exécuter » dans `Mes Agents` / `Compétences` avec un champ d'essai vide, pré-remplir automatiquement une demande de test opérationnelle côté UI et accepter une valeur par défaut propre.

### 2.3 Couche Interface Utilisateur (`packages/ui/` & `apps/web/`)
1. **Correction de A1 (`apps/web/src/features/catalog/index.tsx` & `packages/ui/src/components/AgentsAndSkillsManagerView.tsx`)** :
   - Permettre de cliquer sur `Exécuter l'agent` / `Tester la compétence` même si le champ de test est vide (auto-remplissage d'une entrée de test + touche `Entrée`), afficher un état `⏳ Exécution en cours avec votre modèle IA...` et remonter toute erreur éventuelle au lieu de `.catch(() => undefined)`.
   - Câbler `RemoteServiceTestBenchAndMcpExposureView` dans `CatalogFeaturePanel` avec `onRunTestBench` (appelant `client.runRemoteServiceTestBench` + mise à jour de `steps`, `discoveredCapabilities`, `canActivate`), `onActivateService` (bannière de confirmation d'activation) et `onToggleMcpExposure`.
2. **Correction de A2 (`apps/web/src/features/gates/index.tsx` & `PackBuilderProcessesStudioView.tsx` & `HelpArticleGeneratorAndValidatorView.tsx`)** :
   - Câbler `onCreateBusinessPack` et `onPromoteAssetToPack` dans `GatesFeaturePanel` : crée et active le Pack métier dans `usePlatformSetup().registerPack(...)`, met à jour les simulations d'impact et certifications, et affiche une bannière de confirmation immédiate.
   - Dans `HelpArticleGeneratorAndValidatorView` et `GatesFeaturePanel` : activer le bouton de validation/rattachement (`onGenerateAndAttach`) même à partir d'un état initial pour lancer la validation déterministe (`client.validateHelpArticle`) et afficher le résultat (`passed: true`) + confirmation de rattachement à chaud.
3. **Correction de A3 (`apps/web/src/features/workspaces/index.tsx` & `DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` & `CommandPaletteModal.tsx`)** :
   - Dans `DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` : afficher le bouton `Compiler une règle métier` même lorsque `mechanism === null` pour permettre à l'utilisateur de déclencher la compilation dès l'état initial.
   - Dans `WorkspacesFeaturePanel` : câbler `onCompileFromNorm` (`client.compileDnaStarlark` + mise à jour de `mechanism`), `onSignAndActivate`, `onPromoteInFlow` (`addOntologyConcept`), `onRejectCandidate`, `onRegisterWaiver` et `onSelectItem` sur `CommandPaletteModal`.
4. **Correction de A4 (`apps/web/src/features/inbox/index.tsx`, `AssistantGovernanceModalAndStudio.tsx`, `AssistantFoldersAndCollaborativeThreadView.tsx`)** :
   - Dans `AssistantFoldersAndCollaborativeThreadView.tsx` : ajouter un bouton `+ Nouveau dossier` dans l'en-tête / l'onglet `📁 Dossiers` permettant de créer un dossier thématique dès l'état initial (`onCreateFolder`).
   - Dans `InboxFeaturePanel` : câbler `onCreateFolder` (`client.createAssistantFolder`), `onSendCollaborativeMessage`, `onSaveDraft`, ainsi que `onSaveUserPreferences`, `onSaveWorkspaceSettings`, `onSaveStudioOverride` et `onResetStudioOverride` sur `AssistantGovernanceModalAndStudio` avec bandeau de confirmation immédiat.
5. **Correction de A5 (`apps/web/src/components/ShellContainer.tsx`)** :
   - Câbler `onQueryChange` et `onTriggerSpeed2Now` sur `TopHeaderSearchCommand` (`⌘K`) pour appeler `client.searchFederated` et afficher les résultats sémantiques `speed2Hits` (ou un retour immédiat).

### 2.4 Comment s'assurer que cela ne se reproduise plus jamais ? (Double Barrière CI + Gouvernance `GEMINI.md` / `CLAUDE.md`)
1. **Création d'une suite de tests d'audit automatisée bloquante en CI (`apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`)** :
   - **Test Statique AST/Source n°1 (Zéro `.catch(() => undefined)` sur les actions utilisateur)** : Scanne tous les fichiers de `apps/web/src/features/` et `apps/web/src/routes/` pour interdire tout `.catch(() => undefined)` sur une action déclenchée par l'utilisateur.
   - **Test Statique n°2 (Zéro Primitive `@orcia/ui` montée sans ses callbacks d'action dans `apps/web`)** : Vérifie que chaque primitive interactive montée dans `apps/web` (`AssistantSpeedSelectorAndStreamView`, `AssistantGovernanceModalAndStudio`, `AssistantFoldersAndCollaborativeThreadView`, `AssistantCitationPillsAndArtifactCard`, `RemoteServiceTestBenchAndMcpExposureView`, `PackBuilderProcessesStudioView`, `HelpArticleGeneratorAndValidatorView`, `DnaStarlarkCompilerAndGlossaryLifecycleView`, `WorkspaceFiveTabsAndExternalRebaseView`, `TopHeaderSearchCommand`, `CommandPaletteModal`) reçoit bien ses handlers d'action (`onSendTurn`, `onRunTestBench`, `onCreateBusinessPack`, `onGenerateAndAttach`, `onCompileFromNorm`, `onTriggerSpeed2Now`, `onSelectItem`, etc.).
   - **Test Dynamique d'Interaction Bouton-par-Bouton** : Monte chaque écran de `apps/web`, clique sur les boutons d'action et vérifie que chaque clic produit un changement d'état visible dans le DOM (jamais un clic muet).
2. **Ajout du Garde-Fou n°5 dans `GEMINI.md`** :
   - Inscrire la règle **« Garde-Fou n°5 : Zéro Bouton Muet, Zéro Callback Optionnel Oublié & Zéro `.catch(() => undefined)` sur Action Utilisateur »** dans `GEMINI.md`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Créés / Modifiés

| Fichier | Nature | Description |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py` | Modifié | Ajout de `llm_response_override: str \| None = None` sur `execute_agent` et `execute_skill` (`AD-19` pur, `0` import externe). |
| `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` | Modifié | Ajout de `system_instructions_override: str \| None = None` sur `invoke_configured_llm_for_assistant_turn` pour personnaliser l'instruction système lors de l'exécution d'un Agent ou d'une Compétence. |
| `apps/api/src/orcia_api/routers/agents_and_skills.py` | Modifié | Câblage de `invoke_configured_llm_for_assistant_turn` dans `execute_agent_endpoint` et `execute_skill_endpoint`. |
| `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` | Modifié | Auto-remplissage d'une consigne d'essai par défaut si le champ de test est vide au clic sur `Exécuter` + soumission via touche `Entrée`. |
| `packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` | Modifié | Ajout du bouton `compile-starlark-btn` dans l'état vide (`dna-starlark-empty-state`) lorsque `onCompileFromNorm` est fourni. |
| `packages/ui/src/primitives/HelpArticleGeneratorAndValidatorView.tsx` | Modifié | Activation de `generate-and-attach-help-btn` dès que `onGenerateAndAttach` est fourni. |
| `packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx` | Modifié | Ajout de la prop `onCreateFolder` et du formulaire rapide (`assistant-new-folder-title-input` + `assistant-create-folder-btn`) dans l'onglet `FOLDERS`. |
| `apps/web/src/features/catalog/index.tsx` | Modifié | Câblage complet de `onRunTestBench`, `onActivateService`, `onToggleMcpExposure` et suppression des 6 `.catch(() => undefined)` au profit de `catalog-action-feedback-banner`. |
| `apps/web/src/features/gates/index.tsx` | Modifié | Câblage de `onCreateBusinessPack`, `onPromoteAssetToPack` et `onGenerateAndAttach` avec retour visuel `gates-action-feedback-banner`. |
| `apps/web/src/features/workspaces/index.tsx` | Modifié | Câblage de `onSelectItem`, `onRegisterWaiver`, `onCompileFromNorm`, `onSignAndActivate`, `onPromoteInFlow` et `onRejectCandidate` avec `workspaces-action-feedback-banner`. |
| `apps/web/src/features/inbox/index.tsx` | Modifié | Câblage de `onSaveUserPreferences`, `onSaveWorkspaceSettings`, `onSaveStudioOverride`, `onResetStudioOverride`, `onCreateFolder`, `onSendCollaborativeMessage` et `onSaveDraft` avec `assistant-governance-feedback-banner`. |
| `apps/web/src/components/ShellContainer.tsx` | Modifié | Câblage de `speed2Hits`, `speed2Loading`, `onQueryChange` et `onTriggerSpeed2Now` sur `TopHeaderSearchCommand` (`⌘K`). |
| `apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` | Créé | **Garde-Fou CI Permanent (6 tests)** : audit statique anti-`.catch(() => undefined)`, audit statique de câblage des callbacks `@orcia/ui`, et tests dynamiques de clic sur tous les panneaux métiers. |
| `GEMINI.md` | Modifié | Ajout du **Garde-Fou n°5** dans le Protocole Tech Lead. |

### 3.2 Résultats des Portes de Vérification (`AD-17` & `AD-19`)

- **Ruff Check & Format** : `.venv/bin/ruff check . && .venv/bin/ruff format --check .` $\rightarrow$ **0 erreur (`529 files already formatted`)**.
- **Mypy Strict** : `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` $\rightarrow$ **0 erreur (`Success: no issues found in 210 source files`)**.
- **Frontières Hexagonales (`lint-imports`)** : `.venv/bin/lint-imports` $\rightarrow$ **5 contrats respectés, 0 brisé**.
- **Tests Unitaires Python (`pytest`)** : `.venv/bin/pytest tests/unit/test_agents_and_skills_router_and_service.py tests/unit/test_epic_10_story_10_2_three_speed_router.py` $\rightarrow$ **8 passed**.
- **TypeScript (`pnpm turbo run lint typecheck test`)** :
  - `@orcia/api-client` : `8 passed`
  - `@orcia/ui` : `15 test files, 55 passed`
  - `@orcia/web` : `4 test files, 34 passed` (incluant les **6 nouveaux tests de `zero-dead-buttons-and-silent-catches-audit.test.tsx`**).
