# Rapport Tech Lead — Unification UX/UI des Onglets (`@orcia/ui` & `apps/web`) : Bleu Intense au Focus / Sélection (`aria-selected="true"`) & Bleu Pâle Hors Focus (`aria-selected="false"`), ADR `AD-22` & `ACTION_ITEM UX-DS-RADIX-01`

- **Identifiant** : `2026-11-05-unification-ux-onglets-bleu-intense-actif-bleu-pale-inactif-tech-lead-report`
- **Date** : `2026-11-05`
- **Auteur** : Tech Lead / Dev Senior (Antigravity), Sally (UX/UI Designer) & Winston (Architecte)
- **Périmètre** : `packages/ui/src/styles/tokens.css`, `packages/ui/src/primitives/*`, `packages/ui/src/components/AgentsAndSkillsManagerView.tsx`, `apps/web/src/routes/settings.tsx`, `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md`, `docs/implementation-artifacts/sprint-status.yaml`, `infra/scripts/sync_site_catalog.py`, `apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Besoin exprimé & Validation UX (Sally) + Architecture (Winston)
1. **Hiérarchie chromatique unifiée de tous les onglets d'ORCIA** :
   - **Onglet actif ou ayant le focus (`aria-selected="true"`, `:focus-visible`)** : Conserver le **fond bleu intense** (`--color-tab-active-bg: #2563EB`, bordure `--color-tab-active-border: #1D4ED8`, texte blanc `--color-tab-active-fg: #FFFFFF`, ratio de contraste WCAG AA `5.17:1`).
   - **Onglets inactifs / hors focus (`aria-selected="false"`)** : Appliquer systématiquement un **fond bleu pâle** (`--color-tab-inactive-bg: #DBEAFE`, survol `--color-tab-inactive-hover-bg: #BFDBFE`, bordure `--color-tab-inactive-border: #93C5FD`, texte bleu foncé `--color-tab-inactive-fg: #1E3A8A`, ratio de contraste WCAG AAA `8.95:1`).
2. **Adoption en `action_item` et formalisation en ADR (`AD-22`) du socle Design System open source `Radix UI Primitives` + `shadcn/ui` dans `@orcia/ui`** :
   - Ajouter l'action item `UX-DS-RADIX-01` dans `docs/implementation-artifacts/sprint-status.yaml`.
   - Graver la décision d'architecture **`AD-22`** dans `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md`.

### 1.2 Analyse d'impact GitNexus (`repo: /home/romain/Documents/Projects/ORCIA`)
- `SettingsHubView` (`apps/web/src/routes/settings.tsx`) : impact amont `LOW`.
- `WorkspaceFiveTabsAndExternalRebaseView` (`packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`) : impact amont `LOW`.
- `AgentsAndSkillsManagerView` (`packages/ui/src/components/AgentsAndSkillsManagerView.tsx`) : impact amont `LOW`.
- `OrciaTabBar` (`packages/ui/src/primitives/DesignSystemControls.tsx`) : primitive centrale du Design System `@orcia/ui`.

---

## 2. Plan d'Implémentation

### 2.1 Base de données & Migrations Alembic
- Aucune modification SQL requise.

### 2.2 Noyau Hexagonal, Architecture (`AD-22`) & Outillage (`infra/scripts/sync_site_catalog.py`)
- Formaliser `AD-22` dans `ARCHITECTURE-SPINE.md` et `UX-DS-RADIX-01` dans `sprint-status.yaml`.
- Mettre à jour les styles CSS `.tab-btn` et `.tab-btn[aria-selected="true"]` dans `infra/scripts/sync_site_catalog.py` avec le fond bleu pâle (`#DBEAFE`) et le fond bleu intense (`#2563EB`), puis exécuter `pnpm site:sync`.

### 2.3 Backend FastAPI & SDK OpenAPI
- Aucune modification d'endpoint HTTP requise.

