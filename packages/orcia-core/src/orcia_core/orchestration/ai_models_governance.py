"""AI Models Hub Domain Governance Service (`Story 17.5`, `AD-21`, `Story 26.6a`).

Pure domain logic: zero SQL, zero FastAPI, zero httpx imports (`AD-19`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from orcia_core.orchestration._ai_models_delete_helpers import (
    apply_inmemory_delete_or_drain,
    evaluate_inmemory_delete_impact,
)
from orcia_core.orchestration._ai_models_governance_helpers import (
    apply_inmemory_mapping_update,
    apply_inmemory_test_result,
    build_inmemory_mapping_record,
    deactivate_other_inmemory_embeddings,
)
from orcia_core.orchestration.ai_models_crypto import (
    pack_encrypted_api_key,
    unpack_encrypted_api_key,
    validate_safe_llm_endpoint_url,
)
from orcia_core.orchestration.ai_models_errors import (
    LastTierModelInUseError,
    UnsafeLlmEndpointUrlError,
)
from orcia_core.orchestration.ai_models_records import (
    AiModelDeleteImpact,
    AiModelMappingRecord,
    HealthStatus,
    InferenceEffort,
    InferenceTier,
    LlmAuthMode,
    LlmModelUsage,
    LlmProtocolMode,
    PinRemovalMode,
    ScopeLevel,
)
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.secret_hint import SecretInputSpec


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class AiModelsHubService:
    """Pure in-memory governance service for AI model tier mappings (`Story 17.5`, `26.6a`)."""

    def __init__(
        self,
        *,
        vault_cipher: PassthroughVaultCipher | None = None,
        initial_mappings: tuple[AiModelMappingRecord, ...] = (),
    ) -> None:
        self._cipher = vault_cipher or PassthroughVaultCipher(master_key=b"0" * 32)
        self._mappings: dict[str, AiModelMappingRecord] = {m.id: m for m in initial_mappings}
        self._active_runs: dict[str, set[str]] = {}
        self._workflows_tier_reqs: dict[str, set[str]] = {}

    def register_active_run_pin(self, mapping_id: str, run_id: str) -> None:
        self._active_runs.setdefault(mapping_id, set()).add(run_id)

    def release_active_run_pin(self, mapping_id: str, run_id: str) -> None:
        if mapping_id in self._active_runs:
            self._active_runs[mapping_id].discard(run_id)

    def register_workflow_tier_requirement(self, workflow_id: str, tier: str) -> None:
        self._workflows_tier_reqs.setdefault(tier, set()).add(workflow_id)

    def list_mappings(
        self,
        *,
        scope_level: ScopeLevel | None = None,
        scope_id: str | None = None,
        inference_tier: InferenceTier | None = None,
        is_active: bool | None = None,
        usage: LlmModelUsage | None = None,
    ) -> list[AiModelMappingRecord]:
        items = [
            m
            for m in self._mappings.values()
            if (scope_level is None or m.scope_level == scope_level)
            and (scope_id is None or m.scope_id == scope_id)
            and (inference_tier is None or m.inference_tier == inference_tier)
            and (is_active is None or m.is_active == is_active)
            and (usage is None or m.usage == usage)
        ]
        return sorted(items, key=lambda m: (m.inference_tier, m.fallback_order, m.created_at))

    def get_active_embedding_mapping(self) -> AiModelMappingRecord | None:
        """Return currently active GLOBAL embedding mapping if any."""
        return next(
            (
                m
                for m in self._mappings.values()
                if m.usage == "embedding"
                and m.scope_level == "GLOBAL"
                and m.is_active
                and not m.draining
            ),
            None,
        )

    def get_mapping(self, mapping_id: str, *, instance: str | None = None) -> AiModelMappingRecord:
        rec = self._mappings.get(mapping_id)
        if rec is None:
            raise ResourceNotFoundError(
                detail_override=f"AI model mapping '{mapping_id}' not found.", instance=instance
            )
        return rec

    def create_mapping(
        self,
        *,
        scope_level: ScopeLevel = "WORKSPACE",
        scope_id: str,
        display_name: str,
        inference_tier: InferenceTier,
        effort: InferenceEffort = "default",
        provider_slug: str,
        model_family: str,
        model_name: str,
        fallback_model_name: str | None = None,
        endpoint_uri: str,
        auth_mode: LlmAuthMode = "api_key",
        protocol_mode: LlmProtocolMode = "openai_compatible",
        usage: LlmModelUsage = "chat",
        env_var_name: str | None = None,
        fallback_order: int = 1,
        max_tokens_budget: int = 8192,
        max_cost_usd: float = 10.0,
        secret_input: SecretInputSpec | None = None,
        supports_tools: bool | None = None,
        supports_tools_override: bool | None = None,
        actor_id: str = "system",
        instance: str | None = None,
    ) -> AiModelMappingRecord:
        now = _now_iso()
        rec = build_inmemory_mapping_record(
            cipher=self._cipher,
            now_iso=now,
            scope_level=scope_level,
            scope_id=scope_id,
            display_name=display_name,
            inference_tier=inference_tier,
            effort=effort,
            provider_slug=provider_slug,
            model_family=model_family,
            model_name=model_name,
            fallback_model_name=fallback_model_name,
            endpoint_uri=endpoint_uri,
            auth_mode=auth_mode,
            protocol_mode=protocol_mode,
            usage=usage,
            env_var_name=env_var_name,
            fallback_order=fallback_order,
            max_tokens_budget=max_tokens_budget,
            max_cost_usd=max_cost_usd,
            secret_input=secret_input,
            supports_tools=supports_tools,
            supports_tools_override=supports_tools_override,
            actor_id=actor_id,
            instance=instance,
        )
        if usage == "embedding" and scope_level == "GLOBAL":
            deactivate_other_inmemory_embeddings(self._mappings, now_iso=now)
        self._mappings[rec.id] = rec
        return rec

    def update_mapping(
        self,
        mapping_id: str,
        *,
        display_name: str | None = None,
        fallback_model_name: str | None = None,
        endpoint_uri: str | None = None,
        auth_mode: LlmAuthMode | None = None,
        protocol_mode: LlmProtocolMode | None = None,
        usage: LlmModelUsage | None = None,
        env_var_name: str | None = None,
        is_active: bool | None = None,
        secret_input: SecretInputSpec | None = None,
        supports_tools: bool | None = None,
        supports_tools_override: bool | None = None,
        clear_supports_tools_override: bool = False,
        actor_id: str = "system",
        instance: str | None = None,
    ) -> AiModelMappingRecord:
        current = self.get_mapping(mapping_id, instance=instance)
        updated = apply_inmemory_mapping_update(
            mappings=self._mappings,
            cipher=self._cipher,
            current=current,
            now_iso=_now_iso(),
            display_name=display_name,
            fallback_model_name=fallback_model_name,
            endpoint_uri=endpoint_uri,
            auth_mode=auth_mode,
            protocol_mode=protocol_mode,
            usage=usage,
            env_var_name=env_var_name,
            is_active=is_active,
            secret_input=secret_input,
            supports_tools=supports_tools,
            supports_tools_override=supports_tools_override,
            clear_supports_tools_override=clear_supports_tools_override,
            actor_id=actor_id,
            instance=instance,
        )
        self._mappings[mapping_id] = updated
        return updated

    def record_test_result(
        self,
        mapping_id: str,
        *,
        health_status: HealthStatus,
        latency_ms: int,
        supports_tools: bool | None = None,
        instance: str | None = None,
    ) -> AiModelMappingRecord:
        updated = apply_inmemory_test_result(
            self.get_mapping(mapping_id, instance=instance),
            health_status=health_status,
            latency_ms=latency_ms,
            supports_tools=supports_tools,
            now_iso=_now_iso(),
        )
        self._mappings[mapping_id] = updated
        return updated

    def evaluate_delete_impact(
        self, mapping_id: str, *, instance: str | None = None
    ) -> AiModelDeleteImpact:
        return evaluate_inmemory_delete_impact(
            mappings=self._mappings,
            workflows_tier_reqs=self._workflows_tier_reqs,
            active_runs=self._active_runs,
            mapping_id=mapping_id,
            current=self.get_mapping(mapping_id, instance=instance),
        )

    def delete_or_drain_mapping(
        self,
        mapping_id: str,
        *,
        mode: PinRemovalMode = "reject",
        actor_role: str = "PLATFORM_ADMIN",
        instance: str | None = None,
    ) -> AiModelMappingRecord | None:
        current = self.get_mapping(mapping_id, instance=instance)
        return apply_inmemory_delete_or_drain(
            mappings=self._mappings,
            impact=self.evaluate_delete_impact(mapping_id, instance=instance),
            current=current,
            mapping_id=mapping_id,
            mode=mode,
            actor_role=actor_role,
            now_iso=_now_iso(),
            instance=instance,
        )

    def resolve_decrypted_api_key(
        self, mapping_id: str, *, instance: str | None = None
    ) -> str | None:
        current = self.get_mapping(mapping_id, instance=instance)
        if not current.encrypted_api_key:
            return None
        host = urlparse(current.endpoint_uri).netloc or "default"
        return unpack_encrypted_api_key(
            self._cipher,
            mapping_id=mapping_id,
            packed=current.encrypted_api_key,
            target_host=host,
        )


__all__ = [
    "AiModelDeleteImpact",
    "AiModelMappingRecord",
    "AiModelsHubService",
    "HealthStatus",
    "InferenceEffort",
    "InferenceTier",
    "LastTierModelInUseError",
    "LlmAuthMode",
    "LlmProtocolMode",
    "PinRemovalMode",
    "ScopeLevel",
    "UnsafeLlmEndpointUrlError",
    "pack_encrypted_api_key",
    "unpack_encrypted_api_key",
    "validate_safe_llm_endpoint_url",
]
