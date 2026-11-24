"""Default in-memory topology builder for Permissions & Auth domain (`AD-19`)."""

from __future__ import annotations

from typing import cast

from orcia_core.permissions._permissions_locales import (
    DEFAULT_SERVICE_CATALOG_TITLES,
    DEFAULT_SERVICE_PERSONA_NAMES,
)
from orcia_core.permissions.crypto import Argon2idPasswordHasher
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    CatalogAclEntry,
    ExecutionIdentityMode,
    OrgUnitNode,
    OrgUnitType,
    UserIdentity,
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
    RevocationStoreProtocol,
)


def build_default_auth_and_org_service(
    revocation_store: RevocationStoreProtocol | None = None,
    *,
    allow_persona_impersonation: bool = True,
    seed_reference_personas: bool = True,
) -> AuthAndOrganizationService:
    """Build the topology and optional test personas (`seed_reference_personas`).

    Real runtime uses `seed_reference_personas=should_seed_test_personas_in_memory()`
    so real PostgreSQL instances start with zero in-memory mock personas (`Marc`, `Karim`, etc.).
    """
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
    cat_titles = DEFAULT_SERVICE_CATALOG_TITLES["fr"]
    p_names = DEFAULT_SERVICE_PERSONA_NAMES["fr"]
    catalog_acls = (
        CatalogAclEntry(
            id="0192c4e0-0000-7000-8000-000000000501",
            resource_id="res-blackbox-security-agent",
            resource_uri="git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0",
            title=cat_titles["blackbox"],
            visibility_scope="SHARED_TEAM",
            owner_org_unit_id="0192c4e0-0000-7000-8000-000000000103",
            can_discover=True,
            can_execute=True,
            can_read_source=False,
            can_edit=False,
            can_admin=False,
            system_prompt_secret=(  # pragma: allowlist secret
                "SYSTEM_SECRET: Audit OWASP & PCI-DSS strict ruleset v2.1"
            ),
        ),
        CatalogAclEntry(
            id="0192c4e0-0000-7000-8000-000000000502",
            resource_id="res-open-checkout-skill",
            resource_uri="git://gitlab.entreprise.io/payments/checkout-web/skills/payment-flow@v1.0.0",
            title=cat_titles["checkout"],
            visibility_scope="SHARED_WORKSPACE",
            owner_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
            owner_workspace_id="0192c4e0-0000-7000-8000-000000000201",
            can_discover=True,
            can_execute=True,
            can_read_source=True,
            can_edit=True,
            can_admin=True,
            system_prompt_secret=(  # pragma: allowlist secret
                "OPEN_SKILL_SOURCE: Checkout validation workflow steps"
            ),
        ),
    )
    users: tuple[UserIdentity, ...]
    persona_map: dict[str, str]
    if seed_reference_personas:
        users = (
            UserIdentity(
                id="0192c4e0-0000-7000-8000-000000000601",
                email="karim.admin@orcia.io",
                display_name=p_names["karim"],
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
                display_name=p_names["claire"],
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
                display_name=p_names["marc"],
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
                display_name=p_names["nadia"],
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
                display_name=p_names["partenaire"],
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
    else:
        users = ()
        persona_map = {}
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
        allow_persona_impersonation=allow_persona_impersonation,
    )


__all__ = ["build_default_auth_and_org_service"]
