"""User-centered Agents & Skills Creation, 1-Click Attachment & Direct Execution Service.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
Starts 100% empty at Day 0 (`0` fictional agents, `0` fictional skills) and persists
via `sql_agents_and_skills.py` when PostgreSQL 18 is available.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any

from orcia_core.orchestration._agents_and_skills_executor import (
    delete_skill_from_registries,
    normalize_agent_upsert_lists,
)
from orcia_core.orchestration._agents_and_skills_executor import (
    require_non_empty_field as _require_non_empty,
)
from orcia_core.orchestration._agents_and_skills_mixin import AgentLifecycleMethodsMixin
from orcia_core.orchestration._agents_and_skills_outcomes import ensure_agent_ready_for_activation
from orcia_core.orchestration._agents_namespacing import annotate_skills_and_agents_namespacing
from orcia_core.orchestration._agents_skills_locales import get_agents_skills_copy
from orcia_core.orchestration.agents_and_skills_models import (
    AgentDialogueMechanism,
    AgentExecutionOutcome,
    AgentHumanPartnerRole,
    AgentInvocationMode,
    AgentKindType,
    AgentLifecycleStatus,
    AgentLlmModelTier,
    AgentOutputContractFormat,
    AgentPostureType,
    AgentSkillVisibilityScope,
    AgentTestBenchStatus,
    AgentThinkingLevel,
    InvokedSkillTraceItem,
    ManagedAgentRecord,
    ManagedSkillRecord,
    McpToolPermissionMode,
    SkillExecutionOutcome,
    build_managed_agent_record,
    build_managed_skill_record,
    compute_payload_sha256,
    format_skill_execution_outcome,
    normalize_identifier_slug,
)
from orcia_core.orchestration.errors import AgentDraftLifecycleBlockedError
from orcia_kernel.errors import ResourceNotFoundError
from orcia_kernel.ports import LLMPort, LlmPromptRequest


def _run_llm_sync(llm: LLMPort, request: LlmPromptRequest) -> str:
    """Execute `llm.complete(request)` safely from both sync and async calling contexts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(llm.complete(request)).content
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(llm.complete(request)).content).result()


