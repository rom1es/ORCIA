# Prompt BMAD : corriger l'ordonnancement après l'intégration de la stack et de la modularité

> **Skill principal : `bmad-correct-course`.** C'est un ajustement du plan existant (proposition de changement de sprint du 27/10, epics, sprint-status).
> Il est suivi de `bmad-architecture` en mode *update* (nettoyage de la spine) et de `bmad-sprint-planning` en mode *validate/fix* (cohérence du suivi).
> Les étapes sont séquentielles. Je valide à chaque pause.

---

## Contexte et documents d'entrée
- Proposition à amender : `docs/planning-artifacts/sprint-change-proposal-2026-10-27.md`
- Epics : `docs/planning-artifacts/epics.md` (stories `3.2a`, `3.2b`, `3.2c`, `3.2d`, `4.1a`)
- Suivi : `docs/implementation-artifacts/sprint-status.yaml` (`action_items` `ARCH-*`)
- Spine : `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md`
- Analyses de référence : `docs/planning-artifacts/research/stack-review-2026-10-27.md`, `docs/planning-artifacts/research/modularity-analysis-2026-10-27.md`
- Règles : `AGENTS.md` (ne jamais modifier une story `done`, GitNexus limité à `repo: "ORCIA"`, commandes Python via `.venv/bin/`)

Langue : **français**.

### Décisions déjà prises (ne pas les rouvrir)
- **Q2 = 2A** : table outbox `domain_events_outbox` **indépendante du moteur d'orchestration**. Le relais peut être fait avec Dramatiq ou avec DBOS.
- **Q5 = pas de Rust au MVP**, seulement l'`action_item` `ARCH-RUST-DEFERRED` (P3).
- Q1 = 1A (4 packages `uv`), Q3 = 3A (plugins `entry_points` dans le processus, MCP hors processus), Q4 = 4A (un seul schéma `public`).

---

## Étape 1 : `bmad-correct-course`, amendement de la proposition
Analyser et corriger les **8 écarts** suivants, puis produire un **avenant** dans la proposition de changement de sprint (section « Avenant A1 — 27/10/2026 »).

| # | Écart constaté | Correction attendue |
|---|---|---|
| **C1** | Le spike DBOS (`ARCH-P2`) est inclus dans `3.2b`, avec P1, P6, P7 et P9. La story est surchargée (5 `action_items`, adaptateurs SQLAlchemy de 8 domaines, DBOS, SeaweedFS, BM25, OpenTelemetry). | Créer une **story de spike `3.2s`** (ou un `action_item` `ARCH-P2-SPIKE`), **limitée à 2 ou 3 jours**, **sans dépendance**, à mener **en parallèle de `3.2a`**. Critères de sortie : pause et reprise après crash (`DBOS.recv`), `fork_workflow` pour la relance à partir d'une étape, `@DBOS.scheduled`, `SetWorkflowID` (pas de doublon), cohabitation avec le Blackboard en ajout seul et avec Dramatiq, intégration avec la Unit of Work SQLAlchemy, et testabilité avec testcontainers. Livrable : rapport go / no-go. `3.2b` conserve **l'intégration** de DBOS seulement si le verdict est go. |
| **C2** | La dépendance est inversée : `ARCH-P2.depends_on = [ARCH-P1]`. | `ARCH-P1.depends_on` inclut `ARCH-P2-SPIKE`. **Raison** : avec DBOS, ce sont ses transactions (`@DBOS.transaction`) qui gèrent les sessions SQLAlchemy. Les accès à la base doivent donc être conçus *après* la validation de DBOS. |
| **C3** | L'outbox dépend de DBOS : `ARCH-M6.depends_on = [ARCH-P1, ARCH-P2]`. | `ARCH-M6.depends_on = [ARCH-P1]` seulement. Le relais passe par un port `OutboxRelayPort`, avec deux implémentations possibles (Dramatiq ou workflow DBOS planifié). Mettre à jour `3.2c` en conséquence. |
| **C4** | Le moteur maison de la story `3.2` (`done`) sera remplacé par DBOS sans que ce soit écrit. | Ajouter dans **`3.2b`** (pas dans `3.2`) un critère d'acceptation : « les tests de la story 3.2 sont conservés comme tests de non-régression et restent verts ; le code du moteur maison remplacé est supprimé (0 code mort) ; le rapport Tech Lead de `3.2b` documente ce remplacement ». |
| **C5** | `ARCH-M10` ne correspond pas à M10 de l'analyse : M10 = **profils activables `lite`, `standard`, `full`**, alors que l'item parle d'extraire des packages. | Renommer l'item actuel en **`ARCH-M2-EXTRACT`** (extraction progressive de packages, P3, après le MVP). Créer **`ARCH-M10`** « Profils de déploiement `lite`, `standard`, `full` (modules activables, manifeste exposé par `/api/v1/shell`) », P3, après le MVP. |
| **C6** | `ARCH-01` et `ARCH-P1` font la même chose (adaptateurs SQLAlchemy). | Fusionner `ARCH-01` dans `ARCH-P1`, puis supprimer `ARCH-01` et mettre à jour toutes les références (`depends_on`, `story_ref`, epics). |
| **C7** | Enchaînement strictement séquentiel `3.2a → 3.2b → 3.2c → 3.2d`. | `3.2d` (front Vite) dépend seulement de `ARCH-P3` et `ARCH-M3`, donc de `3.2a`, et avance **en parallèle** de `3.2b` et `3.2c`. Vérifier que `3.3` dépend bien de `3.2c` **et** de `3.2d`. |
| **C8** | Résidus Rust dans la spine, contraires à Q5 : L57 `permissions (RBAC/Cedar Port…)` et L67 `T1: Wasmtime/Rust`. | À traiter à l'étape 2. |

