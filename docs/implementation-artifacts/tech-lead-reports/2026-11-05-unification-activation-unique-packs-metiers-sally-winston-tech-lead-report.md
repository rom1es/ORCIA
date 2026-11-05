# 2026-11-05 — Dialogue Sally (UX/UI) & Winston (Architecte) : Unification en Une Seule Méthode d'Activation des Packs Métiers & Déduplication Hiérarchique des Périmètres (`SettingsPacksSection.tsx`)

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md`

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-unification-activation-unique-packs-metiers-sally-winston` (`Post-Epic 12` / `Ajustement Transverse UX & Architecture`)
- **Auteur / Contexte** : **Sally (`bmad-agent-ux-designer` 🎨)** & **Winston (`bmad-agent-architect` 🏗️)** — Réponse au diagnostic visuel de l'utilisateur sur l'onglet **Packs Métiers** (`/settings`, [`SettingsPacksSection.tsx`](../../../apps/web/src/routes/SettingsPacksSection.tsx)) : *« Sur cet écran, pourquoi y a-t-il 2 méthodes d'activation des packs ? Sally ? Winston ? »*. Application stricte de la Règle Fondamentale UX n°2 (*Loi de Hick / Minimalisme : 1 intention = 1 contrôle unique*) et cohérence hiérarchique des périmètres d'activation (`Plateforme entière` $\supset$ `Direction` $\supset$ `Espace`).
- **Commits associés** : `En cours sur fix/packs-single-activation-method-ux`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Dialogue Critique Sally (UX) & Winston (Architecte)

#### Question de l'Utilisateur (Capture d'écran de l'onglet `Packs Métiers`)
> *« Sur cet écran, pourquoi y a-t-il 2 méthodes d'activation des packs ? Sally ? Winston ? »*

#### Dialogue d'Analyse entre Sally (🎨 UX Designer) et Winston (🏗️ System Architect)

- **🎨 Sally (`bmad-agent-ux-designer`)** :
  > *« Tu as mis le doigt sur une erreur classique d'empilement d'interface ! En regardant ta capture d'écran de l'onglet **Packs Métiers**, on ne voit pas seulement deux, mais **trois zones qui se répètent** et entrent en collision cognitive (violation directe de notre Règle Fondamentale UX n°2 — **Loi de Hick & Minimalisme**):*
  > *1. **En haut à droite** : une liste déroulante de sélection de Pack (`Atelier de Création & Gouvernance de Packs Métiers (v0.1.0)`) accolée à un bouton primaire bleu `Activer sur ce périmètre` ;*
  > *2. **Au milieu** : les **2 grandes cartes du Catalogue des Packs Métiers disponibles**, qui affichent chacune le titre, la description, le nombre de processus/agents et **leur propre bouton d'action** (`Activer ce Pack` / `Désactiver`) ;*
  > *3. **En bas** : une troisième liste de lignes récapitulatives qui répète encore le nom du pack, sa version `v0.1.0`, un badge vert `Actif · Plateforme entière` et un second bouton `Désactiver`.*
  > *Pourquoi y avait-il ces 2 méthodes d'activation concurrentes ? Parce que lors du remplacement de l'ancien formulaire texte libre par les cartes du Catalogue, le formulaire d'en-tête (`pack-key-input` + `save-pack-btn`) avait été conservé en parallèle des nouvelles cartes. Résultat : l'utilisateur hésite entre choisir un pack dans la liste déroulante du haut ou cliquer directement sur la carte du pack qu'il a sous les yeux ! »*

