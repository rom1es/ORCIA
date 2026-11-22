"""Story 26.5 — Golden `0 $` Ontology Relevance, Axiom & Hat Translation Evals (`AD-17` C4)."""

from __future__ import annotations

import pytest

from orcia_core.ontology import (
    OntologyAxiomEntity,
    OntologyConceptEntity,
    OntologyGovernanceService,
)
from orcia_core.ontology.context_ranker import (
    format_ranked_ontology_summary,
    rank_ontology_snapshot_for_query,
)
from orcia_core.orchestration.assistant_prompt_builder import AssistantPromptBuilder

_WS_PAY = "0192c4e0-0000-7000-8000-000000000201"


def _golden_ontology_service() -> OntologyGovernanceService:
    c_l1 = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000003001",
        concept_key="concept-l1-critical-payment-asset",
        canonical_term="Payment Gateway Asset",
        level="1_ENTERPRISE",
        scope_id="scope-global",
        definition_text="Tier-1 payment processing engine governed by DORA and PCI-DSS.",
        synonyms=("Checkout Engine", "PSP Bridge"),
        profile_translations={
            "EXECUTIVE": "Payment Gateway Asset (DORA SLA 99.99% & Fraud Risk)",
            "ARCHITECT": "Payment Gateway Asset (Idempotent Event-Sourced Core)",
            "SECOPS": "Payment Gateway Asset (PCI-DSS Scope & Append-Only Audit)",
        },
    )
    c_l3_ws = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000003002",
        concept_key="concept-l3-ws-capture-key",
        canonical_term="Capture Idempotency Key",
        level="3_WORKSPACE",
        scope_id=_WS_PAY,
        definition_text="UUIDv7 deduplication key enforced before every PSP settlement call.",
        synonyms=("Dedup Key", "Settlement Lock"),
        profile_translations={
            "EXECUTIVE": "Duplicate Capture Financial Safeguard",
            "ARCHITECT": "Capture Idempotency Key (UUIDv7 + PG18 UNIQUE Constraint)",
        },
    )
    c_l3_unrelated = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000003003",
        concept_key="concept-l3-ws-cafeteria",
        canonical_term="Office Catering Menu",
        level="3_WORKSPACE",
        scope_id=_WS_PAY,
        definition_text="Weekly lunch menu schedule for campus building B.",
    )
    ax_pci = OntologyAxiomEntity(
        id="0192c4e0-0000-7000-8000-000000003101",
        axiom_key="ax-pci-no-pan-log",
        concept_key="concept-l1-critical-payment-asset",
        level="1_ENTERPRISE",
        scope_id="scope-global",
        rule_expression="Never log raw PAN or CVV fields into telemetry or Blackboard.",
        immutable=True,
    )
    ax_dedup = OntologyAxiomEntity(
        id="0192c4e0-0000-7000-8000-000000003102",
        axiom_key="ax-capture-uuidv7",
        concept_key="concept-l3-ws-capture-key",
        level="3_WORKSPACE",
        scope_id=_WS_PAY,
        rule_expression="Every PSP capture request MUST carry a non-empty UUIDv7 key.",
        immutable=True,
    )
    ax_catering = OntologyAxiomEntity(
        id="0192c4e0-0000-7000-8000-000000003103",
        axiom_key="ax-catering-cutoff",
        concept_key="concept-l3-ws-cafeteria",
        level="3_WORKSPACE",
        scope_id=_WS_PAY,
        rule_expression="Orders close at 10:00.",
        immutable=False,
    )
    return OntologyGovernanceService(
        concepts=(c_l1, c_l3_ws, c_l3_unrelated),
        axioms=(ax_pci, ax_dedup, ax_catering),
    )


@pytest.mark.parametrize(
    ("hat", "query", "expected_term_sub", "expected_axiom_key"),
    [
        (
            "EXECUTIVE",
            "What is the DORA SLA and financial safeguard for the checkout engine?",
            "DORA SLA 99.99%",
            "ax-pci-no-pan-log",
        ),
        (
            "ARCHITECT",
            "How does capture idempotency key prevent duplicate PSP settlement?",
            "UUIDv7 + PG18 UNIQUE Constraint",
            "ax-capture-uuidv7",
        ),
        (
            "SECOPS",
            "Audit PCI-DSS rules on the Payment Gateway Asset",
            "PCI-DSS Scope & Append-Only Audit",
            "ax-pci-no-pan-log",
        ),
    ],
)
def test_golden_ontology_relevance_axioms_and_hat_translation_in_layer_2(
    hat: str,
    query: str,
    expected_term_sub: str,
    expected_axiom_key: str,
) -> None:
    """Verify Layer 2 ranks relevant L1-L4 concepts, translates per hat, and injects axioms."""
    gov = _golden_ontology_service()
    snap = gov.resolve_snapshot(workspace_scope_id=_WS_PAY)
    ranked = rank_ontology_snapshot_for_query(
        snap,
        query_text=query,
        active_hat=hat,
    )
    concepts_payload, axioms_payload, _ = format_ranked_ontology_summary(ranked)
    builder = AssistantPromptBuilder()
    assembled = builder.assemble_prompt(
        user_prompt=query,
        human_profile_archetype=hat,
        workspace_id=_WS_PAY,
        intent="QA_COACHING",
        ontology_concepts=concepts_payload,
        ontology_axioms=axioms_payload,
        locale="en",
    )
    layer_2 = next(b for b in assembled.layers if b.layer_order == 2)
    assert expected_term_sub in layer_2.content
    assert expected_axiom_key in layer_2.content
    assert "Office Catering Menu" not in layer_2.content
    assert "ax-catering-cutoff" not in layer_2.content