### 2.4 Design System `@orcia/ui` & Interface SPA `apps/web`
1. `packages/ui/src/styles/tokens.css` :
   - Déclarer dans `:root` et `[data-theme="dark"]` les tokens `--color-tab-active-bg`, `--color-tab-active-fg`, `--color-tab-active-border`, `--color-tab-inactive-bg`, `--color-tab-inactive-hover-bg`, `--color-tab-inactive-fg`, `--color-tab-inactive-border`.
   - Mettre à jour `.orcia-ds-tab` et `[role="tab"]` (inactif en bleu pâle `#DBEAFE`, actif/focus en bleu intense `#2563EB`).
2. Unifier les 10 barres d'onglets d'ORCIA sur `.orcia-ds-tab` :
   - `OrciaTabBar` (`DesignSystemControls.tsx` / `OrciaProductShowcaseSiteView.tsx`)
   - `apps/web/src/routes/settings.tsx`
   - `packages/ui/src/components/AgentsAndSkillsManagerView.tsx`
   - `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`
   - `packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx`
   - `packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx`
   - `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx`
   - `packages/ui/src/primitives/TopHeaderSearchCommand.tsx`
   - `packages/ui/src/primitives/WorkflowTopGovernanceBar.tsx`
   - `packages/ui/src/primitives/WorkspaceControlCenter.tsx`
3. Ajouter les assertions de non-régression dans `apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx`.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Fichiers modifiés
| Fichier | Nature de la modification |
| :--- | :--- |
| `packages/ui/src/styles/tokens.css` | Ajout des tokens `--color-tab-active-*` (`#2563EB`) et `--color-tab-inactive-*` (`#DBEAFE` / `#1E3A8A`) en mode clair et sombre, et application sur `.orcia-ds-tab` + `[role="tab"]` (`[aria-selected="true"]` & `:focus-visible`). |
| `apps/web/src/routes/settings.tsx` | Unification des onglets `Configuration` sur `.orcia-ds-tabs` / `.orcia-ds-tab`. |
| `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` | Unification des onglets `Mes Agents` (`Agents`, `Compétences`, `Connexions`) sur `.orcia-ds-tab`. |
| `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx` | Unification des 5 sous-onglets `Mes Espaces` sur `.orcia-ds-tab`. |
| `packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx` | Unification des 3 onglets `Mon Assistant` sur `.orcia-ds-tab`. |
| `packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx` | Unification des 3 onglets de gouvernance `Mon Assistant` sur `.orcia-ds-tab`. |
| `packages/ui/src/primitives/UserAccountDropdownAndSettingsModal.tsx` | Unification des 4 onglets `Paramètres de mon compte` sur `.orcia-ds-tab`. |
| `packages/ui/src/primitives/TopHeaderSearchCommand.tsx` | Unification des onglets de portée `⌘K` sur `.orcia-ds-tab`. |
| `packages/ui/src/primitives/WorkflowTopGovernanceBar.tsx` & `WorkspaceControlCenter.tsx` | Unification des onglets sur `.orcia-ds-tab`. |
| `infra/scripts/sync_site_catalog.py` & `docs/site-catalog/index.html` | Application du style bleu pâle / bleu intense aux onglets du site HTML autonome et régénération (`pnpm site:sync`). |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md` | Création de l'ADR **`AD-22`** (*Socle Design System Open Source `@orcia/ui` Radix UI + `shadcn/ui`, Séparation Tripartite, RGAA 4.1 & Hiérarchie Chromatique des Onglets*). |
| `docs/implementation-artifacts/sprint-status.yaml` | Ajout de l'action item **`UX-DS-RADIX-01`** (`status: open`, `ad_ref: "AD-1, AD-22"`). |
| `apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx` | Assertions automatisées sur les tokens `--color-tab-active-bg` et `--color-tab-inactive-bg`. |

### 3.2 Résultats des Portes de Vérification
- `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **OK (`0 findings`)**.
- `.venv/bin/python infra/scripts/sync_site_catalog.py --check` : **OK** (`73 reports, 20 routes, 66 UI primitives, 22 ADs`).
- `pnpm turbo run lint typecheck test` : **9/9 tâches réussies** (`28/28` tests dans `@orcia/web`, `15/15` fichiers de test dans `@orcia/ui`, `8/8` dans `@orcia/api-client`).
- `.venv/bin/pytest tests/unit/test_site_catalog_sync.py -q` : **3 passed**.
