"""Graph traversal What-If impact simulator for ontology concepts."""

from __future__ import annotations

from orcia_core.ontology.errors import ResourceNotFoundError
from orcia_core.ontology.models import (
    ONTOLOGY_LEVEL_PRIORITY,
    OntologyAxiomEntity,
    OntologyConceptEntity,
    OntologyRelationEntity,
    WhatIfImpactReport,
)


class ImpactSimulatorService:
    """Graph traversal What-If impact simulator over relations, templates, workflows, and runs."""

    @staticmethod
    def simulate_what_if(
        *,
        concept_key: str,
        proposed_change: str,
        concepts: tuple[OntologyConceptEntity, ...],
        relations: tuple[OntologyRelationEntity, ...],
        axioms: tuple[OntologyAxiomEntity, ...],
        template_bindings: dict[str, tuple[str, ...]],
        workflow_bindings: dict[str, tuple[str, ...]],
        active_run_bindings: dict[str, tuple[str, ...]],
        violates_immutable_axiom: bool = False,
    ) -> WhatIfImpactReport:
        concept = next((c for c in concepts if c.concept_key == concept_key), None)
        if concept is None:
            raise ResourceNotFoundError(detail_override=f"Concept '{concept_key}' not found.")

        visited: list[str] = [concept_key]
        frontier: list[str] = [concept_key]
        while frontier:
            curr = frontier.pop(0)
            for rel in relations:
                if rel.source_concept_key == curr and rel.target_concept_key not in visited:
                    visited.append(rel.target_concept_key)
                    frontier.append(rel.target_concept_key)

        transitively_affected = tuple(k for k in visited if k != concept_key)
        affected_set = set(visited)

        impacted_templates = tuple(
            tpl
            for tpl, bound_keys in sorted(template_bindings.items())
            if affected_set.intersection(bound_keys)
        )
        impacted_workflows = tuple(
            wf
            for wf, bound_keys in sorted(workflow_bindings.items())
            if affected_set.intersection(bound_keys)
        )
        impacted_runs = tuple(
            run_id
            for run_id, bound_keys in sorted(active_run_bindings.items())
            if affected_set.intersection(bound_keys)
        )

        concept_by_id = {c.id: c for c in concepts}
        concept_by_key = {c.concept_key: c for c in concepts}
        ancestor_keys: set[str] = {concept_key}
        cursor_id = concept.parent_concept_id
        while cursor_id and cursor_id in concept_by_id:
            parent_c = concept_by_id[cursor_id]
            if parent_c.concept_key in ancestor_keys:
                break
            ancestor_keys.add(parent_c.concept_key)
            cursor_id = parent_c.parent_concept_id

        for other_c in concepts:
            if other_c.canonical_term == concept.canonical_term and (
                ONTOLOGY_LEVEL_PRIORITY[other_c.level] <= ONTOLOGY_LEVEL_PRIORITY[concept.level]
            ):
                ancestor_keys.add(other_c.concept_key)

        has_immutable = violates_immutable_axiom or any(
            ax.immutable and ax.concept_key in ancestor_keys and ax.concept_key in concept_by_key
            for ax in axioms
        )
        return WhatIfImpactReport(
            concept_key=concept_key,
            canonical_term=concept.canonical_term,
            proposed_change=proposed_change,
            transitively_affected_concepts=transitively_affected,
            impacted_artifact_templates=impacted_templates,
            impacted_workflow_uris=impacted_workflows,
            impacted_active_run_ids=impacted_runs,
            has_immutable_axiom_conflict=has_immutable,
        )


__all__ = ["ImpactSimulatorService"]
