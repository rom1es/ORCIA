"""Unit tests for Story 7.4: Post-Hoc Audit, `SM-A1..A3` Metrics & Kill-Switch (`AD-17`)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from orcia_connectors.autonomous_runner import (
    AutonomousActionRequest,
    AutonomousGateInput,
    execute_autonomous_contract_run,
)
from orcia_core.audit_finops import CognitiveImpactService, PostHocAuditService
from orcia_core.audit_finops._internal import sql_cognitive_impact
from orcia_core.audit_finops.post_hoc_audit_models import (
    clamp_sampling_rate,
    compute_autonomous_governance_metrics,
    select_post_hoc_sample_deterministic,
)
from orcia_core.catalog.contextual_help import (
    ContextualHelpResolutionService,
    HelpArticleCatalogItem,
)
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService
from orcia_core.permissions import (
    AutonomyContractService,
    HierarchicalRbacService,
    IamAccountRecord,
    SignAutonomyContractCommand,
)
from orcia_core.permissions.connector_invoker import ConnectorInvoker
from orcia_core.permissions.models import UserIdentity


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.deleted: list[str] = []

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def setex(self, key: str, ttl: int, val: str) -> None:
        del ttl
        self.store[key] = val

    def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            self.deleted.append(key)
            if key in self.store:
                del self.store[key]
                count += 1
        return count


class _FakeSecretProvider:
    async def resolve_secret(self, secret_ref: Any) -> str:
        return f"resolved-{secret_ref.uri}"  # pragma: allowlist secret


class _FakeConnector:
    async def execute_action(
        self, action_key: str, payload: dict[str, Any], secret_value: str | None = None
    ) -> dict[str, Any]:
        del secret_value
        return {"ok": True, "action": action_key, "payload": payload}


def test_deterministic_post_hoc_sampling_between_10_and_20_percent() -> None:
    """Sampling rate is clamped `[0.10, 0.20]` and SHA-256 selection hits ~15% deterministically."""
    assert clamp_sampling_rate(None) == Decimal("0.15")
    assert clamp_sampling_rate(Decimal("0.01")) == Decimal("0.10")
    assert clamp_sampling_rate(Decimal("0.99")) == Decimal("0.20")

    selected = sum(
        1
        for i in range(500)
        if select_post_hoc_sample_deterministic(
            run_id=f"0195f000-0000-7000-8000-{i:012d}",
            sampling_rate=Decimal("0.15"),
        )
    )
    assert 50 <= selected <= 105
    # Deterministic on repeat
    assert select_post_hoc_sample_deterministic(
        run_id="run-fixed-seed-1", sampling_rate=Decimal("0.15")
    ) == select_post_hoc_sample_deterministic(
        run_id="run-fixed-seed-1", sampling_rate=Decimal("0.15")
    )


def test_decimal_sm_a1_to_a3_metrics_and_alert_threshold() -> None:
    """`SM-A1`, `SM-A2` (alert >= 1%), and `SM-A3` compute exact `Decimal` ratios."""
    zero = compute_autonomous_governance_metrics(
        total_autonomous_runs=0,
        escalated_runs_count=0,
        killed_runs_count=0,
        sampled_runs_count=0,
        pending_samples_count=0,
        validated_samples_count=0,
        invalidated_samples_count=0,
        total_autonomous_cost_usd=Decimal("0"),
        total_ttm_gain_minutes=Decimal("0"),
    )
    assert zero.autonomous_escalation_rate == Decimal("0.0000")
    assert zero.post_hoc_invalidation_rate == Decimal("0.0000")
    assert zero.invalidation_alert is False

    alerted = compute_autonomous_governance_metrics(
        total_autonomous_runs=20,
        escalated_runs_count=3,
        killed_runs_count=1,
        sampled_runs_count=10,
        pending_samples_count=2,
        validated_samples_count=7,
        invalidated_samples_count=1,
        total_autonomous_cost_usd=Decimal("1.500000"),
        total_ttm_gain_minutes=Decimal("300.00"),
    )
    assert alerted.autonomous_escalation_rate == Decimal("0.1500")
    assert alerted.post_hoc_invalidation_rate == Decimal("0.1250")
    assert alerted.invalidation_alert is True
    assert alerted.avg_autonomous_cost_usd == Decimal("0.075000")
    assert alerted.avg_ttm_gain_minutes == Decimal("15.00")

    # Cognitive dashboard keeps SM-C1/C2 isolated from autonomous runs
    import inspect

    sql_src = inspect.getsource(sql_cognitive_impact)
    assert "execution_regime <> 'AUTONOMOUS_CONTRACT'" in sql_src
    post_hoc = PostHocAuditService()
    ws_id = new_uuid7_str()
    post_hoc.register_in_memory_run(
        run_id=new_uuid7_str(),
        workspace_id=ws_id,
        status="PAUSED_AUTONOMOUS_ESCALATION",
    )
    svc = CognitiveImpactService(post_hoc_service=post_hoc)
    import asyncio

    cog = asyncio.run(svc.get_dashboard(scope_type="WORKSPACE", scope_id=ws_id))
    assert cog.quick_pass_rate == 0.0
    assert cog.active_framing_ratio == 1.0
    assert cog.autonomous_governance is not None
    assert cog.autonomous_governance.total_autonomous_runs == 1
    assert cog.autonomous_governance.escalated_runs_count == 1


@pytest.mark.asyncio
async def test_supervision_kill_switch_step_boundary_and_help_rollback_redis_flush(
    tmp_path: Path,
) -> None:
    """Emergency Stop halts at step boundary & Invalidate/Restore rolls back `@v(N-1)` + Redis."""
    fake_redis = _FakeRedis()
    help_service = ContextualHelpResolutionService(repo_root=tmp_path, redis_client=fake_redis)
    article_id = "help.process.overview"
    v1 = HelpArticleCatalogItem(
        resource_id=article_id,
        uri="orcia://help/fr/processes",
        title="Guide Processus v1",
        version="1.0.0",
        lang="fr",
        layer="WORKSPACE",
        pack_name="core",
        bound_routes=("/processes",),
        summary_what_for="Version initiale valide",
        step_by_step_items=("Ouvrir les processus",),
        key_terms_items=(),
        faq_items=(),
        cas_key="cas/" + "1" * 64,
        sha256="1" * 64,
        markdown_body="# Guide v1",
    )
    help_service.upsert_seeded_article(v1)
    run_id = new_uuid7_str()
    ws_id = new_uuid7_str()
    wf_id = "orcia://pack-sdlc/workflows/generate-help"
    help_service.publish_hot_version(
        resource_id=article_id,
        new_version="1.1.0",
        new_title="Guide Processus Auto v1.1",
        new_summary_what_for="Brouillon autonome fautif",
        new_markdown_body="# Guide v1.1 auto",
        is_autonomous_generated=True,
        autonomous_run_id=run_id,
        contract_label="Contrat Docs Espace",
        trigger_label="Mise à jour nocturne",
    )
    # Prime Redis cache for /processes
    res_before = help_service.resolve_for_route(route="/processes", pack="core", lang="fr")
    fake_redis.setex(res_before.redis_cache_key, 3600, "1.1.0")
    assert res_before.is_autonomous_generated is True
    assert res_before.previous_version_available is True
    assert res_before.redis_cache_key in fake_redis.store
    assert res_before.redis_cache_key in help_service._redis_cache

    post_hoc = PostHocAuditService()
    sup = AutonomousSupervisionService(
        redis_client=fake_redis,
        post_hoc_service=post_hoc,
        help_service=help_service,
    )
    contract_id = new_uuid7_str()
    trig_id = new_uuid7_str()
    await sup.register_autonomous_run(
        run_id=run_id,
        workspace_id=ws_id,
        workflow_id=wf_id,
        contract_id=contract_id,
        status="COMMITTED_AUTONOMOUS",
        trigger_id=trig_id,
        trigger_label="Mise à jour nocturne",
        help_resource_id=article_id,
        force_post_hoc_sample=True,
    )
    assert len(sup.notifications) == 1
    assert sup.notifications[0].notification_type == "POST_HOC_AUDIT_SAMPLE"

    # 1-click Invalidate & Restore @v(N-1)
    rb = await sup.invalidate_and_restore(
        run_id=run_id, actor_user_id="usr-lead-1", comment="Contenu erroné"
    )
    assert rb.status == "ROLLED_BACK"
    assert rb.restored_version == "1.0.0"
    assert rb.redis_cache_invalidated_ms < 10.0
    assert rb.sse_dispatch_latency_ms < 500.0
    assert res_before.redis_cache_key not in fake_redis.store
    res_after = help_service.resolve_for_route(route="/processes", pack="core", lang="fr")
    assert res_after.active_article.version == "1.0.0"
    assert res_after.is_autonomous_generated is False

    # Emergency Stop halts autonomous runner at step boundary
    stopped_run_id = new_uuid7_str()
    await sup.register_autonomous_run(
        run_id=stopped_run_id,
        workspace_id=ws_id,
        workflow_id=wf_id,
        contract_id=contract_id,
        status="RUNNING",
        trigger_id=trig_id,
        trigger_label="Mise à jour nocturne",
    )
    stop_out = await sup.emergency_stop(
        run_id=stopped_run_id,
        actor_user_id="usr-lead-1",
        reason="Arrêt opérateur",
        suspend_trigger=True,
    )
    assert stop_out.status == "KILL_SWITCH_STOPPED"
    assert stop_out.trigger_suspended is True
    assert stop_out.sse_dispatch_latency_ms < 500.0
    assert await sup.is_run_stopped(stopped_run_id) is True

    # Autonomous runner respects kill_switch_check_fn at step boundary
    contract_svc = AutonomyContractService(rbac_service=HierarchicalRbacService())
    sp = IamAccountRecord(
        id=new_uuid7_str(),
        principal_id="sp-docs",
        display_name="Robot Docs",
        email=None,
        account_kind="SERVICE_PRINCIPAL",
        auth_source="SERVICE_TOKEN",
        roles=("TEAM_LEAD",),
        team_ids=(ws_id,),
        status="ACTIVE",
        created_at_iso="2026-11-17T00:00:00Z",
    )
    lead = UserIdentity(
        id="lead-1",
        email="lead@orcia.local",
        display_name="Lead",
        auth_mode="LOCAL",
        human_profile_archetype="Tech Lead",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id=ws_id,
        roles=("PLATFORM_ADMIN", "TEAM_LEAD"),
    )
    contract = await contract_svc.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id=wf_id,
            workflow_version="1.0.0",
            workflow_sha256="a" * 64,
            criticality="LOW_NON_CRITICAL",
            service_principal_id=sp.id,
            allowed_read_sources=("catalog:read",),
            allowed_write_actions=("catalog:write",),
            max_cost_per_run_usd=5.0,
        ),
        signer=lead,
        service_principal=sp,
    )
    runner_out, _runner_events = await execute_autonomous_contract_run(
        run_id=stopped_run_id,
        contract=contract,
        criticality="LOW_NON_CRITICAL",
        actions=[AutonomousActionRequest(action_key="catalog:write", payload={"doc": "v2"})],
        gates=AutonomousGateInput(),
        connector_invoker=ConnectorInvoker(),
        kill_switch_check_fn=sup.is_run_stopped,
    )
    assert runner_out.status == "KILL_SWITCH_STOPPED"
    assert runner_out.executed_actions == []

    metrics = await post_hoc.get_autonomous_governance_metrics(
        scope_type="WORKSPACE", scope_id=ws_id
    )
    assert metrics.total_autonomous_runs == 2
    assert metrics.killed_runs_count == 1
    assert metrics.invalidated_samples_count == 1
    assert metrics.invalidation_alert is True

    # Escalation notification + list + post_hoc_review VALIDATED / INVALIDATED + 404
    esc_run_id = new_uuid7_str()
    await sup.register_autonomous_run(
        run_id=esc_run_id,
        workspace_id=ws_id,
        workflow_id=wf_id,
        contract_id=contract_id,
        status="PAUSED_AUTONOMOUS_ESCALATION",
        trigger_id=trig_id,
        trigger_label="Escalade règle métier",
    )
    assert any(n.notification_type == "AUTONOMOUS_ESCALATION" for n in sup.notifications)
    listed = await sup.list_autonomous_runs(workspace_id=ws_id)
    assert len(listed) == 3

    sample_run_id = new_uuid7_str()
    await sup.register_autonomous_run(
        run_id=sample_run_id,
        workspace_id=ws_id,
        workflow_id=wf_id,
        contract_id=contract_id,
        status="COMMITTED_AUTONOMOUS",
        trigger_id=trig_id,
        force_post_hoc_sample=True,
    )
    val_res = await sup.review_post_hoc_sample(
        run_id=sample_run_id, actor_user_id="usr-lead-1", decision="VALIDATED", comment="OK"
    )
    assert val_res["review_status"] == "VALIDATED"

    inv_run_id = new_uuid7_str()
    await sup.register_autonomous_run(
        run_id=inv_run_id,
        workspace_id=ws_id,
        workflow_id=wf_id,
        contract_id=contract_id,
        status="COMMITTED_AUTONOMOUS",
        trigger_id=trig_id,
        force_post_hoc_sample=True,
    )
    inv_res = await sup.review_post_hoc_sample(
        run_id=inv_run_id,
        actor_user_id="usr-lead-1",
        decision="INVALIDATED_ROLLED_BACK",
        comment="Ko",
    )
    assert inv_res["review_status"] == "INVALIDATED_ROLLED_BACK"
    assert len(sup.outbox_events) >= 2
    assert len(post_hoc.outbox_events) >= 3

    from orcia_kernel.errors import ResourceNotFoundError

    with pytest.raises(ResourceNotFoundError):
        await sup.emergency_stop(run_id=new_uuid7_str(), actor_user_id="usr-lead-1")
    with pytest.raises(ResourceNotFoundError):
        await sup.invalidate_and_restore(run_id=new_uuid7_str(), actor_user_id="usr-lead-1")
