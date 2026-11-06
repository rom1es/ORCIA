# 2026-11-06 — Documentation FAQ Architecture & Modèle Métier : Lien entre Espace de Travail (`Workspace`) et Entités de l'Organisation (`OrgUnit`)

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md`

- **Date** : 2026-11-06
- **Story / Clé Sprint** : `2026-11-06-documentation-faq-lien-workspace-org-unit` (`Documentation Architecture & Modèle Métier — Winston`)
- **Auteur / Contexte** : Winston (Architecte Système ORCIA) — Formalisation pérenne dans la documentation d'architecture (`architecture.md`), dans une fiche FAQ dédiée (`docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/faq-architecture-modele-metier.md`) et dans l'aide utilisateur (`docs/help/fr/spaces-sources.md` & `docs/help/en/spaces-sources.md`) de la distinction et des liens relationnels entre **l'objet Espace de Travail (`Workspace` / table `workspaces`)** et **les Entités de l'Organisation (`OrgUnit` / table `org_units`)** (`AD-6`, `AD-14`, `AD-21`, `FR-3`, `FR-21`, migration `0002_story_1_2_auth_org_workspaces_permissions.py`).
- **Commits associés** : `HEAD`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Question posée** : *« Quel est le lien entre l'objet Espace de Travail (quel est son terme interne dans ORCIA) et les entités de l'organisation ? »*
- **Problématique constatée** : Bien que le découplage entre l'arbre hiérarchique d'organisation (`org_units`) et les environnements opérationnels de travail (`workspaces`) soit implémenté dès la révision Alembic `0002_story_1_2_auth_org_workspaces_permissions.py` et dans le moteur d'habilitation (`AD-6`, `AD-14`, `AD-21`), il manquait dans la documentation d'architecture et dans l'aide contextuelle une section **FAQ Architecture & Modèle Métier (Winston)** synthétisant clairement :
  1. Les termes internes exacts dans ORCIA (`OrgUnit` / table `org_units` vs `Workspace` / table `workspaces`) et leur rôle respectif (*« Qui nous sommes »* vs *« Sur quoi nous travaillons »*).
  2. Les **deux liens relationnels SQL** (`owner_org_unit_id` en propriété `N ➔ 1` avec `ON DELETE RESTRICT`, et `workspace_memberships.invited_org_unit_id` en collaboration inter-équipes `N ➔ N`).
  3. Le **diagramme entité-relation (ER Mermaid)** complet reliant `ORG_UNITS`, `USERS`, `WORKSPACES`, `WORKSPACE_MEMBERSHIPS`, `WORKSPACE_DATASOURCES` et `WORKFLOW_RUNS`.
  4. La **cascade d'héritage de gouvernance à 4 niveaux** (`GLOBAL ➔ BU ➔ TEAM ➔ WORKSPACE`) et le comportement d'isolation des espaces confidentiels (`CONFIDENTIAL_RESTRICTED` / `INHERITANCE_BLOCK`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact (`0002_story_1_2_auth_org_workspaces_permissions.py`, `architecture.md`, `docs/help/`)** :
  - Intervention purement documentaire (aucun changement de schéma SQL ni de code exécutable UI en cours d'édition par un autre sous-agent).
  - Respect strict de la règle d'étanchéité éditoriale :
    - Dans `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md` (Section 8) et `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/faq-architecture-modele-metier.md` : documentation technique complète (termes internes `OrgUnit`/`Workspace`, DDL PostgreSQL 18, diagramme ER Mermaid, cascade 4 niveaux).
    - Dans `docs/help/fr/spaces-sources.md` et `docs/help/en/spaces-sources.md` : enrichissement de la section `## Questions fréquentes` / `## Frequently asked questions` en langage métier clair pour l'utilisateur final (zéro jargon technique interne conformément aux 3 règles impératives de microcopy `GEMINI.md` et au validateur `HelpArticleDeterministicValidator`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune nouvelle migration requise : documentation exacte des tables `org_units`, `users`, `workspaces`, `workspace_memberships` et `workspace_datasources` définies dans [`0002_story_1_2_auth_org_workspaces_permissions.py`](file:///home/romain/Documents/Projects/ORCIA/infra/migrations/versions/0002_story_1_2_auth_org_workspaces_permissions.py).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- Aucune modification du noyau métier.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Aucune modification des routes API ni du SDK OpenAPI.

