# Rapport d'Analyse & Plan d'Implémentation Tech Lead — `Story 12.3` : Montage de « Mes Espaces » (5 Sous-Onglets, Chaîne ADN Starlark, Glossaire `✨ À valider`), du Banc de Test MCP/A2A `🔌` et de l'Atelier `orcia-pack-builder` dans `apps/web` (`Epic 11`)

- **Clé de la Story** : `12-3-montage-mes-espaces-5-onglets-adn-starlark-mcp-pack-builder`
- **Epic** : `Epic 12` — Intégration Bout-en-Bout du Portail SPA (`apps/web`)
- **Date** : `2026-10-31`
- **Auteur** : Agent Tech Lead / Dev Senior (Antigravity)
- **Statut** : `done`
- **Références Architecture & UX** : `AD-14`, `AD-16`, `AD-19`, `AD-20`, `AD-21`, `draft-ux-principes-et-architecture-2026-10-30.md` (Principes D.4, I, J, L, M.1, M.2, M.4, Sections 3 & 4)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte & Problématique Métier / Technique
L'Epic 11 a livré les 5 primitives UI dans `@orcia/ui` couvrant la gouvernance métier de l'Espace, les services MCP/A2A et l'atelier `orcia-pack-builder` :
1. **`WorkspaceFiveTabsAndExternalRebaseView`** (Story 11.1) : Navigation à 5 sous-onglets (`Vue d'ensemble`, `Documents & Sources`, `Livrables & Artefacts`, `Glossaire & Règles`, `Membres & Équipe`), dérogations `workspace_exception_waivers` (`Verrou V1`) et réconciliation `ExternalEditRebaser` (`Verrou V2`).
2. **`DnaStarlarkCompilerAndGlossaryLifecycleView`** (Story 11.2) : Chaîne causale ADN (`DIRECTIVE ➔ NORME ➔ MÉCANISME`), compilateur `Text-to-Starlark` Palier 1b (`< 2 ms`, `0` token LLM au runtime) et file `✨ À valider` (`<= 15` FIFO + promotion *In-Flow* `Top-3` `Verrou V4`).
3. **`RemoteServiceTestBenchAndMcpExposureView`** (Story 11.3) : Banc de test à chaud en 4 étapes (`🔌 Tester & Découvrir`), qualification `READ_ONLY` vs `WRITE_STAGED_REQUIRED`, et exposition MCP gouvernée (`/api/v1/mcp` sous les 7 verrous matériels).
4. **`PackBuilderProcessesStudioView`** (Story 11.4) : Atelier `packages/orcia-pack-builder` (Processus 1 à 4 : création avec Ancrage Humain Violet obligatoire, simulation *What-If* préservant `run-lock.json`, certification Starlark Palier 1b `< 2 ms`, promotion vers Pack avec scrubbing).
5. **`HelpArticleGeneratorAndValidatorView`** (Story 11.5) : Processus 5 `generate-and-attach-help`, validateur déterministe `validate_help_article` (`< 5 s`) et rattachement à chaud `< 100 ms`.

Ces 5 vues devaient être montées dans les panneaux de fonctionnalités de `apps/web` correspondant aux entrées du menu latéral à 8 entrées :
- `/workspaces` & `/spaces` (`WorkspacesFeaturePanel`) $\rightarrow$ `WorkspaceFiveTabsAndExternalRebaseView` + `DnaStarlarkCompilerAndGlossaryLifecycleView`
- `/agents` & `/catalog` (`CatalogFeaturePanel`) $\rightarrow$ `RemoteServiceTestBenchAndMcpExposureView`
- `/processes` & `/gates` (`GatesFeaturePanel`) $\rightarrow$ `PackBuilderProcessesStudioView` + `HelpArticleGeneratorAndValidatorView`
- `/help` & `/ontology` (`OntologyFeaturePanel`) $\rightarrow$ `ContextualHelpColumnAndCenter` (`mode="HELP_MENU_CENTER"`) + `HelpArticleGeneratorAndValidatorView`

