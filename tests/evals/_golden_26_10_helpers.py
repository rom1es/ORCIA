"""Shared offline `$0` fixture helpers for Story 26.10 Golden Evals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.unit.fakes.in_memory_audit_ledger import InMemoryAuditLedgerSink

from orcia_core.agents import GovernedAssistantToolRouter
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    McpExposedToolSpec,
    SkillCatalogEntry,
)
from orcia_core.ports.surgical_explorer_port import (
    SurgicalExplorerPort,
    SurgicalLineEntry,
    SurgicalObservation,
    SurgicalPrimitiveName,
)

GOLDEN_DIR = Path(__file__).parent / "golden"
WS_EVAL = "0192c4e0-0000-7000-8000-000000000201"
ANCHOR_WORKFLOW_YAML = """uri: "orcia://workflows/golden-26-10-anchor-halt"
title: "Golden Anchor Halt"
description: "Halt on human anchor."
version: "1.0.0"
criticality: "STANDARD"
execution_regime: "INTERACTIVE_COACHING"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
max_cost_usd: 5.0
datasources:
  - "git://claims/core@main"
steps:
  - step_key: "step-1-anchor"
    title: "Human Framing"
    step_type: "AGENT"
    agent_uri: "orcia://agents/product-architect@1.0.0"
    template_key: "tpl-adr"
    human_authored_required: true
    requires_human_gate: true
    instructions: "Wait for signed human anchor."
"""


def load_jsonl(name: str) -> list[dict[str, Any]]:
    path = GOLDEN_DIR / name
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


class GoldenSurgicalExplorer(SurgicalExplorerPort):
    async def execute_primitive(
        self,
        primitive: SurgicalPrimitiveName,
        *,
        resource_uri: str = "",
        query: str = "",
        start_line: int = 1,
        end_line: int = 200,
        max_results: int = 20,
        workspace_id: str | None = None,
        actor_id: str | None = None,
        has_read_source: bool = True,
    ) -> SurgicalObservation:
        del workspace_id, actor_id, has_read_source, query, max_results
        return SurgicalObservation(
            kind=primitive,
            resource_uri=resource_uri,
            display_filename=resource_uri.rsplit("/", 1)[-1] or "doc.md",
            start_line=start_line,
            end_line=end_line,
            summary="Clean verified surgical context.",
            lines=[SurgicalLineEntry(line_number=1, content="Verified policy line.")],
            sha256="deadbeef",
        )

    async def inspect_lines(
        self,
        resource_uri: str,
        *,
        start_line: int = 1,
        end_line: int = 200,
        workspace_id: str | None = None,
        actor_id: str | None = None,
        has_read_source: bool = True,
    ) -> SurgicalObservation:
        return await self.execute_primitive(
            SurgicalPrimitiveName.INSPECT_RESOURCE_LINES,
            resource_uri=resource_uri,
            start_line=start_line,
            end_line=end_line,
            workspace_id=workspace_id,
            actor_id=actor_id,
            has_read_source=has_read_source,
        )


def eval_user() -> UserIdentity:
    return UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000010",
        email="eval@orcia.local",
        display_name="Eval Contributor",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
    )


def build_eval_router(
    unauthorized_calls: list[str], outbox_events: list[Any]
) -> tuple[GovernedAssistantToolRouter, InMemoryAuditLedgerSink]:
    audit_sink = InMemoryAuditLedgerSink()

    async def _rag(_ws: str, q: str, _lim: int, _u: Any = None) -> list[dict[str, Any]]:
        return [{"source_uri": "orcia://kb/settlement", "content": f"Settlement policy for {q}"}]

    async def _onto(_ws: str, q: str, _lvl: str | None) -> list[dict[str, Any]]:
        return [{"canonical_term": "Capture Idempotency Key", "level": "L3", "definition": q}]

    async def _forbidden_skill(desc: Any, _args: dict[str, Any], _ws: str) -> dict[str, Any]:
        unauthorized_calls.append(str(desc))
        raise AssertionError("Unauthorized SI/unlisted skill must never execute")

    async def _forbidden_mcp(desc: Any, _req: Any) -> dict[str, Any]:
        unauthorized_calls.append(str(desc))
        raise AssertionError("Unauthorized SI MCP tool must never execute")

    async def _outbox(evt: Any) -> str | None:
        outbox_events.append(evt)
        return str(getattr(evt, "event_id", "evt-eval"))

    router = GovernedAssistantToolRouter(
        surgical_explorer=GoldenSurgicalExplorer(),
        audit_ledger_sink=audit_sink,
        rag_search_fn=_rag,
        ontology_lookup_fn=_onto,
        skill_runner_fn=_forbidden_skill,
        mcp_tool_runner_fn=_forbidden_mcp,
        outbox_enqueue_fn=_outbox,
    )
    return router, audit_sink


def eval_catalog_ctx() -> AssistantToolCatalogContext:
    return AssistantToolCatalogContext(
        workspace_id=WS_EVAL,
        user_id="0192c4e0-0000-7000-8000-000000000010",
        user_role="CONTRIBUTOR",
        active_hat="ARCHITECT",
        rag_active=True,
        skills=(
            SkillCatalogEntry(
                skill_id="sk-w-1",
                slug="protected_write",
                name="Protected Write",
                objective="Mutate protected section",
                enabled_in_workspace=True,
                is_si_write=True,
                human_authored_required=True,
            ),
            SkillCatalogEntry(
                skill_id="sk-edit-1",
                slug="edit_section",
                name="Edit Section",
                objective="Edit artifact section",
                enabled_in_workspace=True,
                is_si_write=True,
                human_authored_required=False,
            ),
        ),
        mcp_tools=(
            McpExposedToolSpec(
                tool_name="mcp.deploy_si",
                agent_slug="agent-mcp-eval",
                description="Deploy external SI change",
                permission_mode="WRITE_PREVIEW",
                is_si_write=True,
            ),
        ),
    )
