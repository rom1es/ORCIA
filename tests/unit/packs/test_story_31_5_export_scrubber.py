"""Unit tests for Story 31.5 export scrubber, tenant loader & leak scanner (`<= 280 L`)."""

from __future__ import annotations

import pytest
from uuid_utils import uuid7

from orcia_core.packs._internal._pack_export_infra_loader import (
    extract_host as _extract_host,
)
from orcia_core.packs._internal._pack_export_scrubber import (
    TenantInfraIdentifiers,
    _is_forbidden_host_or_ip,
    scan_rendered_files_for_leaks,
)
from orcia_core.packs._internal._pack_export_scrubber_mappers import (
    debind_ref_value,
    normalize_model_tier,
    normalize_skill_ref,
)
from orcia_core.packs.errors import PackPiiOrInfraLeakError
from orcia_core.packs.models import PackSlotSpec

pytestmark = pytest.mark.story("31.5")


def test_host_ip_and_tier_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify SSRF/private host checks, model tier normalization & slot de-binding."""
    monkeypatch.setenv("ORCIA_LLM_ALLOWED_PRIVATE_HOSTS", "llm-internal.example.net")
    assert _extract_host("https://api.example.com:8443/v1") == "api.example.com"
    assert _extract_host("http://[::1") == ""
    assert not _is_forbidden_host_or_ip("json-schema.org", frozenset())
    assert _is_forbidden_host_or_ip("169.254.169.254", frozenset())
    assert _is_forbidden_host_or_ip("100.100.100.200", frozenset())
    assert _is_forbidden_host_or_ip("10.0.1.5", frozenset())
    assert _is_forbidden_host_or_ip("service.internal", frozenset())
    assert _is_forbidden_host_or_ip("tenant-host.corp", frozenset({"tenant-host.corp"}))
    assert not _is_forbidden_host_or_ip("api.github.com", frozenset())

    assert normalize_model_tier("fast") == "simple"
    assert normalize_model_tier("reasoning") == "complex"
    assert normalize_model_tier("gpt-4o-custom") == "medium"
    assert normalize_skill_ref("orcia://workspaces/ws-1/skills/lint-code") == "lint-code"
    assert normalize_skill_ref("/pack-a/lint-code") == "lint-code"

    ds_uuid = str(uuid7())
    infra = TenantInfraIdentifiers(
        datasource_slots_by_ref={
            ds_uuid: {
                "slot_key": "repo_main",
                "scheme": "git",
                "connector_kind": "git",
                "source_nature": "SOURCE_CODE",
            }
        }
    )
    slots: dict[str, PackSlotSpec] = {}
    assert (
        debind_ref_value(ds_uuid, pack_slug="my-pack", infra=infra, slots_by_key=slots)
        == "slot://repo_main"
    )
    assert "repo_main" in slots
    assert (
        debind_ref_value("slot://extra_kb", pack_slug="my-pack", infra=infra, slots_by_key=slots)
        == "slot://extra_kb"
    )
    assert (
        debind_ref_value(
            "orcia://workspaces/ws-1/agents/helper",
            pack_slug="my-pack",
            infra=infra,
            slots_by_key=slots,
        )
        == "orcia://packs/my-pack/agents/helper"
    )
    assert (
        debind_ref_value(
            "pack://old/skills/lint", pack_slug="my-pack", infra=infra, slots_by_key=slots
        )
        == "orcia://packs/my-pack/skills/lint"
    )


def test_leak_scanner_rejects_pii_secrets_uuids_and_private_hosts() -> None:
    """Verify O(1) leak scanner fails closed with `PackPiiOrInfraLeakError`."""
    ws_uuid = str(uuid7())
    infra = TenantInfraIdentifiers(
        tenant_uuids=frozenset({ws_uuid}),
        tenant_emails=frozenset({"secret.owner@company.com"}),
        tenant_hosts=frozenset({"gitlab.corp.internal"}),
    )
    bad_cases: list[dict[str, bytes]] = [
        {"agents/a.agent.md": f"Workspace {ws_uuid} instructions.".encode()},
        {"agents/a.agent.md": b"Contact alice@example.org for details."},
        {"apm.yml": b"name: p\nauthor: secret.owner@company.com\n"},
        {"apm.yml": b"name: p\ndescription: ping somebody@public.org\n"},
        {"workflows/wf.yaml": b"endpoint: http://169.254.169.254/latest/meta-data"},
        {"workflows/wf.yaml": b"endpoint: https://gitlab.corp.internal/repo"},
        {"agents/a.agent.md": b"Use token sk-abcdefghijklmnopqrstuvwxyz123456"},
        {"agents/a.agent.md": b"Ref vault://orcia/datasources/ws/secret"},
        {"agents/a.agent.md": b"Authorization: Bearer super_secret_token_99999"},
        {
            "workflows/wf.yaml": (
                b"dsn: postgresql://" + b"user:pass" + b"@db.corp.local:5432/orcia"
            )
        },
        {"workflows/wf.yaml": b"cache: redis://10.0.0.5:6379/0"},
        {"agents/a.agent.md": b"Connect ::1 or fe80::1 directly."},
        {"apm.yml": b"name: p\nquick_actions:\n  - label: ping me@public.org\n"},
    ]
    for files in bad_cases:
        with pytest.raises(PackPiiOrInfraLeakError) as exc_info:
            scan_rendered_files_for_leaks(files, infra)
        assert exc_info.value.http_status == 422
        assert exc_info.value.leak_findings

    clean_files = {
        "apm.yml": (
            b"name: clean\nversion: 1.0.0\nauthor: external@oss.org\n"
            b"maintainers:\n  - email: lead@oss.org\n"
        ),
        "apm.lock.yaml": b"bundle_sha256: abc\n",
        "policies/git-ro.policy.md": b"---\nuri_pattern: git://*\n---\nRead.\n",
        "agents/a.agent.md": (
            b"---\nname: Clean\n$schema: https://json-schema.org/draft/2020-12/schema\n"
            b"---\nFollow slot://repo rules.\n"
        ),
    }
    scan_rendered_files_for_leaks(clean_files, infra)
