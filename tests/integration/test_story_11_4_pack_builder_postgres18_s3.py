"""Integration test for Story 11.4 against real PostgreSQL 18 + S3 container (`testcontainers`)."""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.postgres import PostgresContainer

from orcia_core.catalog import CasObjectEntry, S3CompatibleCasObjectStore
from orcia_core.orchestration.pack_builder_processes import (
    DnaChainPackSeedSpec,
    PackBuilderSystemService,
)

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
REPO_ROOT = Path(__file__).resolve().parents[2]

SAMPLE_STARLARK_RULE = """
def evaluate(ctx):
    data = orcia_sys.input("CheckPayload")
    orcia_sys.assert_rule(
        rule_id="NORM-OPS-01",
        condition=(data.get("slo_pct", 0) >= 99),
        message="SLO >= 99% requis.",
        evidence_ref="slo_pct"
    )
"""


class _ContainerBucketBackend:
    """S3BucketBackendProtocol persisting `cas/<sha256>` in the live S3 container `/data` volume."""

    def __init__(self, data_root: Path, container: DockerContainer) -> None:
        self._root = data_root
        self._container = container

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        _ = content_type
        target = self._root / bucket / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def get_bytes(self, bucket: str, key: str) -> bytes | None:
        target = self._root / bucket / key
        if not target.exists():
            return None
        exit_code, _out = self._container.exec(f"sh -c 'test -f /data/{bucket}/{key}'")
        assert exit_code == 0
        return target.read_bytes()

    def head_key(self, bucket: str, key: str) -> bool:
        exit_code, _out = self._container.exec(f"sh -c 'test -f /data/{bucket}/{key}'")
        return exit_code == 0


@pytest.mark.asyncio
async def test_story_11_4_pack_builder_persists_catalog_outbox_and_s3_cas() -> None:
    """Verify Process 1 persists `BUSINESS_PACK` in PG18 `catalog_items` + Outbox & S3 CAS."""
    s3_data_dir = (
        REPO_ROOT / ".pytest_cache" / "tc_s" / f"s3_11_4_{os.getpid()}_{int(time.time() * 1000)}"
    )
    s3_data_dir.mkdir(parents=True, exist_ok=True)
    s3_data_dir.chmod(0o777)

    try:
        with (
            PostgresContainer("pgvector/pgvector:pg18") as pg_container,
            DockerContainer("minio/minio:RELEASE.2025-02-28T09-55-16Z")
            .with_env("MINIO_ROOT_USER", "orcia_minio")
            .with_env("MINIO_ROOT_PASSWORD", "orcia_minio_secret")
            .with_volume_mapping(str(s3_data_dir), "/data", "rw")
            .with_command("server /data") as s3_container,
        ):
            wait_for_logs(s3_container, "API:", timeout=30)
            sync_url = pg_container.get_connection_url().replace(
                "postgresql+psycopg2://", "postgresql+psycopg://"
            )
            async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
            alembic_cfg = Config()
            alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

            engine = create_async_engine(async_url, pool_size=2, max_overflow=2)
            try:
                async with engine.begin() as conn:

                    def _upgrade(sync_conn: sa.Connection) -> None:
                        alembic_cfg.attributes["connection"] = sync_conn
                        command.upgrade(alembic_cfg, "head")

                    await conn.run_sync(_upgrade)

                session_factory = async_sessionmaker(engine, expire_on_commit=False)
                svc = PackBuilderSystemService(session_factory=session_factory)

                res = await svc.create_business_pack(
                    pack_slug="ops-sre",
                    title="Pack SRE & Résilience Opérationnelle",
                    version="1.0.0",
                    domain_name="OPS_SRE",
                    human_anchor_intent=(
                        "Assurer la résilience opérationnelle DORA et le respect des SLO critiques."
                    ),
                    dna_seeds=[
                        DnaChainPackSeedSpec(
                            directive_code="DIR-DORA-01",
                            directive_title="Résilience opérationnelle numérique DORA",
                            norm_code="NORM-OPS-01",
                            norm_title="SLO de disponibilité >= 99%",
                            mechanism_code="MECH-OPS-SLO",
                            rule_id="NORM-OPS-01",
                            starlark_source=SAMPLE_STARLARK_RULE,
                            passing_test_payload={"slo_pct": 99.9},
                            failing_test_payload={"slo_pct": 95.0},
                        )
                    ],
                    human_profiles=["SRE Lead"],
                    agents=["@SRE-Postmortem"],
                    workflows=["ops/postmortem-review"],
                    actor_id="karim-sre",
                )

                # Store generated pack.yaml in S3 CAS container
                backend = _ContainerBucketBackend(s3_data_dir, s3_container)
                cas_store = S3CompatibleCasObjectStore(backend, bucket_name="orcia-cas")
                pack_yaml_bytes = res.generated_files[f"{res.target_directory}/pack.yaml"].encode(
                    "utf-8"
                )
                digest = hashlib.sha256(pack_yaml_bytes).hexdigest()
                cas_key = f"cas/{digest}"
                cas_store.put_object(
                    CasObjectEntry(
                        sha256=digest,
                        cas_key=cas_key,
                        content_bytes=pack_yaml_bytes,
                        content_type="application/yaml",
                    )
                )
                assert cas_store.has_object(cas_key) is True

                async with session_factory() as session:
                    cat_row = (
                        await session.execute(
                            sa.text(
                                """
                                SELECT item_type, visibility_scope, version
                                FROM catalog_items
                                WHERE resource_id = 'pack-ops-sre'
                                """
                            )
                        )
                    ).one()
                    assert cat_row.item_type == "BUSINESS_PACK"
                    assert cat_row.visibility_scope == "PUBLISHED_ORG"
                    assert cat_row.version == "1.0.0"

                    outbox_count = (
                        await session.execute(
                            sa.text(
                                """
                                SELECT COUNT(*) FROM domain_events_outbox
                                WHERE aggregate_type = 'BusinessPack'
                                  AND aggregate_id = :pack_id
                                """
                            ),
                            {"pack_id": res.pack_id},
                        )
                    ).scalar_one()
                    assert int(outbox_count) == 1
            finally:
                await engine.dispose()
    finally:
        shutil.rmtree(s3_data_dir, ignore_errors=True)
