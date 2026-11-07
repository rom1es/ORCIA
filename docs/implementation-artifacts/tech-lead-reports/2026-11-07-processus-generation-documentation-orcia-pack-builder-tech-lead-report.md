# 2026-11-07 — Intégration du Processus `generate-orcia-documentation` dans `orcia-pack-builder` & Exécution en 1 Clic dans `☍ Mes Processus`

- **Date** : 2026-11-07
- **Story / Clé Sprint** : `2026-11-07-processus-generation-documentation-orcia-pack-builder` (`Post-Epic 12 / Pack Builder & Documentation Vivante`)
- **Auteur / Contexte** : Winston (Architecte) & Sally (UX/UI) — Implémentation de bout en bout de la **Méthode 2** : intégration native du 6e processus gouverné `generate-orcia-documentation` (« Génération et Synchronisation de la Documentation Complète d'ORCIA ») dans le Pack Système `packages/orcia-pack-builder` (`AD-20`), exécution déterministe en 4 étapes (`run_generate_orcia_documentation_workflow` pilotée par `@Rédacteur-Documentation-Orcia`) et exposition directe en 1 clic dans `☍ Mes Processus` (`/processes`) avec aperçu formaté `FormattedMarkdownContent` et chargement dans l'Atelier de Processus (`SimplifiedProcessBuilderSection`).
- **Commits associés** : `feat/pack-builder-generate-orcia-documentation-process`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problématique métier & UX** : L'utilisateur souhaite disposer, directement dans le Pack Système `packages/orcia-pack-builder` et dans l'écran `☍ Mes Processus` (`/processes`), d'un processus clé en main **`generate-orcia-documentation`** capable de générer, vérifier et synchroniser en 4 étapes toute la documentation d'ORCIA (guides fonctionnels par écran FR/EN, FAQ d'architecture & modèle métier, et manifeste du site de documentation) ou d'être chargé en 1 clic dans l'Atelier de Processus pour personnalisation.
- **Comportement attendu vs comportement actuel** :
  - Actuellement, `packages/orcia-pack-builder` expose 5 processus (`create-business-pack`, `evolve-business-pack`, `certify-pack-tool`, `export-from-workspace-to-pack`, `generate-and-attach-help`) centrés sur la création unitaire d'une fiche `HelpArticle`.
  - Le besoin ajoute le **Processus 6 (`generate-orcia-documentation`)** dans `pack.yaml`, `PACK_BUILDER_PROCESSES` (`orcia_pack_builder/__init__.py`) et `HelpGenerationAndHotAttachmentService.run_generate_orcia_documentation_workflow(...)`, ainsi qu'une carte dédiée `OrciaDocumentationProcessCard.tsx` montée dans `GatesFeaturePanel` (`apps/web/src/features/gates/index.tsx`).
- **Contraintes d'architecture (`ARCHITECTURE-SPINE.md`, `AD-19`, `AD-20`)** :
  - Respect strict des frontières du monolithe modulaire (`orcia_kernel` $\leftarrow$ `orcia_core` $\leftarrow$ `orcia_pack_builder` / `orcia_api`).
  - Volumétrie maximale `< 400` lignes par fichier : extraction de `OrciaDocumentationProcessCard.tsx` pour maintenir `apps/web/src/features/gates/index.tsx` sous `320` lignes.
  - Respect du Garde-Fou CI n°5 (`zero-dead-buttons-and-silent-catches-audit.test.tsx`) : zéro `.catch(() => undefined)` dans `apps/web/src/features/` et callbacks d'action systématiquement câblés avec bannière de retour explicite.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus & Références** :
  - `PACK_BUILDER_PROCESSES` est défini dans `packages/orcia-pack-builder/src/orcia_pack_builder/__init__.py` et consommé par `get_pack_builder_manifest()`, `apps/api/src/orcia_api/routers/pack_builder.py` (`list_installed_business_packs_endpoint`) et `tests/unit/test_epic_11_story_11_4_pack_builder_processes.py`.
  - `HelpGenerationAndHotAttachmentService` (`packages/orcia-core/src/orcia_core/orchestration/help_generator_and_validator.py`) fournit déjà `render_bilingual_help_markdown` et `HelpArticleDeterministicValidator.validate_help_article`.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Réutilisation directe de `HelpArticleDeterministicValidator` pour l'Étape 3 (Contrôle Qualité Déterministe `< 5 s`) de `run_generate_orcia_documentation_workflow`.
  - Réutilisation de la primitive `@orcia/ui` `FormattedMarkdownContent` pour l'aperçu du guide généré (`data-testid="orcia-doc-generation-output-preview"`).
  - Création d'un composant dédié `apps/web/src/features/gates/OrciaDocumentationProcessCard.tsx` (`~230` lignes) afin que `apps/web/src/features/gates/index.tsx` reste compact (`~295` lignes) et que `SimplifiedProcessBuilderSection.tsx` puisse pré-remplir son formulaire lorsqu'un modèle de processus lui est transmis.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune nouvelle table SQL requise : le processus `generate-orcia-documentation` s'appuie sur le stockage existant `catalog_items` (`item_type = 'HELP_ARTICLE'`), la table de configuration `platform_setup_snapshot` (`workflows`, `runs`) et le cache Redis `help:route:*`.

### 2.2 Noyau Métier Hexagonal & Pack Système (`packages/orcia-pack-builder/`, `packages/orcia-core/`)
- `packages/orcia-pack-builder/pack.yaml` & `packages/orcia-pack-builder/src/orcia_pack_builder/__init__.py` :
  - Ajout du **Processus 6 (`generate-orcia-documentation`)** (`uri: "orcia://pack-builder/workflows/generate-orcia-documentation"`, `lead_agent_handle: "@Rédacteur-Documentation-Orcia"`, `requires_human_anchor: False`) dans `PACK_BUILDER_PROCESSES` et `ORCIA_DOCUMENTATION_GENERATOR_PROCESS`.
- `packages/orcia-core/src/orcia_core/orchestration/help_generator_and_validator.py` :
  - Ajout des dataclasses immuables `OrciaDocumentationWorkflowStepResult` et `OrciaDocumentationWorkflowReport`.
  - Ajout de la méthode `run_generate_orcia_documentation_workflow(...)` sur `HelpGenerationAndHotAttachmentService` (et fonction helper `run_generate_orcia_documentation_workflow`) exécutant les **4 étapes gouvernées** :
    1. **Étape 1 — Inventaire du dépôt ORCIA** : recense les routes UI (`DEFAULT_KNOWN_ROUTES`), les primitives `@orcia/ui` (`KNOWN_ORCIA_UI_COMPONENTS`), les fiches d'aide bilingues (`docs/help/{fr,en}/*.md`), la FAQ d'architecture (`faq-architecture-modele-metier.md`) et les rapports Tech Lead.
    2. **Étape 2 — Génération & Enrichissement des Guides et de la FAQ** : structure le guide complet avec les sections `Objectif`, `Guide Fonctionnel par Écran`, `Architecture & Modèle Métier`, `Questions Fréquentes (FAQ)` ainsi que les sections bilingues normalisées pilotées par `@Rédacteur-Documentation-Orcia` et `@Architecte-Métier-Pack`.
    3. **Étape 3 — Contrôle Qualité Déterministe (`validate_help_article`)** : valide les routes liées (`bound_routes`), la présence des sections obligatoires et l'absence de secrets ou de jargon technique interne dans les guides utilisateurs.
    4. **Étape 4 — Publication & Rattachement à Chaud (`/showcase` & `docs/help/`)** : produit le récapitulatif complet des documents générés/vérifiés et met à jour l'état du processus.

### 2.3 Couche Backend API & Contrats (`apps/api/`)
- Le endpoint `GET /api/v1/pack-builder/manifest` et `GET /api/v1/pack-builder/installed-packs` exposent automatiquement les 6 processus gouvernés de `orcia-pack-builder` (incluant `generate-orcia-documentation`), et `POST /api/v1/pack-builder/processes/validate-help-article` valide à chaud le guide généré.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `apps/web/src/features/gates/OrciaDocumentationProcessCard.tsx` :
  - Carte dédiée (`data-testid="orcia-doc-generation-process-card"`) affichant le titre `📚 Processus du Pack ORCIA — Génération de la Documentation ORCIA (generate-orcia-documentation)`, le badge `📦 Pack : orcia-pack-builder · Agent : @Rédacteur-Documentation-Orcia` et la description courte sans jargon interne.
  - Bouton 1 : **`▶️ Lancer la génération de la documentation ORCIA`** (`data-testid="run-orcia-doc-generation-process-btn"`) :
    - Enregistre/publie automatiquement le processus `generate-orcia-documentation` dans `workflows` (via `upsertWorkflow`),
    - Lance une exécution (`launchRun` si un espace est actif + appel de validation API `validateHelpArticle` avec gestion d'erreur explicite),
    - Affiche en direct le bilan des **4 étapes exécutées** (`data-testid="orcia-doc-generation-steps-summary"`) et l'aperçu Markdown formaté (`<FormattedMarkdownContent />`) dans `data-testid="orcia-doc-generation-output-preview"`.
  - Bouton 2 : **`✏️ Charger dans l'Atelier de Processus`** (`data-testid="load-orcia-doc-process-in-builder-btn"`) :
    - Charge le modèle `generate-orcia-documentation` dans `SimplifiedProcessBuilderSection` et l'enregistre dans `workflows` pour personnalisation immédiate.
- `apps/web/src/components/SimplifiedProcessBuilderSection.tsx` & `apps/web/src/features/gates/index.tsx` :
  - Ajout d'une prop optionnelle `presetDraft` sur `SimplifiedProcessBuilderSection` permettant à `load-orcia-doc-process-in-builder-btn` de pré-remplir les champs du formulaire de l'Atelier (`workflow-title-input`, `workflow-key-input`, `workflow-preprompt-textarea`, `workflow-params-input`, `workflow-sections-input`, `layers`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-pack-builder/pack.yaml` | Modification | Ajout déclaratif du Processus 6 `generate-orcia-documentation` (`orcia://pack-builder/workflows/generate-orcia-documentation`). |
| `packages/orcia-pack-builder/src/orcia_pack_builder/__init__.py` | Modification | Exposition de `ORCIA_DOCUMENTATION_GENERATOR_PROCESS`, mise à jour de `PACK_BUILDER_PROCESSES` (`6` processus gouvernés) et export de `run_generate_orcia_documentation_workflow`. |
| `packages/orcia-core/src/orcia_core/orchestration/help_generator_and_validator.py` | Modification | Ajout des dataclasses `OrciaDocumentationWorkflowStepResult` et `OrciaDocumentationWorkflowReport` et de la méthode `run_generate_orcia_documentation_workflow` en 4 étapes (`Inventaire`, `Génération & Enrichissement`, `Contrôle Qualité Déterministe validate_help_article`, `Publication & Rattachement à Chaud`). |
| `apps/web/src/features/gates/OrciaDocumentationProcessCard.tsx` | Création (`383` lignes) | Carte dédiée dans `☍ Mes Processus` (`/processes`) avec exécution en 1 clic (`run-orcia-doc-generation-process-btn`), affichage des 4 étapes (`orcia-doc-generation-steps-summary`), aperçu formaté `FormattedMarkdownContent` (`orcia-doc-generation-output-preview`) et chargement dans l'Atelier (`load-orcia-doc-process-in-builder-btn`). |
| `apps/web/src/features/gates/index.tsx` | Modification (`307` lignes) | Montage de `<OrciaDocumentationProcessCard />` et passage de `presetDraft` à `<SimplifiedProcessBuilderSection />` en respectant `< 350` lignes. |
| `apps/web/src/components/SimplifiedProcessBuilderSection.tsx` | Modification | Ajout de la prop optionnelle `presetDraft` pré-remplissant automatiquement le formulaire de l'Atelier lors du clic sur `✏️ Charger dans l'Atelier de Processus`. |
| `tests/unit/test_epic_11_story_11_4_pack_builder_processes.py` | Modification | Vérification de la présence de `generate-orcia-documentation` dans `PACK_BUILDER_PROCESSES` et `get_pack_builder_manifest()`. |
| `tests/unit/test_epic_11_story_11_5_help_generator_and_validator.py` | Modification | Test unitaire `test_process6_generate_orcia_documentation_workflow_runs_4_steps` validant l'exécution des 4 étapes et le rejet de `READ_ONLY_OBSERVER`. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modification | Test d'intégration UI sur `/processes` vérifiant l'affichage de `orcia-doc-generation-process-card`, l'exécution en 1 clic de `run-orcia-doc-generation-process-btn` et le chargement dans l'Atelier via `load-orcia-doc-process-in-builder-btn`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests unitaires Python (`pytest`)** : `9 passed` sur `test_epic_11_story_11_4_pack_builder_processes.py` et `test_epic_11_story_11_5_help_generator_and_validator.py`.
- **Tests unitaires & intégration TypeScript (`pnpm turbo run lint typecheck test`)** : `9/9 tasks successful` (`58` tests `@orcia/ui`, `8` tests `@orcia/api-client`, `36` tests `@orcia/web` incluant `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `0 warning` (`All checks passed!`)
  - `mypy --strict` & `pnpm typecheck` : `0 error` (`Success: no issues found in 210 source files`)
  - `lint-imports` : `5 contracts kept, 0 broken`

### 3.3 Validation & Procédure de Test (5 Couches `AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1 — Tests Unitaires (`pytest`, `Vitest`)** : Exécution déterministe des 4 étapes de `run_generate_orcia_documentation_workflow`, rejet `ObserverModeReadOnlyError`, validation `validate_help_article` FR/EN et rendu `FormattedMarkdownContent`.
- **Couche 2 & 3 — Contrats & Intégration API** : Exposition de `generate-orcia-documentation` dans `/api/v1/pack-builder/manifest` et `/api/v1/pack-builder/installed-packs` + appel `validateHelpArticle` avec gestion d'erreur explicite (zéro `.catch(() => undefined)`).
- **Couche 5 — Tests UI & Garde-Fou n°5 (`zero-dead-buttons-and-silent-catches-audit.test.tsx`)** : Vérification sur `/processes` de la publication en 1 clic dans `workflows`, du bilan des 4 étapes, de l'aperçu Markdown formaté et du pré-remplissage de l'Atelier de Processus.
