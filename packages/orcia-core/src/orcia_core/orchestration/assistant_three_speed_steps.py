"""3-Speed Execution Branch Builders (`SPEED_1_FAST`, `SPEED_2_AGENT_TOOLS`, `SPEED_3`)."""

from __future__ import annotations

import time
from collections.abc import Iterator

from orcia_core.orchestration.assistant_three_speed_models import (
    AssistantSpeedMode,
    CachedAssembledPromptResult,
    ThreeSpeedStepProgressItem,
    ThreeSpeedTurnResult,
)
from orcia_kernel.ids import new_uuid7_str


def iter_three_speed_turn_sse_events(turn: ThreeSpeedTurnResult) -> Iterator[dict[str, object]]:
    """Yield SSE event dicts (`cache_status`, `step_progress`, `token`, `done`) for a turn."""
    yield {
        "event": "cache_status",
        "data": {
            "cache_key": turn.cache_key,
            "cache_hit": turn.cache_hit,
            "cache_lookup_ms": turn.cache_lookup_ms,
            "nodes_1_to_4_deterministic_ms": turn.nodes_1_to_4_deterministic_ms,
            "speed_mode": turn.speed_mode,
        },
    }
    for step in turn.step_progress:
        yield {
            "event": "step_progress",
            "data": {
                "step_code": step.step_code,
                "label": step.label,
                "duration_ms": step.duration_ms,
                "status": step.status,
                "connector_or_lens": step.connector_or_lens,
                "intermediate_output": step.intermediate_output,
            },
        }
    yield {"event": "token", "data": {"text": turn.response_text, "ttft_ms": turn.ttft_ms}}
    yield {
        "event": "done",
        "data": {
            "turn_id": turn.turn_id,
            "speed_mode": turn.speed_mode,
            "ttft_ms": turn.ttft_ms,
            "intermediate_llm_calls": turn.intermediate_llm_calls,
            "assembled_prompt_sha256": turn.assembled_prompt_sha256,
        },
    }


def build_speed_1_turn_result(
    *,
    workspace_id: str,
    user_id: str,
    active_hat: str,
    user_prompt: str,
    prompt_excerpt: str,
    cadrage_summary: str,
    det_ms: float,
    cached_prompt: CachedAssembledPromptResult,
    llm_response_override: str | None,
    llm_step_label_override: str | None,
    llm_latency_ms_override: float | None,
    llm_thinking_override: str | None,
) -> ThreeSpeedTurnResult:
    """Build Speed 1 (`SPEED_1_FAST`) deterministic + single-shot result."""
    from orcia_core.orchestration._assistant_locales import ASSISTANT_THREE_SPEED_LOCALES

    tloc = ASSISTANT_THREE_SPEED_LOCALES["fr"]
    t0 = time.perf_counter()
    step2_label = llm_step_label_override or tloc["s1_step2_label"]
    step2_thinking = llm_thinking_override or tloc["s1_step2_thinking"].format(
        prompt_excerpt=prompt_excerpt
    )
    llm_ms = (
        round(llm_latency_ms_override, 2)
        if llm_latency_ms_override is not None
        else round((time.perf_counter() - t0) * 1000.0, 3)
    )
    steps: tuple[ThreeSpeedStepProgressItem, ...] = (
        ThreeSpeedStepProgressItem(
            step_code="NODES_1_TO_4_DETERMINISTIC",
            label=tloc["s1_det_label"],
            duration_ms=det_ms,
            intermediate_output=cadrage_summary,
        ),
        ThreeSpeedStepProgressItem(
            step_code="NODE_5_SINGLE_STREAM_LLM",
            label=step2_label,
            duration_ms=llm_ms,
            intermediate_output=step2_thinking,
        ),
    )
    response_text = llm_response_override or tloc["s1_response"].format(
        active_hat=active_hat,
        cache_state="HIT" if cached_prompt.cache_hit else "MISS",
        prompt=user_prompt.strip(),
    )
    return ThreeSpeedTurnResult(
        turn_id=new_uuid7_str(),
        workspace_id=workspace_id,
        user_id=user_id,
        hat=active_hat,
        speed_mode="SPEED_1_FAST",
        cache_key=cached_prompt.cache_key,
        cache_hit=cached_prompt.cache_hit,
        cache_lookup_ms=cached_prompt.lookup_latency_ms,
        nodes_1_to_4_deterministic_ms=det_ms,
        ttft_ms=round(det_ms + llm_ms, 2),
        intermediate_llm_calls=0,
        invoked_targets=(),
        step_progress=steps,
        response_text=response_text,
        assembled_prompt_sha256=cached_prompt.layers_sha256,
    )


