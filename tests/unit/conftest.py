"""Shared unit-test fixtures with isolated session-scoped app & cached `RepoSourceIndex`."""

from __future__ import annotations

import copy
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from tests.unit.fakes.test_app_helpers import (
    RepoSourceIndex,
    create_seeded_test_app,
    get_repo_source_index,
)

_SESSION_APP_STATE: dict[str, Any] = {
    "app": None,
    "base_state": None,
    "base_wf_fallback": None,
    "base_vsm_fallback": None,
    "base_evaluator_snapshot": None,
}


@pytest.fixture(scope="session")
def seeded_test_app() -> FastAPI:
    """Provide a session-scoped `create_seeded_test_app()` protected by per-test state isolation."""
    app = create_seeded_test_app()
    _SESSION_APP_STATE["app"] = app
    _SESSION_APP_STATE["base_state"] = dict(app.state._state)
    wf_store = getattr(app.state, "workflows_v2_sql_store", None)
    vsm_store = getattr(app.state, "vsm_v2_sql_store", None)
    _SESSION_APP_STATE["base_wf_fallback"] = (
        copy.deepcopy(wf_store._memory_fallback) if wf_store is not None else None
    )
    _SESSION_APP_STATE["base_vsm_fallback"] = (
        copy.deepcopy(vsm_store._memory_fallback) if vsm_store is not None else None
    )
    auth_svc = getattr(app.state, "auth_service", None)
    ev = getattr(auth_svc, "evaluator", None)
    _SESSION_APP_STATE["base_evaluator_snapshot"] = (
        (
            dict(ev._org_units_by_id),
            dict(ev._workspaces_by_id),
            tuple(ev._memberships),
            tuple(ev._catalog_acls),
        )
        if ev is not None
        else None
    )
    return app


@pytest.fixture(autouse=True)
def _isolate_seeded_test_app_state() -> Iterator[None]:
    """Snapshot/restore `dependency_overrides`, `app.state`, and `evaluator` if active."""
    yield
    app: FastAPI | None = _SESSION_APP_STATE["app"]
    if app is None:
        return
    app.dependency_overrides.clear()
    base_state = _SESSION_APP_STATE["base_state"]
    if isinstance(base_state, dict):
        app.state._state.clear()
        app.state._state.update(base_state)
    wf_store = getattr(app.state, "workflows_v2_sql_store", None)
    base_wf = _SESSION_APP_STATE["base_wf_fallback"]
    if wf_store is not None and isinstance(base_wf, dict):
        wf_store._memory_fallback.clear()
        wf_store._memory_fallback.update(copy.deepcopy(base_wf))
    vsm_store = getattr(app.state, "vsm_v2_sql_store", None)
    base_vsm = _SESSION_APP_STATE["base_vsm_fallback"]
    if vsm_store is not None and isinstance(base_vsm, dict):
        vsm_store._memory_fallback.clear()
        vsm_store._memory_fallback.update(copy.deepcopy(base_vsm))
    auth_svc = getattr(app.state, "auth_service", None)
    ev = getattr(auth_svc, "evaluator", None)
    base_ev = _SESSION_APP_STATE["base_evaluator_snapshot"]
    if ev is not None and isinstance(base_ev, tuple):
        org_map, ws_map, memberships, catalog_acls = base_ev
        ev._org_units_by_id.clear()
        ev._org_units_by_id.update(org_map)
        ev._workspaces_by_id.clear()
        ev._workspaces_by_id.update(ws_map)
        ev._memberships = tuple(memberships)
        ev._catalog_acls = tuple(catalog_acls)


@pytest.fixture(scope="session")
def repo_source_index() -> RepoSourceIndex:
    """Provide a cached `RepoSourceIndex` for unit AST/file audits."""
    return get_repo_source_index()
