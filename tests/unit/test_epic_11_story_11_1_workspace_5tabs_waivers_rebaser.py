"""Unit & API contract tests for Story 11.1 (`Mes Espaces`, Cascade, DNA Waivers, Rebaser)."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration.errors import (
    EnterpriseDirectiveWaiverForbiddenError,
    OrthogonalJudgeSovereigntyViolationError,
    PathTraversalDeniedError,
)
from orcia_core.orchestration.workspace_governance_and_rebaser import (
    DnaChainNode,
    WorkspaceGovernanceAndArtifactRoutingService,
    WorkspaceSourceSummary,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError


def test_five_subtabs_and_observer_guard() -> None:
    """Verify the 5 sub-tabs of `Mes Espaces` and `READ_ONLY_OBSERVER` protection."""
    svc = WorkspaceGovernanceAndArtifactRoutingService()
    ws_id = uuid4()
    src = WorkspaceSourceSummary(
        source_id=uuid4(),
        uri="confluence://SPACE/RGPD",
        title="Politique RGPD",
        authority_role="REFERENCE",
        access_mode="READ_ONLY",
        freshness_status="FRESH",
    )
    state = svc.configure_workspace_tabs(
        workspace_id=ws_id,
        workspace_slug="claims-core",
        actor_role="TEAM_LEAD",
        default_artifact_destination_uri="git://github.com/orcia/claims/specs",
        sources=[src],
        pending_glossary_candidates_count=22,
    )
    assert state.tabs == (
        "OVERVIEW",
        "DOCUMENTS_SOURCES",
        "DELIVERABLES_ARTIFACTS",
        "GLOSSARY_RULES",
        "MEMBERS_TEAM",
    )
    assert state.pending_glossary_candidates_count == 15
    assert len(state.sources) == 1

    with pytest.raises(ObserverModeReadOnlyError):
        svc.configure_workspace_tabs(
            workspace_id=ws_id,
            workspace_slug="claims-core",
            actor_role="READ_ONLY_OBSERVER",
            default_artifact_destination_uri="git://github.com/orcia/claims/specs",
        )


def test_dna_waiver_verrou_v1_and_sha256_drift_invalidation() -> None:
    """Verify `Verrou V1` (`ERR_ENTERPRISE_DIRECTIVE_WAIVER_FORBIDDEN` & SHA-256 invalidation)."""
    svc = WorkspaceGovernanceAndArtifactRoutingService()
    ws_id = uuid4()
    user_id = uuid4()

    # Local 3_WORKSPACE norm can be waived by TEAM_LEAD
    waiver = svc.register_exception_waiver(
        workspace_id=ws_id,
        source_uri="confluence://SPACE/ARCH-OLD",
        source_sha256="sha256_v1_abcdef",
        conflict_rule_id="RULE_STALE_ARCH",
        norm_level="3_WORKSPACE",
        dna_chain=[
            DnaChainNode(
                node_key="NORM_LOCAL_NAMING",
                stereotype="NORM",
                level="3_WORKSPACE",
                inviolable=False,
            )
        ],
        approved_by_user_id=user_id,
        approved_by_role="TEAM_LEAD",
        reason="Migration prévue sprint prochain",
    )
    assert waiver.status == "ACTIVE"
    assert (
        svc.evaluate_conflict_waiver(
            workspace_id=ws_id,
            source_uri="confluence://SPACE/ARCH-OLD",
            current_source_sha256="sha256_v1_abcdef",
            conflict_rule_id="RULE_STALE_ARCH",
        )
        is True
    )
    # SHA-256 change invalidates the waiver automatically
    assert (
        svc.evaluate_conflict_waiver(
            workspace_id=ws_id,
            source_uri="confluence://SPACE/ARCH-OLD",
            current_source_sha256="sha256_v2_modified",
            conflict_rule_id="RULE_STALE_ARCH",
        )
        is False
    )

    # 3_WORKSPACE norm tracing back to 1_ENTERPRISE inviolable directive is forbidden to TEAM_LEAD
    inviolable_chain = [
        DnaChainNode(
            node_key="DIR_ZERO_PII",
            stereotype="DIRECTIVE",
            level="1_ENTERPRISE",
            inviolable=True,
        ),
        DnaChainNode(
            node_key="NORM_PSEUDONYMIZE",
            stereotype="NORM",
            level="3_WORKSPACE",
            inviolable=False,
        ),
    ]
    with pytest.raises(EnterpriseDirectiveWaiverForbiddenError) as exc_info:
        svc.register_exception_waiver(
            workspace_id=ws_id,
            source_uri="git://repo/file.py",
            source_sha256="sha256_11111111",
            conflict_rule_id="MECH_NO_RAW_IBAN",
            norm_level="3_WORKSPACE",
            dna_chain=inviolable_chain,
            approved_by_user_id=user_id,
            approved_by_role="TEAM_LEAD",
            reason="Test local bypass",
        )
    assert exc_info.value.error_code == "ERR_ENTERPRISE_DIRECTIVE_WAIVER_FORBIDDEN"

    # SECOPS is allowed
    secops_waiver = svc.register_exception_waiver(
        workspace_id=ws_id,
        source_uri="git://repo/file.py",
        source_sha256="sha256_11111111",
        conflict_rule_id="MECH_NO_RAW_IBAN",
        norm_level="3_WORKSPACE",
        dna_chain=inviolable_chain,
        approved_by_user_id=user_id,
        approved_by_role="SECOPS",
        reason="Dérogation SecOps auditée",
    )
    assert secops_waiver.status == "ACTIVE"


def test_four_level_artifact_destination_cascade_and_realpath_confinement(
    tmp_path: Path,
) -> None:
    """Verify the 4-level destination cascade and `local://` `os.path.realpath` confinement."""
    svc = WorkspaceGovernanceAndArtifactRoutingService()
    ws_id = uuid4()
    payload = b"# Spec Technique\nContenu test"

    # Level 4 fallback (Orcia Vault S3 CAS)
    r4 = svc.resolve_artifact_destination(
        workspace_id=ws_id,
        workspace_slug="claims",
        artifact_type="tech-spec",
        artifact_slug="orcia-101",
        version=2,
        content_bytes=payload,
    )
    assert r4.selected_level == "4_ORCIA_VAULT_FALLBACK"
    assert r4.canonical_alias_uri == "orcia://workspaces/claims/artifacts/tech-spec/orcia-101@v2"
    assert r4.cas_storage_path.startswith("cas/")
    assert r4.staged_for_gate_publication is False

    # Level 3 workspace default
    r3 = svc.resolve_artifact_destination(
        workspace_id=ws_id,
        workspace_slug="claims",
        artifact_type="tech-spec",
        artifact_slug="orcia-101",
        version=2,
        content_bytes=payload,
        workspace_default_uri="confluence://CLAIMS/Specs",
    )
    assert r3.selected_level == "3_WORKSPACE_DEFAULT"
    assert r3.staged_for_gate_publication is True

    # Level 2 workflow step target
    r2 = svc.resolve_artifact_destination(
        workspace_id=ws_id,
        workspace_slug="claims",
        artifact_type="tech-spec",
        artifact_slug="orcia-101",
        version=2,
        content_bytes=payload,
        workflow_step_target_uri="git://github.com/orcia/claims/docs/orcia-101.md",
        workspace_default_uri="confluence://CLAIMS/Specs",
    )
    assert r2.selected_level == "2_WORKFLOW_STEP_TARGET"

    # Level 1 run override with local:// confinement
    r1 = svc.resolve_artifact_destination(
        workspace_id=ws_id,
        workspace_slug="claims",
        artifact_type="tech-spec",
        artifact_slug="orcia-101",
        version=2,
        content_bytes=payload,
        run_override_uri="local://specs/orcia-101.md",
        workflow_step_target_uri="git://github.com/orcia/claims/docs/orcia-101.md",
        local_root_realpath=str(tmp_path),
    )
    assert r1.selected_level == "1_RUN_OVERRIDE"

    with pytest.raises(PathTraversalDeniedError) as exc_info:
        svc.resolve_artifact_destination(
            workspace_id=ws_id,
            workspace_slug="claims",
            artifact_type="tech-spec",
            artifact_slug="orcia-101",
            version=2,
            content_bytes=payload,
            run_override_uri="local://../../etc/passwd",
            local_root_realpath=str(tmp_path),
        )
    assert exc_info.value.error_code == "ERR_PATH_TRAVERSAL_DENIED"


def test_external_edit_rebaser_verrou_v2_and_pilot_workflow_verrou_v3() -> None:
    """Verify `ExternalEditRebaser` (`Verrou V2`) and `ticket-to-tech-spec` (`Verrou V3`)."""
    svc = WorkspaceGovernanceAndArtifactRoutingService()
    orcia_md = (
        "# Spec ORCIA-42\n"
        "## 1. Contexte\nContexte initial généré.\n"
        "## 2. Sécurité\nAuthentification simple par API Key.\n"
    )
    ext_md = (
        "# Spec ORCIA-42\n"
        "## 1. Contexte\nContexte initial généré.\n"
        "## 2. Sécurité\nAuthentification OIDC mTLS obligatoire (amendé par Tech Lead).\n"
    )
    rebased = svc.rebase_external_artifact_edits(
        artifact_uri="git://github.com/orcia/claims/specs/orcia-42.md",
        current_version=1,
        orcia_markdown=orcia_md,
        external_markdown=ext_md,
        step_memlog_entries=[
            "Hypothèse sur 1. Contexte validée",
            "Hypothèse sur 2. Sécurité basée sur API Key",
        ],
    )
    assert rebased.divergence_detected is True
    assert rebased.imported_version == 2
    sec_chunks = [c for c in rebased.chunks if "Sécurité" in c.section_title]
    assert len(sec_chunks) == 1
    assert sec_chunks[0].status == "HUMAN_AMENDED_EXTERNAL"
    assert sec_chunks[0].locked_against_agent_overwrite is True
    assert any("[SUPERSEDED_BY_HUMAN_COMMIT]" in m for m in rebased.step_memlog_annotations)

    # Pilot workflow Verrou V3 sovereignty check
    ws_id = uuid4()
    with pytest.raises(OrthogonalJudgeSovereigntyViolationError):
        svc.run_pilot_ticket_to_tech_spec_workflow(
            workspace_id=ws_id,
            workspace_slug="claims",
            ticket_key="CLAIMS-42",
            ticket_summary="Ajout du contrôle IBAN",
            workspace_sovereignty_tier="ON_PREM_AIRGAPPED",
            generator_model_family="llama-3.3",
            judge_model_family="claude-4.6",
            judge_sovereignty_tier="CLOUD_PUBLIC",
        )


def test_story_11_1_fastapi_endpoints() -> None:
    """Verify Story 11.1 FastAPI endpoints and RFC 9457 Problem Details error codes."""
    client = TestClient(create_app())
    ws_id = str(uuid4())

    resp_tabs = client.get(
        f"/api/v1/workspaces/{ws_id}/five-tabs",
        params={"persona_key": "karim", "workspace_slug": "claims-core"},
    )
    assert resp_tabs.status_code == 200
    assert len(resp_tabs.json()["tabs"]) == 5

    # Attempt local waiver on 1_ENTERPRISE inviolable directive as TEAM_LEAD (claire)
    resp_forbidden = client.post(
        f"/api/v1/workspaces/{ws_id}/exception-waivers",
        params={"persona_key": "claire"},
        json={
            "source_uri": "git://repo/sec.py",
            "source_sha256": "sha256_test_v1",
            "conflict_rule_id": "RULE_ENTERPRISE_SEC",
            "norm_level": "3_WORKSPACE",
            "dna_chain": [
                {
                    "node_key": "DIR_SEC_1",
                    "stereotype": "DIRECTIVE",
                    "level": "1_ENTERPRISE",
                    "inviolable": True,
                }
            ],
            "reason": "Tentative de contournement local",
        },
    )
    assert resp_forbidden.status_code == 403
    assert resp_forbidden.json()["error_code"] == "ERR_ENTERPRISE_DIRECTIVE_WAIVER_FORBIDDEN"

    # Attempt path traversal on local:// destination
    resp_traversal = client.post(
        f"/api/v1/workspaces/{ws_id}/artifacts/resolve-destination",
        params={"persona_key": "karim"},
        json={
            "workspace_slug": "claims-core",
            "artifact_type": "tech-spec",
            "artifact_slug": "claims-99",
            "version": 1,
            "content_markdown": "# Spec",
            "run_override_uri": "local://../../../etc/shadow",
        },
    )
    assert resp_traversal.status_code == 403
    assert resp_traversal.json()["error_code"] == "ERR_PATH_TRAVERSAL_DENIED"
