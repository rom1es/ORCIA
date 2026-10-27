# Prompt BMAD : intégrer la réévaluation de la stack et la modularité au plan ORCIA

> À soumettre dans une nouvelle conversation. Les étapes sont **séquentielles** : chacune démarre seulement quand la précédente a produit ses livrables et que je les ai validés.

---

## Contexte et documents d'entrée (à lire en premier)
- `docs/planning-artifacts/research/stack-review-2026-10-27.md` : écarts E1 à E8 entre la spine et le code, préconisations **P1 à P9**, option Rust
- `docs/planning-artifacts/research/modularity-analysis-2026-10-27.md` : diagnostic du couplage, pistes **M1 à M11**, phases **A à F**, décisions ouvertes
- `docs/planning-artifacts/research/technical-frontend-spa-nextjs-vs-vite-tanstack-rou-2026-10-27/` : recherche existante sur le front (pour P8)
- Spine : `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md` et `architecture.md`
- PRD : `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md`
- Epics : `docs/planning-artifacts/epics.md` · Sprint : `docs/implementation-artifacts/sprint-status.yaml`
- Règles : `AGENTS.md` (Tech Lead, TDD, couverture ≥ 90 %, 5 couches de tests, invariants)

Langue des livrables : **français**. Toute commande Python passe par `.venv/bin/`. Toute requête GitNexus est limitée à `repo: "ORCIA"`.

---

## Étape 1 : `bmad-architecture` (Winston), mode *validate* puis *update*
**Objectif** : transformer P1 à P9 et M1 à M11 en décisions d'architecture.

1. **Valider** : vérifier toi-même les écarts E1 à E8 et les 3 dépendances circulaires (`blackboard` ↔ `orchestration`, `catalog` ↔ `bootstrap`, `permissions` ↔ `bootstrap`), en utilisant `gitnexus_context` et `gitnexus_impact` (`direction: upstream`) sur `orchestration/engine.py`, `blackboard/models.py`, `bootstrap/__init__.py` et `permissions/broker.py`. **Signaler tout risque HIGH ou CRITICAL.**
2. **Décider et rédiger** :
   - **nouvel AD-19** « Monolithe modulaire » : sens unique des dépendances, packages `uv` (au départ `kernel`, `core`, `api`, `worker`), un seul point d'assemblage, `import-linter`, `schemas` déplacés dans `apps/api`, erreurs par domaine, événements outbox pour les effets secondaires, plugins `entry_points` et MCP ;
   - **amender AD-1** : packaging `uv`, rôle de Next.js (P8) ;
   - **amender AD-2, AD-13, AD-18** : moteur d'exécution durable (P2). Si les faits externes manquent, laisser `[PENDING-RECON]` et recommander `bmad-deep-recon` ;
   - **amender AD-8** (BM25, P7), **AD-9** (sandbox, P5, Rust en option), **AD-12** (OpenTelemetry, P9) ;
   - **corriger le tableau des versions** (P3, P6) et **ajouter les dépendances nouvelles** (`import-linter`, et éventuellement `cedarpy` ou `jsonschema-rs`).
3. **Respecter les invariants** : UUIDv7, Alembic immuable, `audit_ledger` et `blackboard_snapshots` en ajout seul, RFC 9457, `@orcia/ui` isolé, i18n en français par défaut, pas de microservices ni de base par domaine.
4. **Lint obligatoire, 0 finding** :
   `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`

**Livrables de l'étape 1**
- Spine et `architecture.md` mis à jour.
- Rapport de validation (écarts classés par gravité).
- Liste des questions ouvertes.

⏸️ **Pause : je dois arbitrer les questions ouvertes avant l'étape 2.**

---

## Étape 2 : `bmad-correct-course`
**Objectif** : mesurer l'impact sur le plan en cours et produire une **proposition de changement de sprint**.

À traiter :
- Impact sur le PRD (NFR concernés, éventuellement NFR-MAINT nouveau), les epics, l'architecture et l'UX (Epic UI, P8 et M11).
- **Placement** des phases de modularité et des préconisations :

  | Élément | Placement attendu |
  |---|---|
  | Phase A (M1, M3, M4, M5) + P1 + P9 | `Story 3.1a` : squelette de bout en bout et assainissement (Étape 0, refactorisation préalable) |
  | Phase B (M2) + P3 + P4 | `action_item` ou `Story 3.1b` |
  | P2 (moteur durable) | Spike `bmad-deep-recon`, bloquant pour la phase D |
  | Phase C (M9, M11) | Intégrée aux stories des workers réels et de l'Epic UI |
  | Phase D (M6, M7) | `Story N.Ma` placée avant l'Epic autonomie et déclencheurs (AD-18) |
  | Phase E (M8, P5, Rust) | `Story N.Ma` liée à AD-9 |
  | P6, P7 | `action_items`, avec veille externe |
  | Phase F (M10) | Backlog après le MVP |
