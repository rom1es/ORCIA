"""Story 31.1 — Declarative Pack Bundles v2 DDL, Drafts, Activations & Slot Bindings.

Revision ID: 20261126_311
Revises: 20261125_303
Create Date: 2026-11-26 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261126_311"
down_revision: str | None = "20261125_303"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

_CHILD_UNIQUE_SPECS: tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...] = (
    ("catalog_items", (("resource_id", "resource_id", "catalog_items_resource_id_key"),)),
    (
        "workflow_definitions_v2",
        (("id_ver", "workflow_id, version", "uq_workflow_definitions_v2_id_ver"),),
    ),
    (
        "vsm_definitions_v2",
        (
            ("vsm_id", "vsm_id", "vsm_definitions_v2_vsm_id_key"),
            ("slug", "slug", "vsm_definitions_v2_slug_key"),
        ),
    ),
    (
        "ontology_concepts",
        (
            ("key", "concept_key", "ontology_concepts_concept_key_key"),
            (
                "scope_term",
                "level, scope_id, canonical_term",
                "ontology_concepts_level_scope_id_canonical_term_key",
            ),
        ),
    ),
    ("ontology_relations", (("key", "relation_key", "ontology_relations_relation_key_key"),)),
    ("ontology_axioms", (("key", "axiom_key", "ontology_axioms_axiom_key_key"),)),
    (
        "permission_broker_policies",
        (
            ("key", "policy_key", "permission_broker_policies_policy_key_key"),
            ("uri", "uri_pattern", "permission_broker_policies_uri_pattern_key"),
        ),
    ),
)

_PACK_TRIGGER_STATEMENTS: tuple[str, ...] = (
    """
    CREATE OR REPLACE FUNCTION fn_enforce_workspace_pack_activation_scope()
    RETURNS TRIGGER AS $$
    DECLARE v_scope_type TEXT; v_scope_id TEXT;
    BEGIN
        SELECT scope_type, scope_id INTO v_scope_type, v_scope_id
          FROM declarative_pack_bundles WHERE id = NEW.pack_bundle_id;
        IF v_scope_type = 'WORKSPACE' AND v_scope_id <> NEW.workspace_id::text THEN
            RAISE EXCEPTION 'Cross-workspace pack activation forbidden (% <> %)',
                v_scope_id, NEW.workspace_id;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """,
    "DROP TRIGGER IF EXISTS trg_workspace_pack_activations_scope_guard ON workspace_pack_activations;",  # noqa: E501
    """
    CREATE TRIGGER trg_workspace_pack_activations_scope_guard
        BEFORE INSERT OR UPDATE ON workspace_pack_activations
        FOR EACH ROW EXECUTE FUNCTION fn_enforce_workspace_pack_activation_scope();
    """,
)

_BUNDLE_UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    ALTER TABLE declarative_pack_bundles
        ADD COLUMN IF NOT EXISTS bundle_kind TEXT NOT NULL DEFAULT 'SYSTEM',
        ADD COLUMN IF NOT EXISTS scope_type TEXT NOT NULL DEFAULT 'GLOBAL',
        ADD COLUMN IF NOT EXISTS scope_id TEXT NOT NULL DEFAULT 'global',
        ADD COLUMN IF NOT EXISTS archive_sha256 CHAR(64),
        ADD COLUMN IF NOT EXISTS cas_object_key TEXT,
        ADD COLUMN IF NOT EXISTS manifest_yaml TEXT,
        ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'PUBLISHED',
        ADD COLUMN IF NOT EXISTS source_origin TEXT NOT NULL DEFAULT 'LOCAL_SYSTEM',
        ADD COLUMN IF NOT EXISTS declared_slots_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
        ADD COLUMN IF NOT EXISTS author TEXT, ADD COLUMN IF NOT EXISTS description TEXT,
        ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS created_by_user_id UUID NULL,
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
    """,
    "UPDATE declarative_pack_bundles SET archive_sha256 = bundle_sha256 WHERE archive_sha256 IS NULL;",  # noqa: E501
    "ALTER TABLE declarative_pack_bundles ALTER COLUMN archive_sha256 SET NOT NULL;",
    """
    ALTER TABLE declarative_pack_bundles
        DROP CONSTRAINT IF EXISTS declarative_pack_bundles_slug_key,
        DROP CONSTRAINT IF EXISTS declarative_pack_bundles_pack_id_key,
        DROP CONSTRAINT IF EXISTS uq_pack_bundle_scope_slug_ver,
        DROP CONSTRAINT IF EXISTS ck_declarative_pack_bundles_bundle_kind,
        DROP CONSTRAINT IF EXISTS ck_declarative_pack_bundles_scope_type,
        DROP CONSTRAINT IF EXISTS ck_declarative_pack_bundles_source_origin,
        DROP CONSTRAINT IF EXISTS ck_declarative_pack_bundles_status,
        ADD CONSTRAINT ck_declarative_pack_bundles_bundle_kind
            CHECK (bundle_kind IN ('SYSTEM', 'ORG', 'IMPORTED', 'CUSTOM')),
        ADD CONSTRAINT ck_declarative_pack_bundles_scope_type
            CHECK (scope_type IN ('GLOBAL', 'BU', 'TEAM', 'WORKSPACE')),
        ADD CONSTRAINT ck_declarative_pack_bundles_source_origin
            CHECK (source_origin IN ('LOCAL_SYSTEM', 'APM_ZIP', 'APM_GIT', 'ORCIA_COMPOSER')),
        ADD CONSTRAINT ck_declarative_pack_bundles_status
            CHECK (status IN ('DRAFT', 'PUBLISHED', 'DEPRECATED')),
        ADD CONSTRAINT uq_pack_bundle_scope_slug_ver UNIQUE (scope_type, scope_id, slug, version);
    """,
    "CREATE INDEX IF NOT EXISTS idx_declarative_pack_bundles_pack_id ON declarative_pack_bundles (pack_id);",  # noqa: E501
)

