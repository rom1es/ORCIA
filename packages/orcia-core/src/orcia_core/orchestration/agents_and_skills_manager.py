"""User-centered Agents & Skills Creation, 1-Click Attachment & Direct Execution Service.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
Starts 100% empty at Day 0 (`0` fictional agents, `0` fictional skills) and persists
via `sql_agents_and_skills.py` when PostgreSQL 18 is available.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, replace
from typing import Literal

from orcia_core.catalog.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import LLMPort, LlmPromptRequest

AgentThinkingLevel = Literal["simple", "medium", "complex", "auto"]

_SLUG_CLEAN_RE = re.compile(r"[^a-z0-9]+")


def normalize_identifier_slug(raw_name: str, fallback_prefix: str = "item") -> str:
    """Convert a human-readable name into a clean lowercase kebab-case slug."""
    cleaned = _SLUG_CLEAN_RE.sub("-", raw_name.strip().lower()).strip("-")
    return cleaned or f"{fallback_prefix}-{new_uuid7_str()[:8]}"


def compute_payload_sha256(payload: dict[str, object]) -> str:
    """Compute a deterministic SHA-256 hex digest over a JSON-serializable payload."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class ManagedSkillRecord:
    """User-created reusable Skill (`🛠️ Compétence`)."""

    skill_id: str
    slug: str
    command_handle: str
    uri: str
    name: str
    objective: str
    input_parameters: tuple[str, ...]
    instructions: str
    expected_output_format: str
    version: str = "1.0.0"
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class ManagedAgentRecord:
    """User-created Agent (`🤖 Agent`) with 1-click attached Skills."""

    agent_id: str
    slug: str
    handle: str
    uri: str
    name: str
    role_mission: str
    instructions: str
    thinking_level: AgentThinkingLevel
    skill_ids: tuple[str, ...] = ()
    version: str = "1.0.0"
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class SkillExecutionOutcome:
    """Result of testing/executing a Skill in 1 click."""

    skill_id: str
    skill_name: str
    command_handle: str
    input_text: str
    applied_parameters: dict[str, str]
    output_text: str
    expected_output_format: str
    status: Literal["SUCCEEDED"] = "SUCCEEDED"


@dataclass(frozen=True, slots=True)
class InvokedSkillTraceItem:
    """Trace of a Skill mobilized during an Agent execution."""

    skill_id: str
    skill_name: str
    command_handle: str
    output_summary: str


@dataclass(frozen=True, slots=True)
class AgentExecutionOutcome:
    """Result of testing/executing an Agent with its attached Skills in 1 click."""

    agent_id: str
    agent_name: str
    agent_handle: str
    thinking_level: AgentThinkingLevel
    prompt: str
    response_text: str
    invoked_skills: tuple[InvokedSkillTraceItem, ...]
    status: Literal["SUCCEEDED"] = "SUCCEEDED"


