"""Unit tests for Story 19.5 Alembic migration (`AD-24.5`, `D5`, `D6`)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock


def test_alembic_migration_story_19_5_upgrade_downgrade() -> None:
    """Verify migration 20261115_2105 is valid, reversible, and executes expected DDL."""
    mig_path = Path(
        "infra/migrations/versions/20261115_2105_story_19_5_ai_models_usage_and_embedding_unique_idx.py"
    )
    spec = importlib.util.spec_from_file_location("mig_19_5", mig_path)
    assert spec is not None and spec.loader is not None
    mig_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig_mod)

    assert mig_mod.revision == "20261115_2105"
    assert mig_mod.down_revision == "20261115_1901"

    mock_op = MagicMock()
    mig_mod.op = mock_op

    # Test upgrade
    mig_mod.upgrade()
    assert mock_op.execute.call_count == 2
    upgrade_sql = " ".join(str(call[0][0]) for call in mock_op.execute.call_args_list)
    assert "usage VARCHAR(32)" in upgrade_sql
    assert "idx_llm_tier_mappings_single_active_global_embedding" in upgrade_sql

    mock_op.reset_mock()

    # Test downgrade
    mig_mod.downgrade()
    assert mock_op.execute.call_count == 2
    downgrade_sql = " ".join(str(call[0][0]) for call in mock_op.execute.call_args_list)
    assert (
        "DROP INDEX IF EXISTS idx_llm_tier_mappings_single_active_global_embedding" in downgrade_sql
    )
    assert "DROP COLUMN IF EXISTS usage" in downgrade_sql
