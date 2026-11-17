"""Priority OpenSearch 2.x / Elasticsearch 8.x `LogSinkQueryPort` adapter (`AD-23`, `Story 7.0b`).

Uses standard REST JSON endpoints (`/_search`, `/_count`, `/_cluster/health`) over
`httpx.AsyncClient` without proprietary vendor client SDK lock-in.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from orcia_core.kernel.log_sink_ports import MAX_LOG_QUERY_LIMIT, LogEntry, LogQuery
from orcia_core.kernel.secret_ports import SecretProviderPort, SecretRef
from orcia_core.observability._internal.ecs_formatter import register_sensitive_secret_value
from orcia_core.observability._internal.url_guard import validate_safe_log_sink_url
from orcia_core.observability.errors import LogSinkQueryFailedError
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.observability.log_sink")

_SAFE_INDEX_PATTERN_RE = re.compile(r"^[a-zA-Z0-9_.*,-]+$")


def _validate_index_pattern(index_pattern: str) -> str:
    cleaned = (index_pattern or "").strip()
    if not cleaned or ".." in cleaned or not _SAFE_INDEX_PATTERN_RE.match(cleaned):
        raise ValueError(f"Invalid OpenSearch/Elasticsearch index pattern: {index_pattern!r}")
    return cleaned


def _keyword_or_phrase_clause(field: str, value: str) -> dict[str, Any]:
    return {
        "bool": {
            "should": [
                {"term": {f"{field}.keyword": value}},
                {"match_phrase": {field: value}},
            ],
            "minimum_should_match": 1,
        }
    }


def _hit_to_log_entry(source: dict[str, Any]) -> LogEntry:
    raw_ctx = source.get("ctx")
    ctx_dict: dict[str, Any] = dict(raw_ctx) if isinstance(raw_ctx, dict) else {}
    fp = source.get("fingerprint") or ctx_dict.get("error_fingerprint_sha256")
    return LogEntry(
        timestamp=str(source.get("timestamp") or source.get("@timestamp") or ""),
        level=str(source.get("level") or "info").lower(),
        service=str(source.get("service") or "unknown"),
        logger=str(source.get("logger") or "orcia"),
        message=str(source.get("message") or ""),
        trace_id=str(source["trace_id"]) if source.get("trace_id") is not None else None,
        span_id=str(source["span_id"]) if source.get("span_id") is not None else None,
        exception=str(source["exception"]) if source.get("exception") is not None else None,
        fingerprint=str(fp) if fp is not None else None,
        ctx=ctx_dict,
        workspace_id=(
            str(source["workspace_id"])
            if source.get("workspace_id") is not None
            else (
                str(ctx_dict["workspace_id"]) if ctx_dict.get("workspace_id") is not None else None
            )
        ),
        run_id=(
            str(source["run_id"])
            if source.get("run_id") is not None
            else (str(ctx_dict["run_id"]) if ctx_dict.get("run_id") is not None else None)
        ),
    )


class ElasticsearchLogSinkAdapter:
    """OpenSearch 2.x & Elasticsearch 8.x compatible `LogSinkQueryPort` via REST JSON."""

    def __init__(
        self,
        base_url: str,
        *,
        index_pattern: str = "orcia-logs-*",
        http_client: httpx.AsyncClient | None = None,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
        secret_provider: SecretProviderPort | None = None,
        auth_secret_ref: SecretRef | None = None,
        api_key_header: str = "Authorization",
        api_key_prefix: str = "ApiKey ",
        timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = validate_safe_log_sink_url(base_url)
        self._index_pattern = _validate_index_pattern(index_pattern)
        self._http_client = http_client
        self._client_factory = client_factory
        self._secret_provider = secret_provider
        self._auth_secret_ref = auth_secret_ref
        self._api_key_header = api_key_header
        self._api_key_prefix = api_key_prefix
        self._timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 3.0))

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._auth_secret_ref is not None and self._secret_provider is not None:
            resolved = self._secret_provider.resolve_secret(self._auth_secret_ref)
            if resolved:
                register_sensitive_secret_value(resolved)
                headers[self._api_key_header] = f"{self._api_key_prefix}{resolved}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        headers = self._build_headers()
        if self._http_client is not None:
            return await self._http_client.request(
                method, url, json=json_body, headers=headers, timeout=self._timeout
            )
        if self._client_factory is not None:
            async with self._client_factory() as client:
                return await client.request(
                    method, url, json=json_body, headers=headers, timeout=self._timeout
                )
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await client.request(method, url, json=json_body, headers=headers)

    @staticmethod
    def _build_filters(query: LogQuery) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = []
        if query.service:
            filters.append(_keyword_or_phrase_clause("service", query.service))
        if query.level:
            lvl_low = query.level.strip().lower()
            lvl_up = lvl_low.upper()
            filters.append(
                {
                    "bool": {
                        "should": [
                            {"term": {"level.keyword": lvl_low}},
                            {"term": {"level.keyword": lvl_up}},
                            {"match_phrase": {"level": lvl_low}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        if query.workspace_id:
            filters.append(
                {
                    "bool": {
                        "should": [
                            _keyword_or_phrase_clause("workspace_id", query.workspace_id)["bool"][
                                "should"
                            ][0],
                            _keyword_or_phrase_clause("workspace_id", query.workspace_id)["bool"][
                                "should"
                            ][1],
                            _keyword_or_phrase_clause("ctx.workspace_id", query.workspace_id)[
                                "bool"
                            ]["should"][0],
                            _keyword_or_phrase_clause("ctx.workspace_id", query.workspace_id)[
                                "bool"
                            ]["should"][1],
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        if query.run_id:
            filters.append(
                {
                    "bool": {
                        "should": [
                            _keyword_or_phrase_clause("run_id", query.run_id)["bool"]["should"][0],
                            _keyword_or_phrase_clause("run_id", query.run_id)["bool"]["should"][1],
                            _keyword_or_phrase_clause("ctx.run_id", query.run_id)["bool"]["should"][
                                0
                            ],
                            _keyword_or_phrase_clause("ctx.run_id", query.run_id)["bool"]["should"][
                                1
                            ],
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        if query.fingerprint:
            filters.append(
                {
                    "bool": {
                        "should": [
                            {"term": {"ctx.error_fingerprint_sha256.keyword": query.fingerprint}},
                            {"term": {"fingerprint.keyword": query.fingerprint}},
                            {"match_phrase": {"ctx.error_fingerprint_sha256": query.fingerprint}},
                            {"match_phrase": {"fingerprint": query.fingerprint}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        if query.search_text:
            filters.append(
                {
                    "multi_match": {
                        "query": query.search_text,
                        "fields": ["message", "exception"],
                        "type": "phrase",
                    }
                }
            )
        if query.since_seconds is not None:
            cutoff_iso = (
                (datetime.now(UTC) - timedelta(seconds=query.since_seconds))
                .isoformat()
                .replace("+00:00", "Z")
            )
            filters.append(
                {
                    "bool": {
                        "should": [
                            {"range": {"timestamp": {"gte": cutoff_iso}}},
                            {"range": {"@timestamp": {"gte": cutoff_iso}}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        return filters

    async def query_logs(self, query: LogQuery) -> list[LogEntry]:
        filters = self._build_filters(query)
        size = max(1, min(query.limit, MAX_LOG_QUERY_LIMIT))
        body: dict[str, Any] = {
            "size": size,
            "sort": [
                {"timestamp": {"order": "desc", "unmapped_type": "date"}},
                {"@timestamp": {"order": "desc", "unmapped_type": "date"}},
            ],
            "query": {"bool": {"filter": filters}} if filters else {"match_all": {}},
        }
        try:
            resp = await self._request("POST", f"/{self._index_pattern}/_search", json_body=body)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.warning(
                "log_sink_query_failed",
                operation="query_logs",
                index_pattern=self._index_pattern,
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            raise LogSinkQueryFailedError(
                detail_override=f"Log sink search failed ({type(exc).__name__})."
            ) from exc

        hits = payload.get("hits", {}).get("hits", [])
        return [
            _hit_to_log_entry(hit.get("_source", {}))
            for hit in hits
            if isinstance(hit, dict) and isinstance(hit.get("_source"), dict)
        ]

    async def count_errors(
        self,
        fingerprint: str,
        window_seconds: int,
        *,
        service: str | None = None,
    ) -> int:
        if window_seconds < 0:
            raise ValueError("window_seconds must be >= 0")
        base_filters = self._build_filters(
            LogQuery(
                service=service,
                fingerprint=fingerprint,
                since_seconds=window_seconds,
            )
        )
        level_filter: dict[str, Any] = {
            "bool": {
                "should": [
                    {"term": {"level.keyword": "error"}},
                    {"term": {"level.keyword": "ERROR"}},
                    {"term": {"level.keyword": "critical"}},
                    {"term": {"level.keyword": "CRITICAL"}},
                    {"match_phrase": {"level": "error"}},
                    {"match_phrase": {"level": "critical"}},
                ],
                "minimum_should_match": 1,
            }
        }
        body: dict[str, Any] = {
            "query": {"bool": {"filter": [*base_filters, level_filter]}},
        }
        try:
            resp = await self._request("POST", f"/{self._index_pattern}/_count", json_body=body)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.warning(
                "log_sink_query_failed",
                operation="count_errors",
                index_pattern=self._index_pattern,
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            raise LogSinkQueryFailedError(
                detail_override=f"Log sink count failed ({type(exc).__name__})."
            ) from exc

        return int(payload.get("count", 0))

    async def healthcheck(self) -> bool:
        try:
            resp = await self._request("GET", "/_cluster/health")
            if resp.status_code != 200:
                logger.warning(
                    "log_sink_healthcheck_failed",
                    status_code=resp.status_code,
                    index_pattern=self._index_pattern,
                )
                return False
            status = str(resp.json().get("status", "")).lower()
            return status in ("green", "yellow")
        except Exception as exc:
            logger.warning(
                "log_sink_healthcheck_failed",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            return False


__all__ = ["ElasticsearchLogSinkAdapter"]
