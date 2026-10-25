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

IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

CONCIERGE_WORKFLOW_URI: str = "orcia://system/workflows/concierge-agent"

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


@dataclass(frozen=True, slots=True)
class OrgUnitSeed:
    """Reference OrgUnit node for hierarchical team tree bootstrap (AD-6, AD-14)."""

    id: str
    slug: str
    name: str
    unit_type: str
    parent_id: str | None


@dataclass(frozen=True, slots=True)
class WorkspaceSeed:
    """Reference Solution Workspace seed decoupled from OrgUnits (AD-6, AD-14)."""

    id: str
    slug: str
    name: str
    owner_org_unit_id: str
    visibility_mode: str
    finops_cost_usd: float


@dataclass(frozen=True, slots=True)
class WorkspaceDatasourceSeed:
    """Reference federated datasource attached to a Solution Workspace (`1..N` per scheme)."""

    id: str
    workspace_id: str
    alias: str
    scheme: str
    uri: str
    role: str
    execution_identity: str = "passthrough"
    freshness_ttl_days: int = 90


DEFAULT_ORG_UNIT_SEEDS: tuple[OrgUnitSeed, ...] = (
    OrgUnitSeed(
        "0192c4e0-0000-7000-8000-000000000101",
        "orcia-enterprise",
        "Entreprise ORCIA Group",
        "ENTERPRISE",
        None,
    ),
    OrgUnitSeed(
        "0192c4e0-0000-7000-8000-000000000102",
        "bu-digital-payments",
        "BU Digital & Paiements",
        "BU",
        "0192c4e0-0000-7000-8000-000000000101",
    ),
    OrgUnitSeed(
        "0192c4e0-0000-7000-8000-000000000103",
        "team-architecture-parent",
        "Équipe Parente Architecture & Plateforme",
        "TEAM",
        "0192c4e0-0000-7000-8000-000000000102",
    ),
    OrgUnitSeed(
        "0192c4e0-0000-7000-8000-000000000104",
        "subteam-checkout-squad",
        "Sous-Équipe Checkout & Core Solutions",
        "SUB_TEAM",
        "0192c4e0-0000-7000-8000-000000000103",
    ),
    OrgUnitSeed(
        "0192c4e0-0000-7000-8000-000000000105",
        "team-partner-external",
        "Équipe Partenaire Intégration",
        "TEAM",
        "0192c4e0-0000-7000-8000-000000000101",
    ),
)

DEFAULT_WORKSPACE_SEEDS: tuple[WorkspaceSeed, ...] = (
    WorkspaceSeed(
        "0192c4e0-0000-7000-8000-000000000201",
        "ws-solution-paiement",
        "Workspace 1 : Solution Paiement",
        "0192c4e0-0000-7000-8000-000000000104",
        "STANDARD",
        142.50,
    ),
    WorkspaceSeed(
        "0192c4e0-0000-7000-8000-000000000202",
        "ws-solution-fidelite",
        "Workspace 2 : Solution Fidélité",
        "0192c4e0-0000-7000-8000-000000000104",
        "STANDARD",
        87.25,
    ),
    WorkspaceSeed(
        "0192c4e0-0000-7000-8000-000000000203",
        "ws-projet-confidentiel",
        "Workspace 3 : Projet Confidentiel M&A",
        "0192c4e0-0000-7000-8000-000000000104",
        "CONFIDENTIAL_RESTRICTED",
        310.00,
    ),
)

