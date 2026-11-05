"""Production `LiteLLMAdapter` implementing `orcia_kernel.ports.LLMPort` (`AD-10`, `DEC-SEC-01`).

Supports OpenAI-compatible LiteLLM HTTP gateway calls (`httpx.AsyncClient`), governed
`ConnectorInvoker` retries (`Retry-After`, circuit breaker, `AD-12` budget), `SecretRef`
resolution via `SecretProviderPort` (`0` default `sk-*` key in code, `NFR-SEC-4`), and
deterministic cassette fallback (`0 $` external LLM calls in CI).
"""

from __future__ import annotations

from typing import Any

import httpx

from orcia_core.observability.logging import (
    get_current_trace_id,
    get_logger,
    register_sensitive_secret_value,
)
from orcia_core.permissions.connector_invoker import (
    ConnectorInvocationOutcome,
    ConnectorInvoker,
)
from orcia_core.permissions.secret_manager import EnvelopeVaultSecretProvider
from orcia_core.testing.cassette_llm import CassetteEntry, DeterministicCassetteLLM
from orcia_kernel.errors import (
    FunctionalConnectorError,
    OrciaDomainError,
    PermanentInfraError,
    RateLimitedError,
    TransientInfraError,
    UpstreamTimeoutError,
)
from orcia_kernel.ports import (
    ConnectorCapabilities,
    ConnectorFetchResult,
    ConnectorHealthStatus,
    ConnectorInvokeResult,
    ConnectorPort,
    LlmCompletionResponse,
    LLMPort,
    LlmPromptRequest,
    SecretProviderPort,
    SecretRef,
    assert_model_orthogonality,
    compute_prompt_sha256,
)

DEFAULT_LITELLM_SECRET_REF = SecretRef(uri="secret://llm/litellm/gateway-api-key")


class _LiteLLMHttpConnector(ConnectorPort):
    """Internal `ConnectorPort` adapter wrapping synchronous/async LiteLLM gateway calls."""

    def __init__(self, adapter: LiteLLMAdapter) -> None:
        self._adapter = adapter

    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            scheme="litellm",
            display_name="LiteLLM AI Gateway",
            pack_name="orcia-core",
            supports_read=True,
            supports_write=True,
        )

    def fetch(self, uri: str) -> ConnectorFetchResult:
        return ConnectorFetchResult(
            uri=uri,
            scheme="litellm",
            resolved_version="v1",
            content_bytes=b"{}",
        )

    def invoke(
        self, action: str, payload: dict[str, Any], idempotency_key: str
    ) -> ConnectorInvokeResult:
        response_body = self._adapter._execute_gateway_call_sync(payload)
        return ConnectorInvokeResult(
            scheme="litellm",
            action=action,
            idempotency_key=idempotency_key,
            replayed_from_idempotency_cache=False,
            status="SUCCEEDED",
            output=response_body,
        )

    def health(self) -> ConnectorHealthStatus:
        return ConnectorHealthStatus(scheme="litellm", state="HEALTHY", latency_ms=1.0)

    def map_error(self, exc: Exception) -> OrciaDomainError:
        if isinstance(exc, OrciaDomainError):
            return exc
        if isinstance(exc, httpx.TimeoutException):
            return UpstreamTimeoutError(detail_override=str(exc))
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            if code == 429:
                retry_hdr = exc.response.headers.get("Retry-After", "1")
                try:
                    retry_s = float(retry_hdr)
                except ValueError:
                    retry_s = 1.0
                return RateLimitedError(retry_after_s=retry_s, detail_override=str(exc))
            if code in (502, 503, 504):
                return TransientInfraError(retry_after_s=0.05, detail_override=str(exc))
            if 400 <= code < 500:
                return FunctionalConnectorError(detail_override=str(exc))
            return PermanentInfraError(detail_override=str(exc))
        return TransientInfraError(retry_after_s=0.05, detail_override=str(exc))


