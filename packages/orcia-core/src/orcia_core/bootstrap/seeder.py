"""Idempotent reference data seeder foundation (`INSERT ... ON CONFLICT DO UPDATE`, AD-16)."""

from __future__ import annotations

import re
from dataclasses import dataclass

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
        id="0192c4e0-0000-7000-8000-000000000101",
        slug="orcia-enterprise",
        name="Entreprise ORCIA Group",
        unit_type="ENTERPRISE",
        parent_id=None,
    ),
    OrgUnitSeed(
        id="0192c4e0-0000-7000-8000-000000000102",
        slug="bu-digital-payments",
        name="BU Digital & Paiements",
        unit_type="BU",
        parent_id="0192c4e0-0000-7000-8000-000000000101",
    ),
    OrgUnitSeed(
        id="0192c4e0-0000-7000-8000-000000000103",
        slug="team-architecture-parent",
        name="Équipe Parente Architecture & Plateforme",
        unit_type="TEAM",
        parent_id="0192c4e0-0000-7000-8000-000000000102",
    ),
    OrgUnitSeed(
        id="0192c4e0-0000-7000-8000-000000000104",
        slug="subteam-checkout-squad",
        name="Sous-Équipe Checkout & Core Solutions",
        unit_type="SUB_TEAM",
        parent_id="0192c4e0-0000-7000-8000-000000000103",
    ),
    OrgUnitSeed(
        id="0192c4e0-0000-7000-8000-000000000105",
        slug="team-partner-external",
        name="Équipe Partenaire Intégration",
        unit_type="TEAM",
        parent_id="0192c4e0-0000-7000-8000-000000000101",
    ),
)

DEFAULT_WORKSPACE_SEEDS: tuple[WorkspaceSeed, ...] = (
    WorkspaceSeed(
        id="0192c4e0-0000-7000-8000-000000000201",
        slug="ws-solution-paiement",
        name="Workspace 1 : Solution Paiement",
        owner_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
        visibility_mode="STANDARD",
        finops_cost_usd=142.50,
    ),
    WorkspaceSeed(
        id="0192c4e0-0000-7000-8000-000000000202",
        slug="ws-solution-fidelite",
        name="Workspace 2 : Solution Fidélité",
        owner_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
        visibility_mode="STANDARD",
        finops_cost_usd=87.25,
    ),
    WorkspaceSeed(
        id="0192c4e0-0000-7000-8000-000000000203",
        slug="ws-projet-confidentiel",
        name="Workspace 3 : Projet Confidentiel M&A",
        owner_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
        visibility_mode="CONFIDENTIAL_RESTRICTED",
        finops_cost_usd=310.00,
    ),
)

DEFAULT_WORKSPACE_DATASOURCE_SEEDS: tuple[WorkspaceDatasourceSeed, ...] = (
    # Workspace 1 (Solution Paiement): 3 git://, 2 jira://, 2 confluence://
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000301",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        alias="git-payment-frontend",
        scheme="git",
        uri="git://gitlab.entreprise.io/payments/checkout-web",
        role="code_frontend",
    ),
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000302",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        alias="git-payment-api",
        scheme="git",
        uri="git://gitlab.entreprise.io/payments/ledger-api",
        role="code_backend",
    ),
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000303",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        alias="git-payment-infra",
        scheme="git",
        uri="git://gitlab.entreprise.io/payments/infra-terraform",
        role="infra_iac",
    ),
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000304",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        alias="jira-pay-build",
        scheme="jira",
        uri="jira://jira.entreprise.io/projects/PAYBUILD",
        role="backlog_build",
    ),
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000305",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        alias="jira-pay-run",
        scheme="jira",
        uri="jira://jira.entreprise.io/projects/PAYSEC",
        role="incidents_secops",
    ),
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000306",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        alias="confluence-pay-product",
        scheme="confluence",
        uri="confluence://wiki.entreprise.io/spaces/PAYPROD",
        role="kb_product",
    ),
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000307",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        alias="confluence-pay-adr",
        scheme="confluence",
        uri="confluence://wiki.entreprise.io/spaces/PAYADR",
        role="kb_architecture",
    ),
    # Workspace 2 (Solution Fidélité): isolated datasources
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000308",
        workspace_id="0192c4e0-0000-7000-8000-000000000202",
        alias="git-loyalty-core",
        scheme="git",
        uri="git://gitlab.entreprise.io/loyalty/rewards-engine",
        role="code_backend",
    ),
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000309",
        workspace_id="0192c4e0-0000-7000-8000-000000000202",
        alias="jira-loyalty-backlog",
        scheme="jira",
        uri="jira://jira.entreprise.io/projects/LOYALTY",
        role="backlog_build",
    ),
    WorkspaceDatasourceSeed(
        id="0192c4e0-0000-7000-8000-000000000310",
        workspace_id="0192c4e0-0000-7000-8000-000000000202",
        alias="confluence-loyalty-kb",
        scheme="confluence",
        uri="confluence://wiki.entreprise.io/spaces/LOYKB",
        role="kb_product",
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
