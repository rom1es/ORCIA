"""Story 18.2 — Unit tests for Freshness Differential Engine, 24h Probe & GitNexus Worker.

Covers:
1. Hypothesis property-based tests on SHA-256 fingerprint normalization & idempotence.
2. 24h freshness probe decision matrix (quiet weekend 0 $ LLM vs drift auto-heal vs stale).
3. HMAC-SHA256 constant-time verification & WebhookSignatureInvalidError RFC 9457 contract.
4. Confined path validation (anti-path-traversal ValueError on `..` or escaping) and disk purge.
5. Async/sync execution of `codegraph_indexer` with token resolution & injectable runner.
6. Lightweight AST indexing 0 $ LLM verification (Arbitrage 3A).
"""

from __future__ import annotations

import hashlib
import hmac
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from orcia_api.routers.datasource_webhooks import _verify_hmac
from orcia_core.permissions import WebhookSignatureInvalidError
from orcia_core.rag.indexer_and_rrf import DifferentiatedIncrementalIndexer
from orcia_core.rag.source_freshness_reconciler import (
    RECONCILE_OUTCOME_AUTO_HEAL_DELTA_SYNC,
    RECONCILE_OUTCOME_DELTA_SYNC_REQUIRED,
    RECONCILE_OUTCOME_NO_OP_UNCHANGED,
    RECONCILE_OUTCOME_QUIET_UNCHANGED,
    RECONCILE_OUTCOME_RECENT_SIGNALS_OK,
    RECONCILE_OUTCOME_STALE_DETECTED,
    RemoteFingerprintProbePort,
    compute_content_sha256,
    evaluate_24h_freshness_probe,
    normalize_fingerprint,
    reconcile_incoming_fingerprint,
)
from orcia_worker.codegraph_indexer import (
    CodegraphIndexExecutionResult,
    execute_codegraph_index_job,
    execute_codegraph_index_job_async,
    purge_confined_graph_dir,
    resolve_confined_graph_dir,
)


# 1. Hypothesis Property Tests: SHA-256 normalization and idempotence
@given(st.text(alphabet="abcdef0123456789", min_size=64, max_size=64))
def test_hypothesis_sha256_reconcile_identical_is_always_noop(sha: str) -> None:
    outcome = reconcile_incoming_fingerprint(sha, sha)
    assert outcome == RECONCILE_OUTCOME_NO_OP_UNCHANGED


@given(
    st.text(alphabet="abcdef0123456789", min_size=64, max_size=64),
    st.text(alphabet=" \t\n", min_size=0, max_size=4),
)
def test_hypothesis_sha256_case_and_whitespace_insensitivity(sha: str, padding: str) -> None:
    stored = f"{padding}{sha.upper()}{padding}"
    incoming = f"{sha.lower()}"
    outcome = reconcile_incoming_fingerprint(stored, incoming)
    assert outcome == RECONCILE_OUTCOME_NO_OP_UNCHANGED


@given(
    st.text(alphabet="abcdef0123456789", min_size=64, max_size=64),
    st.text(alphabet="abcdef0123456789", min_size=64, max_size=64),
)
def test_hypothesis_sha256_divergent_is_delta_sync(sha1: str, sha2: str) -> None:
    if sha1.lower() != sha2.lower():
        assert reconcile_incoming_fingerprint(sha1, sha2) == RECONCILE_OUTCOME_DELTA_SYNC_REQUIRED


# 2. 24h Freshness Probe Decision Matrix
class MockProbe(RemoteFingerprintProbePort):
    def __init__(self, response_hash: str | None = None, raise_error: bool = False) -> None:
        self.response_hash = response_hash
        self.raise_error = raise_error
        self.call_count = 0

    async def probe_remote_fingerprint(
        self,
        *,
        datasource_id: str,
        target_ref: str | None = None,
        target_scope: str | None = None,
    ) -> str | None:
        self.call_count += 1
        if self.raise_error:
            raise ConnectionError("Remote unreachable")
        return self.response_hash


@pytest.mark.asyncio
async def test_freshness_probe_within_24h_is_synced_without_probe_call() -> None:
    now = datetime.now(UTC)
    last_signal = now - timedelta(hours=12)
    stored_hash = "a" * 64
    probe = MockProbe(response_hash="b" * 64)

    res = await evaluate_24h_freshness_probe(
        stored_hash=stored_hash,
        last_signal_at=last_signal,
        current_time=now,
        probe=probe,
    )

    assert res.freshness_status == "SYNCED"
    assert res.outcome == RECONCILE_OUTCOME_RECENT_SIGNALS_OK
    assert res.delta_sync_needed is False
    assert probe.call_count == 0


