"""Bounded Context 7: Permissions (5 Dissociated Catalog Permissions, Scope Guard & Broker)."""

from __future__ import annotations

from typing import cast

from orcia_core.permissions.broker import (
    BrokerConnectorScheme,
    BrokerStepState,
    BrokerTicketAction,
    BrokerTicketStatus,
    PermissionBrokerPolicy,
    PermissionBrokerService,
    PermissionBrokerTicket,
    PermissionCheckOutcome,
    build_default_permission_broker_service,
    build_prefilled_jira_request_url,
    extract_connector_scheme,
    parse_permission_kb_markdown,
)
from orcia_core.permissions.crypto import (
    ACCESS_TOKEN_TTL_SECONDS,
    REFRESH_TOKEN_TTL_SECONDS,
    Argon2idPasswordHasher,
    JwtSessionManager,
    PassthroughVaultCipher,
    SessionTokenPair,
    TokenClaims,
    TotpManager,
)
from orcia_core.permissions.evaluator import (
    ADMIN_MODULE_ALLOWED_ROLES,
    ROLLUP_SUPERVISOR_ROLES,
    MatrixPermissionEvaluator,
)
from orcia_core.permissions.models import (
    AccessMode,
    AuthMode,
    CatalogAclEntry,
    CatalogPermission,
    CatalogVisibilityScope,
    DatasourceScheme,
    EffectiveResourcePermissions,
    ExecutionIdentityMode,
    OrgUnitNode,
    OrgUnitType,
    PassthroughCredentialRecord,
    PlatformRole,
    UserIdentity,
    WorkspaceAccessSummary,
    WorkspaceDatasourceEntity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
    WorkspaceVisibilityMode,
)
from orcia_core.permissions.seeds import (
    DEFAULT_ORG_UNIT_SEEDS,
    DEFAULT_WORKSPACE_DATASOURCE_SEEDS,
    DEFAULT_WORKSPACE_SEEDS,
)
from orcia_core.permissions.service import (
    DEFAULT_TOTP_SECRET_KARIM,
    AuthAndOrganizationService,
    InMemoryRevocationStore,
    KeyValueRevocationStore,
    RevocationStoreProtocol,
)

DOMAIN_NAME: str = "permissions"


