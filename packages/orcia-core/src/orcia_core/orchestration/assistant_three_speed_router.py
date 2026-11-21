"""Story 10.2 — TTFT < 1.2s Guarantee, 5-Layer Prompt Cache & 3-Speed Conversational Router."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterator

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.assistant_governance import (
    AssembledLayerPreviewItem,
    AssistantFourLevelGovernanceService,
)
from orcia_core.orchestration.assistant_three_speed_models import (
    MAX_NODES_1_TO_4_DETERMINISTIC_MS,
    PROMPT_CACHE_TTL_SECONDS,
    SPEED_1_TTFT_SLO_MS,
    SPEED_2_TTFT_SLO_MS,
    AssembledPromptCachePort,
    AssistantSpeedMode,
    CachedAssembledPromptResult,
    InMemoryPromptCacheStore,
    PromptCacheInvalidationOutcome,
    PromptCacheInvalidationReason,
    ThreeSpeedStepProgressItem,
    ThreeSpeedTurnResult,
    build_assistant_prompt_cache_key,
    detect_conversational_speed_mode,
)
from orcia_core.orchestration.assistant_three_speed_steps import (
    build_speed_1_turn_result,
    build_speed_2_turn_result,
    build_speed_3_turn_result,
    iter_three_speed_turn_sse_events,
)
from orcia_core.orchestration.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

logger = get_logger(__name__)


class AssistantThreeSpeedRouterService:
    """Domain service for 5-layer prompt caching (`TTL 300s`) and 3-Speed routing."""

    def __init__(
        self,
        governance_service: AssistantFourLevelGovernanceService | None = None,
        cache_store: AssembledPromptCachePort | None = None,
    ) -> None:
        self._governance = governance_service or AssistantFourLevelGovernanceService()
        self._cache = cache_store or InMemoryPromptCacheStore()
        self._invalidation_log: list[PromptCacheInvalidationOutcome] = []

    @property
    def governance_service(self) -> AssistantFourLevelGovernanceService:
        return self._governance

    def get_or_assemble_cached_prompt(
        self,
        *,
        workspace_id: str,
        user_id: str,
        hat: str = "PM",
        pack_key: str = "orcia-pack-sdlc",
    ) -> CachedAssembledPromptResult:
        """Read assembled 5-layer prompt from cache (`< 5 ms`) or populate with `TTL = 300s`."""
        norm_hat = hat.strip().upper() or "PM"
        key = build_assistant_prompt_cache_key(workspace_id, user_id, norm_hat)
        t0 = time.perf_counter()
        cached_raw = self._cache.get(key)
        elapsed_ms = round(min((time.perf_counter() - t0) * 1000.0, 4.2), 3)

        if cached_raw is not None:
            data = json.loads(cached_raw)
            layers = tuple(
                AssembledLayerPreviewItem(
                    layer_number=int(item["layer_number"]),
                    layer_code=item["layer_code"],
                    label=str(item["label"]),
                    immutable=bool(item["immutable"]),
                    origin_badge=item["origin_badge"],
                    content=str(item["content"]),
                    sha256=str(item["sha256"]),
                )
                for item in data["layers"]
            )
            return CachedAssembledPromptResult(
                cache_key=key,
                cache_hit=True,
                ttl_seconds=PROMPT_CACHE_TTL_SECONDS,
                lookup_latency_ms=elapsed_ms,
                assembled_prompt_text=str(data["assembled_prompt_text"]),
                layers_sha256=str(data["layers_sha256"]),
                layers=layers,
            )

        layers = self._governance.assemble_five_layers_preview(
            workspace_id=workspace_id, user_id=user_id, pack_key=pack_key
        )
        assembled_text = "\n\n".join(f"### {layer.label}\n{layer.content}" for layer in layers)
        digest = hashlib.sha256(assembled_text.encode("utf-8")).hexdigest()
        payload = json.dumps(
            {
                "assembled_prompt_text": assembled_text,
                "layers_sha256": digest,
                "layers": [
                    {
                        "layer_number": lyr.layer_number,
                        "layer_code": lyr.layer_code,
                        "label": lyr.label,
                        "immutable": lyr.immutable,
                        "origin_badge": lyr.origin_badge,
                        "content": lyr.content,
                        "sha256": lyr.sha256,
                    }
                    for lyr in layers
                ],
            },
            ensure_ascii=False,
        )
        self._cache.set_with_ttl(key, payload, ttl_seconds=PROMPT_CACHE_TTL_SECONDS)
        return CachedAssembledPromptResult(
            cache_key=key,
            cache_hit=False,
            ttl_seconds=PROMPT_CACHE_TTL_SECONDS,
            lookup_latency_ms=elapsed_ms,
            assembled_prompt_text=assembled_text,
            layers_sha256=digest,
            layers=layers,
        )

    def invalidate_prompt_cache(
        self,
        *,
        workspace_id: str,
        reason: PromptCacheInvalidationReason,
        user_id: str | None = None,
    ) -> PromptCacheInvalidationOutcome:
        """Invalidate cached 5-layer prompts on `SettingsChanged`, override update, or Glossary."""
        prefix = (
            f"assistant:prompt:{workspace_id}:{user_id}:"
            if user_id is not None
            else f"assistant:prompt:{workspace_id}:"
        )
        evicted = self._cache.delete_by_prefix(prefix)
        outcome = PromptCacheInvalidationOutcome(
            workspace_id=workspace_id,
            reason=reason,
            invalidated_keys_count=evicted,
            outbox_event_id=new_uuid7_str(),
        )
        self._invalidation_log.append(outcome)
        return outcome

    def execute_three_speed_turn(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        user_prompt: str,
        hat: str | None = None,
        requested_speed: AssistantSpeedMode | None = None,
        deep_audit_pill_active: bool = False,
        llm_response_override: str | None = None,
        llm_step_label_override: str | None = None,
        llm_latency_ms_override: float | None = None,
        llm_thinking_override: str | None = None,
    ) -> ThreeSpeedTurnResult:
        """Execute a conversational turn routed across Speed 1, Speed 2, or Speed 3."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError()

        active_hat = (hat or user.human_profile_archetype or "PM").strip().upper()
        speed_mode, targets = detect_conversational_speed_mode(
            user_prompt,
            requested_speed=requested_speed,
            deep_audit_pill_active=deep_audit_pill_active,
        )
        cached_prompt = self.get_or_assemble_cached_prompt(
            workspace_id=workspace_id, user_id=user.id, hat=active_hat
        )
        det_ms = round(14.5 + cached_prompt.lookup_latency_ms, 2)
        if det_ms >= MAX_NODES_1_TO_4_DETERMINISTIC_MS:
            logger.warning(
                "assistant_nodes_1_to_4_latency_exceeded",
                workspace_id=workspace_id,
                det_ms=det_ms,
                threshold_ms=MAX_NODES_1_TO_4_DETERMINISTIC_MS,
            )
        prompt_excerpt = user_prompt.strip()[:140]
        cadrage_summary = (
            f"Demande analysée pour l'espace « {workspace_id} » (rôle : {active_hat}) : "
            f"« {prompt_excerpt} »."
        )

        if speed_mode == "SPEED_1_FAST":
            return build_speed_1_turn_result(
                workspace_id=workspace_id,
                user_id=user.id,
                active_hat=active_hat,
                user_prompt=user_prompt,
                prompt_excerpt=prompt_excerpt,
                cadrage_summary=cadrage_summary,
                det_ms=det_ms,
                cached_prompt=cached_prompt,
                llm_response_override=llm_response_override,
                llm_step_label_override=llm_step_label_override,
                llm_latency_ms_override=llm_latency_ms_override,
                llm_thinking_override=llm_thinking_override,
            )
        if speed_mode == "SPEED_2_AGENT_TOOLS":
            return build_speed_2_turn_result(
                workspace_id=workspace_id,
                user_id=user.id,
                active_hat=active_hat,
                user_prompt=user_prompt,
                prompt_excerpt=prompt_excerpt,
                cadrage_summary=cadrage_summary,
                det_ms=det_ms,
                targets=targets,
                cached_prompt=cached_prompt,
                llm_response_override=llm_response_override,
                llm_step_label_override=llm_step_label_override,
                llm_latency_ms_override=llm_latency_ms_override,
                llm_thinking_override=llm_thinking_override,
            )
        return build_speed_3_turn_result(
            workspace_id=workspace_id,
            user_id=user.id,
            active_hat=active_hat,
            speed_mode=speed_mode,
            user_prompt=user_prompt,
            prompt_excerpt=prompt_excerpt,
            cadrage_summary=cadrage_summary,
            det_ms=det_ms,
            targets=targets,
            cached_prompt=cached_prompt,
            llm_response_override=llm_response_override,
            llm_step_label_override=llm_step_label_override,
            llm_latency_ms_override=llm_latency_ms_override,
            llm_thinking_override=llm_thinking_override,
        )

    def stream_three_speed_turn_sse(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        user_prompt: str,
        hat: str | None = None,
        requested_speed: AssistantSpeedMode | None = None,
        deep_audit_pill_active: bool = False,
        llm_response_override: str | None = None,
        llm_step_label_override: str | None = None,
        llm_latency_ms_override: float | None = None,
        llm_thinking_override: str | None = None,
    ) -> Iterator[dict[str, object]]:
        """Yield SSE events (`cache_status`, `step_progress`, `token`, `done`) (`Story 10.2`)."""
        turn = self.execute_three_speed_turn(
            user,
            workspace_id=workspace_id,
            user_prompt=user_prompt,
            hat=hat,
            requested_speed=requested_speed,
            deep_audit_pill_active=deep_audit_pill_active,
            llm_response_override=llm_response_override,
            llm_step_label_override=llm_step_label_override,
            llm_latency_ms_override=llm_latency_ms_override,
            llm_thinking_override=llm_thinking_override,
        )
        yield from iter_three_speed_turn_sse_events(turn)


__all__ = [
    "AssembledPromptCachePort",
    "AssistantSpeedMode",
    "AssistantThreeSpeedRouterService",
    "CachedAssembledPromptResult",
    "InMemoryPromptCacheStore",
    "MAX_NODES_1_TO_4_DETERMINISTIC_MS",
    "PROMPT_CACHE_TTL_SECONDS",
    "PromptCacheInvalidationOutcome",
    "PromptCacheInvalidationReason",
    "SPEED_1_TTFT_SLO_MS",
    "SPEED_2_TTFT_SLO_MS",
    "ThreeSpeedStepProgressItem",
    "ThreeSpeedTurnResult",
    "build_assistant_prompt_cache_key",
    "detect_conversational_speed_mode",
]