def build_speed_2_turn_result(
    *,
    workspace_id: str,
    user_id: str,
    active_hat: str,
    user_prompt: str,
    prompt_excerpt: str,
    cadrage_summary: str,
    det_ms: float,
    targets: tuple[str, ...],
    cached_prompt: CachedAssembledPromptResult,
    llm_response_override: str | None,
    llm_step_label_override: str | None,
    llm_latency_ms_override: float | None,
    llm_thinking_override: str | None,
) -> ThreeSpeedTurnResult:
    """Build Speed 2 (`SPEED_2_AGENT_TOOLS`) result with governed connector steps."""
    from orcia_core.orchestration._assistant_locales import ASSISTANT_THREE_SPEED_LOCALES

    tloc = ASSISTANT_THREE_SPEED_LOCALES["fr"]
    t0 = time.perf_counter()
    effective_targets = targets or ("@tracker-triage",)
    first_token = effective_targets[0].lstrip("@/").split("-", maxsplit=1)[0]
    target_source = first_token.capitalize() if first_token else tloc["s2_default_target"]
    connector_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    llm_ms = (
        round(llm_latency_ms_override, 2)
        if llm_latency_ms_override is not None
        else round((time.perf_counter() - t0) * 1000.0, 3)
    )
    targets_csv = ", ".join(effective_targets)
    steps: tuple[ThreeSpeedStepProgressItem, ...] = (
        ThreeSpeedStepProgressItem(
            step_code="NODES_1_TO_4_DETERMINISTIC",
            label=tloc["s2_det_label"],
            duration_ms=det_ms,
            intermediate_output=cadrage_summary,
        ),
        ThreeSpeedStepProgressItem(
            step_code="CONNECTOR_INTERROGATION",
            label=tloc["s2_conn_label"].format(target_source=target_source),
            duration_ms=connector_ms,
            connector_or_lens=targets_csv,
            intermediate_output=tloc["s2_conn_out"].format(targets=targets_csv),
        ),
        ThreeSpeedStepProgressItem(
            step_code="CONNECTOR_INVOKER_EXEC",
            label=llm_step_label_override or tloc["s2_exec_label"].format(targets=targets_csv),
            duration_ms=llm_ms,
            connector_or_lens=effective_targets[0],
            intermediate_output=llm_thinking_override
            or tloc["s2_exec_thinking"].format(targets=targets_csv, prompt_excerpt=prompt_excerpt),
        ),
    )
    response_text = llm_response_override or tloc["s2_response"].format(
        targets=targets_csv, prompt=user_prompt.strip()
    )
    return ThreeSpeedTurnResult(
        turn_id=new_uuid7_str(),
        workspace_id=workspace_id,
        user_id=user_id,
        hat=active_hat,
        speed_mode="SPEED_2_AGENT_TOOLS",
        cache_key=cached_prompt.cache_key,
        cache_hit=cached_prompt.cache_hit,
        cache_lookup_ms=cached_prompt.lookup_latency_ms,
        nodes_1_to_4_deterministic_ms=det_ms,
        ttft_ms=round(det_ms + connector_ms + llm_ms, 2),
        intermediate_llm_calls=0,
        invoked_targets=effective_targets,
        step_progress=steps,
        response_text=response_text,
        assembled_prompt_sha256=cached_prompt.layers_sha256,
    )


def build_speed_3_turn_result(
    *,
    workspace_id: str,
    user_id: str,
    active_hat: str,
    speed_mode: AssistantSpeedMode,
    user_prompt: str,
    prompt_excerpt: str,
    cadrage_summary: str,
    det_ms: float,
    targets: tuple[str, ...],
    cached_prompt: CachedAssembledPromptResult,
    llm_response_override: str | None,
    llm_step_label_override: str | None,
    llm_latency_ms_override: float | None,
    llm_thinking_override: str | None,
) -> ThreeSpeedTurnResult:
    """Build Speed 3 (`SPEED_3_DEEP_AUDIT`) multi-lens AD-10 audit result."""
    from orcia_core.orchestration._assistant_locales import ASSISTANT_THREE_SPEED_LOCALES

    tloc = ASSISTANT_THREE_SPEED_LOCALES["fr"]
    t0 = time.perf_counter()
    lenses = ("ARCHITECTURE_CONSISTENCY", "SECURITY_ZERO_TRUST", "FINOPS_CONTRAST")
    plan_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    judge_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    llm_ms = (
        round(llm_latency_ms_override, 2)
        if llm_latency_ms_override is not None
        else round((time.perf_counter() - t0) * 1000.0, 3)
    )
    steps: tuple[ThreeSpeedStepProgressItem, ...] = (
        ThreeSpeedStepProgressItem(
            step_code="NODES_1_TO_4_DETERMINISTIC",
            label=tloc["s3_det_label"],
            duration_ms=det_ms,
            intermediate_output=cadrage_summary,
        ),
        ThreeSpeedStepProgressItem(
            step_code="DEEP_PLANNING_LLM",
            label=tloc["s3_plan_label"],
            duration_ms=plan_ms,
            connector_or_lens="PLANNER_LLM",
            intermediate_output=tloc["s3_plan_out"].format(prompt_excerpt=prompt_excerpt),
        ),
        ThreeSpeedStepProgressItem(
            step_code="ORTHOGONAL_MULTI_LENS_AD10",
            label=tloc["s3_lens_label"],
            duration_ms=judge_ms,
            connector_or_lens="ORTHOGONAL_JUDGE_AD10",
            intermediate_output=llm_thinking_override or tloc["s3_lens_out"],
        ),
        ThreeSpeedStepProgressItem(
            step_code="DEEP_SYNTHESIS_STREAM",
            label=llm_step_label_override or tloc["s3_synth_label"],
            duration_ms=llm_ms,
            intermediate_output=tloc["s3_synth_out"],
        ),
    )
    response_text = llm_response_override or tloc["s3_response"].format(
        lenses=", ".join(lenses), prompt=user_prompt.strip()
    )
    return ThreeSpeedTurnResult(
        turn_id=new_uuid7_str(),
        workspace_id=workspace_id,
        user_id=user_id,
        hat=active_hat,
        speed_mode=speed_mode,
        cache_key=cached_prompt.cache_key,
        cache_hit=cached_prompt.cache_hit,
        cache_lookup_ms=cached_prompt.lookup_latency_ms,
        nodes_1_to_4_deterministic_ms=det_ms,
        ttft_ms=round(det_ms + plan_ms + judge_ms + llm_ms, 2),
        intermediate_llm_calls=2,
        invoked_targets=targets,
        step_progress=steps,
        response_text=response_text,
        assembled_prompt_sha256=cached_prompt.layers_sha256,
        deep_audit_lenses=lenses,
    )
