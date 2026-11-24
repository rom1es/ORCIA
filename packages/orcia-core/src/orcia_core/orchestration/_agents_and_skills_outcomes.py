"""Execution Outcome Formatters & Agent Skill Rebuilder (`<= 140 L`, `AD-19`)."""

from __future__ import annotations

from dataclasses import replace

from orcia_core.orchestration._agents_and_skills_types import (
    AgentExecutionOutcome,
    InvokedSkillTraceItem,
    ManagedAgentRecord,
    ManagedSkillRecord,
    SkillExecutionOutcome,
    compute_payload_sha256,
)


def rebuild_agent_with_skills(
    agent: ManagedAgentRecord, next_skills: tuple[str, ...]
) -> ManagedAgentRecord:
    """Return a copy of `agent` with updated `skill_ids` and recomputed `sha256`."""
    digest = compute_payload_sha256(
        {
            "agent_id": agent.agent_id,
            "slug": agent.slug,
            "name": agent.name,
            "role_mission": agent.role_mission,
            "instructions": agent.instructions,
            "thinking_level": agent.thinking_level,
            "skill_ids": list(next_skills),
            "version": agent.version,
            "visibility_scope": agent.visibility_scope,
            "source_pack_key": agent.source_pack_key,
            "enabled_in_workspace": agent.enabled_in_workspace,
            "mcp_exposed": agent.mcp_exposed,
            "agent_kind": agent.agent_kind,
            "remote_endpoint_url": agent.remote_endpoint_url,
            "posture": agent.posture,
            "human_partner_role": agent.human_partner_role,
            "llm_model_tier": agent.llm_model_tier,
            "temperature": agent.temperature,
            "max_tokens": agent.max_tokens,
            "prompt_ref": agent.prompt_ref,
            "invocation_modes": list(agent.invocation_modes),
            "dialogue_mechanism": agent.dialogue_mechanism,
            "allowed_rag_sources": list(agent.allowed_rag_sources),
            "ontology_views": list(agent.ontology_views),
            "mcp_tool_permissions": dict(agent.mcp_tool_permissions),
            "guardrails": list(agent.guardrails),
            "output_contract_format": agent.output_contract_format,
            "write_preview_required": agent.write_preview_required,
            "test_bench_validated": agent.test_bench_validated,
        }
    )
    return replace(agent, skill_ids=next_skills, sha256=digest)


def format_skill_execution_outcome(
    skill: ManagedSkillRecord,
    clean_input: str,
    parameters: dict[str, str] | None,
    llm_response_override: str | None,
) -> SkillExecutionOutcome:
    """Build a formatted `SkillExecutionOutcome` from a `ManagedSkillRecord` and input."""
    from orcia_core.orchestration._agents_skills_locales import get_agents_skills_copy

    copy = get_agents_skills_copy()
    provided = {
        str(k).strip(): str(v).strip() for k, v in (parameters or {}).items() if str(k).strip()
    }
    for p in skill.input_parameters:
        provided.setdefault(p, clean_input)
    params_summary = (
        ", ".join(f"{k}={v}" for k, v in provided.items())
        if provided
        else copy.no_additional_params
    )
    res = (
        llm_response_override.strip()
        if llm_response_override and llm_response_override.strip()
        else copy.validated_synthesis_tpl.format(clean_input=clean_input)
    )
    lines = [
        copy.skill_success_tpl.format(name=skill.name, handle=skill.command_handle),
        copy.skill_objective_tpl.format(objective=skill.objective),
        copy.skill_input_tpl.format(clean_input=clean_input),
        copy.skill_params_tpl.format(params_summary=params_summary),
        copy.skill_method_tpl.format(instructions=skill.instructions),
        copy.skill_result_tpl.format(expected_output_format=skill.expected_output_format, res=res),
    ]
    return SkillExecutionOutcome(
        skill_id=skill.skill_id,
        skill_name=skill.name,
        command_handle=skill.command_handle,
        input_text=clean_input,
        applied_parameters=provided,
        output_text="\n".join(lines),
        expected_output_format=skill.expected_output_format,
    )


def format_agent_execution_outcome(
    agent: ManagedAgentRecord,
    clean_prompt: str,
    traces: list[InvokedSkillTraceItem],
    llm_text: str,
) -> AgentExecutionOutcome:
    """Build a formatted `AgentExecutionOutcome` from an Agent, traces, and LLM output."""
    from orcia_core.orchestration._agents_skills_locales import get_agents_skills_copy

    copy = get_agents_skills_copy()
    skills_names = (
        ", ".join(f"{t.skill_name} ({t.command_handle})" for t in traces)
        if traces
        else copy.no_attached_skill
    )
    posture_lbl = (
        copy.posture_evaluator if agent.posture == "EVALUATOR_GATE" else copy.posture_producer
    )
    lines = [
        copy.agent_header_tpl.format(
            name=agent.name, handle=agent.handle, role_mission=agent.role_mission
        ),
        copy.agent_posture_tpl.format(
            posture_lbl=posture_lbl,
            human_partner_role=agent.human_partner_role,
            output_contract_format=agent.output_contract_format,
        ),
        copy.agent_engine_tpl.format(
            llm_model_tier=agent.llm_model_tier,
            thinking_level=agent.thinking_level,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
        ),
        copy.agent_prompt_tpl.format(clean_prompt=clean_prompt),
        copy.agent_skills_tpl.format(count=len(traces), skills_names=skills_names),
        copy.agent_synthesis_tpl.format(
            instructions=agent.instructions, clean_prompt=clean_prompt, llm_text=llm_text
        ),
    ]
    return AgentExecutionOutcome(
        agent_id=agent.agent_id,
        agent_name=agent.name,
        agent_handle=agent.handle,
        thinking_level=agent.thinking_level,
        prompt=clean_prompt,
        response_text="\n".join(lines),
        invoked_skills=tuple(traces),
    )


__all__ = [
    "format_agent_execution_outcome",
    "format_skill_execution_outcome",
    "rebuild_agent_with_skills",
]
