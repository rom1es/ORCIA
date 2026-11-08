"""User-centered Agents & Skills Creation, 1-Click Attachment & Direct Execution Service.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
Starts 100% empty at Day 0 (`0` fictional agents, `0` fictional skills) and persists
via `sql_agents_and_skills.py` when PostgreSQL 18 is available.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Literal

from orcia_core.catalog.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.orchestration.agents_and_skills_models import (
    AgentExecutionOutcome,
    AgentKindType,
    AgentSkillVisibilityScope,
    AgentThinkingLevel,
    InvokedSkillTraceItem,
    ManagedAgentRecord,
    ManagedSkillRecord,
    SkillExecutionOutcome,
    build_managed_agent_record,
    build_managed_skill_record,
    compute_payload_sha256,
    format_agent_execution_outcome,
    format_skill_execution_outcome,
    normalize_identifier_slug,
    rebuild_agent_with_skills,
)
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.ports import LLMPort, LlmPromptRequest

_PACK_IMMUTABILITY_ERROR_MSG = (
    "Les agents et compétences issus d'un Pack Métier ne peuvent pas être supprimés ; "
    "vous pouvez les désactiver sur l'espace ou les dupliquer pour les personnaliser."
)


def _run_llm_sync(llm: LLMPort, request: LlmPromptRequest) -> str:
    """Execute `llm.complete(request)` safely from both sync and async calling contexts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(llm.complete(request)).content
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(llm.complete(request)).content).result()


def _require_non_empty(value: str, detail_msg: str, instance: str | None) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationDomainError(detail_override=detail_msg, instance=instance)
    return cleaned