@pytest.mark.asyncio
async def test_freshness_probe_quiet_weekend_unchanged_preserves_synced_zero_llm_cost() -> None:
    now = datetime.now(UTC)
    last_signal = now - timedelta(hours=36)
    stored_hash = "c" * 64
    probe = MockProbe(response_hash=stored_hash)

    res = await evaluate_24h_freshness_probe(
        stored_hash=stored_hash,
        last_signal_at=last_signal,
        current_time=now,
        probe=probe,
    )

    assert res.freshness_status == "SYNCED"
    assert res.outcome == RECONCILE_OUTCOME_QUIET_UNCHANGED
    assert res.delta_sync_needed is False
    assert probe.call_count == 1


@pytest.mark.asyncio
async def test_freshness_probe_divergent_hash_after_24h_triggers_auto_heal() -> None:
    now = datetime.now(UTC)
    last_signal = now - timedelta(hours=48)
    stored_hash = "d" * 64
    probe = MockProbe(response_hash="e" * 64)

    res = await evaluate_24h_freshness_probe(
        stored_hash=stored_hash,
        last_signal_at=last_signal,
        current_time=now,
        probe=probe,
    )

    assert res.freshness_status == "SYNCED"
    assert res.outcome == RECONCILE_OUTCOME_AUTO_HEAL_DELTA_SYNC
    assert res.delta_sync_needed is True
    assert probe.call_count == 1


@pytest.mark.asyncio
async def test_freshness_probe_failing_or_missing_after_24h_marks_stale() -> None:
    now = datetime.now(UTC)
    last_signal = now - timedelta(hours=30)
    stored_hash = "f" * 64
    failing_probe = MockProbe(raise_error=True)

    res = await evaluate_24h_freshness_probe(
        stored_hash=stored_hash,
        last_signal_at=last_signal,
        current_time=now,
        probe=failing_probe,
    )

    assert res.freshness_status == "STALE"
    assert res.outcome == RECONCILE_OUTCOME_STALE_DETECTED
    assert res.delta_sync_needed is False

    # Missing probe also marks STALE
    res_no_probe = await evaluate_24h_freshness_probe(
        stored_hash=stored_hash,
        last_signal_at=last_signal,
        current_time=now,
        probe=None,
    )
    assert res_no_probe.freshness_status == "STALE"
    assert res_no_probe.outcome == RECONCILE_OUTCOME_STALE_DETECTED


# 3. HMAC-SHA256 Constant-Time Verification & RFC 9457 Error Contract
def test_hmac_sha256_verification_constant_time() -> None:
    secret = "my-webhook-secret-key-123"  # pragma: allowlist secret
    body = b'{"ref": "refs/heads/main", "delivery_key": "del-001"}'
    valid_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert _verify_hmac(body, secret, valid_sig) is True
    assert _verify_hmac(body, secret, f"sha256={valid_sig}") is True
    assert _verify_hmac(body, secret, valid_sig.upper()) is True
    assert _verify_hmac(body, secret, "invalid-sig") is False
    assert _verify_hmac(body, "wrong-secret", valid_sig) is False
    assert _verify_hmac(body, secret, None) is False


def test_webhook_signature_invalid_error_rfc9457_contract() -> None:
    err = WebhookSignatureInvalidError(instance="/api/v1/webhooks/datasources/ds-123")
    assert err.http_status == 401
    assert err.error_code == "ERR_WEBHOOK_SIGNATURE_INVALID"
    assert err.type_slug == "webhook-signature-invalid"
    assert "https://orcia.io/problems/webhook-signature-invalid" in err.type_uri


# 4. Directory Confinement & Path Traversal Prevention
def test_resolve_confined_graph_dir_safe_and_traversal_prevention() -> None:
    with tempfile.TemporaryDirectory() as tmp_root:
        root = Path(tmp_root)
        ws_id = "ws-prod-01"
        ds_id = "ds-git-repo"

        resolved = resolve_confined_graph_dir(root, ws_id, ds_id)
        assert resolved == (root / ws_id / ds_id).resolve()
        assert resolved.is_relative_to(root)

        # Dangerous characters raise ValueError
        with pytest.raises(ValueError, match="Unsafe"):
            resolve_confined_graph_dir(root, "../escaping", ds_id)
        with pytest.raises(ValueError, match="Unsafe"):
            resolve_confined_graph_dir(root, ws_id, "ds/../../root")
        with pytest.raises(ValueError, match="Unsafe"):
            resolve_confined_graph_dir(root, "ws;rm -rf", ds_id)


