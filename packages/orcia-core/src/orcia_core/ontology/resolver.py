"""OntologyHierarchyResolver, CTE SQL builder, and Triple Active Execution (Story 2.1, AD-7).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from typing import Any

from orcia_core.ontology.errors import OntologyConflictError
from orcia_core.ontology.models import (
    ONTOLOGY_LEVEL_PRIORITY,
    BlackboardSchemaValidationResult,
    ExpandedRagQuery,
    HumanProfileArchetype,
    OntologyAxiomEntity,
    OntologyConceptEntity,
    OntologyRelationEntity,
    ResolvedOntologySnapshot,
)


def build_ontology_resolution_cte_sql() -> str:
    """Return the PostgreSQL 18 recursive CTE query merging 4 ontology levels by priority.

    Priority order: `4_RUN_EPHEMERAL (ACTIVE) -> 3_WORKSPACE -> 3_TEAM [Sub-Team -> Parent Team]
    -> 2_DOMAIN -> 1_ENTERPRISE` (`< 15 ms`, `AD-7`, `NFR-PERF-3`).
    """
    return (
        "WITH RECURSIVE team_ancestry AS ("
        " SELECT id, slug, parent_id, 0 AS depth FROM org_units"
        " WHERE CAST(id AS TEXT) = :team_org_unit_id OR slug = :team_org_unit_id"
        " UNION ALL"
        " SELECT p.id, p.slug, p.parent_id, a.depth + 1 FROM org_units p"
        " INNER JOIN team_ancestry a ON p.id = a.parent_id AND p.unit_type = 'TEAM'"
        "), ranked_concepts AS ("
        " SELECT c.*, CASE c.level"
        "   WHEN '4_RUN_EPHEMERAL' THEN 500"
        "   WHEN '3_WORKSPACE' THEN 400"
        "   WHEN '3_TEAM' THEN 350 - COALESCE(ta.depth, 0)"
        "   WHEN '2_DOMAIN' THEN 200"
        "   WHEN '1_ENTERPRISE' THEN 100"
        "   ELSE 0 END AS priority_rank"
        " FROM ontology_concepts c"
        " LEFT JOIN team_ancestry ta ON c.level = '3_TEAM'"
        "   AND (c.scope_id = CAST(ta.id AS TEXT) OR c.scope_id = ta.slug)"
        " WHERE c.snapshot_branch_status = 'ACTIVE'"
        "   AND ("
        "     (c.level = '1_ENTERPRISE' AND c.scope_id = :enterprise_scope_id)"
        "     OR (c.level = '2_DOMAIN' AND c.scope_id = :domain_scope_id)"
        "     OR (c.level = '3_TEAM' AND (ta.id IS NOT NULL OR c.scope_id = :team_org_unit_id))"
        "     OR (c.level = '3_WORKSPACE' AND c.scope_id = :workspace_scope_id)"
        "     OR (c.level = '4_RUN_EPHEMERAL' AND c.scope_id = :run_id)"
        "   )"
        ")"
        " SELECT DISTINCT ON (canonical_term) * FROM ranked_concepts"
        " ORDER BY canonical_term, priority_rank DESC;"
    )


class ProfileSemanticTranslator:
    """Plan 2 of Triple Active Execution: translates concepts per Human Profile archetype."""

    @staticmethod
    def translate_concept(
        concept: OntologyConceptEntity, archetype: HumanProfileArchetype | str
    ) -> str:
        custom = concept.profile_translations.get(archetype)
        if custom:
            return custom
        return f"{concept.canonical_term} — {concept.definition_text}"


class OntologyHierarchyResolver:
    """Resolves the 4-level Ontology hierarchy and executes all 3 active ontology planes."""

    @staticmethod
    def _candidate_rank(
        concept: OntologyConceptEntity,
        *,
        enterprise_scope_id: str,
        domain_scope_id: str,
        team_chain_scope_ids: tuple[str, ...],
        workspace_scope_id: str,
        run_scope_id: str | None,
    ) -> int | None:
        if concept.snapshot_branch_status != "ACTIVE":
            return None
        if concept.level == "1_ENTERPRISE" and concept.scope_id == enterprise_scope_id:
            return 100
        if concept.level == "2_DOMAIN" and concept.scope_id == domain_scope_id:
            return 200
        if concept.level == "3_TEAM" and concept.scope_id in team_chain_scope_ids:
            # team_chain_scope_ids is ordered from Sub-Team (index 0, highest priority) to Parent
            idx = team_chain_scope_ids.index(concept.scope_id)
            return 350 - idx
        if concept.level == "3_WORKSPACE" and concept.scope_id == workspace_scope_id:
            return 400
        if (
            concept.level == "4_RUN_EPHEMERAL"
            and run_scope_id is not None
            and concept.scope_id == run_scope_id
        ):
            return 500
        return None

    @classmethod
    def resolve_effective_ontology(
        cls,
        *,
        concepts: tuple[OntologyConceptEntity, ...],
        relations: tuple[OntologyRelationEntity, ...],
        axioms: tuple[OntologyAxiomEntity, ...],
        enterprise_scope_id: str,
        domain_scope_id: str,
        team_chain_scope_ids: tuple[str, ...],
        workspace_scope_id: str,
        run_scope_id: str | None = None,
    ) -> ResolvedOntologySnapshot:
        """Resolve merged ontology across L1 -> L2 -> L3_TEAM -> L3_WORKSPACE -> L4_RUN."""
        immutable_axioms_by_term: dict[
            str, list[tuple[OntologyAxiomEntity, OntologyConceptEntity]]
        ] = {}
        immutable_axioms_by_id: dict[
            str, list[tuple[OntologyAxiomEntity, OntologyConceptEntity]]
        ] = {}
        concept_by_key: dict[str, OntologyConceptEntity] = {c.concept_key: c for c in concepts}
        concept_by_id: dict[str, OntologyConceptEntity] = {c.id: c for c in concepts}

        for ax in axioms:
            if ax.immutable:
                target_concept = concept_by_key.get(ax.concept_key)
                if target_concept is not None:
                    immutable_axioms_by_term.setdefault(target_concept.canonical_term, []).append(
                        (ax, target_concept)
                    )
                    immutable_axioms_by_id.setdefault(target_concept.id, []).append(
                        (ax, target_concept)
                    )

        applicable: list[tuple[int, OntologyConceptEntity]] = []
        for concept in concepts:
            rank = cls._candidate_rank(
                concept,
                enterprise_scope_id=enterprise_scope_id,
                domain_scope_id=domain_scope_id,
                team_chain_scope_ids=team_chain_scope_ids,
                workspace_scope_id=workspace_scope_id,
                run_scope_id=run_scope_id,
            )
            if rank is not None:
                applicable.append((rank, concept))

        applicable.sort(key=lambda item: item[0])
        merged_by_term: dict[str, OntologyConceptEntity] = {}
        merged_synonyms_by_term: dict[str, list[str]] = {}
        merged_banned_by_term: dict[str, list[str]] = {}
        merged_translations_by_term: dict[str, dict[str, str]] = {}
        merged_schema_by_term: dict[str, dict[str, str]] = {}

        for cand_rank, candidate in applicable:
            term = candidate.canonical_term
            applicable_imm: list[tuple[OntologyAxiomEntity, OntologyConceptEntity]] = list(
                immutable_axioms_by_term.get(term, [])
            )
            parent_cursor = candidate.parent_concept_id
            visited_parents: set[str] = set()
            while parent_cursor and parent_cursor not in visited_parents:
                visited_parents.add(parent_cursor)
                for pair in immutable_axioms_by_id.get(parent_cursor, []):
                    if pair not in applicable_imm:
                        applicable_imm.append(pair)
                parent_obj = concept_by_id.get(parent_cursor)
                parent_cursor = parent_obj.parent_concept_id if parent_obj else None

            for imm_ax, ax_concept in applicable_imm:
                ax_rank = cls._candidate_rank(
                    ax_concept,
                    enterprise_scope_id=enterprise_scope_id,
                    domain_scope_id=domain_scope_id,
                    team_chain_scope_ids=team_chain_scope_ids,
                    workspace_scope_id=workspace_scope_id,
                    run_scope_id=run_scope_id,
                )
                if ax_rank is None:
                    ax_rank = ONTOLOGY_LEVEL_PRIORITY[imm_ax.level] * 100
                if cand_rank > ax_rank:
                    # Check if specialization contradicts an immutable parent schema or rule
                    existing = dict(ax_concept.expected_schema)
                    existing.update(merged_schema_by_term.get(term, {}))
                    for field_name, expected_type in existing.items():
                        cand_type = candidate.expected_schema.get(field_name)
                        if cand_type is not None and cand_type != expected_type:
                            raise OntologyConflictError(
                                detail_override=(
                                    f"ONTOLOGY_CONFLICT: Concept '{term}' at {candidate.level} "
                                    f"violates immutable parent axiom '{imm_ax.axiom_key}' on "
                                    f"field '{field_name}' ({cand_type} != {expected_type})."
                                )
                            )
                    if "FORBID_OVERRIDE_DEFINITION" in imm_ax.rule_expression and (
                        candidate.definition_text != ax_concept.definition_text
                    ):
                        raise OntologyConflictError(
                            detail_override=(
                                f"ONTOLOGY_CONFLICT: Concept '{term}' at {candidate.level} "
                                f"cannot override immutable definition from '{imm_ax.axiom_key}'."
                            )
                        )

            syns = merged_synonyms_by_term.setdefault(term, [])
            for s in candidate.synonyms:
                if s not in syns:
                    syns.append(s)

            banned = merged_banned_by_term.setdefault(term, [])
            for b in candidate.banned_terms:
                if b not in banned:
                    banned.append(b)

            trans = dict(merged_translations_by_term.get(term, {}))
            trans.update(candidate.profile_translations)
            merged_translations_by_term[term] = trans

            schema = dict(merged_schema_by_term.get(term, {}))
            schema.update(candidate.expected_schema)
            merged_schema_by_term[term] = schema

            merged_by_term[term] = OntologyConceptEntity(
                id=candidate.id,
                concept_key=candidate.concept_key,
                canonical_term=term,
                level=candidate.level,
                scope_id=candidate.scope_id,
                definition_text=candidate.definition_text,
                parent_concept_id=candidate.parent_concept_id,
                synonyms=tuple(syns),
                banned_terms=tuple(banned),
                profile_translations=trans,
                expected_schema=schema,
                introduced_in_snapshot_id=candidate.introduced_in_snapshot_id,
                snapshot_branch_status=candidate.snapshot_branch_status,
            )

        active_keys = {c.concept_key for c in merged_by_term.values()}
        active_relations = tuple(
            r
            for r in relations
            if r.source_concept_key in active_keys or r.target_concept_key in active_keys
        )
        active_axioms = tuple(a for a in axioms if a.concept_key in active_keys)
        chain = (
            *((run_scope_id,) if run_scope_id else ()),
            workspace_scope_id,
            *team_chain_scope_ids,
            domain_scope_id,
            enterprise_scope_id,
        )
        return ResolvedOntologySnapshot(
            workspace_id=workspace_scope_id,
            run_id=run_scope_id,
            concepts_by_term=merged_by_term,
            relations=active_relations,
            axioms=active_axioms,
            resolution_chain_scopes=chain,
        )

    @staticmethod
    def validate_blackboard_artifact(
        *,
        canonical_term: str,
        payload: dict[str, Any],
        snapshot: ResolvedOntologySnapshot,
    ) -> BlackboardSchemaValidationResult:
        """Plan 1 of Triple Active Execution: validate Blackboard/Template payload schema."""
        concept = snapshot.concepts_by_term.get(canonical_term)
        if concept is None:
            return BlackboardSchemaValidationResult(
                valid=False,
                checked_concept_key=canonical_term,
                missing_fields=(canonical_term,),
            )

        missing: list[str] = []
        mismatches: list[str] = []
        card_violations: list[str] = []

        for field_name, expected_type in concept.expected_schema.items():
            if field_name not in payload:
                missing.append(field_name)
                continue
            val = payload[field_name]
            if expected_type == "str" and not isinstance(val, str):
                mismatches.append(f"{field_name}: expected str")
            elif expected_type == "int" and (not isinstance(val, int) or isinstance(val, bool)):
                mismatches.append(f"{field_name}: expected int")
            elif expected_type == "non_empty_list" and (not isinstance(val, list) or len(val) == 0):
                card_violations.append(f"{field_name}: expected 1..N non-empty list")

        valid = not missing and not mismatches and not card_violations
        return BlackboardSchemaValidationResult(
            valid=valid,
            checked_concept_key=concept.concept_key,
            missing_fields=tuple(missing),
            type_mismatches=tuple(mismatches),
            cardinality_violations=tuple(card_violations),
        )

    @staticmethod
    def expand_rag_query(raw_query: str, snapshot: ResolvedOntologySnapshot) -> ExpandedRagQuery:
        """Plan 3 of Triple Active Execution: expand RAG query with synonyms & related concepts."""
        lowered = raw_query.lower()
        expanded: list[str] = []
        matched_keys: list[str] = []
        banned_found: list[str] = []

        concepts_by_key = {c.concept_key: c for c in snapshot.concepts_by_term.values()}

        for concept in snapshot.concepts_by_term.values():
            term_hit = concept.canonical_term.lower() in lowered or any(
                syn.lower() in lowered for syn in concept.synonyms
            )
            if term_hit:
                matched_keys.append(concept.concept_key)
                if concept.canonical_term not in expanded:
                    expanded.append(concept.canonical_term)
                for syn in concept.synonyms:
                    if syn not in expanded:
                        expanded.append(syn)
            for banned in concept.banned_terms:
                if banned.lower() in lowered and banned not in banned_found:
                    banned_found.append(banned)

        for rel in snapshot.relations:
            if rel.source_concept_key in matched_keys:
                target = concepts_by_key.get(rel.target_concept_key)
                if target and target.canonical_term not in expanded:
                    expanded.append(target.canonical_term)

        return ExpandedRagQuery(
            original_query=raw_query,
            expanded_terms=tuple(expanded),
            matched_concept_keys=tuple(matched_keys),
            detected_banned_terms=tuple(banned_found),
        )
