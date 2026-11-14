"""Unit tests for Story 17.5: AI Models Hub Secrets, SSRF Guard, and Lifecycle Governance."""

import Crypto.Cipher.AES  # noqa: F401
import pytest

from orcia_core.kernel.secret_ports import SecretRef
from orcia_core.orchestration.ai_models_crypto import (
    pack_encrypted_api_key,
    unpack_encrypted_api_key,
    validate_safe_llm_endpoint_url,
)
from orcia_core.orchestration.ai_models_errors import (
    LastTierModelInUseError,
    UnsafeLlmEndpointUrlError,
)
from orcia_core.orchestration.ai_models_governance import AiModelsHubService
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ResourcePinnedByActiveRunsError,
)
from orcia_core.permissions import (
    PassthroughVaultCipher,
    SecretInputSpec,
    SecretStatusView,
    compute_secret_masked_hint,
)
from orcia_core.permissions.errors import ValidationDomainError
from orcia_core.permissions.secret_hint import (
    DefaultMemorySecretProvider,
    compute_etag,
    compute_value_sha256,
)


def test_compute_secret_masked_hint_rules() -> None:
    # >= 16 chars: 8 bullets + last 4 chars
    res1 = compute_secret_masked_hint("sk-ant-api03-abcdef123456")  # pragma: allowlist secret
    assert res1 == "••••••••3456"
    res2 = compute_secret_masked_hint("1234567890abcdef")  # pragma: allowlist secret
    assert res2 == "••••••••cdef"

    # 12 to 15 chars: 8 bullets + last 3 chars
    assert compute_secret_masked_hint("123456789012") == "••••••••012"
    assert compute_secret_masked_hint("sk-test-12345") == "••••••••345"

    # < 12 chars: None (too short to expose hint safely)
    assert compute_secret_masked_hint("shortkey") is None
    assert compute_secret_masked_hint("12345678901") is None

    # Pure bullets or asterisks: None
    assert compute_secret_masked_hint("••••••••••••••••") is None
    assert compute_secret_masked_hint("****************") is None
    assert compute_secret_masked_hint("   ") is None


def test_aes256_vault_envelope_encryption_and_decryption() -> None:
    cipher = PassthroughVaultCipher(master_key=b"0" * 32)
    resource_id = "01932900-0001-7000-8000-000000000001"
    plaintext = "sk-live-secret-test-key-999888777"

    packed = pack_encrypted_api_key(
        cipher,
        mapping_id=resource_id,
        plaintext_key=plaintext,
        target_host="api.anthropic.com",
    )
    assert ":" in packed

    decrypted = unpack_encrypted_api_key(
        cipher,
        mapping_id=resource_id,
        packed=packed,
        target_host="api.anthropic.com",
    )
    assert decrypted == plaintext


def test_ssrf_guard_blocks_cloud_metadata_and_link_local_ips() -> None:
    # AWS/GCP/Azure link-local metadata
    with pytest.raises(UnsafeLlmEndpointUrlError) as exc_info:
        validate_safe_llm_endpoint_url("http://169.254.169.254/latest/meta-data")
    assert exc_info.value.error_code == "ERR_UNSAFE_LLM_ENDPOINT_URL"

    # Subnet 169.254.0.0/16
    with pytest.raises(UnsafeLlmEndpointUrlError):
        validate_safe_llm_endpoint_url("http://169.254.0.1/v1/chat")

    # IPv6 link-local fe80::/10
    with pytest.raises(UnsafeLlmEndpointUrlError):
        validate_safe_llm_endpoint_url("http://[fe80::1]/v1")

    # Google Cloud metadata DNS
    with pytest.raises(UnsafeLlmEndpointUrlError):
        validate_safe_llm_endpoint_url("http://metadata.google.internal/computeMetadata/v1")

    # Alibaba Cloud metadata IP
    with pytest.raises(UnsafeLlmEndpointUrlError):
        validate_safe_llm_endpoint_url("http://100.100.100.200/latest/meta-data")

    # Non-HTTP schemes
    with pytest.raises(UnsafeLlmEndpointUrlError):
        validate_safe_llm_endpoint_url("ftp://example.com/api")

    with pytest.raises(UnsafeLlmEndpointUrlError):
        validate_safe_llm_endpoint_url("file:///etc/passwd")