def build_default_auth_and_org_service(
    revocation_store: RevocationStoreProtocol | None = None,
) -> AuthAndOrganizationService:
    """Build the reference Story 1.2 topology (`Karim`, `Claire`, `Marc`, `Nadia`, `Partenaire`)."""
    hasher = Argon2idPasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    org_units = tuple(
        OrgUnitNode(
            id=s.id,
            slug=s.slug,
            name=s.name,
            unit_type=cast(OrgUnitType, s.unit_type),
            parent_id=s.parent_id,
        )
        for s in DEFAULT_ORG_UNIT_SEEDS
    )
    datasources_by_ws: dict[str, list[WorkspaceDatasourceEntity]] = {}
    for ds in DEFAULT_WORKSPACE_DATASOURCE_SEEDS:
        datasources_by_ws.setdefault(ds.workspace_id, []).append(
            WorkspaceDatasourceEntity(
                id=ds.id,
                workspace_id=ds.workspace_id,
                alias=ds.alias,
                scheme=ds.scheme,
                uri=ds.uri,
                role=ds.role,
                execution_identity=cast(ExecutionIdentityMode, ds.execution_identity),
                freshness_ttl_days=ds.freshness_ttl_days,
            )
        )
    workspaces = tuple(
        WorkspaceEntity(
            id=w.id,
            slug=w.slug,
            name=w.name,
            owner_org_unit_id=w.owner_org_unit_id,
            visibility_mode=cast(WorkspaceVisibilityMode, w.visibility_mode),
            finops_cost_usd=w.finops_cost_usd,
            datasources=tuple(datasources_by_ws.get(w.id, ())),
        )
        for w in DEFAULT_WORKSPACE_SEEDS
    )
    memberships = (
        WorkspaceMembershipEntity(
            id="0192c4e0-0000-7000-8000-000000000401",
            workspace_id="0192c4e0-0000-7000-8000-000000000201",
            invited_org_unit_id="0192c4e0-0000-7000-8000-000000000105",
            role="CONTRIBUTOR",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        ),
    )
    catalog_acls = (
        CatalogAclEntry(
            id="0192c4e0-0000-7000-8000-000000000501",
            resource_id="res-blackbox-security-agent",
            resource_uri="git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0",
            title="Agent d'Audit SecOps Boîte Noire (Équipe Parente)",
            visibility_scope="SHARED_TEAM",
            owner_org_unit_id="0192c4e0-0000-7000-8000-000000000103",
            can_discover=True,
            can_execute=True,
            can_read_source=False,
            can_edit=False,
            can_admin=False,
            system_prompt_secret="SYSTEM_SECRET: Audit OWASP & PCI-DSS strict ruleset v2.1",
        ),
        CatalogAclEntry(
            id="0192c4e0-0000-7000-8000-000000000502",
            resource_id="res-open-checkout-skill",
            resource_uri="git://gitlab.entreprise.io/payments/checkout-web/skills/payment-flow@v1.0.0",
            title="Skill Validation Checkout (Source Ouverte Équipe)",
            visibility_scope="SHARED_WORKSPACE",
            owner_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
            owner_workspace_id="0192c4e0-0000-7000-8000-000000000201",
            can_discover=True,
            can_execute=True,
            can_read_source=True,
            can_edit=True,
            can_admin=True,
            system_prompt_secret="OPEN_SKILL_SOURCE: Checkout validation workflow steps",
        ),
    )
    users = (
        UserIdentity(
            id="0192c4e0-0000-7000-8000-000000000601",
            email="karim.admin@orcia.io",
            display_name="Karim (Ingénieur Plateforme)",
            auth_mode="HYBRID",
            oidc_subject="oidc|karim-admin",
            password_hash_argon2id=hasher.hash_password("OrciaAdmin!2026"),
            totp_secret=DEFAULT_TOTP_SECRET_KARIM,
            totp_enabled=True,
            human_profile_archetype="SECOPS",
            platform_role="PLATFORM_ADMIN",
            primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
            transverse_groups=("guild-secops",),
        ),
        UserIdentity(
            id="0192c4e0-0000-7000-8000-000000000602",
            email="claire.bu@orcia.io",
            display_name="Claire (Directrice BU / Équipe Parente)",
            auth_mode="HYBRID",
            oidc_subject="oidc|claire-bu",
            password_hash_argon2id=hasher.hash_password("OrciaDirector!2026"),
            totp_enabled=False,
            human_profile_archetype="EXECUTIVE",
            platform_role="BU_DIRECTOR",
            primary_org_unit_id="0192c4e0-0000-7000-8000-000000000102",
            transverse_groups=("architecture-board",),
        ),
        UserIdentity(
            id="0192c4e0-0000-7000-8000-000000000603",
            email="marc.lead@orcia.io",
            display_name="Marc (Chef d'Équipe / Tech Lead)",
            auth_mode="HYBRID",
            oidc_subject="oidc|marc-lead",
            password_hash_argon2id=hasher.hash_password("OrciaLead!2026"),
            totp_enabled=False,
            human_profile_archetype="TECH_LEAD",
            platform_role="TEAM_LEAD",
            primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
            transverse_groups=("architecture-board",),
        ),
        UserIdentity(
            id="0192c4e0-0000-7000-8000-000000000604",
            email="nadia.dev@orcia.io",
            display_name="Nadia (Développeuse Senior)",
            auth_mode="LOCAL",
            password_hash_argon2id=hasher.hash_password("OrciaDev!2026"),
            totp_enabled=False,
            human_profile_archetype="DEVELOPER",
            platform_role="CONTRIBUTOR",
            primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
        ),
        UserIdentity(
            id="0192c4e0-0000-7000-8000-000000000605",
            email="partenaire.ext@partner.io",
            display_name="Partenaire Externe (Invité Workspace 1)",
            auth_mode="OIDC",
            oidc_subject="oidc|partner-ext",
            totp_enabled=False,
            human_profile_archetype="DEVELOPER",
            platform_role="CONTRIBUTOR",
            primary_org_unit_id="0192c4e0-0000-7000-8000-000000000105",
        ),
    )
    persona_map = {
        "karim": "0192c4e0-0000-7000-8000-000000000601",
        "claire": "0192c4e0-0000-7000-8000-000000000602",
        "marc": "0192c4e0-0000-7000-8000-000000000603",
        "nadia": "0192c4e0-0000-7000-8000-000000000604",
        "partenaire": "0192c4e0-0000-7000-8000-000000000605",
    }
    evaluator = MatrixPermissionEvaluator(
        org_units=org_units,
        workspaces=workspaces,
        memberships=memberships,
        catalog_acls=catalog_acls,
    )
    return AuthAndOrganizationService(
        evaluator=evaluator,
        users=users,
        persona_map=persona_map,
        hasher=hasher,
        revocation_store=revocation_store,
    )


__all__ = [
    "ACCESS_TOKEN_TTL_SECONDS",
    "ADMIN_MODULE_ALLOWED_ROLES",
    "DEFAULT_TOTP_SECRET_KARIM",
    "DOMAIN_NAME",
    "REFRESH_TOKEN_TTL_SECONDS",
    "ROLLUP_SUPERVISOR_ROLES",
    "AccessMode",
    "Argon2idPasswordHasher",
    "AuthAndOrganizationService",
    "AuthMode",
    "BrokerConnectorScheme",
    "BrokerStepState",
    "BrokerTicketAction",
    "BrokerTicketStatus",
    "CatalogAclEntry",
    "CatalogPermission",
    "CatalogVisibilityScope",
    "DatasourceScheme",
    "EffectiveResourcePermissions",
    "ExecutionIdentityMode",
    "InMemoryRevocationStore",
    "JwtSessionManager",
    "KeyValueRevocationStore",
    "MatrixPermissionEvaluator",
    "OrgUnitNode",
    "OrgUnitType",
    "PassthroughCredentialRecord",
    "PassthroughVaultCipher",
    "PermissionBrokerPolicy",
    "PermissionBrokerService",
    "PermissionBrokerTicket",
    "PermissionCheckOutcome",
    "PlatformRole",
    "RevocationStoreProtocol",
    "SessionTokenPair",
    "TokenClaims",
    "TotpManager",
    "UserIdentity",
    "WorkspaceAccessSummary",
    "WorkspaceDatasourceEntity",
    "WorkspaceEntity",
    "WorkspaceMembershipEntity",
    "WorkspaceVisibilityMode",
    "build_default_auth_and_org_service",
    "build_default_permission_broker_service",
    "build_prefilled_jira_request_url",
    "extract_connector_scheme",
    "parse_permission_kb_markdown",
]
