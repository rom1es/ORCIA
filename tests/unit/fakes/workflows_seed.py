"""Test-only helper seeding `workflows_v2` & `vsm_v2` RAM stores (`<= 55 L`)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI

from orcia_api.main import create_app
from orcia_core.packs import ApmPackCodec
from orcia_core.packs.models import LoadedPackBundleV2
from orcia_core.workflows import SqlVsmDefinitionsV2Store, SqlWorkflowDefinitionsV2Store

_REPO_ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _cached_sdlc_bundle() -> LoadedPackBundleV2:
    return ApmPackCodec().decode_directory(_REPO_ROOT / "packs" / "sdlc")


def create_seeded_test_app() -> FastAPI:
    """Return a real `create_app()` instance with SDLC workflows & VSMs pre-seeded in RAM stores."""
    app = create_app()
    bundle = _cached_sdlc_bundle()
    wf_store = SqlWorkflowDefinitionsV2Store(strict_sql=False)
    for wf in bundle.workflows:
        wf_store._memory_fallback[f"{wf.id}:{wf.version}"] = wf.model_dump(mode="json")
    vsm_store = SqlVsmDefinitionsV2Store(strict_sql=False)
    for vsm in bundle.vsm_specs:
        vsm_store._memory_fallback[vsm.id] = vsm.model_dump(mode="json")
    app.state.workflows_v2_sql_store = wf_store
    app.state.vsm_v2_sql_store = vsm_store
    return app
