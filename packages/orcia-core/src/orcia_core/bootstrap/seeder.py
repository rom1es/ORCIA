"""Idempotent reference data seeder foundation (`INSERT ... ON CONFLICT DO UPDATE`, AD-16)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from orcia_core.bootstrap.catalog_seeds import (
    DEFAULT_CATALOG_ITEM_SEEDS,
    DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS,
    DEFAULT_WORKFLOW_DEFINITION_SEEDS,
    CatalogItemSeed,
    CustomizationOverrideSeed,
    WorkflowDefinitionSeed,
)
from orcia_core.bootstrap.permission_broker_seeds import (
    DEFAULT_PERMISSION_BROKER_POLICY_SEEDS,
    DEFAULT_PERMISSION_BROKER_TICKET_SEEDS,
    PermissionBrokerPolicySeed,
    PermissionBrokerTicketSeed,
)
from orcia_core.bootstrap.workflow_bootstrap_seeds import (
    DEFAULT_LLM_MODEL_ENDPOINT_SEEDS,
    DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS,
    DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS,
    DEFAULT_USER_ONBOARDING_STATE_SEEDS,
    LlmModelEndpointSeed,
    SystemBootstrapRunSeed,
    SystemBootstrapWorkflowSeed,
    UserOnboardingStateSeed,
)
from orcia_core.permissions.seeds import (
    DEFAULT_ORG_UNIT_SEEDS,
    DEFAULT_WORKSPACE_DATASOURCE_SEEDS,
    DEFAULT_WORKSPACE_SEEDS,
    OrgUnitSeed,
    WorkspaceDatasourceSeed,
    WorkspaceSeed,
)

IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

ASSISTANT_WORKFLOW_URI: str = "orcia://system/workflows/assistant-agent"

SYSTEM_BOOTSTRAP_WORKFLOW_URIS: tuple[str, ...] = (
    "orcia://system/bootstrap/init-organization",
    "orcia://system/bootstrap/init-workspace",
    "orcia://system/bootstrap/init-datasource",
    "orcia://system/bootstrap/init-existing-project",
    "orcia://system/bootstrap/init-skill",
    "orcia://system/bootstrap/init-user",
)


@dataclass(frozen=True, slots=True)
class HumanProfileArchetypeSeed:
    """Reference Human Profile archetype seeded at platform bootstrap (FR-1, FR-15)."""

    key: str
    label_fr: str
    label_en: str


DEFAULT_HUMAN_PROFILE_ARCHETYPES: tuple[HumanProfileArchetypeSeed, ...] = (
    HumanProfileArchetypeSeed("PM_BUSINESS", "PM / Métier", "Product Manager / Business"),
    HumanProfileArchetypeSeed("ARCHITECT", "Architecte", "System Architect"),
    HumanProfileArchetypeSeed("TECH_LEAD", "Tech Lead", "Tech Lead"),
    HumanProfileArchetypeSeed("DEVELOPER", "Développeur", "Software Engineer"),
    HumanProfileArchetypeSeed("SECOPS", "SecOps / IAM", "SecOps / IAM"),
    HumanProfileArchetypeSeed("EXECUTIVE", "Direction", "Executive Leadership"),
)


@dataclass(frozen=True, slots=True)
class UpsertSpec:
    """Declarative specification for an idempotent PostgreSQL `INSERT ... ON CONFLICT DO UPDATE`."""

    table: str
    conflict_columns: tuple[str, ...]
    value_columns: tuple[str, ...]
    insert_only_columns: tuple[str, ...] = ("id",)


def _validate_identifier(name: str) -> str:
    if not IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return name


def build_postgres_upsert_sql(spec: UpsertSpec) -> str:
    """Generate parameterized PostgreSQL `INSERT ... ON CONFLICT (...) DO UPDATE SET ...` SQL."""
    table = _validate_identifier(spec.table)
    if not spec.conflict_columns:
        raise ValueError("conflict_columns must not be empty")
    if not spec.value_columns:
        raise ValueError("value_columns must not be empty")

    conflict_cols = [_validate_identifier(c) for c in spec.conflict_columns]
    value_cols = [_validate_identifier(c) for c in spec.value_columns]
    insert_only = {_validate_identifier(c) for c in spec.insert_only_columns}

    all_cols = list(dict.fromkeys([*conflict_cols, *value_cols]))
    update_cols = [c for c in value_cols if c not in insert_only and c not in conflict_cols]
    cols_clause = ", ".join(all_cols)
    params_clause = ", ".join(f":{col}" for col in all_cols)
    conflict_clause = ", ".join(conflict_cols)
    update_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)

    return (
        f"INSERT INTO {table} ({cols_clause}) "
        f"VALUES ({params_clause}) "
        f"ON CONFLICT ({conflict_clause}) DO UPDATE SET {update_clause};"
    )


ORG_UNITS_UPSERT_SPEC = UpsertSpec("org_units", ("slug",), ("id", "name", "unit_type", "parent_id"))
WORKSPACES_UPSERT_SPEC = UpsertSpec(
    "workspaces", ("slug",),
    ("id", "name", "owner_org_unit_id", "visibility_mode", "finops_cost_usd"),
)  # fmt: skip
WORKSPACE_DATASOURCES_UPSERT_SPEC = UpsertSpec(
    "workspace_datasources", ("workspace_id", "alias"),
    ("id", "scheme", "uri", "role", "execution_identity", "freshness_ttl_days"),
)  # fmt: skip
CATALOG_ITEMS_UPSERT_SPEC = UpsertSpec(
    "catalog_items", ("resource_id",),
    ("id", "uri", "title", "description", "resource_type", "source_format", "version", "sha256", "cas_key", "visibility_scope", "owner_org_unit_id", "owner_workspace_id"),  # noqa: E501
)  # fmt: skip
WORKFLOW_DEFINITIONS_UPSERT_SPEC = UpsertSpec(
    "workflow_definitions", ("uri",),
    ("id", "workspace_id", "version", "source_format", "steps_schema_jsonb", "adaptive_gate_policy", "sha256"),  # noqa: E501
)  # fmt: skip
CUSTOMIZATION_OVERRIDES_UPSERT_SPEC = UpsertSpec(
    "workspace_customization_overrides", ("override_key",),
    ("id", "org_unit_id", "workspace_id", "user_id", "target_uri", "override_layer", "override_manifest_jsonb", "sha256"),  # noqa: E501
)  # fmt: skip
PERMISSION_BROKER_POLICIES_UPSERT_SPEC = UpsertSpec(
    "permission_broker_policies", ("policy_key",),
    ("id", "uri_pattern", "connector_scheme", "required_role", "approver_team", "request_url_template", "sla_hours", "procedure_markdown", "service_principal_allowed", "approved_by_admin_id", "human_anchor_author_id", "human_anchor_signature", "freshness_ttl_days"),  # noqa: E501
)  # fmt: skip
PERMISSION_BROKER_TICKETS_UPSERT_SPEC = UpsertSpec(
    "permission_broker_tickets", ("ticket_key",),
    ("id", "workspace_id", "requester_user_id", "policy_id", "step_key", "step_number", "step_state", "status", "target_uri", "connector_scheme", "execution_identity", "upstream_http_status", "required_role", "approver_team", "sla_hours", "jira_request_url", "permission_broker_hint", "procedure_markdown"),  # noqa: E501
)  # fmt: skip
LLM_MODEL_ENDPOINTS_UPSERT_SPEC = UpsertSpec(
    "llm_model_endpoints", ("endpoint_key",),
    ("id", "provider_slug", "model_family", "model_name", "endpoint_uri", "connectivity_verified", "is_active"),  # noqa: E501
)  # fmt: skip
SYSTEM_BOOTSTRAP_RUNS_UPSERT_SPEC = UpsertSpec(
    "system_bootstrap_runs", ("run_key",),
    ("id", "workflow_uri", "scope_level", "target_org_unit_id", "target_workspace_id", "triggered_by_user_id", "status", "gate_passed", "gate_report_jsonb", "execution_payload_jsonb"),  # noqa: E501
)  # fmt: skip
USER_ONBOARDING_STATES_UPSERT_SPEC = UpsertSpec(
    "user_onboarding_states", ("user_email",),
    ("id", "user_id", "invited_by_user_id", "org_unit_id", "human_profile_archetype", "assigned_role", "workspace_ids_jsonb", "init_user_completed", "linked_connectors_jsonb"),  # noqa: E501
)  # fmt: skip

__all__ = [
    "ASSISTANT_WORKFLOW_URI", "CATALOG_ITEMS_UPSERT_SPEC", "CUSTOMIZATION_OVERRIDES_UPSERT_SPEC",
    "DEFAULT_CATALOG_ITEM_SEEDS", "DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS",
    "DEFAULT_HUMAN_PROFILE_ARCHETYPES", "DEFAULT_LLM_MODEL_ENDPOINT_SEEDS",
    "DEFAULT_ORG_UNIT_SEEDS", "DEFAULT_PERMISSION_BROKER_POLICY_SEEDS",
    "DEFAULT_PERMISSION_BROKER_TICKET_SEEDS", "DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS",
    "DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS", "DEFAULT_USER_ONBOARDING_STATE_SEEDS",
    "DEFAULT_WORKFLOW_DEFINITION_SEEDS", "DEFAULT_WORKSPACE_DATASOURCE_SEEDS",
    "DEFAULT_WORKSPACE_SEEDS", "LLM_MODEL_ENDPOINTS_UPSERT_SPEC", "ORG_UNITS_UPSERT_SPEC",
    "PERMISSION_BROKER_POLICIES_UPSERT_SPEC", "PERMISSION_BROKER_TICKETS_UPSERT_SPEC",
    "SYSTEM_BOOTSTRAP_RUNS_UPSERT_SPEC", "SYSTEM_BOOTSTRAP_WORKFLOW_URIS",
    "USER_ONBOARDING_STATES_UPSERT_SPEC", "WORKFLOW_DEFINITIONS_UPSERT_SPEC",
    "WORKSPACES_UPSERT_SPEC", "WORKSPACE_DATASOURCES_UPSERT_SPEC", "CatalogItemSeed",
    "CustomizationOverrideSeed", "HumanProfileArchetypeSeed", "LlmModelEndpointSeed",
    "OrgUnitSeed", "PermissionBrokerPolicySeed", "PermissionBrokerTicketSeed",
    "SystemBootstrapRunSeed", "SystemBootstrapWorkflowSeed", "UpsertSpec",
    "UserOnboardingStateSeed", "WorkflowDefinitionSeed", "WorkspaceDatasourceSeed",
    "WorkspaceSeed", "build_postgres_upsert_sql",
]  # fmt: skip
