"""Story 20.4 — Unit tests for `user_profile_service.py` & `_assistant_usage_telemetry.py`."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import httpx
import pytest

from orcia_api.routers._assistant_usage_telemetry import (
    estimate_tokens_deterministic,
    extract_usage_tokens_from_payload,
    persist_assistant_turn_ledger_entry,
    resolve_audit_ledger_sink,
    resolve_usage_with_fallback,
)
from orcia_api.routers.assistant_llm_providers import (
    ResolvedLiveLlmEndpoint,
    build_provider_request_body,
    invoke_provider_chat_async,
    stream_provider_chat_sse_async,
)
from orcia_core.audit_finops.user_profile_service import (
    PopularUsageItem,
    compute_activity_streaks,
    derive_user_handle,
    empty_user_profile_summary,
    rank_popular_usage_items,
)
from orcia_core.ports.finops_telemetry import FinopsCostLedgerEntry


class _FakeLedgerSink:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.entries: list[FinopsCostLedgerEntry] = []
        self.should_fail = should_fail

    async def record_entry(self, entry: FinopsCostLedgerEntry) -> str:
        if self.should_fail:
            raise RuntimeError("ledger write boom")
        self.entries.append(entry)
        return entry.source_event_id


def test_compute_activity_streaks_handles_empty_gaps_and_yesterday_active() -> None:
    assert compute_activity_streaks([], today=date(2026, 11, 18)) == (0, 0)

    # Streak ending today (3 days) vs older 5-day streak
    dates = [
        date(2026, 11, 1),
        date(2026, 11, 2),
        date(2026, 11, 3),
        date(2026, 11, 4),
        date(2026, 11, 5),
        date(2026, 11, 16),
        date(2026, 11, 17),
        date(2026, 11, 18),
        date(2026, 11, 18),  # duplicate date ignored
    ]
    assert compute_activity_streaks(dates, today=date(2026, 11, 18)) == (5, 3)

    # Active yesterday (today not yet active) keeps current streak alive
    assert compute_activity_streaks(
        [date(2026, 11, 16), date(2026, 11, 17)], today=date(2026, 11, 18)
    ) == (2, 2)

    # Gap of >= 2 days breaks current streak
    assert compute_activity_streaks(
        [date(2026, 11, 14), date(2026, 11, 15)], today=date(2026, 11, 18)
    ) == (2, 0)


def test_derive_user_handle_empty_summary_and_popular_ranking() -> None:
    assert derive_user_handle("Alice.Martin@orcia.ia", "Alice Martin") == "alice.martin"
    assert derive_user_handle("", "Jean Dupont!") == "jean.dupont"
    assert derive_user_handle("", "!!!") == "user"

    summary = empty_user_profile_summary(
        user_id="u-1", user_email="bob@orcia.ia", display_name="Bob", roles=[]
    )
    assert summary.primary_role == "CONTRIBUTOR"
    assert summary.total_tokens == 0
    assert summary.popular_items == ()

    ranked = rank_popular_usage_items(
        [
            PopularUsageItem("AGENT", "a1", "Agent 1", 2, "/agents"),
            PopularUsageItem("AGENT", "a1", "Agent 1", 3, "/agents"),
            PopularUsageItem("PROCESS", "p1", "Process 1", 4, "/processes"),
            PopularUsageItem("TOOL", "t0", "Zero", 0, "/agents"),
            PopularUsageItem("SKILL", "s1", "Skill 1", 6, "/agents"),
            PopularUsageItem("TOOL", "t1", "Tool 1", 1, "/agents"),
            PopularUsageItem("TOOL", "t2", "Tool 2", 7, "/agents"),
            PopularUsageItem("TOOL", "t3", "Tool 3", 8, "/agents"),
        ],
        limit=5,
    )
    assert [r.item_key for r in ranked] == ["t3", "t2", "s1", "a1", "p1"]
    assert ranked[3].usage_count == 5


def test_usage_extraction_all_providers_and_deterministic_fallback() -> None:
    assert extract_usage_tokens_from_payload({"usage": {"prompt_tokens": 12, "completion_tokens": 34}}) == (12, 34)  # fmt: skip  # noqa: E501
    assert extract_usage_tokens_from_payload({"usage": {"input_tokens": 20, "output_tokens": 40}}) == (20, 40)  # fmt: skip  # noqa: E501
    assert extract_usage_tokens_from_payload({"message": {"usage": {"input_tokens": 15}}}) == (15, 0)  # fmt: skip  # noqa: E501
    assert extract_usage_tokens_from_payload({"usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 25, "thoughtsTokenCount": 5}}) == (10, 30)  # fmt: skip  # noqa: E501
    assert extract_usage_tokens_from_payload({"usageMetadata": {"promptTokenCount": 10, "totalTokenCount": 22}}) == (10, 12)  # fmt: skip  # noqa: E501
    assert extract_usage_tokens_from_payload({"prompt_eval_count": 7, "eval_count": 9}) == (7, 9)
    assert extract_usage_tokens_from_payload({"usage": {}}) is None
    assert extract_usage_tokens_from_payload({"message": {"usage": {}}}) is None
    assert extract_usage_tokens_from_payload({"usageMetadata": {"promptTokenCount": 0}}) is None
    assert extract_usage_tokens_from_payload({"choices": []}) is None

    assert estimate_tokens_deterministic("abcdefgh", "1234") == (2, 1)
    assert resolve_usage_with_fallback(
        prompt_text="x" * 40,
        reply_text="y" * 20,
        observed_input_tokens=11,
        observed_output_tokens=22,
        saw_provider_usage=True,
    ) == (11, 22, "provider")
    assert resolve_usage_with_fallback(
        prompt_text="x" * 40, reply_text="y" * 20, saw_provider_usage=False
    ) == (10, 5, "estimated")


@pytest.mark.asyncio
async def test_streaming_includes_stream_options_and_persists_or_falls_back() -> None:
    ep = ResolvedLiveLlmEndpoint(
        provider="OpenAI",
        model_name="gpt-oss-120b",
        endpoint_uri="https://llm.internal/v1",
        auth_mode="bearer",
        tier="medium",
    )
    body_stream = build_provider_request_body(
        ep=ep,
        target_url="https://llm.internal/v1/chat/completions",
        messages=[{"role": "user", "content": "Hello"}],
        stream=True,
    )
    assert body_stream["stream_options"] == {"include_usage": True}

    captured_requests: list[dict[str, Any]] = []
    sse_with_usage = (
        'data: {"choices": [{"delta": {"content": "Bonjour "}}]}\n\n'
        'data: {"choices": [{"delta": {"content": "ORCIA"}}]}\n\n'
        'data: {"choices": [], "usage": {"prompt_tokens": 42, "completion_tokens": 18}}\n\n'
        "data: [DONE]\n\n"
    )

    def _stream_handler(req: httpx.Request) -> httpx.Response:
        captured_requests.append(json.loads(req.content.decode("utf-8")))
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse_with_usage.encode("utf-8"),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_stream_handler)) as client:
        events = [
            e
            async for e in stream_provider_chat_sse_async(
                client, ep=ep, messages=[{"role": "user", "content": "Hello"}]
            )
        ]
    assert captured_requests[0]["stream_options"] == {"include_usage": True}
    completed = events[-1]
    assert completed["event"] == "turn_completed"
    assert completed["data"]["input_tokens"] == 42
    assert completed["data"]["output_tokens"] == 18
    assert completed["data"]["usage_source"] == "provider"

    # Non-stream without usage falls back deterministically
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"choices": [{"message": {"content": "Reply text 123456"}}]}
            )
        )
    ) as client2:
        ns = await invoke_provider_chat_async(
            client2, ep=ep, messages=[{"role": "user", "content": "Prompt 12345678"}]
        )
    assert ns is not None
    assert ns.usage_source == "estimated"
    assert ns.input_tokens >= 1 and ns.output_tokens >= 1


@pytest.mark.asyncio
async def test_persist_assistant_turn_ledger_entry_and_sink_resolution() -> None:
    from types import SimpleNamespace

    assert resolve_audit_ledger_sink(None) is None
    req_empty = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    assert resolve_audit_ledger_sink(req_empty) is None

    sink = _FakeLedgerSink()
    req_with_sink = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(audit_ledger_service=sink))
    )
    assert resolve_audit_ledger_sink(req_with_sink) is sink

    req_with_engine = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(audit_ledger_service=None, db_engine=object()))
    )
    assert resolve_audit_ledger_sink(req_with_engine) is not None

    # Empty workspace_id and missing sink/user_id short-circuit cleanly
    assert (
        await persist_assistant_turn_ledger_entry(
            audit_ledger_sink=None,
            user_id="usr-alice",
            user_email="alice@orcia.ia",
            user_display_name="Alice",
            workspace_id="",
            turn_id="turn-0",
            model_id="m-1",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
        )
        is None
    )
    assert (
        await persist_assistant_turn_ledger_entry(
            audit_ledger_sink=sink,
            user_id="usr-alice",
            user_email="alice@orcia.ia",
            user_display_name="Alice",
            workspace_id="",
            turn_id="turn-empty-ws",
            model_id="m-1",
            input_tokens=5,
            output_tokens=6,
            latency_ms=10.0,
        )
        is not None
    )
    entry_id = await persist_assistant_turn_ledger_entry(
        audit_ledger_sink=sink,
        user_id="usr-alice",
        user_email="alice@orcia.ia",
        user_display_name="Alice",
        workspace_id="ws-claims-alpha",
        turn_id="turn-abc",
        model_id="m-1",
        input_tokens=120,
        output_tokens=45,
        latency_ms=210.4,
        usage_source="provider",
        invoked_targets=("rag-search",),
    )
    assert entry_id is not None
    assert len(sink.entries) == 2
    e = sink.entries[1]
    assert e.event_type == "ASSISTANT_TURN_COMPLETED"
    assert e.actor_id == "usr-alice"
    assert e.actor_email == "alice@orcia.ia"
    assert e.workspace_id is None  # non-UUID slug safely stored in metadata
    assert e.metadata["workspace_slug"] == "ws-claims-alpha"
    assert e.metadata["usage_source"] == "provider"
    assert e.metadata["tool_name"] == "rag-search"

    # Failing ledger sink never crashes assistant turn
    failing_sink = _FakeLedgerSink(should_fail=True)
    assert (
        await persist_assistant_turn_ledger_entry(
            audit_ledger_sink=failing_sink,
            user_id="usr-alice",
            user_email="alice@orcia.ia",
            user_display_name="Alice",
            workspace_id="0195f000-0000-7000-8000-000000000001",
            turn_id="turn-err",
            model_id="m-1",
            input_tokens=10,
            output_tokens=5,
            latency_ms=50.0,
        )
        is None
    )


@pytest.mark.asyncio
async def test_load_user_identity_and_orgs_supports_tribe_unit_type() -> None:
    from orcia_core.audit_finops._internal._sql_user_profile_orgs import (
        load_user_identity_and_orgs,
    )

    class _FakeRes:
        def __init__(self, rows):  # type: ignore[no-untyped-def]
            self._rows = rows

        def fetchone(self):  # type: ignore[no-untyped-def]
            return self._rows[0] if self._rows else None

        def fetchall(self):  # type: ignore[no-untyped-def]
            return self._rows

    class _FakeConn:
        async def execute(self, stmt, _params=None):  # type: ignore[no-untyped-def]
            sql = str(stmt)
            if "FROM iam_accounts" in sql:
                return _FakeRes([("alice@orcia.ia", "Alice", "alice@orcia.ia", '["BU_LEAD"]')])
            if "FROM org_units" in sql:
                return _FakeRes(
                    [
                        (
                            "Tribu Paiements",
                            "TRIBE",
                            "alice@orcia.ia",
                            '["alice@orcia.ia"]',
                            '["alice@orcia.ia"]',
                            "[]",
                        ),
                        ("Équipe Core", "TEAM", None, "[]", "[]", '["alice@orcia.ia"]'),
                    ]
                )
            return _FakeRes([])

    _, _, _, led_bus, onto_bus, _, member_teams = await load_user_identity_and_orgs(
        _FakeConn(),  # type: ignore[arg-type]
        user_id="alice@orcia.ia",
        user_email="alice@orcia.ia",
        display_name="Alice",
        roles=("BU_LEAD",),
    )
    assert led_bus == ("Tribu Paiements",)
    assert onto_bus == ("Tribu Paiements",)
    assert member_teams == ("Équipe Core",)


@pytest.mark.asyncio
async def test_user_profile_sql_helpers_date_json_coercion_and_resilience() -> None:
    from datetime import UTC, date, datetime

    from orcia_core.audit_finops._internal._sql_user_profile_orgs import _parse_json_str_list
    from orcia_core.audit_finops._internal.sql_user_profile_stats import (
        _coerce_utc_date,
        _load_user_popular_items,
        _load_user_token_stats_and_dates,
    )

    assert _coerce_utc_date(datetime(2026, 11, 18, 12, 30, tzinfo=UTC)) == date(2026, 11, 18)
    assert _coerce_utc_date(date(2026, 11, 17)) == date(2026, 11, 17)
    assert _coerce_utc_date("2026-11-16T00:00:00Z") == date(2026, 11, 16)
    assert _coerce_utc_date("not-a-date") is None
    assert _coerce_utc_date(12345) is None

    assert _parse_json_str_list(["  a ", "", "b"]) == ["a", "b"]
    assert _parse_json_str_list('["x", "y"]') == ["x", "y"]
    assert _parse_json_str_list("{bad-json") == []
    assert _parse_json_str_list('{"k": "v"}') == []
    assert _parse_json_str_list(None) == []

    class _FakeRows:
        def __init__(self, rows: list[tuple[Any, ...]]) -> None:
            self._rows = rows

        def fetchall(self) -> list[tuple[Any, ...]]:
            return self._rows

    class _MixedConn:
        def __init__(self, *, fail: bool) -> None:
            self._fail = fail
            self.calls = 0

        async def execute(self, *_args: Any, **_kwargs: Any) -> _FakeRows:
            self.calls += 1
            if self._fail:
                raise RuntimeError("transient connection error")
            if self.calls == 1:
                return _FakeRows([(None, 42), ("2026-11-18", 10)])
            return _FakeRows([(None,), ("2026-11-17",)])

    total, peak, dates = await _load_user_token_stats_and_dates(
        _MixedConn(fail=False),  # type: ignore[arg-type]
        user_id="u-1",
        user_email="u1@orcia.ia",
    )
    assert (total, peak) == (52, 42)
    assert dates == [date(2026, 11, 18), date(2026, 11, 17)]

    # Non-missing-table errors are logged and degrade gracefully to zeros / empty tuple
    assert await _load_user_token_stats_and_dates(
        _MixedConn(fail=True),  # type: ignore[arg-type]
        user_id="u-1",
        user_email="u1@orcia.ia",
    ) == (0, 0, [])
    assert (
        await _load_user_popular_items(
            _MixedConn(fail=True),  # type: ignore[arg-type]
            user_id="u-1",
            user_email="u1@orcia.ia",
        )
        == ()
    )