### 2.4 Documentation d'Architecture & Aide Utilisateur (`docs/`)
1. **Ajout de la Section `## 8. FAQ Architecture & Modèle Métier (Winston)` dans [`architecture.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md)** :
   - Tableau comparatif des termes internes (`OrgUnit` / `org_units` vs `Workspace` / `workspaces`).
   - Détail des 2 liens relationnels SQL (`owner_org_unit_id` `N ➔ 1` et `workspace_memberships` `N ➔ N`) avec extraits DDL PostgreSQL 18.
   - Diagramme `erDiagram` Mermaid (`ORG_UNITS`, `USERS`, `WORKSPACES`, `WORKSPACE_MEMBERSHIPS`, `WORKSPACE_DATASOURCES`, `WORKFLOW_RUNS`).
   - Explication de la cascade de gouvernance à 4 niveaux (`GLOBAL ➔ BU ➔ TEAM ➔ WORKSPACE`) et du coupe-circuit `CONFIDENTIAL_RESTRICTED` (`INHERITANCE_BLOCK`).
2. **Création du document de référence dédié [`faq-architecture-modele-metier.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/faq-architecture-modele-metier.md)** pour consultation directe.
3. **Enrichissement bilingue des fiches d'aide [`docs/help/fr/spaces-sources.md`](file:///home/romain/Documents/Projects/ORCIA/docs/help/fr/spaces-sources.md) et [`docs/help/en/spaces-sources.md`](file:///home/romain/Documents/Projects/ORCIA/docs/help/en/spaces-sources.md)** sur le lien entre Directions/Équipes et Espaces de Travail.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification) | Description synthétique |
| :--- | :--- | :--- |
| [`docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md) | Modification | Ajout de la **Section 8 — FAQ Architecture & Modèle Métier (Winston)** détaillant les termes internes (`OrgUnit` / `org_units` vs `Workspace` / `workspaces`), les 2 liens relationnels SQL (`owner_org_unit_id` `N ➔ 1` avec `ON DELETE RESTRICT` et `workspace_memberships` `N ➔ N`), le diagramme ER Mermaid complet et la cascade d'héritage à 4 niveaux (`GLOBAL ➔ BU ➔ TEAM ➔ WORKSPACE`). |
| [`docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/faq-architecture-modele-metier.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/faq-architecture-modele-metier.md) | Création | Document de référence autonome « FAQ Architecture & Modèle Métier — ORCIA (Winston) » regroupant le comparatif `OrgUnit` / `Workspace`, les extraits SQL, le diagramme ER Mermaid et les règles d'héritage / isolation `CONFIDENTIAL_RESTRICTED`. |
| [`docs/help/fr/spaces-sources.md`](file:///home/romain/Documents/Projects/ORCIA/docs/help/fr/spaces-sources.md) | Modification | Enrichissement de la rubrique `## Questions fréquentes` (en langage métier sans jargon technique) sur le lien entre une entité de l'organisation (Direction, Équipe) et un Espace de travail. |
| [`docs/help/en/spaces-sources.md`](file:///home/romain/Documents/Projects/ORCIA/docs/help/en/spaces-sources.md) | Modification | Équivalent anglais dans `## Frequently asked questions` expliquant le lien entre *Organization entity (Business Unit, Team)* et *Workspace*. |
| [`docs/implementation-artifacts/tech-lead-reports/2026-11-06-documentation-faq-lien-workspace-org-unit-tech-lead-report.md`](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/tech-lead-reports/2026-11-06-documentation-faq-lien-workspace-org-unit-tech-lead-report.md) | Création | Présent rapport Tech Lead documentant l'intervention. |
| [`docs/implementation-artifacts/tech-lead-reports/README.md`](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/tech-lead-reports/README.md) | Modification | Référencement du rapport Tech Lead dans l'index chronologique. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Tests d'aide contextuelle et de validation documentaire** : `6 passed` (`tests/unit/test_epic_9_story_9_5_contextual_help.py` & `tests/unit/test_epic_11_story_11_5_help_generator_and_validator.py`).
- **Qualité statique & Architecture** :
  - `lint_spine.py` : `ok: true, 0 findings`.
  - Étanchéité éditoriale respectée : détails SQL/DDL/Mermaid dans `architecture.md` et `faq-architecture-modele-metier.md`, langage métier pur dans `docs/help/{fr,en}/spaces-sources.md`.

### 3.3 Validation & Procédure de Test
- **Couche 1 — Tests Unitaires (`pytest`)** : Validation du chargement Git-seeded `docs/help/{fr,en}/spaces-sources.md` par `ContextualHelpResolutionService` et validation déterministe par `HelpArticleDeterministicValidator` (`100 % PASS`).
