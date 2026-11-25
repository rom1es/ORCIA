"""Story 29.2 (Security Layer) — Strict CONFIDENTIAL_RESTRICTED & PRIVATE_USER isolation."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from tests.security._story_29_2_fixtures import (
    WS_CONF_ID,
    WS_PRIV_ID,
    build_confidential_isolation_app,
)

_WS_CONF_ID = WS_CONF_ID


@pytest.mark.asyncio
async def test_confidential_restricted_isolation_blocks_non_member_admin_teammate_and_bu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify non-member PLATFORM_ADMIN (karim), teammate (nadia), and BU (claire) are denied."""
    app = build_confidential_isolation_app(monkeypatch)
    unknown_ws = "0195f292-0000-7000-8000-999999999999"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for intruder in ("karim", "nadia", "claire"):
            # 1. Ontology state hides 3_WORKSPACE & PRIVATE_USER concepts
            r_onto = await client.get(
                "/api/v1/ontology-rag/state",
                params={"persona_key": intruder, "workspace_id": _WS_CONF_ID},
            )
            assert r_onto.status_code == 200
            onto_keys = {c["concept_key"] for c in r_onto.json()["concepts"]}
            assert "secret_merger_codename" not in onto_keys
            assert "private_marc_term" not in onto_keys

            # 1b. /ontology/resolve & /ontology/what-if deny non-members on confidential/private
            for target_ws in (_WS_CONF_ID, WS_PRIV_ID):
                r_res = await client.post(
                    "/api/v1/ontology-rag/ontology/resolve",
                    params={"persona_key": intruder},
                    json={"workspace_scope_id": target_ws, "human_profile": "TECH_LEAD"},
                )
                assert r_res.status_code == 403
                assert r_res.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"
            for secret_key in ("secret_merger_codename", "private_marc_term"):
                r_wi = await client.post(
                    "/api/v1/ontology-rag/ontology/what-if",
                    params={"persona_key": intruder},
                    json={"concept_key": secret_key, "proposed_change": "Probe"},
                )
                assert r_wi.status_code == 403
                assert r_wi.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            # 2. Hybrid RAG search denies access (403 ERR_SCOPE_ACCESS_DENIED)
            r_rag = await client.post(
                f"/api/v1/ontology-rag/rag/search?persona_key={intruder}",
                json={"workspace_id": _WS_CONF_ID, "query_text": "Phoenix", "top_k": 3},
            )
            assert r_rag.status_code == 403
            assert r_rag.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            # 3. Workspace governance routes & datasources & PATCH deny non-members
            for method, path, body in (
                ("GET", f"/api/v1/workspaces/{_WS_CONF_ID}/five-tabs", None),
                ("GET", f"/api/v1/workspaces/{_WS_CONF_ID}/exception-waivers", None),
                (
                    "POST",
                    f"/api/v1/workspaces/{_WS_CONF_ID}/artifacts/resolve-destination",
                    {
                        "workspace_slug": "ws-projet-confidentiel",
                        "artifact_type": "tech-spec",
                        "artifact_slug": "spec-1",
                        "version": 1,
                        "content_markdown": "# Secret",
                    },
                ),
                ("PATCH", f"/api/v1/workspaces/{_WS_CONF_ID}", {"name": "Hijacked Name"}),
            ):
                r_gov = await client.request(
                    method, path, params={"persona_key": intruder}, json=body
                )
                assert r_gov.status_code == 403, f"{intruder} {method} {path}: {r_gov.text}"
                assert r_gov.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            r_ds = await client.get(
                f"/api/v1/workspaces/{_WS_CONF_ID}/datasources", params={"persona": intruder}
            )
            assert r_ds.status_code == 403
            assert r_ds.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

        # 4. Explicit member (marc) keeps access on ontology, resolve, what-if & FinOps
        r_marc_onto = await client.get(
            "/api/v1/ontology-rag/state",
            params={"persona_key": "marc", "workspace_id": _WS_CONF_ID},
        )
        assert r_marc_onto.status_code == 200
        assert any(
            c["concept_key"] == "secret_merger_codename" for c in r_marc_onto.json()["concepts"]
        )
        assert (
            await client.post(
                "/api/v1/ontology-rag/ontology/resolve",
                params={"persona_key": "marc"},
                json={"workspace_scope_id": _WS_CONF_ID, "human_profile": "TECH_LEAD"},
            )
        ).status_code == 200
        assert (
            await client.post(
                "/api/v1/ontology-rag/ontology/what-if",
                params={"persona_key": "marc"},
                json={"concept_key": "secret_merger_codename", "proposed_change": "Refine"},
            )
        ).status_code == 200

        # 5. FinOps aggregate counters preserved for karim while payloads & PRIVATE_USER stay masked
        r_cc = await client.get(
            "/api/v1/control-center/overview",
            params={"scope_type": "GLOBAL", "persona_key": "karim"},
        )
        assert r_cc.status_code == 200
        cc_body = r_cc.json()
        ws_conf_gov = next(
            g for g in cc_body["workspaces_governance"] if g["workspace_id"] == _WS_CONF_ID
        )
        assert ws_conf_gov["finops_cost_usd"] == 310.0
        assert ws_conf_gov["blackboard_payload_masked"] is True
        assert all(g["workspace_id"] != WS_PRIV_ID for g in cc_body["workspaces_governance"])
        assert all(d["workspace_id"] != _WS_CONF_ID for d in cc_body["datasources"])
        masked_run = next(r for r in cc_body["observer_runs"] if r["workspace_id"] == _WS_CONF_ID)
        assert masked_run["blackboard_payload_masked"] is True
        assert masked_run["workflow_key"] == "masked"
        assert masked_run["current_step_key"] == "masked"
        assert masked_run["workspace_name"] == "[CONFIDENTIAL_RESTRICTED]"

        r_cc_priv = await client.get(
            "/api/v1/control-center/overview",
            params={"scope_type": "WORKSPACE", "scope_id": WS_PRIV_ID, "persona_key": "karim"},
        )
        assert r_cc_priv.status_code == 403
        assert r_cc_priv.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

        # 6. DNA/Glossary, Codegraph MCP, Webhooks, Ontology/RAG, Promotions, Leases & Connectors
        for intruder in ("karim", "nadia", "claire"):
            r_state = await client.get(
                "/api/v1/ontology-rag/state", params={"persona_key": intruder}
            )
            assert r_state.status_code == 200
            assert not any(
                p["proposal_key"] == "prop-conf-292" for p in r_state.json()["promotions"]
            )
            assert not any(
                e["edge_key"] == "unknown-ws-edge-292" for e in r_state.json()["tripartite_edges"]
            )
            r_promos = await client.get(
                "/api/v1/ontology-rag/ontology/promotions", params={"persona_key": intruder}
            )
            assert r_promos.status_code == 200
            assert not any(
                p["proposal_key"] == "prop-conf-292" for p in r_promos.json()["proposals"]
            )
            r_dec = await client.post(
                "/api/v1/ontology-rag/ontology/promotions/prop-conf-292/decide",
                params={"persona_key": intruder},
                json={"decision": "APPROVE", "review_comment": "Bypass attempt"},
            )
            assert r_dec.status_code == 403

            for method, path, body in (
                ("GET", f"/api/v1/workspaces/{_WS_CONF_ID}/dna-mechanisms", None),
                ("GET", f"/api/v1/workspaces/{unknown_ws}/dna-mechanisms", None),
                ("GET", f"/api/v1/workspaces/{_WS_CONF_ID}/codegraph/tools", None),
                ("GET", f"/api/v1/workspaces/{unknown_ws}/codegraph/tools", None),
                (
                    "POST",
                    f"/api/v1/workspaces/{_WS_CONF_ID}/codegraph/invoke",
                    {"tool_name": "codegraph_locate_symbol", "arguments": {"repo_alias": "r"}},
                ),
                (
                    "POST",
                    f"/api/v1/workspaces/{_WS_CONF_ID}/datasources/reconcile-staleness",
                    None,
                ),
                (
                    "POST",
                    "/api/v1/ontology-rag/rag/search",
                    {"workspace_id": unknown_ws, "query_text": "secret", "top_k": 3},
                ),
                (
                    "POST",
                    "/api/v1/ontology-rag/rag/index-db-ddl",
                    {
                        "workspace_id": _WS_CONF_ID,
                        "datasource_id": "ds-1",
                        "datasource_alias": "db_conf",
                        "db_uri": "db://conf/db",
                        "ddl_sql": "CREATE TABLE t (id INT);",
                        "schema_version": "v1",
                    },
                ),
                (
                    "POST",
                    "/api/v1/ontology-rag/tripartite/audit-doc-vs-code",
                    {
                        "workspace_id": _WS_CONF_ID,
                        "confluence_uri": "confluence://SEC/1",
                        "git_repo_uri": "git://sec/repo",
                        "git_symbol": "fn",
                        "doc_rule_summary": "A",
                        "code_rule_summary": "B",
                    },
                ),
                (
                    "POST",
                    "/api/v1/resource-leases/acquire",
                    {
                        "resource_uris": [f"orcia://{_WS_CONF_ID}/artifact/secret-1"],
                        "holder_run_id": "run-1",
                        "holder_root_run_id": "run-1",
                        "holder_step_execution_id": "step-1",
                        "ttl_seconds": 60,
                    },
                ),
                (
                    "POST",
                    "/api/v1/resource-leases/fenced-write",
                    {
                        "resource_uri": f"orcia://{unknown_ws}/artifact/secret-1",
                        "fencing_token": 1,
                        "payload": {"op": "hijack"},
                    },
                ),
            ):
                resp = await client.request(
                    method, path, params={"persona_key": intruder}, json=body
                )
                assert resp.status_code == 403, f"{intruder} {method} {path}: {resp.text}"

        # Explicit member (marc) retains access to DNA, Codegraph tools & Leases on _WS_CONF_ID
        assert (
            await client.get(
                f"/api/v1/workspaces/{_WS_CONF_ID}/dna-mechanisms", params={"persona_key": "marc"}
            )
        ).status_code == 200
        assert (
            await client.get(
                f"/api/v1/workspaces/{_WS_CONF_ID}/codegraph/tools", params={"persona_key": "marc"}
            )
        ).status_code == 200
        assert (
            await client.post(
                f"/api/v1/workspaces/{_WS_CONF_ID}/codegraph/invoke",
                params={"persona_key": "marc"},
                headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
                json={"tool_name": "codegraph_locate_symbol", "arguments": {"repo_alias": "r"}},
            )
        ).status_code == 403

        # 7. GET /api/v1/settings/connectors enforces admin RBAC
        r_conn_denied = await client.get("/api/v1/settings/connectors", params={"persona": "nadia"})
        assert r_conn_denied.status_code == 403
        assert r_conn_denied.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"
        r_conn_ok = await client.get("/api/v1/settings/connectors", params={"persona": "karim"})
        assert r_conn_ok.status_code == 200
