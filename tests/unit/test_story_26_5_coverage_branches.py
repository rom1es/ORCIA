"""Targeted branch-coverage unit tests for Story 26.5 modules (no DB network calls)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from orcia_core.blackboard._internal.sql_blackboard_queries import (
    _parse_json_dict,
    _parse_json_list,
    list_active_workspace_blackboard_snapshots_pg,
)
from orcia_core.ontology.context_ranker import (
    _compute_lexical_score,
    _cosine_similarity,
    build_websearch_or_query,
    format_ranked_ontology_summary,
    rank_ontology_snapshot_for_query,
)
from orcia_core.ontology.models import (
    OntologyAxiomEntity,
    OntologyConceptEntity,
    ResolvedOntologySnapshot,
)
from orcia_core.orchestration._internal.sql_assistant_thread_messages import (
    SqlAssistantThreadMessagesRepository,
    _decode_citation_map,
)
from orcia_core.orchestration.assistant_citations_models import (
    EvidenceSourceCitation,
    EvidenceTable,
)
from orcia_core.orchestration.assistant_context_budget import (
    estimate_text_tokens,
    trim_messages_to_token_budget,
)
from orcia_core.orchestration.assistant_evidence_table import (
    build_server_evidence_table_for_turn,
    evidence_table_to_citation_map_dict,
    format_evidence_table_for_layer_4,
)
from orcia_core.rag._context_adapters_helpers import (
    build_blackboard_slices,
    build_catalog_slices,
    build_kb_document_slices,
    build_permission_slices,
    to_vector_hits,
)
from orcia_core.rag.models import HybridRagHit
from orcia_kernel.context_ports import ContextSliceRecord, VectorSearchHitRecord


class _FakeResult:
    def __init__(
        self,
        *,
        scalar_val: Any = None,
        first_row: Any = None,
        one_row: dict[str, Any] | None = None,
        all_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self._scalar = scalar_val
        self._first = first_row
        self._one = one_row
        self._all = all_rows or []

    def scalar(self) -> Any:
        return self._scalar

    def first(self) -> Any:
        return self._first

    def mappings(self) -> _FakeResult:
        return self

    def one(self) -> Any:
        res = self._one if self._one is not None else self._first
        assert res is not None
        return res

    def all(self) -> list[dict[str, Any]]:
        return self._all


class _FakeAsyncConn:
    def __init__(self, handler: Any) -> None:
        self._handler = handler

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        return self._handler(str(stmt), params or {})


class _FakeAsyncEngine:
    def __init__(self, handler: Any) -> None:
        self._handler = handler

    @asynccontextmanager
    async def connect(self) -> Any:
        yield _FakeAsyncConn(self._handler)

    @asynccontextmanager
    async def begin(self) -> Any:
        yield _FakeAsyncConn(self._handler)


def test_context_ranker_edge_branches() -> None:
    assert _cosine_similarity([], [1.0]) == 0.0
    assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert build_websearch_or_query("the and for with") == "the and for with"

    c1 = OntologyConceptEntity(
        id="c1",
        concept_key="c_stop",
        level="1_ENTERPRISE",
        scope_id="scope-global",
        canonical_term="the",
        definition_text="the and",
        synonyms=("for", "alpha"),
        banned_terms=("forbidden_alias",),
    )
    assert _compute_lexical_score(c1, "") == 0.0
    assert _compute_lexical_score(c1, "forbidden_alias") >= 2.0

    snap = ResolvedOntologySnapshot(
        workspace_id="ws-1",
        run_id=None,
        resolution_chain_scopes=("scope-global",),
        concepts_by_term={"the": c1},
        relations=(),
        axioms=(
            OntologyAxiomEntity(
                id="ax1",
                axiom_key="AX_1",
                concept_key="c_stop",
                level="1_ENTERPRISE",
                scope_id="scope-global",
                rule_expression="Rule 1",
                immutable=True,
            ),
        ),
    )
    ranked = rank_ontology_snapshot_for_query(
        snap,
        query_text="forbidden_alias",
        active_hat="ADMIN",
        query_embedding=[1.0, 0.0],
        concept_embeddings={"other": [1.0, 0.0]},
    )
    assert len(ranked.selected_concepts) == 1
    assert len(ranked.applicable_axioms) == 1
    c_dicts, ax_dicts, summary = format_ranked_ontology_summary(ranked)
    assert len(c_dicts) == 1 and len(ax_dicts) == 1 and summary is not None


def test_context_budget_truncation_and_empty_branches() -> None:
    assert estimate_text_tokens("") == 0
    long_sys = "L1: Mandatory Enterprise Guard. " + ("detail " * 200)
    res = trim_messages_to_token_budget(
        system_msg=long_sys,
        user_prompt="Hello",
        conversation_history=None,
        max_tokens_budget=128,
        reserve_output_tokens=16,
    )
    assert res.context_truncated is True
    assert "[CONTEXT_BUDGET_TRIMMED]" in res.messages[0]["content"]
    assert res.dropped_history_count == 0


def test_evidence_table_branches_and_serialization() -> None:
    empty_table = EvidenceTable(
        sources=(), glossary_items=(), tool_outputs=(), footer_summary_line=""
    )
    assert format_evidence_table_for_layer_4(empty_table) == ""

    restricted_table = EvidenceTable(
        sources=(
            EvidenceSourceCitation(
                tag="[S1]",
                index=1,
                uri="orcia://restricted",
                title="Secret",
                authority_tier="ACTIVE",
                freshness="FRESH",
                line_start=None,
                line_end=None,
                restricted_access=True,
                snippet=None,
            ),
        ),
        glossary_items=(),
        tool_outputs=(),
        footer_summary_line="",
    )
    assert format_evidence_table_for_layer_4(restricted_table) == ""

    vec_hit = VectorSearchHitRecord(
        chunk_key="ck-1",
        document_key="doc-v1",
        source_uri="orcia://catalog/item-1",
        contextual_header="ctx",
        injected_content="snippet body",
        rrf_score=0.4,
        is_stale=True,
        stale_warning_marker="[STALE_WARNING]",
    )
    hit_dup_low = HybridRagHit(
        chunk_key="ck-2",
        parent_chunk_key="ck-2",
        document_key="doc-v2",
        datasource_alias="ds",
        source_uri="orcia://catalog/item-1",
        revision_tag="v1",
        contextual_header="ctx",
        injected_content="ignored lower",
        is_stale=False,
        vector_rank=1,
        bm25_rank=2,
        rrf_score=0.1,
    )
    empty_uri_hit = VectorSearchHitRecord(
        chunk_key="ck-0",
        document_key="",
        source_uri="",
        contextual_header="",
        injected_content="",
        rrf_score=0.5,
    )
    stale_slice = ContextSliceRecord(
        slice_id="sl-1",
        source_uri="orcia://kb/stale-doc",
        source_kind="KB_DOCUMENT",
        content_sha256="sha256:1",
        title="Stale Slice",
        structured_payload={"authority_tier": "ACTIVE"},
        text_excerpt="Outdated content",
        is_stale=True,
    )
    denied_slice = ContextSliceRecord(
        slice_id="sl-denied",
        source_uri="orcia://kb/denied-doc",
        source_kind="KB_DOCUMENT",
        content_sha256="sha256:2",
        title="Denied Slice",
        structured_payload={},
        text_excerpt="Denied content",
    )
    concept = OntologyConceptEntity(
        id="c1",
        concept_key="c_sla",
        level="3_WORKSPACE",
        scope_id="ws-1",
        canonical_term="SLA",
        definition_text="48h SLA",
    )
    axiom = OntologyAxiomEntity(
        id="a1",
        axiom_key="AX_SLA",
        concept_key="c_sla",
        level="3_WORKSPACE",
        scope_id="ws-1",
        rule_expression="SLA <= 48h",
        immutable=False,
    )
    from orcia_core.ontology.context_ranker import RankedOntologyConcept

    res = build_server_evidence_table_for_turn(
        rag_hits=(empty_uri_hit, vec_hit, hit_dup_low),
        context_slices=(stale_slice, denied_slice),
        ontology_concepts=(
            RankedOntologyConcept(concept=concept, translated_label="SLA", relevance_score=2.0),
        ),
        ontology_axioms=(axiom,),
        allowed_source_uris=frozenset({"orcia://catalog/item-1", "orcia://kb/stale-doc"}),
        locale="en",
    )
    assert res.masked_count == 1
    assert "[STALE_WARNING]" in res.layer4_markdown
    assert "[G" in res.layer4_markdown
    cmap = evidence_table_to_citation_map_dict(res.evidence_table)
    assert len(cmap["sources"]) == 2
    assert len(cmap["glossary_items"]) == 2


def test_rag_context_adapters_helpers_branches() -> None:
    @dataclass
    class _Doc:
        doc_key: str
        source_uri: str
        title: str
        content_sha256: str
        indexing_regime: str
        revision_tag: str
        datasource_alias: str
        is_stale: bool
        age_days: int
        freshness_ttl_days: int

    docs = [
        _Doc("d1", "orcia://kb/a", "Alpha", "sha1", "HYBRID", "v1", "ds", True, 40, 30),
        _Doc("d2", "orcia://kb/b", "Beta", "sha2", "HYBRID", "v1", "ds", False, 1, 30),
        _Doc("d3", "orcia://kb/skip", "Zeta", "sha3", "HYBRID", "v1", "ds", False, 1, 30),
    ]
    kb_slices = build_kb_document_slices(
        docs, query_terms=["alpha"], uri_filter={"orcia://kb/a", "orcia://kb/b"}, current_count=4
    )
    assert len(kb_slices) == 1 and kb_slices[0].is_stale is True

    @dataclass
    class _CatObj:
        canonical_uri: str
        display_name: str
        sha256: str
        item_kind: str

    cat_slices = build_catalog_slices(
        [
            {"uri": "orcia://catalog/one", "title": "One"},
            {"uri": ""},
            _CatObj("orcia://catalog/two", "Two", "sha2", "AGENT"),
        ],
        uri_filter={"orcia://catalog/one", "orcia://catalog/two"},
    )
    assert len(cat_slices) == 2

    @dataclass
    class _Snap:
        id: str
        step_key: str
        artifact_sha256: str
        artifact_payload: dict[str, Any]

    bb = build_blackboard_slices(
        [_Snap("s1", "plan", "snap_sha_alpha", {"ok": True}), _Snap("s2", "other", "fff111", {})],
        workspace_id="ws-1",
        uri_filter={"orcia://blackboard/ws-1/plan@snap_sha_alp"},
    )
    assert len(bb) == 1

    @dataclass
    class _Pol:
        policy_key: str
        uri_pattern: str
        required_role: str

    perms = build_permission_slices(
        [_Pol("p1", "orcia://*", "MEMBER"), _Pol("p2", "orcia://x", "ADMIN")],
        uri_filter={"orcia://permissions/policies/p1"},
    )
    assert len(perms) == 1
    assert to_vector_hits(()) == ()


@pytest.mark.asyncio
async def test_sql_blackboard_and_thread_messages_unit_branches() -> None:
    assert _parse_json_dict({"a": 1}) == {"a": 1}
    assert _parse_json_dict('{"b": 2}') == {"b": 2}
    assert _parse_json_dict("[1]") == {}
    assert _parse_json_list([1, 2]) == [1, 2]
    assert _parse_json_list('["x"]') == ["x"]
    assert _parse_json_list('{"a": 1}') == []

    assert _decode_citation_map({"sources": []}) == {"sources": []}
    assert _decode_citation_map('{"sources": [1]}') == {"sources": [1]}
    assert _decode_citation_map("[1]") == {}

    ws_id = str(uuid4())
    active_id = str(uuid4())
    sup_id = str(uuid4())

    def _bb_handler(sql: str, params: dict[str, Any]) -> _FakeResult:
        if "SELECT to_regclass('public.workspaces')" in sql:
            return _FakeResult(scalar_val="workspaces")
        if "SELECT id::text FROM workspaces" in sql:
            return _FakeResult(first_row=(ws_id,))
        if "SELECT to_regclass" in sql:
            return _FakeResult(scalar_val="ok", first_row=("ok", "ok"))
        return _FakeResult(
            all_rows=[
                {
                    "id": sup_id,
                    "snapshot_key": "k0",
                    "run_id": str(uuid4()),
                    "step_execution_id": str(uuid4()),
                    "parent_snapshot_id": None,
                    "step_key": "step0",
                    "branch_status": "SUPERSEDED",
                    "artifact_payload_jsonb": "{}",
                    "artifact_cas_key": "cas0",
                    "artifact_sha256": "sha0",
                    "memlog_summary_jsonb": "[]",
                    "superseded_snapshot_ids_jsonb": "[]",
                },
                {
                    "id": active_id,
                    "snapshot_key": "k1",
                    "run_id": str(uuid4()),
                    "step_execution_id": str(uuid4()),
                    "parent_snapshot_id": sup_id,
                    "step_key": "step1",
                    "branch_status": "ACTIVE",
                    "artifact_payload_jsonb": '{"summary": "ready"}',
                    "artifact_cas_key": "cas1",
                    "artifact_sha256": "sha1  ",
                    "memlog_summary_jsonb": '[{"entry_id": "e1", "summary": "ok"}]',
                    "superseded_snapshot_ids_jsonb": f'["{sup_id}"]',
                },
            ]
        )

    bb_none = await list_active_workspace_blackboard_snapshots_pg(
        _FakeAsyncEngine(_bb_handler),  # type: ignore[arg-type]
        workspace_id="",
    )
    assert bb_none == ()
    snaps = await list_active_workspace_blackboard_snapshots_pg(
        _FakeAsyncEngine(_bb_handler),
        workspace_id="ws-slug",
        limit=1,  # type: ignore[arg-type]
    )
    assert len(snaps) == 1 and snaps[0].id == active_id

    no_tbl_engine = _FakeAsyncEngine(
        lambda _sql, _p: _FakeResult(scalar_val=None, first_row=(None, None))
    )
    assert (
        await list_active_workspace_blackboard_snapshots_pg(
            no_tbl_engine,  # type: ignore[arg-type]
            workspace_id="missing",
        )
        == ()
    )
    assert (
        await list_active_workspace_blackboard_snapshots_pg(
            no_tbl_engine,  # type: ignore[arg-type]
            workspace_id=ws_id,
        )
        == ()
    )

    row_payload = {
        "id": str(uuid4()),
        "thread_id": str(uuid4()),
        "workspace_id": ws_id,
        "turn_id": str(uuid4()),
        "parent_turn_id": None,
        "role": "user",
        "content": "Hello",
        "citation_map": '{"sources": []}',
        "token_count": 2,
        "created_at": datetime.now(UTC),
    }

    def _msg_handler(sql: str, params: dict[str, Any]) -> _FakeResult:
        if "SELECT to_regclass" in sql:
            return _FakeResult(scalar_val="assistant_thread_messages")
        if "SELECT id FROM workspaces" in sql:
            return _FakeResult(first_row=(ws_id,))
        if "INSERT INTO assistant_thread_messages" in sql:
            return _FakeResult(one_row=row_payload)
        return _FakeResult(all_rows=[row_payload])

    repo = SqlAssistantThreadMessagesRepository()
    assert await repo.pg_tables_ready() is False
    fallback_rec = await repo.append_message(
        thread_id=str(uuid4()), workspace_id=ws_id, turn_id=str(uuid4()), role="user", content="Hi"
    )
    assert fallback_rec.content == "Hi"
    assert await repo.list_messages_for_thread(workspace_id=ws_id, thread_id=str(uuid4())) == ()

    repo.set_engine(_FakeAsyncEngine(_msg_handler))  # type: ignore[arg-type]
    assert await repo.pg_tables_ready() is True
    assert await repo.pg_tables_ready() is True
    saved = await repo.append_message(
        thread_id=row_payload["thread_id"],
        workspace_id=ws_id,
        turn_id=row_payload["turn_id"],
        role="user",
        content="Hello",
    )
    assert saved.content == "Hello"
    listed = await repo.list_messages_for_thread(
        workspace_id=ws_id, thread_id=row_payload["thread_id"]
    )
    assert len(listed) == 1 and listed[0].citation_map == {"sources": []}
