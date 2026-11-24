"""Async and Sync Replay Executors for `UpstreamChallengeAndReplayService` (`Story 3.5`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from orcia_core.orchestration._challenge_replay_models import (
    StepReplayResult,
    commit_sub_workflow_replay_parent,
    prepare_replay_scope,
)
from orcia_core.orchestration.errors import ValidationDomainError
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from orcia_core.orchestration.challenge_and_replay import UpstreamChallengeAndReplayService


async def execute_replay_async(
    svc: UpstreamChallengeAndReplayService,
    user: UserIdentity,
    *,
    run_id: str,
    step_key: str,
    sub_workflow_step_key: str | None = None,
    revised_section_payload: dict[str, Any] | None = None,
    instance: str | None = None,
) -> StepReplayResult:
    """Async replay from Step $N$ reusing $1..N-1$ snapshots without blocking event loop."""
    run, wf, target_idx, reused, superseded = prepare_replay_scope(
        svc.engine, user, run_id=run_id, step_key=step_key, instance=instance
    )
    all_superseded = list(superseded)
    new_active: list[str] = []
    target_spec = wf.steps[target_idx]
    if sub_workflow_step_key is not None:
        if target_spec.step_type != "SUB_WORKFLOW" or not target_spec.sub_workflow_uri:
            raise ValidationDomainError(
                detail_code="ERR_REPLAY_STEP_NOT_SUB_WORKFLOW",
                detail_params={"step_key": step_key, "sub_step": sub_workflow_step_key},
                instance=instance,
            )
        p_exec = svc.engine.blackboard.get_step_execution(run.id, step_key)
        if not p_exec.child_run_id:
            await svc.engine.execute_step_async(
                user, run_id=run.id, step_key=step_key, commit_immediately=True
            )
            p_exec = svc.engine.blackboard.get_step_execution(run.id, step_key)
        assert p_exec.child_run_id is not None
        child_res = await execute_replay_async(
            svc,
            user,
            run_id=p_exec.child_run_id,
            step_key=sub_workflow_step_key,
            revised_section_payload=revised_section_payload,
            instance=instance,
        )
        reused = (*reused, *child_res.reused_upstream_snapshot_ids)
        all_superseded.extend(child_res.superseded_snapshot_ids)
        new_active.extend(child_res.new_active_snapshot_ids)
        new_active.append(
            commit_sub_workflow_replay_parent(
                svc.engine,
                run=run,
                step_key=step_key,
                target_spec=target_spec,
                sub_workflow_step_key=sub_workflow_step_key,
                parent_step_exec=p_exec,
                reused_upstream_ids=reused,
                superseded_parent_ids=superseded,
            )
        )
        start_idx = target_idx + 1
    else:
        start_idx = target_idx
    for idx in range(start_idx, len(wf.steps)):
        cur = wf.steps[idx]
        cur_exec = svc.engine.blackboard.get_step_execution(run.id, cur.step_key)
        if idx > target_idx and cur_exec.status == "PENDING" and not cur_exec.committed_snapshot_id:
            break
        _, snap = await svc.engine.execute_step_async(
            user,
            run_id=run.id,
            step_key=cur.step_key,
            commit_immediately=True,
            executor_metadata={"revised_section_payload": revised_section_payload}
            if idx == target_idx and revised_section_payload
            else None,
            cost_usd=0.1,
            instance=instance,
        )
        if snap is not None:
            new_active.append(snap.id)
    return svc._finish_replay(
        run=run,
        step_key=step_key,
        sub_workflow_step_key=sub_workflow_step_key,
        reused=reused,
        superseded=all_superseded,
        new_active=new_active,
    )


def execute_replay_sync(
    svc: UpstreamChallengeAndReplayService,
    user: UserIdentity,
    *,
    run_id: str,
    step_key: str,
    sub_workflow_step_key: str | None = None,
    revised_section_payload: dict[str, Any] | None = None,
    instance: str | None = None,
) -> StepReplayResult:
    """Sync replay from Step $N$ reusing $1..N-1$ snapshots."""
    run, wf, target_idx, reused, superseded = prepare_replay_scope(
        svc.engine, user, run_id=run_id, step_key=step_key, instance=instance
    )
    all_superseded = list(superseded)
    new_active: list[str] = []
    target_spec = wf.steps[target_idx]
    if sub_workflow_step_key is not None:
        if target_spec.step_type != "SUB_WORKFLOW" or not target_spec.sub_workflow_uri:
            raise ValidationDomainError(
                detail_code="ERR_REPLAY_STEP_NOT_SUB_WORKFLOW",
                detail_params={"step_key": step_key, "sub_step": sub_workflow_step_key},
                instance=instance,
            )
        p_exec = svc.engine.blackboard.get_step_execution(run.id, step_key)
        if not p_exec.child_run_id:
            svc.engine.execute_step(user, run_id=run.id, step_key=step_key, commit_immediately=True)
            p_exec = svc.engine.blackboard.get_step_execution(run.id, step_key)
        assert p_exec.child_run_id is not None
        child_res = execute_replay_sync(
            svc,
            user,
            run_id=p_exec.child_run_id,
            step_key=sub_workflow_step_key,
            revised_section_payload=revised_section_payload,
            instance=instance,
        )
        reused = (*reused, *child_res.reused_upstream_snapshot_ids)
        all_superseded.extend(child_res.superseded_snapshot_ids)
        new_active.extend(child_res.new_active_snapshot_ids)
        new_active.append(
            commit_sub_workflow_replay_parent(
                svc.engine,
                run=run,
                step_key=step_key,
                target_spec=target_spec,
                sub_workflow_step_key=sub_workflow_step_key,
                parent_step_exec=p_exec,
                reused_upstream_ids=reused,
                superseded_parent_ids=superseded,
            )
        )
        start_idx = target_idx + 1
    else:
        start_idx = target_idx
    for idx in range(start_idx, len(wf.steps)):
        cur = wf.steps[idx]
        cur_exec = svc.engine.blackboard.get_step_execution(run.id, cur.step_key)
        if idx > target_idx and cur_exec.status == "PENDING" and not cur_exec.committed_snapshot_id:
            break
        _, snap = svc.engine.execute_step(
            user,
            run_id=run.id,
            step_key=cur.step_key,
            commit_immediately=True,
            executor_metadata={"revised_section_payload": revised_section_payload}
            if idx == target_idx and revised_section_payload
            else None,
            cost_usd=0.1,
            instance=instance,
        )
        if snap is not None:
            new_active.append(snap.id)
    return svc._finish_replay(
        run=run,
        step_key=step_key,
        sub_workflow_step_key=sub_workflow_step_key,
        reused=reused,
        superseded=all_superseded,
        new_active=new_active,
    )