- **🏗️ Winston (`bmad-agent-architect`)** :
  > *« Et il y a un second problème, purement architectural et métier, visible tout en bas de ta capture d'écran : le pack **Ingénierie Logicielle & Cycle de Vie Produit** apparaît activé deux fois — une première ligne `Actif · Plateforme entière` et une seconde ligne `Actif · Direction · DS3C` !*
  > *Dans le modèle hiérarchique d'ORCIA (`GLOBAL ➔ BU ➔ TEAM/WORKSPACE`), la **Plateforme entière (`GLOBAL`) englobe toutes les Directions et tous les Espaces**. Activer un Pack sur la Plateforme entière tout en conservant (ou en autorisant) une seconde activation redondante sur `Direction · DS3C` crée un doublon d'état dans `platformSetupStore.tsx` et brouille la gouvernance : si l'administrateur clique sur `Désactiver` sur la ligne `Direction · DS3C`, le Pack reste en réalité actif sur `DS3C` puisqu'il est actif sur la `Plateforme entière` !*
  > *Nous devons donc agir sur deux plans complémentaires :*
  > *1. **Unification UX radicale (Sally)** : supprimer définitivement la liste déroulante de Pack (`pack-key-input`) et le bouton `Activer sur ce périmètre` (`save-pack-btn`) de l'en-tête. En haut à droite, on ne choisit que le **Périmètre cible** (`Plateforme entière`, `Direction · ...`, `Espace · ...`). L'activation ou la désactivation se fait **exclusivement sur la carte du Pack concerné**, qui affiche directement ses badges de périmètres actifs et adapte son bouton au périmètre sélectionné.*
  > *2. **Invariant de déduplication hiérarchique (Winston)** : dans `platformSetupStore.tsx` (`registerPack`) et à l'hydratation du store, si un Pack est activé sur `GLOBAL` (`Plateforme entière`), il remplace automatiquement toute activation partielle redondante de ce même Pack sur un sous-périmètre (`BU` / `Espace`), et tant qu'un Pack est actif sur la `Plateforme entière`, les cartes indiquent explicitement qu'il couvre déjà toute l'organisation (y compris la Direction ou l'Espace sélectionné). »*

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `/home/romain/Documents/Projects/ORCIA`)** :
  - `gitnexus_query({search_query: "SettingsPacksSection registerPack removePack", repo: "/home/romain/Documents/Projects/ORCIA"})` : identifie `PlatformSetupProvider.registerPack` (`apps/web/src/components/platformSetupStore.tsx`) et `SettingsHubView` (`apps/web/src/routes/settings.tsx`).
  - `gitnexus_impact({target_uid: "Function:apps/web/src/components/platformSetupStore.tsx:PlatformSetupProvider.registerPack@714:2", direction: "upstream", repo: "/home/romain/Documents/Projects/ORCIA"})` :
    - `impactedCount: 3`, `risk: LOW`, `direct: 1` (`PlatformSetupProvider` $\rightarrow$ `SettingsHubView` $\rightarrow$ `SettingsPacksSection`).
  - Vérification textuelle (`grep -rn "pack-key-input\|save-pack-btn"` dans `apps/web/src/`) :
    - Aucun test dans `apps/web/src/__tests__/i18n-and-shell.test.tsx` n'utilise `pack-key-input` ni `save-pack-btn` (le test de la ligne `1007` utilise déjà `activate-pack-btn-orcia-pack-sdlc` et `deactivate-pack-btn-orcia-pack-sdlc`).
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - [`apps/web/src/routes/SettingsPacksSection.tsx`](../../../apps/web/src/routes/SettingsPacksSection.tsx) passe de `400` lignes à ~`330` lignes en supprimant le formulaire redondant d'en-tête (`selectedPackKey`, `pack-key-input`, `save-pack-btn`) et en intégrant proprement l'état d'activation par périmètre sur chaque carte et dans le récapitulatif épuré.
  - Dans [`apps/web/src/components/platformSetupStore.tsx`](../../../apps/web/src/components/platformSetupStore.tsx), ajout d'une fonction pure `deduplicateConfiguredPacks(packs)` appliquée à la lecture du cache/API et dans `registerPack` pour garantir qu'un Pack activé sur `GLOBAL` ne coexiste jamais avec des entrées redondantes sur des sous-périmètres (`DS3C`, etc.).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune migration Alembic requise : la structure JSONB persistée par `sql_platform_setup_store.py` (`packs`) conserve le contrat `{ packKey, version, scopePath, status }`.

### 2.2 Noyau Métier Hexagonal & Store de Paramétrage (`apps/web/src/components/platformSetupStore.tsx`)
- Création et export d'un utilitaire pur `deduplicateConfiguredPacks(items: readonly ConfiguredPackItem[]): readonly ConfiguredPackItem[]` :
  - Si un `packKey` possède une entrée avec `scopePath === "GLOBAL"`, seules l'entrée `GLOBAL` de ce `packKey` est conservée (toutes les entrées de sous-périmètres `BU` / `TEAM` / `WORKSPACE` pour ce même `packKey` sont purgées car couvertes par `GLOBAL`).
  - Sinon, déduplication stricte par couple `(packKey, scopePath)`.
- Application de `deduplicateConfiguredPacks` :
  - Lors de la lecture initiale (`readCachedPlatformSetupState`) et de la réhydratation API (`getPlatformSetupState`), ce qui nettoie immédiatement l'état incohérent `Plateforme entière` + `Direction · DS3C` existant ;
  - Dans `registerPack(input)` :
    - Si `input.scopePath === "GLOBAL"`, supprime toutes les entrées existantes de `input.packKey` (quel que soit leur sous-périmètre) et enregistre l'activation `GLOBAL`.
    - Si `input.scopePath !== "GLOBAL"` et que `input.packKey` est **déjà actif sur `GLOBAL`**, ne crée pas de doublon sous-périmètre redondant.

### 2.3 Couche Backend API & Contrats (`apps/api/`, `packages/api-client/`)
- Aucun changement de schéma OpenAPI (contrat `0-diff` préservé).

### 2.4 Interface Utilisateur & Expérience (`apps/web/src/routes/SettingsPacksSection.tsx` & `i18n-and-shell.test.tsx`)
- **En-tête épuré de `SettingsPacksSection.tsx`** :
  - À gauche : titre `Catalogue des Packs Métiers disponibles` + bouton d'aide contextuelle `ⓘ` (`packs-overview`).
  - À droite : **uniquement** le sélecteur `Périmètre cible : [Plateforme entière | Direction · ... | Espace · ...]` (`data-testid="pack-scope-input"`).
  - **Suppression totale** de la liste déroulante de Pack (`data-testid="pack-key-input"`) et du bouton `Activer sur ce périmètre` (`data-testid="save-pack-btn"`).
