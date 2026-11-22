"""Story 10.3 — Unit & API tests for `[S1]/[G1]/[O1]` Citations, `READ_SOURCE` & Verrou V5.

Validates:
- Numbered Evidence Table (`[S1..Sn]`, `[G1..Gn]`, `[O1..On]`) where `REFERENCE` strictly
  outranks `ACTIVE`, plus freshness (`FRESH` / `STALE_WARNING`).
- Dynamic per-reader `READ_SOURCE` filtering (`AD-21`): purges `snippet = None` server-side and
  returns `[S1 · 🔒 Source restreinte — Demander l'accès]`.
- `< 5 ms` post-stream anti-phantom citation verifier replacing out-of-bounds `[S99]` with
  `[Citation non vérifiée]` and appending an audit entry.
- **Verrou V5 (`AD-15`)**: rejects direct SI writes (`git://`, `confluence://`, `jira://`) or
  `@v1` Vault officialization from `Mon Assistant` with
  `HTTP 422 ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE` (`DirectSiWriteRequiresProcessGateError`).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import app
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    UNVERIFIED_CITATION_BADGE,
    AssistantCitationAndV5GuardService,
    RawGlossaryCandidate,
    RawSourceCandidate,
    RawToolOutputCandidate,
)
from orcia_core.orchestration.errors import DirectSiWriteRequiresProcessGateError
from orcia_core.permissions.models import PlatformRole, UserIdentity


def _make_user(
    *,
    user_id: str = "u-claire-01",
    role: PlatformRole = "CONTRIBUTOR",
    archetype: str = "PM",
) -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=f"{user_id}@orcia.local",
        display_name=user_id,
        auth_mode="LOCAL",
        human_profile_archetype=archetype,
        platform_role=role,
        primary_org_unit_id="org-unit-alpha",
    )


def test_story_10_3_evidence_table_priority_and_reader_filtering() -> None:
    """Verify `REFERENCE > ACTIVE` ordering and `READ_SOURCE` server-side snippet purge."""
    svc = AssistantCitationAndV5GuardService()
    table = svc.build_evidence_table(
        sources=(
            RawSourceCandidate(
                uri="confluence://kb/draft-notes",
                title="Notes de réunion sprint",
                authority_tier="ACTIVE",
                freshness="STALE_WARNING",
                snippet="Extrait actif potentiellement obsolète.",
                relevance_score=0.95,
            ),
            RawSourceCandidate(
                uri="git://repo-core/docs/adr-015.md",
                title="ADR-015 Architecture de Référence",
                authority_tier="REFERENCE",
                freshness="FRESH",
                snippet="Extrait officiel de référence ADR-015.",
                relevance_score=0.80,
            ),
        ),
        glossary_items=(
            RawGlossaryCandidate(
                term_or_axiom_id="ax-n1-01",
                label="Souveraineté des Gates",
                ontology_level="N1_DIRECTIVE",
                definition="Toute écriture SI passe par une Gate.",
            ),
        ),
        tool_outputs=(
            RawToolOutputCandidate(
                tool_name="jira.search_issues",
                connector_uri="jira://claims/ORCIA-103",
                summary="Ticket ORCIA-103 en cours.",
            ),
        ),
    )

    # REFERENCE source is ranked [S1] ahead of ACTIVE source [S2] despite lower relevance_score
    assert table.sources[0].tag == "S1"
    assert table.sources[0].authority_tier == "REFERENCE"
    assert table.sources[0].uri == "git://repo-core/docs/adr-015.md"
    assert table.sources[1].tag == "S2"
    assert table.sources[1].authority_tier == "ACTIVE"
    assert table.glossary_items[0].tag == "G1"
    assert table.tool_outputs[0].tag == "O1"
    assert "📚 2 sources consultées ([S1]..[S2]) · 1 termes du Glossaire ([G1]) ▾" in (
        table.footer_summary_line
    )

    # Reader lacking READ_SOURCE on S1 gets snippet=None and restricted pill
    reader = _make_user(user_id="u-partenaire", role="CONTRIBUTOR")
    filtered = svc.filter_citation_map_for_reader(
        reader,
        evidence_table=table,
        reader_allowed_source_uris=frozenset({"confluence://kb/draft-notes"}),
    )
    assert filtered.sources[0].restricted_access is True
    assert filtered.sources[0].snippet is None
    assert filtered.sources[0].display_pill == "[S1 · 🔒 Source restreinte — Demander l'accès]"
    assert filtered.sources[1].restricted_access is False
    assert filtered.sources[1].snippet is not None


def test_story_10_3_phantom_citation_verifier_and_v5_lock() -> None:
    """Verify `< 5 ms` phantom citation stripping and Verrou V5 (`AD-15`) enforcement."""
    svc = AssistantCitationAndV5GuardService()
    claire = _make_user(user_id="u-claire-01", role="CONTRIBUTOR")
    table = svc.build_evidence_table(
        sources=(
            RawSourceCandidate(
                uri="git://repo-core/docs/adr-015.md",
                title="ADR-015",
                authority_tier="REFERENCE",
                freshness="FRESH",
                snippet="Texte ADR-015",
            ),
        ),
        glossary_items=(
            RawGlossaryCandidate(
                term_or_axiom_id="g-1",
                label="Verrou V5",
                ontology_level="N2_NORME",
                definition="Pas de publication directe depuis l'assistant.",
            ),
        ),
    )

    # [S1] and [G1] are valid; [S99] and [O4] are phantom citations -> replaced in < 5 ms
    raw_text = "Selon l'ADR [S1] et la norme [G1], le module [S99] et l'outil [O4] s'appliquent."
    res = svc.verify_and_sanitize_citations(
        response_text=raw_text,
        evidence_table=table,
        workspace_id="ws-claims-alpha",
        user_id=claire.id,
    )
    assert res.verification_duration_ms < 5.0
    assert res.valid_tags == ("S1", "G1")
    assert res.stripped_phantom_tags == ("S99", "O4")
    assert UNVERIFIED_CITATION_BADGE in res.sanitized_text
    assert "[S99]" not in res.sanitized_text
    assert res.audit_entry is not None
    assert res.audit_entry.stripped_tags == ("S99", "O4")

    # R5: _saved_drafts & execute_artifact_card_action removed; V5 guard in AssistantTurnEngine
    assert not hasattr(svc, "execute_artifact_card_action")
    assert not hasattr(svc, "_saved_drafts")
    from orcia_core.orchestration.assistant_turn_engine import AssistantTurnEngine

    engine = AssistantTurnEngine(citation_guard=svc)
    with pytest.raises(DirectSiWriteRequiresProcessGateError) as exc1:
        engine.n1_intent_guard(
            claire,
            user_prompt="Écris directement",
            requested_write_target_uri="git://repo-core/docs/spec.md",
        )
    assert exc1.value.error_code == "ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE"


def test_story_10_3_api_endpoints_verify_citations_and_v5_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify legacy `/citations/verify-turn` & `/artifacts/action` are deleted & Lock V5 holds."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    with TestClient(app) as client:
        for legacy_path in (
            "/api/v1/assistant/citations/verify-turn",
            "/api/v1/assistant/artifacts/action",
        ):
            assert client.post(
                legacy_path, params={"persona_key": "nadia"}, json={"workspace_id": ws_id}
            ).status_code in (404, 405)

        turn_res = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "marc"},
            json={"workspace_id": ws_id, "user_prompt": "Vérifie le statut"},
        )
        assert turn_res.status_code == 202
        turn_id = turn_res.json()["turn_id"]

        bad_approve = client.post(
            f"/api/v1/assistant/turns/{turn_id}/approve",
            params={"persona_key": "marc"},
            json={
                "workspace_id": ws_id,
                "proposal_id": "prop-v5",
                "approved": True,
                "human_authored_required": True,
            },
        )
        assert bad_approve.status_code == 422
        assert bad_approve.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"