**Ordre cible :**
```
3.2a (socle modulaire) ─┬─> 3.2b (persistance réelle et OpenTelemetry) ─> 3.2c (outbox et plugins) ─┐
3.2s (spike DBOS) ──────┘                                                                           ├─> 3.3 et suite
3.2a ─────────────────────> 3.2d (front Vite, en parallèle) ────────────────────────────────────────┘
```

Également :
- Réévaluer `ARCH-P5.depends_on` (inclut actuellement `ARCH-M6`). Le garder seulement si la sandbox publie des événements `GateEvaluated` par l'outbox, sinon le retirer. Justifier le choix.
- Lancer `gitnexus_impact` (`direction: upstream`) sur `orchestration/engine.py` pour documenter le périmètre remplacé par DBOS (C4), et signaler tout risque HIGH ou CRITICAL.

**Livrable** : l'avenant A1 dans la proposition (tableau des 8 corrections, nouvel ordre, risques et effort).

⏸️ **Pause : je valide l'avenant.**

---

## Étape 2 : `bmad-architecture`, mode *update* (nettoyage de la spine)
- **L57** : `permissions (RBAC/Cedar Port, …)` devient `permissions (RBAC/ABAC Port, seeds.py & Permission Broker)`.
- **L67** : `T1: Wasmtime/Rust < 5s` devient `T1: wasmtime-py < 5s`.
- Vérifier qu'aucune autre mention de Rust, Cedar, `cargo` ou `pyo3` ne subsiste **en dehors** de la section des éléments reportés (L445) et de `ARCH-RUST-DEFERRED`.
- Ajouter dans AD-2, AD-13 ou AD-18 la mention « intégration DBOS conditionnée au verdict du spike `3.2s` » et, dans AD-19 ou AD-12, « l'outbox est indépendante du moteur (port `OutboxRelayPort`) ».
- Lint obligatoire, **0 finding** :
  `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`

---

## Étape 3 : application dans `epics.md` et `sprint-status.yaml`
- `epics.md` :
  - ajouter **Story 3.2s** (récit, critères de sortie go / no-go, limite de temps) ;
  - mettre à jour **3.2b** (C1, C2, C4), **3.2c** (C3), **3.2d** (C7) et les dépendances de **3.3** ;
  - **ne pas modifier** les stories `done` (`3.1`, `3.2`).
- `sprint-status.yaml` :
  - ajouter `3-2s-…` dans `development_status` (`ready-for-dev`, juste après `3-2a`) ;
  - corriger `ARCH-P1`, `ARCH-P2` (devenu intégration, `depends_on: [ARCH-P2-SPIKE]`), `ARCH-M6` et `ARCH-P5` ;
  - fusionner `ARCH-01` dans `ARCH-P1` ;
  - renommer l'ancien M10 en `ARCH-M2-EXTRACT` et créer le nouveau `ARCH-M10` ;
  - mettre à jour `last_updated`.

---

## Étape 4 : `bmad-sprint-planning`, mode *validate/fix*
- Valider `sprint-status.yaml` : syntaxe YAML, statuts autorisés, chaque story présente dans `epics.md` et inversement, `story_ref` qui existent, **aucun cycle dans les `depends_on`**, aucun `action_item` orphelin.

---

## Étape 5 : vérification finale (obligatoire, recommencer jusqu'à obtenir CONFORME)
Lancer `bmad-review` (lentilles *verification gaps* et *structure*) sur le diff des étapes 1 à 4, puis produire ce tableau dans la proposition (section « Vérification Avenant A1 ») :

| ID | Correction | Fait (oui/non) | Preuve (fichier:ligne ou sortie de commande) |
|---|---|---|---|
| C1 | Story `3.2s` créée, limitée dans le temps, sans dépendance, critères go / no-go | | |
| C2 | `ARCH-P1.depends_on` ∋ `ARCH-P2-SPIKE` ; `ARCH-P2.depends_on` ∌ `ARCH-P1` | | |
| C3 | `ARCH-M6.depends_on == [ARCH-P1]` ; `OutboxRelayPort` présent dans `3.2c` | | |
| C4 | Critère de non-régression et de remplacement du moteur de la story 3.2 dans `3.2b` ; story `3.2` inchangée | | |
| C5 | `ARCH-M2-EXTRACT` et `ARCH-M10` (profils) présents et distincts | | |
| C6 | `ARCH-01` absent ; 0 référence restante (`grep -rn "ARCH-01" docs/`) | | |
| C7 | `3.2d` dépend seulement de `3.2a` ; `3.3` dépend de `3.2c` et `3.2d` | | |
| C8 | `grep -niE "rust\|cedar\|cargo\|pyo3" ARCHITECTURE-SPINE.md` ne remonte que la section des éléments reportés | | |
| Q2 | Aucune dépendance de l'outbox vers DBOS | | |
| Q5 | Rust présent seulement dans `ARCH-RUST-DEFERRED` et dans la section des éléments reportés de la spine | | |

**Contrôles automatiques à exécuter et à rapporter :**
- [ ] `lint_spine.py`, 0 finding (sortie collée)
- [ ] Validation `bmad-sprint-planning` OK (sortie collée)
- [ ] `git diff --stat` : seuls la proposition, `epics.md`, `sprint-status.yaml` et `ARCHITECTURE-SPINE.md` sont modifiés
- [ ] `git diff` sur les sections des stories `3.1` et `3.2` : **0 ligne modifiée**
- [ ] Aucun cycle de `depends_on` (script ou vérification manuelle détaillée)

**Résultat attendu** : un verdict **CONFORME / NON CONFORME**, la liste des fichiers modifiés et la prochaine action (lancer `3.2a` et `3.2s` en parallèle via `bmad-build`).
