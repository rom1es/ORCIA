"""Validation du registre des capacités `docs/product/capabilities.yaml` (CAP-ACT-1 & Story 21.3).

Garde-fous exécutés par `pnpm site:check` :
1. schéma minimal (ids uniques, champs obligatoires, énumérations, FR proposés déclarés) ;
2. couverture : chaque route SPA et chaque routeur FastAPI est référencé par une capacité
   (`surfaces`) ou listé dans `coverage_exemptions` avec une raison ;
3. verrou CI `CAP ↔ UJ ↔ Spec E2E` (`uj_e2e_coverage.check_uj_e2e_coverage`).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from uj_e2e_coverage import (  # noqa: E402
    E2E_DIR,
    PRD_PATH,
    VALID_E2E_BACKLOG_STORIES,
    check_uj_e2e_coverage,
    parse_e2e_spec_headers,
    summarize_uj_e2e_coverage,
)

REPO_ROOT = _SCRIPTS_DIR.parents[1]
REGISTRY_PATH = REPO_ROOT / "docs" / "product" / "capabilities.yaml"
ROUTERS_DIR = REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "routers"
SYNC_SCRIPT = _SCRIPTS_DIR / "sync_site_catalog.py"

REQUIRED_FIELDS = ("id", "title", "origin", "origin_ref", "status")
ORIGINS = {"epic", "adhoc"}
STATUSES = {"live", "partial", "planned"}
KINDS = {"feature", "foundation"}
VERIFICATIONS = {"docs", "runtime", "failed_e2e"}
UJ_PATTERN = re.compile(r"UJ-[1-9]\d?")


def _validate_kind_fields(cap_id: str, cap: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    kind = cap.get("kind")
    if kind not in KINDS:
        errors.append(f"{cap_id}: kind `{kind}` manquant ou invalide ({sorted(KINDS)})")
        return errors
    if kind == "foundation":
        reason = cap.get("e2e_exempt_reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(
                f"{cap_id}: kind `foundation` exige un champ non vide `e2e_exempt_reason`"
            )
        return errors

    ujs = cap.get("uj")
    if not isinstance(ujs, list) or not ujs:
        errors.append(f"{cap_id}: kind `feature` exige une liste non vide `uj` (UJ-1..UJ-99)")
    else:
        for uj in ujs:
            if not isinstance(uj, str) or not UJ_PATTERN.fullmatch(uj):
                errors.append(f"{cap_id}: UJ `{uj}` invalide (attendu UJ-1..UJ-99)")

    db_tables = cap.get("db_tables")
    has_db_tables = (
        isinstance(db_tables, list)
        and len(db_tables) > 0
        and all(isinstance(t, str) and bool(t.strip()) for t in db_tables)
    )
    read_only = cap.get("read_only_surface") is True
    if not has_db_tables and not read_only:
        errors.append(
            f"{cap_id}: kind `feature` exige `db_tables` (liste non vide) "
            "ou `read_only_surface: true`"
        )
    elif db_tables is not None and not has_db_tables:
        errors.append(f"{cap_id}: `db_tables` doit être une liste non vide de noms de tables")
    return errors


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "capabilities" not in data:
        raise ValueError(f"{path}: clé `capabilities` absente")
    return data


def prd_max_fr(path: Path = PRD_PATH) -> int:
    """Plus grand `FR-n` défini (titre `#### FR-n :`) dans le PRD."""
    nums = [int(n) for n in re.findall(r"^#### FR-(\d+) :", path.read_text(encoding="utf-8"), re.M)]
    return max(nums) if nums else 0


def validate_registry(
    data: dict[str, Any], max_fr: int | None = None, repo_root: Path = REPO_ROOT
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    max_fr = prd_max_fr() if max_fr is None else max_fr
    for cap in data.get("capabilities", []):
        cap_id = str(cap.get("id", "?"))
        for field in REQUIRED_FIELDS:
            if not cap.get(field):
                errors.append(f"{cap_id}: champ obligatoire `{field}` manquant")
        if cap_id in seen:
            errors.append(f"{cap_id}: id dupliqué")
        seen.add(cap_id)
        if cap.get("origin") and cap["origin"] not in ORIGINS:
            errors.append(f"{cap_id}: origin `{cap['origin']}` invalide ({sorted(ORIGINS)})")
        if cap.get("status") and cap["status"] not in STATUSES:
            errors.append(f"{cap_id}: status `{cap['status']}` invalide ({sorted(STATUSES)})")
        verif = cap.get("verification")
        if verif is not None and verif not in VERIFICATIONS:
            errors.append(f"{cap_id}: verification `{verif}` invalide ({sorted(VERIFICATIONS)})")
        backlog_story = cap.get("e2e_backlog_story")
        if backlog_story is not None and backlog_story not in VALID_E2E_BACKLOG_STORIES:
            errors.append(
                f"{cap_id}: e2e_backlog_story `{backlog_story}` invalide "
                f"({sorted(VALID_E2E_BACKLOG_STORIES)})"
            )
        remediation_ref = cap.get("e2e_remediation_ref")
        if remediation_ref is not None and (
            not isinstance(remediation_ref, str) or not remediation_ref.strip()
        ):
            errors.append(f"{cap_id}: `e2e_remediation_ref` doit être une chaîne non vide")
        errors.extend(_validate_kind_fields(cap_id, cap))
        for test_path in cap.get("tests", []) or []:
            if not (repo_root / str(test_path)).exists():
                errors.append(f"{cap_id}: test référencé introuvable `{test_path}`")
        if verif == "runtime" and not cap.get("tests"):
            errors.append(f"{cap_id}: verification `runtime` exige au moins un test (`tests:`)")
        for fr in cap.get("fr", []) or []:
            if not re.fullmatch(r"FR-\d+", str(fr)):
                errors.append(f"{cap_id}: FR `{fr}` invalide (attendu FR-<n>)")
            elif int(str(fr)[3:]) > max_fr:
                errors.append(f"{cap_id}: {fr} absent du PRD (max FR-{max_fr})")
    for ex in data.get("coverage_exemptions", []) or []:
        if not ex.get("surface") or not ex.get("reason"):
            errors.append(f"coverage_exemptions: `surface` et `reason` obligatoires ({ex})")
    return errors


def _surfaces_blob(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for cap in data.get("capabilities", []):
        surfaces = cap.get("surfaces") or {}
        parts.extend(f"{k} {v}" for k, v in surfaces.items())
    return "\n".join(parts)


def check_coverage(data: dict[str, Any], routes: list[str], routers: list[str]) -> list[str]:
    blob = _surfaces_blob(data)
    exempt = {str(e.get("surface")) for e in data.get("coverage_exemptions", []) or []}
    errors: list[str] = []
    for route in routes:
        if route in exempt:
            continue
        if not re.search(re.escape(route) + r"(?![\w-])", blob):
            errors.append(
                f"Route SPA `{route}` sans capacité dans capabilities.yaml (surfaces.route)"
            )
    for router in routers:
        if router in exempt or f"{router}.py" in exempt:
            continue
        if not re.search(r"(?<![\w])" + re.escape(router) + r"(?![\w])", blob):
            errors.append(
                f"Routeur FastAPI `{router}.py` sans capacité dans capabilities.yaml (surfaces.api)"
            )
    return errors


def capability_test_stats(
    data: dict[str, Any],
    *,
    include_uj_e2e: bool = False,
    e2e_dir: Path | None = None,
    prd_path: Path = PRD_PATH,
) -> dict[str, Any]:
    """Capacités `live` avec / sans test référencé (`tests:` + en-têtes `@cap`), pour pilotage."""
    header_caps: dict[str, list[str]] = {}
    if e2e_dir is not None or include_uj_e2e:
        resolved_e2e_dir = e2e_dir if e2e_dir is not None else E2E_DIR
        for spec_path, info in parse_e2e_spec_headers(resolved_e2e_dir).items():
            for cap_id in info["caps"]:
                header_caps.setdefault(cap_id, []).append(spec_path)

    live = [c for c in data.get("capabilities", []) if c.get("status") == "live"]
    without = [
        str(c["id"])
        for c in live
        if not c.get("tests") and not header_caps.get(str(c.get("id", "")))
    ]
    base: dict[str, Any] = {
        "live": len(live),
        "with_tests": len(live) - len(without),
        "without_tests": without,
    }
    if include_uj_e2e:
        resolved_e2e_dir = e2e_dir if e2e_dir is not None else E2E_DIR
        base.update(summarize_uj_e2e_coverage(data, prd_path=prd_path, e2e_dir=resolved_e2e_dir))
    return base


def discover_routers(routers_dir: Path = ROUTERS_DIR) -> list[str]:
    return sorted(
        p.stem for p in routers_dir.glob("*.py") if "APIRouter(" in p.read_text(encoding="utf-8")
    )


def discover_routes() -> list[str]:
    spec = importlib.util.spec_from_file_location("sync_site_catalog", SYNC_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    routes: list[str] = module.parse_active_routes(module.ROUTES_DIR, module.ROUTER_FILE)
    return routes


def run_registry_check() -> list[str]:
    data = load_registry()
    errors = validate_registry(data)
    errors += check_coverage(data, discover_routes(), discover_routers())
    errors += check_uj_e2e_coverage(data)
    stats = capability_test_stats(data, include_uj_e2e=True)
    if stats["without_tests"]:
        errors.append(
            f"Capacités `live` sans test référencé (`tests:`): {', '.join(stats['without_tests'])}"
        )
    return errors
