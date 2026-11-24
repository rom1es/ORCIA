"""Agent lifecycle mutation mixin for `AgentsAndSkillsManagementService` (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Literal, cast

from orcia_core.catalog.errors import ValidationDomainError
from orcia_core.orchestration._agents_and_skills_executor import (
    duplicate_agent_into_registry,
    execute_managed_agent,
)
from orcia_core.orchestration.agents_and_skills_models import (
    AgentExecutionOutcome,
    ManagedAgentRecord,
    ManagedSkillRecord,
    rebuild_agent_with_skills,
)

if TYPE_CHECKING:
    from orcia_core.orchestration.agents_and_skills_manager import AgentsAndSkillsManagementService


class AgentLifecycleMethodsMixin:
    """Skill attachment, duplication, enablement & deletion methods for agents."""

    _skills: dict[str, ManagedSkillRecord]
    _agents: dict[str, ManagedAgentRecord]

    def set_agent_skills(
        self,
        agent_id: str,
        *,
        skill_ids: tuple[str, ...] | list[str],
        instance: str | None = None,
    ) -> ManagedAgentRecord:
        svc = cast("AgentsAndSkillsManagementService", self)
        agent = svc.get_agent(agent_id, instance=instance)
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
        svc = cast("AgentsAndSkillsManagementService", self)
        source = svc.get_agent(agent_id, instance=instance)
        return duplicate_agent_into_registry(
            source,
            self._agents,
            new_name=new_name,
            visibility_scope=visibility_scope,
            upsert_fn=svc.upsert_agent,
            instance=instance,
        )

    def set_agent_enabled(
        self,
        agent_id: str,
        *,
        enabled: bool,
        instance: str | None = None,
    ) -> ManagedAgentRecord:
        svc = cast("AgentsAndSkillsManagementService", self)
        agent = svc.get_agent(agent_id, instance=instance)
        updated = rebuild_agent_with_skills(
            replace(agent, enabled_in_workspace=enabled), agent.skill_ids
        )
        self._agents[agent_id] = updated
        return updated

    def set_agent_mcp_exposure(
        self,
        agent_id: str,
        *,
        mcp_exposed: bool,
        instance: str | None = None,
    ) -> ManagedAgentRecord:
        svc = cast("AgentsAndSkillsManagementService", self)
        agent = svc.get_agent(agent_id, instance=instance)
        updated = rebuild_agent_with_skills(
            replace(agent, mcp_exposed=mcp_exposed), agent.skill_ids
        )
        self._agents[agent_id] = updated
        return updated

    def delete_agent(
        self,
        agent_id: str,
        *,
        instance: str | None = None,
    ) -> ManagedAgentRecord:
        svc = cast("AgentsAndSkillsManagementService", self)
        removed = svc.get_agent(agent_id, instance=instance)
        if removed.visibility_scope == "PACK":
            raise ValidationDomainError(
                detail_code="ERR_PACK_SKILL_AGENT_IMMUTABLE", instance=instance
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
        svc = cast("AgentsAndSkillsManagementService", self)
        agent = svc.get_agent(agent_id, instance=instance)
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValidationDomainError(
                detail_code="ERR_AGENT_TEST_PROMPT_REQUIRED", instance=instance
            )
        from orcia_core.orchestration.agents_and_skills_manager import _run_llm_sync

        return execute_managed_agent(
            agent=agent,
            skills_by_id=self._skills,
            agents_by_id=self._agents,
            execute_skill_fn=svc.execute_skill,
            llm=svc._llm,
            router=svc._router,
            clean_prompt=clean_prompt,
            instance=instance,
            llm_response_override=llm_response_override,
            run_llm_fn=_run_llm_sync,
        )


__all__ = ["AgentLifecycleMethodsMixin"]
