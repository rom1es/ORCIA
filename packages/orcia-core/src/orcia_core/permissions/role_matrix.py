"""Native 6-Role Permission Matrix & RBAC Value Objects (`Story 8.1`, `Story 17.3`, `AD-21`).

Zero framework or SQL imports (`test_hexagonal_purity_permissions_package`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.permissions.errors import ValidationDomainError

PermissionVerb = Literal["create", "read", "update", "delete", "execute", "grant"]
PermissionEffect = Literal["ALLOW", "DENY", "INHERITANCE_BLOCK"]
SubjectType = Literal["USER", "ROLE", "SERVICE_PRINCIPAL"]
OfficialIamRole = Literal[
    "PLATFORM_ADMIN",
    "SECOPS",
    "BU_LEAD",
    "TEAM_LEAD",
    "CONTRIBUTOR",
    "OBSERVER",
]
GrantResourceKind = Literal["ALL", "WORKFLOW", "AGENT", "DATASOURCE", "CONNECTOR"]
RoleNaturalScope = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
SecretVisibilityPolicy = Literal["WRITE_ONLY_NEVER_READABLE"]
RoleMatrixResourceFamily = Literal[
    "workflows",
    "agents",
    "datasources",
    "connectors",
    "org_units",
    "iam_exceptions",
]

ALL_PERMISSION_VERBS: tuple[PermissionVerb, ...] = (
    "create",
    "read",
    "update",
    "delete",
    "execute",
    "grant",
)

VALID_IAM_ROLES: tuple[OfficialIamRole, ...] = (
    "PLATFORM_ADMIN",
    "SECOPS",
    "BU_LEAD",
    "TEAM_LEAD",
    "CONTRIBUTOR",
    "OBSERVER",
)

VALID_GRANT_RESOURCE_KINDS: tuple[GrantResourceKind, ...] = (
    "ALL",
    "WORKFLOW",
    "AGENT",
    "DATASOURCE",
    "CONNECTOR",
)


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def normalize_scope_path(scope_path: str) -> str:
    cleaned = scope_path.strip().strip("/")
    if not cleaned:
        raise ValidationDomainError(detail_override="scope_path must not be empty.")
    return cleaned


def iter_scope_prefixes(scope_path: str) -> list[str]:
    """Return hierarchical prefixes from root to full `scope_path`."""
    cleaned = normalize_scope_path(scope_path)
    segments = [seg for seg in cleaned.split("/") if seg]
    if len(segments) <= 2:
        prefixes = ["/".join(segments[:idx]) for idx in range(1, len(segments) + 1)]
        return prefixes if prefixes else [cleaned]
    prefixes = []
    for idx in range(2, len(segments) + 1, 2):
        prefixes.append("/".join(segments[:idx]))
    if not prefixes or prefixes[-1] != cleaned:
        prefixes.append(cleaned)
    return prefixes


@dataclass(frozen=True, slots=True)
class RolePermissionGrant:
    """Hierarchical 6-verb permission grant (`role_permission_grants`, `Story 8.1`/`17.3`)."""

    id: str
    subject_type: SubjectType
    subject_id: str
    scope_path: str
    verb: PermissionVerb
    effect: PermissionEffect = "ALLOW"
    inheritance_block: bool = False
    resource_kind: GrantResourceKind = "ALL"
    conditions: dict[str, Any] = field(default_factory=dict)
    hidden_when_unauthorized: bool = False
    granted_by_user_id: str | None = None
    created_at_iso: str = field(default_factory=now_utc_iso)


@dataclass(frozen=True, slots=True)
class ResourceDiscoveryOutcome:
    """Result of evaluating a resource under the 6-verb RBAC/ABAC matrix (`AD-21`)."""

    scope_path: str
    title: str
    allowed_verbs: tuple[PermissionVerb, ...]
    locked: bool
    reason: str | None = None
    can_request_access: bool = False
    secret_config_visible: bool = False


@dataclass(frozen=True, slots=True)
class RoleMatrixDescriptor:
    """Structured descriptor of one of the 6 official delegated roles (`CA-17.3.2`, `AD-21`)."""

    role: OfficialIamRole
    natural_scope: RoleNaturalScope
    native_verbs: tuple[PermissionVerb, ...]
    resource_permissions: dict[RoleMatrixResourceFamily, tuple[PermissionVerb, ...]]
    secret_visibility: SecretVisibilityPolicy = "WRITE_ONLY_NEVER_READABLE"


DEFAULT_ROLE_PERMISSION_MATRIX: dict[OfficialIamRole, RoleMatrixDescriptor] = {
    "PLATFORM_ADMIN": RoleMatrixDescriptor(
        role="PLATFORM_ADMIN",
        natural_scope="GLOBAL",
        native_verbs=("create", "read", "update", "delete", "execute", "grant"),
        resource_permissions={
            "workflows": ("create", "read", "update", "delete", "execute"),
            "agents": ("create", "read", "update", "delete", "execute"),
            "datasources": ("create", "read", "update", "delete", "execute"),
            "connectors": ("create", "read", "update", "delete", "execute"),
            "org_units": ("create", "read", "update", "delete"),
            "iam_exceptions": ("read",),
        },
    ),
    "SECOPS": RoleMatrixDescriptor(
        role="SECOPS",
        natural_scope="GLOBAL",
        native_verbs=("read", "update", "grant"),
        resource_permissions={
            "workflows": ("read",),
            "agents": ("read",),
            "datasources": ("read",),
            "connectors": ("read", "update"),
            "org_units": ("read",),
            "iam_exceptions": ("create", "read", "update", "delete", "grant"),
        },
    ),
    "BU_LEAD": RoleMatrixDescriptor(
        role="BU_LEAD",
        natural_scope="BU",
        native_verbs=("create", "read", "update", "delete", "execute", "grant"),
        resource_permissions={
            "workflows": ("create", "read", "update", "execute"),
            "agents": ("create", "read", "update", "execute"),
            "datasources": ("read", "execute"),
            "connectors": ("execute",),
            "org_units": ("create", "read", "update", "delete"),
            "iam_exceptions": ("read",),
        },
    ),
    "TEAM_LEAD": RoleMatrixDescriptor(
        role="TEAM_LEAD",
        natural_scope="TEAM",
        native_verbs=("create", "read", "update", "delete", "execute"),
        resource_permissions={
            "workflows": ("create", "read", "update", "execute"),
            "agents": ("create", "read", "update", "execute"),
            "datasources": ("create", "read", "update", "delete", "execute"),
            "connectors": ("execute",),
            "org_units": ("read", "update"),
            "iam_exceptions": (),
        },
    ),
    "CONTRIBUTOR": RoleMatrixDescriptor(
        role="CONTRIBUTOR",
        natural_scope="WORKSPACE",
        native_verbs=("create", "read", "update", "execute"),
        resource_permissions={
            "workflows": ("read", "execute"),
            "agents": ("read", "execute"),
            "datasources": ("read", "execute"),
            "connectors": ("execute",),
            "org_units": ("read",),
            "iam_exceptions": (),
        },
    ),
    "OBSERVER": RoleMatrixDescriptor(
        role="OBSERVER",
        natural_scope="WORKSPACE",
        native_verbs=("read",),
        resource_permissions={
            "workflows": ("read",),
            "agents": ("read",),
            "datasources": ("read",),
            "connectors": (),
            "org_units": ("read",),
            "iam_exceptions": (),
        },
    ),
}


def list_native_role_matrix() -> tuple[RoleMatrixDescriptor, ...]:
    """Return the ordered 6-role native permission matrix (`VALID_IAM_ROLES`)."""
    return tuple(DEFAULT_ROLE_PERMISSION_MATRIX[r] for r in VALID_IAM_ROLES)


__all__ = [
    "ALL_PERMISSION_VERBS",
    "DEFAULT_ROLE_PERMISSION_MATRIX",
    "GrantResourceKind",
    "OfficialIamRole",
    "PermissionEffect",
    "PermissionVerb",
    "ResourceDiscoveryOutcome",
    "RoleMatrixDescriptor",
    "RoleMatrixResourceFamily",
    "RoleNaturalScope",
    "RolePermissionGrant",
    "SecretVisibilityPolicy",
    "SubjectType",
    "VALID_GRANT_RESOURCE_KINDS",
    "VALID_IAM_ROLES",
    "iter_scope_prefixes",
    "list_native_role_matrix",
    "normalize_scope_path",
    "now_utc_iso",
]
