"""Unit & Integration Tests for Story 4.2 + DEC-SEC-01 / SEC-03 (`AD-6`, `AD-10`, `AD-12`).

Covers:
1. Model family orthogonality (`evaluator_model_family != executor_model_family`), CoT purging,
   and sovereign local routing (`SENSITIVE` / `RESTRICTED` -> `local/ollama-*` or `local/vllm-*`).
2. Reversible PII pseudonymization (`PiiReversibleScrubber`) backed by Redis-compatible vault
   scoped per `run_id` and local rehydration on return.
3. 5-Lens Evaluation DAG (`transverse_alignment_step1`, `fact_verification`,
   `adversarial_edge_cases`, `domain_and_security_compliance` + `synthesis_and_structure`
   consolidating `briefing_4blocks_jsonb` and publishing `GateEvaluated` to `domain_events_outbox`).
4. `DEC-SEC-01` & `SEC-03`: `SecretRef`, `EnvelopeVaultSecretProvider` (DEK/KEK rotation & audit),
   removal of `sk-orcia-local` default from `LiteLLMAdapter`, governed invocation through
   `ConnectorInvoker` (`429 Retry-After` -> `200 OK`), `structlog` secret masking, and Canary
   Secret Leak verification across `dbos.*`, `audit_ledger`, `domain_events_outbox`,
   `step_executions`, and `structlog`.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.bootstrap._internal.litellm_adapter import LiteLLMAdapter
from orcia_core.gates import (
    AgenticGateInput,
    AgenticGateService,
    ModelOrthogonalityViolationError,
    PiiReversibleScrubber,
    purge_executor_chain_of_thought,
)
from orcia_core.observability.logging import (
    clear_sensitive_secret_values,
    configure_structlog,
    get_logger,
    scrub_sensitive_dict,
)
from orcia_core.permissions.connector_invoker import ConnectorInvoker
from orcia_core.permissions.secret_manager import (
    EnvelopeVaultSecretProvider,
    verify_canary_secret_absence,
)
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.ports import LlmPromptRequest, SecretRef


class _FakeRedisVaultBackend:
    """Redis-compatible `setex`/`get` test double verifying TTL-scoped PII token persistence."""

    def __init__(self) -> None:
        self.store: dict[str, tuple[int, str]] = {}

    def setex(self, name: str, time: int, value: str) -> bool:
        self.store[name] = (time, value)
        return True

    def get(self, name: str) -> str | None:
        entry = self.store.get(name)
        return entry[1] if entry is not None else None


def test_pii_reversible_scrubber_and_cot_purger() -> None:
    """Verify `PiiReversibleScrubber` deterministic tokens per `run_id` and CoT stripping."""
    redis_vault = _FakeRedisVaultBackend()
    scrubber = PiiReversibleScrubber(vault_backend=redis_vault, ttl_seconds=1800)

    raw_artifact: dict[str, Any] = {
        "title": "Dossier de crédit d'Hélène Martin",
        "summary": (
            "<thinking>Je vais contourner la règle de plafond.</thinking>"
            "Contact: helene.martin@banque-exemple.fr, Tél: +33 6 12 34 56 78, "
            "IBAN: FR76 3000 6000 0112 3456 7890 189, NIR: 2 85 05 75 116 234 91."
        ),
        "chain_of_thought": "Raisonnement interne secret de l'agent exécuteur",
        "reasoning_content": "Autre trace CoT interne",
        "notes": "[THOUGHT]Analyse confidentielle[/THOUGHT] Client VIP Projet-Orphée.",
    }

    purged, cot_count = purge_executor_chain_of_thought(raw_artifact)
    assert cot_count == 4
    assert "chain_of_thought" not in purged
    assert "reasoning_content" not in purged
    assert "contourner la règle" not in str(purged)
    assert "Analyse confidentielle" not in str(purged)

    scrubbed, token_map, redacted_count = scrubber.scrub_payload(
        "run-pii-001",
        purged,
        custom_entities=("Hélène Martin", "Projet-Orphée"),
    )
    assert redacted_count >= 6
    scrubbed_str = str(scrubbed)
    assert "helene.martin@banque-exemple.fr" not in scrubbed_str
    assert "FR76 3000 6000 0112 3456 7890 189" not in scrubbed_str
    assert "Hélène Martin" not in scrubbed_str
    assert "Projet-Orphée" not in scrubbed_str
    assert "[PII_EMAIL_1]" in scrubbed_str
    assert "[PII_IBAN_1]" in scrubbed_str
    assert "[PII_ENTITY_1]" in scrubbed_str
    assert "pii:vault:run:run-pii-001" in redis_vault.store
    assert redis_vault.store["pii:vault:run:run-pii-001"][0] == 1800

    rehydrated = scrubber.rehydrate_payload("run-pii-001", scrubbed)
    assert rehydrated["title"] == "Dossier de crédit d'Hélène Martin"
    assert "helene.martin@banque-exemple.fr" in rehydrated["summary"]
    assert "FR76 3000 6000 0112 3456 7890 189" in rehydrated["summary"]
    assert "Projet-Orphée" in rehydrated["notes"]
    assert len(token_map) >= 6


def test_agentic_gate_orthogonality_5_lenses_and_local_sovereign_routing() -> None:
    """Verify Model Orthogonality (`AD-10`), 5-Lens DAG, fact verification, and local routing."""
    cassette = DeterministicCassetteLLM()
    redis_vault = _FakeRedisVaultBackend()
    scrubber = PiiReversibleScrubber(vault_backend=redis_vault)
    service = AgenticGateService(llm_port=cassette, pii_scrubber=scrubber)

    # 1. Orthogonality violation must raise ModelOrthogonalityViolationError
    with pytest.raises(ModelOrthogonalityViolationError):
        service.evaluate_agentic_gate(
            AgenticGateInput(
                workspace_id="ws-payment",
                run_id="run-402-orth",
                step_execution_id="step-exec-1",
                step_key="step-2-arch",
                executor_model_family="anthropic",
                evaluator_model_family="anthropic",
                candidate_artifact={"summary": "Test"},
            )
        )

    # 2. SENSITIVE classification routes to local sovereign model with PII scrubbing & 5 lenses
    res_pass = service.evaluate_agentic_gate(
        AgenticGateInput(
            workspace_id="ws-payment",
            run_id="run-402-pass",
            step_execution_id="step-exec-2",
            step_key="step-2-arch",
            executor_model_family="anthropic",
            evaluator_model_family="google",
            data_classification="SENSITIVE",
            anonymize_pii_reversible=True,
            custom_pii_entities=("Jean Dupont",),
            candidate_artifact={
                "summary": (
                    "<thinking>CoT caché</thinking>"
                    "Architecture PostgreSQL 18 validée pour Jean Dupont (jean.dupont@orcia.io)."
                ),
                "chain_of_thought": "Ne jamais envoyer à l'évaluateur",
                "claims": [
                    {
                        "statement": "La persistance utilise PostgreSQL 18 et pgvector.",
                        "source_uri": "orcia://ontology/layer-1/postgresql-18",
                        "confidence": 0.96,
                    }
                ],
            },
            step1_prd_invariants=("require:postgresql 18", "forbid:sqlite"),
            step2_arch_invariants=("forbid:minio",),
            ontology_facts={"db_engine": "forbid:sqlite"},
            step_memlog_markers=(
                {
                    "marker_type": "sdlc.DECISION",
                    "text": "Adoption de PostgreSQL 18 + pgvector.",
                },
                {
                    "marker_type": "sdlc.ASSUMPTION",
                    "text": "Latence réseau intra-cluster < 2 ms.",
                },
            ),
        )
    )
    assert res_pass.evaluation.status == "PASS"
    assert res_pass.evaluation.score >= 0.85
    assert res_pass.routed_to_local_sovereign_model is True
    assert res_pass.routed_model_family == "local_ollama"
    assert res_pass.routed_model_id == "local/ollama-qwen2.5-coder-32b"
    assert res_pass.cot_items_purged == 2
    assert res_pass.pii_tokens_redacted >= 2
    assert len(res_pass.lens_results) == 5
    # Verify PII was scrubbed in all 5 LLM calls and CoT was purged
    for call in cassette.call_history:
        assert "jean.dupont@orcia.io" not in call.user_prompt
        assert "Jean Dupont" not in call.user_prompt
        assert "CoT caché" not in call.user_prompt
        assert "Ne jamais envoyer" not in call.user_prompt
    # Verify local rehydration restored PII in the final summary and 4-block briefing
    assert "Jean Dupont" in res_pass.rehydrated_summary
    assert "jean.dupont@orcia.io" in res_pass.rehydrated_summary
    assert "Adoption de PostgreSQL 18 + pgvector." in res_pass.briefing_4blocks.decisions_made
    assert len(service.list_outbox_events()) == 1
    assert service.list_outbox_events()[0].payload["gate_type"] == "AGENTIC"

    # 3. Fact verification / Transverse Step 1 failure blocks the gate
    res_fail = service.evaluate_agentic_gate(
        AgenticGateInput(
            workspace_id="ws-payment",
            run_id="run-402-fail",
            step_execution_id="step-exec-3",
            step_key="step-3-dev",
            executor_model_family="anthropic",
            evaluator_model_family="openai",
            candidate_artifact={
                "summary": "Utilisation de sqlite en test d'intégration.",
                "claims": [
                    {
                        "statement": "Les tests utilisent sqlite en mémoire.",
                        "confidence": 0.55,
                    }
                ],
            },
            step1_prd_invariants=("forbid:sqlite",),
            ontology_facts={"no_sqlite": "forbid:sqlite"},
        )
    )
    assert res_fail.evaluation.status == "FAIL"
    assert res_fail.lens_results[0].passed is False  # transverse_alignment_step1
    assert res_fail.lens_results[1].passed is False  # fact_verification


@pytest.mark.asyncio
async def test_dec_sec_01_secret_ref_envelope_rotation_and_canary_leak_verification(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify `DEC-SEC-01` & `SEC-03`: no `sk-orcia-local`, DEK rotation, 0 canary leak."""
    clear_sensitive_secret_values()
    configure_structlog()

    # 1. Verify `sk-orcia-local` default was removed from LiteLLMAdapter.__init__
    sig = inspect.signature(LiteLLMAdapter.__init__)
    assert sig.parameters["api_key"].default is None
    litellm_src = Path(
        "packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py"
    ).read_text(encoding="utf-8")
    assert "sk-orcia-local" not in litellm_src

    # 2. Store canary secret under Workspace DEK and rotate DEK (SEC-03)
    canary = "CANARY_SECRET_ORCIA_99887766_ULTRA_SENSITIVE"
    secret_provider = EnvelopeVaultSecretProvider(kek_key_id="vault://kms/kek/orcia-prod-v1")
    secret_ref = SecretRef(
        uri="secret://workspace/ws-payment/litellm-api-key",
        workspace_id="ws-payment",
    )
    assert canary not in repr(secret_ref)
    assert canary not in str(secret_ref)
    assert canary not in str(secret_ref.to_dict())

    stored_ref = secret_provider.store_secret(secret_ref, canary, actor_id="karim")
    rotated_dek = secret_provider.rotate_workspace_dek("ws-payment", actor_id="karim")
    assert rotated_dek.dek_version == "v2"
    assert secret_provider.resolve_secret(stored_ref) == canary
    assert len(secret_provider.list_rotation_audit_entries()) >= 1

    # 3. Call LiteLLMAdapter through ConnectorInvoker with 429 Retry-After -> 200 OK
    attempts = 0
    waits: list[float] = []

    def gateway_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        assert request.headers["Authorization"] == f"Bearer {canary}"
        if attempts == 1:
            return httpx.Response(
                429, headers={"Retry-After": "0.25"}, json={"error": "rate_limit"}
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Évaluation orthogonale réussie."}}],
                "usage": {"prompt_tokens": 32, "completion_tokens": 16},
            },
        )

    invoker = ConnectorInvoker(sleep_fn=lambda s: waits.append(s))
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(gateway_handler))
    adapter = LiteLLMAdapter(
        base_url="http://litellm:4000/v1",
        api_key_ref=stored_ref,
        secret_provider=secret_provider,
        connector_invoker=invoker,
        http_client=http_client,
    )

    resp = await adapter.complete(
        LlmPromptRequest(
            system_prompt="Evaluator",
            user_prompt="Check artifact",
            model_family="google",
            model_id="google/gemini-2.5-pro",
            executor_model_family="anthropic",
        )
    )
    await http_client.aclose()

    assert resp.content == "Évaluation orthogonale réussie."
    assert attempts == 2
    assert waits == [0.25]
    assert adapter.last_invocation_outcome is not None
    assert adapter.last_invocation_outcome.status == "SUCCEEDED"

    # Emit a structlog message intentionally containing the canary to test masking processor
    get_logger("orcia.test.canary").info(
        "test.canary.log",
        api_key=canary,
        message=f"Tentative avec {canary} dans le message",
    )
    captured_logs = capsys.readouterr().out.splitlines()

    # Simulate DBOS step I/O, audit_ledger, domain_events_outbox, and step_executions payloads
    dbos_payloads = [
        adapter.last_invocation_outcome.sanitized_input,
        adapter.last_invocation_outcome.sanitized_output,
        stored_ref.to_dict(),
    ]
    audit_entries = [scrub_sensitive_dict({"actor": "karim", "auth": f"Bearer {canary}"})]
    outbox_events = [scrub_sensitive_dict({"event_type": "GateEvaluated", "note": canary})]
    step_executions = [scrub_sensitive_dict({"step_key": "step-1", "secret_ref": str(stored_ref)})]

    report = verify_canary_secret_absence(
        canary,
        dbos_payloads=dbos_payloads,
        audit_entries=audit_entries,
        outbox_events=outbox_events,
        step_executions=step_executions,
        log_lines=captured_logs,
    )
    assert report.passed is True
    assert report.leaked_in_dbos is False
    assert report.leaked_in_audit_ledger is False
    assert report.leaked_in_domain_events_outbox is False
    assert report.leaked_in_step_executions is False
    assert report.leaked_in_structlog is False


