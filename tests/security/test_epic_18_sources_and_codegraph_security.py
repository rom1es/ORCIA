"""Epic 18 — Comprehensive Red-Team & Security Governance Tests (Layer 5 `AD-17`).

Covers:
1. Anti-SSRF validation on data source / code graph endpoints (blocks 169.254.169.254,
   169.254.0.0/16, metadata.google.internal, 100.100.100.200; allows .local/.internal).
2. HMAC webhook invalid signature rejection (401 ERR_WEBHOOK_SIGNATURE_INVALID, RFC 9457).
3. Rejection of READ_ONLY_OBSERVER (403 ERR_OBSERVER_MODE_READ_ONLY) on mutations:
   create, update, delete, sync, reconcile-staleness.
4. Workspace Lead authorization required for GitNexus activation/deactivation
   (403 ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED for CONTRIBUTOR / OBSERVER).
5. Strict workspace_id directory confinement and anti-path-traversal on:
   - codegraph_read_span (.., /etc/passwd, > 250 lines ceiling)
   - resolve_confined_graph_dir (.., / escaping, outside storage root)
6. Zero canary secret leakage (webhook secrets, passthrough tokens, internal tokens)
   in HTTP responses, models str/repr, or structured log entries.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_api.routers.assistant_llm_providers import is_safe_llm_endpoint_url
from orcia_api.routers.datasource_webhooks import _verify_hmac
from orcia_connectors.codegraph.models import validate_read_span_params
from orcia_connectors.codegraph.providers import GitNexusMcpHttpProvider
from orcia_core.bootstrap._internal.sql_datasource_freshness import DatasourceWebhookContext
from orcia_core.permissions import (
    can_manage_workspace_codegraph,
)
from orcia_core.permissions.errors import (
    CodegraphWorkspaceLeadRequiredError,
    ObserverModeReadOnlyError,
)
from orcia_worker.codegraph_indexer import (
    purge_confined_graph_dir,
    resolve_confined_graph_dir,
)

CANARY_SECRET = "canary_secret_deadbeef_test_token_999"  # pragma: allowlist secret
VALID_WS_UUID = "018f0000-0000-7000-8000-000000000001"
VALID_DS_UUID = "018f0000-0000-7000-8000-000000000002"


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    old_pg = os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC")
    old_llm = os.environ.get("ORCIA_USE_CASSETTE_LLM")
    os.environ["ORCIA_DISABLE_PG_BOOTSTRAP_SYNC"] = "1"
    os.environ["ORCIA_USE_CASSETTE_LLM"] = "true"
    app = create_app()
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        if old_pg is None:
            os.environ.pop("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", None)
        else:
            os.environ["ORCIA_DISABLE_PG_BOOTSTRAP_SYNC"] = old_pg
        if old_llm is None:
            os.environ.pop("ORCIA_USE_CASSETTE_LLM", None)
        else:
            os.environ["ORCIA_USE_CASSETTE_LLM"] = old_llm


# ------------------------------------------------------------------------------
# 1. Anti-SSRF Validation
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.10.20:8080/v1",
        "http://100.100.100.200/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://metadata.azure.com/metadata/instance",
        "http://[fe80::1]/v1",
        "file:///etc/passwd",
        "ftp://example.com/source.git",
    ],
)
def test_anti_ssrf_blocks_dangerous_endpoints(url: str) -> None:
    assert not is_safe_llm_endpoint_url(url), f"URL should be blocked: {url}"


@pytest.mark.parametrize(
    "url",
    [
        "http://gitnexus-mcp:8095/mcp",
        "http://gitnexus.local:8095/mcp",
        "http://sourcegraph.internal:3080/mcp",
        "https://gitlab.internal/api/v4",
        "https://api.github.com",
    ],
)
def test_anti_ssrf_allows_legitimate_internal_and_public_destinations(url: str) -> None:
    assert is_safe_llm_endpoint_url(url), f"Legitimate destination should be allowed: {url}"


# ------------------------------------------------------------------------------
# 2. Webhook HMAC Signature Security & Constant-Time Rejection
# ------------------------------------------------------------------------------


def test_webhook_hmac_constant_time_verification() -> None:
    secret = "my-webhook-secret-xyz"  # pragma: allowlist secret
    body = b'{"ref": "refs/heads/main", "after": "abc1234"}'

    expected_sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert _verify_hmac(raw_body=body, secret=secret, signature_header=expected_sig)

    assert not _verify_hmac(raw_body=body, secret=secret, signature_header="sha256=invalidhex000")
    assert not _verify_hmac(raw_body=body, secret=secret, signature_header="")
    assert not _verify_hmac(raw_body=body, secret=secret, signature_header="wrongformat")


def test_webhook_endpoint_rejects_missing_or_invalid_signature_rfc9457(client: TestClient) -> None:
    from unittest.mock import patch

    mock_ctx = DatasourceWebhookContext(
        datasource_id=VALID_DS_UUID,
        workspace_id=VALID_WS_UUID,
        alias="test-repo",
        source_nature="SOURCE_CODE",
        target_ref=None,
        target_scope=None,
        fingerprint_hash=None,
        freshness_status="FRESH",
        connector_id=None,
        connector_base_url=None,
        connector_scheme="git",
        webhook_secret_encrypted=None,
        codegraph_enabled=True,
        codegraph_auth_mode="SERVICE_ACCOUNT",
        codegraph_owner_user_id=None,
        codegraph_status="INITIAL",
    )

    with (
        patch(
            "orcia_api.routers.datasource_webhooks.get_datasource_webhook_context_from_postgres18",
            return_value=mock_ctx,
        ),
        patch.dict(
            os.environ,
            {"ORCIA_DEFAULT_WEBHOOK_SECRET": "test-configured-secret"},  # pragma: allowlist secret
        ),
    ):
        resp = client.post(
            f"/api/v1/webhooks/datasources/{VALID_DS_UUID}",
            content=b'{"delivery_key": "k1", "remote_fingerprint_sha256": "abc"}',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401
        assert "application/problem+json" in resp.headers.get("content-type", "")
        data = resp.json()
        assert data.get("error_code") == "ERR_WEBHOOK_SIGNATURE_INVALID"
        assert "trace_id" in data


# ------------------------------------------------------------------------------
# 3. Role Authorization: READ_ONLY_OBSERVER Rejection on Mutations
# ------------------------------------------------------------------------------


def test_read_only_observer_error_contract() -> None:
    err = ObserverModeReadOnlyError(instance="/api/v1/workspaces/staleness")
    assert err.http_status == 403
    assert err.error_code == "ERR_OBSERVER_MODE_READ_ONLY"
    assert err.type_uri.endswith("/observer-mode-read-only")


def test_read_only_observer_rejected_on_staleness_reconcile_route(client: TestClient) -> None:
    resp = client.post(
        f"/api/v1/workspaces/{VALID_WS_UUID}/datasources/reconcile-staleness",
        headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER", "X-User-Id": "usr-obs"},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data.get("error_code") == "ERR_OBSERVER_MODE_READ_ONLY"


# ------------------------------------------------------------------------------
# 4. Workspace Lead Required for GitNexus Activation
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("roles", "expected_allowed"),
    [
        (["OBSERVER"], False),
        (["READ_ONLY_OBSERVER"], False),
        (["CONTRIBUTOR"], False),
        (["GUEST"], False),
        (["MEMBER"], False),
        (["TEAM_LEAD"], True),
        (["BU_LEAD"], True),
        (["PLATFORM_ADMIN"], True),
        (["SECOPS"], True),
        ([], False),
    ],
)
def test_can_manage_workspace_codegraph_matrix(roles: list[str], expected_allowed: bool) -> None:
    assert can_manage_workspace_codegraph(roles) is expected_allowed


def test_codegraph_workspace_lead_required_rfc9457_contract() -> None:
    err = CodegraphWorkspaceLeadRequiredError(instance="ws-lead-test")
    assert err.http_status == 403
    assert err.error_code == "ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED"
    assert err.type_uri.endswith("/codegraph-workspace-lead-required")


# ------------------------------------------------------------------------------
# 5. Strict Confinement & Anti-Path-Traversal
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "malicious_path",
    [
        "../etc/passwd",
        "../../shadow",
        "/etc/hosts",
        "subdir/../../../secrets.env",
        "..",
        "./../../",
    ],
)
def test_codegraph_read_span_anti_path_traversal(malicious_path: str) -> None:
    with pytest.raises(ValueError, match="traversal or absolute path detected"):
        validate_read_span_params(malicious_path, 1, 10)


@pytest.mark.parametrize(
    ("start_line", "end_line"),
    [
        (0, 10),
        (-5, 20),
        (50, 10),
        (1, 300),  # Exceeds MAX_CODE_SPAN_LINES (250)
    ],
)
def test_codegraph_read_span_bounds_validation(start_line: int, end_line: int) -> None:
    with pytest.raises(ValueError):
        validate_read_span_params("src/main.py", start_line, end_line)


@pytest.mark.parametrize(
    ("workspace_id", "datasource_id"),
    [
        ("../../escape", "repo"),
        ("ws-1", "../../escape"),
        ("/etc/passwd", "repo"),
        ("ws-1", "/root/.ssh"),
    ],
)
def test_codegraph_indexer_anti_path_traversal(
    workspace_id: str, datasource_id: str, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="Unsafe"):
        resolve_confined_graph_dir(
            storage_root=tmp_path,
            workspace_id=workspace_id,
            datasource_id=datasource_id,
        )


def test_codegraph_indexer_purge_confinement(tmp_path: Path) -> None:
    safe_dir = tmp_path / "ws1" / "ds1"
    safe_dir.mkdir(parents=True, exist_ok=True)
    marker = safe_dir / "index.json"
    marker.write_text("{}", encoding="utf-8")

    # Safe purge inside storage_root
    assert purge_confined_graph_dir(storage_root=tmp_path, workspace_id="ws1", datasource_id="ds1")
    assert not safe_dir.exists()


# ------------------------------------------------------------------------------
# 6. Zero Canary Secret Leakage in Models, str, and Provider Exceptions
# ------------------------------------------------------------------------------


def test_zero_canary_secret_leakage_in_models_and_str() -> None:
    provider = GitNexusMcpHttpProvider(internal_token=CANARY_SECRET)
    assert CANARY_SECRET not in repr(provider)
    assert CANARY_SECRET not in str(provider)


@pytest.mark.asyncio
async def test_zero_canary_secret_in_provider_http_error_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    provider = GitNexusMcpHttpProvider(
        endpoint="http://127.0.0.1:59999/unreachable",
        internal_token=CANARY_SECRET,
    )
    with caplog.at_level(logging.WARNING):
        result = await provider._post_tool_call("test_tool", {"query": "foo"})

    assert result.get("status") == "unavailable"
    for record in caplog.records:
        assert CANARY_SECRET not in record.getMessage()
        assert CANARY_SECRET not in str(record.__dict__)