DEFAULT_WORKSPACE_DATASOURCE_SEEDS: tuple[WorkspaceDatasourceSeed, ...] = (
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000301",
        "0192c4e0-0000-7000-8000-000000000201",
        "git-payment-frontend",
        "git",
        "git://gitlab.entreprise.io/payments/checkout-web",
        "code_frontend",
    ),
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000302",
        "0192c4e0-0000-7000-8000-000000000201",
        "git-payment-api",
        "git",
        "git://gitlab.entreprise.io/payments/ledger-api",
        "code_backend",
    ),
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000303",
        "0192c4e0-0000-7000-8000-000000000201",
        "git-payment-infra",
        "git",
        "git://gitlab.entreprise.io/payments/infra-terraform",
        "infra_iac",
    ),
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000304",
        "0192c4e0-0000-7000-8000-000000000201",
        "jira-pay-build",
        "jira",
        "jira://jira.entreprise.io/projects/PAYBUILD",
        "backlog_build",
    ),
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000305",
        "0192c4e0-0000-7000-8000-000000000201",
        "jira-pay-run",
        "jira",
        "jira://jira.entreprise.io/projects/PAYSEC",
        "incidents_secops",
    ),
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000306",
        "0192c4e0-0000-7000-8000-000000000201",
        "confluence-pay-product",
        "confluence",
        "confluence://wiki.entreprise.io/spaces/PAYPROD",
        "kb_product",
    ),
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000307",
        "0192c4e0-0000-7000-8000-000000000201",
        "confluence-pay-adr",
        "confluence",
        "confluence://wiki.entreprise.io/spaces/PAYADR",
        "kb_architecture",
    ),
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000308",
        "0192c4e0-0000-7000-8000-000000000202",
        "git-loyalty-core",
        "git",
        "git://gitlab.entreprise.io/loyalty/rewards-engine",
        "code_backend",
    ),
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000309",
        "0192c4e0-0000-7000-8000-000000000202",
        "jira-loyalty-backlog",
        "jira",
        "jira://jira.entreprise.io/projects/LOYALTY",
        "backlog_build",
    ),
    WorkspaceDatasourceSeed(
        "0192c4e0-0000-7000-8000-000000000310",
        "0192c4e0-0000-7000-8000-000000000202",
        "confluence-loyalty-kb",
        "confluence",
        "confluence://wiki.entreprise.io/spaces/LOYKB",
        "kb_product",
    ),
)

ORG_UNITS_UPSERT_SPEC = UpsertSpec(
    table="org_units",
    conflict_columns=("slug",),
    value_columns=("id", "name", "unit_type", "parent_id"),
)

WORKSPACES_UPSERT_SPEC = UpsertSpec(
    table="workspaces",
    conflict_columns=("slug",),
    value_columns=("id", "name", "owner_org_unit_id", "visibility_mode", "finops_cost_usd"),
)

WORKSPACE_DATASOURCES_UPSERT_SPEC = UpsertSpec(
    table="workspace_datasources",
    conflict_columns=("workspace_id", "alias"),
    value_columns=("id", "scheme", "uri", "role", "execution_identity", "freshness_ttl_days"),
)

CATALOG_ITEMS_UPSERT_SPEC = UpsertSpec(
    table="catalog_items",
    conflict_columns=("resource_id",),
    value_columns=(
        "id",
        "uri",
        "title",
        "description",
        "resource_type",
        "source_format",
        "version",
        "sha256",
        "cas_key",
        "visibility_scope",
        "owner_org_unit_id",
        "owner_workspace_id",
    ),
)

WORKFLOW_DEFINITIONS_UPSERT_SPEC = UpsertSpec(
    table="workflow_definitions",
    conflict_columns=("uri",),
    value_columns=(
        "id",
        "workspace_id",
        "version",
        "source_format",
        "steps_schema_jsonb",
        "adaptive_gate_policy",
        "sha256",
    ),
)

CUSTOMIZATION_OVERRIDES_UPSERT_SPEC = UpsertSpec(
    table="workspace_customization_overrides",
    conflict_columns=("override_key",),
    value_columns=(
        "id",
        "org_unit_id",
        "workspace_id",
        "user_id",
        "target_uri",
        "override_layer",
        "override_manifest_jsonb",
        "sha256",
    ),
)

__all__ = [
    "CATALOG_ITEMS_UPSERT_SPEC",
    "CONCIERGE_WORKFLOW_URI",
    "CUSTOMIZATION_OVERRIDES_UPSERT_SPEC",
    "DEFAULT_CATALOG_ITEM_SEEDS",
    "DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS",
    "DEFAULT_HUMAN_PROFILE_ARCHETYPES",
    "DEFAULT_ORG_UNIT_SEEDS",
    "DEFAULT_WORKFLOW_DEFINITION_SEEDS",
    "DEFAULT_WORKSPACE_DATASOURCE_SEEDS",
    "DEFAULT_WORKSPACE_SEEDS",
    "ORG_UNITS_UPSERT_SPEC",
    "SYSTEM_BOOTSTRAP_WORKFLOW_URIS",
    "WORKFLOW_DEFINITIONS_UPSERT_SPEC",
    "WORKSPACES_UPSERT_SPEC",
    "WORKSPACE_DATASOURCES_UPSERT_SPEC",
    "CatalogItemSeed",
    "CustomizationOverrideSeed",
    "HumanProfileArchetypeSeed",
    "OrgUnitSeed",
    "UpsertSpec",
    "WorkflowDefinitionSeed",
    "WorkspaceDatasourceSeed",
    "WorkspaceSeed",
    "build_postgres_upsert_sql",
]
