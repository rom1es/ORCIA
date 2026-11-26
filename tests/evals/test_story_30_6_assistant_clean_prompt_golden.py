"""Story 30.6 — Offline `$0` Golden Evals for Clean Empty-Evidence Prompts (`AD-17` C4)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from tests.unit.fakes.in_memory_assistant_governance import InMemoryAssistantGovernanceStore

from orcia_api.routers.assistant_llm_prompts import (
    resolve_assembled_turn_context_and_instructions_async,
)
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    UNVERIFIED_CITATION_BADGE,
    AssistantCitationAndV5GuardService,
)
from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.assistant_prompt_builder import AssistantPromptBuilder
from orcia_core.permissions.models import UserIdentity

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "assistant_clean_prompt_30_6.jsonl"

FORBIDDEN_PROMPT_MARKERS: tuple[str, ...] = (
    "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]",
    "[NO_HUMAN_ANCHOR_WRITE]",
    "human_authored_required",
    "[EXPLICIT_PROVENANCE_URI]",
    "[ACTIVE_DOMAIN_PACK:",
    "[ADAPTATION_RUNTIME_METADATA]",
    "[Citation non vérifiée]",
)

FORBIDDEN_OUTPUT_MARKERS: tuple[str, ...] = (
    *FORBIDDEN_PROMPT_MARKERS,
    "orcia://",
)


def _load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _eval_user() -> UserIdentity:
    return UserIdentity(
        id="0192c4e0-0000-7000-8000-000000003060",
        email="helene.eval@orcia.local",
        display_name="Helene Eval",
        auth_mode="LOCAL",
        human_profile_archetype="PM",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
    )


def _mock_request(gov_svc: AssistantFourLevelGovernanceService) -> Any:
    return SimpleNamespace(
        headers={},
        app=SimpleNamespace(
            state=SimpleNamespace(
                assistant_governance_service=gov_svc,
                declarative_pack_bundles={"orcia-pack-sdlc": object()},
                db_engine=None,
                ontology_service=SimpleNamespace(concepts=()),
            )
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: str(c["id"]))
async def test_golden_empty_evidence_prompt_and_post_stream_scrub_zero_cost(
    case: dict[str, Any],
) -> None:
    """Verify clean FR/EN empty-evidence prompts and zero phantom URI/SHA-256("") output."""
    empty_sha = hashlib.sha256(b"").hexdigest()
    locale = str(case["locale"])
    user = _eval_user()

    store = InMemoryAssistantGovernanceStore()
    gov = AssistantFourLevelGovernanceService(store=store)
    gov.update_user_preferences(
        user,
        workspace_id="ws-eval-30-6",
        response_tone="BALANCED",
        favorite_format="STRUCTURED_SECTIONS",
        default_hat=str(case["hat"]),
        personal_instructions="",
    )

    sys_msg, ctx = await resolve_assembled_turn_context_and_instructions_async(
        _mock_request(gov),
        hat=str(case["hat"]),
        speed_mode=str(case["speed_mode"]),
        workspace_id="ws-eval-30-6",
        user_id=user.id,
        user_prompt=str(case["user_prompt"]),
        user=user,
        locale=locale,
    )
    assert ctx.has_evidence is False
    for forbidden in (*FORBIDDEN_PROMPT_MARKERS, empty_sha):
        assert forbidden not in sys_msg, f"Forbidden token {forbidden!r} in {locale} prompt"

    built = AssistantPromptBuilder().assemble_prompt(
        user_prompt=str(case["user_prompt"]),
        human_profile_archetype=str(case["hat"]),
        workspace_id="ws-eval-30-6",
        intent="QA_COACHING",
        locale=locale,
    )
    for forbidden in (*FORBIDDEN_PROMPT_MARKERS, empty_sha):
        assert forbidden not in built.system_prompt
        assert forbidden not in built.user_prompt

    guard = AssistantCitationAndV5GuardService()
    empty_table = guard.build_evidence_table(sources=(), glossary_items=(), tool_outputs=())
    raw_reply = str(case["raw_llm_reply"]).replace("{EMPTY_SHA256}", empty_sha)
    verified = guard.verify_and_sanitize_citations(
        response_text=raw_reply,
        evidence_table=empty_table,
        workspace_id="ws-eval-30-6",
        user_id=user.id,
    )

    assert str(case["expect_kept"]) in verified.sanitized_text
    assert UNVERIFIED_CITATION_BADGE not in verified.sanitized_text
    for forbidden in (*FORBIDDEN_OUTPUT_MARKERS, empty_sha, "[S1]", "[G2]", "[O1]", "[S3]"):
        assert forbidden not in verified.sanitized_text, (
            f"Post-stream guard failed to strip {forbidden!r}"
        )


def test_story_30_6_clean_prompt_golden_minimum_volume() -> None:
    """Enforce minimum FR/EN golden coverage in Story 30.6 clean prompt dataset."""
    cases = _load_cases()
    assert len(cases) >= 6
    locales = {c["locale"] for c in cases}
    assert locales == {"fr", "en"}
