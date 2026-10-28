"""Production `LiteLLMAdapter` implementing `orcia_kernel.ports.LLMPort` (`AD-10`, `ARCH-P1`).

Supports both OpenAI-compatible LiteLLM HTTP gateway calls (`httpx.AsyncClient`) and
deterministic cassette fallback (`0 $` external LLM calls in CI).
"""

from __future__ import annotations

from typing import Any

import httpx

from orcia_core.observability.logging import get_current_trace_id
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.ports import (
    LlmCompletionResponse,
    LLMPort,
    LlmPromptRequest,
    assert_model_orthogonality,
    compute_prompt_sha256,
)


class LiteLLMAdapter(LLMPort):
    """Hexagonal `LLMPort` adapter backed by LiteLLM / OpenAI-compatible endpoints (`AD-10`)."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:4000/v1",
        api_key: str = "sk-orcia-local",  # pragma: allowlist secret
        cost_per_1k_input_usd: float = 0.003,
        cost_per_1k_output_usd: float = 0.015,
        http_client: httpx.AsyncClient | None = None,
        fallback_cassette: DeterministicCassetteLLM | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._cost_in = cost_per_1k_input_usd
        self._cost_out = cost_per_1k_output_usd
        self._client = http_client
        self._fallback = fallback_cassette

    async def complete(self, request: LlmPromptRequest) -> LlmCompletionResponse:
        """Execute a completion request while enforcing AD-10 model family orthogonality."""
        if request.executor_model_family is not None:
            assert_model_orthogonality(
                executor_model_family=request.executor_model_family,
                evaluator_model_family=request.model_family,
            )

        if self._fallback is not None and self._client is None:
            return await self._fallback.complete(request)

        prompt_sha256 = compute_prompt_sha256(request)
        trace_id = get_current_trace_id()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Trace-Id": trace_id,
        }
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
            },
        }

        if self._client is not None:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body: dict[str, Any] = response.json()
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                body = response.json()

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