def test_ssrf_guard_allows_safe_remote_and_local_endpoints() -> None:
    # Commercial HTTPS APIs
    validate_safe_llm_endpoint_url("https://api.anthropic.com/v1")
    validate_safe_llm_endpoint_url("https://api.openai.com/v1")
    validate_safe_llm_endpoint_url("https://generativelanguage.googleapis.com/v1beta")

    # Localhost & Loopback
    validate_safe_llm_endpoint_url("http://localhost:11434/v1")
    validate_safe_llm_endpoint_url("http://127.0.0.1:11434/v1")
    validate_safe_llm_endpoint_url("http://[::1]:11434/v1")

    # Internal enterprise domains
    validate_safe_llm_endpoint_url("http://ollama.internal:11434/v1")
    validate_safe_llm_endpoint_url("http://vllm.local:8000/v1")


def test_ai_models_hub_service_crud_and_secret_redaction() -> None:
    service = AiModelsHubService()

    created = service.create_mapping(
        scope_id="GLOBAL",
        display_name="Claude 3.7 Sonnet (Défaut)",
        inference_tier="medium",
        effort="balanced",
        provider_slug="anthropic",
        model_family="Anthropic",
        model_name="claude-3-7-sonnet",
        fallback_model_name="claude-3-5-haiku",
        endpoint_uri="https://api.anthropic.com/v1",
        auth_mode="api_key",
        protocol_mode="openai_compatible",
        secret_input=SecretInputSpec(
            action="set",
            plaintext_value="sk-ant-api03-verylongsecretkey1234",
        ),
        actor_id="marc",
    )

    assert created.id is not None
    assert created.secret_status.configured is True
    assert created.secret_status.masked_hint == "••••••••1234"
    assert created.secret_status.fingerprint is not None
    assert created.encrypted_api_key is not None
    assert "sk-ant" not in created.encrypted_api_key

    # Fetch mapping: secret status has hint, no plaintext key exposed
    fetched = service.get_mapping(created.id)
    assert fetched is not None
    assert fetched.display_name == "Claude 3.7 Sonnet (Défaut)"
    assert fetched.secret_status.masked_hint == "••••••••1234"

    # Update mapping: update fallback
    updated = service.update_mapping(
        created.id,
        display_name="Claude 3.7 Sonnet (Renommé)",
        fallback_model_name="claude-3-7-haiku",
        actor_id="marc",
    )
    assert updated.display_name == "Claude 3.7 Sonnet (Renommé)"
    assert updated.fallback_model_name == "claude-3-7-haiku"
    # Secret status is preserved on keep
    assert updated.secret_status.masked_hint == "••••••••1234"


def test_ai_models_hub_delete_governance_and_drainage() -> None:
    service = AiModelsHubService()

    # Create a sole model on tier "complex"
    m1 = service.create_mapping(
        scope_id="GLOBAL",
        display_name="Gemini Argon (Deep)",
        inference_tier="complex",
        effort="deep",
        provider_slug="google",
        model_family="Google Gemini",
        model_name="gemini-argon",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
        auth_mode="none_local",
    )

    # Register workflow requirement and active run pin
    service.register_workflow_tier_requirement("wf-published-1", "complex")
    service.register_active_run_pin(m1.id, "run-1")

    impact = service.evaluate_delete_impact(m1.id)
    assert impact.is_last_active_for_tier is True
    assert impact.dependent_workflows_count == 1
    assert impact.pinned_active_runs_count == 1

    # Reject mode raises LastTierModelInUseError
    with pytest.raises(LastTierModelInUseError) as exc_info:
        service.delete_or_drain_mapping(m1.id, mode="reject")
    assert exc_info.value.error_code == "ERR_AI_MODEL_REQUIRED_BY_WORKFLOWS"

    # Add a second active model for "complex" so tier has a remaining active model
    service.create_mapping(
        scope_id="GLOBAL",
        display_name="Claude 3.7 Sonnet (Complex Backup)",
        inference_tier="complex",
        effort="deep",
        provider_slug="anthropic",
        model_family="Anthropic",
        model_name="claude-3-7-sonnet",
        endpoint_uri="https://api.anthropic.com/v1",
        auth_mode="none_local",
    )

    # Drain mode now puts model in draining state because pinned run exists
    drained = service.delete_or_drain_mapping(m1.id, mode="drain")
    assert drained is not None
    assert drained.draining is True
    assert drained.is_active is False

    # Force mode deletes it completely
    deleted = service.delete_or_drain_mapping(m1.id, mode="force")
    assert deleted is None
    with pytest.raises(ResourceNotFoundError):
        service.get_mapping(m1.id)


