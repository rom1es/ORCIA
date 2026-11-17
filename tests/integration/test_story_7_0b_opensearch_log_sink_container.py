"""Real OpenSearch 2.19.1 container integration test for `LogSinkQueryPort` (`Story 7.0b`)."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

import httpx
import pytest
from testcontainers.core.container import DockerContainer
from tests.conformance.log_sink_contract_kit import (
    LogSinkContractTestKit,
    build_contract_seed_entries,
)

from orcia_core.observability import ElasticsearchLogSinkAdapter

OPENSEARCH_IMAGE = "opensearchproject/opensearch:2.19.1"


def _wait_for_opensearch_ready(base_url: str, timeout_s: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"{base_url}/_cluster/health", timeout=2.0)
            if resp.status_code == 200 and resp.json().get("status") in ("green", "yellow"):
                return
        except httpx.HTTPError:
            pass
        time.sleep(1.5)
    raise TimeoutError(f"OpenSearch container did not become ready within {timeout_s}s")


@pytest.mark.integration
async def test_elasticsearch_log_sink_contract_against_real_opensearch_container() -> None:
    """Index real ECS JSON logs into `opensearch:2.19.1` and run `LogSinkContractTestKit`."""
    container = (
        DockerContainer(OPENSEARCH_IMAGE)
        .with_env("discovery.type", "single-node")
        .with_env("DISABLE_SECURITY_PLUGIN", "true")
        .with_env("OPENSEARCH_JAVA_OPTS", "-Xms256m -Xmx256m")
        .with_exposed_ports(9200)
    )
    with container as started:
        host = started.get_container_host_ip()
        port = started.get_exposed_port(9200)
        base_url = f"http://{host}:{port}"
        await asyncio.to_thread(_wait_for_opensearch_ready, base_url)

        now = datetime.now(UTC)
        entries, fp_db, fp_other = build_contract_seed_entries(now)
        index_name = "orcia-logs-2026.11.17"

        async with httpx.AsyncClient(timeout=10.0) as client:
            for idx, entry in enumerate(entries):
                doc = {
                    "timestamp": entry.timestamp,
                    "level": entry.level,
                    "service": entry.service,
                    "logger": entry.logger,
                    "message": entry.message,
                    "trace_id": entry.trace_id,
                    "span_id": entry.span_id,
                    "exception": entry.exception,
                    "workspace_id": entry.workspace_id,
                    "run_id": entry.run_id,
                    "ctx": dict(entry.ctx),
                }
                put_resp = await client.put(
                    f"{base_url}/{index_name}/_doc/{idx}",
                    json=doc,
                )
                assert put_resp.status_code in (200, 201), put_resp.text

            refresh_resp = await client.post(f"{base_url}/{index_name}/_refresh")
            assert refresh_resp.status_code == 200, refresh_resp.text

            adapter = ElasticsearchLogSinkAdapter(
                base_url,
                index_pattern="orcia-logs-*",
                http_client=client,
            )
            kit = LogSinkContractTestKit()
            await kit.run_all(adapter, fp_db=fp_db, fp_other=fp_other)