def test_purge_confined_graph_dir_deletes_directory_when_disabled() -> None:
    with tempfile.TemporaryDirectory() as tmp_root:
        root = Path(tmp_root)
        target = resolve_confined_graph_dir(root, "ws-01", "ds-01")
        target.mkdir(parents=True, exist_ok=True)
        (target / "graph.db").write_text("sample code property graph")
        assert target.exists()

        purged = purge_confined_graph_dir(root, "ws-01", "ds-01")
        assert purged is True
        assert not target.exists()

        # Idempotent second purge returns False
        assert purge_confined_graph_dir(root, "ws-01", "ds-01") is False


# 5. Worker Codegraph Indexer Execution with Injectable Runner
def test_execute_codegraph_index_job_pure_purge_without_db() -> None:
    valid_w3c_trace = "0123456789abcdef0123456789abcdef"  # pragma: allowlist secret
    with tempfile.TemporaryDirectory() as tmp_root:
        res = execute_codegraph_index_job(
            workspace_id="ws-99",
            datasource_id="ds-99",
            trace_id=valid_w3c_trace,
            storage_root=tmp_root,
            engine=None,
        )
        assert isinstance(res, CodegraphIndexExecutionResult)
        assert res.status == "DISABLED"
        assert res.head_sha is None
        assert res.trace_id == valid_w3c_trace


# 6. Lightweight AST Indexing 0 $ LLM (Arbitrage 3A)
def test_lightweight_ast_indexing_zero_llm_cost() -> None:
    sample_code = """
def calculate_vat(amount: float, rate: float = 0.20) -> float:
    \"\"\"Compute French VAT amount.\"\"\"
    return amount * rate

class InvoiceService:
    def process_order(self, order_id: str) -> bool:
        \"\"\"Process invoice order.\"\"\"
        return True
"""
    doc, chunks, edges = DifferentiatedIncrementalIndexer.index_git_ast_and_code_graph(
        workspace_id="ws-ast-01",
        datasource_id="ds-ast-01",
        datasource_alias="repo-billing",
        repo_uri="git://gitlab.internal/billing.git",
        file_path="src/services/billing.py",
        python_source=sample_code,
        commit_sha="c0ffee1234567890",  # pragma: allowlist secret
    )

    assert doc.indexing_regime == "CODE_AST_GRAPH"
    assert doc.revision_tag == "c0ffee1234567890"  # pragma: allowlist secret
    assert len(chunks) == 3  # calculate_vat, InvoiceService, InvoiceService.process_order
    assert any(e.edge_type == "DEFINES" for e in edges)
    # Verifies compute_content_sha256 helper
    content_hash = compute_content_sha256(sample_code)
    assert len(content_hash) == 64
    assert compute_content_sha256(b"raw bytes") == compute_content_sha256("raw bytes")


# 7. Additional Branches for Codegraph Indexer & Reconciler Coverage
@pytest.mark.asyncio
async def test_freshness_probe_tz_naive_and_none_helpers() -> None:
    assert normalize_fingerprint(None) == ""
    now = datetime.now(UTC)
    naive_dt = datetime.now()  # naive
    res = await evaluate_24h_freshness_probe(
        stored_hash=None,
        last_signal_at=naive_dt,
        current_time=now,
    )
    assert res.freshness_status == "SYNCED"