- **Cartes du Catalogue (`installed-pack-card-${item.pack_key}`)** — point unique d'activation/désactivation :
  - Affichage des badges de périmètres où le Pack est actuellement actif (`Actif · Plateforme entière`, ou la liste des Directions/Espaces actifs avec retrait direct).
  - Si le Pack est actif sur `Plateforme entière` (`GLOBAL`) et que l'utilisateur inspecte un sous-périmètre (`Direction · DS3C`), la carte indique clairement : *« Couvert par l'activation Plateforme entière »* et propose le bouton `Désactiver (Plateforme entière)` (`data-testid="deactivate-pack-btn-${item.pack_key}"`) au lieu de permettre une double activation redondante.
  - Sinon, le bouton unique de la carte indique explicitement le périmètre cible :
    - S'il n'est pas actif sur le périmètre sélectionné : **`Activer sur : [Nom du périmètre]`** (`data-testid="activate-pack-btn-${item.pack_key}"`) ;
    - S'il est actif sur le périmètre sélectionné : **`Désactiver sur ce périmètre`** (`data-testid="deactivate-pack-btn-${item.pack_key}"`).
- **Tests unitaires & d'intégration (`apps/web/src/__tests__/i18n-and-shell.test.tsx`)** :
  - Vérification dans le test `"presents the backend-known Business Packs catalog..."` :
    1. Absence totale de `pack-key-input` et de `save-pack-btn` (`queryByTestId(...) === null`) — prouvant qu'il n'existe plus qu'une seule méthode d'activation ;
    2. Activation sur `Direction · Direction Produit`, puis bascule sur `Plateforme entière` et activation : vérification que l'activation sur `Plateforme entière` remplace automatiquement l'activation partielle `Direction · Direction Produit` (une seule ligne active `Plateforme entière`, zéro doublon `Plateforme entière` + `Direction`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/web/src/routes/SettingsPacksSection.tsx` | Modification / Épuration UX (`391 lignes`) | Suppression de la liste déroulante de Pack (`pack-key-input`) et du bouton redondant `Activer sur ce périmètre` (`save-pack-btn`) dans l'en-tête. Conservé uniquement le sélecteur `Périmètre cible` (`pack-scope-input`) en haut et unifié l'activation/désactivation sur chaque carte du Catalogue (`Activer sur : [Périmètre]` / `Désactiver sur ce périmètre`) avec badges de périmètres actifs et mention explicite de couverture lorsque le Pack est actif sur `Plateforme entière`. |
| `apps/web/src/components/platformSetupStore.tsx` | Modification | Ajout de `deduplicateConfiguredPacks(items)` appliqué à la lecture du cache/API et dans `registerPack` afin que l'activation d'un Pack sur `GLOBAL` (`Plateforme entière`) purge automatiquement toute activation partielle redondante sur un sous-périmètre (`BU` / `Espace`) et empêche les doublons `Plateforme entière` + `Direction`. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modification | Mise à jour du test `"presents the backend-known Business Packs catalog..."` pour vérifier l'absence de `pack-key-input` et `save-pack-btn` ainsi que la déduplication automatique d'une activation `Direction · Direction Produit` lors du passage à `Plateforme entière`. |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-05-unification-activation-unique-packs-metiers-sally-winston-tech-lead-report.md` | Création | Rapport Tech Lead pérenne documentant le dialogue Sally & Winston, l'analyse GitNexus et le bilan de vérification. |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Référencement du rapport dans l'index chronologique. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests TypeScript (`pnpm turbo run lint typecheck test`)** : `9/9 tasks successful` (`@orcia/ui`: `15 files, 55 tests passed`; `@orcia/api-client`: `2 files, 10 tests passed`; `@orcia/web`: `1 file, 20 tests passed`).
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `All checks passed! 518 files already formatted` (`0 warning`)
  - `pnpm turbo run lint typecheck` : `0 error`
  - `lint_spine.py` : `ok: true, total_findings: 0`

### 3.3 Validation & Procédure de Test (5 Couches `AD-17` + Garde-Fous UX/UI)
- **Couche 1 — Tests Unitaires & Composants (`Vitest`)** : Validation de l'unicité de la méthode d'activation (`queryByTestId("pack-key-input") === null`, `queryByTestId("save-pack-btn") === null`) et de la déduplication hiérarchique (`Direction · Direction Produit` $\rightarrow$ `Plateforme entière`).
- **Couches 2 à 5 — Persistance & Contrat** : Contrat JSONB `platform_setup_state` (`packs`) inchangé (`0-diff` OpenAPI) et nettoyage automatique des états déjà en cache ou en base via `deduplicateConfiguredPacks`.