### 1.2 Analyse d'Impact GitNexus (Symboles, Appels & Risques)
- **Requêtes `gitnexus_impact` (`WorkspacesFeaturePanel`, `CatalogFeaturePanel`, `direction: "upstream"`)** :
  - Appelant direct : `ModuleWorkspaceView` (`apps/web/src/components/ModuleWorkspaceView.tsx`).
  - Invariants préservés : `workspace-topology-empty-state`, `create-workspace-panel`, `workspace-name-input`, `create-workspace-submit-btn`, `catalog-setup-guidance-card`, `catalog-explorer-empty-state`, `gates-empty-state-panel`, `ontology-create-concept-card`.

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (< 350 Lignes)
- Création de [`apps/web/src/i18n/locales/epic11_labels.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/i18n/locales/epic11_labels.ts) centralisant les labels bilingues FR/EN des 5 primitives de l'Epic 11 avec parité récursive à 100 %.

---

## 2. Plan d'Implémentation

### 2.1 Dictionnaire i18n Bilingue (`apps/web/src/i18n/locales/epic11_labels.ts`)
- Définition de `Epic11DictionarySection` (`workspaceFiveTabs`, `dnaStarlarkGlossary`, `remoteServiceTestBench`, `packBuilderStudio`, `helpArticleGenerator`) et intégration dans `types.ts`, `fr.ts` et `en.ts`.

### 2.2 Montage dans les 4 Panneaux de Fonctionnalités (`apps/web/src/features/*`)
- **`apps/web/src/features/workspaces/index.tsx`** : Montage de `WorkspaceFiveTabsAndExternalRebaseView` (navigation interactive entre les 5 sous-onglets) et `DnaStarlarkCompilerAndGlossaryLifecycleView` (compilation/signature Starlark et promotion *In-Flow* du glossaire).
- **`apps/web/src/features/catalog/index.tsx`** : Montage de `RemoteServiceTestBenchAndMcpExposureView` (banc de test 4 étapes `🔌` et bascule d'exposition MCP `/api/v1/mcp`).
- **`apps/web/src/features/gates/index.tsx`** : Montage de `PackBuilderProcessesStudioView` (Processus 1 à 4 de `orcia-pack-builder`) et `HelpArticleGeneratorAndValidatorView` (Processus 5 `generate-and-attach-help`).
- **`apps/web/src/features/ontology/index.tsx`** : Montage de `ContextualHelpColumnAndCenter` (`mode="HELP_MENU_CENTER"`) en tête de `/help` pour offrir le Centre d'Aide complet (recherche par routes/packs, ancres et rollback `@v(N-1)`).

---

## 3. Bilan des Modifications & Résultats (Après Implémentation)

### 3.1 Fichiers Créés ou Modifiés
| Fichier | Nature | Rôle |
|---|---|---|
| `apps/web/src/i18n/locales/epic11_labels.ts` | Créé | Labels bilingues FR/EN pour les 5 primitives de l'Epic 11 |
| `apps/web/src/i18n/types.ts` | Modifié | Extension de `TranslationDictionary` avec `Epic11DictionarySection` |
| `apps/web/src/i18n/locales/fr.ts` | Modifié | Inclusion de `EPIC11_FR_LABELS` |
| `apps/web/src/i18n/locales/en.ts` | Modifié | Inclusion de `EPIC11_EN_LABELS` |
| `apps/web/src/features/workspaces/index.tsx` | Modifié | Montage de `WorkspaceFiveTabsAndExternalRebaseView` et `DnaStarlarkCompilerAndGlossaryLifecycleView` |
| `apps/web/src/features/catalog/index.tsx` | Modifié | Montage de `RemoteServiceTestBenchAndMcpExposureView` |
| `apps/web/src/features/gates/index.tsx` | Modifié | Montage de `PackBuilderProcessesStudioView` et `HelpArticleGeneratorAndValidatorView` |
| `apps/web/src/features/ontology/index.tsx` | Modifié | Montage de `ContextualHelpColumnAndCenter` (`HELP_MENU_CENTER`) |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modifié | Test d'intégration Vitest vérifiant `/workspaces`, `/agents`, `/processes` et `/help` |

### 3.2 Validation des Couches de Tests (`AD-17`) & Qualité
- **Parité i18n FR/EN** : `100 %` (`collectNestedKeys`).
- **Zéro couleur hexadécimale & Isolation Feature-Sliced (`M11`, `AD-19`)** : `PASS`.
- **Suite `@orcia/ui` & `@orcia/web`** : `pnpm turbo run lint typecheck test` `0` erreur.
