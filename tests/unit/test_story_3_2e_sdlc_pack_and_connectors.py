"""Layer 1 Unit & Layer 3 Integration Tests for Story 3.2e (`AD-20`, `DEC-SEED-01`)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration.errors import (
    IntentionBeforeCodeRequiredError,
    UnknownWorkflowPolicyError,
)
from orcia_core.orchestration.yaml_validator import WorkflowAsCodeValidator
from orcia_kernel.enums import (
    is_valid_memlog_marker,
    list_registered_memlog_markers,
    normalize_memlog_marker,
    register_memlog_marker,
)
from orcia_kernel.ports import list_registered_connector_schemes
from orcia_pack_sdlc import (
    SDLC_BUG_CODE_MARKER,
    SDLC_DOC_OBSOLETE_MARKER,
    activate_sdlc_pack,
    get_bmad_pack_format_adapter,
    get_git_code_ast_indexer,
    get_jira_hybrid_indexer,
    get_tripartite_graph_indexer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ac_e2_zero_sdlc_vocabulary_in_kernel_and_orchestration() -> None:
    """Verify grep for SDLC vocabulary in `orcia_core.kernel` & `orcia-core/orchestration` is 0."""
    proc = subprocess.run(
        [
            "grep",
            "-rnIiE",
            "--exclude-dir=__pycache__",
            "--exclude=*agents_and_skills*",
            "writes_code|BUG_CODE|DOC_OBSOLETE|brownfield|confluence|git://|jira",
            "packages/orcia-core/src/orcia_core/kernel",
            "packages/orcia-core/src/orcia_core/orchestration",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.stdout.strip() == "", f"Unexpected SDLC vocabulary found:\n{proc.stdout}"


def test_ac_e1_and_e2_sdlc_pack_entry_points_and_unknown_workflow_policy_error() -> None:
    """Verify `orcia_pack_sdlc` entry_points, `tags`/`policies` & `ERR_UNKNOWN_WORKFLOW_POLICY`."""
    activate_sdlc_pack()
    assert {"orcia", "db", "mcp", "git", "jira", "confluence", "nexus"}.issubset(
        list_registered_connector_schemes()
    )
    assert get_bmad_pack_format_adapter() is not None
    assert callable(get_git_code_ast_indexer())
    assert callable(get_jira_hybrid_indexer())
    assert get_tripartite_graph_indexer() is not None

    # Namespaced marker registry + legacy aliases
    assert is_valid_memlog_marker(SDLC_BUG_CODE_MARKER) is True
    assert is_valid_memlog_marker(SDLC_DOC_OBSOLETE_MARKER) is True
    assert normalize_memlog_marker("BUG_CODE_SUSPECTED") == SDLC_BUG_CODE_MARKER
    assert normalize_memlog_marker("DOC_OBSOLETE_SUSPECTED") == SDLC_DOC_OBSOLETE_MARKER
    register_memlog_marker("erp.invoice_mismatch_suspected")
    assert "erp.invoice_mismatch_suspected" in list_registered_memlog_markers()

    # Unknown workflow policy raises UnknownWorkflowPolicyError (ERR_UNKNOWN_WORKFLOW_POLICY)
    unknown_policy_yaml = """uri: "orcia://workflows/test-unknown-policy"
title: "Workflow Politique Inconnue"
version: "1.0.0"
criticality: "STANDARD"
execution_regime: "INTERACTIVE_COACHING"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
steps:
  - step_key: "step-1"
    title: "Étape 1"
    step_type: "AGENT"
    instructions: "Test"
    policies:
      - "unregistered.policy_rule"
"""
    with pytest.raises(UnknownWorkflowPolicyError) as pol_exc:
        WorkflowAsCodeValidator.validate_manifest(unknown_policy_yaml, raise_on_error=True)
    assert pol_exc.value.error_code == "ERR_UNKNOWN_WORKFLOW_POLICY"

    # Namespaced tags (`sdlc.writes_code` without `sdlc.declares_intention`) trigger FR-13
    namespaced_fr13_yaml = """uri: "orcia://workflows/test-namespaced-fr13"
title: "Workflow FR-13 Namespaced"
version: "1.0.0"
criticality: "STANDARD"
execution_regime: "INTERACTIVE_COACHING"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
steps:
  - step_key: "code-step"
    title: "Étape Code"
    step_type: "AGENT"
    instructions: "Modifier code"
    tags:
      - "sdlc.writes_code"
    policies:
      - "sdlc.fr13_intention_before_code"
"""
    with pytest.raises(IntentionBeforeCodeRequiredError):
        WorkflowAsCodeValidator.validate_manifest(namespaced_fr13_yaml, raise_on_error=True)

    # API endpoint returns RFC 9457 Problem Details for ERR_UNKNOWN_WORKFLOW_POLICY
    client = TestClient(create_app())
    res = client.post(
        "/api/v1/orchestration/workflows/validate?persona_key=marc",
        json={"raw_manifest": unknown_policy_yaml},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "ERR_UNKNOWN_WORKFLOW_POLICY"
