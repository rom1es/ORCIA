"""Layer 1 Unit & Property-Based Tests for Story 3.1: Workflow-as-Code, Templates & Run Lock."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from orcia_api.main import create_app
from orcia_core.domain.exceptions import (
    CriticalWorkflowRequiresHumanGateError,
    IntentionBeforeCodeRequiredError,
    ObserverModeReadOnlyError,
    SubWorkflowCycleDetectedError,
    SubWorkflowMaxDepthExceededError,
    ValidationDomainError,
)
from orcia_core.orchestration import (
    DEFAULT_ROOT_WORKFLOW_YAML,
    ArtifactTemplateDefinition,
    ArtifactTemplateSectionSpec,
    MultiAudienceTemplateCompiler,
    WorkflowAsCodeValidator,
    build_default_orchestration_setup_service,
)
from orcia_core.permissions.models import UserIdentity


def test_workflow_as_code_validator_nominal_and_line_accurate_errors() -> None:
    """Verify DAG validation, line numbers, HIGH_CRITICAL guard, Intention->Code, and depth <= 3."""
    svc = build_default_orchestration_setup_service()
    rep = svc.validate_workflow_manifest(DEFAULT_ROOT_WORKFLOW_YAML)
    assert rep.valid is True
    assert rep.workflow is not None
    assert rep.resolved_max_nesting_depth == 2
    assert rep.topological_order == (
        "frame-architecture-intent",
        "delegate-remediation-subworkflow",
        "post-deploy-verification",
    )

    # Empty manifest
    empty_rep = WorkflowAsCodeValidator.validate_manifest("")
    assert empty_rep.valid is False
    assert empty_rep.findings[0].rule_code == "RULE_SYNTAX_EMPTY_MANIFEST"

    # Invalid YAML syntax reports exact line
    bad_yaml = "uri: 'orcia://workflows/bad'\ntitle: [\n"
    syntax_rep = WorkflowAsCodeValidator.validate_manifest(bad_yaml)
    assert syntax_rep.valid is False
    assert syntax_rep.findings[0].rule_code == "RULE_YAML_JSON_SYNTAX_ERROR"
    assert syntax_rep.findings[0].line >= 2

    # Non-mapping root
    list_rep = WorkflowAsCodeValidator.validate_manifest("- item1\n- item2\n")
    assert list_rep.valid is False
    assert list_rep.findings[0].rule_code == "RULE_ROOT_MAPPING_REQUIRED"

    # HIGH_CRITICAL + AUTONOMOUS_CONTRACT rejected with ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE
    crit_auto_yaml = """uri: "orcia://workflows/crit-auto"
title: "Critical Autonomous Forbidden"
version: "1.0.0"
criticality: "HIGH_CRITICAL"
execution_regime: "AUTONOMOUS_CONTRACT"
steps:
  - step_key: "step-1"
    title: "Step 1"
    step_type: "AGENT"
    instructions: "Do something"
    requires_human_gate: true
"""
    with pytest.raises(CriticalWorkflowRequiresHumanGateError) as exc_info:
        svc.validate_workflow_manifest(crit_auto_yaml, raise_on_error=True)
    assert "Ligne 5" in str(exc_info.value)

    # HIGH_CRITICAL without any human gate or anchor rejected
    crit_no_gate_yaml = """uri: "orcia://workflows/crit-no-gate"
title: "Critical Without Gate"
version: "1.0.0"
criticality: "HIGH_CRITICAL"
execution_regime: "INTERACTIVE_COACHING"
steps:
  - step_key: "step-1"
    title: "Step 1"
    step_type: "AGENT"
    instructions: "No gate"
"""
    with pytest.raises(CriticalWorkflowRequiresHumanGateError):
        svc.validate_workflow_manifest(crit_no_gate_yaml, raise_on_error=True)

    # Intention -> Code violation (writes_code=True without upstream declares_intention=True)
    no_intent_yaml = """uri: "orcia://workflows/no-intent"
title: "Code Without Intention"
version: "1.0.0"
criticality: "STANDARD"
execution_regime: "INTERACTIVE_COACHING"
mode: "standard"
steps:
  - step_key: "write-code-directly"
    title: "Direct Code Write"
    step_type: "AGENT"
    instructions: "Write code without spec"
    writes_code: true
"""
    with pytest.raises(IntentionBeforeCodeRequiredError) as intent_exc:
        svc.validate_workflow_manifest(no_intent_yaml, raise_on_error=True)
    assert "Ligne 8" in str(intent_exc.value)

    # Code -> Doc reverse documentation without mode: brownfield_bootstrap rejected
    rev_doc_yaml = """uri: "orcia://workflows/reverse-doc"
