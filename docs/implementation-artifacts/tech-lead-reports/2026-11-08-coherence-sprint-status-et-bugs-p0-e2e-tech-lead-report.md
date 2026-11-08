# 2026-11-08 — Cohérence de `sprint-status.yaml` et correction des bugs P0 révélés par les E2E

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-coherence-sprint-status-et-bugs-p0-e2e` (`Epic 13`, tickets `BUG-E2E-01..04`)
- **Capacité(s)** : `CAP-073` (dossiers Assistant), `CAP-023` (ancrages humains / arbitrage), `CAP-040` (notifications / claim temps réel), `CAP-001` (authentification) — classification `feature` (bugfix) + `doc`
- **Branche dédiée** : `fix/p0-e2e-bugs`
- **Statut** : `in-progress`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Incohérences du suivi de sprint (constat du 2026-11-08)
1. `CAP-ACT-5` marqué `done` alors que seules 3 / 57 capacités sont en `verification: runtime`.
2. `TEST-07` marqué `done` alors que la refonte HTTP des fichiers d'intégration historiques (`test_story_9_*`, `10_*`, `11_*`) n'est pas faite.
3. `CAP-ACT-1` et `UX-DS-RADIX-01` rattachés à `epic-12` (terminé) au lieu de `epic-13`.
4. Stories `3.4`, `4.3`, `5.1` en `done` alors que leur surface UI / temps réel n'est pas utilisable (`BUG-E2E-02/03/05`) : à annoter.
5. `last_updated` obsolète.

### 1.2 Bugs P0 (à investiguer dans le code avant plan détaillé)
| Bug | Symptôme | Garde-fou violé |
| :--- | :--- | :--- |
| `BUG-E2E-04` | `resolve_user()` retombe sur la persona `marc` sans jeton ; notifications fictives semées en mémoire | Sécurité (usurpation), zéro donnée fictive |
| `BUG-E2E-01` | Dossiers Assistant non réhydratés depuis PostgreSQL après `F5` | Garde-fou n°3 (survie au F5 via `GET`) |
| `BUG-E2E-02` | `HumanLedAnchorCard` / `ArbitrationTieBreakCard` non montés dans `apps/web` | Garde-fou n°5 / câblage vertical |
| `BUG-E2E-03` | `/api/v1/events/stream` rejoue puis se ferme (pas de SSE persistant) | Règle 2 (zéro faux streaming), FR-2 |

L'étude d'impact détaillée (GitNexus) de chaque bug est consignée en Section 2 au fur et à mesure, avant chaque modification de code.

## 2. Plan d'Implémentation

### 2.0 Étape 0 — Cohérence documentaire
- Corriger `sprint-status.yaml` (statuts, rattachements, annotations, `last_updated`) et la ligne `CAP-ACT-5` / `TEST-07` du rapport `2026-11-08-test-07-a-10-...`.

### 2.1 à 2.4 — Bugs P0
Plan par bug complété ci-dessous après analyse d'impact.

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.0 Étape 0 — Cohérence documentaire (faite)
| Élément | Avant | Après |
| :--- | :--- | :--- |
| `CAP-ACT-5` | `done` | `in-progress` (54/54 capacités live testées, mais 3/57 en `runtime`) |
| `TEST-07` | `done` | `review` (reste : refonte HTTP des fichiers historiques `test_story_9_*`, `10_*`, `11_*`) |
| `CAP-ACT-1`, `UX-DS-RADIX-01` | `epic-12` | `epic-13` |
| Stories `3.4`, `4.3`, `5.1` | `done` sans réserve | `done` + annotation renvoyant vers `BUG-E2E-02/05/03` |
| Story `13.1` | `review` | `review` justifié (attend CAP-ACT-1 / CAP-ACT-5) |
| `last_updated` | 09:30 | 14:40 |

### 3.1 Bugs P0
_En cours — complété après chaque correction._
