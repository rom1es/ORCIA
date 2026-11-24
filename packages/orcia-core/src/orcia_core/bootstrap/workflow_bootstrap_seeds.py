"""Idempotent System Bootstrap Workflow, Orthogonal LLM Family & Onboarding seeds (Story 1.5)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from orcia_core.bootstrap._bootstrap_locales import WORKFLOW_BOOTSTRAP_SEED_LOCALES


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _j(payload: object) -> str:
    return json.dumps(payload, sort_keys=True)


@dataclass(frozen=True, slots=True)
class LlmModelEndpointSeed:
    """Reference LLM endpoint seed across distinct model families (`AD-10`, `FR-28`)."""

    id: str
    endpoint_key: str
    provider_slug: str
    model_family: str
    model_name: str
    endpoint_uri: str
    connectivity_verified: bool = True
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class SystemBootstrapWorkflowSeed:
    """Reference pre-embedded `orcia://system/bootstrap/*` workflow definition seed (`FR-28`)."""

    id: str
    uri: str
    title: str
    description: str
    required_role: str
    scope_level: str
    deterministic_gate_rules: tuple[str, ...]
    steps_schema_json: str
    sha256: str


@dataclass(frozen=True, slots=True)
class SystemBootstrapRunSeed:
    """Reference system bootstrap run record seed (`AD-16`, `FR-28`)."""

    id: str
    run_key: str
    workflow_uri: str
    scope_level: str
    target_org_unit_id: str | None
    target_workspace_id: str | None
    triggered_by_user_id: str
    status: str
    gate_passed: bool
    gate_report_json: str
    execution_payload_json: str


@dataclass(frozen=True, slots=True)
class UserOnboardingStateSeed:
    """Reference user onboarding state seed tracking `init-user` first-login execution."""

    id: str
    user_email: str
    user_id: str | None
    invited_by_user_id: str | None
    org_unit_id: str
    human_profile_archetype: str
    assigned_role: str
    workspace_ids_json: str
    init_user_completed: bool
    linked_connectors_json: str


DEFAULT_LLM_MODEL_ENDPOINT_SEEDS: tuple[LlmModelEndpointSeed, ...] = ()


def _wf_seed(
    seed_id: str,
    uri: str,
    title: str,
    description: str,
    required_role: str,
    scope_level: str,
    gates: tuple[str, ...],
) -> SystemBootstrapWorkflowSeed:
    schema = _j(
        {
            "uri": uri,
            "title": title,
            "description": description,
            "required_role": required_role,
            "scope_level": scope_level,
            "deterministic_gate_rules": list(gates),
        }
    )
    return SystemBootstrapWorkflowSeed(
        seed_id,
        uri,
        title,
        description,
        required_role,
        scope_level,
        gates,
        schema,
        _sha256_text(schema),
    )


_WF_FR = WORKFLOW_BOOTSTRAP_SEED_LOCALES["fr"]

DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS: tuple[SystemBootstrapWorkflowSeed, ...] = (
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001301", "orcia://system/bootstrap/init-organization",
        _WF_FR["init-organization"][0],
        _WF_FR["init-organization"][1],
        "PLATFORM_ADMIN", "GLOBAL",
        ("GATE-AUTH-RBAC-VALID", "GATE-LLM-ORTHOGONALITY-MIN-2-FAMILIES"),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001302", "orcia://system/bootstrap/init-workspace",
        _WF_FR["init-workspace"][0],
        _WF_FR["init-workspace"][1],
        "TEAM_LEAD", "TEAM",
        ("GATE-ONTOLOGY-L3-NO-UPSTREAM-CONFLICT", "GATE-WORKSPACE-NON-EMPTY"),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001303", "orcia://system/bootstrap/init-datasource",
        _WF_FR["init-datasource"][0],
        _WF_FR["init-datasource"][1],
        "TEAM_LEAD", "WORKSPACE",
        ("GATE-PERMISSION-BROKER-HUMAN-ANCHOR-SIGNED", "GATE-FRESHNESS-TTL-DAYS-REQUIRED"),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001304", "orcia://system/bootstrap/init-existing-project",
        _WF_FR["init-existing-project"][0],
        _WF_FR["init-existing-project"][1],
        "TEAM_LEAD", "WORKSPACE",
        ("GATE-BROWNFIELD-SCAN-VERIFIED",),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001305", "orcia://system/bootstrap/init-skill",
        _WF_FR["init-skill"][0],
        _WF_FR["init-skill"][1],
        "CONTRIBUTOR", "WORKSPACE",
        ("GATE-SKILL-SCHEMA-VALID",),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001306", "orcia://system/bootstrap/init-user",
        _WF_FR["init-user"][0],
        _WF_FR["init-user"][1],
        "CONTRIBUTOR", "WORKSPACE",
        ("GATE-HUMAN-PROFILE-CONFIRMED", "GATE-PASSTHROUGH-AES256GCM-ENCRYPTED"),
    ),
)  # fmt: skip

DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS: tuple[SystemBootstrapRunSeed, ...] = (
    SystemBootstrapRunSeed(
        "0192c4e0-0000-7000-8000-000000001401", "boot-run-day0-init-organization",
        "orcia://system/bootstrap/init-organization", "GLOBAL",
        "0192c4e0-0000-7000-8000-000000000101", None, "0192c4e0-0000-7000-8000-000000000601",
        "COMPLETED", True,
        _j(
            {
                "auth_rbac_valid": True,
                "verified_llm_families": [],
                "distinct_families_count": 0,
            }
        ),
        _j({"organization_name": "Entreprise ORCIA Group", "seeded_workflows": 6}),
    ),
    SystemBootstrapRunSeed(
        "0192c4e0-0000-7000-8000-000000001402", "boot-run-team-checkout-init-workspace",
        "orcia://system/bootstrap/init-workspace", "TEAM",
        "0192c4e0-0000-7000-8000-000000000104", "0192c4e0-0000-7000-8000-000000000201",
        "0192c4e0-0000-7000-8000-000000000603", "COMPLETED", True,
        _j({"ontology_conflicts": [], "workspaces_created": 2, "invited_members": 2}),
        _j(
            {
                "team_slug": "subteam-checkout-squad",
                "workspaces": ["ws-solution-paiement", "ws-solution-fidelite"],
            }
        ),
    ),
)  # fmt: skip

DEFAULT_USER_ONBOARDING_STATE_SEEDS: tuple[UserOnboardingStateSeed, ...] = (
    UserOnboardingStateSeed(
        "0192c4e0-0000-7000-8000-000000001501", "marc.lead@orcia.io",
        "0192c4e0-0000-7000-8000-000000000603", "0192c4e0-0000-7000-8000-000000000601",
        "0192c4e0-0000-7000-8000-000000000104", "TECH_LEAD", "TEAM_LEAD",
        _j(["0192c4e0-0000-7000-8000-000000000201", "0192c4e0-0000-7000-8000-000000000202"]),
        True, _j(["git", "jira", "confluence"]),
    ),
    UserOnboardingStateSeed(
        "0192c4e0-0000-7000-8000-000000001502", "nadia.dev@orcia.io",
        "0192c4e0-0000-7000-8000-000000000604", "0192c4e0-0000-7000-8000-000000000603",
        "0192c4e0-0000-7000-8000-000000000104", "DEVELOPER", "CONTRIBUTOR",
        _j(["0192c4e0-0000-7000-8000-000000000201", "0192c4e0-0000-7000-8000-000000000202"]),
        False, _j([]),
    ),
)  # fmt: skip
