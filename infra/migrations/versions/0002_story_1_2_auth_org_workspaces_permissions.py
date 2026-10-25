"""Story 1.2 Auth, OrgUnits, Multi-Source Workspaces & 5 Dissociated Permissions.

Revision ID: 0002_story_1_2
Revises: 0001_story_1_1
Create Date: 2026-10-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002_story_1_2"
down_revision: str | None = "0001_story_1_1"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE org_units (
        id UUID PRIMARY KEY,
        slug VARCHAR(128) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        unit_type VARCHAR(32) NOT NULL CHECK (
            unit_type IN ('ENTERPRISE', 'BU', 'TRIBE', 'TEAM', 'SUB_TEAM')
        ),
        parent_id UUID NULL REFERENCES org_units(id) ON DELETE RESTRICT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_org_units_parent_id ON org_units(parent_id);",
    """
    CREATE TABLE users (
        id UUID PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        display_name VARCHAR(255) NOT NULL,
        auth_mode VARCHAR(16) NOT NULL CHECK (auth_mode IN ('OIDC', 'LOCAL', 'HYBRID')),
        oidc_subject VARCHAR(255) NULL UNIQUE,
        password_hash_argon2id TEXT NULL,
        totp_secret_encrypted TEXT NULL,
        totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
        human_profile_archetype VARCHAR(64) NOT NULL,
        platform_role VARCHAR(64) NOT NULL CHECK (
            platform_role IN (
                'PLATFORM_ADMIN',
                'BU_DIRECTOR',
                'TEAM_LEAD',
                'CONTRIBUTOR',
                'GATE_REVIEWER',
                'ONTOLOGY_STEWARD_L3',
                'OBSERVER'
            )
        ),
        primary_org_unit_id UUID NOT NULL REFERENCES org_units(id) ON DELETE RESTRICT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_users_primary_org_unit_id ON users(primary_org_unit_id);",
    """
    CREATE TABLE transverse_groups (
        id UUID PRIMARY KEY,
        slug VARCHAR(128) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE user_transverse_groups (
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        group_id UUID NOT NULL REFERENCES transverse_groups(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (user_id, group_id)
    );
    """,
    """
    CREATE TABLE workspaces (
        id UUID PRIMARY KEY,
        slug VARCHAR(128) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        owner_org_unit_id UUID NOT NULL REFERENCES org_units(id) ON DELETE RESTRICT,
        visibility_mode VARCHAR(32) NOT NULL DEFAULT 'STANDARD' CHECK (
            visibility_mode IN ('STANDARD', 'CONFIDENTIAL_RESTRICTED')
        ),
        settings_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        finops_cost_usd NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_workspaces_owner_org_unit_id ON workspaces(owner_org_unit_id);",
    """
    CREATE TABLE workspace_datasources (
        id UUID PRIMARY KEY,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        alias VARCHAR(128) NOT NULL,
        scheme VARCHAR(32) NOT NULL CHECK (
            scheme IN ('git', 'jira', 'confluence', 'db', 'nexus')
        ),
        uri TEXT NOT NULL,
        role VARCHAR(64) NOT NULL,
        execution_identity VARCHAR(32) NOT NULL DEFAULT 'passthrough' CHECK (
            execution_identity IN ('passthrough', 'service_principal')
        ),
        freshness_ttl_days INTEGER NOT NULL DEFAULT 90 CHECK (freshness_ttl_days > 0),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (workspace_id, alias)
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_workspace_datasources_workspace_id "
        "ON workspace_datasources(workspace_id);"
    ),
    """
    CREATE TABLE workspace_memberships (
        id UUID PRIMARY KEY,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE,
        invited_org_unit_id UUID NULL REFERENCES org_units(id) ON DELETE CASCADE,
        role VARCHAR(64) NOT NULL CHECK (
            role IN (
                'TEAM_LEAD',
                'CONTRIBUTOR',
                'GATE_REVIEWER',
                'ONTOLOGY_STEWARD_L3',
                'OBSERVER'
            )
        ),
        access_mode VARCHAR(64) NOT NULL CHECK (
            access_mode IN ('CONTRIBUTOR_ACTION_REQUIRED', 'READ_ONLY_OBSERVER')
        ),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CHECK (num_nonnulls(user_id, invited_org_unit_id) = 1)
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_workspace_memberships_workspace_id "
        "ON workspace_memberships(workspace_id);"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_workspace_memberships_user_id "
        "ON workspace_memberships(user_id);"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_workspace_memberships_invited_org_unit_id "
        "ON workspace_memberships(invited_org_unit_id);"
    ),
    """
    CREATE TABLE workspace_invitations (
        id UUID PRIMARY KEY,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        email VARCHAR(255) NOT NULL,
        assigned_role VARCHAR(64) NOT NULL CHECK (
            assigned_role IN (
                'TEAM_LEAD',
                'CONTRIBUTOR',
                'GATE_REVIEWER',
                'ONTOLOGY_STEWARD_L3',
                'OBSERVER'
            )
        ),
        assigned_archetype VARCHAR(64) NOT NULL,
        token_sha256 VARCHAR(64) NOT NULL UNIQUE,
        expires_at TIMESTAMPTZ NOT NULL,
        accepted_at TIMESTAMPTZ NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE user_passthrough_credentials (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        connector_scheme VARCHAR(32) NOT NULL CHECK (
            connector_scheme IN ('git', 'jira', 'confluence', 'db', 'nexus')
        ),
        target_host VARCHAR(255) NOT NULL,
        ciphertext_b64 TEXT NOT NULL,
        nonce_b64 TEXT NOT NULL,
        key_version INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, connector_scheme, target_host)
    );
    """,
    """
    CREATE TABLE catalog_acl_entries (
        id UUID PRIMARY KEY,
        resource_id VARCHAR(128) NOT NULL,
        resource_uri TEXT NOT NULL,
        title VARCHAR(255) NOT NULL DEFAULT '',
        visibility_scope VARCHAR(32) NOT NULL CHECK (
            visibility_scope IN (
                'DRAFT',
                'SHARED_WORKSPACE',
                'SHARED_TEAM',
                'SHARED_BU',
                'PUBLISHED_ORG',
                'PENDING_APPROVAL'
            )
        ),
        owner_org_unit_id UUID NOT NULL REFERENCES org_units(id) ON DELETE CASCADE,
        owner_workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        grantee_org_unit_id UUID NULL REFERENCES org_units(id) ON DELETE CASCADE,
        grantee_workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        can_discover BOOLEAN NOT NULL DEFAULT TRUE,
        can_execute BOOLEAN NOT NULL DEFAULT FALSE,
        can_read_source BOOLEAN NOT NULL DEFAULT FALSE,
        can_edit BOOLEAN NOT NULL DEFAULT FALSE,
        can_admin BOOLEAN NOT NULL DEFAULT FALSE,
        system_prompt_secret TEXT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_catalog_acl_entries_resource_uri "
        "ON catalog_acl_entries(resource_uri);"
    ),
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS catalog_acl_entries;",
    "DROP TABLE IF EXISTS user_passthrough_credentials;",
    "DROP TABLE IF EXISTS workspace_invitations;",
    "DROP TABLE IF EXISTS workspace_memberships;",
    "DROP TABLE IF EXISTS workspace_datasources;",
    "DROP TABLE IF EXISTS workspaces;",
    "DROP TABLE IF EXISTS user_transverse_groups;",
    "DROP TABLE IF EXISTS transverse_groups;",
    "DROP TABLE IF EXISTS users;",
    "DROP TABLE IF EXISTS org_units;",
)


def upgrade() -> None:
    """Create Story 1.2 organizational tree, workspaces, auth, and ACL tables."""
    for sql in UPGRADE_STATEMENTS:
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Drop Story 1.2 organizational tree, workspaces, auth, and ACL tables."""
    for sql in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(sql))
