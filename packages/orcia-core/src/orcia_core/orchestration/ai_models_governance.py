"""AI Models Hub Domain Governance Service (`Story 17.5`, `AD-21`).

Pure domain logic: zero SQL, zero FastAPI, zero httpx imports (`AD-19`).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from urllib.parse import urlparse

from orcia_core.orchestration.ai_models_crypto import (
    apply_ai_model_secret_input,
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
    LlmProtocolMode,
    PinRemovalMode,
    ScopeLevel,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ResourcePinnedByActiveRunsError,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.secret_hint import SecretInputSpec, SecretStatusView
from orcia_kernel.ids import new_uuid7_str


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class AiModelsHubService:
    """Pure in-memory governance service for AI model tier mappings (`Story 17.5`)."""

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
    ) -> list[AiModelMappingRecord]:
        items = list(self._mappings.values())
        if scope_level is not None:
            items = [m for m in items if m.scope_level == scope_level]
        if scope_id is not None:
            items = [m for m in items if m.scope_id == scope_id]
        if inference_tier is not None:
            items = [m for m in items if m.inference_tier == inference_tier]
        if is_active is not None:
            items = [m for m in items if m.is_active == is_active]
        return sorted(items, key=lambda m: (m.inference_tier, m.fallback_order, m.created_at))

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
        env_var_name: str | None = None,
        fallback_order: int = 1,
        max_tokens_budget: int = 8192,
        max_cost_usd: float = 10.0,
        secret_input: SecretInputSpec | None = None,
        actor_id: str = "system",
        instance: str | None = None,
    ) -> AiModelMappingRecord:
        clean_url = validate_safe_llm_endpoint_url(endpoint_uri, instance=instance)
        mapping_id = new_uuid7_str()
        now = _now_iso()
        host = urlparse(clean_url).netloc or "default"
        init_sec = SecretStatusView(
            configured=False,
            fingerprint=None,
            masked_hint=None,
            updated_at=now,
            updated_by=actor_id,
        )
        sec_status, encrypted_key = apply_ai_model_secret_input(
            self._cipher,
            mapping_id=mapping_id,
            target_host=host,
            current_status=init_sec,
            current_encrypted_key=None,
            secret_input=secret_input if auth_mode == "api_key" else None,
            now_iso=now,
            actor_id=actor_id,
        )

        rec = AiModelMappingRecord(
            id=mapping_id,
            scope_level=scope_level,
            scope_id=scope_id,
            display_name=display_name.strip() or f"{provider_slug} / {model_name}",
            inference_tier=inference_tier,
            effort=effort,
            provider_slug=provider_slug,
            model_family=model_family,
            model_name=model_name,
            fallback_model_name=fallback_model_name,
            endpoint_uri=clean_url,
            auth_mode=auth_mode,
            protocol_mode=protocol_mode,
            env_var_name=env_var_name,
            fallback_order=fallback_order,
            max_tokens_budget=max_tokens_budget,
            max_cost_usd=max_cost_usd,
            is_active=True,
            draining=False,
            health_status="UNTESTED",
            created_at=now,
            updated_at=now,
            secret_status=sec_status,
            encrypted_api_key=encrypted_key,
        )
        self._mappings[mapping_id] = rec
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
        env_var_name: str | None = None,
        is_active: bool | None = None,
        secret_input: SecretInputSpec | None = None,
        actor_id: str = "system",
        instance: str | None = None,
    ) -> AiModelMappingRecord:
        current = self.get_mapping(mapping_id, instance=instance)
        now = _now_iso()
        clean_url = current.endpoint_uri
        if endpoint_uri is not None:
            clean_url = validate_safe_llm_endpoint_url(endpoint_uri, instance=instance)
        host = urlparse(clean_url).netloc or "default"

        sec_status, encrypted_key = apply_ai_model_secret_input(
            self._cipher,
            mapping_id=mapping_id,
            target_host=host,
            current_status=current.secret_status,
            current_encrypted_key=current.encrypted_api_key,
            secret_input=secret_input,
            now_iso=now,
            actor_id=actor_id,
        )

        updated = replace(
            current,
            display_name=display_name.strip() if display_name is not None else current.display_name,
            fallback_model_name=(
                fallback_model_name
                if fallback_model_name is not None
                else current.fallback_model_name
            ),
            endpoint_uri=clean_url,
            auth_mode=auth_mode if auth_mode is not None else current.auth_mode,
            protocol_mode=protocol_mode if protocol_mode is not None else current.protocol_mode,
            env_var_name=env_var_name if env_var_name is not None else current.env_var_name,
            is_active=is_active if is_active is not None else current.is_active,
            updated_at=now,
            secret_status=sec_status,
            encrypted_api_key=encrypted_key,
        )
        self._mappings[mapping_id] = updated
        return updated

    def record_test_result(
        self,
        mapping_id: str,
        *,
        health_status: HealthStatus,
        latency_ms: int,
        instance: str | None = None,
    ) -> AiModelMappingRecord:
        current = self.get_mapping(mapping_id, instance=instance)
        updated = replace(
            current,
            health_status=health_status,
            last_latency_ms=latency_ms,
            last_tested_at=_now_iso(),
            updated_at=_now_iso(),
        )
        self._mappings[mapping_id] = updated
        return updated

    def evaluate_delete_impact(
        self, mapping_id: str, *, instance: str | None = None
    ) -> AiModelDeleteImpact:
        current = self.get_mapping(mapping_id, instance=instance)
        other_active = [
            m
            for m in self._mappings.values()
            if m.id != mapping_id
            and m.inference_tier == current.inference_tier
            and m.is_active
            and not m.draining
        ]
        wf_deps = tuple(sorted(self._workflows_tier_reqs.get(current.inference_tier, set())))
        run_pins = tuple(sorted(self._active_runs.get(mapping_id, set())))
        is_last = len(other_active) == 0

        return AiModelDeleteImpact(
            mapping_id=mapping_id,
            inference_tier=current.inference_tier,
            model_name=current.model_name,
            remaining_active_for_tier=len(other_active),
            dependent_workflows_count=len(wf_deps),
            dependent_workflow_ids=wf_deps,
            pinned_active_runs_count=len(run_pins),
            pinned_run_ids=run_pins,
            is_last_active_for_tier=is_last,
        )

    def delete_or_drain_mapping(
        self,
        mapping_id: str,
        *,
        mode: PinRemovalMode = "reject",
        actor_role: str = "PLATFORM_ADMIN",
        instance: str | None = None,
    ) -> AiModelMappingRecord | None:
        if actor_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        impact = self.evaluate_delete_impact(mapping_id, instance=instance)

        if (
            impact.dependent_workflows_count > 0
            and impact.is_last_active_for_tier
            and mode != "force"
        ):
            raise LastTierModelInUseError(instance=instance)

        if impact.pinned_active_runs_count > 0:
            if mode == "reject":
                raise ResourcePinnedByActiveRunsError(instance=instance)
            if mode == "drain":
                current = self.get_mapping(mapping_id, instance=instance)
                draining = replace(current, draining=True, is_active=False, updated_at=_now_iso())
                self._mappings[mapping_id] = draining
                return draining

        self._mappings.pop(mapping_id, None)
        return None

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
