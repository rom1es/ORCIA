"""Unit tests for Story 31.4 pure slot readiness evaluator, errors & lock helpers (<= 300 L)."""

from __future__ import annotations

import pytest

from orcia_api.errors.registry import resolve_domain_error_mapping
from orcia_core.packs import (
    EffectiveSlotBindingView,
    PackActivationInvalidError,
    PackSlotBindingInvalidError,
    PackSlotSpec,
    PackSlotTargetKind,
    PackSlotUnboundError,
    PinnedPackManifestEntry,
    WorkspacePacksService,
    build_pinned_run_lock_payload,
    evaluate_pack_slot_readiness,
    is_binding_effectively_bound,
)
from orcia_core.packs._internal._sql_run_lock_reads import (
    map_v2_status_to_workflow_run_status,
    parse_run_uuid,
)
from orcia_core.packs._internal._sql_workspace_pack_queries import decode_declared_slots
from orcia_kernel.errors import get_localized_error_text


def _slot(key: str, *, required: bool = True, scheme: str = "git") -> PackSlotSpec:
    return PackSlotSpec(
        slot_key=key,
        scheme=scheme,
        connector_kind=f"mcp:{scheme}",
        required=required,
    )


def test_evaluate_slot_readiness_required_unbound_and_detached_fks() -> None:
    """Required unbound, ON DELETE SET NULL detached FKs, and disabled connectors must fail."""
    declared = [_slot("code-repo", required=True), _slot("optional-wiki", required=False)]

    with pytest.raises(PackSlotUnboundError) as exc_info:
        evaluate_pack_slot_readiness(declared, {}, pack_slug="delivery", raise_on_missing=True)
    err = exc_info.value
    assert err.http_status == 422
    assert err.error_code == "ERR_PACK_SLOT_UNBOUND"
    assert err.missing_slots == ("code-repo",)
    assert err.pack_slug == "delivery"
    fr_copy = get_localized_error_text(
        err.error_code,
        locale="fr",
        detail_code=err.detail_code,
        detail_params=err.detail_params,
    )
    en_copy = get_localized_error_text(
        err.error_code,
        locale="en",
        detail_code=err.detail_code,
        detail_params=err.detail_params,
    )
    assert "code-repo" in fr_copy.detail
    assert "code-repo" in en_copy.detail

    # Simulate ON DELETE SET NULL clearing bound_datasource_id
    detached_ds = EffectiveSlotBindingView(
        workspace_id="ws-1",
        pack_slug="delivery",
        slot_key="code-repo",
        target_kind=PackSlotTargetKind.WORKSPACE_DATASOURCE,
        target_id="stale-uuid",
        bound_datasource_id=None,
        is_effective_bound=False,
    )
    assert is_binding_effectively_bound(detached_ds) is False
    _, missing_after_det = evaluate_pack_slot_readiness(
        declared, {"code-repo": detached_ds}, pack_slug="delivery", raise_on_missing=False
    )
    assert missing_after_det == ["code-repo"]

    # Simulate disabled enterprise connector
    disabled_ec = EffectiveSlotBindingView(
        workspace_id="ws-1",
        pack_slug="delivery",
        slot_key="code-repo",
        target_kind=PackSlotTargetKind.ENTERPRISE_CONNECTOR,
        target_id="ec-1",
        bound_connector_id="ec-1",
        is_effective_bound=True,
        target_enabled=False,
    )
    assert is_binding_effectively_bound(disabled_ec) is False


