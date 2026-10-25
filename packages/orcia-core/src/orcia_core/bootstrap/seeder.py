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

    all_cols = list(dict.fromkeys([*conflict_cols, *value_cols]))
    cols_clause = ", ".join(all_cols)
    params_clause = ", ".join(f":{col}" for col in all_cols)
    conflict_clause = ", ".join(conflict_cols)
    update_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in value_cols)

    return (
        f"INSERT INTO {table} ({cols_clause}) "
        f"VALUES ({params_clause}) "
        f"ON CONFLICT ({conflict_clause}) DO UPDATE SET {update_clause};"
    )
