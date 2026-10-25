"""Idempotent System Bootstrap Workflow, Orthogonal LLM Family & Onboarding seeds (Story 1.5)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


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


DEFAULT_LLM_MODEL_ENDPOINT_SEEDS: tuple[LlmModelEndpointSeed, ...] = (
    LlmModelEndpointSeed(
        "0192c4e0-0000-7000-8000-000000001201", "llm-anthropic-claude-sonnet-4",
        "anthropic", "anthropic-claude", "claude-sonnet-4-20260514",
        "https://api.anthropic.com/v1/messages", True, True,
    ),
    LlmModelEndpointSeed(
        "0192c4e0-0000-7000-8000-000000001202", "llm-openai-gpt-4-1",
        "openai", "openai-gpt", "gpt-4.1-2026-04-14",
        "https://api.openai.com/v1/chat/completions", True, True,
    ),
    LlmModelEndpointSeed(
        "0192c4e0-0000-7000-8000-000000001203", "llm-mistral-large-2",
        "mistral", "mistral-large", "mistral-large-2511",
        "https://api.mistral.ai/v1/chat/completions", True, True,
    ),
)  # fmt: skip


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


DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS: tuple[SystemBootstrapWorkflowSeed, ...] = (
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001301", "orcia://system/bootstrap/init-organization",
        "Amorçage Jour 0 de l'Organisation (init-organization)",
        "Configure OIDC/Local Argon2id, RBAC, >= 2 familles LLM orthogonales et le catalogue.",
        "PLATFORM_ADMIN", "GLOBAL",
        ("GATE-AUTH-RBAC-VALID", "GATE-LLM-ORTHOGONALITY-MIN-2-FAMILIES"),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001302", "orcia://system/bootstrap/init-workspace",
        "Onboarding Autonome d'Équipe & Multi-Workspaces (init-workspace)",
        "Crée en self-service l'équipe/sous-équipes, 1..N Workspaces solutions et invitations.",
        "TEAM_LEAD", "TEAM",
        ("GATE-ONTOLOGY-L3-NO-UPSTREAM-CONFLICT", "GATE-WORKSPACE-NON-EMPTY"),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001303", "orcia://system/bootstrap/init-datasource",
        "Rattachement Gouverné Multi-Sources (init-datasource)",
        "Rattache N x git://, confluence:// (CQL), jira:// (JQL), db:// avec Ancre Humaine.",
        "TEAM_LEAD", "WORKSPACE",
        ("GATE-PERMISSION-BROKER-HUMAN-ANCHOR-SIGNED", "GATE-FRESHNESS-TTL-DAYS-REQUIRED"),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001304", "orcia://system/bootstrap/init-existing-project",
        "Absorption Brownfield de Projet Existant (init-existing-project)",
        "Analyse un projet existant et génère sa proposition d'ontologie et de sources fédérées.",
        "TEAM_LEAD", "WORKSPACE",
        ("GATE-BROWNFIELD-SCAN-VERIFIED",),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001305", "orcia://system/bootstrap/init-skill",
        "Initialisation Gouvernée de Skill / Agent (init-skill)",
        "Crée un nouveau Skill ou Agent dans le Catalogue Fédéré avec ses 5 permissions.",
        "CONTRIBUTOR", "WORKSPACE",
        ("GATE-SKILL-SCHEMA-VALID",),
    ),
    _wf_seed(
        "0192c4e0-0000-7000-8000-000000001306", "orcia://system/bootstrap/init-user",
        "Onboarding Première Connexion & Liaison Passthrough (init-user)",
        "Confirme le Profil Humain et lie Jira, Confluence et Git en passthrough AES-256-GCM.",
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
                "verified_llm_families": ["anthropic-claude", "mistral-large", "openai-gpt"],
                "distinct_families_count": 3,
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
