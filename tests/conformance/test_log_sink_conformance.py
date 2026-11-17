"""Conformance tests for `LogSinkQueryPort` (Fake & Elasticsearch/OpenSearch adapters)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from tests.conformance.log_sink_contract_kit import (
    LogSinkContractTestKit,
    build_contract_seed_entries,
)
from tests.unit.fakes.fake_log_sink import FakeInMemoryLogSinkAdapter

from orcia_core.observability import ElasticsearchLogSinkAdapter
from orcia_core.ports.log_sink import NoopLogSinkAdapter


def _match_es_filter(doc: dict[str, Any], clause: dict[str, Any]) -> bool:
    """Evaluate minimal OpenSearch/Elasticsearch Query DSL clauses against an ECS doc."""
    if "bool" in clause:
        b = clause["bool"]
        if b.get("filter") and not all(_match_es_filter(doc, c) for c in b["filter"]):
            return False
        if b.get("must") and not all(_match_es_filter(doc, c) for c in b["must"]):
            return False
        if b.get("should"):
            min_match = int(b.get("minimum_should_match", 1))
            hits = sum(1 for c in b["should"] if _match_es_filter(doc, c))
            if hits < min_match:
                return False
        return True
    if "term" in clause:
        field, expected = next(iter(clause["term"].items()))
        val = doc.get(field.removesuffix(".keyword"))
        if field.startswith("ctx."):
            val = doc.get("ctx", {}).get(field.removeprefix("ctx.").removesuffix(".keyword"))
        if isinstance(expected, dict):
            expected = expected.get("value")
        return str(val or "").lower() == str(expected).lower()
    if "terms" in clause:
        field, expected_list = next(iter(clause["terms"].items()))
        val = str(doc.get(field.removesuffix(".keyword")) or "").lower()
        return val in [str(x).lower() for x in expected_list]
    if "match_phrase" in clause:
        field, expected = next(iter(clause["match_phrase"].items()))
        if isinstance(expected, dict):
            expected = expected.get("query", "")
        if field.startswith("ctx."):
            val = str(doc.get("ctx", {}).get(field.removeprefix("ctx.")) or "")
        else:
            val = str(doc.get(field) or "")
        return str(expected).lower() in val.lower()
    if "multi_match" in clause:
        q = str(clause["multi_match"].get("query", "")).lower()
        fields = clause["multi_match"].get("fields", [])
        return any(q in str(doc.get(f) or "").lower() for f in fields)
    if "range" in clause:
        field, bounds = next(iter(clause["range"].items()))
        raw = doc.get(field)
        if not raw:
            return False
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        gte = bounds.get("gte")
        if gte:
            cutoff = datetime.fromisoformat(str(gte).replace("Z", "+00:00"))
            return dt >= cutoff
        return True
    return True


def _build_mock_opensearch_transport(docs: list[dict[str, Any]]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/_cluster/health":
            return httpx.Response(200, json={"cluster_name": "orcia-test", "status": "green"})
        body = json.loads(request.content.decode("utf-8")) if request.content else {}
        query_clause = body.get("query", {"match_all": {}})
        matched = [
            d
            for d in docs
            if query_clause == {"match_all": {}} or _match_es_filter(d, query_clause)
        ]
        matched.sort(key=lambda d: str(d.get("timestamp", "")), reverse=True)
        if request.url.path.endswith("/_count"):
            return httpx.Response(200, json={"count": len(matched)})
        if request.url.path.endswith("/_search"):
            size = int(body.get("size", 50))
            hits = [{"_id": str(i), "_source": doc} for i, doc in enumerate(matched[:size])]
            return httpx.Response(
                200, json={"hits": {"total": {"value": len(matched)}, "hits": hits}}
            )
        return httpx.Response(404, json={"error": "not_found"})

    return httpx.MockTransport(handler)


async def test_log_sink_contract_kit_passes_for_in_memory_fake_and_elasticsearch_adapter() -> None:
    """Verify `LogSinkContractTestKit` passes identically for Fake and Elasticsearch adapters."""
    now = datetime.now(UTC)
    entries, fp_db, fp_other = build_contract_seed_entries(now)
    kit = LogSinkContractTestKit()

    # 1. In-memory fake
    fake = FakeInMemoryLogSinkAdapter(entries, clock_now=now)
    await kit.run_all(fake, fp_db=fp_db, fp_other=fp_other)

    # 2. Elasticsearch/OpenSearch REST JSON adapter
    es_docs = [
        {
            "timestamp": e.timestamp,
            "level": e.level,
            "service": e.service,
            "logger": e.logger,
            "message": e.message,
            "trace_id": e.trace_id,
            "span_id": e.span_id,
            "exception": e.exception,
            "workspace_id": e.workspace_id,
            "run_id": e.run_id,
            "ctx": dict(e.ctx),
        }
        for e in entries
    ]
    transport = _build_mock_opensearch_transport(es_docs)
    async with httpx.AsyncClient(transport=transport) as client:
        es_adapter = ElasticsearchLogSinkAdapter(
            "http://opensearch.orcia.local:9200",
            index_pattern="orcia-logs-*",
            http_client=client,
        )
        await kit.run_all(es_adapter, fp_db=fp_db, fp_other=fp_other)

    # 3. NoopLogSinkAdapter contract smoke
    noop = NoopLogSinkAdapter()
    assert await noop.healthcheck() is True
    assert await noop.count_errors(fp_db, 300) == 0
    assert (
        await noop.query_logs(
            __import__("orcia_core.ports.log_sink", fromlist=["LogQuery"]).LogQuery()
        )
        == []
    )
    assert timedelta(seconds=1) > timedelta(0)
