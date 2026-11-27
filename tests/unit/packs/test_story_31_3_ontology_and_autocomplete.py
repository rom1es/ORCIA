"""Unit tests for Story 31.3: Service Disambiguation, Tool Catalog & API Resolve (`<= 300 L`)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from orcia_api.middleware.trace_and_error import register_exception_handlers
from orcia_api.routers.agents_and_skills import router as agents_router
from orcia_core.agents import build_authorized_tool_catalog
from orcia_core.orchestration import (
    AgentsAndSkillsManagementService,
    ManagedAgentRecord,
    ManagedSkillRecord,
)
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    SkillCatalogEntry,
)


def _make_agent(
    *, pack: str | None, slug: str = "reviewer", lifecycle: str = "ACTIVE"
) -> ManagedAgentRecord:
    aid = f"{pack}:{slug}" if pack else f"agent-{slug}"
    return ManagedAgentRecord(
        agent_id=aid,
        slug=slug,
        handle=f"@{slug}",
        uri=f"orcia://packs/{pack}/agents/{slug}@1.0.0" if pack else f"orcia://agents/{slug}@1.0.0",
        name=f"{pack or 'ws'} {slug}",
        role_mission="Review",
        instructions="Check all items",
        thinking_level="medium",
        visibility_scope="PACK" if pack else "TEAM",
        source_pack_key=f"orcia-pack-{pack}" if pack else None,
        lifecycle_status="ACTIVE" if lifecycle == "ACTIVE" else "DRAFT",
        test_bench_status="PASSED" if lifecycle == "ACTIVE" else "UNTESTED",
        test_bench_validated=(lifecycle == "ACTIVE"),
        pack_slug=pack,
    )


def _make_skill(*, pack: str | None, slug: str = "compliance-check") -> ManagedSkillRecord:
    sid = f"{pack}:{slug}" if pack else f"skill-{slug}"
    return ManagedSkillRecord(
        skill_id=sid,
        slug=slug,
        command_handle=f"/{slug}",
        uri=f"orcia://packs/{pack}/skills/{slug}@1.0.0" if pack else f"orcia://skills/{slug}@1.0.0",
        name=f"{pack or 'ws'} {slug}",
        objective="Run check",
        input_parameters=("target",),
        instructions="Execute check",
        expected_output_format="Markdown",
        visibility_scope="PACK" if pack else "TEAM",
        source_pack_key=f"orcia-pack-{pack}" if pack else None,
        pack_slug=pack,
    )


def test_agents_service_collision_annotation_and_resolution() -> None:
    svc = AgentsAndSkillsManagementService()
    ag_sdlc = _make_agent(pack="sdlc")
    ag_legal = _make_agent(pack="legal-audit")
    sk_sdlc = _make_skill(pack="sdlc")
    sk_legal = _make_skill(pack="legal-audit")

    svc.sync_from_records(
        skills=(sk_sdlc, sk_legal),
        agents=(ag_sdlc, ag_legal),
        active_pack_priorities={"legal-audit": 1, "sdlc": 2},
    )
    assert len(svc.agents) == 2
    assert len(svc.skills) == 2
    by_id = {a.agent_id: a for a in svc.agents}
    assert by_id["sdlc:reviewer"].qualified_ref == "@sdlc/reviewer"
    assert by_id["legal-audit:reviewer"].qualified_ref == "@legal-audit/reviewer"
    assert by_id["sdlc:reviewer"].is_colliding is True
    assert by_id["sdlc:reviewer"].collision_pack_slugs == ("legal-audit", "sdlc")

    resolved_bare = svc.resolve_agent_ref(
        "@reviewer", active_pack_priorities={"legal-audit": 1, "sdlc": 2}
    )
    assert resolved_bare.winner.entity_id == "legal-audit:reviewer"

    resolved_explicit = svc.resolve_agent_ref("@sdlc/reviewer")
    assert resolved_explicit.winner.entity_id == "sdlc:reviewer"

    resolved_colon = svc.resolve_skill_ref("legal-audit:compliance-check")
    assert resolved_colon.winner.entity_id == "legal-audit:compliance-check"
    assert resolved_colon.qualified_ref == "/legal-audit/compliance-check"


def test_tool_catalog_preserves_colliding_pack_skills() -> None:
    ctx = AssistantToolCatalogContext(
        workspace_id="ws-001",
        user_id="u-1",
        user_role="WORKSPACE_MEMBER",
        active_hat="ARCHITECT",
        user_permissions=frozenset({"read", "execute"}),
        rag_active=False,
        skills=(
            SkillCatalogEntry(
                skill_id="sdlc:compliance-check",
                slug="compliance-check",
                name="SDLC Compliance",
                objective="Verify SDLC",
                uri="orcia://packs/sdlc/skills/compliance-check@1.0.0",
            ),
            SkillCatalogEntry(
                skill_id="legal-audit:compliance-check",
                slug="compliance-check",
                name="Legal Compliance",
                objective="Verify Legal",
                uri="orcia://packs/legal-audit/skills/compliance-check@1.0.0",
            ),
            SkillCatalogEntry(
                skill_id="skill-unique",
                slug="unique-helper",
                name="Unique Helper",
                objective="Assist",
                uri="orcia://workspaces/ws-001/skills/unique-helper",
            ),
        ),
    )
    descriptors = build_authorized_tool_catalog(ctx)
    names = {d.tool_name for d in descriptors}
    assert "skill_sdlc__compliance_check" in names
    assert "skill_legal_audit__compliance_check" in names
    assert "skill_unique_helper" in names


def test_api_agents_resolve_strict_409_bilingual_and_qualified() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(agents_router)
    svc = AgentsAndSkillsManagementService()
    svc.sync_from_records(
        skills=(_make_skill(pack="sdlc"), _make_skill(pack="legal-audit")),
        agents=(_make_agent(pack="sdlc"), _make_agent(pack="legal-audit")),
        active_pack_priorities={"sdlc": 1, "legal-audit": 2},
    )
    app.state.agents_and_skills_service = svc

    client = TestClient(app)
    list_res = client.get("/api/v1/agents-and-skills")
    assert list_res.status_code == 200
    agents = list_res.json()["agents"]
    assert {a["qualified_ref"] for a in agents} == {"@sdlc/reviewer", "@legal-audit/reviewer"}
    assert all(a["is_colliding"] is True for a in agents)

    # Strict disambiguation returns bilingual RFC 9457 409
    err_fr = client.get(
        "/api/v1/agents-and-skills/resolve",
        params={"ref": "@reviewer", "kind": "agent", "strict_disambiguation": "true"},
        headers={"Accept-Language": "fr"},
    )
    assert err_fr.status_code == 409
    assert err_fr.json()["error_code"] == "ERR_PACK_ENTITY_AMBIGUOUS"
    assert "reviewer" in err_fr.json()["detail"]

    err_en = client.get(
        "/api/v1/agents-and-skills/resolve",
        params={"ref": "@reviewer", "kind": "agent", "strict_disambiguation": "true"},
        headers={"Accept-Language": "en"},
    )
    assert err_en.status_code == 409
    assert "matches multiple candidates" in err_en.json()["detail"]

    # Qualified ref succeeds even with strict_disambiguation=true
    ok = client.get(
        "/api/v1/agents-and-skills/resolve",
        params={
            "ref": "@legal-audit/reviewer",
            "kind": "agent",
            "strict_disambiguation": "true",
        },
    )
    assert ok.status_code == 200
    payload = ok.json()
    assert payload["entity_id"] == "legal-audit:reviewer"
    assert payload["pack_slug"] == "legal-audit"
    assert payload["qualified_ref"] == "@legal-audit/reviewer"
