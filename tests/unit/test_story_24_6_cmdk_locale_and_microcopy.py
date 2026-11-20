"""Story 24.6 Layer 1a Unit Tests: Cmd+K Locale Filtering & Microcopy Purge."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration.assistant_three_speed_router import (
    AssistantThreeSpeedRouterService,
)
from orcia_core.orchestration.errors import (
    ResourceNotFoundError,
    StepAlreadyClaimedByPeerError,
    ValidationDomainError,
)
from orcia_core.orchestration.notifications_and_claims import (
    UnifiedNotificationAndClaimService,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.rag._internal.sql_federated_search import (
    load_federated_search_candidates_pg18,
    normalize_search_locale,
)
from orcia_core.rag.two_speed_search import (
    FederatedSearchCandidate,
    TwoSpeedFederatedSearchService,
    build_speed2_redis_cache_key,
)
from orcia_kernel.events import DomainEvent


class _FakeResult:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


class _CapturingAsyncConnection:
    """Stub AsyncConnection capturing SQL statements and bind parameters."""

    def __init__(self, table_rows: dict[str, list[tuple[Any, ...]]]) -> None:
        self._table_rows = table_rows
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = str(stmt)
        self.executed.append((sql, params))
        if "FROM pg_tables" in sql:
            return _FakeResult([(name,) for name in self._table_rows])
        if "FROM catalog_items" in sql:
            return _FakeResult(self._table_rows.get("catalog_items", []))
        return _FakeResult([])


def test_normalize_search_locale_handles_bcp47_and_fallbacks() -> None:
    assert normalize_search_locale(None) == "fr"
    assert normalize_search_locale("") == "fr"
    assert normalize_search_locale("fr") == "fr"
    assert normalize_search_locale("fr-FR") == "fr"
    assert normalize_search_locale("fr_CA") == "fr"
    assert normalize_search_locale("en") == "en"
    assert normalize_search_locale("en-US") == "en"
    assert normalize_search_locale("EN_GB") == "en"
    assert normalize_search_locale("de-DE") == "fr"


async def test_load_federated_search_candidates_pg18_filters_help_article_by_locale_only() -> None:
    conn_fr = _CapturingAsyncConnection(
        {
            "workspace_memberships": [],
            "catalog_items": [
                (
                    "help-fr-cockpit",
                    "orcia://help/cockpit/fr",
                    "Guide Cockpit FR",
                    "Piloter vos validations",
                    "template",
                    "HELP_ARTICLE",
                    "GLOBAL",
                    "PUBLISHED_ORG",
                ),
            ],
        }
    )
    cands_fr = await load_federated_search_candidates_pg18(
        conn_fr,  # type: ignore[arg-type]
        user_id="user-1",
        user_role="CONTRIBUTOR",
        locale="fr-FR",
    )
    assert len(cands_fr) == 1
    assert cands_fr[0].family == "HELP_ACTIONS"
    assert cands_fr[0].title == "Guide Cockpit FR"

    catalog_calls_fr = [item for item in conn_fr.executed if "FROM catalog_items" in item[0]]
    assert len(catalog_calls_fr) == 1
    sql_fr, params_fr = catalog_calls_fr[0]
    assert params_fr is not None
    assert params_fr["locale"] == "fr"
    assert "COALESCE(ci.item_type, 'CATALOG_RESOURCE') = 'HELP_ARTICLE'" in sql_fr
    assert "COALESCE(ci.item_type, 'CATALOG_RESOURCE') != 'HELP_ARTICLE'" in sql_fr
    assert "ci.metadata_jsonb->>'lang'" in sql_fr
    assert ") = :locale" in sql_fr

    conn_en = _CapturingAsyncConnection(
        {
            "workspace_memberships": [],
            "catalog_items": [
                (
                    "help-en-cockpit",
                    "orcia://help/cockpit/en",
                    "Cockpit Guide EN",
                    "Manage human approvals",
                    "template",
                    "HELP_ARTICLE",
                    "GLOBAL",
                    "PUBLISHED_ORG",
                ),
            ],
        }
    )
    cands_en = await load_federated_search_candidates_pg18(
        conn_en,  # type: ignore[arg-type]
        user_id="user-1",
        user_role="CONTRIBUTOR",
        locale="en-US",
    )
    assert len(cands_en) == 1
    assert cands_en[0].title == "Cockpit Guide EN"

    catalog_calls_en = [item for item in conn_en.executed if "FROM catalog_items" in item[0]]
    assert len(catalog_calls_en) == 1
    _, params_en = catalog_calls_en[0]
    assert params_en is not None
    assert params_en["locale"] == "en"


def test_build_speed2_redis_cache_key_normalizes_and_isolates_locales() -> None:
    key_fr = build_speed2_redis_cache_key("ws-alpha", "aide cockpit", locale="fr")
    key_fr_bcp = build_speed2_redis_cache_key("ws-alpha", "aide cockpit", locale="fr-FR")
    key_en = build_speed2_redis_cache_key("ws-alpha", "aide cockpit", locale="en")
    key_en_bcp = build_speed2_redis_cache_key("ws-alpha", "aide cockpit", locale="en_US")

    assert key_fr == key_fr_bcp
    assert key_en == key_en_bcp
    assert key_fr != key_en
    assert ":fr:" in key_fr
    assert ":en:" in key_en

    svc = TwoSpeedFederatedSearchService(
        candidates=(
            FederatedSearchCandidate(
                item_id="help:1",
                family="HELP_ACTIONS",
                title="Aide Cockpit",
                snippet="Guide pratique",
                workspace_id="GLOBAL",
                screen_route="/help",
                deep_link_uri="/help",
                embedding=(1.0, 0.0),
            ),
        )
    )
    res_fr = svc.execute_search(
        query="Aide",
        scope="ALL_WORKSPACES",
        active_workspace_id="ws-alpha",
        locale="fr",
        include_speed2=True,
        force_semantic=True,
        query_embedding=(1.0, 0.0),
    )
    res_en = svc.execute_search(
        query="Aide",
        scope="ALL_WORKSPACES",
        active_workspace_id="ws-alpha",
        locale="en",
        include_speed2=True,
        force_semantic=True,
        query_embedding=(1.0, 0.0),
    )
    assert res_fr.speed2_redis_key is not None
    assert res_en.speed2_redis_key is not None
    assert res_fr.speed2_redis_key != res_en.speed2_redis_key


def test_assistant_three_speed_router_capitalizes_synthese_conforme_pour() -> None:
    svc = AssistantThreeSpeedRouterService()
    user = UserIdentity(
        id="user-24-6",
        email="claire@orcia.local",
        display_name="Claire",
        auth_mode="LOCAL",
        human_profile_archetype="PM",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="org-1",
    )
    turn = svc.execute_three_speed_turn(
        user,
        workspace_id="ws-24-6",
        user_prompt="état des validations en attente",
        hat="PM",
    )
    assert "Synthèse conforme pour « état des validations en attente »" in turn.response_text
    assert ": synthèse conforme pour" not in turn.response_text


def test_notifications_and_claims_humanizes_inbox_review_step_title() -> None:
    assert (
        UnifiedNotificationAndClaimService._format_step_claim_title("inbox-review-step")
        == "Prise en charge directe — Relecture en boîte de réception"
    )
    assert (
        UnifiedNotificationAndClaimService._format_step_claim_title("custom_audit-step")
        == "Prise en charge directe — Custom Audit Step"
    )


async def test_notifications_and_claims_error_guards_and_outbox_noop() -> None:
    import pytest

    svc = UnifiedNotificationAndClaimService()
    user_a = UserIdentity(
        id="user-a",
        email="a@orcia.local",
        display_name="Alice",
        auth_mode="LOCAL",
        human_profile_archetype="PM",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="org-1",
    )
    user_b = UserIdentity(
        id="user-b",
        email="b@orcia.local",
        display_name="Bob",
        auth_mode="LOCAL",
        human_profile_archetype="PM",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="org-1",
    )

    unknown_evt = DomainEvent(
        event_id="evt-unknown-24-6",
        event_type="UnknownUnmappedEvent",
        aggregate_id="step-unknown-1",
        aggregate_type="StepExecution",
        workspace_id="ws-1",
        run_id="run-1",
        payload={},
    )
    assert svc.consume_outbox_event(unknown_evt) is None
    assert await svc.consume_outbox_event_async(unknown_evt) is None

    with pytest.raises(ResourceNotFoundError):
        svc.claim_by_task_id(user_a, task_id="missing-task-id")
    with pytest.raises(ResourceNotFoundError):
        svc.release_claim(user_a, task_id="missing-task-id")

    outcome = await svc.claim_by_step_execution_async(
        user_a,
        run_id="run-1",
        step_execution_id="step-exec-24-6",
        workspace_id="ws-1",
        step_key="inbox-review-step",
    )
    assert outcome.notification.title == "Prise en charge directe — Relecture en boîte de réception"

    with pytest.raises(ValidationDomainError):
        svc.claim_by_task_id(user_a, task_id=outcome.notification.id, ttl_seconds=0)

    with pytest.raises(StepAlreadyClaimedByPeerError):
        svc.verify_step_mutation_allowed(user_b, step_execution_id="step-exec-24-6")
