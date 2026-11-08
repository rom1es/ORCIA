"""TEST-08 — Eval « Golden Dataset » des citations `[S1]/[G1]/[O1]` (couche 4 `AD-17`).

Zéro appel LLM externe (`0 $`) : service de vérification déterministe.
Seuils bloquants :
- 0 citation fantôme conservée dans le texte assaini ;
- 100 % des citations valides conservées ;
- 100 % des citations fantômes détectées.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
    RawGlossaryCandidate,
    RawSourceCandidate,
    RawToolOutputCandidate,
)

GOLDEN_PATH = Path(__file__).parent / "golden" / "citations.jsonl"
TAG_RE = re.compile(r"\[([SGO]\d+)\]")


def _load_cases() -> list[dict[str, object]]:
    return [
        json.loads(line) for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines() if line
    ]


def _service_and_table():  # type: ignore[no-untyped-def]
    svc = AssistantCitationAndV5GuardService()
    table = svc.build_evidence_table(
        sources=(
            RawSourceCandidate(
                uri="git://claims/adr-reference",
                title="ADR Reference",
                authority_tier="REFERENCE",
                freshness="FRESH",
                snippet="ADR officiel",
            ),
            RawSourceCandidate(
                uri="confluence://claims/active-note",
                title="Note Active",
                authority_tier="ACTIVE",
                freshness="FRESH",
                snippet="Note active",
            ),
        ),
        glossary_items=(
            RawGlossaryCandidate(
                term_or_axiom_id="term-1",
                label="Terme",
                ontology_level="L4_GLOSSARY",
                definition="Définition du terme.",
            ),
        ),
        tool_outputs=(
            RawToolOutputCandidate(
                tool_name="jira.search", connector_uri="jira://claims", summary="3 tickets"
            ),
        ),
    )
    return svc, table


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: str(c["id"]))
def test_golden_case_keeps_valid_and_strips_phantom_citations(case: dict[str, object]) -> None:
    svc, table = _service_and_table()
    result = svc.verify_and_sanitize_citations(
        response_text=str(case["text"]),
        evidence_table=table,
        workspace_id="0192c4e0-0000-7000-8000-000000001030",
        user_id="u-eval-01",
    )
    kept = sorted(TAG_RE.findall(result.sanitized_text))
    assert kept == sorted(case["expect_kept"]), f"citations conservées inattendues: {kept}"  # type: ignore[arg-type]
    assert sorted(result.stripped_phantom_tags) == sorted(case["expect_stripped"])  # type: ignore[arg-type]


def test_golden_dataset_thresholds_zero_phantom_leak() -> None:
    cases = _load_cases()
    assert len(cases) >= 6, "jeu doré minimal"
    leaked = 0
    for case in cases:
        svc, table = _service_and_table()
        result = svc.verify_and_sanitize_citations(
            response_text=str(case["text"]),
            evidence_table=table,
            workspace_id="0192c4e0-0000-7000-8000-000000001030",
            user_id="u-eval-01",
        )
        leaked += len(set(TAG_RE.findall(result.sanitized_text)) & set(case["expect_stripped"]))  # type: ignore[arg-type]
    assert leaked == 0
