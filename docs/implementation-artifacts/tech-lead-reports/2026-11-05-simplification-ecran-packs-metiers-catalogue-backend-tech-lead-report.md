# 2026-11-05 — Simplification de l'Écran « Packs Métiers » par Sélection sur le Catalogue Backend (`GET /api/v1/pack-builder/installed-packs` & `<SettingsPacksSection />`)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/2026-11-05-simplification-ecran-packs-metiers-catalogue-backend-tech-lead-report.md`

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-simplification-ecran-packs-metiers-catalogue-backend` (`Ajustement Transverse Post-Epic 12 — UX & Architecture Packs Métiers`)
- **Auteur / Contexte** : Binôme **Sally (`bmad-agent-ux-designer`)** & **Winston (`bmad-agent-architect`)** — Suppression des 3 champs de saisie texte libre (`Identifiant du Pack`, `1.0.0`, `GLOBAL`) dans l'onglet `Packs Métiers` de `/settings`, exposition du catalogue réel des Packs métiers installés dans le backend (`GET /api/v1/pack-builder/installed-packs` conforme `AD-20`), sélection guidée du périmètre d'activation (`Plateforme entière` ou Directions `BU` / `Espaces`), activation/désactivation en 1 clic (`registerPack` / `removePack`) et aide contextuelle ciblée `ⓘ` (`sectionId="packs-overview"`).
- **Commits associés** : `71ec5ae`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Dialogue Architectural et UX (Sally & Winston)

L'utilisateur a souligné à juste titre l'incohérence de l'onglet **`Packs Métiers`** dans `/settings` (`apps/web/src/routes/settings.tsx:L1147-L1230`), qui présentait 3 zones de saisie texte libre (`[Identifiant du Pack (ex: orcia-pack-sdlc)...]`, `[1.0.0]`, `[GLOBAL]`) suivies d'un bouton `[+ Activer le Pack]` :
> *« Sur cet écran, pourquoi des zones inputs libres ? Les packs ne sont-ils pas connus dans le back ORCIA ? Je ne suis pas certain qu'il y ait un mécanisme pour charger à chaud des nouveaux packs ou nouvelles versions ? Comment simplifier ? Sally et Winston ? »*

#### 🏗️ Diagnostic Architectural de Winston (`bmad-agent-architect`)
1. **Les Packs métiers sont connus et installés côté Backend (`AD-20`)** :
   - Dans l'architecture modulaire d'ORCIA (`AD-20`), un Pack métier est un package Python versionné et déclaré dans le workspace (`packages/orcia-pack-sdlc` pour l'Ingénierie Logicielle & Cycle de Vie Produit, `packages/orcia-pack-builder` pour l'Atelier de Conception & Gouvernance de Packs Métiers) ou un Pack généré et persisté via `PackBuilderSystemService` (`catalog_items` `item_type = 'BUSINESS_PACK'`).
   - Il n'existe **aucun** mécanisme de téléchargement dynamique arbitraire qui irait chercher du code exécutable inconnu à partir d'une chaîne libre tapée au clavier ni d'une version SemVer inventée par l'utilisateur.
   - Demander à l'administrateur de saisir manuellement `orcia-pack-sdlc`, `1.0.0` et `GLOBAL` viole le principe de source de vérité unique du backend et expose à des erreurs de saisie (fautes de frappe sur le slug, versions inexistantes, périmètre `GLOBAL` codé en anglais).
2. **Solution Backend & Contrat OpenAPI 3.1** :
   - Exposer l'endpoint `GET /api/v1/pack-builder/installed-packs` (`InstalledBusinessPackListResponse` / `InstalledBusinessPackItemResponse` dans `apps/api/src/orcia_api/schemas/pack_builder.py` et `apps/api/src/orcia_api/routers/pack_builder.py`) qui interroge `PackBuilderSystemService.list_installed_business_packs()`.
   - Cette méthode consolide de manière déterministe :
     1. Le pack métier pré-installé **`orcia-pack-sdlc`** (*Ingénierie Logicielle & Cycle de Vie Produit*, connecteurs Git/Jira/Confluence/Nexus, processus de spécification et revue croisée) ;
     2. Le pack métier système pré-installé **`orcia-pack-builder`** (*Atelier de Création & Gouvernance de Packs Métiers*, 4 agents spécialisés et 5 processus gouvernés) ;
     3. Tout Pack métier additionnel créé via l'Atelier de Packs (`self._created_packs` et entrées `BUSINESS_PACK` en base PostgreSQL 18).
   - Exposer `listInstalledBusinessPacks()` dans `@orcia/api-client` (`packages/api-client/src/domains/bootstrapAndOntology.ts`) et régénérer les schémas OpenAPI 3.1 (`scripts/export_openapi.py`, `0-diff`).

#### 🎨 Diagnostic & Simplification UX de Sally (`bmad-agent-ux-designer`)
1. **Élimination radicale de la saisie manuelle (Loi de Hick & Zéro Jargon)** :
   - **Suppression des 3 champs texte libres** (`Identifiant du Pack`, `1.0.0`, `GLOBAL`). L'administrateur n'a plus jamais à deviner un identifiant technique, un numéro SemVer ni le mot-clé interne `GLOBAL`.
   - Présentation directe du **Catalogue des Packs Métiers installés** sous forme de cartes claires et lisibles en moins de 2 secondes :
     - **Titre métier explicite en français** (ex. *« Ingénierie Logicielle & Cycle de Vie Produit »*, *« Atelier de Création de Packs Métiers »*), badge de **version installée en lecture seule** (`v1.0.0`), domaine métier et résumé de ce que contient le pack (`X processus · Y agents spécialisés`).
     - **Sélecteur déroulant du Périmètre d'activation** proposant *« Plateforme entière »* (valeur interne `GLOBAL` jamais affichée en anglais) ainsi que les Directions (`BU`) et `Espaces` réellement créés dans l'organisation (`orgUnits` & `workspaces`).
     - **Action en 1 clic** : bouton *« Activer ce Pack »* (ou *« Désactiver »* lorsqu'il est déjà actif sur le périmètre choisi, grâce à la nouvelle action `removePack(packKey, scopePath)` ajoutée à `platformSetupStore.tsx`).
     - **Sélecteur guidé rapide** en tête de section (conservant les `data-testid` `pack-key-input`, `pack-scope-input`, `save-pack-btn` pour une rétrocompatibilité 100 % sans friction avec les tests existants) permettant également d'activer en 1 clic n'importe quel pack installé sur le périmètre choisi.
     - **Icône d'aide contextuelle `ⓘ` (`<ContextualInfoTriggerButton sectionId="packs-overview" />`)** qui ouvre automatiquement la colonne d'aide contextuelle droite sur la section `packs-overview` enrichie.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `gitnexus_impact({target: "SettingsHubView", direction: "upstream"})` : `impactedCount: 3`, `risk: LOW` (`apps/web/src/routes/settings.tsx`, `apps/web/src/router.tsx`, `apps/web/src/main.tsx`).
  - `gitnexus_impact({target: "get_system_pack_builder_manifest_endpoint", direction: "upstream"})` : `impactedCount: 0` (endpoint HTTP terminal dans `apps/api/src/orcia_api/routers/pack_builder.py`).
  - `gitnexus_impact({target: "PackBuilderSystemService", direction: "upstream"})` : injecté via `get_pack_builder_system_service` dans `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` et appelé par `apps/api/src/orcia_api/routers/pack_builder.py`.
- **Contrôle de volumétrie & Anti-Conflits Git** :
  - `apps/web/src/routes/settings.tsx` compte actuellement `1 450` lignes et fait l'objet de travaux parallèles sur les onglets `iam` et `ai-models`.
  - Conformément à la politique Tech Lead (`GEMINI.md`), l'onglet `packs` est extrait dans un composant dédié **`apps/web/src/routes/SettingsPacksSection.tsx`** (`< 280` lignes), réduisant la taille de `settings.tsx` et isolant strictement la modification au bloc `{activeTab === "packs" && (...)}`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune nouvelle migration Alembic requise : les Packs métiers créés dynamiquement sont déjà persistés dans la table `catalog_items` (`item_type = 'BUSINESS_PACK'`, migration `0003`/`0023`) et l'état d'activation par périmètre est persisté dans PostgreSQL 18 via `platform_settings` (`GET/PUT /api/v1/bootstrap/platform-setup-state`).

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/pack_builder_processes.py` :
  - Ajout du dataclass immuable `InstalledBusinessPackDescriptor` (`pack_key`, `pack_slug`, `version`, `title_fr`, `title_en`, `domain_name`, `description_fr`, `description_en`, `workflows_count`, `agents_count`, `is_system_pack`).
  - Ajout de la méthode `PackBuilderSystemService.list_installed_business_packs()` retournant les packs installés connus du backend (`orcia-pack-sdlc`, `orcia-pack-builder`) ainsi que tout pack créé via `create_business_pack` (en mémoire ou persisté dans `catalog_items` `BUSINESS_PACK`).

