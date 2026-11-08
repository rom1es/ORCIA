"""Validation du registre des capacités `docs/product/capabilities.yaml` (CAP-ACT-1).

Garde-fous exécutés par `pnpm site:check` :
1. schéma minimal (ids uniques, champs obligatoires, énumérations, FR proposés déclarés) ;
2. couverture : chaque route SPA et chaque routeur FastAPI est référencé par une capacité
   (`surfaces`) ou listé dans `coverage_exemptions` avec une raison.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "docs" / "product" / "capabilities.yaml"
ROUTERS_DIR = REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "routers"
PRD_PATH = REPO_ROOT / "docs" / "planning-artifacts" / "prds" / "prd-ORCIA-2026-10-24" / "prd.md"
SYNC_SCRIPT = Path(__file__).resolve().parent / "sync_site_catalog.py"

REQUIRED_FIELDS = ("id", "title", "origin", "origin_ref", "status")
ORIGINS = {"epic", "adhoc"}
STATUSES = {"live", "partial", "planned"}


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
        for test_path in cap.get("tests", []) or []:
            if not (repo_root / str(test_path)).exists():
                errors.append(f"{cap_id}: test référencé introuvable `{test_path}`")
        if cap.get("verification") == "runtime" and not cap.get("tests"):
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


def capability_test_stats(data: dict[str, Any]) -> dict[str, Any]:
    """Capacités `live` avec / sans test référencé (`tests:`), pour pilotage de la pyramide."""
    live = [c for c in data.get("capabilities", []) if c.get("status") == "live"]
    without = [str(c["id"]) for c in live if not c.get("tests")]
    return {"live": len(live), "with_tests": len(live) - len(without), "without_tests": without}


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
    stats = capability_test_stats(data)
    if stats["without_tests"]:
        errors.append(
            f"Capacités `live` sans test référencé (`tests:`): {', '.join(stats['without_tests'])}"
        )
    return errors
