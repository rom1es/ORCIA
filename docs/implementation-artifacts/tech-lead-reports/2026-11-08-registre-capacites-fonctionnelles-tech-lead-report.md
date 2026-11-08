# 2026-11-08 — Registre des capacités fonctionnelles (source de vérité « ce qui est en place »)

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-registre-capacites-fonctionnelles` (`Ajustement Transverse` — gouvernance documentaire)
- **Auteur / Contexte** : audit validé par l'utilisateur (artefact `audit-fonctionnalites-orcia.md`). Les fonctionnalités sont dispersées entre PRD (30 FR, sans Epics 8–12), `epics.md`, `sprint-status.yaml` et 92 rapports Tech Lead (dont 38 hors epic). Objectif : un registre unique `docs/product/capabilities.yaml`, lié aux FR, aux epics/rapports et aux surfaces (route, routeur, composant UI, migration).
- **Commits associés** : à renseigner à la validation.

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Aucun document ne répond à « qu'est-ce qui est livré aujourd'hui ? ». Le PRD ne couvre pas Mes Espaces, Mon Assistant, pack-builder, wizards, banc MCP/A2A ; `GEMINI.md` annonce 33 FR pour 30 réels.
- Au moins 8 capacités fonctionnelles sont nées hors epic (journal d'activité, agents & skills, authentification modèles IA, IAM…). Chevauchement possible Journal d'activité ↔ Story 6.1 (`backlog`).
- Changement **documentaire et outillage uniquement** : aucune migration, aucun code applicatif orcia_core/api/web.

### 1.2 Exploration, Impact GitNexus, Factorisation & Dette
- **GitNexus** : seul `infra/scripts/sync_site_catalog.py` (script autonome, hors graphe applicatif) sera touché ; aucun symbole `orcia_core`/`orcia_api`/`apps/web` modifié → impact applicatif nul. (`gitnexus_detect_changes` exécuté en fin de lot.)
- **Exploration** : 20 routes actives (manifeste), 31 routeurs FastAPI, 27 migrations Alembic, 66 primitives UI, 92 rapports.
- **Factorisation** : le manifeste `/showcase` est déjà généré ; le registre l'alimentera plutôt que de créer un second inventaire. Le check de couverture sera ajouté dans `sync_site_catalog.py` (volumétrie vérifiée avant édition ; split si > 400 l.).
- **Dette / tickets** : Epic 13 « Évolutions continues » + réconciliation Epic 6/7 + PRD v2 (FR-31+) à inscrire dans `sprint-status.yaml` `action_items` (CAP-ACT-1..4).

---

## 2. Plan d'Implémentation

### 2.1 Alembic
- Non applicable.

### 2.2 Noyau hexagonal & workers
- Non applicable.

### 2.3 Backend / SDK / outillage
- Créer `docs/product/capabilities.yaml` (schéma : `id`, `title`, `fr`, `origin`, `origin_ref`, `status`, `surfaces{route,api,ui,migration}`, `verified`), rétro-rempli depuis epics, rapports ad-hoc, routes et routeurs.
- Étape suivante (lot ultérieur, après validation du registre) : ajout du champ `capability` au gabarit de rapport ; check CI route/routeur sans capacité dans `sync_site_catalog.py`.
- Inscrire les `action_items` ci-dessus dans `sprint-status.yaml`.

### 2.4 Interface SPA
- Non applicable (le `/showcase` consommera le registre dans un lot ultérieur).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers
| Fichier | Nature | Description |
| :--- | :--- | :--- |
| `docs/product/capabilities.yaml` | Création | 57 capacités (54 live, 1 partial, 2 planned ; 40 issues d'epics, 17 ad-hoc), blocs `proposed_fr` FR-31..36 |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | `action_items` CAP-ACT-1..4 (vérification runtime + check CI, PRD v2, réconciliation Epic 6, Epic 13 + champ `capability`) |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Entrée du présent rapport |

### 3.2 Résultats & limites
- **Correction d'audit** : l'audit initial citait 75 rapports / 24 ad-hoc (manifeste du 06/11). Le dénombrement réel est 92 rapports dont 38 ad-hoc ; les 14 rapports 06–08/11 manquants (assistant, notifications d'équipes, rattachement équipe/facturation, FAQ…) ont été intégrés (CAP-043, 067, 068, 075, 076, 084, 092).
- YAML validé par `yaml.safe_load` (ids uniques, 4 action_items lisibles).
- Aucun code applicatif touché : tests 5 couches AD-17, couverture et `pnpm site:sync` non concernés (le registre n'est pas encore branché sur le manifeste → CAP-ACT-1).
- **Limite** : registre `verification: docs` (déduit des rapports/routeurs), pas rejoué à l'exécution. Statut de CAP-065 / CAP-200 à confirmer (CAP-ACT-3).
