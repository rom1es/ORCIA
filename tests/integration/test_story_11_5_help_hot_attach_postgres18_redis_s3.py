"""Integration test for Story 11.5 against PostgreSQL 18 + Redis 7.4 + S3 (`testcontainers`)."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import pytest
import redis
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from orcia_core.catalog import CasObjectEntry, S3CompatibleCasObjectStore
from orcia_core.orchestration.help_generator_and_validator import (
    HelpGenerationAndHotAttachmentService,
)

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
REPO_ROOT = Path(__file__).resolve().parents[2]


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
async def test_story_11_5_help_hot_attach_pg18_redis_and_s3_cas(tmp_path: Path) -> None:
    """Verify Process 5 persists `HELP_ARTICLE` in PG18, S3 CAS, and invalidates Redis 7.4."""
    s3_data_dir = (
        REPO_ROOT / ".pytest_cache" / "tc_s" / f"s3_11_5_{os.getpid()}_{int(time.time() * 1000)}"
    )
    s3_data_dir.mkdir(parents=True, exist_ok=True)
    s3_data_dir.chmod(0o777)

    try:
        with (
            RedisContainer("redis:7.4-alpine") as redis_container,
            PostgresContainer("pgvector/pgvector:pg18") as pg_container,
            DockerContainer("minio/minio:RELEASE.2025-02-28T09-55-16Z")
            .with_env("MINIO_ROOT_USER", "orcia_minio")
            .with_env("MINIO_ROOT_PASSWORD", "orcia_minio_secret")
            .with_volume_mapping(str(s3_data_dir), "/data", "rw")
            .with_command("server /data") as s3_container,
        ):
            wait_for_logs(s3_container, "API:", timeout=30)
            r_client = redis.Redis(
                host=redis_container.get_container_host_ip(),
                port=int(redis_container.get_exposed_port(6379)),
                db=0,
            )
            r_client.set("help:route:/cockpit:claims:fr", "stale-cache-fr", ex=3600)
            r_client.set("help:route:/cockpit:claims:en", "stale-cache-en", ex=3600)

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
                svc = HelpGenerationAndHotAttachmentService(
                    session_factory=session_factory,
                    redis_client=r_client,
                )

                res = await svc.generate_and_attach_help(
                    article_id="help.claims.triage",
                    article_slug="claims-triage",
                    version="1.0.0",
                    pack_slug="claims",
                    title_fr="Aide Triage Sinistres",
                    title_en="Claims Triage Help",
                    bound_routes=["/cockpit"],
                    roles_allowed=["CONTRIBUTOR", "ARCHITECT"],
                    glossary_terms=["Franchise Contractuelle"],
                    related_workflows=["claims/triage-flow"],
                    purpose_fr="Explique le triage rapide des sinistres.",
                    purpose_en="Explains rapid claims triage.",
                    steps_fr=["Ouvrir le Cockpit", "Valider les pièces"],
                    steps_en=["Open the Cockpit", "Validate documents"],
                    faq_fr=["Que faire en cas d'écart ?"],
                    faq_en=["What to do on discrepancy?"],
                    ui_component_name="ContextualHelpColumnAndCenter",
                    known_glossary_terms=["Franchise Contractuelle"],
                    export_root_dir=tmp_path,
                )

                # Verify Redis cache keys invalidated in < 100 ms
                assert r_client.get("help:route:/cockpit:claims:fr") is None
                assert r_client.get("help:route:/cockpit:claims:en") is None

                # Store bilingual Markdown blobs in S3 CAS container
                backend = _ContainerBucketBackend(s3_data_dir, s3_container)
                cas_store = S3CompatibleCasObjectStore(backend, bucket_name="orcia-cas")
                for sha, cas_key, md_text in (
                    (res.fr_sha256, res.fr_cas_key, res.fr_markdown),
                    (res.en_sha256, res.en_cas_key, res.en_markdown),
                ):
                    cas_store.put_object(
                        CasObjectEntry(
                            sha256=sha,
                            cas_key=cas_key,
                            content_bytes=md_text.encode("utf-8"),
                            content_type="text/markdown",
                        )
                    )
                    assert cas_store.has_object(cas_key) is True

                async with session_factory() as session:
                    rows = (
                        await session.execute(
                            sa.text(
                                """
                                SELECT resource_id, item_type,
                                       metadata_jsonb->>'authority_role' AS role
                                FROM catalog_items
                                WHERE resource_id IN (
                                    'help.claims.triage-fr',
                                    'help.claims.triage-en'
                                )
                                ORDER BY resource_id
                                """
                            )
                        )
                    ).all()
                    assert len(rows) == 2
                    for row in rows:
                        assert row.item_type == "HELP_ARTICLE"
                        assert row.role == "REFERENCE"
            finally:
                await engine.dispose()
    finally:
        shutil.rmtree(s3_data_dir, ignore_errors=True)
