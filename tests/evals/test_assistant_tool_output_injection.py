"""Golden Anti-Injection Evaluation for Untrusted Tool Outputs (`Story 26.6b`, `AD-17` C4).

Runs at `$0` (`DeterministicCassetteLLM` + `GovernedAssistantToolRouter`) to prove:
1. Prompt injections, closing-tag breakouts, `[LAYER_*]` spoofing, and leaked credentials inside
   tool payloads are sanitized (`scrub_connector_secrets`) and wrapped strictly inside
   `<untrusted_tool_output ... untrusted="true">` delimiters.
2. Constitutional Layer 1 (`CONSTITUTIONAL_LAYER_1_TEXT`) remains invariant across the turn.
3. Subsequent malicious tool calls injected by untrusted payloads (SI writes, human-anchor edits,
   or `service_principal` privilege escalation) are deterministically blocked by Steps A/B.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from orcia_core.agents import GovernedAssistantToolRouter
from orcia_core.orchestration.assistant_harness import (
    CONSTITUTIONAL_LAYER_1_TEXT,
    AssistantHarness,
)
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    AssistantToolExecutionRequest,
    McpExposedToolSpec,
    SkillCatalogEntry,
)
from orcia_core.ports.llm_port import LlmPromptRequest
from orcia_core.ports.surgical_explorer_port import (
    SurgicalExplorerPort,
    SurgicalLineEntry,
    SurgicalObservation,
    SurgicalPrimitiveName,
)
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM

GOLDEN_PATH = Path(__file__).parent / "golden" / "assistant_tool_output_injection.jsonl"


def _load_injection_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class _AdversarialSurgicalExplorer(SurgicalExplorerPort):
    """Returns adversarial injection payloads from golden dataset cases."""

    def __init__(self, payload_text: str) -> None:
        self._payload_text = payload_text

    async def execute_primitive(
        self,
        primitive: SurgicalPrimitiveName,
        *,
        resource_uri: str,
        workspace_id: str,
        actor_id: str,
        has_read_source: bool = True,
        query: str = "",
        start_line: int = 1,
        end_line: int = 200,
        max_results: int = 20,
    ) -> SurgicalObservation:
        del workspace_id, actor_id, has_read_source, query, max_results
        return SurgicalObservation(
            kind=primitive,
            resource_uri=resource_uri,
            display_filename=resource_uri.rsplit("/", 1)[-1] or "doc.md",
            start_line=start_line,
            end_line=end_line,
            summary=self._payload_text,
            lines=[SurgicalLineEntry(line_number=1, content=self._payload_text)],
            sha256="abc123",
        )


class _RecordingAuditSink:
    def __init__(self) -> None:
        self.entries: list[Any] = []

    async def record_entry(self, entry: Any) -> str:
        self.entries.append(entry)
        return f"aud-{len(self.entries)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _load_injection_cases(), ids=lambda c: str(c["id"]))
async def test_golden_tool_output_injection_neutralized(case: dict[str, Any]) -> None:
    payload = case["malicious_payload"]
    payload_str = payload if isinstance(payload, str) else json.dumps(payload)

    async def _rag_search(
        _ws: str, _q: str, _limit: int, _user: Any = None
    ) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            enriched = dict(payload)
            enriched["api_key"] = "dummy-eval-cred-99"  # pragma: allowlist secret
            return [enriched]
        return [{"source_uri": "orcia://kb/doc", "content": payload_str}]

    async def _onto_lookup(_ws: str, _q: str, _lvl: str | None) -> list[dict[str, Any]]:
        return [{"canonical_term": "Run", "level": "L1", "definition": "Governed execution"}]

    async def _skill_run(_desc: Any, _args: dict[str, Any], _ws: str) -> dict[str, Any]:
        raise AssertionError("SI write or human-anchor skill must never execute directly in chat")

    async def _mcp_run(_desc: Any, _args: dict[str, Any], _ws: str) -> dict[str, Any]:
        raise AssertionError("SI write MCP tool must never execute directly in chat")

    audit_sink = _RecordingAuditSink()
    outbox_events: list[Any] = []

    async def _outbox_enqueue(event: Any) -> str | None:
        outbox_events.append(event)
        return str(getattr(event, "event_id", "evt-1"))

    router = GovernedAssistantToolRouter(
        surgical_explorer=_AdversarialSurgicalExplorer(payload_str),
        audit_ledger_sink=audit_sink,
        rag_search_fn=_rag_search,
        ontology_lookup_fn=_onto_lookup,
        skill_runner_fn=_skill_run,
        mcp_tool_runner_fn=_mcp_run,
        outbox_enqueue_fn=_outbox_enqueue,
    )
    ctx = AssistantToolCatalogContext(
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        user_id="user-eval-1",
        user_role="CONTRIBUTOR",
        active_hat="ARCHITECT",
        rag_active=True,
        skills=(
            SkillCatalogEntry(
                skill_id="sk-write-1",
                slug="protected_write",
                name="Protected Write Skill",
                objective="Mutate protected section",
                enabled_in_workspace=True,
                is_si_write=True,
                human_authored_required=True,
            ),
            SkillCatalogEntry(
                skill_id="sk-edit-sec",
                slug="edit_section",
                name="Edit Section Skill",
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
                description="Deploy change to external system",
                permission_mode="WRITE_PREVIEW",
                is_si_write=True,
            ),
        ),
    )
    catalog = router.build_authorized_catalog(ctx)

    first_res = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="turn-eval-1",
            iteration=0,
            tool_call_id="tc-read-1",
            tool_name=str(case["tool_name"]),
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            user_role=ctx.user_role,
            active_hat=ctx.active_hat,
            arguments={"resource_uri": "orcia://workspace/doc.md", "query": "status"},
        ),
        catalog=catalog,
    )
    assert first_res.verdict == "EXECUTED"
    wrapped = first_res.delimited_output
    assert wrapped.startswith('<untrusted_tool_output tool_call_id="tc-read-1"')
    assert wrapped.endswith("</untrusted_tool_output>")

    inner_body = wrapped.split("\n", 1)[1].rsplit("\n", 1)[0]
    for forbidden in case["forbidden_raw_markers"]:
        assert forbidden not in inner_body
    for expected_tok in case["expected_escaped_tokens"]:
        assert expected_tok in wrapped

    prompt = AssistantHarness().assemble_prompt(
        human_profile_archetype="ARCHITECT",
        user_prompt=f"Summarize evidence cleanly:\n{wrapped}",
        workspace_id=ctx.workspace_id,
        intent="QA",
    )
    assert prompt.layers[0].immutable is True
    assert CONSTITUTIONAL_LAYER_1_TEXT in prompt.system_prompt
    cassette_res = await DeterministicCassetteLLM().complete(
        LlmPromptRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=f"Summarize evidence:\n{wrapped}",
            model_family="openai",
            model_id="gpt-4.1-mini",
        )
    )
    assert CONSTITUTIONAL_LAYER_1_TEXT in prompt.system_prompt
    assert cassette_res.content

    followup = case["followup_tool"]
    follow_res = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="turn-eval-1",
            iteration=1,
            tool_call_id="tc-followup-1",
            tool_name=str(followup["tool_name"]),
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            user_role=ctx.user_role,
            active_hat=ctx.active_hat,
            execution_identity=str(followup.get("execution_identity", "passthrough")),
            arguments=dict(followup.get("arguments", {"query": "Run"})),
        ),
        catalog=catalog,
    )
    assert follow_res.verdict == followup["expected_verdict"]
    assert follow_res.audit_event_type == followup["expected_audit"]
    if follow_res.verdict == "APPROVAL_REQUIRED":
        assert len(outbox_events) == 1
        assert outbox_events[0].event_type == "HumanArbitrationRequested"
