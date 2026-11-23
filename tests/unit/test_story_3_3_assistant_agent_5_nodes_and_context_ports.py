"""Unit & API Conformance tests for Story 3.3 & DEC-CTX-01 (`AssistantAgentService` 5-node DAG).

Covers:
1. `DEC-CTX-01`: `ContextSourcePort`, `VectorStorePort`, and `orcia.indexers` registry.
2. 5-Node `orcia://system/workflows/assistant-agent` DAG and `< 1.5 s` latency (`NFR-PERF-1`).
3. 5-Layer `AssistantHarness`, Constitutional Layer 1 refusal (`FR-4`), and Human Profile adaptation
   (`EXECUTIVE`, `PM`, `ARCHITECT`, `SECOPS`, `FR-1`, `UX-DR12`).
4. Arthur (`UJ-10`) conversational workflow composition (`WORKFLOW_COMPOSE`), modification
   (`WORKFLOW_MODIFY`), `@xyflow/react` graph + YAML manifest (`UX-DR15`), and 1-click
   `save-and-launch` real execution via `orcia.step_executors`.
5. `core-without-sdlc` (`AD-20`): zero SDLC vocabulary in `orcia-core` Assistant modules.
6. FastAPI endpoints (`/api/v1/assistant/chat`, `/api/v1/assistant/chat/stream`,
   `/api/v1/assistant/workflows/save-and-launch`).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration.assistant_agent import (
    ASSISTANT_WORKFLOW_URI,
    AssistantAgentService,
)
from orcia_core.orchestration.assistant_composer import build_generic_core_blueprint
from orcia_core.orchestration.assistant_harness import (
    CONSTITUTIONAL_LAYER_1_TEXT,
    AssistantHarness,
    resolve_profile_adaptation,
)
from orcia_core.orchestration.seeds import build_default_orchestration_setup_service
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.rag import build_seeded_rag_service
from orcia_core.rag.context_adapters import (
    CatalogAndBlackboardContextSourceAdapter,
    HybridRagVectorStoreAdapter,
)
from orcia_kernel.context_ports import (
    IndexerRegimeDescriptor,
    get_registered_indexer_regime,
    list_registered_assistant_templates,
    list_registered_indexer_regimes,
    register_indexer_regime,
)
from orcia_pack_sdlc import activate_sdlc_pack

_WS_PAY = "0192c4e0-0000-7000-8000-000000000201"


def _build_assistant_fixture() -> tuple[AssistantAgentService, str]:
    activate_sdlc_pack()
    auth_svc = build_default_auth_and_org_service()
    setup_svc = build_default_orchestration_setup_service(evaluator=auth_svc.evaluator)
    from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

    from orcia_core.orchestration.step_executors import _DEFAULT_AGENT_EXECUTOR
    from orcia_core.testing.cassette_llm import DeterministicCassetteLLM

    cassette = DeterministicCassetteLLM()
    _DEFAULT_AGENT_EXECUTOR.set_llm_gateway(cassette)
    fake_emb = FakeDeterministicEmbeddingAdapter()
    seeded_rag, _ = build_seeded_rag_service(embedding_port=fake_emb)
    workspace_id = _WS_PAY

    vector_store = HybridRagVectorStoreAdapter(seeded_rag, embedding_port=fake_emb)
    context_source = CatalogAndBlackboardContextSourceAdapter(
        rag_service=seeded_rag,
        catalog_items_provider=lambda _ws: tuple(setup_svc.workflows),
        blackboard_snapshots_provider=lambda _ws: (),
        permission_policies_provider=lambda _ws: (
            {
                "ticket_key": "PERM-403",
                "target_uri": "git://payment-v2/repo",
                "status": "APPROVED",
            },
        ),
    )
    context_source.register_context_slice(
        slice_id="slice-archi-pay-v2",
        source_uri="confluence://ARCHI/payment-v2-spec",
        source_kind="KB_DOCUMENT",
        title="Spécification Architecture Paiement v2",
        structured_payload={"doc_key": "ARCHI-PAY-V2", "revision": "v12"},
        text_excerpt="Invariants de conformité PCI-DSS et idempotence.",
        is_stale=True,
        stale_warning_marker="[STALE_WARNING: age=120d > ttl=90d]",
    )
    service = AssistantAgentService(
        context_source=context_source,
        vector_store=vector_store,
        llm_gateway=cassette,
        orchestration_setup=setup_svc,
        workflow_engine=setup_svc.engine,
    )
    return service, workspace_id


def test_dec_ctx_01_context_source_port_vector_store_port_and_indexers_registry() -> None:
    """Verify DEC-CTX-01: ContextSourcePort, VectorStorePort, and `orcia.indexers` registry."""
    service, workspace_id = _build_assistant_fixture()
    regimes = list_registered_indexer_regimes()
    assert "CODE_AST_GRAPH" in regimes
    assert "JIRA_HYBRID" in regimes
    assert "TRIPARTITE_GRAPH" in regimes

    code_desc = get_registered_indexer_regime("CODE_AST_GRAPH")
    assert code_desc is not None
    assert code_desc.pack_name == "orcia-pack-sdlc"

    # Register a custom domain indexer dynamically (e.g., Legal Contract Clauses)
    register_indexer_regime(
        IndexerRegimeDescriptor(
            regime_key="LEGAL_CLAUSE_TREE",
            display_name="Découpage hiérarchique par article et alinéa juridique",
            pack_name="orcia-pack-legal",
        )
    )
    assert get_registered_indexer_regime("LEGAL_CLAUSE_TREE") is not None

    # Verify ContextSourcePort and VectorStorePort adapters directly
    turn = service.run_conversation_turn(
        workspace_id=workspace_id,
        user_prompt="Quels sont les invariants de Paiement v2 ?",
        human_profile_archetype="ARCHITECT",
    )
    assert len(turn.node_traces) == 5
    assert any("confluence://ARCHI/payment-v2-spec" in u for u in turn.assembled_prompt.cited_uris)
    assert len(turn.assembled_prompt.stale_warnings) >= 1


def test_assistant_5_nodes_dag_and_5_layer_harness_profiles_and_constitutional_refusal() -> None:
    """Verify the 5-node DAG, < 1.5s latency, 4 Human Profiles, and Layer 1 refusal (`FR-4`)."""
    service, workspace_id = _build_assistant_fixture()

    # 1. Verify all 4 Human Profiles adapt register, vocabulary, and indicators (`FR-1`, `UX-DR12`)
    seen_prefixes: set[str] = set()
    for profile in ("EXECUTIVE", "PM", "ARCHITECT", "SECOPS"):
        spec = resolve_profile_adaptation(profile)
        assert spec.archetype == profile
        turn = service.run_conversation_turn(
            workspace_id=workspace_id,
            user_prompt="Synthétise l'état de conformité du projet Paiement v2.",
            human_profile_archetype=profile,
        )
        assert turn.workflow_uri == ASSISTANT_WORKFLOW_URI
        assert turn.first_token_latency_ms < 1500.0
        assert [t.node_id for t in turn.node_traces] == [
            "1_INTENT_ROUTER",
            "2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION",
            "3_PARALLEL_FAN_OUT",
            "4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION",
            "5_PROFILE_ADAPTIVE_SYNTHESIZER",
        ]
        assert len(turn.assembled_prompt.layers) == 5
        assert turn.assembled_prompt.layers[0].layer_id == "1_CONSTITUTIONAL_IMMUTABLE"
        assert turn.assembled_prompt.layers[0].immutable is True
        assert CONSTITUTIONAL_LAYER_1_TEXT in turn.assembled_prompt.system_prompt
        seen_prefixes.add(spec.response_prefix_fr)
        assert spec.response_prefix_fr in turn.response_text

    assert len(seen_prefixes) == 4

    # 2. Verify Constitutional Layer 1 refusal when user asks "Remplis-le pour moi" (`FR-4`)
    refusal_turn = service.run_conversation_turn(
        workspace_id=workspace_id,
        user_prompt="L'ancre humaine est trop longue, remplis-le pour moi s'il te plaît.",
        human_profile_archetype="ARCHITECT",
    )
    assert refusal_turn.intent == "HUMAN_ANCHOR_WRITE_REFUSAL"
    assert "human_authored_required: true" in refusal_turn.response_text
    assert "Question socratique" in refusal_turn.response_text


def test_arthur_uj10_conversational_workflow_composer_modify_and_save_and_launch() -> None:
    """Verify Arthur (`UJ-10`): compose workflow, add step 4, and 1-click save-and-launch."""
    service, workspace_id = _build_assistant_fixture()
    auth_svc = build_default_auth_and_org_service()
    arthur = auth_svc.resolve_user(persona_key="marc")

    # Step 1: Arthur asks the Assistant to compose a Confluence/Jira vs Git audit workflow
    compose_turn = service.run_conversation_turn(
        workspace_id=workspace_id,
        user_prompt=(
            "Propose un workflow pour comparer la documentation Confluence et Jira "
            "avec le code Git et identifier les écarts."
        ),
        human_profile_archetype="ARCHITECT",
    )
    assert compose_turn.intent == "WORKFLOW_COMPOSE"
    assert compose_turn.workflow_proposal is not None
    proposal_v1 = compose_turn.workflow_proposal
    assert len(proposal_v1.nodes) == 4
    assert len(proposal_v1.edges) == 3
    assert "step_1_scope_anchor" in [n.id for n in proposal_v1.nodes]

    # Step 2: Arthur asks to add a 4th intermediate security control step (`WORKFLOW_MODIFY`)
    modify_turn = service.run_conversation_turn(
        workspace_id=workspace_id,
        user_prompt="Ajoute une étape 4 de vérification de conformité sécurité avant la synthèse.",
        human_profile_archetype="ARCHITECT",
    )
    assert modify_turn.intent == "WORKFLOW_MODIFY"
    assert modify_turn.workflow_proposal is not None
    proposal_v2 = modify_turn.workflow_proposal
    assert len(proposal_v2.nodes) == 5
    assert "step_4_security_compliance_check" in [n.id for n in proposal_v2.nodes]

    # Step 3: Validate manifest & launch durable process via AssistantProcessLauncherService
    from orcia_core.orchestration.assistant_process_launcher import AssistantProcessLauncherService

    assert service._setup is not None
    rep = service._setup.validate_workflow_manifest(
        proposal_v2.manifest_yaml, workspace_id=workspace_id, raise_on_error=True
    )
    assert rep.workflow is not None
    service._setup.register_validated_workflow(rep.workflow)
    launcher = AssistantProcessLauncherService(setup_service=service._setup, engine=service._engine)
    launched = asyncio.run(
        launcher.launch_process_async(
            arthur,
            workspace_id=workspace_id,
            workflow_uri=proposal_v2.workflow_uri,
            idempotency_token="uj10-composed-v2",
        )
    )
    assert launched.workflow_uri == proposal_v2.workflow_uri
    assert "step_1_scope_anchor" in launched.waiting_step_keys
    assert launched.run_status == "WAITING_FOR_HUMAN_ARBITRATION"
    assert launched.snapshot_count == 0


def test_core_without_sdlc_zero_vocabulary_and_generic_blueprint_fallback() -> None:
    """Verify `AD-20`: zero SDLC terms in `orcia-core` Assistant files and generic fallback."""
    core_dir = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "orcia-core"
        / "src"
        / "orcia_core"
        / "orchestration"
    )
    forbidden_terms = ("jira", "confluence", "gitlab", "github", "sonar", "pull_request")
    for fname in ("assistant_harness.py", "assistant_agent.py", "assistant_composer.py"):
        content = (core_dir / fname).read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            assert term not in content, f"Forbidden SDLC term {term!r} found in {fname}"

    # Generic core blueprint works without any SDLC plugin matching
    generic_bp = build_generic_core_blueprint(
        workspace_id="ws-legal",
        modification_instruction="Ajoute un contrôle RGPD",
    )
    assert generic_bp.template_key == "core-multi-source-audit"
    assert len(generic_bp.steps_summary) == 4
    assert len(list_registered_assistant_templates()) >= 1
    harness = AssistantHarness()
    prompt = harness.assemble_prompt(
        user_prompt="Audit conformité",
        human_profile_archetype="EXECUTIVE",
        workspace_id="ws-legal",
        intent="WORKFLOW_COMPOSE",
        workflow_blueprint=generic_bp,
    )
    assert prompt.profile_adaptation.archetype == "EXECUTIVE"


def test_fastapi_assistant_chat_stream_and_save_and_launch_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify FastAPI `/api/v1/assistant/chat`, `/chat/stream`, and `/workflows/save-and-launch`."""
    from orcia_core.orchestration.step_executors import _DEFAULT_AGENT_EXECUTOR
    from orcia_core.testing.cassette_llm import DeterministicCassetteLLM

    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    _DEFAULT_AGENT_EXECUTOR.set_llm_gateway(DeterministicCassetteLLM())
    app = create_app()
    with TestClient(app) as client:
        # 1. Deleted legacy /chat, /chat/stream, and /workflows/save-and-launch must return 404/405
        assert client.post(
            "/api/v1/assistant/chat?persona_key=marc",
            json={"workspace_id": _WS_PAY, "user_prompt": "Bonjour"},
        ).status_code in (404, 405)
        assert client.post(
            "/api/v1/assistant/chat/stream?persona_key=marc",
            json={"workspace_id": _WS_PAY, "user_prompt": "Bonjour"},
        ).status_code in (404, 405)
        assert client.post(
            "/api/v1/assistant/workflows/save-and-launch?persona_key=marc",
            json={"workspace_id": _WS_PAY, "manifest_yaml": "uri: orcia://workflows/legacy\n"},
        ).status_code in (404, 405)

        # 2. Canonical POST /api/v1/assistant/turns -> GET /turns/{id}/stream (SSE)
        turn_resp = client.post(
            "/api/v1/assistant/turns?persona_key=marc",
            json={
                "workspace_id": _WS_PAY,
                "user_prompt": "Explique la gouvernance de ce workspace.",
            },
        )
        assert turn_resp.status_code == 202
        turn_id = turn_resp.json()["turn_id"]
        stream_resp = client.get(f"{turn_resp.json()['stream_url']}?persona_key=marc")
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]
        sse_text = stream_resp.text
        assert "event: token_delta" in sse_text
        assert "event: citation_map" in sse_text
        assert "event: turn_completed" in sse_text

        # 3. Canonical CONTINUE_IN_PROCESS via /turns/{id}/approve (Contributor `marc` succeeds)
        launch_resp = client.post(
            f"/api/v1/assistant/turns/{turn_id}/approve?persona_key=marc",
            json={
                "workspace_id": _WS_PAY,
                "proposal_id": "prop-story-3-3",
                "approved": True,
                "human_anchor_markdown": "Human anchor justification >= 10 chars.",
                "continue_in_process": True,
            },
        )
        assert launch_resp.status_code == 200
        launch_body = launch_resp.json()
        assert launch_body["status"] == "APPROVED"
        assert launch_body["run_id"]
        assert launch_body["run_status"] == "WAITING_FOR_HUMAN_ARBITRATION"
        assert launch_body["waiting_step_keys"] == ["frame-architecture-intent"]

        # 4. Observer role (`claire` BU_DIRECTOR in observer mode on workspace) is rejected with 403
        obs_resp = client.post(
            f"/api/v1/assistant/turns/{turn_id}/approve?persona_key=claire",
            json={
                "workspace_id": _WS_PAY,
                "proposal_id": "prop-story-3-3-obs",
                "approved": True,
                "human_anchor_markdown": "Observer anchor should be denied.",
                "continue_in_process": True,
            },
        )
        assert obs_resp.status_code == 403
        assert obs_resp.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
