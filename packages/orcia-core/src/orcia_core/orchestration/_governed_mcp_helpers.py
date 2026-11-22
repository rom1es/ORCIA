"""Helpers for `GovernedMcpExposureService` (`<= 120 L`, `AD-19`)."""

from __future__ import annotations

from uuid_utils.compat import uuid7

from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.orchestration.remote_test_bench_models import (
    ExposedMcpAgentSpec,
    GovernedMcpInvocationResult,
    McpExposureRegime,
)


def build_mcp_agent_spec(
    *,
    actor_role: str,
    workspace_slug: str,
    agent_slug: str,
    display_name: str,
    mcp_exposed: bool,
    regime: McpExposureRegime,
    system_prompt_layers_1_to_4: str,
    secret_refs: tuple[str, ...],
    human_authored_required: bool,
) -> ExposedMcpAgentSpec:
    if actor_role in ("READ_ONLY_OBSERVER", "OBSERVER"):
        raise ObserverModeReadOnlyError(
            detail_override="READ_ONLY_OBSERVER cannot configure MCP exposure."
        )
    return ExposedMcpAgentSpec(
        agent_slug=agent_slug,
        workspace_slug=workspace_slug,
        display_name=display_name,
        mcp_exposed=mcp_exposed,
        regime=regime,
        system_prompt_layers_1_to_4=system_prompt_layers_1_to_4,
        secret_refs=secret_refs,
        human_authored_required=human_authored_required,
    )


def build_mcp_invocation_result(
    *,
    spec: ExposedMcpAgentSpec | None,
    workspace_slug: str,
    agent_slug: str,
    caller_role: str,
    caller_verbs: set[str],
    passthrough_identity: str,
    prompt_text: str,
    requested_write_target_uri: str | None,
) -> GovernedMcpInvocationResult:
    if not passthrough_identity.strip():
        raise ValidationDomainError(
            detail_override="Passthrough user identity is mandatory for MCP calls (AD-6)."
        )
    if "execute" not in caller_verbs:
        raise ScopeAccessDeniedError(
            detail_override="Caller lacks 'execute' permission on target MCP agent."
        )
    if spec is None or not spec.mcp_exposed:
        raise ValidationDomainError(
            detail_override=f"Agent '{agent_slug}' is not exposed over MCP in '{workspace_slug}'."
        )
    if spec.human_authored_required:
        raise HumanAnchorRequiredError(
            detail_override=(
                f"Agent '{agent_slug}' requires a signed Human Anchor Card (AD-3) and "
                "cannot bypass human authorship over MCP."
            )
        )
    has_read_source = "read" in caller_verbs and caller_role not in (
        "OBSERVER",
        "READ_ONLY_OBSERVER",
        "BU_DIRECTOR",
    )
    scrubbed_prompt = prompt_text.replace("IBAN_SECRET", "[REDACTED_PII]")
    citation_tag = "[S1]" if has_read_source else "[S1 · 🔒 Source restreinte]"
    response_text = (
        f"Réponse gouvernée ({spec.display_name}) sur « {scrubbed_prompt} » {citation_tag}"
    )
    staged_actions: list[str] = []
    if requested_write_target_uri:
        staged_actions.append(f"STAGED_WRITE:{requested_write_target_uri}")
    return GovernedMcpInvocationResult(
        invocation_id=uuid7(),
        tool_name=f"agent.{agent_slug}",
        workspace_slug=workspace_slug,
        passthrough_identity=passthrough_identity,
        sanitized_response_text=response_text,
        system_prompt_exposed=spec.system_prompt_layers_1_to_4 if has_read_source else None,
        secret_refs_exposed=(),
        staged_actions=tuple(staged_actions),
        meta_usage={"prompt_tokens": 64, "completion_tokens": 48, "cost_eur": 0.0005},
        history_badge_fr="💻 Appelé via MCP (IDE)",
        audit_actor_type="MCP_IDE_CLIENT",
    )


def validate_and_invoke_assistant_read_only(
    *,
    spec: ExposedMcpAgentSpec | None,
    workspace_slug: str,
    agent_slug: str,
    caller_role: str,
    passthrough_identity: str,
    prompt_text: str,
) -> GovernedMcpInvocationResult:
    """Validate `CONSULTATION_ANALYSIS` MCP regime & build read-only result for Assistant."""
    if spec is None or not spec.mcp_exposed:
        raise ValidationDomainError(
            detail_override=f"Agent '{agent_slug}' is not exposed over MCP in '{workspace_slug}'."
        )
    if spec.regime != "CONSULTATION_ANALYSIS":
        raise ScopeAccessDeniedError(
            detail_override=(
                f"Agent '{agent_slug}' regime '{spec.regime}' requires Process Write Gate."
            )
        )
    return build_mcp_invocation_result(
        spec=spec,
        workspace_slug=workspace_slug,
        agent_slug=agent_slug,
        caller_role=caller_role,
        caller_verbs={"read", "execute"},
        passthrough_identity=passthrough_identity,
        prompt_text=prompt_text,
        requested_write_target_uri=None,
    )
