"""Execution helper extracted from `agents_and_skills_manager.py`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from orcia_core.catalog.errors import ValidationDomainError
from orcia_core.orchestration._agents_skills_locales import get_agents_skills_copy
from orcia_core.orchestration.agents_and_skills_models import (
    AgentExecutionOutcome,
    InvokedSkillTraceItem,
    ManagedAgentRecord,
    ManagedSkillRecord,
    SkillExecutionOutcome,
    format_agent_execution_outcome,
    normalize_identifier_slug,
    rebuild_agent_with_skills,
)
from orcia_kernel.ports import LLMPort, LlmPromptRequest


def execute_managed_agent(
    *,
    agent: ManagedAgentRecord,
    skills_by_id: dict[str, ManagedSkillRecord],
    agents_by_id: dict[str, ManagedAgentRecord],
    execute_skill_fn: Callable[..., SkillExecutionOutcome],
    llm: LLMPort | None,
    router: Any | None,
    clean_prompt: str,
    instance: str | None,
    llm_response_override: str | None,
    run_llm_fn: Callable[[LLMPort, LlmPromptRequest], str],
) -> AgentExecutionOutcome:
    """Execute a `ManagedAgentRecord` with bound skills and governed LLM resolution."""
    copy = get_agents_skills_copy()
    traces = [
        InvokedSkillTraceItem(
            skill_id=s.skill_id,
            skill_name=s.name,
            command_handle=s.command_handle,
            output_summary=copy.agent_trace_tpl.format(
                name=s.name,
                handle=s.command_handle,
                expected_output_format=s.expected_output_format,
                clean_prompt=clean_prompt,
            ),
        )
        for sid in agent.skill_ids
        if (s := skills_by_id.get(sid)) is not None
        and execute_skill_fn(sid, input_text=clean_prompt, instance=instance)
    ]
    skills_block = (
        "\n".join(f"- {t.output_summary}" for t in traces)
        if traces
        else copy.no_external_skill_used
    )
    model_family = ""
    model_id = ""
    tier = (
        agent.llm_model_tier
        if agent.llm_model_tier in ("simple", "medium", "complex")
        else "medium"
    )
    if router is not None:
        try:
            resolved = router.resolve_mapping(scope_id="", tier=tier, effort="default")
            model_family = resolved.model_family
            model_id = resolved.model_name
        except Exception:
            pass

    if llm_response_override and llm_response_override.strip():
        llm_text = llm_response_override.strip()
    else:
        if not model_family or not model_id:
            if bool(getattr(llm, "is_cassette_adapter", False)):
                model_family = "cassette"
                model_id = f"cassette/{agent.slug}"
            else:
                from orcia_core.orchestration.errors import TierModelNotConfiguredError

                raise TierModelNotConfiguredError(
                    inference_tier=tier,
                    instance=f"agent_manager:{agent.slug}",
                )
        if llm is None:
            from orcia_core.orchestration.errors import TierModelNotConfiguredError

            raise TierModelNotConfiguredError(
                inference_tier=tier,
                instance=f"agent_manager:{agent.slug}",
            )
        llm_text = run_llm_fn(
            llm,
            LlmPromptRequest(
                system_prompt=copy.agent_system_tpl.format(
                    name=agent.name,
                    handle=agent.handle,
                    role_mission=agent.role_mission,
                    posture=agent.posture,
                    instructions=agent.instructions,
                ),
                user_prompt=copy.agent_user_tpl.format(
                    clean_prompt=clean_prompt, skills_block=skills_block
                ),
                model_family=model_family,
                model_id=model_id,
                execution_mode="COACHING",
                metadata={"agent_id": agent.agent_id, "thinking_level": agent.thinking_level},
            ),
        )
    validated_agent = rebuild_agent_with_skills(
        replace(agent, test_bench_validated=True), agent.skill_ids
    )
    agents_by_id[agent.agent_id] = validated_agent
    return format_agent_execution_outcome(validated_agent, clean_prompt, traces, llm_text)


def duplicate_agent_into_registry(
    source: ManagedAgentRecord,
    agents_by_id: dict[str, ManagedAgentRecord],
    *,
    new_name: str | None,
    visibility_scope: Any,
    upsert_fn: Callable[..., ManagedAgentRecord],
    instance: str | None,
) -> ManagedAgentRecord:
    """Duplicate a managed agent (`TEAM` or `PRIVATE`) with unique slug & copied metadata."""
    resolved_name = (new_name or "").strip() or (
        f"{source.name} {get_agents_skills_copy().copy_suffix}"
    )
    base_slug = normalize_identifier_slug(resolved_name, fallback_prefix="agent")
    candidate_id, suffix = f"agent-{base_slug}", 2
    while candidate_id in agents_by_id:
        candidate_id = f"agent-{base_slug}-{suffix}"
        suffix += 1
    return upsert_fn(
        agent_id=candidate_id,
        name=resolved_name,
        role_mission=source.role_mission,
        instructions=source.instructions,
        thinking_level=source.thinking_level,
        skill_ids=source.skill_ids,
        visibility_scope=visibility_scope,
        source_pack_key=source.source_pack_key,
        enabled_in_workspace=True,
        mcp_exposed=False,
        agent_kind=source.agent_kind,
        remote_endpoint_url=source.remote_endpoint_url,
        posture=source.posture,
        human_partner_role=source.human_partner_role,
        llm_model_tier=source.llm_model_tier,
        temperature=source.temperature,
        max_tokens=source.max_tokens,
        prompt_ref=source.prompt_ref,
        invocation_modes=source.invocation_modes,
        dialogue_mechanism=source.dialogue_mechanism,
        allowed_rag_sources=source.allowed_rag_sources,
        ontology_views=source.ontology_views,
        mcp_tool_permissions=source.mcp_tool_permissions,
        guardrails=source.guardrails,
        output_contract_format=source.output_contract_format,
        write_preview_required=source.write_preview_required,
        test_bench_validated=source.test_bench_validated,
        instance=instance,
    )


def delete_skill_from_registries(
    removed: ManagedSkillRecord,
    skills: dict[str, ManagedSkillRecord],
    agents: dict[str, ManagedAgentRecord],
    *,
    instance: str | None,
) -> tuple[ManagedSkillRecord, tuple[str, ...]]:
    """Remove non-pack skill and unlink it from all registered agents."""
    if removed.visibility_scope == "PACK":
        raise ValidationDomainError(detail_code="ERR_PACK_SKILL_AGENT_IMMUTABLE", instance=instance)
    del skills[removed.skill_id]
    updated_agent_ids: list[str] = []
    for aid, agent in list(agents.items()):
        if removed.skill_id in agent.skill_ids:
            next_skills = tuple(sid for sid in agent.skill_ids if sid != removed.skill_id)
            agents[aid] = rebuild_agent_with_skills(agent, next_skills)
            updated_agent_ids.append(aid)
    return removed, tuple(updated_agent_ids)


def normalize_agent_upsert_lists(
    *,
    skill_ids: tuple[str, ...] | list[str],
    valid_skills_map: dict[str, ManagedSkillRecord],
    invocation_modes: tuple[str, ...] | list[str] | None,
    allowed_rag_sources: tuple[str, ...] | list[str] | None,
    ontology_views: tuple[str, ...] | list[str] | None,
    mcp_tool_permissions: dict[str, str] | tuple[tuple[str, str], ...] | None,
    guardrails: tuple[str, ...] | list[str] | None,
    prompt_ref: str | None,
) -> tuple[
    tuple[str, ...],
    str | None,
    tuple[str, ...] | None,
    tuple[str, ...] | None,
    tuple[str, ...] | None,
    tuple[tuple[str, str], ...] | None,
    tuple[str, ...] | None,
]:
    """Normalize optional tuple and permission inputs for agent upsert."""
    valid_skills = tuple(
        dict.fromkeys(sid.strip() for sid in skill_ids if sid.strip() in valid_skills_map)
    )
    norm_perms: tuple[tuple[str, str], ...] | None = None
    if mcp_tool_permissions is not None:
        items = (
            mcp_tool_permissions.items()
            if isinstance(mcp_tool_permissions, dict)
            else mcp_tool_permissions
        )
        norm_perms = tuple((str(k).strip(), str(v).strip()) for k, v in items if str(k).strip())

    def _clean(raw: tuple[str, ...] | list[str] | None) -> tuple[str, ...] | None:
        return tuple(str(x).strip() for x in raw if str(x).strip()) if raw is not None else None

    clean_prompt_ref = prompt_ref.strip() if prompt_ref and prompt_ref.strip() else None
    return (
        valid_skills,
        clean_prompt_ref,
        _clean(invocation_modes),
        _clean(allowed_rag_sources),
        _clean(ontology_views),
        norm_perms,
        _clean(guardrails),
    )


__all__ = [
    "delete_skill_from_registries",
    "duplicate_agent_into_registry",
    "execute_managed_agent",
    "normalize_agent_upsert_lists",
]
