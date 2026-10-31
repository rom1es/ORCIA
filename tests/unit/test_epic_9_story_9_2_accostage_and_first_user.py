"""Unit & HTTP Contract Tests for Story 9.2 — Progressive Day-0 Accostage (1/6),
Anti-First-User Takeover (`LOCK TABLE users IN EXCLUSIVE MODE` + `ORCIA_BOOTSTRAP_TOKEN`)
& Progressive LLM Tier (`1 Modèle -> >= 2 Familles AD-10`).
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.bootstrap.errors import (
    FirstUserAlreadyInitializedError,
    InvalidBootstrapTokenError,
)
from orcia_core.bootstrap.models import LlmModelEndpoint
from orcia_core.bootstrap.progressive_accostage import (
    ACCOSTAGE_SIX_MILESTONES,
    ProgressiveDay0AccostageService,
)

DUMMY_HASH = "argon2id$test_hash"  # pragma: allowlist secret
DUMMY_PW = "TestPassword!123"  # pragma: allowlist secret


def test_story_9_2_first_user_takeover_guard_bootstrap_token_and_exclusivity() -> None:
    """Verify `ORCIA_BOOTSTRAP_TOKEN` requirement when `ORCIA_ENV != 'local'`."""
    svc_staging = ProgressiveDay0AccostageService(
        orcia_env="staging",
        expected_bootstrap_token="boot-tok-secret-999",
    )

    # Missing or wrong token on non-local env raises HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN
    with pytest.raises(InvalidBootstrapTokenError) as exc_info:
        svc_staging.create_first_platform_admin(
            email="attacker@evil.test",
            display_name="Attacker",
            password_hash=DUMMY_HASH,
            bootstrap_token="wrong-token",
        )
    assert exc_info.value.error_code == "ERR_INVALID_BOOTSTRAP_TOKEN"
    assert exc_info.value.http_status == 403

    # Valid token creates the single first PLATFORM_ADMIN
    created = svc_staging.create_first_platform_admin(
        email="karim@orcia.io",
        display_name="Karim Admin",
        password_hash=DUMMY_HASH,
        bootstrap_token="boot-tok-secret-999",
    )
    assert created.email == "karim@orcia.io"
    assert created.platform_role == "PLATFORM_ADMIN"
    assert created.sql_lock_statement == "LOCK TABLE users IN EXCLUSIVE MODE"

    # Any subsequent attempt when COUNT(*) FROM users > 0 is rejected (409)
    with pytest.raises(FirstUserAlreadyInitializedError) as dup_exc:
        svc_staging.create_first_platform_admin(
            email="second@orcia.io",
            display_name="Second",
            password_hash=DUMMY_HASH,
            bootstrap_token="boot-tok-secret-999",
        )
    assert dup_exc.value.error_code == "ERR_FIRST_USER_ALREADY_INITIALIZED"
    assert dup_exc.value.http_status == 409

    # In local env (`ORCIA_ENV == 'local'`), bootstrap_token is not required if users == 0
    svc_local = ProgressiveDay0AccostageService(orcia_env="local", expected_bootstrap_token=None)
    local_admin = svc_local.create_first_platform_admin(
        email="marc@orcia.local",
        display_name="Marc Local",
        password_hash=DUMMY_HASH,
        bootstrap_token=None,
    )
    assert local_admin.platform_role == "PLATFORM_ADMIN"


@pytest.mark.asyncio
async def test_story_9_2_concurrent_first_admin_creation_serialized_by_exclusive_lock() -> None:
    """Verify concurrent calls to `create_first_platform_admin_async` allow exactly 1 winner."""
    svc = ProgressiveDay0AccostageService(
        orcia_env="production",
        expected_bootstrap_token="prod-boot-token-123",
    )

    results = await asyncio.gather(
        svc.create_first_platform_admin_async(
            email="admin1@orcia.io",
            display_name="Admin 1",
            password_hash=DUMMY_HASH,
            bootstrap_token="prod-boot-token-123",
        ),
        svc.create_first_platform_admin_async(
            email="admin2@orcia.io",
            display_name="Admin 2",
            password_hash=DUMMY_HASH,
            bootstrap_token="prod-boot-token-123",
        ),
        svc.create_first_platform_admin_async(
            email="admin3@orcia.io",
            display_name="Admin 3",
            password_hash=DUMMY_HASH,
            bootstrap_token="prod-boot-token-123",
        ),
        return_exceptions=True,
    )
    successes = [r for r in results if not isinstance(r, BaseException)]
    conflicts = [r for r in results if isinstance(r, FirstUserAlreadyInitializedError)]
    assert len(successes) == 1
    assert len(conflicts) == 2


def test_story_9_2_progressive_llm_tier_and_accostage_1_to_6_progression() -> None:
    """Verify 1 model -> Quick Trial Mode, >= 2 families -> Agentic Gates AD-10."""
    assert len(ACCOSTAGE_SIX_MILESTONES) == 6
    svc = ProgressiveDay0AccostageService(orcia_env="local")

    # Initial state: 0 models, Accostage 1/6
    status0 = svc.get_accostage_status()
    assert status0.completed_count == 1
    assert status0.total_count == 6
    assert status0.badge_label == "Accostage 1/6"
    assert status0.llm_tier_mode == "UNCONFIGURED"
    assert status0.assistant_trial_enabled is False
    assert status0.agentic_gates_ad10_enabled is False

    # Configure 1 single LLM family (e.g. Ollama local) at step 2 -> Quick Trial Mode unlocked!
    ep1 = LlmModelEndpoint(
        id="ep-ollama-1",
        endpoint_key="ollama-qwen",
        provider_slug="ollama",
        model_family="qwen-2.5",
        model_name="qwen2.5-coder:14b",
        endpoint_uri="http://localhost:11434",
    )
    status1 = svc.register_progressive_llm_endpoint(ep1)
    assert status1.llm_tier_mode == "QUICK_TRIAL_SINGLE_FAMILY"
    assert status1.assistant_trial_enabled is True
    assert status1.agentic_gates_ad10_enabled is False
    assert "⚠️ 1 seule famille de modèles configurée" in (status1.amber_warning_badge or "")
    assert "AD-10" in (status1.amber_warning_badge or "")
    assert status1.completed_count == 2
    assert status1.badge_label == "Accostage 2/6"

    # Configure a 2nd distinct LLM family (e.g. Anthropic Claude) -> Agentic Gates AD-10 unlocked!
    ep2 = LlmModelEndpoint(
        id="ep-claude-2",
        endpoint_key="claude-sonnet",
        provider_slug="anthropic",
        model_family="anthropic-claude",
        model_name="claude-3-7-sonnet",
        endpoint_uri="https://api.anthropic.com",
    )
    status2 = svc.register_progressive_llm_endpoint(ep2)
    assert status2.llm_tier_mode == "FULL_ORTHOGONAL_AD10"
    assert status2.assistant_trial_enabled is True
    assert status2.agentic_gates_ad10_enabled is True
    assert status2.amber_warning_badge is None
    assert status2.distinct_families == ("anthropic-claude", "qwen-2.5")


def test_story_9_2_api_endpoints_welcome_setup_and_accostage() -> None:
    """Verify FastAPI endpoints for `/api/v1/bootstrap/welcome-setup/*` and `/accostage-status`."""
    app = create_app()
    client = TestClient(app)

    # 1. GET /api/v1/bootstrap/accostage-status
    resp0 = client.get("/api/v1/bootstrap/accostage-status")
    assert resp0.status_code == 200
    body0 = resp0.json()
    assert body0["badge_label"] == "Accostage 1/6"

    # 2. POST /api/v1/bootstrap/welcome-setup/first-admin with wrong token when env != local -> 403
    resp_denied = client.post(
        "/api/v1/bootstrap/welcome-setup/first-admin",
        json={
            "email": "intruder@orcia.io",
            "display_name": "Intruder",
            "password": DUMMY_PW,
            "orcia_env": "production",
            "bootstrap_token": "invalid-token",
        },
    )
    assert resp_denied.status_code == 403
    assert resp_denied.json()["error_code"] == "ERR_INVALID_BOOTSTRAP_TOKEN"

    # 3. POST /api/v1/bootstrap/welcome-setup/progressive-llm with 1 model -> Quick Trial Mode
    resp_llm1 = client.post(
        "/api/v1/bootstrap/welcome-setup/progressive-llm",
        json={
            "endpoint_key": "local-ollama",
            "provider_slug": "ollama",
            "model_family": "llama-3.3",
            "model_name": "llama3.3:70b",
            "endpoint_uri": "http://localhost:11434",
        },
    )
    assert resp_llm1.status_code == 200
    data1 = resp_llm1.json()
    assert data1["llm_tier_mode"] == "QUICK_TRIAL_SINGLE_FAMILY"
    assert data1["assistant_trial_enabled"] is True
    assert data1["agentic_gates_ad10_enabled"] is False
    assert "⚠️ 1 seule famille de modèles configurée" in data1["amber_warning_badge"]

    # 4. Add 2nd family -> FULL_ORTHOGONAL_AD10
    resp_llm2 = client.post(
        "/api/v1/bootstrap/welcome-setup/progressive-llm",
        json={
            "endpoint_key": "mistral-eu",
            "provider_slug": "mistral",
            "model_family": "mistral-large",
            "model_name": "mistral-large-latest",
            "endpoint_uri": "https://api.mistral.ai",
        },
    )
    assert resp_llm2.status_code == 200
    data2 = resp_llm2.json()
    assert data2["llm_tier_mode"] == "FULL_ORTHOGONAL_AD10"
    assert data2["agentic_gates_ad10_enabled"] is True
    assert data2["amber_warning_badge"] is None
