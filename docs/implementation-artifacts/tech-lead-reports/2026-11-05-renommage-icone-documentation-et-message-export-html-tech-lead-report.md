# Rapport Tech Lead — Renommage de l'Icône de Documentation (« Documentation ») & Simplification du Message d'Export HTML (`docs/site-catalog/index.html`)

- **Identifiant** : `2026-11-05-renommage-icone-documentation-et-message-export-html-tech-lead-report`
- **Date** : `2026-11-05`
- **Auteur** : Tech Lead / Dev Senior (Antigravity)
- **Périmètre** : `packages/ui` (`OrciaProductShowcaseSiteView.tsx`), `apps/web` (`ShellContainer.tsx`, `features/ontology/index.tsx`), `infra/scripts/sync_site_catalog.py`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Besoin exprimé
1. **Libellé court de l'icône / bouton de documentation** : L'entrée / bouton d'accès à la documentation d'ORCIA (`open-orcia-showcase-site-btn` dans le menu latéral gauche et sur l'écran d'aide `/help`) doit être nommé **`Documentation`** seulement (au lieu de `"Site de Présentation ORCIA (Vision, Fonctionnalités & Architecture)"`).
2. **Simplification du message d'ouverture du fichier HTML autonome** : Dans la bannière d'export (`showcase-standalone-export-banner` de `OrciaProductShowcaseSiteView.tsx`), indiquer **`ouvrez directement \`docs/site-catalog/index.html\`.`** plutôt que `"ouvrez directement \`docs/site-catalog/index.html\` ou \`dist/orcia-site/index.html\` dans n'importe quel navigateur (zéro serveur requis, synchronisé via \`pnpm site:sync\`)."`.

### 1.2 Analyse d'impact GitNexus (`repo: /home/romain/Documents/Projects/ORCIA`)
- `InnerShellContainer` (`apps/web/src/components/ShellContainer.tsx`) : impact amont `LOW` (appelé uniquement par `ShellContainer`). Contient le bouton latéral `open-orcia-showcase-site-btn` (lignes 282-308).
- `OntologyFeaturePanel` (`apps/web/src/features/ontology/index.tsx`) : impact amont `LOW` (monté sur `/ontology` et `/help`). Contient le bouton `open-orcia-showcase-site-btn` (lignes 74-83).
- `OrciaProductShowcaseSiteView` (`packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx`) : appelé uniquement par `ShowcaseRouteView` (`apps/web/src/routes/showcase.tsx`). Contient la bannière `showcase-standalone-export-banner` (lignes 358-367).
- Tests associés : `apps/web/src/__tests__/orcia-showcase-site.test.tsx`.

---

## 2. Plan d'Implémentation

### 2.1 Base de données & Migrations Alembic
- Aucune modification de schéma SQL requise.

### 2.2 Noyau Hexagonal & Outillage (`infra/scripts/sync_site_catalog.py`)
- Exécuter `pnpm site:sync` après mise à jour du rapport Tech Lead dans `docs/implementation-artifacts/tech-lead-reports/README.md` afin de régénérer `apps/web/src/generated/orciaSiteManifest.ts` et `docs/site-catalog/index.html`.

### 2.3 Backend FastAPI & SDK OpenAPI
- Aucune modification d'endpoint HTTP requise.

### 2.4 Interface SPA Vite + TanStack Router & Design System `@orcia/ui`
1. `apps/web/src/components/ShellContainer.tsx` :
   - Sur `open-orcia-showcase-site-btn`, remplacer le libellé `"Site de Présentation ORCIA (Vision, Fonctionnalités & Architecture)"` / `"ORCIA Product & Architecture Site"` par `"Documentation"`.
2. `apps/web/src/features/ontology/index.tsx` :
   - Sur `open-orcia-showcase-site-btn`, remplacer le libellé `"🌐 Site de Présentation ORCIA (Vision, Fonctionnalités & Architecture)"` / `"🌐 ORCIA Product & Architecture Site"` par `"🌐 Documentation"`.
3. `packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx` :
   - Sur `showcase-standalone-export-banner`, remplacer le texte par :
     - FR : `"Export HTML5 autonome prêt : ouvrez directement \`docs/site-catalog/index.html\`."`
     - EN : `"Standalone HTML5 export ready: open \`docs/site-catalog/index.html\` directly."`
4. `apps/web/src/__tests__/orcia-showcase-site.test.tsx` :
   - Vérifier que `open-orcia-showcase-site-btn` affiche `"Documentation"` et que le clic sur `showcase-export-standalone-btn` affiche `"ouvrez directement \`docs/site-catalog/index.html\`."` dans `showcase-standalone-export-banner`.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Fichiers modifiés
| Fichier | Nature de la modification |
| :--- | :--- |
| `apps/web/src/components/ShellContainer.tsx` | Renommage du bouton latéral `open-orcia-showcase-site-btn` en `🌐 Documentation` uniquement. |
| `apps/web/src/features/ontology/index.tsx` | Renommage du bouton `open-orcia-showcase-site-btn` en `🌐 Documentation` uniquement. |
| `packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx` | Simplification du message `showcase-standalone-export-banner` en `Export HTML5 autonome prêt : ouvrez directement \`docs/site-catalog/index.html\`.` |
| `apps/web/src/__tests__/orcia-showcase-site.test.tsx` | Mise à jour des assertions de test sur le libellé `Documentation` et sur le message d'export HTML simplifié. |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Enregistrement du rapport Tech Lead (`72` rapports indexés). |
| `apps/web/src/generated/orciaSiteManifest.ts` & `docs/site-catalog/index.html` | Régénération automatique via `pnpm site:sync`. |

### 3.2 Résultats des Portes de Vérification
- `.venv/bin/python infra/scripts/sync_site_catalog.py --check` : **OK** (`72 reports, 20 routes, 66 UI primitives`).
- `pnpm turbo run lint typecheck test` : **9/9 tâches réussies** (`@orcia/ui`, `@orcia/api-client`, `@orcia/web` — `28/28` tests Vitest passés dont `orcia-showcase-site.test.tsx`).
- `.venv/bin/pytest tests/unit/test_site_catalog_sync.py -q` : **3 passed**.
