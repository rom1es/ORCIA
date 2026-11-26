"""Profile Semantic Translator & Ontology CTE SQL Builder (`Story 2.1`, `Story 26.5`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from typing import Any

from orcia_core.ontology.models import (
    BlackboardSchemaValidationResult,
    ExpandedRagQuery,
    HumanProfileArchetype,
    OntologyConceptEntity,
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
        "   WHEN '4_WORKSPACE' THEN 400"
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
        "     OR (c.level IN ('3_WORKSPACE', '4_WORKSPACE') AND c.scope_id = :workspace_scope_id)"
        "     OR (c.level = '4_RUN_EPHEMERAL' AND c.scope_id = :run_id)"
        "   )"
        ")"
        " SELECT DISTINCT ON (canonical_term) * FROM ranked_concepts"
        " ORDER BY canonical_term, priority_rank DESC;"
    )


def build_workspace_pack_ontology_cte_sql() -> str:
    """Return bounded PG18 CTE evaluating flat `WORKSPACE_PACK` precedence (`R4`, `D6.a`).

    Precedence: `4_RUN_EPHEMERAL -> 3_WORKSPACE (overrides) -> WORKSPACE_PACK
    (ordered by workspace_pack_activations.priority_order ASC) -> 3_TEAM -> 2_DOMAIN
    -> 1_ENTERPRISE -> SYSTEM_PACK`.
    """
    return (
        "WITH RECURSIVE team_ancestry AS ("
        " SELECT id, slug, parent_id, 0 AS depth FROM org_units"
        " WHERE CAST(id AS TEXT) = :team_org_unit_id OR slug = :team_org_unit_id"
        " UNION ALL"
        " SELECT p.id, p.slug, p.parent_id, a.depth + 1 FROM org_units p"
        " INNER JOIN team_ancestry a ON p.id = a.parent_id AND p.unit_type = 'TEAM'"
        "), active_packs AS ("
        " SELECT wpa.pack_bundle_id, wpa.pack_slug, wpa.priority_order"
        " FROM workspace_pack_activations wpa"
        " LEFT JOIN workspaces w ON w.id = wpa.workspace_id"
        " WHERE wpa.is_active = TRUE"
        "   AND (CAST(wpa.workspace_id AS TEXT) = :workspace_scope_id"
        "        OR LOWER(w.slug) = LOWER(:workspace_scope_id))"
        "), ranked_concepts AS ("
        " SELECT c.*, dpb.slug AS pack_slug, dpb.bundle_kind AS pack_bundle_kind,"
        "   CASE"
        "     WHEN c.pack_bundle_id IS NULL AND c.level = '4_RUN_EPHEMERAL' THEN 500000"
        "     WHEN c.pack_bundle_id IS NULL AND c.level IN ('3_WORKSPACE', '4_WORKSPACE')"
        "       THEN 400000"
        "     WHEN ap.pack_bundle_id IS NOT NULL"
        "       THEN 380000 - COALESCE(ap.priority_order, 9999)"
        "     WHEN c.pack_bundle_id IS NULL AND c.level = '3_TEAM'"
        "       THEN 350000 - COALESCE(ta.depth, 0)"
        "     WHEN c.pack_bundle_id IS NULL AND c.level = '2_DOMAIN' THEN 200000"
        "     WHEN c.pack_bundle_id IS NULL AND c.level = '1_ENTERPRISE' THEN 100000"
        "     WHEN dpb.bundle_kind = 'SYSTEM' AND dpb.status = 'PUBLISHED' THEN 50000"
        "     ELSE 0 END AS priority_rank"
        " FROM ontology_concepts c"
        " LEFT JOIN declarative_pack_bundles dpb ON dpb.id = c.pack_bundle_id"
        " LEFT JOIN active_packs ap ON ap.pack_bundle_id = c.pack_bundle_id"
        " LEFT JOIN team_ancestry ta ON c.pack_bundle_id IS NULL AND c.level = '3_TEAM'"
        "   AND (c.scope_id = CAST(ta.id AS TEXT) OR c.scope_id = ta.slug)"
        " WHERE c.snapshot_branch_status = 'ACTIVE'"
        "   AND ("
        "     ap.pack_bundle_id IS NOT NULL"
        "     OR (c.pack_bundle_id IS NOT NULL AND dpb.bundle_kind = 'SYSTEM'"
        "         AND dpb.status = 'PUBLISHED')"
        "     OR (c.pack_bundle_id IS NULL AND ("
        "       (c.level = '1_ENTERPRISE' AND c.scope_id = :enterprise_scope_id)"
        "       OR (c.level = '2_DOMAIN' AND c.scope_id = :domain_scope_id)"
        "       OR (c.level = '3_TEAM' AND (ta.id IS NOT NULL OR c.scope_id = :team_org_unit_id))"
        "       OR (c.level IN ('3_WORKSPACE', '4_WORKSPACE') AND c.scope_id = :workspace_scope_id)"
        "       OR (c.level = '4_RUN_EPHEMERAL' AND c.scope_id = :run_id)"
        "     ))"
        "   )"
        ")"
        " SELECT DISTINCT ON (canonical_term) * FROM ranked_concepts"
        " ORDER BY canonical_term, priority_rank DESC;"
    )


class ProfileSemanticTranslator:
    """Plan 2 of Triple Active Execution: translates concepts per Human Profile archetype."""

    _ARCHETYPE_ALIASES: dict[str, str] = {
        "PM": "PM_BUSINESS",
        "PM_BUSINESS": "PM",
    }

    @classmethod
    def translate_concept(
        cls, concept: OntologyConceptEntity, archetype: HumanProfileArchetype | str
    ) -> str:
        norm = str(archetype or "").strip().upper()
        custom = concept.profile_translations.get(norm)
        if not custom and norm in cls._ARCHETYPE_ALIASES:
            custom = concept.profile_translations.get(cls._ARCHETYPE_ALIASES[norm])
        if custom:
            return custom
        return f"{concept.canonical_term} — {concept.definition_text}"


def validate_blackboard_artifact_schema(
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


def expand_rag_query_terms(raw_query: str, snapshot: ResolvedOntologySnapshot) -> ExpandedRagQuery:
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


__all__ = [
    "ProfileSemanticTranslator",
    "build_ontology_resolution_cte_sql",
    "build_workspace_pack_ontology_cte_sql",
    "expand_rag_query_terms",
    "validate_blackboard_artifact_schema",
]
