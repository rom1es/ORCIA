"""Prompt Assembly & Tool Schema Facade delegating to `AssistantPromptBuilder` (`AD-15`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.routers._assistant_context_assembly import (
    AssembledTurnContext,
    assemble_real_workspace_context_for_turn_async,
)
from orcia_api.routers._assistant_context_assembly import (
    resolve_5_layers_and_ontology_from_request as resolve_5_layers_and_ontology_from_request,
)
from orcia_api.routers._assistant_llm_tools_and_budget import (
    build_multi_turn_messages as build_multi_turn_messages,
)
from orcia_api.routers._assistant_llm_tools_and_budget import (
    build_workspace_tools_and_catalog_async as build_workspace_tools_and_catalog_async,
)
from orcia_api.routers._assistant_llm_tools_and_budget import (
    build_workspace_tools_schema as build_workspace_tools_schema,
)
from orcia_api.routers._assistant_llm_tools_and_budget import (
    resolve_turn_tools_and_router_async as resolve_turn_tools_and_router_async,
)
from orcia_api.routers._assistant_prompt_sanitization import (
    detect_adaptive_thinking_steps_for_question as detect_adaptive_thinking_steps_for_question,
)
from orcia_api.routers._assistant_prompt_sanitization import (
    resolve_request_locale as resolve_request_locale,
)
from orcia_core.orchestration.assistant_prompt_builder import AssistantPromptBuilder
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.embedding import EmbeddingPort

_PROMPT_BUILDER = AssistantPromptBuilder()


def _format_user_governance_and_folder_block(
    *,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Delegate Layer 4 Workspace, Layer 5 User prefs & Folder Notes formatting."""
    return _PROMPT_BUILDER.format_governance_and_folder_block(
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
    )


def build_assistant_system_instructions(
    *,
    hat: str,
    speed_mode: str,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    allow_system_override: bool = False,
    assembled_5_layers_prompt: str | None = None,
    ontology_concepts_summary: str | None = None,
    federated_evidence_summary: str | None = None,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
    has_evidence: bool | None = None,
    pack_key: str | None = None,
) -> str:
    """Delegate conversational system prompt assembly to `AssistantPromptBuilder`."""
    return _PROMPT_BUILDER.build_system_instructions(
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier,
        thinking_effort=thinking_effort,
        system_instructions_override=system_instructions_override,
        allow_system_override=allow_system_override,
        assembled_5_layers_prompt=assembled_5_layers_prompt,
        ontology_concepts_summary=ontology_concepts_summary,
        federated_evidence_summary=federated_evidence_summary,
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
        has_evidence=has_evidence,
        pack_key=pack_key,
    )


async def resolve_5_layers_and_ontology_from_request_async(
    request: Request,
    *,
    workspace_id: str,
    user_id: str,
    hat: str,
    user_prompt: str = "",
    user: UserIdentity | None = None,
    embedding_port: EmbeddingPort | None = None,
    locale: str = "fr",
) -> tuple[str | None, str | None]:
    """Async version hydrating PG18 Mode A, ranked Ontology L1-L4 & Server EvidenceTable."""
    ctx = await assemble_real_workspace_context_for_turn_async(
        request,
        workspace_id=workspace_id,
        user_id=user_id,
        hat=hat,
        user_prompt=user_prompt,
        user=user,
        embedding_port=embedding_port,
        locale=locale,
    )
    return ctx.assembled_5_layers_prompt, ctx.ontology_summary


async def resolve_assembled_turn_context_and_instructions_async(
    request: Request,
    *,
    hat: str,
    speed_mode: str,
    workspace_id: str,
    user_id: str,
    user_prompt: str = "",
    user: UserIdentity | None = None,
    embedding_port: EmbeddingPort | None = None,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    allow_system_override: bool = False,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> tuple[str, AssembledTurnContext]:
    """Assemble full PG18 context, benchmark latency (`R6`), and build system instructions."""
    ctx = await assemble_real_workspace_context_for_turn_async(
        request,
        workspace_id=workspace_id,
        user_id=user_id,
        hat=hat,
        user_prompt=user_prompt,
        user=user,
        embedding_port=embedding_port,
        locale=locale,
    )
    sys_msg = build_assistant_system_instructions(
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier,
        thinking_effort=thinking_effort,
        system_instructions_override=system_instructions_override,
        allow_system_override=allow_system_override,
        assembled_5_layers_prompt=ctx.assembled_5_layers_prompt,
        ontology_concepts_summary=ctx.ontology_summary,
        federated_evidence_summary=ctx.federated_evidence_summary,
        response_tone=response_tone if response_tone is not None else ctx.response_tone,
        response_format=response_format if response_format is not None else ctx.response_format,
        personal_instructions=(
            personal_instructions
            if personal_instructions is not None
            else ctx.personal_instructions
        ),
        workspace_instructions=(
            workspace_instructions
            if workspace_instructions is not None
            else ctx.workspace_instructions
        ),
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
        has_evidence=ctx.has_evidence,
        pack_key=ctx.pack_key,
    )
    return sys_msg, ctx


async def resolve_assembled_system_instructions_for_turn_async(
    request: Request,
    *,
    hat: str,
    speed_mode: str,
    workspace_id: str,
    user_id: str,
    user_prompt: str = "",
    user: UserIdentity | None = None,
    embedding_port: EmbeddingPort | None = None,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    allow_system_override: bool = False,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Async builder hydrating Mode A, PG18 ontology & EvidenceTable into system prompt."""
    sys_msg, _ = await resolve_assembled_turn_context_and_instructions_async(
        request,
        hat=hat,
        speed_mode=speed_mode,
        workspace_id=workspace_id,
        user_id=user_id,
        user_prompt=user_prompt,
        user=user,
        embedding_port=embedding_port,
        requested_tier=requested_tier,
        thinking_effort=thinking_effort,
        system_instructions_override=system_instructions_override,
        allow_system_override=allow_system_override,
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
    )
    return sys_msg


def resolve_assembled_system_instructions_for_turn(
    request: Request,
    *,
    hat: str,
    speed_mode: str,
    workspace_id: str,
    user_id: str,
    requested_tier: str | None = None,
    thinking_effort: str | None = None,
    system_instructions_override: str | None = None,
    allow_system_override: bool = False,
    response_tone: str | None = None,
    response_format: str | None = None,
    personal_instructions: str | None = None,
    workspace_instructions: str | None = None,
    folder_pinned_notes: str | None = None,
    locale: str = "fr",
) -> str:
    """Build the complete 5-layer + ontology + preferences system prompt for a turn."""
    assembled_5_layers, ontology_summary = resolve_5_layers_and_ontology_from_request(
        request, workspace_id=workspace_id, user_id=user_id, hat=hat, locale=locale
    )
    return build_assistant_system_instructions(
        hat=hat,
        speed_mode=speed_mode,
        requested_tier=requested_tier,
        thinking_effort=thinking_effort,
        system_instructions_override=system_instructions_override,
        allow_system_override=allow_system_override,
        assembled_5_layers_prompt=assembled_5_layers,
        ontology_concepts_summary=ontology_summary,
        response_tone=response_tone,
        response_format=response_format,
        personal_instructions=personal_instructions,
        workspace_instructions=workspace_instructions,
        folder_pinned_notes=folder_pinned_notes,
        locale=locale,
    )