def test_evaluate_slot_readiness_optional_unbound_and_bound_targets() -> None:
    """Optional unbound slots do not block and record `optional_unbound` in pinned manifest."""
    declared = [
        _slot("code-repo", required=True, scheme="git"),
        _slot("internal-store", required=True, scheme="internal"),
        _slot("optional-wiki", required=False, scheme="db"),
    ]
    bindings = {
        "code-repo": EffectiveSlotBindingView(
            workspace_id="ws-1",
            pack_slug="delivery",
            slot_key="code-repo",
            target_kind=PackSlotTargetKind.WORKSPACE_DATASOURCE,
            target_id="ds-1",
            bound_datasource_id="ds-1",
            connector_scheme="git",
            is_effective_bound=True,
            target_uri="git://org/repo",
        ),
        "internal-store": EffectiveSlotBindingView(
            workspace_id="ws-1",
            pack_slug="delivery",
            slot_key="internal-store",
            target_kind=PackSlotTargetKind.INTERNAL,
            target_id="internal:internal-store",
            is_effective_bound=True,
            target_uri="orcia://internal/internal-store",
        ),
    }
    resolved, missing = evaluate_pack_slot_readiness(
        declared, bindings, pack_slug="delivery", raise_on_missing=True
    )
    assert missing == []
    assert [r.slot_key for r in resolved] == ["code-repo", "internal-store", "optional-wiki"]
    assert resolved[0].status == "bound"
    assert resolved[0].target_uri == "git://org/repo"
    assert resolved[1].status == "bound"
    assert resolved[2].status == "optional_unbound"
    assert resolved[2].target_kind == PackSlotTargetKind.UNBOUND
    assert resolved[2].target_id is None

    pinned = [
        PinnedPackManifestEntry(
            pack_bundle_id="b-1",
            pack_slug="delivery",
            version="1.0.0",
            archive_sha256="a" * 64,
            priority_order=1,
            resolved_pack_slots=resolved,
        )
    ]
    payload_a, sha_a = build_pinned_run_lock_payload(
        run_id="run-1",
        workspace_id="ws-1",
        workflow_id="wf-1",
        workflow_slug="wf-1",
        workflow_version="1.0.0",
        workflow_sha256="b" * 64,
        pinned_packs=pinned,
    )
    payload_b, sha_b = build_pinned_run_lock_payload(
        run_id="run-1",
        workspace_id="ws-1",
        workflow_id="wf-1",
        workflow_slug="wf-1",
        workflow_version="1.0.0",
        workflow_sha256="b" * 64,
        pinned_packs=pinned,
    )
    assert sha_a == sha_b
    assert len(sha_a) == 64
    assert payload_a["pinned_packs"][0]["pack_bundle_id"] == "b-1"
    assert len(payload_a["resolved_pack_slots"]) == 3


def test_error_registry_mappings_and_run_lock_utilities() -> None:
    """Verify RFC 9457 error mappings, UUID parser, status mapping & no-engine service."""
    for cls, code in (
        (PackSlotUnboundError, "ERR_PACK_SLOT_UNBOUND"),
        (PackActivationInvalidError, "ERR_PACK_ACTIVATION_INVALID"),
        (PackSlotBindingInvalidError, "ERR_PACK_SLOT_BINDING_INVALID"),
    ):
        mapping = resolve_domain_error_mapping(cls())
        assert mapping.http_status == 422
        assert mapping.error_code == code
        assert get_localized_error_text(code, locale="fr").title
        assert get_localized_error_text(code, locale="en").title

    assert parse_run_uuid("run-0195f000-0000-7000-8000-000000000999") == (
        "0195f000-0000-7000-8000-000000000999"
    )
    assert parse_run_uuid("not-a-uuid") is None
    assert map_v2_status_to_workflow_run_status("COMPLETED_APPROVED") == "COMPLETED"
    assert map_v2_status_to_workflow_run_status("FAILED_GATES") == "FAILED"
    assert map_v2_status_to_workflow_run_status("WAITING_SUBSTEP_HITL") == "WAITING_FOR_HUMAN_GATE"
    assert map_v2_status_to_workflow_run_status("ROLLED_BACK") == "ROLLED_BACK"
    assert (
        map_v2_status_to_workflow_run_status("PAUSED_CIRCUIT_BREAKER") == "PAUSED_CIRCUIT_BREAKER"
    )
    assert map_v2_status_to_workflow_run_status("RUNNING") == "RUNNING"

    decoded = decode_declared_slots('[{"slot_key": "repo", "scheme": "git", "required": true}]')
    assert len(decoded) == 1
    assert decoded[0].slot_key == "repo"
    assert decode_declared_slots("bad-json") == []