class LiteLLMAdapter(LLMPort):
    """Hexagonal `LLMPort` adapter backed by LiteLLM, `SecretRef` & `ConnectorInvoker`."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:4000/v1",
        api_key: str | SecretRef | None = None,
        api_key_ref: SecretRef | None = None,
        secret_provider: SecretProviderPort | None = None,
        connector_invoker: ConnectorInvoker | None = None,
        cost_per_1k_input_usd: float = 0.003,
        cost_per_1k_output_usd: float = 0.015,
        http_client: httpx.AsyncClient | None = None,
        fallback_cassette: DeterministicCassetteLLM | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._secret_provider: SecretProviderPort = secret_provider or EnvelopeVaultSecretProvider()
        if api_key_ref is not None:
            self._api_key_ref: SecretRef | None = api_key_ref
        elif isinstance(api_key, SecretRef):
            self._api_key_ref = api_key
        elif isinstance(api_key, str) and api_key.strip():
            register_sensitive_secret_value(api_key)
            self._api_key_ref = self._secret_provider.store_secret(
                DEFAULT_LITELLM_SECRET_REF, api_key.strip(), actor_id="litellm_init"
            )
        else:
            self._api_key_ref = None

        self._invoker = connector_invoker
        self._cost_in = cost_per_1k_input_usd
        self._cost_out = cost_per_1k_output_usd
        self._client = http_client
        self._fallback = fallback_cassette
        self._last_invocation_outcome: ConnectorInvocationOutcome | None = None

    @property
    def api_key_ref(self) -> SecretRef | None:
        """Return the opaque `SecretRef` configured for this adapter (never plaintext)."""
        return self._api_key_ref

    @property
    def last_invocation_outcome(self) -> ConnectorInvocationOutcome | None:
        """Return the latest `ConnectorInvocationOutcome` when `connector_invoker` is used."""
        return self._last_invocation_outcome

    def register(self, key_or_sha256: str, entry: CassetteEntry) -> None:
        """Register or override a deterministic cassette entry on the offline fallback cassette."""
        if self._fallback is None:
            self._fallback = DeterministicCassetteLLM()
        self._fallback.register(key_or_sha256, entry)

    @property
    def call_history(self) -> tuple[LlmPromptRequest, ...]:
        """Return immutable tuple of all recorded requests on the fallback cassette."""
        if self._fallback is None:
            return ()
        return self._fallback.call_history

    def _resolve_api_key(self) -> str:
        """Resolve API key on-the-fly from `SecretProviderPort` (`DEC-SEC-01`, `NFR-SEC-4`)."""
        if self._api_key_ref is None:
            raise PermanentInfraError(
                detail_override=(
                    "Aucune SecretRef configurée pour LiteLLMAdapter (DEC-SEC-01: "
                    "les clés par défaut en dur sont interdites)."
                )
            )
        resolved = self._secret_provider.resolve_secret(self._api_key_ref)
        register_sensitive_secret_value(resolved)
        return resolved

    def _execute_gateway_call_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute an HTTP POST to LiteLLM inside a sync connector call."""
        import asyncio
        import concurrent.futures

        async def _do_post() -> dict[str, Any]:
            return await self._post_chat_completions(payload)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_do_post())
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(_do_post())).result()

    async def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        resolved_key = self._resolve_api_key()
        trace_id = str(payload.get("metadata", {}).get("trace_id") or get_current_trace_id())
        headers = {
            "Authorization": f"Bearer {resolved_key}",
            "Content-Type": "application/json",
            "X-Trace-Id": trace_id,
        }
        get_logger("orcia.litellm").info(
            "litellm.gateway.call",
            model=payload.get("model"),
            secret_ref=str(self._api_key_ref),
            authorization_preview=f"Bearer {resolved_key}",
        )
        if self._client is not None:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            return body
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
            return body

    async def complete(self, request: LlmPromptRequest) -> LlmCompletionResponse:
        """Execute a completion request while enforcing AD-10 model family orthogonality."""
        if request.executor_model_family is not None:
            assert_model_orthogonality(
                executor_model_family=request.executor_model_family,
                evaluator_model_family=request.model_family,
            )

        if self._fallback is not None and self._client is None and self._invoker is None:
            return await self._fallback.complete(request)

        prompt_sha256 = compute_prompt_sha256(request)
        trace_id = get_current_trace_id()
        payload: dict[str, Any] = {
            "model": request.model_id,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "metadata": {
                **request.metadata,
                "model_family": request.model_family,
                "execution_mode": request.execution_mode,
                "trace_id": trace_id,
                "secret_ref": str(self._api_key_ref) if self._api_key_ref else "none",
            },
        }

        if self._invoker is not None:
            connector = _LiteLLMHttpConnector(self)
            outcome = self._invoker.invoke(
                scheme="litellm",
                action="chat.completions",
                payload=payload,
                idempotency_key=f"litellm:{prompt_sha256}",
                connector=connector,
            )
            self._last_invocation_outcome = outcome
            if outcome.status != "SUCCEEDED":
                raise PermanentInfraError(
                    detail_override=(
                        f"Échec de l'appel gouverné LiteLLM via ConnectorInvoker: "
                        f"status={outcome.status}, code={outcome.error_code}"
                    )
                )
            body = dict(outcome.sanitized_output)
        else:
            body = await self._post_chat_completions(payload)

        choices = body.get("choices", [])
        content = str(choices[0]["message"]["content"]) if choices else ""
        usage = body.get("usage", {})
        input_tokens = int(usage.get("prompt_tokens", max(1, len(request.user_prompt) // 4)))
        output_tokens = int(usage.get("completion_tokens", max(1, len(content) // 4)))
        cost = round(
            (input_tokens / 1000.0) * self._cost_in + (output_tokens / 1000.0) * self._cost_out,
            6,
        )
        return LlmCompletionResponse(
            content=content,
            model_family=request.model_family,
            model_id=request.model_id,
            prompt_sha256=prompt_sha256,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
            scenario_tag="LITELLM_GATEWAY",
        )
