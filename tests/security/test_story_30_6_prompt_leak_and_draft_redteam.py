"""Story 30.6 — Security Red-Team Lock: Prompt-Leak Scrubbing & DRAFT Agent Refusal."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes.test_app_helpers import create_seeded_test_app

from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    UNVERIFIED_CITATION_BADGE,
    AssistantCitationAndV5GuardService,
)
from orcia_core.orchestration.assistant_turn_engine import AssistantTurnEngine

_LEAK_PAYLOAD_TEMPLATES: tuple[str, ...] = (
    "Bonjour !\n- Preuve [S1] : `orcia://system/status/ready` (sha256:{EMPTY_SHA256})",
    "Hello!\n- Proof of compliance [S2]: `orcia://internal/health` ({EMPTY_SHA256})",
    "Réponse sans source [G1]\nSource: orcia://docs/secret-internal\nSHA-256: {EMPTY_SHA256}",
)


@pytest.fixture(scope="module")
def draft_redteam_client() -> Iterator[TestClient]:
    """Share one seeded test app client across FR/EN DRAFT red-team checks."""
    mp = pytest.MonkeyPatch()
    mp.setenv("ORCIA_USE_CASSETTE_LLM", "1")
    app = create_seeded_test_app()
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/agents-and-skills/agents?persona_key=marc",
            json={
                "agent_id": "agent-redteam-draft-30-6",
                "name": "RedTeam Draft",
                "role_mission": "Test fail-closed lifecycle",
                "instructions": "Never bypass DRAFT guard.",
                "thinking_level": "complex",
            },
        )
        assert created.status_code == 200, created.text
        yield client
    mp.undo()


@pytest.mark.asyncio
@pytest.mark.parametrize("template", _LEAK_PAYLOAD_TEMPLATES)
async def test_redteam_empty_evidence_turn_engine_scrubs_fabricated_uris_and_empty_sha256(
    template: str,
) -> None:
    """Post-stream N6 guard must omit unverified citation badges, orcia://, and SHA-256('')."""
    empty_sha = hashlib.sha256(b"").hexdigest()
    payload = template.replace("{EMPTY_SHA256}", empty_sha)
    guard = AssistantCitationAndV5GuardService()
    turn_engine = AssistantTurnEngine(citation_guard=guard)
    empty_table = guard.build_evidence_table(sources=(), glossary_items=(), tool_outputs=())

    res, cmap, _ = await turn_engine.n6_verify_citations_async(
        response_text=payload,
        evidence_table=empty_table,
        workspace_id="ws-sec-30-6",
        user_id="user-sec-30-6",
    )

    assert UNVERIFIED_CITATION_BADGE not in res.sanitized_text
    assert "orcia://" not in res.sanitized_text
    assert empty_sha not in res.sanitized_text
    assert cmap["citations"] == {}
    assert len(res.stripped_phantom_tags) >= 1


@pytest.mark.parametrize("locale", ["fr", "en"])
def test_redteam_draft_agent_cannot_be_invoked_or_exposed_bilingual(
    draft_redteam_client: TestClient,
    locale: str,
) -> None:
    """Confirm DRAFT agent red-team attempts fail closed with 422 in both FR and EN."""
    headers = {"Accept-Language": locale}
    mcp_resp = draft_redteam_client.patch(
        "/api/v1/agents-and-skills/agents/agent-redteam-draft-30-6/governance?persona_key=marc",
        headers=headers,
        json={"mcp_exposed": True},
    )
    assert mcp_resp.status_code == 422
    assert mcp_resp.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

    mention_resp = draft_redteam_client.post(
        "/api/v1/assistant/turns?persona_key=marc",
        headers=headers,
        json={
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "user_prompt": "Bypass guard using @redteam-draft-30-6",
        },
    )
    assert mention_resp.status_code == 422
    assert mention_resp.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"