### 2.3 Couche Backend API & Client SDK (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/pack_builder.py` :
  - Ajout de `InstalledBusinessPackItemResponse` et `InstalledBusinessPackListResponse`.
- `apps/api/src/orcia_api/routers/pack_builder.py` :
  - Ajout de l'endpoint `GET /api/v1/pack-builder/installed-packs` (`list_installed_business_packs_endpoint`).
- `packages/api-client/src/domains/bootstrapAndOntology.ts` & `scripts/export_openapi.py` :
  - Ajout de la méthode `listInstalledBusinessPacks()` dans `createBootstrapAndOntologyDomainClient`.
  - Régénération déterministe de `packages/api-client/openapi.json` et `packages/api-client/src/generated/*.ts` (`0-diff`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `apps/web/src/components/platformSetupStore.tsx` :
  - Ajout et exposition de `removePack(packKey: string, scopePath?: string)` avec enregistrement d'un événement d'audit `PackDeactivated` et synchronisation PostgreSQL 18 (`persistSnapshot`).
- `apps/web/src/routes/SettingsPacksSection.tsx` (Nouveau fichier `< 280` lignes) :
  - Charge le catalogue des Packs installés depuis `client.listInstalledBusinessPacks()` avec repli déterministe sur le catalogue embarqué des packs backend (`orcia-pack-sdlc`, `orcia-pack-builder`) + workflows/packs déjà connus.
  - Affiche l'en-tête avec bouton d'aide contextuelle `ⓘ` (`<ContextualInfoTriggerButton sectionId="packs-overview" onOpenHelpSection={openHelpSection} />`).
  - Remplace les champs texte libres par :
    1. Un sélecteur de **Périmètre d'activation** en langage naturel (*« Plateforme entière »*, Directions `BU` et `Espaces` créés) ;
    2. Les **Cartes des Packs Métiers installés** affichant le titre métier, le badge de version installée en lecture seule (`v1.0.0`), la description métier, le nombre de processus et d'agents inclus, et un bouton 1-clic **« Activer ce Pack »** / **« Désactiver »** ;
    3. La liste claire des Packs actuellement activés avec leur périmètre lisible et bouton de désactivation rapide.
- `apps/web/src/routes/settings.tsx` :
  - Remplacement exclusif du bloc `{activeTab === "packs" && (...)}` par `<SettingsPacksSection ... />`.
- `apps/web/src/components/contextualHelpCatalog.ts` :
  - Enrichissement de la section `packs-overview` (FR/EN) pour préciser que les Packs métiers sont pré-installés dans la plateforme (ou conçus dans *Mes Processus*) et s'activent en 1 clic sur toute la plateforme ou sur un Espace précis sans saisie manuelle de version.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/pack_builder_processes.py` | Modification | Ajout de `PackBuilderSystemService.list_created_packs()` exposant les Packs métiers créés via le Processus 1 (`create-business-pack`). |
| `apps/api/src/orcia_api/schemas/pack_builder.py` | Modification | Ajout des schémas Pydantic v2 `InstalledBusinessPackItemResponse` et `InstalledBusinessPackListResponse`. |
| `apps/api/src/orcia_api/routers/pack_builder.py` | Modification | Exposition de l'endpoint `GET /api/v1/pack-builder/installed-packs` retournant le catalogue réel des Packs métiers installés et connus du backend (`orcia-pack-sdlc`, `orcia-pack-builder` et packs créés). |
| `packages/api-client/src/domains/bootstrapAndOntology.ts` | Modification | Ajout de `listInstalledBusinessPacks()` et des types `InstalledBusinessPackItemResponse` / `InstalledBusinessPackListResponse` + régénération OpenAPI 3.1 (`openapi.json`, `schema.ts`, `0-diff`). |
| `apps/web/src/components/platformSetupStore.tsx` | Modification | Ajout de `removePack(packKey, scopePath)` avec événement d'audit `PackDeactivated`, mise à jour du dédoublonnage par `(packKey, scopePath)` et persistance PostgreSQL 18 (`persistSnapshot`). |
| `apps/web/src/routes/SettingsPacksSection.tsx` | Création (`280` lignes) | Composant dédié pour l'onglet `Packs Métiers` de `/settings` : suppression des champs texte libres (`SemVer`, `GLOBAL`), affichage des cartes des Packs installés, sélecteur de périmètre (`Plateforme entière`, `Direction`, `Espace`), activation/désactivation en 1 clic et bouton `ⓘ` (`sectionId="packs-overview"`). |
| `apps/web/src/routes/settings.tsx` | Refactoring | Remplacement exclusif du bloc `{activeTab === "packs" && (...)}` par `<SettingsPacksSection ... />` (sans toucher aux onglets `iam` ni `ai-models`). |
| `apps/web/src/components/contextualHelpCatalog.ts` | Modification | Enrichissement bilingue (`fr`/`en`) de la section `packs-overview` expliquant l'activation/désactivation en 1 clic des Packs fournis par la plateforme. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` & `tests/unit/test_epic_11_story_11_4_pack_builder_processes.py` | Modification | Tests unitaires et d'intégration couvrant `GET /api/v1/pack-builder/installed-packs` et le parcours UX complet de `SettingsPacksSection`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture & Tests** :
  - `pnpm turbo run lint typecheck test` : `9/9` tâches réussies (`19/19` suites Vitest `@orcia/web` passées).
  - `pytest tests/unit/test_epic_11_story_11_4_pack_builder_processes.py` : `4/4` tests passés.
  - `pytest tests/contract/test_openapi_contract.py -k test_openapi_client_zero_diff_gate` : `1/1` (`0-diff` OpenAPI 3.1).
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `All checks passed! (514 files already formatted)`
  - `mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `Success: no issues found in 209 source files`
  - `lint-imports` : `5 contracts kept, 0 broken`
  - `lint_spine.py` : `ok: true, total_findings: 0`

### 3.3 Validation & Procédure de Test (5 Couches `AD-17` + 4 Garde-Fous de Câblage Vertical)
- **Couche 1 — Tests Unitaires (`pytest` & `Vitest`)** : Validation de `list_installed_business_packs_endpoint`, de l'absence de champ texte libre SemVer (`pack-version-input` absent), de l'affichage des cartes des Packs installés (`orcia-pack-sdlc`, `orcia-pack-builder`), de l'activation/désactivation en 1 clic et de l'ouverture de l'aide contextuelle `ⓘ` (`packs-overview`).
- **Couche 2 — Câblage Vertical `UI ➔ SDK ➔ API ➔ Core/SQL`** : `SettingsPacksSection` appelle `client.listInstalledBusinessPacks()` (`GET /api/v1/pack-builder/installed-packs`) et persiste les activations/désactivations via `registerPack` / `removePack` (`PUT /api/v1/bootstrap/platform-setup-state`).
- **Couche 3 — Contrat OpenAPI 3.1 (`0-diff`)** : Vérifié par `scripts/export_openapi.py --check` et `test_openapi_client_zero_diff_gate`.
- **Couche 5 — Survie au `F5` & Parité `i18n` (`fr`/`en`)** : `100 %` de parité des clés `fr.ts` / `en.ts`, zéro couleur hexadécimale en dur, zéro jargon interne dans les libellés visibles.