class AgentsAndSkillsManagementService(AgentLifecycleMethodsMixin):
    """Domain service for creating, linking, and executing Skills and Agents (`🤖 Mes Agents`)."""

    def __init__(
        self,
        *,
        llm_gateway: LLMPort | None = None,
        cognitive_router: Any | None = None,
    ) -> None:
        self._llm: LLMPort | None = llm_gateway
        self._router = cognitive_router
        self._skills: dict[str, ManagedSkillRecord] = {}
        self._agents: dict[str, ManagedAgentRecord] = {}

    @property
    def skills(self) -> tuple[ManagedSkillRecord, ...]:
        return tuple(self._skills.values())

    @property
    def agents(self) -> tuple[ManagedAgentRecord, ...]:
        return tuple(self._agents.values())

    def sync_from_records(
        self,
        *,
        skills: tuple[ManagedSkillRecord, ...],
        agents: tuple[ManagedAgentRecord, ...],
        active_pack_priorities: dict[str, int] | None = None,
    ) -> None:
        ann_skills, ann_agents = annotate_skills_and_agents_namespacing(
            skills, agents, active_pack_priorities=active_pack_priorities
        )
        valid_ids = {s.skill_id for s in ann_skills}
        self._skills = {s.skill_id: s for s in ann_skills}
        self._agents = {
            a.agent_id: replace(a, skill_ids=tuple(sid for sid in a.skill_ids if sid in valid_ids))
            for a in ann_agents
        }

    def get_skill(self, skill_id: str, *, instance: str | None = None) -> ManagedSkillRecord:
        skill = self._skills.get(skill_id)
        if skill is None:
            raise ResourceNotFoundError(instance=instance)
        return skill

    def get_agent(self, agent_id: str, *, instance: str | None = None) -> ManagedAgentRecord:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ResourceNotFoundError(instance=instance)
        return agent

    def upsert_skill(
        self,
        *,
        name: str,
        objective: str,
        input_parameters: tuple[str, ...] | list[str] = (),
        instructions: str,
        expected_output_format: str | None = None,
        skill_id: str | None = None,
        version: str = "1.0.0",
        visibility_scope: AgentSkillVisibilityScope | None = None,
        source_pack_key: str | None = None,
        enabled_in_workspace: bool | None = None,
        instance: str | None = None,
    ) -> ManagedSkillRecord:
        clean_name = _require_non_empty(name, "ERR_SKILL_NAME_REQUIRED", instance)
        clean_obj = _require_non_empty(objective, "ERR_SKILL_OBJECTIVE_REQUIRED", instance)
        clean_inst = _require_non_empty(instructions, "ERR_SKILL_INSTRUCTIONS_REQUIRED", instance)
        default_fmt = get_agents_skills_copy().default_output_format
        slug = normalize_identifier_slug(clean_name, fallback_prefix="skill")
        resolved_id = (skill_id or "").strip() or f"skill-{slug}"
        record = build_managed_skill_record(
            resolved_id=resolved_id,
            slug=slug,
            clean_name=clean_name,
            clean_obj=clean_obj,
            params=tuple(dict.fromkeys(p.strip() for p in input_parameters if p.strip())),
            clean_inst=clean_inst,
            clean_fmt=(expected_output_format or "").strip() or default_fmt,
            version=version,
            existing=self._skills.get(resolved_id),
            visibility_scope=visibility_scope,
            source_pack_key=source_pack_key,
            enabled_in_workspace=enabled_in_workspace,
        )
        self._skills[resolved_id] = record
        return record

    def delete_skill(
        self, skill_id: str, *, instance: str | None = None
    ) -> tuple[ManagedSkillRecord, tuple[str, ...]]:
        removed = self.get_skill(skill_id, instance=instance)
        return delete_skill_from_registries(removed, self._skills, self._agents, instance=instance)

    def execute_skill(
        self,
        skill_id: str,
        *,
        input_text: str,
        parameters: dict[str, str] | None = None,
        instance: str | None = None,
        llm_response_override: str | None = None,
    ) -> SkillExecutionOutcome:
        skill = self.get_skill(skill_id, instance=instance)
        clean_input = _require_non_empty(input_text, "ERR_SKILL_TEST_INPUT_REQUIRED", instance)
        return format_skill_execution_outcome(skill, clean_input, parameters, llm_response_override)

    def upsert_agent(
        self,
        *,
        name: str,
        role_mission: str,
        instructions: str,
        thinking_level: AgentThinkingLevel = "medium",
        skill_ids: tuple[str, ...] | list[str] = (),
        agent_id: str | None = None,
        version: str = "1.0.0",
        visibility_scope: AgentSkillVisibilityScope | None = None,
        source_pack_key: str | None = None,
        enabled_in_workspace: bool | None = None,
        mcp_exposed: bool | None = None,
        agent_kind: AgentKindType | None = None,
        remote_endpoint_url: str | None = None,
        posture: AgentPostureType | None = None,
        human_partner_role: AgentHumanPartnerRole | None = None,
        llm_model_tier: AgentLlmModelTier | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        prompt_ref: str | None = None,
        invocation_modes: tuple[str, ...] | list[str] | None = None,
        dialogue_mechanism: AgentDialogueMechanism | None = None,
        allowed_rag_sources: tuple[str, ...] | list[str] | None = None,
        ontology_views: tuple[str, ...] | list[str] | None = None,
        mcp_tool_permissions: dict[str, str] | tuple[tuple[str, str], ...] | None = None,
        guardrails: tuple[str, ...] | list[str] | None = None,
        output_contract_format: AgentOutputContractFormat | None = None,
        write_preview_required: bool | None = None,
        test_bench_validated: bool | None = None,
        lifecycle_status: AgentLifecycleStatus | None = None,
        test_bench_status: AgentTestBenchStatus | None = None,
        instance: str | None = None,
    ) -> ManagedAgentRecord:
        clean_name = _require_non_empty(name, "ERR_AGENT_NAME_REQUIRED", instance)
        clean_role = _require_non_empty(role_mission, "ERR_AGENT_ROLE_REQUIRED", instance)
        clean_inst = _require_non_empty(instructions, "ERR_AGENT_INSTRUCTIONS_REQUIRED", instance)
        slug = normalize_identifier_slug(clean_name, fallback_prefix="agent")
        resolved_id = (agent_id or "").strip() or f"agent-{slug}"
        normalized = normalize_agent_upsert_lists(
            skill_ids=skill_ids,
            valid_skills_map=self._skills,
            invocation_modes=invocation_modes,
            allowed_rag_sources=allowed_rag_sources,
            ontology_views=ontology_views,
            mcp_tool_permissions=mcp_tool_permissions,
            guardrails=guardrails,
            prompt_ref=prompt_ref,
        )
        valid_skills, clean_prompt_ref, clean_modes, clean_sources = normalized[:4]
        clean_views, norm_perms, clean_guardrails = normalized[4:]
        record = build_managed_agent_record(
            resolved_id=resolved_id,
            slug=slug,
            clean_name=clean_name,
            clean_role=clean_role,
            clean_inst=clean_inst,
            thinking_level=thinking_level,
            valid_skills=valid_skills,
            version=version,
            existing=self._agents.get(resolved_id),
            visibility_scope=visibility_scope,
            source_pack_key=source_pack_key,
            enabled_in_workspace=enabled_in_workspace,
            mcp_exposed=mcp_exposed,
            agent_kind=agent_kind,
            remote_endpoint_url=remote_endpoint_url,
            posture=posture,
            human_partner_role=human_partner_role,
            llm_model_tier=llm_model_tier,
            temperature=temperature,
            max_tokens=max_tokens,
            prompt_ref=clean_prompt_ref,
            invocation_modes=clean_modes,
            dialogue_mechanism=dialogue_mechanism,
            allowed_rag_sources=clean_sources,
            ontology_views=clean_views,
            mcp_tool_permissions=norm_perms,
            guardrails=clean_guardrails,
            output_contract_format=output_contract_format,
            write_preview_required=write_preview_required,
            test_bench_validated=test_bench_validated,
            lifecycle_status=lifecycle_status,
            test_bench_status=test_bench_status,
        )
        if record.lifecycle_status == "ACTIVE":
            ensure_agent_ready_for_activation(record, instance=instance)
        if record.mcp_exposed and record.lifecycle_status == "DRAFT":
            raise AgentDraftLifecycleBlockedError(
                detail_code="ERR_DRAFT_AGENT_CANNOT_EXPOSE_MCP",
                detail_params={"agent_name": record.name},
                instance=instance,
            )
        self._agents[resolved_id] = record
        return record


__all__ = [
    "AgentDialogueMechanism",
    "AgentExecutionOutcome",
    "AgentHumanPartnerRole",
    "AgentInvocationMode",
    "AgentKindType",
    "AgentLifecycleStatus",
    "AgentLlmModelTier",
    "AgentOutputContractFormat",
    "AgentPostureType",
    "AgentSkillVisibilityScope",
    "AgentTestBenchStatus",
    "AgentThinkingLevel",
    "AgentsAndSkillsManagementService",
    "InvokedSkillTraceItem",
    "ManagedAgentRecord",
    "ManagedSkillRecord",
    "McpToolPermissionMode",
    "SkillExecutionOutcome",
    "compute_payload_sha256",
    "normalize_identifier_slug",
]
