"""Story 26.5 — Unit tests for Ontology Ranking, EvidenceTable, Budget Trimmer & History."""

from __future__ import annotations

import pytest

from orcia_core.ontology import (
    OntologyAxiomEntity,
    OntologyConceptEntity,
    OntologyGovernanceService,
    ProfileSemanticTranslator,
)
from orcia_core.ontology.context_ranker import (
    format_ranked_ontology_summary,
    rank_ontology_snapshot_for_query,
    rank_ontology_with_optional_embedding_async,
)
from orcia_core.orchestration.assistant_context_budget import trim_messages_to_token_budget
from orcia_core.orchestration.assistant_evidence_table import build_server_evidence_table_for_turn
from orcia_core.orchestration.assistant_prompt_locales import CONSTITUTIONAL_LAYER_1_TEXT_EN
from orcia_core.rag.models import HybridRagHit
from orcia_kernel.context_ports import ContextSliceRecord


class _StubEmbeddingPort:
    dimension = 1024

    async def embed(self, texts: list[str] | tuple[str, ...]) -> list[list[float]]:
        out: list[list[float]] = []
        for txt in texts:
            low = txt.lower()
            if "settlement" in low or "ledger" in low or "paiement" in low:
                out.append([1.0, 0.0] + [0.0] * 1022)
            else:
                out.append([0.0, 1.0] + [0.0] * 1022)
        return out

    async def embed_texts(self, texts: list[str] | tuple[str, ...]) -> list[list[float]]:
        return await self.embed(texts)

    async def embed_query(self, query: str) -> list[float]:
        return (await self.embed([query]))[0]


def _build_test_ontology() -> OntologyGovernanceService:
    ws_id = "0195f000-0000-7000-8000-000000000301"
    c1 = OntologyConceptEntity(
        id="0195f000-0000-7000-8000-000000002101",
        concept_key="concept-l1-payment-ledger",
        canonical_term="Payment Ledger",
        level="1_ENTERPRISE",
        scope_id="scope-global",
        definition_text="Append-only financial settlement ledger for capture events.",
        synonyms=("Settlement Journal", "Grand Livre"),
        profile_translations={
            "EXECUTIVE": "Payment Ledger (DORA Audit & Settlement SLA)",
            "ARCHITECT": "Event-Sourced Payment Ledger (PG18 Append-Only)",
        },
    )
    c2 = OntologyConceptEntity(
        id="0195f000-0000-7000-8000-000000002102",
        concept_key="concept-l3-ws-idempotency",
        canonical_term="Idempotency Token",
        level="3_WORKSPACE",
        scope_id=ws_id,
        definition_text="UUIDv7 deduplication key preventing duplicate payment capture.",
        synonyms=("Dedup Key",),
        profile_translations={
            "ARCHITECT": "Idempotency Token (UUIDv7 UNIQUE Constraint)",
            "PM_BUSINESS": "Duplicate Charge Prevention Key",
        },
    )
    c3 = OntologyConceptEntity(
        id="0195f000-0000-7000-8000-000000002103",
        concept_key="concept-l3-ws-unrelated-hr",
        canonical_term="Onboarding Badge",
        level="3_WORKSPACE",
        scope_id=ws_id,
        definition_text="Physical office access badge issued on employee start date.",
    )
    ax1 = OntologyAxiomEntity(
        id="0195f000-0000-7000-8000-000000002201",
        axiom_key="ax-ledger-append-only",
        concept_key="concept-l1-payment-ledger",
        level="1_ENTERPRISE",
        scope_id="scope-global",
        rule_expression="Ledger rows MUST NOT be updated or deleted once committed.",
        immutable=True,
    )
    ax3 = OntologyAxiomEntity(
        id="0195f000-0000-7000-8000-000000002202",
        axiom_key="ax-badge-expiry",
        concept_key="concept-l3-ws-unrelated-hr",
        level="3_WORKSPACE",
        scope_id=ws_id,
        rule_expression="Badge expires after 365 days.",
        immutable=False,
    )
    return OntologyGovernanceService(concepts=(c1, c2, c3), axioms=(ax1, ax3))


def test_ontology_ranker_empty_bundle_returns_no_fallback_concepts() -> None:
    empty_gov = OntologyGovernanceService()
    snap = empty_gov.resolve_snapshot(workspace_scope_id="0195f000-0000-7000-8000-000000000301")
    ranked = rank_ontology_snapshot_for_query(
        snap,
        query_text="Explain payment ledger rules",
        active_hat="ARCHITECT",
    )
    assert ranked.selected_concepts == ()
    assert ranked.applicable_axioms == ()
    concepts_dicts, axioms_dicts, summary = format_ranked_ontology_summary(ranked)
    assert concepts_dicts == ()
    assert axioms_dicts == ()
    assert summary is None


def test_ontology_ranker_lexical_hat_translation_and_applicable_axioms() -> None:
    gov = _build_test_ontology()
    ws_id = "0195f000-0000-7000-8000-000000000301"
    snap = gov.resolve_snapshot(workspace_scope_id=ws_id)
    ranked = rank_ontology_snapshot_for_query(
        snap,
        query_text="How does the payment ledger guarantee no duplicate capture?",
        active_hat="ARCHITECT",
    )
    terms = [rc.concept.canonical_term for rc in ranked.selected_concepts]
    assert "Payment Ledger" in terms
    assert "Idempotency Token" in terms
    assert "Onboarding Badge" not in terms
    assert ranked.selected_concepts[0].translated_label == (
        "Event-Sourced Payment Ledger (PG18 Append-Only)"
    )
    axiom_keys = [a.axiom_key for a in ranked.applicable_axioms]
    assert axiom_keys == ["ax-ledger-append-only"]

    pm_translated = ProfileSemanticTranslator.translate_concept(
        ranked.selected_concepts[1].concept, "PM"
    )
    assert pm_translated == "Duplicate Charge Prevention Key"