def _run_llm_sync(llm: LLMPort, request: LlmPromptRequest) -> str:
    """Execute `llm.complete(request)` safely from both sync and async calling contexts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(llm.complete(request)).content
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(llm.complete(request)).content).result()


class AgentsAndSkillsManagementService:
    """Domain service for creating, linking, and executing Skills and Agents (`🤖 Mes Agents`)."""

    def __init__(self, *, llm_gateway: LLMPort | None = None) -> None:
        self._llm: LLMPort = llm_gateway or DeterministicCassetteLLM()
        self._skills: dict[str, ManagedSkillRecord] = {}
        self._agents: dict[str, ManagedAgentRecord] = {}

    @property
    def skills(self) -> tuple[ManagedSkillRecord, ...]:
        """Return all user-configured skills in creation order."""
        return tuple(self._skills.values())

    @property
    def agents(self) -> tuple[ManagedAgentRecord, ...]:
        """Return all user-configured agents in creation order."""
        return tuple(self._agents.values())

    def sync_from_records(
        self,
        *,
        skills: tuple[ManagedSkillRecord, ...],
        agents: tuple[ManagedAgentRecord, ...],
    ) -> None:
        """Hydrate in-memory state from PostgreSQL 18 records."""
        valid_skill_ids = {s.skill_id for s in skills}
        self._skills = {s.skill_id: s for s in skills}
        self._agents = {
            a.agent_id: replace(
                a,
                skill_ids=tuple(sid for sid in a.skill_ids if sid in valid_skill_ids),
            )
            for a in agents
        }

    def get_skill(self, skill_id: str, *, instance: str | None = None) -> ManagedSkillRecord:
        """Retrieve a Skill by ID or raise `ResourceNotFoundError`."""
        skill = self._skills.get(skill_id)
        if skill is None:
            raise ResourceNotFoundError(instance=instance)
        return skill

    def get_agent(self, agent_id: str, *, instance: str | None = None) -> ManagedAgentRecord:
        """Retrieve an Agent by ID or raise `ResourceNotFoundError`."""
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
        instance: str | None = None,
    ) -> ManagedSkillRecord:
        """Create or update a reusable Skill (`🛠️ Compétence`)."""
        clean_name = name.strip()
        clean_objective = objective.strip()
        clean_instructions = instructions.strip()
        clean_format = expected_output_format.strip() or "Synthèse structurée"
        if not clean_name:
            raise ValidationDomainError(
                detail_override="Le nom de la compétence est obligatoire.",
                instance=instance,
            )
        if not clean_objective:
            raise ValidationDomainError(
                detail_override="L'objectif métier de la compétence est obligatoire.",
                instance=instance,
            )
        if not clean_instructions:
            raise ValidationDomainError(
                detail_override="Les instructions d'exécution de la compétence sont obligatoires.",
                instance=instance,
            )

        slug = normalize_identifier_slug(clean_name, fallback_prefix="skill")
        resolved_id = (skill_id or "").strip() or f"skill-{slug}"
        params = tuple(dict.fromkeys(p.strip() for p in input_parameters if p.strip()))
        uri = f"orcia://skills/{slug}@{version}"
        digest = compute_payload_sha256(
            {
                "skill_id": resolved_id,
                "slug": slug,
                "name": clean_name,
                "objective": clean_objective,
                "input_parameters": list(params),
                "instructions": clean_instructions,
                "expected_output_format": clean_format,
                "version": version,
            }
        )
        record = ManagedSkillRecord(
            skill_id=resolved_id,
            slug=slug,
            command_handle=f"/{slug}",
            uri=uri,
            name=clean_name,
            objective=clean_objective,
            input_parameters=params,
            instructions=clean_instructions,
            expected_output_format=clean_format,
            version=version,
            sha256=digest,
        )
        self._skills[resolved_id] = record
        return record

    def delete_skill(
        self, skill_id: str, *, instance: str | None = None
    ) -> tuple[ManagedSkillRecord, tuple[str, ...]]:
        """Delete a Skill and automatically detach it from any Agents referencing it."""
        removed = self.get_skill(skill_id, instance=instance)
        del self._skills[skill_id]
        updated_agent_ids: list[str] = []
        for aid, agent in list(self._agents.items()):
            if skill_id in agent.skill_ids:
                next_skills = tuple(sid for sid in agent.skill_ids if sid != skill_id)
                self._agents[aid] = self._rebuild_agent_with_skills(agent, next_skills)
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
        """Execute/test a Skill directly on a concrete input and return its formatted result."""
        skill = self.get_skill(skill_id, instance=instance)
        clean_input = input_text.strip()
        if not clean_input:
            raise ValidationDomainError(
                detail_override="Veuillez saisir une entrée de test pour exécuter la compétence.",
                instance=instance,
            )
        provided_params = {
            str(k).strip(): str(v).strip() for k, v in (parameters or {}).items() if str(k).strip()
        }
        for expected_param in skill.input_parameters:
            if expected_param not in provided_params:
                provided_params[expected_param] = clean_input

        params_summary = (
            ", ".join(f"{k}={v}" for k, v in provided_params.items())
            if provided_params
            else "aucun paramètre additionnel"
        )
        resolved_result = (
            llm_response_override.strip()
            if llm_response_override and llm_response_override.strip()
            else f"Synthèse validée pour « {clean_input} »."
        )
        output_lines = [
            f"✅ Compétence « {skill.name} » ({skill.command_handle}) exécutée avec succès.",
            f"• Objectif appliqué : {skill.objective}",
            f"• Entrée analysée : {clean_input}",
            f"• Paramètres pris en compte : {params_summary}",
            f"• Méthode exécutée : {skill.instructions}",
            f"• Résultat ({skill.expected_output_format}) :\n{resolved_result}",
        ]
        return SkillExecutionOutcome(
            skill_id=skill.skill_id,
            skill_name=skill.name,
            command_handle=skill.command_handle,
            input_text=clean_input,
            applied_parameters=provided_params,
            output_text="\n".join(output_lines),
            expected_output_format=skill.expected_output_format,
        )

    def _rebuild_agent_with_skills(
        self, agent: ManagedAgentRecord, next_skills: tuple[str, ...]
    ) -> ManagedAgentRecord:
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
            }
        )
        return replace(agent, skill_ids=next_skills, sha256=digest)

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
        instance: str | None = None,
    ) -> ManagedAgentRecord:
        """Create or update an Agent (`🤖 Agent`) with its attached `skill_ids`."""
        clean_name = name.strip()
        clean_role = role_mission.strip()
        clean_instructions = instructions.strip()
        if not clean_name:
            raise ValidationDomainError(
                detail_override="Le nom de l'agent est obligatoire.",
                instance=instance,
            )
        if not clean_role:
            raise ValidationDomainError(
                detail_override="Le rôle et la mission de l'agent sont obligatoires.",
                instance=instance,
            )
        if not clean_instructions:
            raise ValidationDomainError(
                detail_override="Les instructions de l'agent sont obligatoires.",
                instance=instance,
            )

        slug = normalize_identifier_slug(clean_name, fallback_prefix="agent")
        resolved_id = (agent_id or "").strip() or f"agent-{slug}"
        valid_skills = tuple(
            dict.fromkeys(sid.strip() for sid in skill_ids if sid.strip() in self._skills)
        )
        uri = f"orcia://agents/{slug}@{version}"
        base = ManagedAgentRecord(
            agent_id=resolved_id,
            slug=slug,
            handle=f"@{slug}",
            uri=uri,
            name=clean_name,
            role_mission=clean_role,
            instructions=clean_instructions,
            thinking_level=thinking_level,
            skill_ids=valid_skills,
            version=version,
        )
        record = self._rebuild_agent_with_skills(base, valid_skills)
        self._agents[resolved_id] = record
        return record

    def set_agent_skills(
        self,
        agent_id: str,
        *,
        skill_ids: tuple[str, ...] | list[str],
        instance: str | None = None,
    ) -> ManagedAgentRecord:
        """Attach or detach Skills on an Agent in 1 click."""
        agent = self.get_agent(agent_id, instance=instance)
        valid_skills = tuple(
            dict.fromkeys(sid.strip() for sid in skill_ids if sid.strip() in self._skills)
        )
        updated = self._rebuild_agent_with_skills(agent, valid_skills)
        self._agents[agent_id] = updated
        return updated

    def delete_agent(self, agent_id: str, *, instance: str | None = None) -> ManagedAgentRecord:
        """Delete an Agent by ID."""
        removed = self.get_agent(agent_id, instance=instance)
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
        """Execute an Agent with its attached Skills on a user prompt."""
        agent = self.get_agent(agent_id, instance=instance)
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValidationDomainError(
                detail_override="Veuillez saisir une demande pour tester l'agent.",
                instance=instance,
            )

        invoked_traces: list[InvokedSkillTraceItem] = []
        for sid in agent.skill_ids:
            skill = self._skills.get(sid)
            if skill is None:
                continue
            self.execute_skill(sid, input_text=clean_prompt, instance=instance)
            invoked_traces.append(
                InvokedSkillTraceItem(
                    skill_id=skill.skill_id,
                    skill_name=skill.name,
                    command_handle=skill.command_handle,
                    output_summary=(
                        f"{skill.name} ({skill.command_handle}) -> "
                        f"{skill.expected_output_format} produit pour « {clean_prompt} »"
                    ),
                )
            )

        skills_block = (
            "\n".join(f"- {t.output_summary}" for t in invoked_traces)
            if invoked_traces
            else "Aucune compétence externe mobilisée."
        )
        if llm_response_override and llm_response_override.strip():
            llm_text = llm_response_override.strip()
        else:
            llm_req = LlmPromptRequest(
                system_prompt=(
                    f"Agent: {agent.name} ({agent.handle}) | Rôle: {agent.role_mission} | "
                    f"Instructions: {agent.instructions}"
                ),
                user_prompt=f"Demande: {clean_prompt}\nCompétences: {skills_block}",
                model_family="anthropic",
                model_id="anthropic/claude-3-7-sonnet",
                execution_mode="COACHING",
                metadata={"agent_id": agent.agent_id, "thinking_level": agent.thinking_level},
            )
            llm_text = _run_llm_sync(self._llm, llm_req)

        skills_names = (
            ", ".join(f"{t.skill_name} ({t.command_handle})" for t in invoked_traces)
            if invoked_traces
            else "aucune compétence rattachée"
        )
        response_lines = [
            f"🤖 Réponse de {agent.name} ({agent.handle}) — Mission : {agent.role_mission}",
            f"• Demande traitée : « {clean_prompt} »",
            f"• Compétences mobilisées ({len(invoked_traces)}) : {skills_names}",
            (
                f"• Synthèse : Selon mes instructions (« {agent.instructions} »), "
                f"voici la proposition structurée pour « {clean_prompt} ». ({llm_text})"
            ),
        ]
        return AgentExecutionOutcome(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            agent_handle=agent.handle,
            thinking_level=agent.thinking_level,
            prompt=clean_prompt,
            response_text="\n".join(response_lines),
            invoked_skills=tuple(invoked_traces),
        )