title: "Reverse Doc Without Brownfield Mode"
version: "1.0.0"
mode: "standard"
steps:
  - step_key: "extract-doc"
    title: "Extract Doc"
    step_type: "AGENT"
    instructions: "Reverse doc"
    reverse_doc_from_code: true
"""
    with pytest.raises(IntentionBeforeCodeRequiredError):
        svc.validate_workflow_manifest(rev_doc_yaml, raise_on_error=True)

    # Same reverse doc with mode: brownfield_bootstrap succeeds
    rev_doc_ok = rev_doc_yaml.replace('mode: "standard"', 'mode: "brownfield_bootstrap"')
    ok_rep = svc.validate_workflow_manifest(rev_doc_ok, raise_on_error=True)
    assert ok_rep.valid is True


def test_sub_workflow_cycle_and_max_depth_detection() -> None:
    """Verify static cycle detection and nesting_depth <= 3 enforcement on SUB_WORKFLOW steps."""
    svc = build_default_orchestration_setup_service()
    lead = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000603",
        email="marc.lead@orcia.io",
        display_name="Marc",
        auth_mode="HYBRID",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )

    # Step cycle inside a single workflow
    step_cycle_yaml = """uri: "orcia://workflows/step-cycle"
title: "Step Cycle"
steps:
  - step_key: "s1"
    title: "S1"
    step_type: "AGENT"
    depends_on: ["s2"]
    instructions: "A"
  - step_key: "s2"
    title: "S2"
    step_type: "AGENT"
    depends_on: ["s1"]
    instructions: "B"
"""
    with pytest.raises(ValidationDomainError):
        svc.validate_workflow_manifest(step_cycle_yaml, raise_on_error=True)

    # Self-recursive SUB_WORKFLOW cycle
    sub_cycle_yaml = """uri: "orcia://workflows/self-sub-cycle"
title: "Self Sub Cycle"
steps:
  - step_key: "call-self"
    title: "Call Self"
    step_type: "SUB_WORKFLOW"
    sub_workflow_uri: "orcia://workflows/self-sub-cycle"
    instructions: "Cycle"
"""
    with pytest.raises(SubWorkflowCycleDetectedError):
        svc.validate_workflow_manifest(sub_cycle_yaml, raise_on_error=True)

    # Register depth-3 wrapper calling claims-engineering-delivery (depth 2 -> total 3)
    depth3_yaml = """uri: "orcia://workflows/depth-3-wrapper"
title: "Depth 3 Wrapper"
steps:
  - step_key: "call-root"
    title: "Call Root"
    step_type: "SUB_WORKFLOW"
    sub_workflow_uri: "orcia://workflows/claims-engineering-delivery"
    instructions: "Depth 3"
"""
    wf3 = svc.register_workflow_manifest(
        lead, depth3_yaml, workspace_id="0192c4e0-0000-7000-8000-000000000201"
    )
    assert wf3.max_nesting_depth == 3

    # Depth 4 wrapper calling depth-3-wrapper -> exceeds MAX_SUB_WORKFLOW_NESTING_DEPTH (3)
    depth4_yaml = """uri: "orcia://workflows/depth-4-exceeded"
title: "Depth 4 Exceeded"
steps:
  - step_key: "call-depth-3"
    title: "Call Depth 3"
    step_type: "SUB_WORKFLOW"
    sub_workflow_uri: "orcia://workflows/depth-3-wrapper"
    instructions: "Depth 4"
