"""Story 24.5 Layer 1a unit tests: Accostage identity/role filtering & /inbox Zone 4 help."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from orcia_api.routers.bootstrap_accostage import _resolve_optional_caller_role
from orcia_core.bootstrap import (
    ACCOSTAGE_SIX_MILESTONES,
    AccostageVisibleMilestone,
    FirstPlatformAdminRecord,
    LlmModelEndpoint,
    ProgressiveDay0AccostageService,
    is_accostage_milestone_accessible,
)
from orcia_core.bootstrap._internal.sql_first_user_guard import (
    create_first_platform_admin_on_postgres18,
    get_first_platform_admin_from_postgres18,
)
from orcia_core.bootstrap.errors import (
    FirstUserAlreadyInitializedError,
    InvalidBootstrapTokenError,
)
from orcia_core.catalog.contextual_help import (
    BASE_CONTEXTUAL_HELP_ROUTES,
    ContextualHelpResolutionService,
)
from orcia_core.catalog.contextual_help_models import HelpArticleCatalogItem

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_accostage_six_milestones_never_target_welcome_setup() -> None:
    keys = [m.key for m in ACCOSTAGE_SIX_MILESTONES]
    assert keys == [
        "first-admin",
        "first-llm-model",
        "first-org-unit",
        "first-space",
        "first-datasource",
        "pilot-workflow-run",
    ]
    for spec in ACCOSTAGE_SIX_MILESTONES:
        assert spec.target_route != "/welcome-setup"
        assert "/welcome-setup" not in spec.target_route

    first_admin_spec = ACCOSTAGE_SIX_MILESTONES[0]
    assert first_admin_spec.key == "first-admin"
    assert first_admin_spec.target_route == "/profile"


def test_accostage_status_pre_admin_day0_vs_post_admin_targets_and_identity() -> None:
    svc = ProgressiveDay0AccostageService(orcia_env="local")

    day0_status = svc.get_accostage_status()
    assert day0_status.first_admin_initialized is False
    assert day0_status.platform_admin_display_name is None
    assert day0_status.first_admin_display_name is None
    day0_map = {m.key: m for m in day0_status.visible_milestones}
    assert len(day0_map) == 6
    assert day0_map["first-admin"].target_route == "/cockpit"
    assert day0_map["first-admin"].completed is False

    rec = svc.create_first_platform_admin(
        email="alice.admin@orcia.ia",
        display_name="Alice Administratrice",
        password_hash="argon2id-hash",  # pragma: allowlist secret
    )
    assert isinstance(rec, FirstPlatformAdminRecord)

    post_admin_status = svc.get_accostage_status(user_role="PLATFORM_ADMIN")
    assert post_admin_status.first_admin_initialized is True
    assert post_admin_status.platform_admin_display_name == "Alice Administratrice"
    assert post_admin_status.first_admin_display_name == "Alice Administratrice"
    assert [m.key for m in post_admin_status.visible_milestones] == [
        "first-admin",
        "first-llm-model",
        "first-org-unit",
        "first-space",
        "first-datasource",
        "pilot-workflow-run",
    ]
    assert post_admin_status.visible_milestones[0] == AccostageVisibleMilestone(
        index=1,
        key="first-admin",
        title_fr="1. Compte Admin",
        title_en="1. Admin Account",
        target_route="/profile",
        completed=True,
        is_accessible=True,
    )


@pytest.mark.parametrize(
    ("role", "read_only_observer", "expected_keys"),
    [
        (
            "PLATFORM_ADMIN",
            False,
            [
                "first-admin",
                "first-llm-model",
                "first-org-unit",
                "first-space",
                "first-datasource",
                "pilot-workflow-run",
            ],
        ),
        (
            "BU_LEAD",
            False,
            ["first-org-unit", "first-space", "pilot-workflow-run"],
        ),
        (
            "BU_DIRECTOR",
            False,
            ["first-org-unit", "first-space", "pilot-workflow-run"],
        ),
        (
            "TEAM_LEAD",
            False,
            ["first-org-unit", "first-space", "pilot-workflow-run"],
        ),
        (
            "CONTRIBUTOR",
            False,
            ["first-space", "pilot-workflow-run"],
        ),
        (
            "SECOPS",
            False,
            ["first-space", "pilot-workflow-run"],
        ),
        (
            "READ_ONLY_OBSERVER",
            False,
            [],
        ),
        (
            "CONTRIBUTOR",
            True,
            [],
        ),
    ],
)
def test_accostage_status_filters_visible_milestones_and_preserves_real_platform_admin_identity(
    role: str,
    read_only_observer: bool,
    expected_keys: list[str],
) -> None:
    svc = ProgressiveDay0AccostageService(orcia_env="local")
    svc.create_first_platform_admin(
        email="alice.admin@orcia.ia",
        display_name="Alice Administratrice",
        password_hash="argon2id-hash",  # pragma: allowlist secret
    )
    svc.register_progressive_llm_endpoint(
        LlmModelEndpoint(
            id="ep-1",
            endpoint_key="tier-1",
            provider_slug="openai",
            model_family="openai",
            model_name="gpt-4o",
            endpoint_uri="https://api.openai.local/v1",
        )
    )
    svc.mark_milestone_completed("first-space")

    status = svc.get_accostage_status(
        user_role=role,
        read_only_observer=read_only_observer,
    )
    # Real platform admin identity is ALWAYS Alice Administratrice, never the caller's role/name
    assert status.platform_admin_display_name == "Alice Administratrice"
    assert status.first_admin_email == "alice.admin@orcia.ia"
    assert [m.key for m in status.visible_milestones] == expected_keys
    assert all(m.target_route != "/welcome-setup" for m in status.visible_milestones)

    # Direct helper checks
    for spec in ACCOSTAGE_SIX_MILESTONES:
        assert is_accostage_milestone_accessible(
            spec.key,
            user_role=role,
            read_only_observer=read_only_observer,
            first_admin_initialized=True,
        ) is (spec.key in expected_keys)


@pytest.mark.asyncio
async def test_sql_first_user_guard_queries_strictly_platform_admin_role() -> None:
    executed_sql: list[str] = []

    class FakeResult:
        def __init__(self, row: tuple[object, ...] | None) -> None:
            self._row = row

        def first(self) -> tuple[object, ...] | None:
            return self._row

    class FakeConn:
        async def execute(self, stmt: object) -> FakeResult:
            executed_sql.append(str(stmt))
            return FakeResult(
                ("0195f000-0000-7000-8000-000000000001", "admin@orcia.ia", "Real Admin")
            )

    class FakeConnectCtx:
        async def __aenter__(self) -> FakeConn:
            return FakeConn()

        async def __aexit__(self, *args: object) -> None:
            return None

    fake_engine = MagicMock()
    fake_engine.connect.return_value = FakeConnectCtx()

    rec = await get_first_platform_admin_from_postgres18(fake_engine, orcia_env="local")
    assert rec is not None
    assert rec.display_name == "Real Admin"
    assert rec.platform_role == "PLATFORM_ADMIN"
    assert len(executed_sql) == 1
    assert "platform_role = 'PLATFORM_ADMIN'" in executed_sql[0]

    # Empty result returns None
    class EmptyConn:
        execute = AsyncMock(return_value=FakeResult(None))

    class EmptyCtx:
        async def __aenter__(self) -> EmptyConn:
            return EmptyConn()

        async def __aexit__(self, *args: object) -> None:
            return None

    fake_engine.connect.return_value = EmptyCtx()
    assert await get_first_platform_admin_from_postgres18(fake_engine, orcia_env="local") is None

    # Invalid bootstrap token in staging raises InvalidBootstrapTokenError
    with pytest.raises(InvalidBootstrapTokenError):
        await create_first_platform_admin_on_postgres18(
            fake_engine,
            email="admin@orcia.ia",
            display_name="Admin",
            password_hash="hash",  # pragma: allowlist secret
            orcia_env="staging",
            expected_bootstrap_token="expected-secret",  # pragma: allowlist secret
            provided_bootstrap_token="wrong-secret",  # pragma: allowlist secret
            instance="/api/v1/bootstrap/welcome-setup/first-admin",
        )

    # Existing users > 0 raises FirstUserAlreadyInitializedError
    class ExistingCountConn:
        execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=1)))

    class BeginCtx:
        async def __aenter__(self) -> ExistingCountConn:
            return ExistingCountConn()

        async def __aexit__(self, *args: object) -> None:
            return None

    fake_engine.begin.return_value = BeginCtx()
    with pytest.raises(FirstUserAlreadyInitializedError):
        await create_first_platform_admin_on_postgres18(
            fake_engine,
            email="admin@orcia.ia",
            display_name="Admin",
            password_hash="hash",  # pragma: allowlist secret
            orcia_env="local",
            instance="/api/v1/bootstrap/welcome-setup/first-admin",
        )


def test_resolve_optional_caller_role_handles_unauthenticated_and_invalid_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req_no_auth = MagicMock()
    req_no_auth.headers = {}
    req_no_auth.state = MagicMock(resolved_bearer_user=None)
    assert _resolve_optional_caller_role(req_no_auth) == (None, False)

    def _raise_bad_token(_request: object) -> object:
        raise ValueError("invalid bearer token")

    monkeypatch.setattr(
        "orcia_api.routers.bootstrap_accostage.resolve_request_user",
        _raise_bad_token,
    )
    req_bad_auth = MagicMock()
    req_bad_auth.headers = {"Authorization": "Bearer invalid-token"}
    req_bad_auth.state = MagicMock(resolved_bearer_user=None)
    assert _resolve_optional_caller_role(req_bad_auth) == (None, False)


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_contextual_help_resolves_inbox_to_dedicated_article_even_with_legacy_assistant_binding(
    lang: str,
) -> None:
    assert "/inbox" in BASE_CONTEXTUAL_HELP_ROUTES

    svc = ContextualHelpResolutionService(repo_root=REPO_ROOT)
    res = svc.resolve_for_route(route="/inbox", pack="core", lang=lang)  # type: ignore[arg-type]
    assert res.active_article.resource_id == f"help-base-inbox-{lang}"
    assert "/inbox" in res.active_article.bound_routes
    assert "assistant" not in res.active_article.resource_id

    # Verify /assistant does NOT bind /inbox anymore
    assistant_art = svc._articles_by_id[f"help-base-assistant-{lang}"]
    assert "/inbox" not in assistant_art.bound_routes

    # Inject a legacy help-base-assistant-* record that still binds /inbox:
    # /inbox resolution must STILL exclude it.
    legacy_assistant = HelpArticleCatalogItem(
        resource_id=assistant_art.resource_id,
        uri=assistant_art.uri,
        title=assistant_art.title,
        version=assistant_art.version,
        lang=assistant_art.lang,
        layer=assistant_art.layer,
        pack_name=assistant_art.pack_name,
        bound_routes=("/assistant", "/inbox"),
        summary_what_for=assistant_art.summary_what_for,
        step_by_step_items=assistant_art.step_by_step_items,
        key_terms_items=assistant_art.key_terms_items,
        faq_items=assistant_art.faq_items,
        cas_key=assistant_art.cas_key,
        sha256=assistant_art.sha256,
        markdown_body=assistant_art.markdown_body,
    )
    svc._articles_by_id[legacy_assistant.resource_id] = legacy_assistant
    svc._redis_cache.clear()

    res_with_legacy = svc.resolve_for_route(
        route="/inbox",
        pack="core",
        lang=lang,  # type: ignore[arg-type]
    )
    assert res_with_legacy.active_article.resource_id == f"help-base-inbox-{lang}"
