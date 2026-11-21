"""3-Speed Execution Branch Builders (`SPEED_1_FAST`, `SPEED_2_AGENT_TOOLS`, `SPEED_3`)."""

from __future__ import annotations

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
    llm_ms = round(llm_latency_ms_override, 2) if llm_latency_ms_override is not None else 380.0
    step2_label = (
        llm_step_label_override or "💬 Nœud 5 — Appel LLM unique en streaming SSE (TTFT < 1,2 s)"
    )
    step2_thinking = (
        llm_thinking_override
        or f"Formulation d'une réponse directe et synthétique pour « {prompt_excerpt} »."
    )
    steps: tuple[ThreeSpeedStepProgressItem, ...] = (
        ThreeSpeedStepProgressItem(
            step_code="NODES_1_TO_4_DETERMINISTIC",
            label=(
                "⚡ Nœuds 1–4 déterministes (Intention, RBAC, RAG SQL/pgvector & Cache 5 couches)"
            ),
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
    response_text = llm_response_override or (
        f"[⚡ Vitesse 1 · Casquette {active_hat}] Réponse directe générée avec "
        f"prompt 5 couches ({'HIT' if cached_prompt.cache_hit else 'MISS'} Redis) : "
        f"Synthèse conforme pour « {user_prompt.strip()} » [S1] [G1]."
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
    effective_targets = targets or ("@tracker-triage",)
    first_token = effective_targets[0].lstrip("@/").split("-", maxsplit=1)[0]
    target_source = first_token.capitalize() if first_token else "Connecteur"
    llm_ms = round(llm_latency_ms_override, 2) if llm_latency_ms_override is not None else 410.0
    steps: tuple[ThreeSpeedStepProgressItem, ...] = (
        ThreeSpeedStepProgressItem(
            step_code="NODES_1_TO_4_DETERMINISTIC",
            label="⚡ Nœuds 1–4 déterministes & vérification RBAC/Passthrough",
            duration_ms=det_ms,
            intermediate_output=cadrage_summary,
        ),
        ThreeSpeedStepProgressItem(
            step_code="CONNECTOR_INTERROGATION",
            label=f"🔍 Interrogation de {target_source}...",
            duration_ms=520.0,
            connector_or_lens=", ".join(effective_targets),
            intermediate_output=(
                f"Mobilisation des compétences et connecteurs : {', '.join(effective_targets)}."
            ),
        ),
        ThreeSpeedStepProgressItem(
            step_code="CONNECTOR_INVOKER_EXEC",
            label=llm_step_label_override
            or f"🛠️ Exécution ConnectorInvoker ({', '.join(effective_targets)})",
            duration_ms=llm_ms,
            connector_or_lens=effective_targets[0],
            intermediate_output=llm_thinking_override
            or (
                f"Consolidation des éléments retournés par {', '.join(effective_targets)} "
                f"pour « {prompt_excerpt} »."
            ),
        ),
    )
    response_text = llm_response_override or (
        f"[🛠️ Vitesse 2 · {', '.join(effective_targets)}] Résultat d'interrogation "
        f"outillée pour « {user_prompt.strip()} » [S1] [O1]."
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
        ttft_ms=round(det_ms + 520.0 + llm_ms, 2),
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
    lenses = ("ARCHITECTURE_CONSISTENCY", "SECURITY_ZERO_TRUST", "FINOPS_CONTRAST")
    llm_ms = round(llm_latency_ms_override, 2) if llm_latency_ms_override is not None else 490.0
    steps: tuple[ThreeSpeedStepProgressItem, ...] = (
        ThreeSpeedStepProgressItem(
            step_code="NODES_1_TO_4_DETERMINISTIC",
            label="⚡ Nœuds 1–4 déterministes & assemblage 5 couches",
            duration_ms=det_ms,
            intermediate_output=cadrage_summary,
        ),
        ThreeSpeedStepProgressItem(
            step_code="DEEP_PLANNING_LLM",
            label="📋 Planification LLM intermédiaire & décomposition causale N1–N3...",
            duration_ms=640.0,
            connector_or_lens="PLANNER_LLM",
            intermediate_output=(
                f"Décomposition de la problématique « {prompt_excerpt} » en 3 axes : "
                "1) Synthèse exécutive, 2) Risques & conformité, 3) Plan d'action."
            ),
        ),
        ThreeSpeedStepProgressItem(
            step_code="ORTHOGONAL_MULTI_LENS_AD10",
            label=(
                "🔬 Vérification multi-facettes orthogonale "
                "(AD-10 : Architecture, Sécurité, FinOps)..."
            ),
            duration_ms=820.0,
            connector_or_lens="ORTHOGONAL_JUDGE_AD10",
            intermediate_output=llm_thinking_override
            or (
                "Revue croisée des 3 facettes : cohérence fonctionnelle, "
                "sécurité des accès et maîtrise des coûts."
            ),
        ),
        ThreeSpeedStepProgressItem(
            step_code="DEEP_SYNTHESIS_STREAM",
            label=llm_step_label_override or "✍️ Synthèse contradictoire consolidée",
            duration_ms=llm_ms,
            intermediate_output="Rédaction de la synthèse structurée finale.",
        ),
    )
    response_text = llm_response_override or (
        f"[🧠 Vitesse 3 Approfondi · Audit multi-facettes AD-10 ({', '.join(lenses)})] "
        f"Analyse approfondie vérifiée pour « {user_prompt.strip()} » [S1] [G1]."
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
        ttft_ms=round(det_ms + 1460.0, 2),
        intermediate_llm_calls=2,
        invoked_targets=targets,
        step_progress=steps,
        response_text=response_text,
        assembled_prompt_sha256=cached_prompt.layers_sha256,
        deep_audit_lenses=lenses,
    )
