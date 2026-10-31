"""Unit & API contract tests for Story 11.2 (DNA Chain, Starlark Sandbox, 2-Pass Glossary V4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.gates import StarlarkMechanismSandbox, StarlarkSandboxError
from orcia_core.orchestration.dna_starlark_and_glossary_lifecycle import (
    DnaStarlarkAndGlossaryLifecycleService,
)


def test_starlark_sandbox_determinism_redos_and_staged_effects() -> None:
    """Verify `StarlarkMechanismSandbox` (`< 2 ms`, anti-ReDoS $O(n)$, forbidden AST & Staged)."""
    sandbox = StarlarkMechanismSandbox(max_steps=50)
    script = (
        "def evaluate(doc):\n"
        "    code = str(doc.get('code', ''))\n"
        "    if orcia_sys.re_fullmatch(r'^[A-Z]{3}-[0-9]{2}$', code):\n"
        "        orcia_sys.emit_verdict('RULE_CODE', 'PASS', 'Format valide')\n"
        "    else:\n"
        "        orcia_sys.emit_verdict('RULE_CODE', 'FAIL', 'Format invalide')\n"
        "        orcia_sys.emit_effect('STAGE_COMMENT', 'orcia://staged/1', {'code': code})\n"
    )
    res_pass = sandbox.evaluate_script(starlark_code=script, payload={"code": "ABC-42"})
    assert res_pass.passed is True
    assert res_pass.llm_tokens_consumed == 0
    assert res_pass.elapsed_ms < 20.0

    res_fail = sandbox.evaluate_script(starlark_code=script, payload={"code": "bad"})
    assert res_fail.passed is False
    assert len(res_fail.staged_effects) == 1
    assert res_fail.staged_effects[0].staged_only is True

    # Reject catastrophic ReDoS regex pattern (a+)+$
    bad_redos_script = (
        "def evaluate(doc):\n"
        "    orcia_sys.re_fullmatch(r'(a+)+$', 'aaaa')\n"
        "    orcia_sys.emit_verdict('R1', 'PASS', 'ok')\n"
    )
    with pytest.raises(StarlarkSandboxError, match="RE2 linear-time"):
        sandbox.evaluate_script(starlark_code=bad_redos_script, payload={})

    # Reject forbidden non-deterministic imports / while loops
    with pytest.raises(StarlarkSandboxError, match="Forbidden non-deterministic"):
        sandbox.evaluate_script(starlark_code="import os\n", payload={})


def test_text_to_starlark_compiler_self_correction_and_breadcrumb() -> None:
    """Verify `compile_from_natural_language` auto-test (`PASS`/`FAIL`), self-correction & DNA."""
    svc = DnaStarlarkAndGlossaryLifecycleService()
    mech = svc.compile_from_natural_language(
        actor_role="TEAM_LEAD",
        rule_id="RULE_TICKET_KEY",
        directive_title="ISO-25010 Traçabilité",
        norm_title="Format Clé Ticket",
        natural_language_rule_fr="Toute clé de ticket doit respecter ^[A-Z0-9_-]{3,64}$",
        target_json_schema={"required": ["ticket_key"]},
        required_field="ticket_key",
        simulate_initial_bad_regex=True,
    )
    assert mech.self_corrected is True
    assert mech.signed_and_active is True
    assert "🛡️ [ISO-25010 Traçabilité] ➔ 📏 [Format Clé Ticket]" in mech.causal_breadcrumb
    assert mech.script_name == "rule-ticket-key.star"

    runtime_res = svc.evaluate_runtime_mechanism(
        mechanism_id=mech.mechanism_id,
        payload={"ticket_key": "ORCIA_11_2"},
    )
    assert runtime_res.passed is True
    assert runtime_res.llm_tokens_consumed == 0


def test_two_pass_glossary_extractor_verrou_v4_fifo_and_in_flow_promotion() -> None:
    """Verify Pass 1 (`0 $` on `git_push`), Pass 2 FIFO `<= 15`, `Top-3` pre-checked & promotion."""
    svc = DnaStarlarkAndGlossaryLifecycleService()
    ws_id = uuid4()
    now = datetime.now(UTC)

    # Pass 1 on git_push: 0 LLM calls, no pre-checked items
    res_push = svc.extract_glossary_candidates_two_pass(
        workspace_id=ws_id,
        trigger_type="git_push",
        raw_candidates=[("Terme Git Push", "Définition déterministe AST", 0.92)],
        now=now - timedelta(days=35),
    )
    assert res_push.pass_1_deterministic_executed is True
    assert res_push.pass_2_llm_batch_executed is False
    assert res_push.llm_calls_count == 0
    assert len(res_push.top3_in_flow_prechecked) == 0

    # 35 days later on human_gate: expired >30d purged, FIFO capped at 15, Top-3 pre-checked
    twenty_candidates = [
        (f"Terme Métier {i:02d}", f"Définition consolidée {i}", 0.70 + (i * 0.014))
        for i in range(20)
    ]
    res_gate = svc.extract_glossary_candidates_two_pass(
        workspace_id=ws_id,
        trigger_type="human_gate",
        raw_candidates=twenty_candidates,
        existing_enterprise_terms={"Terme Métier 19": "Définition Entreprise Officielle"},
        now=now,
    )
    assert res_gate.purged_expired_ephemeral_count == 1
    assert res_gate.pass_2_llm_batch_executed is True
    assert res_gate.llm_calls_count == 1
    assert len(res_gate.active_queue_candidates) == 15
    assert len(res_gate.top3_in_flow_prechecked) == 3
    assert all(c.pre_checked_for_in_flow_promotion for c in res_gate.top3_in_flow_prechecked)

    # Promote Top-3 and reject 1 candidate
    promote_ids = [c.candidate_id for c in res_gate.top3_in_flow_prechecked]
    reject_id = res_gate.active_queue_candidates[-1].candidate_id
    rejected_term = res_gate.active_queue_candidates[-1].canonical_term

    promo = svc.promote_or_reject_in_flow(
        workspace_id=ws_id,
        actor_role="TEAM_LEAD",
        promote_candidate_ids=promote_ids,
        reject_candidate_ids=[reject_id],
    )
    assert len(promo.promoted_terms) == 3
    assert promo.rejected_terms == (rejected_term,)
    assert promo.assistant_prompt_cache_invalidated is True

    # Re-submitting the rejected term in Pass 1 must be ignored (REJECTED_CANDIDATE fingerprint)
    res_after = svc.extract_glossary_candidates_two_pass(
        workspace_id=ws_id,
        trigger_type="git_push",
        raw_candidates=[(rejected_term, "Nouvelle tentative", 0.99)],
        now=now,
    )
    assert all(c.canonical_term != rejected_term for c in res_after.active_queue_candidates)


def test_story_11_2_fastapi_endpoints() -> None:
    """Verify Story 11.2 FastAPI endpoints (`/dna-mechanisms/compile` & `/extract-two-pass`)."""
    client = TestClient(create_app())
    ws_id = str(uuid4())

    resp_compile = client.post(
        f"/api/v1/workspaces/{ws_id}/dna-mechanisms/compile",
        params={"persona_key": "claire"},
        json={
            "rule_id": "RULE_RGPD_REF",
            "directive_title": "RGPD Art.32",
            "norm_title": "Référence Dossier",
            "natural_language_rule_fr": "La référence dossier doit être alphanumérique majuscule.",
            "target_json_schema": {"required": ["dossier_ref"]},
            "required_field": "dossier_ref",
        },
    )
    assert resp_compile.status_code == 200
    mech_id = resp_compile.json()["mechanism_id"]

    resp_eval = client.post(
        f"/api/v1/workspaces/{ws_id}/dna-mechanisms/{mech_id}/evaluate",
        params={"persona_key": "claire"},
        json={"payload": {"dossier_ref": "DOS_2026_01"}},
    )
    assert resp_eval.status_code == 200
    assert resp_eval.json()["passed"] is True
    assert resp_eval.json()["llm_tokens_consumed"] == 0

    resp_ext = client.post(
        f"/api/v1/workspaces/{ws_id}/glossary/extract-two-pass",
        params={"persona_key": "claire"},
        json={
            "trigger_type": "mr_pr",
            "raw_candidates": [
                {
                    "canonical_term": "Sinistre Majeur",
                    "definition_fr": "Sinistre dépassant le seuil de réassurance.",
                    "confidence_score": 0.93,
                }
            ],
        },
    )
    assert resp_ext.status_code == 200
    assert len(resp_ext.json()["top3_in_flow_prechecked"]) == 1
