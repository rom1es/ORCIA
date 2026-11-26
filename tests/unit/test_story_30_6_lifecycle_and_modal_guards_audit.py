"""Story 30.6 — Backend Lifecycle Guards & Structural UI Anti-Regression Audit."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
_HIDDEN_DISPLAY_NONE_RE = re.compile(r"""display\s*:\s*["']none["']""")
_EVALUATE_CLICK_RE = re.compile(r"""\.\s*evaluate\s*\([^;\n)]*\.click\s*\(""")


def test_modal_sources_and_e2e_specs_forbid_hidden_save_and_evaluate_click_hacks() -> None:
    """Ensure modals have zero display:none Save buttons and E2E has zero evaluate().click()."""
    modal_paths = (
        REPO_ROOT / "packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx",
        REPO_ROOT / "packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx",
        REPO_ROOT / "packages/ui/src/components/AgentDetailAndSandboxModal.tsx",
    )
    for modal_path in modal_paths:
        src = modal_path.read_text(encoding="utf-8")
        assert _HIDDEN_DISPLAY_NONE_RE.search(src) is None, (
            f"Forbidden display:none found in {modal_path.relative_to(REPO_ROOT)}"
        )

    gov_modal_src = modal_paths[0].read_text(encoding="utf-8")
    agent_modal_src = modal_paths[2].read_text(encoding="utf-8")
    assert 'testId="assistant-gov-error-banner"' in gov_modal_src
    assert 'tone="crimson"' in gov_modal_src
    assert 'role="alert"' in agent_modal_src
    assert "agent-detail-modal-error-" in agent_modal_src

    e2e_dir = REPO_ROOT / "apps/web/e2e"
    for spec_path in sorted(e2e_dir.rglob("*.ts")):
        if "node_modules" in spec_path.parts:
            continue
        spec_src = spec_path.read_text(encoding="utf-8")
        assert _EVALUATE_CLICK_RE.search(spec_src) is None, (
            f"Forbidden .evaluate(...click()) hack in {spec_path.relative_to(REPO_ROOT)}"
        )


def test_focus_review_uses_single_primary_decision_banner_without_bar_duplication() -> None:
    """Lock Focus Review to ProcessRunActionBanner without legacy Bar 1/Bar 2 stacking."""
    focus_src = (
        REPO_ROOT / "apps/web/src/features/processes/execution/ProcessRunFocusReviewPage.tsx"
    ).read_text(encoding="utf-8")
    banner_src = (
        REPO_ROOT / "apps/web/src/features/processes/execution/ProcessRunActionBanner.tsx"
    ).read_text(encoding="utf-8")
    rail_src = (
        REPO_ROOT / "apps/web/src/features/processes/execution/ProcessRunReasoningRail.tsx"
    ).read_text(encoding="utf-8")

    assert "ProcessRunActionBanner" in focus_src
    assert "InteractiveRunDeliverableAndHitlPanels" not in focus_src
    assert "anchor-card-four-actions-panel" not in focus_src
    assert "renderSinglePrimaryCta" in banner_src
    assert "defaultCollapsedWhenCompleted={true}" in rail_src


def test_backend_draft_agent_blocked_across_assistant_processes_and_mcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce HTTP 422 ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED on all DRAFT execution/exposure routes."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "1")
    client = TestClient(create_app())

    pending_day0 = client.get("/api/v1/workflows/v2/runs?persona_key=marc")
    assert pending_day0.status_code == 200
    assert pending_day0.json()["pending_count"] == 0

    created = client.post(
        "/api/v1/agents-and-skills/agents?persona_key=marc",
        json={
            "agent_id": "agent-audit-30-6-draft",
            "name": "Audit 30.6 Draft",
            "role_mission": "Lock lifecycle exclusion",
            "instructions": "Never allow while DRAFT.",
            "thinking_level": "medium",
        },
    )
    assert created.status_code == 200
    assert created.json()["lifecycle_status"] == "DRAFT"
    assert created.json()["test_bench_status"] == "UNTESTED"

    # 1. Assistant @mention blocked with 422
    turn_resp = client.post(
        "/api/v1/assistant/turns?persona_key=marc",
        json={
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "user_prompt": "Ask @audit-30-6-draft to summarize architecture",
        },
    )
    assert turn_resp.status_code == 422
    assert turn_resp.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

    # 2. MCP exposure blocked with 422 on both governance PATCH and MCP PUT
    patch_mcp = client.patch(
        "/api/v1/agents-and-skills/agents/agent-audit-30-6-draft/governance?persona_key=marc",
        json={"mcp_exposed": True},
    )
    assert patch_mcp.status_code == 422
    assert patch_mcp.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

    put_mcp = client.put(
        "/api/v1/mcp/exposure?persona_key=marc",
        json={
            "workspace_slug": "global",
            "agent_slug": "audit-30-6-draft",
            "display_name": "Audit 30.6 Draft",
            "mcp_exposed": True,
        },
    )
    assert put_mcp.status_code == 422
    assert put_mcp.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

    # 3. Processes workflow save (step ref) and reflexive execution blocked with 422
    base_wf = client.get("/api/v1/workflows/v2").json()["items"][0]
    wf_step_draft = {
        **base_wf,
        "id": "wf-audit-30-6-step-draft",
        "slug": "wf-audit-30-6-step-draft",
        "sub_steps": [
            {
                **base_wf["sub_steps"][0],
                "instruction_prompt_or_ref": "@audit-30-6-draft",
            }
        ],
    }
    wf_put = client.put(
        "/api/v1/workflows/v2/wf-audit-30-6-step-draft?persona_key=marc",
        json={"workflow": wf_step_draft, "publish": False},
    )
    assert wf_put.status_code == 422
    assert wf_put.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

    reflex_resp = client.post(
        "/api/v1/executions/reflexive?persona_key=marc",
        json={
            "actor_slug": "audit-30-6-draft",
            "objective": "Verify DRAFT block",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "initial_resources": ["workspace://docs/readme.md"],
        },
    )
    assert reflex_resp.status_code == 422
    assert reflex_resp.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"
