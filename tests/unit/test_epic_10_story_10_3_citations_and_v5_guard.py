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
    assert len(svc.phantom_audit_log) == 1

    # Allowed Artifact Card actions: SAVE_DRAFT (@draft) and CONTINUE_IN_PROCESS
    draft = svc.execute_artifact_card_action(
        claire,
        workspace_id="ws-claims-alpha",
        action_type="SAVE_DRAFT",
        artifact_title="Note de cadrage Sinistres",
        artifact_content="# Cadrage [S1]",
        cited_tags=("S1", "G1"),
    )
    assert draft.artifact_version_tag == "@draft"
    assert draft.draft_uri is not None and draft.draft_uri.endswith("@draft")

    cont = svc.execute_artifact_card_action(
        claire,
        workspace_id="ws-claims-alpha",
        action_type="CONTINUE_IN_PROCESS",
        artifact_title="Note de cadrage Sinistres",
        artifact_content="# Cadrage [S1]",
        cited_tags=("S1", "G1"),
    )
    assert cont.process_launch_prefill["preserved_evidence_tags"] == ["S1", "G1"]

    # Verrou V5 (AD-15): Direct SI write or @v1 Vault officialization -> 422
    with pytest.raises(DirectSiWriteRequiresProcessGateError) as exc1:
        svc.execute_artifact_card_action(
            claire,
            workspace_id="ws-claims-alpha",
            action_type="DIRECT_SI_WRITE",
            artifact_title="Note",
            artifact_content="Contenu",
            target_uri="git://repo-core/docs/spec.md",
        )
    assert exc1.value.error_code == "ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE"

    with pytest.raises(DirectSiWriteRequiresProcessGateError) as exc2:
        svc.execute_artifact_card_action(
            claire,
            workspace_id="ws-claims-alpha",
            action_type="PUBLISH_V1_VAULT",
            artifact_title="Note",
            artifact_content="Contenu",
        )
    assert exc2.value.error_code == "ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE"


def test_story_10_3_api_endpoints_verify_citations_and_v5_guard() -> None:
    """Verify `/api/v1/assistant/citations/verify-turn` and `/artifacts/action` (`Story 10.3`)."""
    with TestClient(app) as client:
        v_resp = client.post(
            "/api/v1/assistant/citations/verify-turn",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "response_text": "Conformément à [S1] et [S99].",
                "sources": [
                    {
                        "uri": "git://repo-core/docs/adr-015.md",
                        "title": "ADR-015",
                        "authority_tier": "REFERENCE",
                        "freshness": "FRESH",
                        "snippet": "Extrait confidentiel ADR-015",
                    }
                ],
                "reader_allowed_source_uris": [],
            },
        )
        assert v_resp.status_code == 200
        v_data = v_resp.json()
        assert "[Citation non vérifiée]" in v_data["sanitized_text"]
        assert v_data["stripped_phantom_tags"] == ["S99"]
        assert v_data["sources"][0]["restricted_access"] is True
        assert v_data["sources"][0]["snippet"] is None
        assert (
            v_data["sources"][0]["display_pill"] == "[S1 · 🔒 Source restreinte — Demander l'accès]"
        )

        # Verrou V5 via API -> HTTP 422 ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE
        bad_act = client.post(
            "/api/v1/assistant/artifacts/action",
            params={"persona_key": "claire"},
            json={
                "workspace_id": "ws-claims-alpha",
                "action_type": "DIRECT_SI_WRITE",
                "artifact_title": "Spec directe",
                "artifact_content": "# Spec",
                "target_uri": "confluence://space/page-1",
            },
        )
        assert bad_act.status_code == 422
        assert bad_act.json()["error_code"] == "ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE"
