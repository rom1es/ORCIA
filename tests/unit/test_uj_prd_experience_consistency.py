"""Cross-artifact consistency tests for User Journeys across PRD, Experience, and Registry."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[2]
PRD_PATH = REPO_ROOT / "docs" / "planning-artifacts" / "prds" / "prd-ORCIA-2026-10-24" / "prd.md"
EXPERIENCE_PATH = (
    REPO_ROOT
    / "docs"
    / "planning-artifacts"
    / "ux-designs"
    / "ux-ORCIA-2026-10-24"
    / "EXPERIENCE.md"
)
REGISTRY_PATH = REPO_ROOT / "docs" / "product" / "capabilities.yaml"

EXPECTED_UJ_NUMBERS = list(range(1, 21))
EXPECTED_UJ_IDS = [f"UJ-{num}" for num in EXPECTED_UJ_NUMBERS]
EXPECTED_FR_IDS = [f"FR-{num}" for num in range(1, 37)]
UJ_TOKEN_RE = re.compile(r"\bUJ-([1-9]\d?)\b")


def _extract_prd_user_journey_headings(prd_text: str) -> list[str]:
    return re.findall(r"^#### (UJ-\d+)\.", prd_text, flags=re.MULTILINE)


def _extract_prd_fr_blocks(prd_text: str) -> dict[str, str]:
    fr_matches = list(re.finditer(r"^#### (FR-\d+)\s*:", prd_text, flags=re.MULTILINE))
    section_boundaries = [
        m.start() for m in re.finditer(r"^#{2,4}\s+", prd_text, flags=re.MULTILINE)
    ]
    blocks: dict[str, str] = {}
    for match in fr_matches:
        start = match.start()
        next_starts = [pos for pos in section_boundaries if pos > start]
        end = next_starts[0] if next_starts else len(prd_text)
        blocks[match.group(1)] = prd_text[start:end]
    return blocks


def _extract_experience_key_flows_body(experience_text: str) -> str:
    heading_match = re.search(r"^## 9\. Key Flows[^\n]*\n", experience_text, flags=re.MULTILINE)
    assert heading_match is not None, "Section `## 9. Key Flows` absente dans EXPERIENCE.md"
    body_start = heading_match.end()
    next_h2 = re.search(r"^## \d+\.", experience_text[body_start:], flags=re.MULTILINE)
    body_end = body_start + next_h2.start() if next_h2 is not None else len(experience_text)
    return experience_text[body_start:body_end]


def _load_registry_feature_ujs() -> tuple[set[str], dict[str, list[str]]]:
    data: dict[str, Any] = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    all_ujs: set[str] = set()
    by_uj: dict[str, list[str]] = {}
    for cap in data.get("capabilities", []):
        if not isinstance(cap, dict):
            continue
        cap_id = str(cap.get("id", ""))
        ujs = cap.get("uj")
        if isinstance(ujs, list):
            for uj in ujs:
                if isinstance(uj, str):
                    all_ujs.add(uj)
                    if cap.get("kind") == "feature":
                        by_uj.setdefault(uj, []).append(cap_id)
    return all_ujs, by_uj


def test_prd_defines_contiguous_user_journey_headings() -> None:
    prd_text = PRD_PATH.read_text(encoding="utf-8")
    found_headings = _extract_prd_user_journey_headings(prd_text)
    assert found_headings == EXPECTED_UJ_IDS, f"Attendu {EXPECTED_UJ_IDS}, trouvé {found_headings}"


def test_prd_functional_requirements_reference_user_journeys() -> None:
    prd_text = PRD_PATH.read_text(encoding="utf-8")
    fr_blocks = _extract_prd_fr_blocks(prd_text)
    assert list(fr_blocks.keys()) == EXPECTED_FR_IDS, (
        f"FR manquantes ou désordonnées : {list(fr_blocks.keys())}"
    )

    missing_uj_refs: list[str] = []
    invalid_uj_refs: list[str] = []
    valid_ujs = set(EXPECTED_UJ_IDS)

    for fr_id, block in fr_blocks.items():
        refs = [f"UJ-{num}" for num in UJ_TOKEN_RE.findall(block)]
        if not refs:
            missing_uj_refs.append(fr_id)
        unknown = sorted(set(refs) - valid_ujs)
        if unknown:
            invalid_uj_refs.append(f"{fr_id}: {unknown}")

    assert not missing_uj_refs, f"Exigences sans référence UJ-* : {missing_uj_refs}"
    assert not invalid_uj_refs, f"Références UJ-* inconnues dans le PRD : {invalid_uj_refs}"


def test_experience_key_flows_cover_all_user_journeys() -> None:
    experience_text = EXPERIENCE_PATH.read_text(encoding="utf-8")
    flows_body = _extract_experience_key_flows_body(experience_text)
    flow_headings = re.findall(r"^### Flow \d+\b", flows_body, flags=re.MULTILINE)
    assert len(flow_headings) >= 11, f"Nombre de Flows insuffisant en §9 : {len(flow_headings)}"

    covered_ujs = {f"UJ-{num}" for num in UJ_TOKEN_RE.findall(flows_body)}
    missing_in_experience = [uj for uj in EXPECTED_UJ_IDS if uj not in covered_ujs]
    unknown_in_experience = sorted(covered_ujs - set(EXPECTED_UJ_IDS))

    assert not missing_in_experience, (
        f"User Journeys absents de EXPERIENCE.md §9 : {missing_in_experience}"
    )
    assert not unknown_in_experience, (
        f"User Journeys inconnus dans EXPERIENCE.md §9 : {unknown_in_experience}"
    )


def test_capabilities_registry_user_journeys_align_with_prd_and_experience() -> None:
    prd_ujs = set(_extract_prd_user_journey_headings(PRD_PATH.read_text(encoding="utf-8")))
    experience_flows_body = _extract_experience_key_flows_body(
        EXPERIENCE_PATH.read_text(encoding="utf-8")
    )
    experience_ujs = {f"UJ-{num}" for num in UJ_TOKEN_RE.findall(experience_flows_body)}
    registry_all_ujs, feature_caps_by_uj = _load_registry_feature_ujs()

    missing_from_prd = sorted(registry_all_ujs - prd_ujs)
    missing_from_experience = sorted(registry_all_ujs - experience_ujs)
    ujs_without_feature_cap = [uj for uj in EXPECTED_UJ_IDS if not feature_caps_by_uj.get(uj)]

    assert not missing_from_prd, f"UJ du registre absents de prd.md : {missing_from_prd}"
    assert not missing_from_experience, (
        f"UJ du registre absents de EXPERIENCE.md §9 : {missing_from_experience}"
    )
    assert not ujs_without_feature_cap, (
        f"User Journeys sans capacité `kind: feature` : {ujs_without_feature_cap}"
    )
