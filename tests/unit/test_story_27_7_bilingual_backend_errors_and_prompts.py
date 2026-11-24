"""Story 27.7 — Bilingual RFC 9457 Backend Error Catalogs, Prompts & Locale Bundles Tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

import orcia_api.errors.registry as error_registry
import orcia_core.permissions.ssrf_policy  # noqa: F401
from orcia_api.errors.registry import (
    HelpArticleValidationError,
    InvalidMcpTokenConfigurationError,
    PackBuilderValidationError,
)
from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.main import create_app
from orcia_api.routers._assistant_prompt_sanitization import (
    detect_adaptive_thinking_steps_for_question,
    resolve_request_locale,
)
from orcia_api.schemas._shell_locales import get_shell_scope_copy
from orcia_core.agents._agents_locales import get_agent_runtime_copy
from orcia_core.orchestration.assistant_prompt_locales import get_prompt_locale_bundle
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.permissions.errors import PrivilegeEscalationForbiddenError
from orcia_kernel.errors import ERROR_CATALOG, get_localized_error_text, resolve_locale


def test_story_27_7_missing_error_codes_registered_bilingually() -> None:
    """All 3 previously unregistered error codes must expose distinct FR and EN RFC 9457 copy."""
    expected_codes = (
        "ERR_HELP_ARTICLE_VALIDATION_FAILED",
        "ERR_INVALID_MCP_TOKEN_CONFIG",
        "ERR_PACK_BUILDER_VALIDATION_FAILED",
    )
    for code in expected_codes:
        assert code in ERROR_CATALOG, f"{code} missing from ERROR_CATALOG"
        fr_copy = get_localized_error_text(code, "fr")
        en_copy = get_localized_error_text(code, "en")
        assert fr_copy.title and fr_copy.detail
        assert en_copy.title and en_copy.detail
        assert fr_copy.title != en_copy.title
        assert fr_copy.detail != en_copy.detail


def test_story_27_7_accept_language_localized_domain_errors() -> None:
    """Domain errors must resolve bilingual title/detail via `resolve_locale` and `.localized`."""
    _ = error_registry.API_EXTRA_ERROR_CATALOG

    help_err = HelpArticleValidationError()
    fr_help = help_err.localize(resolve_locale("fr"))
    en_help = help_err.localize(resolve_locale("en"))
    assert fr_help.detail != en_help.detail
    assert "Help article" in en_help.title

    mcp_err = InvalidMcpTokenConfigurationError()
    fr_mcp = mcp_err.localize(resolve_locale("fr-FR"))
    en_mcp = mcp_err.localize(resolve_locale("en-US"))
    assert fr_mcp.title != en_mcp.title
    assert "personal access token" in en_mcp.title

    pack_err = PackBuilderValidationError()
    fr_pack = pack_err.localize("fr")
    en_pack = pack_err.localize("en")
    assert fr_pack.detail != en_pack.detail

    param_err = ResourceNotFoundError(
        detail_code="ERR_ORG_UNIT_NOT_FOUND_DETAIL",
        detail_params={"org_unit_id": "unit-42"},
    )
    fr_org = param_err.localize(resolve_locale("fr-FR"))
    en_org = param_err.localize(resolve_locale("en-US,fr;q=0.8"))
    assert "unit-42" in fr_org.detail
    assert "unit-42" in en_org.detail
    assert "introuvable" in fr_org.detail
    assert "not found" in en_org.detail

    esc_err = PrivilegeEscalationForbiddenError(detail_code="ERR_IAM_PLATFORM_ADMIN_ONLY_ROLE")
    fr_esc = esc_err.localize("fr")
    en_esc = esc_err.localize("en")
    assert "Administrateur Plateforme" in fr_esc.detail
    assert "Platform Administrator" in en_esc.detail


def test_story_27_7_http_rfc9457_accept_language_header() -> None:
    """HTTP API must return localized RFC 9457 `application/problem+json` per `Accept-Language`."""
    app = create_app()
    client = TestClient(app)
    res_fr = client.post(
        "/api/v1/users/me/mcp-tokens?persona_key=marc",
        json={"expires_in_days": 999},
        headers={"Accept-Language": "fr"},
    )
    res_en = client.post(
        "/api/v1/users/me/mcp-tokens?persona_key=marc",
        json={"expires_in_days": 999},
        headers={"Accept-Language": "en"},
    )
    assert res_fr.status_code == 422
    assert res_en.status_code == 422
    body_fr = res_fr.json()
    body_en = res_en.json()
    assert body_fr["error_code"] == "ERR_INVALID_MCP_TOKEN_CONFIG"
    assert body_en["error_code"] == "ERR_INVALID_MCP_TOKEN_CONFIG"
    assert body_fr["title"] != body_en["title"]
    assert body_fr["detail"] != body_en["detail"]


def test_story_27_7_locale_bundles_bilingual_switching() -> None:
    """Router, shell scope, adaptive thinking steps, and prompt bundles must switch cleanly."""
    assert get_router_copy("fr").pack_sdlc_title != get_router_copy("en").pack_sdlc_title
    assert get_shell_scope_copy("fr")["scope_global"] != get_shell_scope_copy("en")["scope_global"]
    assert get_router_copy("fr").thinking_deep != get_router_copy("en").thinking_deep
    assert (
        get_agent_runtime_copy("fr").fallback_synthesis_heading
        != get_agent_runtime_copy("en").fallback_synthesis_heading
    )

    fr_steps = detect_adaptive_thinking_steps_for_question("Explique le bug python", locale="fr")
    en_steps = detect_adaptive_thinking_steps_for_question("Explain the python bug", locale="en")
    assert len(fr_steps) == 3 and len(en_steps) == 3
    assert fr_steps[0][0] != en_steps[0][0]

    assert resolve_request_locale(None, "en-US") == "en"
    assert resolve_request_locale(None, "fr-FR") == "fr"

    fr_prompt = get_prompt_locale_bundle("fr")
    en_prompt = get_prompt_locale_bundle("en")
    assert fr_prompt.language_rule != en_prompt.language_rule
