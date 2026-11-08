"""Eval « Golden Dataset » pour l'Assistant (`FR-4`, 5 couches) & l'Ontologie (`AD-17` C4).

Exécute à `0 $` (`DeterministicCassetteLLM` & services déterministes) :
- Le jeu doré `tests/evals/golden/assistant_and_ontology.jsonl` : refus constitutionnel Couche 1
  (`HUMAN_ANCHOR_WRITE_REFUSAL`), adaptation de registre aux profils humains (`EXECUTIVE`,
  `ARCHITECT`, `PM`), composition conversationnelle (`WORKFLOW_COMPOSE`) et validation d'artefacts
  Blackboard contre l'Ontologie à 4 niveaux.
- Les garde-fous d'orthogonalité des modèles (`AD-10`) et de conflit (`ERR_ONTOLOGY_CONFLICT`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from orcia_core.gates.errors import ModelOrthogonalityViolationError
from orcia_core.ontology import (
    OntologyConceptEntity,
    OntologyHierarchyResolver,
    build_seeded_ontology_service,
)
from orcia_core.ontology.errors import OntologyConflictError
from orcia_core.orchestration.assistant_agent import AssistantAgentService
from orcia_core.orchestration.assistant_harness import CONSTITUTIONAL_LAYER_1_TEXT
from orcia_core.orchestration.seeds import build_default_orchestration_setup_service
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.ports.llm_port import LlmPromptRequest
from orcia_core.rag import build_seeded_rag_service
from orcia_core.rag.context_adapters import (
    CatalogAndBlackboardContextSourceAdapter,
    HybridRagVectorStoreAdapter,
)
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_pack_sdlc import activate_sdlc_pack

GOLDEN_PATH = Path(__file__).parent / "golden" / "assistant_and_ontology.jsonl"
_WS_EVAL = "0192c4e0-0000-7000-8000-000000000201"


def _load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines() if line
    ]


def _build_assistant_service() -> AssistantAgentService:
    activate_sdlc_pack()
    auth_svc = build_default_auth_and_org_service()
    setup_svc = build_default_orchestration_setup_service(evaluator=auth_svc.evaluator)
    seeded_rag, _ = build_seeded_rag_service()
    vector_store = HybridRagVectorStoreAdapter(seeded_rag)
    context_source = CatalogAndBlackboardContextSourceAdapter(
        rag_service=seeded_rag,
        catalog_items_provider=lambda _ws: tuple(setup_svc.workflows),
        blackboard_snapshots_provider=lambda _ws: (),
        permission_policies_provider=lambda _ws: (),
    )
    return AssistantAgentService(
        context_source=context_source,
        vector_store=vector_store,
        orchestration_setup=setup_svc,
        workflow_engine=setup_svc.engine,
    )


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: str(c["id"]))
def test_golden_assistant_and_ontology_case(case: dict[str, Any]) -> None:
    if case["kind"] == "assistant_turn":
        svc = _build_assistant_service()
        turn = svc.run_conversation_turn(
            workspace_id=_WS_EVAL,
            user_prompt=str(case["prompt"]),
            human_profile_archetype=str(case["profile"]),
        )
        assert turn.intent == case["expected_intent"]
        assert len(turn.assembled_prompt.layers) == 5
        assert turn.assembled_prompt.layers[0].immutable is True
        assert CONSTITUTIONAL_LAYER_1_TEXT in turn.assembled_prompt.system_prompt
        expected_sub = str(case["expected_substring"])
        combined_output = turn.response_text
        if turn.workflow_proposal is not None:
            combined_output += " " + " ".join(n.id for n in turn.workflow_proposal.nodes)
        assert expected_sub in combined_output
    elif case["kind"] == "ontology_validate":
        gov = build_seeded_ontology_service()
        snap = gov.resolve_snapshot(run_scope_id="run-checkout-001")
        res = OntologyHierarchyResolver.validate_blackboard_artifact(
            canonical_term=str(case["term"]),
            payload=dict(case["payload"]),
            snapshot=snap,
        )
        assert res.valid is bool(case["expect_valid"])


@pytest.mark.asyncio
async def test_cassette_llm_zero_cost_and_ontology_l1_conflict_guard() -> None:
    """Verify `0 $` cassette replay, `AD-10` orthogonality, and L1 axiom conflict rejection."""
    cassette = DeterministicCassetteLLM()
    reply = await cassette.complete(
        LlmPromptRequest(
            system_prompt="Coach mode",
            user_prompt="Choix AMBIGU entre deux architectures",
            model_family="anthropic",
            model_id="claude-3-7-sonnet",
            execution_mode="COACHING",
        )
    )
    assert reply.estimated_cost_usd == 0.0
    assert reply.scenario_tag == "WAITING_FOR_HUMAN_ARBITRATION"

    with pytest.raises(ModelOrthogonalityViolationError):
        await cassette.complete(
            LlmPromptRequest(
                system_prompt="Gate Evaluator",
                user_prompt="Evaluate artifact",
                model_family="anthropic",
                model_id="claude-3-7-sonnet",
                executor_model_family="anthropic",
            )
        )

    gov = build_seeded_ontology_service()
    contradictory = OntologyConceptEntity(
        id="0192c4e0-0000-7000-8000-000000002999",
        concept_key="concept-l3-illegal-override",
        canonical_term="Actif Stratégique",
        level="3_WORKSPACE",
        scope_id="ws-solution-paiement",
        definition_text="Surcharge illégale d'axiome L1.",
        expected_schema={"asset_id": "int"},
    )
    with pytest.raises(OntologyConflictError) as exc_info:
        OntologyHierarchyResolver.resolve_effective_ontology(
            concepts=(*gov.concepts, contradictory),
            relations=gov.relations,
            axioms=gov.axioms,
            enterprise_scope_id="scope-global",
            domain_scope_id="scope-bu-digital",
            team_chain_scope_ids=("scope-subteam-checkout", "scope-team-core"),
            workspace_scope_id="ws-solution-paiement",
        )
    assert exc_info.value.error_code == "ERR_ONTOLOGY_CONFLICT"
