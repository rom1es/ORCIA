"""Branch-coverage edge unit tests for Story 31.3 parser, loaders & pack SQL helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import pytest

from orcia_core.domain.namespacing import (
    format_agent_mention,
    format_skill_command,
    parse_qualified_entity_ref,
)
from orcia_core.kernel.errors import ValidationDomainError
from orcia_core.orchestration._agents_namespacing import (
    infer_record_pack_slug_and_tier,
    resolve_agent_reference,
)
from orcia_core.orchestration._internal._sql_agents_pack_queries import (
    ensure_root_org_unit_id,
    load_workspace_pack_priorities_pg,
    optional_uuid,
    resolve_pack_tier_for_row,
)
from orcia_core.packs._internal._sql_pack_flat_loaders import (
    decode_json_dict,
    load_flat_broker_policies,
    load_flat_dna_mechanisms,
    load_flat_pack_instructions,
    tier_rank,
)
from orcia_core.packs.namespacing import (
    WorkspaceEntityCandidate,
    resolve_workspace_entity_candidates,
)


class _FakeResult:
    def __init__(self, *, scalar: Any = None, rows: Sequence[tuple[Any, ...]] = ()) -> None:
        self._scalar = scalar
        self._rows = list(rows)

    def scalar(self) -> Any:
        return self._scalar

    def scalar_one(self) -> Any:
        return self._scalar

    def first(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


class _FakeConn:
    def __init__(self, responses: list[_FakeResult]) -> None:
        self._responses = list(responses)

    async def execute(self, stmt: Any, params: Any = None) -> _FakeResult:
        _ = stmt, params
        return self._responses.pop(0)


def test_parser_and_formatter_edge_branches() -> None:
    ws_uri = parse_qualified_entity_ref("orcia://workspaces/ws-1/skills/lint@1.0.0")
    assert (
        ws_uri.pack_slug,
        ws_uri.entity_slug,
        ws_uri.version_ref,
        ws_uri.is_workspace_scope,
    ) == (
        "workspace",
        "lint",
        "1.0.0",
        True,
    )
    pk_uri = parse_qualified_entity_ref("pack://sdlc/agents/reviewer:2.0")
    assert (pk_uri.pack_slug, pk_uri.entity_slug, pk_uri.version_ref) == ("sdlc", "reviewer", "2.0")

    ag_colon = parse_qualified_entity_ref("sdlc:@reviewer")
    sk_colon = parse_qualified_entity_ref("sdlc:/check")
    assert ag_colon.kind == "agents" and sk_colon.kind == "skills"

    for bad in ("ftp://host/a/b", "orcia://onlyone"):
        with pytest.raises(ValidationDomainError):
            parse_qualified_entity_ref(bad)

    assert format_agent_mention("rev", workspace_scoped=True) == "@workspace/rev"
    assert format_agent_mention("rev") == "@rev"
    assert format_skill_command("chk", workspace_scoped=True) == "/workspace/chk"
    assert format_skill_command("chk") == "/chk"

    c_sk = WorkspaceEntityCandidate("sdlc:chk", "chk", "sdlc", "WORKSPACE_PACK", 1)
    c_wf = WorkspaceEntityCandidate("sdlc:flow", "flow", "sdlc", "WORKSPACE_PACK", 1)
    assert (
        resolve_workspace_entity_candidates("sdlc:chk", [c_sk], default_kind="skills").qualified_ref
        == "/sdlc/chk"
    )
    assert (
        resolve_workspace_entity_candidates(
            "sdlc:flow", [c_wf], default_kind="workflows"
        ).qualified_ref
        == "orcia://packs/sdlc/workflows/flow"
    )


def test_agents_namespacing_inference_fallbacks() -> None:
    assert infer_record_pack_slug_and_tier(
        entity_id="a1",
        slug="a1",
        uri="orcia://packs/fin/agents/a1",
        visibility_scope="PACK",
        source_pack_key=None,
    ) == ("fin", "WORKSPACE_PACK")
    assert infer_record_pack_slug_and_tier(
        entity_id="legal:rev",
        slug="rev",
        uri="orcia://x",
        visibility_scope="PACK",
        source_pack_key=None,
        bundle_kind="SYSTEM",
    ) == ("legal", "SYSTEM_PACK")
    assert infer_record_pack_slug_and_tier(
        entity_id="rev",
        slug="rev",
        uri="orcia://x",
        visibility_scope="PACK",
        source_pack_key="orcia-pack-hr",
    ) == ("hr", "WORKSPACE_PACK")
    assert infer_record_pack_slug_and_tier(
        entity_id="ws-rev",
        slug="rev",
        uri="orcia://ws/rev",
        visibility_scope="WORKSPACE",
        source_pack_key=None,
    ) == (None, "WORKSPACE_OVERRIDE")
    assert resolve_agent_reference([], "   ") is None
    assert resolve_agent_reference([], "@missing") is None


@pytest.mark.asyncio
async def test_flat_pack_loaders_and_sql_queries_branches() -> None:
    assert decode_json_dict({"a": 1}) == {"a": 1}
    assert decode_json_dict('{"b": 2}') == {"b": 2}
    assert decode_json_dict("{bad") == {}
    assert decode_json_dict(123) == {}

    assert tier_rank(None, None, {}) == ((0, 0), "WORKSPACE_OVERRIDE")
    assert tier_rank("b1", "IMPORTED", {"b1": 2}) == ((1, 2), "WORKSPACE_PACK")
    assert tier_rank("b2", "SYSTEM", {}) == ((2, 0), "SYSTEM_PACK")
    assert tier_rank("b3", "IMPORTED", {}) is None

    c_empty = _FakeConn([_FakeResult(scalar=None), _FakeResult(scalar=None)])
    assert await load_flat_dna_mechanisms(c_empty, {}) == ()  # type: ignore[arg-type]
    assert await load_flat_broker_policies(c_empty, {}) == ()  # type: ignore[arg-type]

    c_data = _FakeConn(
        [
            _FakeResult(scalar="pack_dna_mechanisms"),
            _FakeResult(
                rows=[
                    ("m1", "Mech 1", "def eval(): pass", "abc", "b1", "sdlc", "IMPORTED"),
                    ("m2", "Ignored", "def eval(): pass", "def", "b_off", "off", "IMPORTED"),
                ]
            ),
            _FakeResult(scalar="permission_broker_policies"),
            _FakeResult(
                rows=[
                    ("sdlc:p1", "mcp://gate", "mcp", "ADMIN", "SEC", 12, "b1", "sdlc", "IMPORTED"),
                    ("off:p2", "mcp://off", "mcp", "ADMIN", "SEC", 12, "b_off", "off", "IMPORTED"),
                ]
            ),
            _FakeResult(
                rows=[
                    (
                        "ws:i1",
                        "orcia://ws/i1",
                        "rule",
                        '{"slug":"rule","body_markdown":"WS"}',
                        "ws1",
                        None,
                        None,
                        None,
                    ),
                    ("other:i", "orcia://ws/other", "rule", "{}", "ws2", None, None, None),
                    (
                        "off:i",
                        "orcia://packs/off/i",
                        "rule",
                        "{}",
                        None,
                        "b_off",
                        "off",
                        "IMPORTED",
                    ),
                    (
                        "sdlc:i1",
                        "orcia://packs/sdlc/i1",
                        "rule",
                        '{"slug":"rule","body_markdown":"SDLC"}',
                        None,
                        "b1",
                        "sdlc",
                        "IMPORTED",
                    ),
                ]
            ),
        ]
    )
    mechs = await load_flat_dna_mechanisms(c_data, {"b1": 1})  # type: ignore[arg-type]
    pols = await load_flat_broker_policies(c_data, {"b1": 1})  # type: ignore[arg-type]
    insts = await load_flat_pack_instructions(c_data, "ws1", {"b1": 1})  # type: ignore[arg-type]
    assert mechs[0]["pack_slug"] == "sdlc" and len(mechs) == 1
    assert pols[0]["policy_slug"] == "p1" and len(pols) == 1
    assert insts[0]["body_markdown"] == "WS" and len(insts) == 1

    assert await load_workspace_pack_priorities_pg(_FakeConn([]), "") == ({}, set())  # type: ignore[arg-type]
    assert await load_workspace_pack_priorities_pg(
        _FakeConn([_FakeResult(scalar=None)]), "ws1"
    ) == ({}, set())  # type: ignore[arg-type]
    c_prio = _FakeConn(
        [_FakeResult(scalar="wpa"), _FakeResult(rows=[("sdlc", 1, True), ("off", 2, False)])]
    )
    assert await load_workspace_pack_priorities_pg(c_prio, "ws1") == ({"sdlc": 1}, {"off"})  # type: ignore[arg-type]

    assert resolve_pack_tier_for_row(pack_slug=None, bundle_kind=None, active_priorities={}) is None
    assert (
        resolve_pack_tier_for_row(
            pack_slug="sdlc", bundle_kind="IMPORTED", active_priorities={"sdlc": 1}
        )
        == "WORKSPACE_PACK"
    )
    assert (
        resolve_pack_tier_for_row(pack_slug="sys", bundle_kind="SYSTEM", active_priorities={})
        == "SYSTEM_PACK"
    )
    assert (
        resolve_pack_tier_for_row(pack_slug="other", bundle_kind="IMPORTED", active_priorities={})
        == "WORKSPACE_PACK"
    )

    uid = "0195f000-0000-7000-8000-000000000001"
    assert (
        optional_uuid(None) is None
        and optional_uuid("bad") is None
        and optional_uuid(uid) == UUID(uid)
    )
    assert await ensure_root_org_unit_id(_FakeConn([_FakeResult(rows=[(uid,)])])) == UUID(uid)  # type: ignore[arg-type]
    assert await ensure_root_org_unit_id(
        _FakeConn([_FakeResult(rows=[]), _FakeResult(scalar=uid)])
    ) == UUID(uid)  # type: ignore[arg-type]
