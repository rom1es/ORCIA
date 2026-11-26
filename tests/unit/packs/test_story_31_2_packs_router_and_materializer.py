"""Unit tests for Story 31.2 transactional PG18 materializer & delete guards (`<= 300 L`)."""

from __future__ import annotations

import io
import zipfile
from contextlib import asynccontextmanager
from typing import Any

import pytest
import yaml

from orcia_core.packs._internal._sql_pack_delete_tx import delete_bundle_transactional
from orcia_core.packs._internal._sql_pack_import_tx import import_bundle_transactional
from orcia_core.packs._internal.apm_codec import ApmPackCodec
from orcia_core.packs.errors import (
    EntityReferencedByPackDraftError,
    PackBundleNotFoundError,
    PackSystemDeleteForbiddenError,
    PackVersionConflictError,
    ResourcePinnedByActiveRunsError,
)


class _FakeResult:
    def __init__(self, *, scalar: Any = None, mapping: dict[str, Any] | None = None) -> None:
        self._scalar = scalar
        self._mapping = mapping

    def scalar(self) -> Any:
        return self._scalar

    def scalar_one(self) -> Any:
        return self._scalar

    def first(self) -> Any:
        if self._mapping is not None:
            return self._mapping
        return (self._scalar,) if self._scalar is not None else None

    def mappings(self) -> _FakeResult:
        return self


class _FakeConn:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.queries: list[str] = []

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = str(stmt)
        self.queries.append(sql)
        return self._resolver(sql, params or {})


class _FakeEngine:
    def __init__(self, resolver: Any) -> None:
        self.conn = _FakeConn(resolver)

    @asynccontextmanager
    async def begin(self) -> Any:
        yield self.conn


def _make_sample_zip(slug: str = "demo-pack", version: str = "1.0.0") -> bytes:
    buf = io.BytesIO()
    apm = yaml.safe_dump(
        {
            "name": slug,
            "version": version,
            "description": "Demo",
            "x-orcia": {
                "slug": slug,
                "bundle_kind": "IMPORTED",
                "scope_type": "WORKSPACE",
                "scope_id": "0195f000-0000-7000-8000-000000000301",
                "status": "PUBLISHED",
            },
        }
    )
    agent = (
        "---\nname: Demo Agent\ndescription: Role\n"
        "x-orcia:\n  posture: PRODUCER\n  human_partner_role: TECH_LEAD\n"
        "---\nFollow rules.\n"
    )
    skill = (
        "---\nname: Demo Skill\ndescription: Skill\n"
        "x-orcia:\n  command_handle: /demo\n---\nRun demo.\n"
    )
    wf = yaml.safe_dump(
        {
            "id": "wf-demo",
            "slug": "wf-demo",
            "pack_id": f"orcia-pack-{slug}",
            "title": "Demo WF",
            "subtitle": "Demo",
            "version": "1.0.0",
            "status": "published",
            "execution_mode": "native_orcia",
            "orchestration_type": "deterministic_dbos",
            "sub_steps": [
                {
                    "id": "s1",
                    "short_label": "S1",
                    "name": "Step 1",
                    "trigger_condition_label": "Manual",
                    "role_description": "Lead",
                    "output_description": "Doc",
                    "checkpoint_label": "Gate 1",
                    "instruction_prompt_or_ref": "Do",
                    "requires_human_checkpoint": True,
                }
            ],
        }
    )
    vsm = yaml.safe_dump(
        {
            "id": "vsm-demo",
            "slug": "vsm-demo",
            "pack_id": f"orcia-pack-{slug}",
            "title": "Demo VSM",
            "subtitle": "Flow",
            "source_note": "test",
            "guiding_principle": "test",
            "phases": [],
            "nodes": [],
            "opportunities": {},
        }
    )
    glossary = yaml.safe_dump(
        {
            "terms": [{"key": "KPI", "label": "KPI", "definition": "Metric"}],
            "relations": [
                {"source": "KPI", "target": "KPI", "relation_type": "SELF", "cardinality": "1..1"}
            ],
            "axioms": [{"concept_key": "KPI", "rule_expression": "len(x) > 0"}],
        }
    )
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{slug}/apm.yml", apm)
        zf.writestr(f"{slug}/agents/demo-agent.agent.md", agent)
        zf.writestr(f"{slug}/skills/demo-skill/SKILL.md", skill)
        zf.writestr(f"{slug}/workflows/wf-demo.yaml", wf)
        zf.writestr(f"{slug}/workflows/vsm-demo.yaml", vsm)
        zf.writestr(f"{slug}/ontology/glossary.yaml", glossary)
        zf.writestr(
            f"{slug}/instructions/base.instructions.md", "---\napplyTo: '**/*'\n---\nHint.\n"
        )
        zf.writestr(
            f"{slug}/help/fr/intro.md",
            "---\ntitle: Intro\nbound_routes:\n  - /agents\n---\nAide.\n",
        )
    return buf.getvalue()