class AgentsAndSkillsManagementService:
    """Domain service for creating, linking, and executing Skills and Agents (`🤖 Mes Agents`)."""

    def __init__(self, *, llm_gateway: LLMPort | None = None) -> None:
        self._llm: LLMPort = llm_gateway or DeterministicCassetteLLM()
        self._skills: dict[str, ManagedSkillRecord] = {}
        self._agents: dict[str, ManagedAgentRecord] = {}

    @property
    def skills(self) -> tuple[ManagedSkillRecord, ...]:
        return tuple(self._skills.values())

    @property
    def agents(self) -> tuple[ManagedAgentRecord, ...]:
        return tuple(self._agents.values())

    def sync_from_records(
        self, *, skills: tuple[ManagedSkillRecord, ...], agents: tuple[ManagedAgentRecord, ...]
    ) -> None:
        valid_ids = {s.skill_id for s in skills}
        self._skills = {s.skill_id: s for s in skills}
        self._agents = {
            a.agent_id: replace(a, skill_ids=tuple(sid for sid in a.skill_ids if sid in valid_ids))
            for a in agents
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
        expected_output_format: str = "Synthèse structurée",
        skill_id: str | None = None,
        version: str = "1.0.0",
        visibility_scope: AgentSkillVisibilityScope | None = None,
        source_pack_key: str | None = None,
        enabled_in_workspace: bool | None = None,
        instance: str | None = None,
    ) -> ManagedSkillRecord:
        clean_name = _require_non_empty(name, "Le nom de la compétence est obligatoire.", instance)
        clean_obj = _require_non_empty(
            objective, "L'objectif métier de la compétence est obligatoire.", instance
        )
        clean_inst = _require_non_empty(
            instructions,
            "Les instructions d'exécution de la compétence sont obligatoires.",
            instance,
        )
        slug = normalize_identifier_slug(clean_name, fallback_prefix="skill")
        resolved_id = (skill_id or "").strip() or f"skill-{slug}"
        record = build_managed_skill_record(
            resolved_id=resolved_id,
            slug=slug,
            clean_name=clean_name,
            clean_obj=clean_obj,
            params=tuple(dict.fromkeys(p.strip() for p in input_parameters if p.strip())),
            clean_inst=clean_inst,
            clean_fmt=expected_output_format.strip() or "Synthèse structurée",
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
        if removed.visibility_scope == "PACK":
            raise ValidationDomainError(
                detail_override=_PACK_IMMUTABILITY_ERROR_MSG, instance=instance
            )
        del self._skills[skill_id]
        updated_agent_ids: list[str] = []
        for aid, agent in list(self._agents.items()):
            if skill_id in agent.skill_ids:
                next_skills = tuple(sid for sid in agent.skill_ids if sid != skill_id)
                self._agents[aid] = rebuild_agent_with_skills(agent, next_skills)
                updated_agent_ids.append(aid)
        return removed, tuple(updated_agent_ids)

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
        clean_input = _require_non_empty(
            input_text, "Veuillez saisir une entrée de test pour exécuter la compétence.", instance
        )
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
        instance: str | None = None,
    ) -> ManagedAgentRecord:
        clean_name = _require_non_empty(name, "Le nom de l'agent est obligatoire.", instance)
        clean_role = _require_non_empty(
            role_mission, "Le rôle et la mission de l'agent sont obligatoires.", instance
        )
        clean_inst = _require_non_empty(
            instructions, "Les instructions de l'agent sont obligatoires.", instance
        )
        slug = normalize_identifier_slug(clean_name, fallback_prefix="agent")
        resolved_id = (agent_id or "").strip() or f"agent-{slug}"
        valid_skills = tuple(
            dict.fromkeys(sid.strip() for sid in skill_ids if sid.strip() in self._skills)
        )
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
        )
        self._agents[resolved_id] = record
        return record

    def set_agent_skills(
        self, agent_id: str, *, skill_ids: tuple[str, ...] | list[str], instance: str | None = None
    ) -> ManagedAgentRecord:
        agent = self.get_agent(agent_id, instance=instance)
        valid = tuple(
            dict.fromkeys(sid.strip() for sid in skill_ids if sid.strip() in self._skills)
        )
        updated = rebuild_agent_with_skills(agent, valid)
        self._agents[agent_id] = updated
        return updated

    def duplicate_agent(
        self,
        agent_id: str,
        *,
        new_name: str | None = None,
        visibility_scope: Literal["PRIVATE", "TEAM"] = "TEAM",
        instance: str | None = None,
    ) -> ManagedAgentRecord:
        source = self.get_agent(agent_id, instance=instance)
        resolved_name = (new_name or "").strip() or f"{source.name} (Copie)"
        base_slug = normalize_identifier_slug(resolved_name, fallback_prefix="agent")
        candidate_id, suffix = f"agent-{base_slug}", 2
        while candidate_id in self._agents:
            candidate_id = f"agent-{base_slug}-{suffix}"
            suffix += 1
        return self.upsert_agent(
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
            instance=instance,
        )

    def set_agent_enabled(
        self, agent_id: str, *, enabled: bool, instance: str | None = None
    ) -> ManagedAgentRecord:
        agent = self.get_agent(agent_id, instance=instance)
        updated = rebuild_agent_with_skills(
            replace(agent, enabled_in_workspace=enabled), agent.skill_ids
        )
        self._agents[agent_id] = updated
        return updated

    def set_agent_mcp_exposure(
        self, agent_id: str, *, mcp_exposed: bool, instance: str | None = None
    ) -> ManagedAgentRecord:
        agent = self.get_agent(agent_id, instance=instance)
        updated = rebuild_agent_with_skills(
            replace(agent, mcp_exposed=mcp_exposed), agent.skill_ids
        )
        self._agents[agent_id] = updated
        return updated

    def delete_agent(self, agent_id: str, *, instance: str | None = None) -> ManagedAgentRecord:
        removed = self.get_agent(agent_id, instance=instance)
        if removed.visibility_scope == "PACK":
            raise ValidationDomainError(
                detail_override=_PACK_IMMUTABILITY_ERROR_MSG, instance=instance
            )
        del self._agents[agent_id]
        return removed

    def execute_agent(
        self,
        agent_id: str,
        *,
        prompt: str,
        instance: str | None = None,
        llm_response_override: str | None = None,
    ) -> AgentExecutionOutcome:
        agent = self.get_agent(agent_id, instance=instance)
        clean_prompt = _require_non_empty(
            prompt, "Veuillez saisir une demande pour tester l'agent.", instance
        )
        traces = [
            InvokedSkillTraceItem(
                skill_id=s.skill_id,
                skill_name=s.name,
                command_handle=s.command_handle,
                output_summary=(
                    f"{s.name} ({s.command_handle}) -> "
                    f"{s.expected_output_format} produit pour « {clean_prompt} »"
                ),
            )
            for sid in agent.skill_ids
            if (s := self._skills.get(sid)) is not None
            and self.execute_skill(sid, input_text=clean_prompt, instance=instance)
        ]
        skills_block = (
            "\n".join(f"- {t.output_summary}" for t in traces)
            if traces
            else "Aucune compétence externe mobilisée."
        )
        llm_text = (
            llm_response_override.strip()
            if llm_response_override and llm_response_override.strip()
            else _run_llm_sync(
                self._llm,
                LlmPromptRequest(
                    system_prompt=(
                        f"Agent: {agent.name} ({agent.handle}) | Rôle: {agent.role_mission} | "
                        f"Instructions: {agent.instructions}"
                    ),
                    user_prompt=f"Demande: {clean_prompt}\nCompétences: {skills_block}",
                    model_family="anthropic",
                    model_id="anthropic/claude-3-7-sonnet",
                    execution_mode="COACHING",
                    metadata={"agent_id": agent.agent_id, "thinking_level": agent.thinking_level},
                ),
            )
        )
        return format_agent_execution_outcome(agent, clean_prompt, traces, llm_text)


__all__ = [
    "AgentExecutionOutcome",
    "AgentKindType",
    "AgentSkillVisibilityScope",
    "AgentThinkingLevel",
    "AgentsAndSkillsManagementService",
    "InvokedSkillTraceItem",
    "ManagedAgentRecord",
    "ManagedSkillRecord",
    "SkillExecutionOutcome",
    "compute_payload_sha256",
    "normalize_identifier_slug",
]
