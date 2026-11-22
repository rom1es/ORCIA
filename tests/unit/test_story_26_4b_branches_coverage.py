"""Story 26.4b — Branch Coverage Unit Tests for Governance, Folders, Citations & Feedback."""

from __future__ import annotations

import pytest
from tests.unit.fakes.in_memory_assistant_governance import InMemoryAssistantGovernanceStore

from orcia_core.orchestration._internal._sql_assistant_folders_queries import (
    _decode_str_list,
    coerce_folder_uuid,
)
from orcia_core.orchestration._internal._sql_assistant_governance_queries import decode_manifest
from orcia_core.orchestration._internal.sql_assistant_feedback import (
    SqlAssistantFeedbackRepository,
)
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
    RawGlossaryCandidate,
    RawSourceCandidate,
    RawToolOutputCandidate,
    _parse_optional_uuid,
)
from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.errors import FunnelRuleViolationError
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.finops_telemetry import FinopsCostLedgerEntry


class _FailingLedgerSink:
    async def record_entry(self, entry: FinopsCostLedgerEntry, *, conn: object = None) -> str:
        _ = (entry, conn)
        raise RuntimeError("simulated ledger outage")


def _make_lead(user_id: str = "u-lead-264b") -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=f"{user_id}@orcia.io",
        display_name=user_id,
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )


@pytest.mark.asyncio
async def test_governance_async_fallbacks_store_and_funnel_rule() -> None:
    """Exercise async fallback paths, store freeze/unfreeze, and default preview branches."""
    store = InMemoryAssistantGovernanceStore()
    svc = AssistantFourLevelGovernanceService(store=store)
    lead = _make_lead()

    await svc.freeze_mcp_at_upper_layer_async(workspace_id="ws-cov", frozen=True, origin="TEAM")
    with pytest.raises(FunnelRuleViolationError):
        await svc.update_workspace_settings_async(
            lead,
            workspace_id="ws-cov",
            workspace_instructions="Blocked reopen",
            default_checked_sources=(),
            recommended_agents=(),
            arbitration_policy="PAUSE_AND_ESCALATE",
            mcp_expose_assistant=True,
        )
    await svc.freeze_mcp_at_upper_layer_async(workspace_id="ws-cov", frozen=False, origin="TEAM")
    updated_ws = await svc.update_workspace_settings_async(
        lead,
        workspace_id="ws-cov",
        workspace_instructions="Unfrozen reopen",
        default_checked_sources=("orcia://s1",),
        recommended_agents=("@arch",),
        arbitration_policy="AUTO_RESOLVE_WITH_TRACE",
        mcp_expose_assistant=False,
    )
    assert updated_ws.mcp_expose_assistant is False
    assert (await svc.get_workspace_settings_async("ws-cov")).workspace_instructions == (
        "Unfrozen reopen"
    )

    prefs = await svc.update_user_preferences_async(
        lead,
        workspace_id="ws-cov",
        response_tone="SYNTHETIC",
        favorite_format="BULLETS_SUMMARY",
        default_hat="ARCHITECT",
        personal_instructions="Cite [S1].",
    )
    assert prefs.default_hat == "ARCHITECT"
    assert (
        await svc.get_user_preferences_async(workspace_id="ws-cov", user_id=lead.id)
    ).default_hat == "ARCHITECT"

    layers_en = await svc.assemble_five_layers_preview_async(
        workspace_id="ws-cov", user_id=lead.id, locale="en"
    )
    assert len(layers_en) == 5
    view = await svc.get_governance_view_async(lead, workspace_id="ws-cov", locale="en")
    assert len(view.override_records) == 2

    stateless = AssistantFourLevelGovernanceService()
    assert (
        len(stateless.assemble_five_layers_preview(workspace_id="ws-0", user_id="u-0", locale="en"))
        == 5
    )
    assert stateless.get_governance_view(lead, workspace_id="ws-0").workspace_id == "ws-0"


@pytest.mark.asyncio
async def test_citations_async_failing_sink_and_mappers_decode_branches() -> None:
    """Exercise failing audit sink graceful warning, UUID helpers, and JSON/list decoders."""
    assert _parse_optional_uuid(None) is None
    assert _parse_optional_uuid("not-a-uuid") is None
    assert _parse_optional_uuid("0192c4e0-0000-7000-8000-000000000201") is not None

    cit_svc = AssistantCitationAndV5GuardService()
    cit_svc.set_audit_ledger_sink(_FailingLedgerSink())  # type: ignore[arg-type]
    table = cit_svc.build_evidence_table(
        sources=(
            RawSourceCandidate(
                uri="orcia://s1",
                title="S1",
                authority_tier="REFERENCE",
                freshness="FRESH",
                snippet="snippet",
            ),
        ),
        glossary_items=(
            RawGlossaryCandidate(
                term_or_axiom_id="g1",
                label="G1",
                ontology_level="N1_DIRECTIVE",
                definition="def",
            ),
        ),
        tool_outputs=(
            RawToolOutputCandidate(tool_name="t1", connector_uri="mcp://t1", summary="ok"),
        ),
    )
    res = await cit_svc.verify_and_sanitize_citations_async(
        response_text="Valid [S1] [G1] [O1] and bad [S88].",
        evidence_table=table,
        workspace_id="ws-slug-not-uuid",
        user_id="u-1",
    )
    assert res.stripped_phantom_tags == ("S88",)

    assert _decode_str_list(None, default=("S1",)) == ("S1",)
    assert _decode_str_list('["a", "b"]') == ("a", "b")
    assert _decode_str_list(123, default=("fallback",)) == ("fallback",)
    assert decode_manifest('{"k": "v"}') == {"k": "v"}
    assert decode_manifest("[]") == {}
    assert decode_manifest(None) == {}
    assert str(coerce_folder_uuid(None))

    fb_repo = SqlAssistantFeedbackRepository()
    assert await fb_repo.pg_tables_ready() is False
    rec = await fb_repo.upsert_feedback(
        turn_id="turn-slug-1",
        workspace_id="ws-1",
        user=_make_lead(),
        rating="up",
        reason_code="CLEAR",
        comment="Nice",
    )
    assert rec.rating == "up"
