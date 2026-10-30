"""Tests unitaires, basés sur les propriétés (Hypothesis) et contrats HTTP pour l'Epic 8 (AD-21).

Couvre :
- Story 8.1 + ACTION_ITEM-8.1..8.3 : RBAC/ABAC à 6 verbes, héritage d'arbre, priorité DENY,
  inheritance_block, ABAC execute (env, max_tokens_per_run), hidden_when_unauthorized (404) vs
  découverte passive + AccessRequested, confinement de grant (403 ERR_GRANT_ESCALATION_FORBIDDEN),
  anti-lockout (422 ERR_ADMIN_LOCKOUT_PREVENTED) et révocation en frontière de step.
- Story 8.2 + PROC-01 : Tiers cognitifs (simple|medium|complex|auto) & effort, escalade auto
  déterministe persistée de façon idempotente dans inference_attempts, orthogonalité AD-10,
  plafonds budgétaires hiérarchiques, garde 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS
  et workflow durable PROC-01 de bout en bout (start -> auto escalation -> pause -> replay).
- Story 8.3 + DEC-SEC-01 : platform_settings versionnés If-Match/ETag (428/412), protocole
  SecretInput/SecretStatus, test canari DEC-SEC-01 (zéro fuite de secret en clair)
  et replay Outbox borné (<= 500, dry_run=True par défaut).
- Story 8.4 : Hub des connecteurs, healthcheck fail-fast (< 5 s), garde C0-C2 vs C3 (403),
  fail-fast OCR 0 caractère (422 ERR_EMPTY_OR_UNREADABLE_DOCUMENT), détection PII + arbitrage humain
  à 3 choix, et test de réciprocité RAG 1-clic avec citation obligatoire.
- Story 8.5 : Studio Visuel 5 onglets, fork immuable SemVer (v1.0.0 -> v1.1.0-draft), contrat,
  inspecteur COUCHES · N (enabled=False -> SKIPPED), dry-run isolé (0 écriture externe), et Registre
  des Packs Métiers (ACTIVE, DRAINING, ORPHANED).
- Story 8.6 : 3 Wizards durables DBOS (sdlc_tech_lead, ops_manager, secops_admin), reprise exacte à
  l'étape 3/5 après déconnexion, persistance SecretRef uniquement, provisionnement Démo
  et migration Alembic 0022_epic_8.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from orcia_api.main import create_app
from orcia_core.bootstrap.durable_wizards import DurableOnboardingWizardService
from orcia_core.bootstrap.seeder import (
    PLATFORM_SETTINGS_UPSERT_SPEC,
    ROLE_PERMISSION_GRANTS_UPSERT_SPEC,
    WIZARD_SESSIONS_UPSERT_SPEC,
    WORKSPACE_LLM_TIER_MAPPINGS_UPSERT_SPEC,
    build_postgres_upsert_sql,
)
from orcia_core.orchestration.cognitive_router import (
    CognitiveModelRouterService,
    ResolvedInferenceTier,
)
from orcia_core.orchestration.errors import (
    ResourcePinnedByActiveRunsError,
)
from orcia_core.orchestration.studio_and_packs import (
    WorkflowStudioAndPackService,
)
from orcia_core.permissions.errors import (
    AdminLockoutPreventedError,
    C3WorkspaceRequiredError,
    GrantEscalationForbiddenError,
    PreconditionRequiredError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    SecretConfigReadDeniedError,
    SettingsVersionConflictError,
)
from orcia_core.permissions.hierarchical_rbac import (
    ALL_PERMISSION_VERBS,
    HierarchicalRbacService,
    RolePermissionGrant,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.platform_settings import (
    PlatformSettingsService,
    SecretInputSpec,
)
from orcia_core.rag.connector_hub_and_ingestion import ConnectorHubAndIngestionService
from orcia_core.rag.errors import EmptyOrUnreadableDocumentError
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.errors import ModelOrthogonalityViolationError


def _make_user(
    user_id: str,
    role: str = "PLATFORM_ADMIN",
) -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=f"{user_id}@orcia.local",
        display_name=user_id,
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id="0195f000-0000-7000-8000-000000000101",
    )


def test_story_8_1_hierarchical_rbac_inheritance_deny_abac_and_confinement() -> None:
    admin_user = _make_user("0195f000-0000-7000-8000-000000000201", "PLATFORM_ADMIN")
    lead_user = _make_user("user-team-lead", "TEAM_LEAD")

    svc = HierarchicalRbacService(
        initial_grants=(
            RolePermissionGrant(
                id="grant-root-all",
                subject_type="USER",
                subject_id=admin_user.id,
                scope_path="org/orcia",
                verb="grant",
            ),
        ),
    )

    # Admin delegates read, execute (with ABAC conditions), and grant on team/checkout to lead_user
    delegated = svc.delegate_grant(
        admin_user,
        subject_type="USER",
        subject_id=lead_user.id,
        scope_path="org/orcia/bu/retail/team/checkout",
        verbs=("read", "execute", "grant"),
        conditions={
            "allowed_environments": ["staging", "prod"],
            "max_tokens_per_run": 50_000,
        },
    )
    assert len(delegated) == 3

    # Inheritance down the tree + ABAC conditions on execute
    effective_ok = svc.resolve_effective_verbs(
        subject_id=lead_user.id,
        scope_path="org/orcia/bu/retail/team/checkout/workspace/payments",
        context={"env": "staging", "requested_tokens": 20_000},
    )
    assert "execute" in effective_ok
    assert "read" in effective_ok

    # ABAC env mismatch or token ceiling exceeded -> execute not granted
    effective_bad_env = svc.resolve_effective_verbs(
        subject_id=lead_user.id,
        scope_path="org/orcia/bu/retail/team/checkout/workspace/payments",
        context={"env": "sandbox", "requested_tokens": 20_000},
    )
    assert "execute" not in effective_bad_env

    effective_bad_tokens = svc.resolve_effective_verbs(
        subject_id=lead_user.id,
        scope_path="org/orcia/bu/retail/team/checkout/workspace/payments",
        context={"env": "staging", "requested_tokens": 80_000},
    )
    assert "execute" not in effective_bad_tokens

    # Bounded delegation confinement: lead_user cannot delegate 'delete' (not held)
    with pytest.raises(GrantEscalationForbiddenError) as exc_info:
        svc.delegate_grant(
            lead_user,
            subject_type="USER",
            subject_id="user-dev",
            scope_path="org/orcia/bu/retail/team/checkout/workspace/payments",
            verbs=("delete",),
        )
    assert exc_info.value.error_code == "ERR_GRANT_ESCALATION_FORBIDDEN"
    assert exc_info.value.http_status == 403

    # Explicit DENY overrides inherited ALLOW
    svc.delegate_grant(
        admin_user,
        subject_type="USER",
        subject_id=lead_user.id,
        scope_path="org/orcia/bu/retail/team/checkout/workspace/payments",
        verbs=("read",),
        effect="DENY",
    )
    after_deny = svc.resolve_effective_verbs(
        subject_id=lead_user.id,
        scope_path="org/orcia/bu/retail/team/checkout/workspace/payments",
        context={"env": "staging", "requested_tokens": 10_000},
    )
    assert "read" not in after_deny

    # Confidential C3 inheritance_block clears ancestor grants
    svc.delegate_grant(
        admin_user,
        subject_type="USER",
        subject_id=lead_user.id,
        scope_path="org/orcia/bu/retail/team/checkout/workspace/c3-vault",
        verbs=("read",),
        effect="DENY",
        inheritance_block=True,
    )
    after_block = svc.resolve_effective_verbs(
        subject_id=lead_user.id,
        scope_path="org/orcia/bu/retail/team/checkout/workspace/c3-vault",
        context={"env": "staging", "requested_tokens": 10_000},
    )
    assert after_block == set()


def test_story_8_1_discovery_404_vs_passive_lock_anti_lockout_and_step_boundary() -> None:
    sole_admin = _make_user("0195f000-0000-7000-8000-000000000201", "PLATFORM_ADMIN")
    visitor = _make_user("user-visitor", "CONTRIBUTOR")

    svc = HierarchicalRbacService(
        initial_grants=(
            RolePermissionGrant(
                id="grant-sole-admin",
                subject_type="USER",
                subject_id=sole_admin.id,
                scope_path="org/orcia",
                verb="grant",
            ),
            RolePermissionGrant(
                id="grant-exec-only",
                subject_type="USER",
                subject_id=visitor.id,
                scope_path="org/orcia/bu/claims/workspace/ws-1/resource/conn-1",
                verb="execute",
            ),
        ),
        active_platform_admin_ids={sole_admin.id},
        active_auth_methods={"LOCAL"},
    )

    # Anti-lockout prevents revoking last admin grant, removing last admin, or disabling last auth
    with pytest.raises(AdminLockoutPreventedError) as lockout_exc:
        svc.revoke_grant(sole_admin, "grant-sole-admin")
    assert lockout_exc.value.error_code == "ERR_ADMIN_LOCKOUT_PREVENTED"
    assert lockout_exc.value.http_status == 422

    with pytest.raises(AdminLockoutPreventedError):
        svc.remove_platform_admin(sole_admin, sole_admin.id)

    with pytest.raises(AdminLockoutPreventedError):
        svc.disable_auth_method(sole_admin, "LOCAL")

    # Execute without read -> SecretConfigReadDeniedError (403) when requesting secret config read
    with pytest.raises(SecretConfigReadDeniedError) as sec_exc:
        svc.evaluate_resource_access(
            subject_id=visitor.id,
            scope_path="org/orcia/bu/claims/workspace/ws-1/resource/conn-1",
            require_secret_read=True,
        )
    assert sec_exc.value.http_status == 403

    # Hidden when unauthorized -> 404 ResourceNotFoundError
    svc.set_scope_hidden_when_unauthorized(
        "org/orcia/bu/claims/workspace/ws-c3/resource/hidden",
        hidden=True,
    )
    with pytest.raises(ResourceNotFoundError) as nf_exc:
        svc.evaluate_resource_access(
            subject_id=visitor.id,
            scope_path="org/orcia/bu/claims/workspace/ws-c3/resource/hidden",
        )
    assert nf_exc.value.http_status == 404

    # Passive discovery -> locked=True, can_request_access=True + AccessRequested Outbox event
    passive = svc.evaluate_resource_access(
        subject_id=visitor.id,
        scope_path="org/orcia/bu/claims/workspace/ws-1/resource/shared-kb",
        title="Shared KB",
    )
    assert passive.locked is True
    assert passive.can_request_access is True
    req_evt = svc.request_access(
        visitor,
        scope_path="org/orcia/bu/claims/workspace/ws-1/resource/shared-kb",
        requested_verb="execute",
        justification="Need KB access for audit",
    )
    assert req_evt.event_type == "AccessRequested"

    # Step-boundary revocation blocks the next @DBOS.step boundary
    svc.enforce_step_boundary_execution_guard(
        subject_id=visitor.id,
        subject_type="USER",
        scope_path="org/orcia/bu/claims/workspace/ws-1/resource/conn-1",
    )
    svc.revoke_subject_immediately(sole_admin, visitor.id)
    with pytest.raises(ScopeAccessDeniedError):
        svc.enforce_step_boundary_execution_guard(
            subject_id=visitor.id,
            subject_type="USER",
            scope_path="org/orcia/bu/claims/workspace/ws-1/resource/conn-1",
        )


@given(
    has_deny=st.booleans(),
    inheritance_blocked=st.booleans(),
    direct_allow=st.booleans(),
)
@settings(max_examples=25)
def test_story_8_1_hypothesis_rbac_precedence_invariants(
    has_deny: bool,
    inheritance_blocked: bool,
    direct_allow: bool,
) -> None:
    grants: list[RolePermissionGrant] = [
        RolePermissionGrant(
            id="g-parent",
            subject_type="USER",
            subject_id="u1",
            scope_path="org/orcia",
            verb="read",
        )
    ]
    if inheritance_blocked:
        grants.append(
            RolePermissionGrant(
                id="g-block",
                subject_type="USER",
                subject_id="u1",
                scope_path="org/orcia/bu/claims",
                verb="execute",
                inheritance_block=True,
            )
        )
    if direct_allow:
        grants.append(
            RolePermissionGrant(
                id="g-direct",
                subject_type="USER",
                subject_id="u1",
                scope_path="org/orcia/bu/claims",
                verb="read",
                effect="ALLOW",
            )
        )
    if has_deny:
        grants.append(
            RolePermissionGrant(
                id="g-deny",
                subject_type="USER",
                subject_id="u1",
                scope_path="org/orcia/bu/claims",
                verb="read",
                effect="DENY",
            )
        )

    svc = HierarchicalRbacService(initial_grants=tuple(grants))
    verbs = svc.resolve_effective_verbs(
        subject_id="u1",
        scope_path="org/orcia/bu/claims",
    )
    if has_deny:
        assert "read" not in verbs
    elif direct_allow:
        assert "read" in verbs
    elif inheritance_blocked:
        assert "read" not in verbs
    else:
        assert "read" in verbs
    assert verbs.issubset(set(ALL_PERMISSION_VERBS))


def test_story_8_2_cognitive_router_tiers_idempotency_orthogonality_and_proc01() -> None:
    llm = DeterministicCassetteLLM()
    router = CognitiveModelRouterService(llm_gateway=llm)
    ws_id = "0195f000-0000-7000-8000-000000000301"

    # Orthogonality violation if generator and evaluator share the same model family
    with pytest.raises(ModelOrthogonalityViolationError):
        asyncio.run(
            router.execute_with_tier_routing(
                run_id="run-orth-fail",
                step_execution_id="step-orth",
                scope_id=ws_id,
                system_prompt="System",
                user_prompt="Prompt",
                inference_tier="simple",
                evaluator_model_family="anthropic-claude",
            )
        )

    # Auto escalation simple -> medium + DBOS replay idempotency
    def _gate_fail_simple(_content: str, tier: ResolvedInferenceTier) -> tuple[bool, str]:
        if tier == "simple":
            return False, "Simple tier failed schema validation"
        return True, ""

    outcome1 = asyncio.run(
        router.execute_with_tier_routing(
            run_id="run-auto-1",
            step_execution_id="step-auto-1",
            scope_id=ws_id,
            system_prompt="System",
            user_prompt="Escalation test",
            inference_tier="auto",
            effort="deep",
            deterministic_gate_fn=_gate_fail_simple,
        )
    )
    assert outcome1.final_resolved_tier == "medium"
    assert len(outcome1.attempts) == 2

    # Replay with same (run_id, step_execution_id) returns stored attempts without re-running
    outcome_replayed = asyncio.run(
        router.execute_with_tier_routing(
            run_id="run-auto-1",
            step_execution_id="step-auto-1",
            scope_id=ws_id,
            system_prompt="System",
            user_prompt="Escalation test",
            inference_tier="auto",
            effort="deep",
            deterministic_gate_fn=_gate_fail_simple,
        )
    )
    assert outcome_replayed.attempts[0].id == outcome1.attempts[0].id
    assert outcome_replayed.attempts[1].id == outcome1.attempts[1].id

    # Hierarchical budget ceiling pause
    router.set_scope_budget_ceiling("bu:exhausted", 0.0)
    budget_paused = asyncio.run(
        router.execute_with_tier_routing(
            run_id="run-budget",
            step_execution_id="step-budget",
            scope_id=ws_id,
            system_prompt="System",
            user_prompt="Budget check",
            inference_tier="simple",
            scope_hierarchy_ids=("bu:exhausted",),
        )
    )
    assert budget_paused.paused_budget_exceeded is True

    # Full PROC-01 durable lifecycle verification
    paused_proc01 = asyncio.run(
        router.start_proc01_durable_run(
            workspace_id=ws_id,
            user_prompt="Execute durable PROC-01",
            effort="balanced",
        )
    )
    assert paused_proc01.status == "WAITING_FOR_HUMAN_ARBITRATION"
    assert paused_proc01.step_1_outcome.final_resolved_tier == "medium"

    completed_proc01 = asyncio.run(
        router.replay_and_resume_proc01_run(
            run_id=paused_proc01.run_id,
            arbitration_choice="APPROVE_ARCHITECTURE",
        )
    )
    assert completed_proc01.status == "COMPLETED"
    assert completed_proc01.replayed_after_restart is True
    assert completed_proc01.final_artifact["verified_tier"] == "medium"

    # Active run pinning guard (409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS)
    mapping_id = "0195f000-0000-7000-8000-000000008201"
    router.pin_mapping_for_active_run(mapping_id, "run-active-99")
    with pytest.raises(ResourcePinnedByActiveRunsError) as pin_exc:
        router.delete_or_drain_mapping(mapping_id, mode="reject")
    assert pin_exc.value.error_code == "ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS"
    assert pin_exc.value.http_status == 409

    drained = router.delete_or_drain_mapping(mapping_id, mode="drain")
    assert drained is not None and drained.draining is True


def test_story_8_3_platform_settings_etag_canary_secret_and_outbox_replay() -> None:
    svc = PlatformSettingsService()
    admin_user = _make_user("user-admin", "PLATFORM_ADMIN")
    canary_secret = "CANARY_SUPER_SECRET_VALUE_9988776655"  # pragma: allowlist secret

    initial = svc.upsert_initial_setting(
        scope_level="WORKSPACE",
        scope_id="ws-payments",
        category="connectors",
        key="primary-repo",
        value_jsonb={"endpoint": "orcia://connectors/primary-repo"},
        secret_input=SecretInputSpec(action="set", plaintext_value=canary_secret),
        actor_id=admin_user.id,
    )
    assert initial.version == 1
    assert initial.secret_status.configured is True
    assert initial.secret_status.fingerprint is not None
    assert initial.secret_status.fingerprint.startswith("sha256:")

    # Missing If-Match -> 428 ERR_PRECONDITION_REQUIRED
    with pytest.raises(PreconditionRequiredError) as pre_exc:
        svc.patch_setting(
            admin_user,
            scope_level="WORKSPACE",
            scope_id="ws-payments",
            category="connectors",
            key="primary-repo",
            value_jsonb={"endpoint": "orcia://connectors/primary-repo-v2"},
            if_match=None,
        )
    assert pre_exc.value.http_status == 428

    # Stale If-Match -> 412 ERR_SETTINGS_VERSION_CONFLICT
    with pytest.raises(SettingsVersionConflictError) as conflict_exc:
        svc.patch_setting(
            admin_user,
            scope_level="WORKSPACE",
            scope_id="ws-payments",
            category="connectors",
            key="primary-repo",
            value_jsonb={"endpoint": "orcia://connectors/primary-repo-v2"},
            if_match='W/"0-stale"',
        )
    assert conflict_exc.value.http_status == 412

    # Valid If-Match updates version and emits SettingsChanged Outbox event
    updated = svc.patch_setting(
        admin_user,
        scope_level="WORKSPACE",
        scope_id="ws-payments",
        category="connectors",
        key="primary-repo",
        value_jsonb={"endpoint": "orcia://connectors/primary-repo-v2"},
        if_match=initial.etag,
        secret_input=SecretInputSpec(action="set", plaintext_value=canary_secret),
    )
    assert updated.version == 2
    assert updated.etag != initial.etag

    # DEC-SEC-01 Canary test: plaintext secret MUST NEVER appear in settings or Outbox
    assert canary_secret not in repr(updated)
    assert len(svc.outbox_events) == 1
    assert svc.outbox_events[0].event_type == "SettingsChanged"
    assert canary_secret not in repr(svc.outbox_events[0])
    assert canary_secret not in str(svc.outbox_events[0].to_outbox_dict())

    # Bounded Outbox replay (<= 500 events, dry_run=True by default)
    dry_replay = svc.replay_outbox_events(
        admin_user,
        consumer_name="audit_finops",
    )
    assert dry_replay.dry_run is True
    assert dry_replay.scanned_count == 1
    assert dry_replay.replayed_count == 0

    applied_replay = svc.replay_outbox_events(
        admin_user,
        consumer_name="audit_finops",
        dry_run=False,
        max_events=500,
    )
    assert applied_replay.replayed_count == 1


def test_story_8_4_connector_hub_fail_fast_ocr_pii_c3_and_reciprocity() -> None:
    hub = ConnectorHubAndIngestionService()
    lead_user = _make_user("user-lead", "TEAM_LEAD")
    std_ws = "0195f000-0000-7000-8000-000000000301"
    secret_val = "kb-token-xyz"  # pragma: allowlist secret

    conn = hub.upsert_connector(
        lead_user,
        workspace_id=std_ws,
        alias="primary-kb",
        scheme="orcia",
        uri="orcia://connectors/primary-kb",
        secret_input=SecretInputSpec(action="set", plaintext_value=secret_val),
    )
    assert conn.secret_status.configured is True

    # Fail-fast connection test (< 5 s)
    hc_ok = hub.test_connector_connection(lead_user, conn.id)
    assert hc_ok.status == "HEALTHY"
    assert hc_ok.timeout_budget_ms == 5000

    hc_unreach = hub.test_connector_connection(
        lead_user,
        conn.id,
        simulated_status="UNREACHABLE",
    )
    assert hc_unreach.status == "UNREACHABLE"

    # C3 document in standard workspace -> 403 ERR_C3_WORKSPACE_REQUIRED
    with pytest.raises(C3WorkspaceRequiredError):
        hub.ingest_document_with_guardrails(
            lead_user,
            workspace_id=std_ws,
            uri="orcia://connectors/primary-kb/secret-board-notes",
            title="Board Notes",
            raw_extracted_text="Board notes content",
            classification="C3_CONFIDENTIAL_RESTRICTED",
        )

    # 0-character unreadable scan -> 422 ERR_EMPTY_OR_UNREADABLE_DOCUMENT
    with pytest.raises(EmptyOrUnreadableDocumentError) as ocr_exc:
        hub.ingest_document_with_guardrails(
            lead_user,
            workspace_id=std_ws,
            uri="orcia://connectors/primary-kb/blank-scan.pdf",
            title="Blank Scan",
            raw_extracted_text="   \n\t  ",
            classification="C0_C2_STANDARD",
        )
    assert ocr_exc.value.error_code == "ERR_EMPTY_OR_UNREADABLE_DOCUMENT"
    assert ocr_exc.value.http_status == 422

    # PII detection pauses for 3-choice Human Arbitration, then PSEUDONYMIZE indexes masked content
    pii_paused = hub.ingest_document_with_guardrails(
        lead_user,
        workspace_id=std_ws,
        uri="orcia://connectors/primary-kb/customer-ticket",
        title="Customer Ticket",
        raw_extracted_text="Contact client jean.dupont@example.com pour vérification.",
        classification="C0_C2_STANDARD",
    )
    assert pii_paused.status == "WAITING_FOR_PII_ARBITRATION"
    assert "EMAIL" in pii_paused.pii_categories

    pii_masked = hub.ingest_document_with_guardrails(
        lead_user,
        workspace_id=std_ws,
        uri="orcia://connectors/primary-kb/customer-ticket",
        title="Customer Ticket",
        raw_extracted_text="Contact client jean.dupont@example.com pour vérification.",
        classification="C0_C2_STANDARD",
        pii_decision="PSEUDONYMIZE",
        document_id=pii_paused.document_id,
    )
    assert pii_masked.status == "INDEXED"
    assert pii_masked.pseudonymized is True

    # 1-Click RAG Reciprocity Test returns mandatory URI + chunk citation
    reciprocity = hub.verify_rag_reciprocity(pii_masked.document_id)
    assert reciprocity.passed is True
    assert reciprocity.cited_uri == "orcia://connectors/primary-kb/customer-ticket"
    assert reciprocity.cited_chunk_id != ""
    assert "[PII_EMAIL_REDACTED]" in reciprocity.response_markdown


def test_story_8_5_visual_studio_fork_layers_dryrun_and_pack_registry() -> None:
    studio = WorkflowStudioAndPackService()
    seed_rev_id = "0195f000-0000-7000-8000-000000008501"

    # Editing a PUBLISHED revision creates an immutable SemVer draft fork (v1.0.0 -> v1.1.0-draft)
    draft = studio.fork_published_to_draft(seed_rev_id)
    assert draft.version == "v1.1.0-draft"
    assert draft.lifecycle_tab == "DRAFT"

    # Toggle layer enabled=False -> runtime marks it SKIPPED without breaking parent DAG
    studio.update_sub_workflow_layer(
        draft.id,
        step_key="step-02-macro-analysis",
        layer_id="layer-02",
        enabled=False,
    )
    dry_run = studio.run_what_if_dry_run(
        draft.id,
        input_values={"p_1": "scope-a", "p_2": "STANDARD"},
    )
    assert dry_run.deterministic_structure_gate_passed is True
    assert dry_run.external_writes_count == 0
    assert "step-02-macro-analysis:layer-02:SKIPPED" in dry_run.skipped_layers

    # Pack registry with 409 active run guard and ORPHANED status on uninstalled pack
    studio.pin_pack_for_active_run("orcia-pack-sdlc", "run-pack-active-1")
    with pytest.raises(ResourcePinnedByActiveRunsError):
        studio.configure_or_toggle_pack(
            "orcia-pack-sdlc",
            target_status="DISABLED",
            removal_mode="reject",
        )
    drained_pack = studio.configure_or_toggle_pack(
        "orcia-pack-sdlc",
        target_status="DISABLED",
        removal_mode="drain",
    )
    assert drained_pack.status == "DRAINING"

    orphaned = studio.configure_or_toggle_pack("orcia-pack-legacy-fin")
    assert orphaned.status == "ORPHANED"


def test_story_8_6_durable_wizards_checkpoint_resumption_and_demo_workspace() -> None:
    wiz_svc = DurableOnboardingWizardService()
    lead_user = _make_user("user-tech-lead", "TEAM_LEAD")
    ws_id = "0195f000-0000-7000-8000-000000000301"

    session = wiz_svc.start_or_resume_wizard(
        lead_user,
        wizard_type="sdlc_tech_lead",
        scope_id=ws_id,
    )
    assert session.current_step_index == 1

    # Complete steps 1 and 2 -> advances to step 3/5
    wiz_svc.save_step_and_advance(
        lead_user,
        session.id,
        step_index=1,
        step_payload={"profile": "sdlc_tech_lead"},
    )
    wiz_svc.save_step_and_advance(
        lead_user,
        session.id,
        step_index=2,
        step_payload={"repo_uri": "orcia://connectors/primary-repo"},
        secret_input=SecretInputSpec(
            action="set",
            plaintext_value="wizard-repo-token",  # pragma: allowlist secret
        ),
    )

    # Simulate browser tab closure and resumption -> resumes at exact step 3/5
    resumed = wiz_svc.start_or_resume_wizard(
        lead_user,
        wizard_type="sdlc_tech_lead",
        scope_id=ws_id,
    )
    assert resumed.id == session.id
    assert resumed.current_step_index == 3

    # Completing steps 3, 4, 5 finishes the wizard with RAG reciprocity proof
    wiz_svc.save_step_and_advance(
        lead_user,
        session.id,
        step_index=3,
        step_payload={"default_tier": "auto"},
    )
    wiz_svc.save_step_and_advance(
        lead_user,
        session.id,
        step_index=4,
        step_payload={"pack_key": "orcia-pack-sdlc"},
    )
    completed = wiz_svc.save_step_and_advance(
        lead_user,
        session.id,
        step_index=5,
        step_payload={"verify_rag_reciprocity": True},
    )
    assert completed.status == "COMPLETED"
    assert completed.rag_reciprocity_verified is True

    # 1-Click Zero Empty-State Demo Workspace provisioning
    demo = wiz_svc.provision_zero_empty_state_demo(lead_user)
    assert demo.plaintext_secrets_count == 0
    assert demo.rag_reciprocity_verified is True

    # Verify Day-0 seeder includes Epic 8 idempotent ON CONFLICT DO UPDATE UpsertSpecs
    for spec in (
        ROLE_PERMISSION_GRANTS_UPSERT_SPEC,
        WORKSPACE_LLM_TIER_MAPPINGS_UPSERT_SPEC,
        PLATFORM_SETTINGS_UPSERT_SPEC,
        WIZARD_SESSIONS_UPSERT_SPEC,
    ):
        sql = build_postgres_upsert_sql(spec)
        assert f"INSERT INTO {spec.table}" in sql
        assert "ON CONFLICT" in sql


def test_epic_8_alembic_migration_0022_upgrade_and_downgrade_sql() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "migrations"
        / "versions"
        / "0022_epic_8_settings_rbac_llm_tiers_and_wizards.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0022", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0022_epic_8"
    assert module.down_revision == "0021_story_5_1"

    executed_sql: list[str] = []
    mock_op = MagicMock()
    mock_op.execute.side_effect = lambda clause: executed_sql.append(str(clause))
    module.op = mock_op

    module.upgrade()
    joined_upgrade = "\n".join(executed_sql)
    for table_name in (
        "role_permission_grants",
        "workspace_llm_tier_mappings",
        "inference_attempts",
        "platform_settings",
        "wizard_sessions",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in joined_upgrade

    executed_sql.clear()
    module.downgrade()
    joined_downgrade = "\n".join(executed_sql)
    for table_name in (
        "wizard_sessions",
        "platform_settings",
        "inference_attempts",
        "workspace_llm_tier_mappings",
        "role_permission_grants",
    ):
        assert f"DROP TABLE IF EXISTS {table_name}" in joined_downgrade


def test_epic_8_fastapi_endpoints_contract_and_rfc9457() -> None:
    app = create_app()
    client = TestClient(app)

    # 1. Evaluate RBAC resource access & delegate grant via HTTP
    eval_resp = client.post(
        "/api/v1/settings/iam/evaluate",
        json={
            "subject_id": "0195f000-0000-7000-8000-000000000204",
            "subject_type": "USER",
            "roles": ["CONTRIBUTOR"],
            "scope_path": "org/orcia/bu/claims/team/alpha/workspace/ws-1/resource/res-1",
            "title": "Connecteur Cible",
            "context": {"env": "prod"},
            "require_secret_read": False,
            "require_execute": False,
        },
    )
    assert eval_resp.status_code == 200
    assert eval_resp.json()["locked"] is True

    grant_resp = client.post(
        "/api/v1/settings/iam/grants",
        json={
            "actor_persona": "karim",
            "subject_type": "USER",
            "subject_id": "0195f000-0000-7000-8000-000000000204",
            "scope_path": "org/orcia/bu/claims/team/alpha",
            "verbs": ["read", "execute"],
            "effect": "ALLOW",
        },
    )
    assert grant_resp.status_code == 200
    assert len(grant_resp.json()) == 2

    # 2. Platform settings ETag & canary secret protection over HTTP
    entries_resp = client.get("/api/v1/settings/entries")
    assert entries_resp.status_code == 200
    initial_entry: dict[str, Any] = entries_resp.json()[0]

    patch_resp = client.patch(
        "/api/v1/settings/entries",
        headers={"If-Match": initial_entry["etag"]},
        json={
            "actor_persona": "karim",
            "scope_level": initial_entry["scope_level"],
            "scope_id": initial_entry["scope_id"],
            "category": initial_entry["category"],
            "key": initial_entry["key"],
            "value_jsonb": {"uri": "orcia://connectors/primary-kb"},
            "secret_input": {
                "action": "set",
                "plaintext_value": "HTTP_CANARY_SECRET_777",  # pragma: allowlist secret
            },
        },
    )
    assert patch_resp.status_code == 200
    assert patch_resp.headers.get("ETag") is not None
    assert "HTTP_CANARY_SECRET_777" not in patch_resp.text
    assert patch_resp.json()["secret_status"]["configured"] is True

    # Missing If-Match returns RFC 9457 Problem Details 428
    missing_etag_resp = client.patch(
        "/api/v1/settings/entries",
        json={
            "actor_persona": "karim",
            "scope_level": initial_entry["scope_level"],
            "scope_id": initial_entry["scope_id"],
            "category": initial_entry["category"],
            "key": initial_entry["key"],
            "value_jsonb": {"uri": "orcia://connectors/primary-kb"},
        },
    )
    assert missing_etag_resp.status_code == 428
    assert missing_etag_resp.json()["error_code"] == "ERR_PRECONDITION_REQUIRED"

    # Outbox replay over HTTP
    replay_resp = client.post(
        "/api/v1/admin/outbox/replays",
        json={"actor_persona": "karim", "consumer_name": "audit_finops", "dry_run": True},
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["dry_run"] is True

    # 3. AI Models, Connectors, Studio dry-run & Wizards over HTTP
    mappings_resp = client.get("/api/v1/settings/ai-models/mappings")
    assert mappings_resp.status_code == 200
    assert len(mappings_resp.json()) >= 3

    route_resp = client.post(
        "/api/v1/settings/ai-models/route",
        json={
            "run_id": "run-http-1",
            "step_execution_id": "step-http-1",
            "scope_id": "0195f000-0000-7000-8000-000000000301",
            "system_prompt": "System",
            "user_prompt": "Prompt",
            "inference_tier": "auto",
            "effort": "balanced",
            "fail_simple_tier_gate": True,
        },
    )
    assert route_resp.status_code == 200
    assert route_resp.json()["final_resolved_tier"] == "medium"

    hc_resp = client.post(
        "/api/v1/settings/connectors/0195f000-0000-7000-8000-000000008401/test-connection"
    )
    assert hc_resp.status_code == 200
    assert hc_resp.json()["status"] == "HEALTHY"

    dry_resp = client.post(
        "/api/v1/studio/revisions/0195f000-0000-7000-8000-000000008501/dry-run",
        json={"input_values": {"p_1": "Payments", "p_2": "STANDARD"}},
    )
    assert dry_resp.status_code == 200
    assert dry_resp.json()["external_writes_count"] == 0

    wiz_resp = client.post(
        "/api/v1/wizards/sessions",
        json={
            "actor_persona": "marc",
            "wizard_type": "sdlc_tech_lead",
            "scope_id": "0195f000-0000-7000-8000-000000000301",
        },
    )
    assert wiz_resp.status_code == 200
    session_id = wiz_resp.json()["id"]

    step_resp = client.post(
        f"/api/v1/wizards/sessions/{session_id}/steps",
        json={
            "actor_persona": "marc",
            "step_index": 1,
            "step_payload": {"workspace_name": "Payments Core"},
        },
    )
    assert step_resp.status_code == 200
    assert step_resp.json()["current_step_index"] == 2

    demo_resp = client.post("/api/v1/wizards/demo-workspace?actor_persona=marc")
    assert demo_resp.status_code == 200
    demo_data: dict[str, Any] = demo_resp.json()
    assert demo_data["plaintext_secrets_count"] == 0
