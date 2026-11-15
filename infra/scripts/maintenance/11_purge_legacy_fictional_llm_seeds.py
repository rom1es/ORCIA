"""Maintenance script `11_purge_legacy_fictional_llm_seeds.py` (Story 19.4, Decision D4).

Purges legacy hardcoded seed models from `llm_model_endpoints` and `workspace_llm_tier_mappings`
in existing running databases, ensuring complete Day-0 neutrality without modifying past migrations.

Conventions (GEMINI.md):
- Operational data transformations live in `infra/scripts/maintenance/XX_*.py`.
- Mandatory `--dry-run` mode by default (rolls back unless `--apply` is explicitly passed).
- Uses batched idempotent transactions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_CORE_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-core" / "src")
_KERNEL_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-kernel" / "src")
for _src_path in (_KERNEL_SRC, _CORE_SRC):
    if _src_path not in sys.path:
        sys.path.insert(0, _src_path)

from orcia_core.config import resolve_database_url  # noqa: E402

LEGACY_FICTIONAL_ENDPOINT_KEYS: frozenset[str] = frozenset(
    {
        "llm-anthropic-claude-sonnet-4",
        "llm-openai-gpt-4-1",
        "llm-mistral-large-2",
    }
)

LEGACY_FICTIONAL_ENDPOINT_IDS: frozenset[str] = frozenset(
    {
        "0192c4e0-0000-7000-8000-000000001201",
        "0192c4e0-0000-7000-8000-000000001202",
        "0192c4e0-0000-7000-8000-000000001203",
    }
)

LEGACY_FICTIONAL_TIER_MAPPING_IDS: frozenset[str] = frozenset(
    {
        "0195f000-0000-7000-8000-000000008201",
        "0195f000-0000-7000-8000-000000008202",
        "0195f000-0000-7000-8000-000000008203",
    }
)

LEGACY_FICTIONAL_MODEL_NAMES: frozenset[str] = frozenset(
    {
        "claude-sonnet-4-20260514",
        "gpt-4.1-2026-04-14",
        "mistral-large-2511",
    }
)


@dataclass(frozen=True, slots=True)
class PurgeFictionalLlmSeedsReport:
    """Summary of the legacy fictional LLM seeds purge."""

    purged_endpoints_count: int
    purged_tier_mappings_count: int
    cleaned_setup_snapshots_count: int
    dry_run: bool
    committed: bool


async def purge_legacy_fictional_llm_seeds(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
) -> PurgeFictionalLlmSeedsReport:
    """Purge legacy seed models from `llm_model_endpoints` and `workspace_llm_tier_mappings`.

    Rolls back by default unless `apply_changes=True` is explicitly passed.
    """
    purged_endpoints = 0
    purged_mappings = 0
    cleaned_snapshots = 0

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            existing_rows = await conn.execute(
                sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            existing_tables = {str(r[0]) for r in existing_rows.fetchall()}

            # 1. Purge legacy endpoints
            if "llm_model_endpoints" in existing_tables:
                res = await conn.execute(
                    sa.text(
                        """
                        DELETE FROM llm_model_endpoints
                        WHERE endpoint_key = ANY(:keys)
                           OR id::text = ANY(:ids)
                           OR model_name = ANY(:model_names);
                        """
                    ),
                    {
                        "keys": list(LEGACY_FICTIONAL_ENDPOINT_KEYS),
                        "ids": list(LEGACY_FICTIONAL_ENDPOINT_IDS),
                        "model_names": list(LEGACY_FICTIONAL_MODEL_NAMES),
                    },
                )
                purged_endpoints = int(res.rowcount or 0)

            # 2. Purge legacy tier mappings
            if "workspace_llm_tier_mappings" in existing_tables:
                res = await conn.execute(
                    sa.text(
                        """
                        DELETE FROM workspace_llm_tier_mappings
                        WHERE id::text = ANY(:ids)
                           OR model_name = ANY(:model_names);
                        """
                    ),
                    {
                        "ids": list(LEGACY_FICTIONAL_TIER_MAPPING_IDS),
                        "model_names": list(LEGACY_FICTIONAL_MODEL_NAMES),
                    },
                )
                purged_mappings = int(res.rowcount or 0)

            # 3. Clean platform setup snapshots if they embed fictional seeds
            if "platform_settings" in existing_tables:
                settings_rows = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT id, value_jsonb
                            FROM platform_settings
                            WHERE category = 'iam' AND key = 'platform_setup_state';
                            """
                        )
                    )
                ).fetchall()

                for s_id, val in settings_rows:
                    if val is None:
                        continue
                    payload = json.loads(val) if isinstance(val, str) else dict(val)
                    tiers = list(payload.get("llm_tiers") or [])
                    filtered_tiers: list[dict[str, Any]] = []
                    modified = False
                    for t in tiers:
                        if isinstance(t, dict):
                            model = str(t.get("primaryModel") or t.get("model") or "").strip()
                            if model in LEGACY_FICTIONAL_MODEL_NAMES or not model:
                                modified = True
                                continue
                        filtered_tiers.append(t)
                    if modified:
                        payload["llm_tiers"] = filtered_tiers
                        await conn.execute(
                            sa.text(
                                """
                                UPDATE platform_settings
                                SET value_jsonb = CAST(:val AS jsonb),
                                    updated_at = NOW()
                                WHERE id = :id;
                                """
                            ),
                            {"id": s_id, "val": json.dumps(payload, ensure_ascii=False)},
                        )
                        cleaned_snapshots += 1

            if apply_changes:
                await trans.commit()
                committed = True
            else:
                await trans.rollback()
                committed = False
        except Exception:
            if trans.is_active:
                await trans.rollback()
            raise

    return PurgeFictionalLlmSeedsReport(
        purged_endpoints_count=purged_endpoints,
        purged_tier_mappings_count=purged_mappings,
        cleaned_setup_snapshots_count=cleaned_snapshots,
        dry_run=not apply_changes,
        committed=committed,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Purge legacy fictional LLM seeds from PostgreSQL 18."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Roll back transaction after counting legacy seeds (default).",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Commit deletion of legacy fictional LLM seeds.",
    )
    return parser.parse_args(argv)


async def _async_main() -> int:
    args = _parse_args()
    engine = create_async_engine(resolve_database_url())
    try:
        report = await purge_legacy_fictional_llm_seeds(engine, apply_changes=bool(args.apply))
        mode = "APPLY (COMMITTED)" if report.committed else "DRY-RUN (ROLLED BACK)"
        print(
            f"[11_purge_legacy_fictional_llm_seeds] {mode} — "
            f"purged_endpoints={report.purged_endpoints_count}, "
            f"purged_tier_mappings={report.purged_tier_mappings_count}, "
            f"cleaned_setup_snapshots={report.cleaned_setup_snapshots_count}"
        )
        return 0
    finally:
        await engine.dispose()


def main() -> None:
    sys.exit(asyncio.run(_async_main()))


if __name__ == "__main__":
    main()
