"""FastAPI router for Inter-Step Upstream Challenge & Targeted Step Replay (`Story 3.5`).

Exposes:
- `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/challenge/preview`
- `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/challenge`
- `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/replay`
- `POST /api/v1/runs/{run_id}/steps/{step_key}/replay` (canonical alias per `epics.md:L556`)
"""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_orchestration_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.routers.orchestration_sql_wiring import sync_replay_fork_to_sql
from orcia_api.schemas.challenge_and_replay import (
    StepReplayRequest,
    StepReplayResponse,
    StepReplayResultSchemaItem,
    UpstreamChallengePreviewRequest,
    UpstreamChallengePreviewResponse,
    UpstreamChallengePreviewSchemaItem,
    UpstreamChallengeSchemaItem,
    UpstreamChallengeSubmitRequest,
    UpstreamChallengeSubmitResponse,
)
from orcia_core.orchestration.challenge_and_replay import (
    StepReplayResult,
    UpstreamChallengeEntity,
    UpstreamChallengeImpactPreview,
)

router = APIRouter(tags=["Blackboard & Durable Engine"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", "00000000000000000000000000000000"))


def _serialize_preview(p: UpstreamChallengeImpactPreview) -> UpstreamChallengePreviewSchemaItem:
    return UpstreamChallengePreviewSchemaItem(
        run_id=p.run_id,
        challenger_step_key=p.challenger_step_key,
        target_upstream_step_key=p.target_upstream_step_key,
        challenged_section_key=p.challenged_section_key,
        challenge_reason=p.challenge_reason,
        target_profile_archetype=p.target_profile_archetype,
        translated_summary=p.translated_summary,
        invalidated_downstream_step_keys=list(p.invalidated_downstream_step_keys),
        invalidated_artifact_sections=list(p.invalidated_artifact_sections),
        invalidated_ontology_axiom_keys=list(p.invalidated_ontology_axiom_keys),
        preserved_upstream_step_keys=list(p.preserved_upstream_step_keys),
        upstream_tokens_saved=p.upstream_tokens_saved,
    )


def _serialize_challenge(c: UpstreamChallengeEntity) -> UpstreamChallengeSchemaItem:
    return UpstreamChallengeSchemaItem(
        id=c.id,
        challenge_key=c.challenge_key,
        workspace_id=c.workspace_id,
        run_id=c.run_id,
        challenger_step_key=c.challenger_step_key,
        target_upstream_step_key=c.target_upstream_step_key,
        challenged_section_key=c.challenged_section_key,
        challenge_reason=c.challenge_reason,
        target_profile_archetype=c.target_profile_archetype,
        translated_summary=c.translated_summary,
        invalidated_downstream_step_keys=list(c.invalidated_downstream_step_keys),
        invalidated_artifact_sections=list(c.invalidated_artifact_sections),
        invalidated_ontology_axiom_keys=list(c.invalidated_ontology_axiom_keys),
        preserved_upstream_step_keys=list(c.preserved_upstream_step_keys),
        status=c.status,
        created_by_user_id=c.created_by_user_id,
        outbox_event_id=c.outbox_event_id,
        revised_artifact_version=c.revised_artifact_version,
    )


def _serialize_replay(r: StepReplayResult) -> StepReplayResultSchemaItem:
    return StepReplayResultSchemaItem(
        run_id=r.run_id,
        replayed_from_step_key=r.replayed_from_step_key,
        sub_workflow_step_key=r.sub_workflow_step_key,
        reused_upstream_snapshot_ids=list(r.reused_upstream_snapshot_ids),
        superseded_snapshot_ids=list(r.superseded_snapshot_ids),
        new_active_snapshot_ids=list(r.new_active_snapshot_ids),
        upstream_steps_reexecuted_count=r.upstream_steps_reexecuted_count,
        upstream_tokens_consumed=r.upstream_tokens_consumed,
        run_lock_sha256=r.run_lock_sha256,
    )


@router.post(
    "/api/v1/orchestration/runs/{run_id}/steps/{step_key}/challenge/preview",
    response_model=UpstreamChallengePreviewResponse,
    summary="Compute What-If Impact Preview for an Inter-Step Upstream Challenge (Story 3.5)",
    responses=PROBLEM_RESPONSES,
)
async def preview_upstream_challenge(
    payload: UpstreamChallengePreviewRequest,
    request: Request,
    run_id: str = Path(..., min_length=1, max_length=128),
    step_key: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> UpstreamChallengePreviewResponse:
    """Compute DAG + Ontology `What-If Impact Preview` for an upstream step (`UX-DR7`)."""
    resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    preview = svc.engine.challenge_and_replay.preview_upstream_challenge(
        run_id=run_id,
        challenger_step_key=step_key,
        target_upstream_step_key=payload.target_upstream_step_key,
        challenged_section_key=payload.challenged_section_key,
        challenge_reason=payload.challenge_reason,
        target_profile_archetype=payload.target_profile_archetype,
        instance=str(request.url.path),
    )
    return UpstreamChallengePreviewResponse(
        preview=_serialize_preview(preview),
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/orchestration/runs/{run_id}/steps/{step_key}/challenge",
    response_model=UpstreamChallengeSubmitResponse,
    summary="Submit an Inter-Step Upstream Challenge with Outbox notification (Story 3.5, FR-7)",
    responses=PROBLEM_RESPONSES,
)
async def submit_upstream_challenge(
    payload: UpstreamChallengeSubmitRequest,
    request: Request,
    run_id: str = Path(..., min_length=1, max_length=128),
    step_key: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> UpstreamChallengeSubmitResponse:
    """Record an upstream challenge, translate for upstream profile, and emit Outbox event."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    record, preview = svc.engine.challenge_and_replay.submit_upstream_challenge(
        user,
        run_id=run_id,
        challenger_step_key=step_key,
        target_upstream_step_key=payload.target_upstream_step_key,
        challenged_section_key=payload.challenged_section_key,
        challenge_reason=payload.challenge_reason,
        target_profile_archetype=payload.target_profile_archetype,
        proposed_upstream_revision=payload.proposed_upstream_revision,
        trace_id=_trace(request),
        instance=str(request.url.path),
    )
    return UpstreamChallengeSubmitResponse(
        challenge=_serialize_challenge(record),
        preview=_serialize_preview(preview),
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/orchestration/runs/{run_id}/steps/{step_key}/replay",
    response_model=StepReplayResponse,
    summary="Replay workflow from Step N or intra-sub-workflow Step k (Story 3.5, FR-16, FR-30)",
    responses=PROBLEM_RESPONSES,
)
@router.post(
    "/api/v1/runs/{run_id}/steps/{step_key}/replay",
    response_model=StepReplayResponse,
    include_in_schema=False,
)
async def replay_workflow_from_step(
    request: Request,
    payload: StepReplayRequest | None = None,
    run_id: str = Path(..., min_length=1, max_length=128),
    step_key: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> StepReplayResponse:
    """Replay from Step $N$ (or intra-sub-workflow Step $k$) reusing $1..N-1$ snapshots."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_orchestration_service(request)
    eff = payload or StepReplayRequest()
    res = svc.engine.challenge_and_replay.replay_from_step(
        user,
        run_id=run_id,
        step_key=step_key,
        sub_workflow_step_key=eff.sub_workflow_step_key,
        revised_section_payload=eff.revised_section_payload,
        instance=str(request.url.path),
    )
    run = svc.engine._get_run(run_id, instance=str(request.url.path))
    await sync_replay_fork_to_sql(
        request,
        run=run,
        step_key=step_key,
        revised_payload=eff.revised_section_payload,
    )
    return StepReplayResponse(
        replay=_serialize_replay(res),
        trace_id=_trace(request),
    )
