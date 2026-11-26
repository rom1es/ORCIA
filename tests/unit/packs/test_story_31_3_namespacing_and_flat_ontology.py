"""Unit tests for Story 31.3: Qualified Pack Namespacing & Flat Ontology (`<= 300 L`)."""

from __future__ import annotations

import pytest

from orcia_core.catalog.cas_resolver import parse_federated_uri
from orcia_core.ontology.models import (
    OntologyAxiomEntity,
    OntologyConceptEntity,
    OntologyRelationEntity,
)
from orcia_core.ontology.resolver import (
    OntologyHierarchyResolver,
    build_workspace_pack_ontology_cte_sql,
)
from orcia_core.packs.namespacing import (
    PackEntityCollisionError,
    WorkspaceEntityCandidate,
    format_agent_mention,
    format_pack_resource_uri,
    format_skill_command,
    parse_qualified_entity_ref,
    resolve_workspace_entity_candidates,
)
from orcia_kernel.errors import ResourceNotFoundError, ValidationDomainError


def test_parse_qualified_entity_ref_canonical_and_aliases() -> None:
    p1 = parse_qualified_entity_ref("@sdlc/reviewer")
    assert (p1.pack_slug, p1.entity_slug, p1.kind, p1.is_qualified) == (
        "sdlc",
        "reviewer",
        "agents",
        True,
    )
    assert p1.mention_handle == "@sdlc/reviewer"

    p2 = parse_qualified_entity_ref("/legal-audit/compliance-check")
    assert (p2.pack_slug, p2.entity_slug, p2.kind, p2.is_qualified) == (
        "legal-audit",
        "compliance-check",
        "skills",
        True,
    )
    assert p2.command_handle == "/legal-audit/compliance-check"

    p3 = parse_qualified_entity_ref("sdlc:reviewer")
    assert (p3.pack_slug, p3.entity_slug, p3.is_qualified, p3.canonical_id) == (
        "sdlc",
        "reviewer",
        True,
        "sdlc:reviewer",
    )

    p4 = parse_qualified_entity_ref("orcia://packs/sdlc/agents/reviewer@1.2.0")
    assert (p4.pack_slug, p4.kind, p4.entity_slug, p4.version_ref) == (
        "sdlc",
        "agents",
        "reviewer",
        "1.2.0",
    )

    p5 = parse_qualified_entity_ref("pack://legal-audit/skills/compliance-check")
    assert (p5.pack_slug, p5.kind, p5.entity_slug, p5.is_qualified) == (
        "legal-audit",
        "skills",
        "compliance-check",
        True,
    )

    p6 = parse_qualified_entity_ref("@workspace/custom-helper")
    assert (p6.pack_slug, p6.entity_slug, p6.is_workspace_scope) == (
        "workspace",
        "custom-helper",
        True,
    )

    p7 = parse_qualified_entity_ref("orcia://workspaces/ws-01/skills/local-audit")
    assert (p7.pack_slug, p7.kind, p7.entity_slug, p7.is_workspace_scope) == (
        "workspace",
        "skills",
        "local-audit",
        True,
    )

    p8 = parse_qualified_entity_ref("@reviewer")
    assert (p8.pack_slug, p8.entity_slug, p8.is_qualified) == (None, "reviewer", False)

    assert format_agent_mention("reviewer", pack_slug="sdlc") == "@sdlc/reviewer"
    assert format_agent_mention("reviewer", workspace_scoped=True) == "@workspace/reviewer"
    assert format_skill_command("check", pack_slug="legal-audit") == "/legal-audit/check"
    assert (
        format_pack_resource_uri("sdlc", "agents", "reviewer", version="1.0.0")
        == "orcia://packs/sdlc/agents/reviewer@1.0.0"
    )
    assert (
        format_pack_resource_uri("workspace", "skills", "local", workspace_id="ws-1")
        == "orcia://workspaces/ws-1/skills/local"
    )

    with pytest.raises(ValidationDomainError):
        parse_qualified_entity_ref("")
    with pytest.raises(ValidationDomainError):
        parse_qualified_entity_ref("http://example.com/bad")


def test_parse_federated_uri_normalizes_pack_alias() -> None:
    parsed = parse_federated_uri("pack://sdlc/agents/reviewer@1.0.0")
    assert parsed.scheme == "orcia"
    assert parsed.authority == "packs"
    assert parsed.path == "sdlc/agents/reviewer"
    assert parsed.version_or_ref == "1.0.0"


