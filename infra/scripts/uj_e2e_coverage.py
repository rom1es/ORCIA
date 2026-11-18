"""Validation croisée User Journeys (`prd.md`) ↔ Capacités (`capabilities.yaml`) ↔ Specs E2E."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PRD_PATH = REPO_ROOT / "docs" / "planning-artifacts" / "prds" / "prd-ORCIA-2026-10-24" / "prd.md"
E2E_DIR = REPO_ROOT / "apps" / "web" / "e2e"
PLAYWRIGHT_RESULTS_PATH = (
    REPO_ROOT
    / "docs"
    / "implementation-artifacts"
    / "e2e-campaign-epic-21"
    / "playwright-results.json"
)
VALID_E2E_BACKLOG_STORIES = {"21-5", "21-6", "21-7"}
SMOKE_ONLY_SPEC_PREFIXES = ("11-",)
_PRD_UJ_HEADING_RE = re.compile(r"^#### (UJ-[1-9]\d?)\.", re.MULTILINE)
_UJ_TOKEN_RE = re.compile(r"\bUJ-[1-9]\d?\b")
_CAP_TOKEN_RE = re.compile(r"\bCAP-\d+\b")
_FAILED_TEST_STATUSES = {"failed", "timedOut", "interrupted"}


def extract_prd_user_journeys(prd_path: Path = PRD_PATH) -> list[str]:
    """Return ordered User Journey IDs (`#### UJ-N.`) defined in `prd.md`."""
    if not prd_path.exists():
        return []
    return list(dict.fromkeys(_PRD_UJ_HEADING_RE.findall(prd_path.read_text(encoding="utf-8"))))


def is_functional_e2e_spec(test_path: str) -> bool:
    """Return True if `test_path` is a functional Playwright E2E spec (excluding `11-*` smoke)."""
    path = Path(test_path.replace("\\", "/").strip())
    return (
        path.parent.as_posix() == "apps/web/e2e"
        and path.name.endswith(".spec.ts")
        and not path.name.startswith(SMOKE_ONLY_SPEC_PREFIXES)
    )


def _extract_tag_tokens(head_text: str, tag: str, token_re: re.Pattern[str]) -> list[str]:
    pattern = re.compile(rf"@{tag}\s+([^|\n*]+)")
    tokens = [tok for m in pattern.finditer(head_text) for tok in token_re.findall(m.group(1))]
    return list(dict.fromkeys(tokens))


def parse_e2e_spec_headers(e2e_dir: Path = E2E_DIR) -> dict[str, dict[str, Any]]:
    """Parse `/** @uj ... | @cap ... */` metadata headers across `apps/web/e2e/*.spec.ts`."""
    if not e2e_dir.exists():
        return {}
    headers: dict[str, dict[str, Any]] = {}
    for spec_file in sorted(e2e_dir.glob("*.spec.ts")):
        head_text = "\n".join(spec_file.read_text(encoding="utf-8").splitlines()[:40])
        rel_path = f"apps/web/e2e/{spec_file.name}"
        headers[rel_path] = {
            "ujs": _extract_tag_tokens(head_text, "uj", _UJ_TOKEN_RE),
            "caps": _extract_tag_tokens(head_text, "cap", _CAP_TOKEN_RE),
            "functional": is_functional_e2e_spec(rel_path),
        }
    return headers


def _normalize_playwright_file(raw_file: str) -> str:
    norm = raw_file.replace("\\", "/").strip()
    if norm.startswith("apps/web/e2e/"):
        return norm
    return f"apps/web/{norm}" if norm.startswith("e2e/") else f"apps/web/e2e/{Path(norm).name}"


def _walk_playwright_suites(suites: list[dict[str, Any]], failed: set[str]) -> None:
    for suite in suites:
        if not isinstance(suite, dict):
            continue
        suite_file = str(suite.get("file") or "").strip()
        for spec in suite.get("specs", []) or []:
            if not isinstance(spec, dict):
                continue
            spec_file = str(spec.get("file") or suite_file).strip()
            has_bad_test = any(
                isinstance(t, dict)
                and (
                    t.get("outcome") == "unexpected"
                    or any(
                        isinstance(r, dict) and r.get("status") in _FAILED_TEST_STATUSES
                        for r in (t.get("results") or [])
                    )
                )
                for t in (spec.get("tests") or [])
            )
            if (spec.get("ok") is False or has_bad_test) and spec_file:
                failed.add(_normalize_playwright_file(spec_file))
        if isinstance(suite.get("suites"), list):
            _walk_playwright_suites(suite["suites"], failed)


def load_failed_e2e_specs(results_path: Path = PLAYWRIGHT_RESULTS_PATH) -> set[str]:
    """Return normalized E2E spec paths marked failed in `playwright-results.json` if present."""
    if not results_path.exists():
        return set()
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("suites"), list):
        return set()
    failed: set[str] = set()
    _walk_playwright_suites(payload["suites"], failed)
    return failed


def summarize_uj_e2e_coverage(
    data: dict[str, Any], prd_path: Path = PRD_PATH, e2e_dir: Path = E2E_DIR
) -> dict[str, Any]:
    """Compute UJ and functional E2E coverage counters from registry, PRD, and spec headers."""
    prd_ujs = extract_prd_user_journeys(prd_path)
    header_caps_by_cap: dict[str, list[str]] = {}
    tagged_specs_count = 0
    for spec_path, info in parse_e2e_spec_headers(e2e_dir).items():
        if info["ujs"] or info["caps"]:
            tagged_specs_count += 1
        for cap_id in info["caps"]:
            header_caps_by_cap.setdefault(cap_id, []).append(spec_path)

    covered_ujs: set[str] = set()
    e2e_covered = 0
    backlog_exempt = 0
    live_features = 0
    for cap in data.get("capabilities", []):
        if cap.get("kind") != "feature":
            continue
        covered_ujs.update(str(uj) for uj in (cap.get("uj") or []) if uj in prd_ujs)
        if cap.get("status") != "live":
            continue
        live_features += 1
        declared_func = [t for t in (cap.get("tests") or []) if is_functional_e2e_spec(str(t))]
        cap_key = str(cap.get("id", ""))
        header_func = [p for p in header_caps_by_cap.get(cap_key, []) if is_functional_e2e_spec(p)]
        if declared_func or header_func:
            e2e_covered += 1
        elif cap.get("e2e_backlog_story") or cap.get("e2e_remediation_ref"):
            backlog_exempt += 1

    return {
        "userJourneysCount": len(prd_ujs),
        "coveredUserJourneysCount": len(covered_ujs),
        "liveFeaturesCount": live_features,
        "e2eCoveredCapabilitiesCount": e2e_covered,
        "e2eBacklogExemptCapabilitiesCount": backlog_exempt,
        "e2eHeaderTaggedSpecsCount": tagged_specs_count,
        "e2eHeaderCapsByCapId": header_caps_by_cap,
    }


def _check_feature_capability(
    cap: dict[str, Any],
    prd_uj_set: set[str],
    failed_specs: set[str],
    repo_root: Path,
    ujs_with_feature: set[str],
) -> list[str]:
    errors: list[str] = []
    cap_id = str(cap.get("id", "?"))
    for uj in cap.get("uj") or []:
        if uj not in prd_uj_set:
            errors.append(f"{cap_id}: UJ `{uj}` absent de `prd.md`")
        else:
            ujs_with_feature.add(str(uj))

    declared_tests = [str(t) for t in (cap.get("tests") or [])]
    func_specs = [
        t for t in declared_tests if is_functional_e2e_spec(t) and (repo_root / t).is_file()
    ]
    smoke_only = [
        t
        for t in declared_tests
        if t.replace("\\", "/").startswith("apps/web/e2e/") and not is_functional_e2e_spec(t)
    ]
    backlog_story, remediation_ref = cap.get("e2e_backlog_story"), cap.get("e2e_remediation_ref")
    has_backlog = backlog_story in VALID_E2E_BACKLOG_STORIES
    has_remediation = isinstance(remediation_ref, str) and bool(remediation_ref.strip())

    if backlog_story is not None and not has_backlog:
        allowed = sorted(VALID_E2E_BACKLOG_STORIES)
        errors.append(f"{cap_id}: `e2e_backlog_story` `{backlog_story}` invalide ({allowed})")
    if remediation_ref is not None and not has_remediation:
        errors.append(f"{cap_id}: `e2e_remediation_ref` doit être une chaîne non vide")

    if cap.get("status") == "live" and not func_specs and not has_backlog and not has_remediation:
        hint = f" (smoke uniquement: {', '.join(smoke_only)})" if smoke_only else ""
        errors.append(
            f"{cap_id}: capacité `live` `feature` sans spec E2E fonctionnelle (hors `11-*`)"
            f"{hint} ni `e2e_backlog_story`/`e2e_remediation_ref` valide"
        )

    if cap.get("verification") == "runtime":
        if not func_specs:
            errors.append(
                f"{cap_id}: `verification: runtime` interdit sans spec E2E fonctionnelle "
                "active dans `tests:` (hors smoke `11-*`)"
            )
        if backlog_story is not None or remediation_ref is not None:
            errors.append(
                f"{cap_id}: `verification: runtime` incompatible avec "
                "`e2e_backlog_story` ou `e2e_remediation_ref`"
            )
        failing = [spec for spec in func_specs if spec in failed_specs]
        if failing:
            errors.append(
                f"{cap_id}: `verification: runtime` interdit car spec E2E en échec dans "
                f"`playwright-results.json`: {', '.join(failing)}"
            )
    return errors


def check_uj_e2e_coverage(
    data: dict[str, Any],
    prd_path: Path = PRD_PATH,
    e2e_dir: Path = E2E_DIR,
    playwright_results_path: Path = PLAYWRIGHT_RESULTS_PATH,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    """Enforce blocking CI gates across PRD UJs, `capabilities.yaml`, and functional E2E specs."""
    prd_ujs = extract_prd_user_journeys(prd_path)
    if not prd_ujs:
        return [f"PRD introuvable ou aucun User Journey `#### UJ-N.` défini dans {prd_path}"]
    prd_uj_set = set(prd_ujs)
    ujs_with_feature: set[str] = set()
    failed_specs = load_failed_e2e_specs(playwright_results_path)
    _ = parse_e2e_spec_headers(e2e_dir)
    errors = [
        err
        for cap in data.get("capabilities", [])
        if cap.get("kind") == "feature"
        for err in _check_feature_capability(
            cap, prd_uj_set, failed_specs, repo_root, ujs_with_feature
        )
    ]
    for uj in prd_ujs:
        if uj not in ujs_with_feature:
            errors.append(
                f"User Journey `{uj}` défini dans `prd.md` sans capacité `kind: feature` rattachée"
            )
    return errors