@pytest.mark.asyncio
async def test_workspace_packs_service_no_engine_defaults() -> None:
    """Service gracefully returns empty lists when PG18 engine is absent."""
    svc = WorkspacePacksService()
    assert svc.has_engine() is False
    assert await svc.list_workspace_packs("ws-1") == []
    assert await svc.enforce_run_start_readiness(workspace_id="ws-1") == []
    assert await svc.get_run_lock(run_id="run-1") is None
    with pytest.raises(RuntimeError):
        await svc.deactivate_pack(workspace_id="ws-1", pack_slug="sdlc", actor_id="u-1")


def test_sanitize_inputs_for_unbound_optional_slots_and_shared_pin_error() -> None:
    """Verify `P2-1` strips `slot://opt-kb` URIs and `P1-2` unifies pin error class."""
    from orcia_core.orchestration.errors import ResourcePinnedByActiveRunsError as OrchPinErr
    from orcia_core.packs import (
        PinnedPackManifestEntry,
        ResolvedPackSlotEntry,
        sanitize_workflow_inputs_for_slots,
    )
    from orcia_core.packs.errors import ResourcePinnedByActiveRunsError as PacksPinErr
    from orcia_core.permissions.errors import ResourcePinnedByActiveRunsError as PermPinErr
    from orcia_kernel.errors import ResourcePinnedByActiveRunsError as KernelPinErr

    assert PacksPinErr is KernelPinErr is OrchPinErr is PermPinErr

    pinned = [
        PinnedPackManifestEntry(
            pack_bundle_id="b-1",
            pack_slug="alpha",
            version="1.0.0",
            archive_sha256="a" * 64,
            priority_order=1,
            resolved_pack_slots=[
                ResolvedPackSlotEntry(
                    pack_slug="alpha",
                    slot_key="code-repo",
                    scheme="git",
                    required=True,
                    status="bound",
                    target_kind="WORKSPACE_DATASOURCE",
                    target_id="ds-1",
                    target_uri="git://repo",
                ),
                ResolvedPackSlotEntry(
                    pack_slug="alpha",
                    slot_key="opt-kb",
                    scheme="db",
                    required=False,
                    status="optional_unbound",
                    target_kind="UNBOUND",
                ),
            ],
        )
    ]
    cleaned = sanitize_workflow_inputs_for_slots(
        {
            "repo": "slot://code-repo",
            "kb": "slot://opt-kb",
            "resources": ["slot://opt-kb", "orcia://keep"],
            "nested": {"optional": "slot://opt-kb", "ok": "val"},
        },
        pinned,
    )
    assert cleaned["repo"] == "slot://code-repo"
    assert "kb" not in cleaned
    assert cleaned["resources"] == ["orcia://keep"]
    assert cleaned["nested"] == {"ok": "val"}


def test_committed_autonomous_terminal_and_upgrade_scheme_mismatch() -> None:
    """P1 + P2-2 + P2-3: `COMMITTED_AUTONOMOUS` terminal, kernel error copy & scheme guard."""
    from orcia_core.kernel._error_catalog import ERROR_CATALOG
    from orcia_core.storage.run_lock_guard import TERMINAL_RUN_STATUSES

    assert "COMMITTED_AUTONOMOUS" in TERMINAL_RUN_STATUSES
    assert "COMPLETED_AUTONOMOUS" not in TERMINAL_RUN_STATUSES
    assert "ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS" in ERROR_CATALOG

    mismatched = EffectiveSlotBindingView(
        workspace_id="ws-1",
        pack_slug="alpha-pack",
        slot_key="code-repo",
        target_kind=PackSlotTargetKind.WORKSPACE_DATASOURCE,
        target_id="ds-old",
        bound_datasource_id="ds-old",
        connector_scheme="db",
        is_effective_bound=True,
    )
    with pytest.raises(PackSlotUnboundError) as exc_info:
        evaluate_pack_slot_readiness(
            [_slot("code-repo", scheme="git", required=True)],
            {"code-repo": mismatched},
            pack_slug="alpha-pack",
            raise_on_missing=True,
        )
    assert exc_info.value.missing_slots == ("code-repo",)
