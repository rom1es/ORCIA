"""Story 26.5 — Real PG18 + Redis Vertical Integration Tests (`create_app()`, 0 overrides)."""

from __future__ import annotations

import json
import time
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.api._pg18_story_26_5_helpers import (
    pg_and_redis_urls,
    real_lifespan_client_factory,
    seed_pg18_ontology_rag_and_blackboard,
)

__all__ = ["pg_and_redis_urls", "real_lifespan_client_factory"]


@pytest.mark.asyncio
async def test_story_26_5_real_context_history_acl_and_r6_latency_postgres18(
    real_lifespan_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Verify PG18 ontology, RAG (with & without embedding), Blackboard, history & R6 timing."""
    open_client, pg_url = real_lifespan_client_factory
    engine = create_async_engine(pg_url)
    try:
        async with open_client() as c1:
            boot = await c1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin265@orcia.io",
                    "display_name": "Admin 26.5",
                    "password": "Admin265!StrongPassword",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert boot.status_code == 200, boot.text
            admin_id = boot.json()["user_id"]
            hdrs = {"Authorization": f"Bearer {boot.json()['access_token']}"}

            bu = await c1.post(
                "/api/v1/org-units",
                headers=hdrs,
                json={"name": "BU 26.5", "slug": "bu-265", "kind": "BU"},
            )
            assert bu.status_code == 200, bu.text
            bu_id = bu.json()["id"]

            ws_a = (
                await c1.post(
                    "/api/v1/workspaces",
                    headers=hdrs,
                    json={
                        "name": "WS A 26.5",
                        "slug": "ws-a-265",
                        "owner_org_unit_id": bu_id,
                        "visibility_mode": "STANDARD",
                    },
                )
            ).json()["id"]
            ws_b = (
                await c1.post(
                    "/api/v1/workspaces",
                    headers=hdrs,
                    json={
                        "name": "WS B 26.5",
                        "slug": "ws-b-265",
                        "owner_org_unit_id": bu_id,
                        "visibility_mode": "STANDARD",
                    },
                )
            ).json()["id"]

            # 1 active chat model (0 embeddings initially -> Story 25.5 invariant)
            r_chat_m = await c1.post(
                "/api/v1/settings/ai-models/mappings",
                headers=hdrs,
                json={
                    "scope_level": "GLOBAL",
                    "display_name": "Chat 26.5",
                    "inference_tier": "medium",
                    "effort": "balanced",
                    "provider_slug": "openai",
                    "model_family": "OpenAI",
                    "model_name": "gpt-4o-mini",
                    "endpoint_uri": "https://api.openai.com/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "chat",
                    "max_tokens_budget": 1400,
                },
            )
            assert r_chat_m.status_code in (200, 201), r_chat_m.text

            # Permission Broker policies authorizing jira://PAY* & confluence://PAY*, NOT SECRET
            for p_key, pat in (
                ("pol-jira-pay", "jira://PAY*"),
                ("pol-spec-pay", "confluence://SPEC-PAY*"),
            ):
                r_pol = await c1.post(
                    "/api/v1/permissions/broker/policies/import-markdown",
                    headers=hdrs,
                    json={
                        "policy_key": p_key,
                        "markdown_text": (
                            f"---\nuri_pattern: {pat}\nrequired_role: PLATFORM_ADMIN\n"
                            "approver_team: Security\n"
                            "request_url_template: https://access.orcia.local/req\n"
                            "sla_hours: 24\n---\nAllow read access.\n"
                        ),
                    },
                )
                assert r_pol.status_code == 200, r_pol.text

            await seed_pg18_ontology_rag_and_blackboard(
                engine, ws_a=ws_a, ws_b=ws_b, admin_user_id=admin_id
            )

            folder_id = (
                await c1.post(
                    "/api/v1/assistant/folders",
                    headers=hdrs,
                    json={"workspace_id": ws_a, "title": "Payment Ledger Folder"},
                )
            ).json()["folder_id"]
            thread_id = (
                await c1.post(
                    "/api/v1/assistant/threads",
                    headers=hdrs,
                    json={
                        "workspace_id": ws_a,
                        "folder_id": folder_id,
                        "title": "Ledger Thread",
                    },
                )
            ).json()["thread_id"]

            # Phase A (0 embeddings -> 25.5 invariant): lexical PG18 RAG + Ontology + Blackboard
            t_start = time.perf_counter()
            r_t1 = await c1.post(
                "/api/v1/assistant/three-speed/turn",
                headers=hdrs,
                json={
                    "workspace_id": ws_a,
                    "thread_id": thread_id,
                    "hat": "ARCHITECT",
                    "user_prompt": "What is the Payment Ledger settlement rule?",
                    "locale": "en",
                },
            )
            r6_turn_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
            assert r_t1.status_code == 200, r_t1.text
            assert r6_turn_ms < 2500.0
            sys_prompt_1 = r_t1.json()["assembled_system_prompt"]
            assert "Event-Sourced Payment Ledger (PG18)" in sys_prompt_1
            assert "ax-ledger-append-only" in sys_prompt_1
            assert "Onboarding Badge" not in sys_prompt_1
            assert "jira://PAY-42" in sys_prompt_1
            assert "[STALE_WARNING]" in sys_prompt_1
            assert "orcia://blackboard/" in sys_prompt_1
            assert "RESTRICTED_PAYROLL_LEAK" not in sys_prompt_1
            assert "WORKSPACE_B_LEAK" not in sys_prompt_1
            assert "MUST_NOT_LEAK" not in sys_prompt_1

            # Phase B: active embedding -> hybrid vector + lexical RRF + v2 SSE + budget trim
            r_emb_m = await c1.post(
                "/api/v1/settings/ai-models/mappings",
                headers=hdrs,
                json={
                    "scope_level": "GLOBAL",
                    "display_name": "Emb 26.5",
                    "inference_tier": "medium",
                    "effort": "balanced",
                    "provider_slug": "openai",
                    "model_family": "OpenAI",
                    "model_name": "text-embedding-3-small",
                    "endpoint_uri": "https://api.openai.com/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "embedding",
                },
            )
            assert r_emb_m.status_code in (200, 201), r_emb_m.text
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "UPDATE rag_reindexing_jobs "
                        "SET status = 'COMPLETED', progress_percentage = 100, completed_at = NOW()"
                    )
                )

            r_v2 = await c1.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={
                    "workspace_id": ws_a,
                    "thread_id": thread_id,
                    "hat": "ARCHITECT",
                    "user_prompt": "Confirm settlement threshold and ledger rule.",
                    "locale": "en",
                },
            )
            assert r_v2.status_code == 202, r_v2.text
            v2_turn_id = r_v2.json()["turn_id"]
            async with c1.stream(
                "GET", f"/api/v1/assistant/turns/{v2_turn_id}/stream", headers=hdrs
            ) as sse_resp:
                assert sse_resp.status_code == 200
                body_lines = [ln async for ln in sse_resp.aiter_lines() if ln.startswith("data:")]
            assert any(
                json.loads(ln[5:].strip()).get("accumulated_text")
                or json.loads(ln[5:].strip()).get("delta")
                for ln in body_lines
            )

            # Verify persisted PG18 assistant_thread_messages via HTTP & SQL SELECT
            r_msgs = await c1.get(
                f"/api/v1/assistant/threads/{thread_id}/messages",
                headers=hdrs,
                params={"workspace_id": ws_a},
            )
            assert r_msgs.status_code == 200, r_msgs.text
            items = r_msgs.json()["messages"]
            assert len(items) == 4
            assert [m["role"] for m in items] == ["user", "assistant", "user", "assistant"]
            assert items[1]["citation_map"].get("sources")

            # Phase C (R6): Measure warm PG18 prompt assembly latency across 5 consecutive turns
            from structlog.testing import capture_logs

            warm_samples: list[dict[str, Any]] = []
            with capture_logs() as cap_logs:
                for idx in range(5):
                    r_warm = await c1.post(
                        "/api/v1/assistant/three-speed/turn",
                        headers=hdrs,
                        json={
                            "workspace_id": ws_a,
                            "thread_id": thread_id,
                            "hat": "ARCHITECT",
                            "user_prompt": f"Confirm settlement threshold rule pass {idx}.",
                            "locale": "en",
                        },
                    )
                    assert r_warm.status_code == 200, r_warm.text
            for rec in cap_logs:
                if rec.get("event") == "assistant_prompt_assembly_benchmarked":
                    warm_samples.append(dict(rec))
            assert len(warm_samples) == 5, warm_samples
            warm_latencies = sorted(float(s["assembly_latency_ms"]) for s in warm_samples)
            warm_p50 = warm_latencies[2]
            warm_p95 = warm_latencies[-1]
            print(
                f"STORY_26_5_WARM_PG18_LATENCY_MS p50={warm_p50:.3f} p95={warm_p95:.3f} "
                f"samples={warm_latencies} last_breakdown={warm_samples[-1]}"
            )
            assert warm_p95 <= 100.0, f"Warm p95 {warm_p95}ms > 100ms: {warm_samples}"

            # Verify non-owner workspace contributor gets 403 on PRIVATE thread messages
            r_contrib = await c1.post(
                "/api/v1/settings/iam/accounts",
                headers=hdrs,
                json={
                    "account_kind": "HUMAN",
                    "display_name": "Contrib 26.5",
                    "email": "contrib265@orcia.io",
                    "principal_id": "contrib265@orcia.io",
                    "roles": ["CONTRIBUTOR"],
                    "team_ids": [bu_id],
                    "status": "ACTIVE",
                },
            )
            assert r_contrib.status_code in (200, 201), r_contrib.text
            c_login = await c1.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "contrib265@orcia.io",
                    "password": r_contrib.json()["temporary_password"],
                },
            )
            c_hdrs = {"Authorization": f"Bearer {c_login.json()['access_token']}"}
            r_acl_deny = await c1.get(
                f"/api/v1/assistant/threads/{thread_id}/messages",
                headers=c_hdrs,
                params={"workspace_id": ws_a},
            )
            assert r_acl_deny.status_code == 403

        # Cold restart app2 -> PG18 history remains intact
        async with open_client() as c2:
            login2 = await c2.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "admin265@orcia.io",
                    "password": "Admin265!StrongPassword",  # pragma: allowlist secret
                },
            )
            hdrs2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}
            r_cold_msgs = await c2.get(
                f"/api/v1/assistant/threads/{thread_id}/messages",
                headers=hdrs2,
                params={"workspace_id": ws_a},
            )
            assert r_cold_msgs.status_code == 200
            assert len(r_cold_msgs.json()["messages"]) == 14

        async with engine.connect() as conn:
            db_count = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM assistant_thread_messages "
                        "WHERE thread_id = CAST(:tid AS uuid)"
                    ),
                    {"tid": thread_id},
                )
            ).scalar_one()
            assert db_count == 14
    finally:
        await engine.dispose()