@pytest.mark.asyncio
async def test_ontology_ranker_uses_optional_embedding_when_active() -> None:
    gov = _build_test_ontology()
    ws_id = "0195f000-0000-7000-8000-000000000301"
    ranked = await rank_ontology_with_optional_embedding_async(
        gov,
        workspace_id=ws_id,
        query_text="settlement",
        active_hat="EXECUTIVE",
        embedding_port=_StubEmbeddingPort(),
    )
    assert len(ranked.selected_concepts) >= 1
    assert ranked.selected_concepts[0].concept.canonical_term == "Payment Ledger"
    assert ranked.selected_concepts[0].translated_label == (
        "Payment Ledger (DORA Audit & Settlement SLA)"
    )


def test_server_evidence_table_filters_confidential_sorts_authority_and_marks_stale() -> None:
    rag_active_stale = HybridRagHit(
        chunk_key="chk-conf-1",
        parent_chunk_key="chk-conf-p1",
        document_key="doc-conf-1",
        datasource_alias="confluence",
        source_uri="confluence://PAY/old-architecture",
        revision_tag="v1",
        contextual_header="[confluence | Old Arch]",
        injected_content="Legacy payment gateway specification.",
        rrf_score=0.032,
        vector_rank=1,
        bm25_rank=1,
        is_stale=True,
        stale_warning_marker="[STALE_WARNING: doc-conf-1 @ v1]",
    )
    rag_reference_fresh = HybridRagHit(
        chunk_key="chk-jira-1",
        parent_chunk_key="chk-jira-p1",
        document_key="doc-jira-1",
        datasource_alias="jira",
        source_uri="jira://PAY-42",
        revision_tag="v3",
        contextual_header="[jira | PAY-42]",
        injected_content="Authoritative PAY-42 threshold raised to 7500 EUR.",
        rrf_score=0.025,
        vector_rank=2,
        bm25_rank=2,
        is_stale=False,
        stale_warning_marker=None,
        datasource_role="REFERENCE",
    )
    bb_slice = ContextSliceRecord(
        slice_id="bb-01",
        source_uri="orcia://blackboard/ws-1/step_1@abc123",
        source_kind="BLACKBOARD_SNAPSHOT",
        content_sha256="sha256-bb-001",
        title="Blackboard Snapshot step_1",
        structured_payload={"status": "COMMITTED", "amount": 7500},
        text_excerpt='{"amount": 7500, "status": "COMMITTED"}',
    )
    confidential_slice = ContextSliceRecord(
        slice_id="sec-01",
        source_uri="confidential://vault/payroll-secrets",
        source_kind="CAS_BLOB",
        content_sha256="deadbeef",
        title="Confidential Payroll",
        structured_payload={"visibility_mode": "CONFIDENTIAL_RESTRICTED"},
        text_excerpt="TOP_SECRET_SALARY_DATA_MUST_NOT_LEAK",
    )

    result = build_server_evidence_table_for_turn(
        rag_hits=(rag_active_stale, rag_reference_fresh),
        context_slices=(bb_slice, confidential_slice),
        allowed_source_uris=frozenset(
            {
                "confluence://PAY/old-architecture",
                "jira://PAY-42",
                "orcia://blackboard/ws-1/step_1@abc123",
            }
        ),
        locale="en",
    )

    uris = [s.uri for s in result.evidence_table.sources]
    assert "jira://PAY-42" in uris
    assert "orcia://blackboard/ws-1/step_1@abc123" in uris
    assert "confluence://PAY/old-architecture" in uris
    # REFERENCE sources strictly outrank ACTIVE sources
    jira_idx = uris.index("jira://PAY-42")
    conf_idx = uris.index("confluence://PAY/old-architecture")
    assert jira_idx < conf_idx
    assert "[STALE_WARNING]" in result.layer4_markdown
    assert "TOP_SECRET_SALARY_DATA_MUST_NOT_LEAK" not in result.layer4_markdown
    assert result.masked_count == 1


def test_token_budget_trimmer_preserves_newest_turns_and_layer1() -> None:
    history = [
        {"role": "user", "content": "oldest turn " + ("A" * 1200)},
        {"role": "assistant", "content": "oldest reply " + ("B" * 1200)},
        {"role": "user", "content": "recent turn question"},
        {"role": "assistant", "content": "recent turn answer"},
    ]
    res = trim_messages_to_token_budget(
        system_msg=f"{CONSTITUTIONAL_LAYER_1_TEXT_EN}\n\n[ONTOLOGY]\nShort context",
        user_prompt="Final user follow-up question",
        conversation_history=history,
        max_tokens_budget=400,
    )
    assert res.dropped_history_count >= 2
    assert res.estimated_input_tokens <= 400
    contents = [m["content"] for m in res.messages]
    assert CONSTITUTIONAL_LAYER_1_TEXT_EN in contents[0]
    assert "recent turn question" in contents
    assert "recent turn answer" in contents
    assert contents[-1] == "Final user follow-up question"
    assert not any("oldest turn" in c for c in contents)