- **Réordonnancement** des 23 stories restantes et dépendances explicites.
- Risques, estimation d'effort, impact sur le calendrier.

**Livrable de l'étape 2** : la proposition de changement de sprint (chemin à indiquer).

⏸️ **Pause : je valide la proposition.**

---

## Étape 3 : `bmad-create-epics-and-stories`, en mise à jour
**Objectif** : rédiger les nouvelles stories dans `docs/planning-artifacts/epics.md`.
- Pour chaque story (`3.1a`, `3.1b`, `N.Ma`…) : récit utilisateur, **critères d'acceptation testables** (dont « `import-linter` passe en CI », « 0 singleton créé au chargement dans `apps/api` », « run persisté puis repris après un redémarrage », « génération du SDK OpenAPI sans différence »), AD concernés, dépendances, et les 5 couches de tests (AD-17).
- Ne **jamais** modifier les stories déjà terminées.

---

## Étape 4 : `bmad-sprint-planning`, mode *validate / fix*
**Objectif** : mettre `docs/implementation-artifacts/sprint-status.yaml` en cohérence.
- Ajouter les nouvelles stories (statut `backlog` ou `ready-for-dev`) et les `action_items` (identifiant, priorité, AD, dépendance, `TODO(key)` utilisable).
- Vérifier l'ordre et les dépendances, et l'absence de story orpheline.

---

## Étape 5 : vérification finale de la prise en compte (obligatoire)
**Objectif** : prouver que **chaque élément d'entrée** a une destination. Lancer **`bmad-review`** (lentilles *verification gaps* et *structure*) sur le résultat des étapes 1 à 4, puis produire la **matrice de traçabilité** ci-dessous dans `docs/implementation-artifacts/tech-lead-reports/stack-and-modularity-integration-tech-lead-report.md` (gabarit `TECH-LEAD-REPORT-TEMPLATE.md`).

### 5.1 Matrice de traçabilité (une ligne par élément, aucune case vide)
| ID | Élément | Décision (Retenu / Différé / Rejeté + justification) | AD (section de la spine) | Story ou action_item | Critère d'acceptation vérifiable | Preuve (fichier:ligne) |
|---|---|---|---|---|---|---|
| E1–E8 | Écarts entre la spine et le code | | | | | |
| P1–P9 | Préconisations sur la stack | | | | | |
| M1–M11 | Pistes de modularité | | | | | |
| Rust | Sandbox-runner, Cedar | | | | | |
| Q1–Q4 | Décisions ouvertes de l'analyse de modularité (§4) | | | | | |

### 5.2 Contrôles automatiques à exécuter et à rapporter
- [ ] `lint_spine.py` → **0 finding** (sortie collée)
- [ ] `grep -n "AD-19" ARCHITECTURE-SPINE.md` → présent ; AD-1, 2, 8, 9, 12, 13 et 18 amendés (citer les lignes)
- [ ] Tableau des versions de la spine = `package.json` / `pyproject.toml` cibles, ou écart justifié
- [ ] Chaque nouvelle story de `epics.md` est présente dans `sprint-status.yaml`, et inversement
- [ ] Chaque `action_item` a un identifiant, une priorité, un AD et une dépendance
- [ ] Aucune story terminée n'a été modifiée (`git diff` sur les stories `done`)
- [ ] Aucun marqueur `[PENDING-RECON]` sans `action_item` `bmad-deep-recon` associé
- [ ] Les 3 cycles, les `schemas`, `exceptions.py` et les 3 singletons sont chacun couverts par un critère d'acceptation de `Story 3.1a`

### 5.3 Résultat attendu
- Un verdict **CONFORME / NON CONFORME**, avec la liste des éléments manquants.
- En cas de NON CONFORME : **corriger, puis relancer l'étape 5** jusqu'à obtenir CONFORME.
- Pour finir : la liste des fichiers modifiés et les prochaines actions (spike P2, puis démarrage de `Story 3.1a` via `bmad-build`).
