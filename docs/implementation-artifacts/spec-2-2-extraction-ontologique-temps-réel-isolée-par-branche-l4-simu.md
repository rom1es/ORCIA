---
title: 'Story 2.2: Extraction Ontologique Temps Réel Isolée par Branche (L4), Simulateur What-If & Promotion Gouvernée'
type: 'feature'
created: '2026-10-25'
status: 'done'
route: 'dispatch'
baseline_commit: 'd0230a1e8f92e15a7822e4f0e12d4a50b18c0e11' # pragma: allowlist secret
review_loop_iteration: 1
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/implementation-artifacts/epic-2-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Lorsqu'un *Replay* ramène un Workflow Run à une étape antérieure, les concepts `4_RUN_EPHEMERAL` découverts dans la branche abandonnée ne doivent jamais polluer les nouveaux Runs ni être promus. De plus, avant toute modification ou promotion d'un terme (`L4 -> L3 -> L2 -> L1`), le responsable doit visualiser son impact *What-If* sur les concepts liés, les *Artifact Templates*, les *Workflows* et les *Runs* actifs.

**Approach:** Créer la révision Alembic `0007_story_2_2_l4_extraction_and_promotions.py` (`ontology_promotion_proposals`), implémenter `ImpactSimulatorService` (parcours BFS sur `ontology_relations` + liaisons Templates/Workflows/Runs + détection de conflit d'axiome immuable) et `OntologyGovernanceService` (`extract_l4_concept`, `mark_snapshot_branch_superseded`, `promote_concept` avec contrôle RBAC par niveau cible et rejet des propositions non-`PENDING_REVIEW` ou `SUPERSEDED`), et intégrer le tiroir *What-If* et l'action de promotion dans `OntologyAndKbExplorerPanel` (`@orcia/ui`).

## Boundaries & Constraints

**Always:**
- Rattacher chaque concept `4_RUN_EPHEMERAL` à `introduced_in_snapshot_id` et marquer `snapshot_branch_status = "SUPERSEDED"` dès que la branche de snapshot est invalidée par un *Replay*.
- Vérifier dans `promote_concept` que la proposition est `PENDING_REVIEW`, que le concept source n'est pas `SUPERSEDED`, qu'aucun axiome immuable amont n'est violé, et que l'approbateur possède le rôle requis (`PLATFORM_ADMIN` pour `1_ENTERPRISE`, `TEAM_LEAD` ou `PLATFORM_ADMIN` pour `2_DOMAIN`/`3_TEAM`/`3_WORKSPACE`).

**Never:**
- Ne jamais promouvoir un concept issu d'une branche `SUPERSEDED` ni permettre une double promotion d'une proposition déjà `APPROVED` (`HTTP 422 ERR_ONTOLOGY_CONFLICT`).

</frozen-after-approval>

## Code Map

- `infra/migrations/versions/0007_story_2_2_l4_extraction_and_promotions.py` — Table `ontology_promotion_proposals`.
- `packages/orcia-core/src/orcia_core/ontology/impact_and_promotion.py` — `ImpactSimulatorService` & `OntologyGovernanceService`.
- `apps/api/src/orcia_api/routers/ontology_and_rag.py` — Endpoints `/api/v1/ontology-rag/ontology/what-if` et `/ontology/promote`.
- `packages/ui/src/shell/OntologyAndKbExplorerPanel.tsx` — Boutons `what-if-btn-*`, `promote-btn-*` et tiroir `what-if-impact-drawer`.
- `tests/unit/test_ontology_and_what_if.py` — Tests d'isolation L4 (`SUPERSEDED`), What-If et promotion gouvernée.
