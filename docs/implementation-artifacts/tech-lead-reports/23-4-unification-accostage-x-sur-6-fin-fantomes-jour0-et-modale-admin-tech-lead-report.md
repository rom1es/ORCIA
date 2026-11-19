# Story 23.4 — Unification Accostage `X/6` PG18, Suppression des Fantômes Jour 0 (`AP`, `Notifications 4`) & Ergonomie Modale Premier Administrateur

- **Date** : 2026-11-19
- **Story / Clé Sprint** : `23-4-unification-accostage-x-sur-6-fin-fantomes-jour0-et-modale-admin` (`Epic 23` — Vague 1 `P1`)
- **Capacité(s)** : `CAP-005`, `CAP-060`, `CAP-061` — classification : `feature` + `ux` + `hygiène` (`REM23-06`, `REM23-07`, `REM23-08` / `ARCH23-05`, `P1-UX-4`, `P1-UX-6`, `P1-UX-7`, `P2-UX-8`, `P2-UX-9`, `P2-UX-11`)
- **Auteur / Contexte** : `22.10-impl` (Sally × Winston — pré-implémentation Epic 23). Aligne le parcours d'accostage Jour 0 sur une source de vérité PostgreSQL 18 unique **`Accostage X/6`**, supprime l'identité fantôme `AP` et les `Notifications 4` avant la création du premier utilisateur, homogénéise la coquille sous modale Jour 0 et corrige les défauts ergonomiques de `FirstBootAdminSetupModal`.
- **Commits associés** : `En attente d'implémentation (initialisé par Story 22.10)`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Preuves E2E & Captures (`e2e-campaign-epic-22`)** :
  1. **Split-brain Accostage `X/5` vs `6` jalons (`REM23-06` / `P1-UX-6`, `ARCH23-05`)** :
     - Sur [`#5` (`01-day0-boot` F5)](../e2e-campaign-epic-22/screenshots/01-day0-boot-and-f5-persistence/desktop-cockpit--le-premier-administrateur-cree-survit-a-un-f5-sans-localstorage-rehydratation-postgresql--passed.png) et [`#10` (`03-human-led`)](../e2e-campaign-epic-22/screenshots/03-human-led-anchor-and-arbitration/desktop-cockpit--signature-de-l-ancrage-violet-30-car-rejet-agent-422-arbitrage-motive-et-survie-au-f5--passed.png), `Accostage 0/5` s'affiche deux fois alors que l'Étape 1 (`Alice Admin E2E ✓`) est validée (`2/5` en `#10` ignore toujours Étape 1) ; l'Étape 3 recommence par `1. Modèles IA` (doublon de l'Étape 2) et tronque 3 libellés sur 5 (`2. Structure Organisationnel...`, `4. Sources Documentaires &...`, `5. Packs Métiers & Atelier de...`).
     - Cause code : [`progressive_accostage.py#L146`](../../../packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py#L146) pré-remplit `self._completed_keys = {"first-admin"}` sur `ACCOSTAGE_SIX_MILESTONES` (`6` jalons, `L54-L97`), tandis que [`platformSetupStore.tsx#L451-L466`](../../../apps/web/src/components/platformSetupStore.tsx#L451-L466) recalcule `/5` sans `adminCreated`, et [`platformSetupHydration.ts#L191`](../../../apps/web/src/components/platformSetupHydration.ts#L191) ignore `workspace_llm_tier_mappings`.
  2. **Fantômes pré-admin Jour 0 & props mortes (`REM23-07` / `P1-UX-7`, `P2-UX-11`, `ARCH23-05`)** :
     - À `0` utilisateur en base ([`#2` modal](../e2e-campaign-epic-22/screenshots/00-stack-smoke/desktop-cockpit--apres-reset-jour-0-la-modale-de-premier-administrateur-est-presentee--passed.png), [`#4` 16.2](../e2e-campaign-epic-22/screenshots/00-stack-smoke/desktop-cockpit--story-16-2-moteur-reflexif-asyncio-survie-f5-waiting-write-preview-approbation-writeprev--failed.png), [`#6` reset](../e2e-campaign-epic-22/screenshots/01-day0-boot-and-f5-persistence/desktop-cockpit--apres-reset-jour-0-la-modale-revient-0-utilisateur-en-base--passed.png)), [`ShellContainer.tsx#L119-L125`](../../../apps/web/src/components/ShellContainer.tsx#L119-L125) retombe sur [`DEFAULT_HUMAN_PROFILE`](../../../apps/web/src/components/shellPresets.ts#L26-L32) (`AP Administrateur de la ... Contributeur`), `buildShellNotificationItems` (`shellScopeOptions.ts#L252-L336`) injecte `Notifications 4`, `hiddenMenuKeys` (`L263-L264`) masque `Configuration` (`7` menus vs `8`), et `buildShellDisabledMenuKeys` (`shellScopeOptions.ts#L189-L221`) laisse `Mes Espaces` et `Aide` noirs/actifs pendant que les autres sont grisés sans infobulle explicative. En outre, `ShellContainer.tsx#L202-L204,L278-L287` conserve `5` props mortes (`showOrganizationMenu`, `organizationMenuActive`, `activityMenuActive`, `onSelectOrganizationMenu`, `onSelectActivityMenu`).
  3. **Modale Premier Administrateur (`REM23-08` / `P1-UX-4`, `P2-UX-8`)** :
     - Dans [`FirstBootAdminSetupModal.tsx`](../../../apps/web/src/components/FirstBootAdminSetupModal.tsx), `closeLabel="Annuler (Esc)"` (`L105`) et `first-boot-admin-cancel-btn` (`L221-L228`) rendent deux boutons identiques `Annuler (Esc)` (avec anglicisme `Esc` et bordure noire dominante en haut à droite), le champ mot de passe affiche `placeholder="••••••••••••"` sur `WebkitTextSecurity: "disc"` (`L193,L199`), et le CTA principal `Créer le compte Administrateur` (`L233-L244`) manque de hiérarchie `#2563EB`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `ProgressiveDay0AccostageService` (`packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py:L130-L335`) : `impactedCount: 590`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 3` (`bootstrap/__init__.py`, `sql_first_user_guard.py`), `d=2: 404`, `d=3: 183`, `processes_affected: 195`, `modules_affected: 20`.
  - `ProgressiveDay0AccostageBanner` (`packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx`) : `impactedCount: 127`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 87`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 18`.
  - `InnerShellContainer` (`apps/web/src/components/ShellContainer.tsx`) : `impactedCount: 131`, `risk: "CRITICAL"`, `epistemic: "exact"`, `direct: 91`, `d=2: 33`, `d=3: 7`, `processes_affected: 138`, `modules_affected: 20` (`ShellContainer` comporte `6` homonymes dans l'index, max `impactedCount: 562`).
  - `FirstBootAdminSetupModal` : affecté par la latence d'index GitNexus (`2 commitsBehind`), vérifié par lecture directe (`L80-L260`).
- **Volumétrie & Découpages Obligatoires (`> 300–400` L)** :
  - `apps/web/src/components/platformSetupStore.tsx` (`521` L > `400` L) : extraire les types/dérivations d'accostage `Accostage6Milestones` dans `platformSetupAccostage.ts` (`< 200` L) et ramener `platformSetupStore.tsx` sous `< 380` L.
  - `apps/web/src/components/ShellContainer.tsx` (`403` L > `400` L) : supprimer les `5` props mortes Epic 21 et extraire les helpers de garde pré-admin dans `shellPresets.ts` / `shellScopeOptions.ts` pour descendre sous `< 350` L.
  - `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` (`335` L) : conserver sous `< 350` L.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)
- Aucune migration requise : toutes les tables PG18 (`users`, `workspace_llm_tier_mappings`, `org_units`, `workspaces`, `workspace_datasources`, `workflow_definitions_v2`) existent déjà.

### 2.2 Noyau Métier Hexagonal (`packages/orcia-core/`)
1. **`packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py`** :
   - Supprimer le hardcode `self._completed_keys = {"first-admin"}` à `L146` : calculer le premier jalon (`first-admin`) dynamiquement depuis le compte réel en PG18 (`users_count > 0` / `admin_created`).
   - Harmoniser `ACCOSTAGE_SIX_MILESTONES` (`L54-L97`) avec les 6 jalons non redondants : `1. Compte Admin`, `2. Modèles IA`, `3. Organisation`, `4. Premier Espace`, `5. Première Source`, `6. Premier Processus`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Vérifier que l'endpoint d'état d'amorçage/accostage reflète également `workspace_llm_tier_mappings` (`modelsCount > 0`) lors de l'hydratation après `F5`.
- Régénérer `@orcia/api-client` si un champ DTO d'accostage est ajusté (`0-diff` OpenAPI).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `packages/ui/`)
1. **Unification `Accostage X/6` (`platformSetupStore.tsx`, `platformSetupHydration.ts`, `cockpit/index.tsx`, `ProgressiveDay0AccostageBanner.tsx`)** :
   - Supprimer le calcul divergent `/5` et aligner sur les `6` jalons PG18 (`adminCreated` inclus dès création du premier admin → `1/6`, puis `workspace_llm_tier_mappings`, `orgUnits`, `workspaces`, `datasources`, `workflows`).
   - Afficher **un seul** badge `Accostage X/6` en en-tête de carte (retirer le doublon externe dans `cockpit/index.tsx#L181-L243`).
   - Corriger l'Étape 3 pour ne plus dupliquer `1. Modèles IA` (Étape 2) et agrandir les largeurs/colonnes de liste afin qu'aucun libellé ne soit tronqué à `1440px`.
2. **Suppression fantômes Jour 0 pré-admin (`ShellContainer.tsx`, `shellScopeOptions.ts`, `FourZoneSidebarRail.tsx`)** :
   - Quand `platformAdmin === null` (`0` utilisateur en base) :
     - Ne **pas** retomber sur `DEFAULT_HUMAN_PROFILE` (`AP`) : afficher un état anonyme neutre (ou aucune carte profil utilisateur).
     - Ne **pas** générer les `4` notifications synthétiques `SETUP_PREREQUISITE` (`Notifications 4` -> `0` / masqué tant qu'aucun utilisateur n'est créé).
     - Verrouiller uniformément les entrées de menu bloquées au Jour 0 avec contraste WCAG AA lisible et infobulle explicative au survol/focus.
     - **Alerte compatibilité E2E (`shell.spec.ts#L55-L56,L94-L102`)** : `shell.spec.ts` vérifie actuellement l'absence de `eight-menu-item-configuration` sans `PLATFORM_ADMIN` et inspecte `disabledReasons` (`aria-disabled="true"`). Préserver ce contrat explicite ou synchroniser `shell.spec.ts` en cohérence avec la politique `RBAC` Direction C (`Configuration` réservée aux rôles `PLATFORM_ADMIN`).
     - Supprimer les `5` props mortes `showOrganizationMenu`, `organizationMenuActive`, `activityMenuActive`, `onSelectOrganizationMenu`, `onSelectActivityMenu` dans `ShellContainer.tsx`.
3. **Ergonomie Modale Jour 0 (`FirstBootAdminSetupModal.tsx`, `RadixDesignSystemPrimitives.tsx`, `fr.ts`)** :
   - Supprimer le double bouton `Annuler (Esc)` (`first-boot-admin-cancel-btn` `L221-L228`) ; conserver uniquement la fermeture accessible cohérente avec la nature obligatoire de la création d'admin Jour 0 (pas d'annulation ambiguë ni d'anglicisme `(Esc)`, libellé `(Échap)` si fermeture présente).
   - Retirer `placeholder="••••••••••••"` (`L193`) au profit d'un champ vide (`placeholder=""` + bouton œil afficher/masquer le mot de passe).
   - Donner au CTA primaire `Créer le compte Administrateur` un style plein `#2563EB` net (et un état désactivé clairement différencié tant que les champs requis sont incomplets).

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (`pytest`)** : tests unitaires de `progressive_accostage.py` vérifiant `0/6` sans utilisateur, `1/6` dès création admin (sans `{"first-admin"}` en dur), et progression réelle `1/6 -> 6/6`.
- **Couche 1b (`Vitest`)** : mise à jour/ajout de tests dans `apps/web/src/__tests__/` (`day0-modal-and-settings-auth-token-wiring.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`) vérifiant : zéro `AP`, zéro `Notifications 4` à `0` utilisateur, un seul badge `Accostage X/6`, absence de double bouton `Annuler`, présence bouton œil mot de passe.
- **Couche 2 (`testcontainers` PG18)** : extension de `test_contextual_help_and_accostage_postgres18.py` vérifiant `Accostage 0/6 -> 1/6 -> 2/6` après création admin et modèle IA dans `workspace_llm_tier_mappings`.
- **Couche 5 (E2E)** : `01-day0-boot-and-f5-persistence.spec.ts` et `shell.spec.ts` verts en Desktop + Mobile.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

> *[Pré-implémentation initialisée en Story 22.10 — à compléter après implémentation et validation de la Story 23.4]*

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/progressive_accostage.py` | Modification | *[À compléter après implémentation Story 23.4]* |
| `apps/web/src/components/platformSetupStore.tsx` + `platformSetupAccostage.ts` + `platformSetupHydration.ts` | Refactoring / Modification | *[À compléter après implémentation Story 23.4]* |
| `apps/web/src/components/ShellContainer.tsx`, `shellScopeOptions.ts`, `FirstBootAdminSetupModal.tsx` | Refactoring / Modification | *[À compléter après implémentation Story 23.4]* |
| `apps/web/src/features/cockpit/index.tsx` & `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx` | Modification | *[À compléter après implémentation Story 23.4]* |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : *[À compléter — $\ge 90\%$ requis]*
- **Qualité statique & Architecture** : `ruff`, `mypy --strict`, `pnpm turbo run lint typecheck test`, `gitnexus_detect_changes()` *[À compléter]*

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- *[À compléter après passage de `01-day0-boot` et `shell.spec.ts`]*