@pytest.mark.asyncio
async def test_execute_codegraph_index_job_async_with_mocked_db_branches() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from orcia_core.bootstrap._internal.sql_datasource_freshness import DatasourceWebhookContext

    mock_engine = MagicMock()
    valid_trace = "0123456789abcdef0123456789abcdef"  # pragma: allowlist secret

    # Branch A: ds_ctx is disabled
    disabled_ctx = DatasourceWebhookContext(
        datasource_id="ds-dis",
        workspace_id="ws-dis",
        alias="repo-disabled",
        source_nature="SOURCE_CODE",
        target_ref=None,
        target_scope=None,
        fingerprint_hash=None,
        freshness_status="SYNCED",
        connector_id="conn-1",
        connector_base_url="https://git.internal",
        connector_scheme="git",
        webhook_secret_encrypted=None,
        codegraph_enabled=False,
        codegraph_auth_mode="SERVICE_ACCOUNT",
        codegraph_owner_user_id=None,
        codegraph_status="DISABLED",
    )

    with (
        tempfile.TemporaryDirectory() as tmp_root,
        patch(
            "orcia_worker.codegraph_indexer.get_datasource_webhook_context_from_postgres18",
            new=AsyncMock(return_value=disabled_ctx),
        ),
        patch(
            "orcia_worker.codegraph_indexer.update_datasource_freshness_state",
            new=AsyncMock(),
        ),
    ):
        res = await execute_codegraph_index_job_async(
            workspace_id="ws-dis",
            datasource_id="ds-dis",
            trace_id=valid_trace,
            storage_root=tmp_root,
            engine=mock_engine,
        )
        assert res.status == "DISABLED"

    # Branch B: enabled but missing token
    enabled_ctx = DatasourceWebhookContext(
        datasource_id="ds-en",
        workspace_id="ws-en",
        alias="repo-enabled",
        source_nature="SOURCE_CODE",
        target_ref=None,
        target_scope=None,
        fingerprint_hash=None,
        freshness_status="SYNCED",
        connector_id="conn-1",
        connector_base_url="https://git.internal",
        connector_scheme="git",
        webhook_secret_encrypted=None,
        codegraph_enabled=True,
        codegraph_auth_mode="SERVICE_ACCOUNT",
        codegraph_owner_user_id=None,
        codegraph_status="READY",
    )

    with (
        tempfile.TemporaryDirectory() as tmp_root,
        patch(
            "orcia_worker.codegraph_indexer.get_datasource_webhook_context_from_postgres18",
            new=AsyncMock(return_value=enabled_ctx),
        ),
        patch(
            "orcia_worker.codegraph_indexer.resolve_codegraph_indexer_token",
            new=AsyncMock(return_value=(None, "PAUSED_REFERENT_RENEWAL_REQUIRED")),
        ),
        patch(
            "orcia_worker.codegraph_indexer.update_datasource_freshness_state",
            new=AsyncMock(),
        ),
    ):
        res = await execute_codegraph_index_job_async(
            workspace_id="ws-en",
            datasource_id="ds-en",
            trace_id=valid_trace,
            storage_root=tmp_root,
            engine=mock_engine,
        )
        assert res.status == "PAUSED_REFERENT_RENEWAL_REQUIRED"

    # Branch C: enabled with token and index runner
    with tempfile.TemporaryDirectory() as tmp_root:
        runner_called = False

        def mock_runner(dir_path: Path, url: str | None, token: str | None) -> tuple[str, int]:
            nonlocal runner_called
            runner_called = True
            return ("head-commit-sha", 42)

        with (
            patch(
                "orcia_worker.codegraph_indexer.get_datasource_webhook_context_from_postgres18",
                new=AsyncMock(return_value=enabled_ctx),
            ),
            patch(
                "orcia_worker.codegraph_indexer.resolve_codegraph_indexer_token",
                new=AsyncMock(
                    return_value=(
                        "valid-secret-token",  # pragma: allowlist secret
                        "SERVICE_ACCOUNT",
                    )
                ),
            ),
            patch(
                "orcia_worker.codegraph_indexer.update_datasource_freshness_state",
                new=AsyncMock(),
            ),
        ):
            res = await execute_codegraph_index_job_async(
                workspace_id="ws-en",
                datasource_id="ds-en",
                trace_id=valid_trace,
                storage_root=tmp_root,
                engine=mock_engine,
                index_runner=mock_runner,
            )
            assert res.status == "READY"
            assert res.head_sha == "head-commit-sha"
            assert runner_called is True

    # Branch D: runner error triggers SYNC_ERROR and re-raise
    with tempfile.TemporaryDirectory() as tmp_root:

        def failing_runner(dir_path: Path, url: str | None, token: str | None) -> tuple[str, int]:
            raise RuntimeError("GitNexus CLI failed")

        with (
            patch(
                "orcia_worker.codegraph_indexer.get_datasource_webhook_context_from_postgres18",
                new=AsyncMock(return_value=enabled_ctx),
            ),
            patch(
                "orcia_worker.codegraph_indexer.resolve_codegraph_indexer_token",
                new=AsyncMock(
                    return_value=("valid-token", "SERVICE_ACCOUNT")  # pragma: allowlist secret
                ),
            ),
            patch(
                "orcia_worker.codegraph_indexer.update_datasource_freshness_state",
                new=AsyncMock(),
            ),
            pytest.raises(RuntimeError, match="GitNexus CLI failed"),
        ):
            await execute_codegraph_index_job_async(
                workspace_id="ws-en",
                datasource_id="ds-en",
                trace_id=valid_trace,
                storage_root=tmp_root,
                engine=mock_engine,
                index_runner=failing_runner,
            )
