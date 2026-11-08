# 2026-11-08 — CAP-ACT-1..4 : contrôle CI du registre, PRD v2, réconciliation Epic 6, Epic 13

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-cap-act-1-a-4-gouvernance-registre-capacites` (`Ajustement Transverse`)
- **Capacité(s)** : `none (hygiène/doc)` — outillage de gouvernance ; classification `doc`
- **Auteur / Contexte** : suite du rapport `2026-11-08-registre-capacites-fonctionnelles`. Consigne ajoutée à `AGENTS.md` §5 (GEMINI.md). Exécution de CAP-ACT-1 (contrôle de couverture route/routeur), CAP-ACT-2 (PRD v2, FR-31..36), CAP-ACT-3 (Epic 6 vs journal d'activité), CAP-ACT-4 (Epic 13 + champ `capability`).
- **Commits associés** : à renseigner.

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Sans contrôle automatique, le registre redeviendra obsolète. Il faut échouer en CI si une route SPA ou un routeur FastAPI n'a pas de capacité.
- `infra/scripts/sync_site_catalog.py` fait déjà **836 lignes** → interdit d'y ajouter la logique : nouveau module `infra/scripts/capabilities_registry.py`, simple appel depuis `main()`.
- Le PRD (30 FR) ne couvre pas les Epics 8–12 ; `epics.md` a une `FR Coverage Map` à étendre.
- Epic 6 : vérifier dans le code ce qui existe réellement (`audit_ledger`, `/activity`, `/finops`) avant de rebaser les stories.

### 1.2 Exploration, Impact GitNexus, Factorisation & Dette
- **GitNexus** : scripts `infra/` hors graphe applicatif ; aucun symbole `orcia_core`/`orcia_api`/`apps/web` modifié → impact applicatif nul.
- **Factorisation** : réutilisation de `parse_active_routes` (via import du module de synchronisation) ; le nouveau module ne duplique pas le parsing de routes.
- **Volumétrie** : nouveau module < 200 lignes ; tests dans `tests/unit/test_capabilities_registry.py`.
- **Dette** : le manifeste `/showcase` n'expose pas encore les capacités (le type `OrciaShowcaseManifestData` vit dans `@orcia/ui`) → ticket `CAP-ACT-5`.

---

## 2. Plan d'Implémentation

### 2.1 Alembic — non applicable.
### 2.2 Noyau hexagonal & workers — non applicable.
### 2.3 Outillage / contrats
- `infra/scripts/capabilities_registry.py` : `load_registry`, `validate_registry` (ids uniques, champs obligatoires, statuts, FR proposés déclarés), `discover_surfaces` (routes SPA, fichiers routeurs contenant `APIRouter(`), `check_coverage` (surface référencée par une capacité ou listée dans `coverage_exemptions` avec raison).
- Appel dans `sync_site_catalog.py --check` (échec = exit 1) ; TDD : tests rouges d'abord.
- `docs/product/capabilities.yaml` : ajout du bloc `coverage_exemptions`.
- Documentation : PRD v2 (§4.10 FR-31..36 + glossaire), `epics.md` (FR Coverage Map, Epic 13, Epic 6 rebasé), `sprint-status.yaml` (epic-13, statuts `CAP-ACT-*`), gabarit de rapport (`Capacité(s)`).
### 2.4 Interface SPA — non applicable.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers
| Fichier | Nature | Description |
| :--- | :--- | :--- |
| `AGENTS.md` (= `GEMINI.md`) | Modification | §5 « Registre des Capacités » (consulter avant, mettre à jour après, `pnpm site:check`), PRD v2.0 / 36 FR, entrée « Where things are » |
| `CLAUDE.md` | Modification | Pointeur vers le registre |
| `infra/scripts/capabilities_registry.py` | Création | Validation schéma + couverture routes SPA / routeurs FastAPI + FR ≤ max du PRD |
| `infra/scripts/sync_site_catalog.py` | Modification | `--check` appelle `run_registry_check()` (+5 lignes, pas de croissance du fichier de 836 l.) |
| `tests/unit/test_capabilities_registry.py` | Création | 6 tests (TDD rouge → vert), dont registre réel valide et couvrant |
| `docs/product/capabilities.yaml` | Modification | `coverage_exemptions`, FR-31..36 fusionnés dans `fr`, surfaces complétées, notes Epic 6 |
| `docs/planning-artifacts/prds/.../prd.md` | Modification | v2.0 : §4.10 FR-31..FR-36 |
| `docs/planning-artifacts/epics.md` | Modification | FR Coverage Map FR-31..36, note de réconciliation Epic 6, Epic 13 (Stories 13.1, gabarit 13.x) |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | `epic-13`, 13.1 en `review`, CAP-ACT-2/3/4 `done`, CAP-ACT-1 `in-progress`, CAP-ACT-5 |
| `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md` | Modification | Champ `Capacité(s)` |
| `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html` | Régénération | `pnpm site:sync` (manifeste périmé : 66 → 81 primitives UI) |

### 3.2 Résultats
- **CAP-ACT-3 (constat code)** : aucune migration `audit_ledger` ; `audit_finops/` = `errors.py` ; `/finops` = coquille ; `/activity` lit `auditEvents` du snapshot d'accostage. Epic 6 reste 100 % `backlog` ; Story 6.1 remplace la source de `/activity`.
- Le contrôle a détecté 9 trous dans le registre initial (routeurs/routes non référencés), corrigés → `pnpm site:check` OK, `pytest` registre + site 9/9, `ruff` et `mypy --strict` verts sur le nouveau module.
- **Hors périmètre / non fait** : parcours runtime des 57 capacités et exposition au manifeste `/showcase` (→ `CAP-ACT-5`) ; `gitnexus_detect_changes` non exécuté (aucun symbole applicatif touché) ; couverture `--cov-fail-under=90` non applicable (scripts `infra/`).