def test_ai_models_hub_service_listing_and_filtering() -> None:
    service = AiModelsHubService()
    m_simple = service.create_mapping(
        scope_id="0195f000-0000-7000-8000-000000000301",
        display_name="Haiku Simple",
        inference_tier="simple",
        provider_slug="anthropic",
        model_family="Anthropic",
        model_name="claude-3-5-haiku",
        endpoint_uri="https://api.anthropic.com/v1",
        auth_mode="none_local",
    )
    service.create_mapping(
        scope_id="0195f000-0000-7000-8000-000000000301",
        display_name="Sonnet Medium",
        inference_tier="medium",
        provider_slug="anthropic",
        model_family="Anthropic",
        model_name="claude-3-7-sonnet",
        endpoint_uri="https://api.anthropic.com/v1",
        auth_mode="none_local",
    )

    all_models = service.list_mappings()
    assert len(all_models) == 2

    simple_only = service.list_mappings(inference_tier="simple")
    assert len(simple_only) == 1
    assert simple_only[0].id == m_simple.id

    by_scope = service.list_mappings(
        scope_level="WORKSPACE",
        scope_id="0195f000-0000-7000-8000-000000000301",
    )
    assert len(by_scope) == 2

    # Test connection result recording
    tested = service.record_test_result(m_simple.id, health_status="OPERATIONAL", latency_ms=85)
    assert tested.health_status == "OPERATIONAL"
    assert tested.last_latency_ms == 85
    assert tested.last_tested_at is not None

    # Test key resolution when not configured
    key = service.resolve_decrypted_api_key(m_simple.id)
    assert key is None


def test_ai_models_hub_pinned_rejection_and_observer_guard() -> None:
    service = AiModelsHubService()
    m = service.create_mapping(
        scope_id="GLOBAL",
        display_name="Test Model",
        inference_tier="auto",
        provider_slug="test",
        model_family="Test",
        model_name="test-model",
        endpoint_uri="https://example.com/v1",
        auth_mode="none_local",
    )
    service.register_active_run_pin(m.id, "run-101")

    # Observer cannot delete
    with pytest.raises(ObserverModeReadOnlyError):
        service.delete_or_drain_mapping(m.id, actor_role="OBSERVER")

    # Reject mode raises ResourcePinnedByActiveRunsError when runs are pinned (0 workflows)
    with pytest.raises(ResourcePinnedByActiveRunsError):
        service.delete_or_drain_mapping(m.id, mode="reject")


def test_secret_status_view_and_masked_hint_edge_cases() -> None:
    # All asterisks or bullets returns None
    assert compute_secret_masked_hint("********") is None
    assert compute_secret_masked_hint("••••••••••••") is None
    assert compute_secret_masked_hint("   ") is None

    # SecretStatusView defaults and serialization
    view = SecretStatusView(
        configured=True,
        fingerprint="sha256:12345678",
        masked_hint="••••••••5678",
        updated_at="2026-11-14T10:00:00Z",
        updated_by="admin",
    )
    assert view.configured is True
    assert view.fingerprint == "sha256:12345678"
    assert view.masked_hint == "••••••••5678"

    # ETag and canonical value checksum
    cs = compute_value_sha256({"model": "gpt-4o"}, "sha256:12345678")
    assert cs.startswith("sha256:")
    etag = compute_etag("setting-1", 2, cs)
    assert etag.startswith('W/"2-')

    # SecretInputSpec validation
    with pytest.raises(ValidationDomainError):
        SecretInputSpec(action="set", plaintext_value="")

    with pytest.raises(ValidationDomainError):
        SecretInputSpec(action="set", plaintext_value="••••••••••••")

    valid_spec = SecretInputSpec(action="set", plaintext_value="my-real-secret-12345678")
    assert valid_spec.plaintext_value == "my-real-secret-12345678"

    # Memory secret provider
    prov = DefaultMemorySecretProvider()
    ref = SecretRef(uri="secret://settings/my-key")
    prov.store_secret(ref, "secret-val")
    assert prov.resolve_secret(ref) == "secret-val"
    assert prov.rotate_workspace_dek("ws-1", actor_id="admin") is None
    prov.delete_secret(ref)
    with pytest.raises(ResourceNotFoundError):
        prov.resolve_secret(ref)
