"""Lifecycle & DRAFT Gating Guards for Managed Agents across Assistant, Processes & MCP."""

from __future__ import annotations

import re

from fastapi import Request

from orcia_api.dependencies import get_agents_and_skills_service
from orcia_api.routers._agents_and_skills_helpers import sync_from_postgres18_if_enabled
from orcia_core.domain.namespacing import parse_qualified_entity_ref
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration import ManagedAgentRecord
from orcia_core.orchestration._agents_namespacing import resolve_agent_reference
from orcia_core.orchestration.errors import AgentDraftLifecycleBlockedError
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2
from orcia_kernel.errors import ValidationDomainError

logger = get_logger("orcia.api.agents_lifecycle_guards")
_MENTION_HANDLE_RE = re.compile(r"(?:^|\s)@([a-zA-Z0-9_/-]+(?::[a-zA-Z0-9_.-]+)?)")


def _normalize_agent_ref_token(raw_ref: str) -> str:
    cleaned = raw_ref.strip().lower()
    cleaned = cleaned.split("#", 1)[0]
    if cleaned.endswith(".md"):
        cleaned = cleaned[:-3]
    if "/" in cleaned and not cleaned.startswith(("orcia://", "pack://")):
        return cleaned.lstrip("@")
    return cleaned.lstrip("@")


def _match_managed_agent(
    agents: tuple[ManagedAgentRecord, ...], raw_ref: str
) -> ManagedAgentRecord | None:
    cleaned = raw_ref.strip()
    if not cleaned:
        return None
    if not cleaned.startswith(("@", "/", "orcia://", "pack://")) and "/" in cleaned:
        cleaned = f"@{cleaned}"
    if cleaned.endswith(".md"):
        cleaned = cleaned[:-3]
    try:
        parsed = parse_qualified_entity_ref(cleaned, default_kind="agents")
    except (ValidationDomainError, ValueError) as exc:
        logger.warning(
            "agent_ref_parse_fallback",
            ref=cleaned,
            error_type=type(exc).__name__,
        )
        parsed = None
    if parsed is not None and parsed.is_qualified:
        resolved = resolve_agent_reference(agents, cleaned)
        if resolved is not None and isinstance(resolved.winner.payload, ManagedAgentRecord):
            return resolved.winner.payload
        return None
    token = _normalize_agent_ref_token(raw_ref)
    if not token:
        return None
    for agent in agents:
        lowered_id = agent.agent_id.lower()
        if token in (
            agent.slug.lower(),
            lowered_id,
            lowered_id.removeprefix("agent-"),
            agent.handle.lstrip("@").lower(),
            f"agent-{agent.slug.lower()}",
        ):
            return agent
    return None


async def enforce_active_agents_for_assistant_prompt(
    request: Request,
    user_prompt: str,
    *,
    instance: str | None = None,
) -> None:
    """Reject `@agent` mentions targeting a DRAFT agent in `Mon Assistant` (`HTTP 422`)."""
    resolved_instance = instance or str(request.url.path)
    tokens = _MENTION_HANDLE_RE.findall(user_prompt or "")
    if not tokens:
        return
    svc = get_agents_and_skills_service(request)
    await sync_from_postgres18_if_enabled(request, svc)
    agents = svc.agents
    for raw_token in tokens:
        matched = _match_managed_agent(agents, raw_token)
        if matched is not None and matched.lifecycle_status == "DRAFT":
            raise AgentDraftLifecycleBlockedError(
                detail_code="ERR_DRAFT_AGENT_INVOCATION_BLOCKED",
                detail_params={"agent_name": matched.name, "agent_handle": matched.handle},
                instance=resolved_instance,
            )


async def enforce_active_agents_for_refs(
    request: Request,
    refs: list[str] | tuple[str, ...],
    *,
    instance: str | None = None,
) -> None:
    """Reject execution, workflow, or MCP actions targeting any DRAFT agent (`HTTP 422`)."""
    clean_refs = [r for r in refs if r and r.strip()]
    if not clean_refs:
        return
    resolved_instance = instance or str(request.url.path)
    svc = get_agents_and_skills_service(request)
    await sync_from_postgres18_if_enabled(request, svc)
    agents = svc.agents
    for raw_ref in clean_refs:
        matched = _match_managed_agent(agents, raw_ref)
        if matched is not None and matched.lifecycle_status == "DRAFT":
            raise AgentDraftLifecycleBlockedError(
                detail_code="ERR_DRAFT_AGENT_INVOCATION_BLOCKED",
                detail_params={"agent_name": matched.name, "agent_handle": matched.handle},
                instance=resolved_instance,
            )


async def enforce_active_agents_for_workflow(
    request: Request,
    workflow: WorkflowDefinitionV2,
    *,
    instance: str,
) -> None:
    """Reject Process execution/save referencing a DRAFT primary or delegate agent (`HTTP 422`)."""
    refs: list[str] = []
    if workflow.global_system_prompt_or_ref:
        refs.append(workflow.global_system_prompt_or_ref)
    if workflow.knowledge_feedback_target_agent:
        refs.append(workflow.knowledge_feedback_target_agent)
    refs.extend(workflow.allowed_delegate_agents)
    for step in workflow.sub_steps:
        if step.instruction_prompt_or_ref:
            refs.append(step.instruction_prompt_or_ref)
    for nd_gate in workflow.controls.non_deterministic:
        if nd_gate.agent_ref:
            refs.append(nd_gate.agent_ref)
    await enforce_active_agents_for_refs(request, refs, instance=instance)


__all__ = [
    "enforce_active_agents_for_assistant_prompt",
    "enforce_active_agents_for_refs",
    "enforce_active_agents_for_workflow",
]
