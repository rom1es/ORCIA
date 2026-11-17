"""Security tests for Story 7.0b: SSRF blocking and zero secret leak in LogSink adapter."""

from __future__ import annotations

import json

import httpx
import pytest

from orcia_core.kernel.secret_ports import SecretProviderPort, SecretRef, WorkspaceEnvelopeKeyRecord
from orcia_core.observability import ElasticsearchLogSinkAdapter, configure_logging
from orcia_core.observability.errors import LogSinkQueryFailedError, UnsafeLogSinkUrlError
from orcia_core.ports.log_sink import LogQuery


class _StaticSecretProvider(SecretProviderPort):
    def __init__(self, value: str) -> None:
        self._value = value

    def resolve_secret(self, ref: SecretRef) -> str:
        return self._value

    def store_secret(
        self, ref: SecretRef, plaintext_value: str, *, actor_id: str = "system"
    ) -> SecretRef:
        return ref

    def rotate_workspace_dek(
        self, workspace_id: str, *, actor_id: str
    ) -> WorkspaceEnvelopeKeyRecord:
        raise NotImplementedError


async def test_log_sink_secret_ref_auth_never_leaks_in_logs_on_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify `SecretRef` credentials are injected in headers and redacted if an error occurs."""
    configure_logging(service="api", log_level="DEBUG")
    secret_token = "es_canary_api_key_7_0b_secret_987654"  # pragma: allowlist secret
    seen_auth_headers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_auth_headers.append(request.headers.get("Authorization", ""))
        return httpx.Response(
            401,
            json={"error": f"Unauthorized for ApiKey {secret_token}"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = ElasticsearchLogSinkAdapter(
            "https://opensearch.corp.internal:9200",
            http_client=client,
            secret_provider=_StaticSecretProvider(secret_token),
            auth_secret_ref=SecretRef(uri="secret://platform/logsink/api-key"),
        )
        with pytest.raises(LogSinkQueryFailedError):
            await adapter.query_logs(LogQuery(service="api"))

    assert seen_auth_headers == [f"ApiKey {secret_token}"]
    captured = capsys.readouterr()
    assert captured.err == ""
    assert secret_token not in captured.out
    assert json.loads(captured.out.splitlines()[-1])["message"] == "log_sink_query_failed"


@pytest.mark.parametrize(
    "ssrf_url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://[fe80::1]:9200/_cluster/health",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://100.100.100.200/latest/meta-data/",
    ],
)
def test_log_sink_ssrf_guard_blocks_cloud_metadata(ssrf_url: str) -> None:
    """Verify SSRF guard rejects Cloud Metadata endpoints (`NFR-SEC-1`)."""
    with pytest.raises(UnsafeLogSinkUrlError):
        ElasticsearchLogSinkAdapter(ssrf_url)