def test_api_agentic_gate_endpoint_and_observer_guard() -> None:
    """Verify `POST /api/v1/gates/agentic/evaluate` endpoint, orthogonality 422, observer 403."""
    app = create_app()
    client = TestClient(app)

    ws_id = "0192c4e0-0000-7000-8000-000000000201"

    # 1. READ_ONLY_OBSERVER (`claire`) is rejected with 403 ERR_OBSERVER_MODE_READ_ONLY
    obs_resp = client.post(
        "/api/v1/gates/agentic/evaluate?persona_key=claire",
        json={
            "workspace_id": ws_id,
            "run_id": "run-api-402",
            "step_execution_id": "step-exec-api-1",
            "step_key": "step-2",
            "executor_model_family": "anthropic",
            "evaluator_model_family": "google",
            "candidate_artifact": {"summary": "Test"},
        },
    )
    assert obs_resp.status_code == 403
    assert obs_resp.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # 2. Same model family is rejected with 422 ERR_MODEL_ORTHOGONALITY_VIOLATED
    orth_resp = client.post(
        "/api/v1/gates/agentic/evaluate?persona_key=marc",
        json={
            "workspace_id": ws_id,
            "run_id": "run-api-402",
            "step_execution_id": "step-exec-api-1",
            "step_key": "step-2",
            "executor_model_family": "anthropic",
            "evaluator_model_family": "anthropic",
            "candidate_artifact": {"summary": "Test"},
        },
    )
    assert orth_resp.status_code == 422
    assert orth_resp.json()["error_code"] == "ERR_MODEL_ORTHOGONALITY_VIOLATION"

    # 3. Valid orthogonal evaluation passes and returns 5 lenses + 4-block briefing
    ok_resp = client.post(
        "/api/v1/gates/agentic/evaluate?persona_key=marc",
        json={
            "workspace_id": ws_id,
            "run_id": "run-api-402",
            "step_execution_id": "step-exec-api-1",
            "step_key": "step-2",
            "executor_model_family": "anthropic",
            "evaluator_model_family": "google",
            "data_classification": "SENSITIVE",
            "candidate_artifact": {
                "summary": "<thinking>CoT</thinking> Artefact conforme pour marc@orcia.io.",
            },
            "step1_prd_invariants": ["require:conforme"],
        },
    )
    assert ok_resp.status_code == 200
    body = ok_resp.json()
    assert body["evaluation"]["status"] == "PASS"
    assert body["routed_to_local_sovereign_model"] is True
    assert body["cot_items_purged"] == 1
    assert body["pii_tokens_redacted"] >= 1
    assert "marc@orcia.io" in body["rehydrated_summary"]
    assert len(body["lens_results"]) == 5
    assert "executive_summary" in body["briefing_4blocks"]