_V2_TABLE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS pack_dna_mechanisms (
        id UUID PRIMARY KEY,
        pack_bundle_id UUID NOT NULL REFERENCES declarative_pack_bundles(id) ON DELETE CASCADE,
        mechanism_slug TEXT NOT NULL, name TEXT NOT NULL, starlark_source TEXT NOT NULL,
        source_sha256 CHAR(64) NOT NULL,
        input_schema_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        output_schema_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        passing_test_payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        failing_test_payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE (pack_bundle_id, mechanism_slug)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_pack_dna_mechanisms_bundle ON pack_dna_mechanisms (pack_bundle_id);",  # noqa: E501
    """
    CREATE TABLE IF NOT EXISTS pack_draft_memberships (
        id UUID PRIMARY KEY,
        draft_bundle_id UUID NOT NULL REFERENCES declarative_pack_bundles(id) ON DELETE CASCADE,
        entity_type TEXT NOT NULL CHECK (entity_type IN (
            'AGENT', 'SKILL', 'INSTRUCTION', 'WORKFLOW_V2', 'VSM_V2', 'ONTOLOGY_CONCEPT',
            'ONTOLOGY_RELATION', 'ONTOLOGY_AXIOM', 'DNA_MECHANISM', 'POLICY', 'HELP_ARTICLE'
        )),
        entity_id TEXT NOT NULL, entity_slug TEXT NOT NULL,
        catalog_item_id UUID NULL REFERENCES catalog_items(id) ON DELETE RESTRICT,
        workflow_v2_id UUID NULL REFERENCES workflow_definitions_v2(id) ON DELETE RESTRICT,
        vsm_v2_id UUID NULL REFERENCES vsm_definitions_v2(id) ON DELETE RESTRICT,
        ontology_concept_id UUID NULL REFERENCES ontology_concepts(id) ON DELETE RESTRICT,
        ontology_relation_id UUID NULL REFERENCES ontology_relations(id) ON DELETE RESTRICT,
        ontology_axiom_id UUID NULL REFERENCES ontology_axioms(id) ON DELETE RESTRICT,
        dna_mechanism_id UUID NULL REFERENCES pack_dna_mechanisms(id) ON DELETE RESTRICT,
        policy_id UUID NULL REFERENCES permission_broker_policies(id) ON DELETE RESTRICT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (draft_bundle_id, entity_type, entity_id),
        CONSTRAINT chk_pack_draft_membership_typed_fk CHECK (
            (entity_type IN ('AGENT', 'SKILL', 'INSTRUCTION', 'HELP_ARTICLE')
                AND catalog_item_id IS NOT NULL)
            OR (entity_type = 'WORKFLOW_V2' AND workflow_v2_id IS NOT NULL)
            OR (entity_type = 'VSM_V2' AND vsm_v2_id IS NOT NULL)
            OR (entity_type = 'ONTOLOGY_CONCEPT' AND ontology_concept_id IS NOT NULL)
            OR (entity_type = 'ONTOLOGY_RELATION' AND ontology_relation_id IS NOT NULL)
            OR (entity_type = 'ONTOLOGY_AXIOM' AND ontology_axiom_id IS NOT NULL)
            OR (entity_type = 'DNA_MECHANISM' AND dna_mechanism_id IS NOT NULL)
            OR (entity_type = 'POLICY' AND policy_id IS NOT NULL)
        )
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_pack_draft_memberships_draft ON pack_draft_memberships (draft_bundle_id);",  # noqa: E501
    """
    CREATE TABLE IF NOT EXISTS workspace_pack_activations (
        id UUID PRIMARY KEY,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        pack_bundle_id UUID NOT NULL REFERENCES declarative_pack_bundles(id) ON DELETE RESTRICT,
        pack_slug TEXT NOT NULL,
        priority_order INTEGER NULL CHECK (priority_order IS NULL OR priority_order >= 1),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        activated_by TEXT NOT NULL, activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (workspace_id, pack_slug),
        CONSTRAINT chk_workspace_pack_activation_active_priority CHECK (
            (is_active AND priority_order IS NOT NULL) OR (NOT is_active AND priority_order IS NULL)
        ),
        CONSTRAINT uq_workspace_pack_priority
            UNIQUE (workspace_id, priority_order) DEFERRABLE INITIALLY DEFERRED
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_workspace_pack_activations_ws ON workspace_pack_activations (workspace_id);",  # noqa: E501
    "CREATE INDEX IF NOT EXISTS ix_workspace_pack_activations_bundle ON workspace_pack_activations (pack_bundle_id);",  # noqa: E501
    """
    CREATE TABLE IF NOT EXISTS workspace_pack_slot_bindings (
        id UUID PRIMARY KEY,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        pack_bundle_id UUID NOT NULL REFERENCES declarative_pack_bundles(id) ON DELETE CASCADE,
        pack_slug TEXT NOT NULL, slot_key TEXT NOT NULL,
        target_kind TEXT NOT NULL DEFAULT 'UNBOUND' CHECK (target_kind IN (
            'UNBOUND', 'WORKSPACE_DATASOURCE', 'ENTERPRISE_CONNECTOR', 'INTERNAL'
        )),
        target_id TEXT NULL,
        bound_datasource_id UUID NULL REFERENCES workspace_datasources(id) ON DELETE SET NULL,
        bound_connector_id UUID NULL REFERENCES enterprise_connectors(id) ON DELETE SET NULL,
        connector_scheme TEXT NULL REFERENCES connector_schemes(scheme),
        bound_by TEXT NOT NULL, bound_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (workspace_id, pack_slug, slot_key)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_workspace_pack_slot_bindings_ws ON workspace_pack_slot_bindings (workspace_id);",  # noqa: E501
    """
    INSERT INTO connector_schemes (id, scheme, display_name, pack_name, is_active) VALUES (
        '0192c4e0-0000-7000-8000-00000000c008', 'pack',
        'Pack Déclaratif ORCIA (orcia://packs/)', 'core', TRUE
    ) ON CONFLICT (scheme) DO UPDATE SET display_name = EXCLUDED.display_name,
        pack_name = EXCLUDED.pack_name, is_active = EXCLUDED.is_active;
    """,
)

_DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TRIGGER IF EXISTS trg_workspace_pack_activations_scope_guard ON workspace_pack_activations;",  # noqa: E501
    "DROP FUNCTION IF EXISTS fn_enforce_workspace_pack_activation_scope();",
    "DELETE FROM connector_schemes WHERE scheme = 'pack';",
    "DROP TABLE IF EXISTS workspace_pack_slot_bindings;",
    "DROP TABLE IF EXISTS workspace_pack_activations;",
    "DROP TABLE IF EXISTS pack_draft_memberships;",
    "DROP TABLE IF EXISTS pack_dna_mechanisms;",
)


def upgrade() -> None:
    """Upgrade `declarative_pack_bundles` to v2, scope child constraints, and add v2 tables."""
    for stmt in _BUNDLE_UPGRADE_STATEMENTS:
        op.execute(sa.text(stmt))
    for tbl, uniq_specs in _CHILD_UNIQUE_SPECS:
        for stmt in (
            f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS pack_bundle_id UUID NULL "
            "REFERENCES declarative_pack_bundles(id) ON DELETE CASCADE;",
            f"CREATE INDEX IF NOT EXISTS ix_{tbl}_pack_bundle_id ON {tbl} (pack_bundle_id);",
            f"DO $$ DECLARE r RECORD; BEGIN FOR r IN ("
            f"SELECT conname FROM pg_constraint WHERE conrelid = 'public.{tbl}'::regclass "
            "AND contype = 'u') LOOP EXECUTE "
            f"'ALTER TABLE {tbl} DROP CONSTRAINT IF EXISTS ' || quote_ident(r.conname); "
            "END LOOP; END $$;",
        ):
            op.execute(sa.text(stmt))
        for suffix, cols, _old_name in uniq_specs:
            op.execute(
                sa.text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{tbl}_nonpack_{suffix} "
                    f"ON {tbl} ({cols}) WHERE pack_bundle_id IS NULL;"
                )
            )
            op.execute(
                sa.text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{tbl}_pack_{suffix} "
                    f"ON {tbl} (pack_bundle_id, {cols}) WHERE pack_bundle_id IS NOT NULL;"
                )
            )
    for stmt in (*_V2_TABLE_STATEMENTS, *_PACK_TRIGGER_STATEMENTS):
        op.execute(sa.text(stmt))


def downgrade() -> None:
    """Revert Story 31.1 v2 tables, trigger, scoped child indexes, and bundle extensions."""
    for stmt in _DOWNGRADE_STATEMENTS:
        op.execute(sa.text(stmt))
    for tbl, uniq_specs in reversed(_CHILD_UNIQUE_SPECS):
        for s, _c, _o in uniq_specs:
            op.execute(sa.text(f"DROP INDEX IF EXISTS uq_{tbl}_pack_{s};"))
            op.execute(sa.text(f"DROP INDEX IF EXISTS uq_{tbl}_nonpack_{s};"))
        add_uqs = ", ".join(f"ADD CONSTRAINT {o} UNIQUE ({c})" for _s, c, o in uniq_specs)
        for stmt in (
            f"DELETE FROM {tbl} WHERE pack_bundle_id IS NOT NULL;",
            f"DROP INDEX IF EXISTS ix_{tbl}_pack_bundle_id;",
            f"ALTER TABLE {tbl} DROP COLUMN IF EXISTS pack_bundle_id;",
            f"ALTER TABLE {tbl} {add_uqs};",
        ):
            op.execute(sa.text(stmt))
    for stmt in (
        "DELETE FROM declarative_pack_bundles "
        "WHERE bundle_kind <> 'SYSTEM' OR scope_type <> 'GLOBAL';",
        "DELETE FROM declarative_pack_bundles a USING declarative_pack_bundles b "
        "WHERE a.id < b.id AND (a.slug = b.slug OR a.pack_id = b.pack_id);",
        "DROP INDEX IF EXISTS idx_declarative_pack_bundles_pack_id;",
        "ALTER TABLE declarative_pack_bundles "
        "DROP CONSTRAINT IF EXISTS uq_pack_bundle_scope_slug_ver, "
        "DROP CONSTRAINT IF EXISTS ck_declarative_pack_bundles_status, "
        "DROP CONSTRAINT IF EXISTS ck_declarative_pack_bundles_source_origin, "
        "DROP CONSTRAINT IF EXISTS ck_declarative_pack_bundles_scope_type, "
        "DROP CONSTRAINT IF EXISTS ck_declarative_pack_bundles_bundle_kind, "
        "DROP COLUMN IF EXISTS updated_at, DROP COLUMN IF EXISTS created_by_user_id, "
        "DROP COLUMN IF EXISTS published_at, DROP COLUMN IF EXISTS description, "
        "DROP COLUMN IF EXISTS author, DROP COLUMN IF EXISTS declared_slots_jsonb, "
        "DROP COLUMN IF EXISTS source_origin, DROP COLUMN IF EXISTS status, "
        "DROP COLUMN IF EXISTS manifest_yaml, DROP COLUMN IF EXISTS cas_object_key, "
        "DROP COLUMN IF EXISTS archive_sha256, DROP COLUMN IF EXISTS scope_id, "
        "DROP COLUMN IF EXISTS scope_type, DROP COLUMN IF EXISTS bundle_kind, "
        "ADD CONSTRAINT declarative_pack_bundles_pack_id_key UNIQUE (pack_id), "
        "ADD CONSTRAINT declarative_pack_bundles_slug_key UNIQUE (slug);",
    ):
        op.execute(sa.text(stmt))