@pytest.mark.asyncio
async def test_import_and_delete_bundle_transactional_guards() -> None:
    """Verify full transactional materialization and all `delete_bundle_transactional` guards."""
    bundle = ApmPackCodec().decode_zip_bytes(_make_sample_zip())
    bid = "0195f000-0000-7000-8000-000000000901"

    def _ok_resolver(sql: str, _params: dict[str, Any]) -> _FakeResult:
        if "FROM declarative_pack_bundles" in sql and "FOR UPDATE" in sql:
            return _FakeResult(mapping=None)
        if "SELECT id FROM org_units" in sql or "INSERT INTO org_units" in sql:
            return _FakeResult(scalar="0195f000-0000-7000-8000-000000000001")
        if "INSERT INTO declarative_pack_bundles" in sql:
            return _FakeResult(scalar=bid)
        if "INSERT INTO ontology_concepts" in sql:
            return _FakeResult(scalar="0195f000-0000-7000-8000-000000000902")
        if "to_regclass" in sql:
            return _FakeResult(scalar="audit_ledger")
        return _FakeResult(scalar=None)

    eng = _FakeEngine(_ok_resolver)
    res = await import_bundle_transactional(eng, bundle, actor_id="u-1")  # type: ignore[arg-type]
    assert res["bundle_id"] == bid
    assert res["counts"]["agents"] == 1
    assert any("INSERT INTO catalog_items" in q for q in eng.conn.queries)
    assert any("INSERT INTO workflow_definitions_v2" in q for q in eng.conn.queries)
    assert any("INSERT INTO vsm_definitions_v2" in q for q in eng.conn.queries)
    assert any("INSERT INTO ontology_concepts" in q for q in eng.conn.queries)
    assert any("INSERT INTO audit_ledger" in q for q in eng.conn.queries)

    def _conflict_resolver(sql: str, _params: dict[str, Any]) -> _FakeResult:
        if "FROM declarative_pack_bundles" in sql:
            return _FakeResult(
                mapping={
                    "id": bid,
                    "bundle_kind": "IMPORTED",
                    "status": "PUBLISHED",
                    "archive_sha256": "f" * 64,
                    "cas_object_key": None,
                }
            )
        return _FakeResult()

    with pytest.raises(PackVersionConflictError):
        await import_bundle_transactional(_FakeEngine(_conflict_resolver), bundle)  # type: ignore[arg-type]

    with pytest.raises(PackBundleNotFoundError):
        await delete_bundle_transactional(
            _FakeEngine(lambda _s, _p: _FakeResult(mapping=None)),  # type: ignore[arg-type]
            bundle_id_or_pack_id=bid,
        )

    def _sys_resolver(_sql: str, _p: dict[str, Any]) -> _FakeResult:
        return _FakeResult(
            mapping={
                "id": bid,
                "pack_id": "p",
                "slug": "sdlc",
                "version": "1.0.0",
                "bundle_kind": "SYSTEM",
                "scope_type": "GLOBAL",
                "scope_id": "global",
            }
        )

    with pytest.raises(PackSystemDeleteForbiddenError):
        await delete_bundle_transactional(_FakeEngine(_sys_resolver), bundle_id_or_pack_id=bid)  # type: ignore[arg-type]

    def _pinned_resolver(sql: str, _p: dict[str, Any]) -> _FakeResult:
        if "FROM declarative_pack_bundles" in sql:
            return _FakeResult(
                mapping={
                    "id": bid,
                    "pack_id": "p",
                    "slug": "demo",
                    "version": "1.0.0",
                    "bundle_kind": "IMPORTED",
                    "scope_type": "WORKSPACE",
                    "scope_id": "ws1",
                }
            )
        if "run_lock_manifests" in sql:
            return _FakeResult(scalar=1)
        return _FakeResult(scalar=None)

    with pytest.raises(ResourcePinnedByActiveRunsError):
        await delete_bundle_transactional(_FakeEngine(_pinned_resolver), bundle_id_or_pack_id=bid)  # type: ignore[arg-type]

    def _draft_ref_resolver(sql: str, _p: dict[str, Any]) -> _FakeResult:
        if "FROM declarative_pack_bundles" in sql:
            return _FakeResult(
                mapping={
                    "id": bid,
                    "pack_id": "p",
                    "slug": "demo",
                    "version": "1.0.0",
                    "bundle_kind": "IMPORTED",
                    "scope_type": "WORKSPACE",
                    "scope_id": "ws1",
                }
            )
        if "pack_draft_memberships" in sql and "JOIN catalog_items" in sql:
            return _FakeResult(scalar=1)
        return _FakeResult(scalar=None)

    with pytest.raises(EntityReferencedByPackDraftError):
        await delete_bundle_transactional(
            _FakeEngine(_draft_ref_resolver),  # type: ignore[arg-type]
            bundle_id_or_pack_id=bid,
        )