def test_resolve_workspace_entity_candidates_flat_priority_and_disambiguation() -> None:
    c_sys = WorkspaceEntityCandidate(
        entity_id="system-base:reviewer",
        entity_slug="reviewer",
        pack_slug="system-base",
        resolution_tier="SYSTEM_PACK",
    )
    c_sdlc = WorkspaceEntityCandidate(
        entity_id="sdlc:reviewer",
        entity_slug="reviewer",
        pack_slug="sdlc",
        resolution_tier="WORKSPACE_PACK",
        priority_order=2,
    )
    c_legal = WorkspaceEntityCandidate(
        entity_id="legal-audit:reviewer",
        entity_slug="reviewer",
        pack_slug="legal-audit",
        resolution_tier="WORKSPACE_PACK",
        priority_order=1,
    )

    res_bare = resolve_workspace_entity_candidates(
        "@reviewer",
        [c_sys, c_sdlc, c_legal],
        active_pack_priorities={"legal-audit": 1, "sdlc": 2},
    )
    assert res_bare.winner.entity_id == "legal-audit:reviewer"
    assert res_bare.qualified_ref == "@legal-audit/reviewer"
    assert res_bare.is_colliding is True
    assert res_bare.collision_pack_slugs == ("legal-audit", "sdlc", "system-base")
    assert res_bare.resolution_tier == "WORKSPACE_PACK"

    # Strict disambiguation raises 409 ERR_PACK_ENTITY_AMBIGUOUS on bare ambiguous ref
    with pytest.raises(PackEntityCollisionError) as exc_info:
        resolve_workspace_entity_candidates(
            "@reviewer",
            [c_sdlc, c_legal],
            strict_disambiguation=True,
        )
    assert exc_info.value.http_status == 409
    assert exc_info.value.error_code == "ERR_PACK_ENTITY_AMBIGUOUS"
    assert "correspond à plusieurs candidats" in exc_info.value.localize("fr").detail
    assert "matches multiple candidates" in exc_info.value.localize("en").detail

    # Qualified ref bypasses ambiguity even in strict mode
    res_qual = resolve_workspace_entity_candidates(
        "sdlc:reviewer",
        [c_sdlc, c_legal],
        default_kind="agents",
        strict_disambiguation=True,
    )
    assert res_qual.winner.entity_id == "sdlc:reviewer"
    assert res_qual.qualified_ref == "@sdlc/reviewer"

    # Workspace standalone override beats active priority-1 pack even under strict mode
    c_ws = WorkspaceEntityCandidate(
        entity_id="agent-reviewer",
        entity_slug="reviewer",
        pack_slug=None,
        resolution_tier="WORKSPACE_OVERRIDE",
    )
    res_ws = resolve_workspace_entity_candidates(
        "@reviewer",
        [c_sdlc, c_legal, c_ws],
        strict_disambiguation=True,
    )
    assert res_ws.winner.entity_id == "agent-reviewer"
    assert res_ws.qualified_ref == "@workspace/reviewer"
    assert res_ws.resolution_tier == "WORKSPACE_OVERRIDE"

    with pytest.raises(ResourceNotFoundError):
        resolve_workspace_entity_candidates("@missing", [c_sdlc])


def test_ontology_hierarchy_resolver_flat_workspace_pack_priority_order() -> None:
    def _pc(pslug: str, defn: str, bkind: str = "IMPORTED") -> OntologyConceptEntity:
        return OntologyConceptEntity(
            id=f"c-{pslug}",
            concept_key=f"pack:{pslug}:rg",
            canonical_term="Release Gate",
            level="2_DOMAIN",
            scope_id=pslug,
            definition_text=defn,
            pack_bundle_id=f"b-{pslug}",
            pack_slug=pslug,
            bundle_kind=bkind,
        )

    c_sys = _pc("sys-core", "System baseline gate", "SYSTEM")
    c_sdlc = _pc("sdlc", "SDLC release readiness gate")
    c_legal = _pc("legal-audit", "Legal audit compliance gate")
    c_inactive = _pc("shadow", "Must never leak")
    c_ws = OntologyConceptEntity(
        id="c-ws",
        concept_key="ws:rg",
        canonical_term="Release Gate",
        level="3_WORKSPACE",
        scope_id="ws-001",
        definition_text="Workspace local override gate",
    )

    rels = (
        OntologyRelationEntity(
            "r-1", "rel-g", "pack:legal-audit:rg", "pack:legal-audit:rg", "GOVERNS"
        ),
    )
    axs = (
        OntologyAxiomEntity(
            "a-1", "ax-l", "pack:legal-audit:rg", "2_DOMAIN", "legal-audit", "REQ_SIGN"
        ),
    )

    snap_1 = OntologyHierarchyResolver.resolve_effective_ontology(
        concepts=(c_sys, c_sdlc, c_legal, c_inactive),
        relations=rels,
        axioms=axs,
        enterprise_scope_id="scope-global",
        domain_scope_id="bu-1",
        team_chain_scope_ids=(),
        workspace_scope_id="ws-001",
        active_pack_priorities={"legal-audit": 1, "sdlc": 2},
    )
    assert snap_1.concepts_by_term["Release Gate"].definition_text == "Legal audit compliance gate"
    assert snap_1.pack_priorities == {"legal-audit": 1, "sdlc": 2}

    snap_2 = OntologyHierarchyResolver.resolve_effective_ontology(
        concepts=(c_sys, c_sdlc, c_legal, c_inactive),
        relations=(),
        axioms=(),
        enterprise_scope_id="scope-global",
        domain_scope_id="bu-1",
        team_chain_scope_ids=(),
        workspace_scope_id="ws-001",
        active_pack_priorities={"sdlc": 1, "legal-audit": 2},
    )
    assert snap_2.concepts_by_term["Release Gate"].definition_text == "SDLC release readiness gate"

    snap_3 = OntologyHierarchyResolver.resolve_effective_ontology(
        concepts=(c_sys, c_sdlc, c_legal, c_ws),
        relations=(),
        axioms=(),
        enterprise_scope_id="scope-global",
        domain_scope_id="bu-1",
        team_chain_scope_ids=(),
        workspace_scope_id="ws-001",
        active_pack_priorities={"sdlc": 1, "legal-audit": 2},
    )
    assert (
        snap_3.concepts_by_term["Release Gate"].definition_text == "Workspace local override gate"
    )
    assert "workspace_pack_activations" in build_workspace_pack_ontology_cte_sql()