"""
    with pytest.raises(SubWorkflowMaxDepthExceededError) as depth_exc:
        svc.validate_workflow_manifest(depth4_yaml, raise_on_error=True)
    assert "Profondeur SUB_WORKFLOW 4 > 3" in str(depth_exc.value)


@given(word_count=st.integers(min_value=10, max_value=1400))
@settings(max_examples=15, deadline=None)
def test_multi_audience_template_compiler_hypothesis_chunking(word_count: int) -> None:
    """Property test: cognitive chunks never exceed 800 words and JSON Schema binds Ontology."""
    svc = build_default_orchestration_setup_service()
    long_text = " ".join(f"mot{i}" for i in range(word_count))
    tpl = ArtifactTemplateDefinition(
        template_key="tpl-hyp-test",
        uri="orcia://templates/tpl-hyp-test@1.0.0",
        title="Gabarit Test Hypothesis",
        version="1.0.0",
        description="Test chunking",
        required_variables=("system_name",),
        sections=(
            ArtifactTemplateSectionSpec(
                section_key="sec_main",
                title="Section Principale",
                markdown_body_template=f"Système {{{{ system_name }}}} : {long_text}",
                ontology_concept_term="Actif Stratégique",
                human_authored_required=True,
                mandatory=True,
                max_words_chunk=500,
            ),
        ),
    )
    snapshot = svc.ontology_service.resolve_snapshot(workspace_scope_id="ws-solution-paiement")
    compiled = MultiAudienceTemplateCompiler.compile_template(
        tpl, variables={"system_name": "ORCIA-Core"}, ontology_snapshot=snapshot
    )
    assert "ORCIA-Core" in compiled.human_markdown_view
    assert all(chunk.word_count <= 800 for chunk in compiled.cognitive_chunks)
    assert "Actif Stratégique" in compiled.bound_ontology_terms
    sec_schema = compiled.agent_json_schema["properties"]["sec_main"]
    assert sec_schema["x-ontology-canonical-term"] == "Actif Stratégique"
    assert sec_schema["x-human-authored-required"] is True


def test_recursive_run_lock_and_rest_endpoints() -> None:
    """Verify recursive run-lock.json, idempotency, observer guard, and FastAPI endpoints."""
    svc = build_default_orchestration_setup_service()
    lead = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000603",
        email="marc.lead@orcia.io",
        display_name="Marc",
        auth_mode="HYBRID",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )
    observer = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000699",
        email="obs@orcia.io",
        display_name="Observer",
        auth_mode="LOCAL",
        human_profile_archetype="PM_BUSINESS",
        platform_role="OBSERVER",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )

    with pytest.raises(ObserverModeReadOnlyError):
        svc.instantiate_workflow_run(
            observer,
            workflow_uri="orcia://workflows/claims-engineering-delivery",
            workspace_id="0192c4e0-0000-7000-8000-000000000201",
        )

    run1 = svc.instantiate_workflow_run(
        lead,
        workflow_uri="orcia://workflows/claims-engineering-delivery",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        trigger_id="trg-1",
        trigger_idempotency_key="evt-100",
    )
    run2 = svc.instantiate_workflow_run(
        lead,
        workflow_uri="orcia://workflows/claims-engineering-delivery",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        trigger_id="trg-1",
        trigger_idempotency_key="evt-100",
    )
    assert run1.id == run2.id
    assert len(run1.run_lock.sub_workflow_locks) == 1
    child_lock = run1.run_lock.sub_workflow_locks[0]
    assert child_lock.workflow_uri == "orcia://workflows/sub-remediate-and-verify"
    assert child_lock.nesting_depth == 1
    assert len(child_lock.sub_workflow_locks) == 1
    assert (
        child_lock.sub_workflow_locks[0].workflow_uri
        == "orcia://workflows/sub-verify-regression-suite"
    )
    assert child_lock.sub_workflow_locks[0].nesting_depth == 2

    # FastAPI router tests
    client = TestClient(create_app())
    state_res = client.get("/api/v1/orchestration/state?persona_key=marc")
    assert state_res.status_code == 200
    state_json = state_res.json()
    assert len(state_json["workflows"]) == 3
    assert len(state_json["runs"]) >= 1

    val_res = client.post(
        "/api/v1/orchestration/workflows/validate?persona_key=marc",
        json={"raw_manifest": DEFAULT_ROOT_WORKFLOW_YAML},
    )
    assert val_res.status_code == 200
    assert val_res.json()["valid"] is True

    tpl_res = client.post(
        "/api/v1/orchestration/templates/compile?persona_key=marc",
        json={
            "template_key": "tpl-architecture-decision-record",
            "variables": {"project_name": "Claims", "jira_key": "PAY-142"},
        },
    )
    assert tpl_res.status_code == 200
    assert "Claims" in tpl_res.json()["compiled_template"]["human_markdown_view"]

    inst_obs = client.post(
        "/api/v1/orchestration/runs/instantiate?persona_key=claire",
        json={
            "workflow_uri": "orcia://workflows/claims-engineering-delivery",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        },
    )
    assert inst_obs.status_code == 403
    assert inst_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    inst_ok = client.post(
        "/api/v1/orchestration/runs/instantiate?persona_key=marc",
        json={
            "workflow_uri": "orcia://workflows/claims-engineering-delivery",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        },
    )
    assert inst_ok.status_code == 200
    assert inst_ok.json()["run"]["nesting_depth"] == 0
