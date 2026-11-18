"""OpenAPI 3.1 / Pydantic v2 transport schemas for Story 17.3 IAM Accounts & 6-Role Matrix.

Kept exclusively in `apps/api/src/orcia_api/schemas/` — never inside `orcia-core` (`AD-19`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OfficialIamRoleLiteral = Literal[
    "PLATFORM_ADMIN",
    "SECOPS",
    "BU_LEAD",
    "TEAM_LEAD",
    "ONTOLOGY_LEAD",
    "CONTRIBUTOR",
    "OBSERVER",
]
IamAccountKindLiteral = Literal["HUMAN", "SERVICE_PRINCIPAL"]
IamAuthSourceLiteral = Literal[
    "LOCAL_BOOTSTRAP",
    "LOCAL_PASSWORD",
    "OIDC_FEDERATED",
    "SERVICE_TOKEN",
]
IamAccountStatusLiteral = Literal["ACTIVE", "INVITED", "DISABLED"]
RoleNaturalScopeLiteral = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
PermissionVerbLiteral = Literal["create", "read", "update", "delete", "execute", "grant"]
SecretVisibilityPolicyLiteral = Literal["WRITE_ONLY_NEVER_READABLE"]


class IamAccountResponse(BaseModel):
    """Serialized IAM directory account (`HUMAN` or `SERVICE_PRINCIPAL`, `Story 17.3`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    principal_id: str
    display_name: str
    email: str | None = None
    account_kind: IamAccountKindLiteral
    auth_source: IamAuthSourceLiteral
    roles: list[OfficialIamRoleLiteral]
    team_ids: list[str]
    status: IamAccountStatusLiteral
    temporary_password: str | None = Field(default=None)  # pragma: allowlist secret
    created_at_iso: str
    updated_at_iso: str
    led_bu_ids: list[str] = Field(default_factory=list)
    led_team_ids: list[str] = Field(default_factory=list)
    ontology_led_bu_ids: list[str] = Field(default_factory=list)


class IamAccountsListResponse(BaseModel):
    """Envelope returned by `GET /api/v1/settings/iam/accounts` (`Story 17.3`)."""

    model_config = ConfigDict(extra="forbid")

    accounts: list[IamAccountResponse]
    trace_id: str


class IamAccountCreateRequest(BaseModel):
    """Payload for `POST /api/v1/settings/iam/accounts` (`Story 17.3`)."""

    model_config = ConfigDict(extra="forbid")

    principal_id: str | None = Field(default=None, max_length=128)
    display_name: str = Field(default="Nouveau Compte", min_length=1, max_length=160)
    email: str | None = Field(default=None, max_length=255)
    account_kind: IamAccountKindLiteral = "HUMAN"
    auth_source: IamAuthSourceLiteral | None = None
    roles: list[str] = Field(default_factory=lambda: ["CONTRIBUTOR"], max_length=12)
    team_ids: list[str] = Field(default_factory=list, max_length=64)
    status: IamAccountStatusLiteral = "ACTIVE"
    led_bu_ids: list[str] | None = Field(default=None, max_length=64)
    led_team_ids: list[str] | None = Field(default=None, max_length=64)
    ontology_led_bu_ids: list[str] | None = Field(default=None, max_length=64)


class IamAccountPatchRequest(BaseModel):
    """Payload for `PATCH /api/v1/settings/iam/accounts/{account_id}` (`Story 17.3`)."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    email: str | None = Field(default=None, max_length=255)
    roles: list[str] | None = Field(default=None, max_length=12)
    team_ids: list[str] | None = Field(default=None, max_length=64)
    status: IamAccountStatusLiteral | None = None
    led_bu_ids: list[str] | None = Field(default=None, max_length=64)
    led_team_ids: list[str] | None = Field(default=None, max_length=64)
    ontology_led_bu_ids: list[str] | None = Field(default=None, max_length=64)


class IamAccountDeleteResponse(BaseModel):
    """Envelope returned by `DELETE /api/v1/settings/iam/accounts/{account_id}` (`Story 17.3`)."""

    model_config = ConfigDict(extra="forbid")

    deleted_id: str
    trace_id: str


class RoleMatrixEntryResponse(BaseModel):
    """Native role descriptor in the closed 6-role matrix (`Story 17.3`, `AD-21`)."""

    model_config = ConfigDict(extra="forbid")

    role: OfficialIamRoleLiteral
    natural_scope: RoleNaturalScopeLiteral
    native_verbs: list[PermissionVerbLiteral]
    resource_permissions: dict[str, list[PermissionVerbLiteral]]
    secret_visibility: SecretVisibilityPolicyLiteral


class RoleMatrixResponse(BaseModel):
    """Envelope returned by `GET /api/v1/settings/iam/role-matrix` (`Story 17.3`, `AD-21`)."""

    model_config = ConfigDict(extra="forbid")

    secret_visibility_policy: SecretVisibilityPolicyLiteral
    roles: list[RoleMatrixEntryResponse]
    trace_id: str
