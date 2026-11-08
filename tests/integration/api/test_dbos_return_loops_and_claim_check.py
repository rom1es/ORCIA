"""Integration & API tests for TASK-05 (`test_dbos_return_loops_and_claim_check.py`).

Validates:
- `GET /api/v1/packs` & `POST /api/v1/packs/export/{workspace_id}` (healthchecks + `.zip` export)
- `GET /api/v1/vsm` & `GET /api/v1/workflows/v2`
- `PUT /api/v1/workflows/v2/{id}` auto-forking `PUBLISHED` -> `vX.Y.Z-draft` (`CA-9.1.2`)
- `POST /api/v1/workflows/v2/{id}/what-if` isolated dry-run (`external_writes == 0`, `CA-9.3.4`)
- `POST /api/v1/workflows/v2/{id}/runs` & `POST /api/v1/runs/{run_id}/hitl-signal`:
  - Cyclic idempotency keys `f"{run_id}:{sub_step.id}:iter-{iteration}"` (`CA-9.5.3`)
  - S3 `ClaimCheckPointer` persistence & `AMEND_DIFF` with new `SHA-256` (`CA-9.5.2`)
  - Return loop (`REJECT_AND_LOOP`) in `corrections` mode (`iter-2`)
  - `EXTERNAL_DELEGATED_GATE` (`wf-08-dev-external-gate`) waiting for external PR event (`CA-9.3.3`)
"""

from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient

from orcia_api.main import app


def test_packs_registry_healthcheck_and_zip_export_endpoints() -> None:
    """Verify `GET /api/v1/packs` and `POST /api/v1/packs/export/{workspace_id}`."""
    with TestClient(app) as client:
        resp = client.get("/api/v1/packs")
        assert resp.status_code == 200
        data = resp.json()
        pack_ids = {p["id"] for p in data["packs"]}
        assert {"orcia-pack-sdlc", "orcia-pack-docs"}.issubset(pack_ids)

        sdlc = next(p for p in data["packs"] if p["id"] == "orcia-pack-sdlc")
        assert sdlc["agents_count"] == 4
        assert sdlc["skills_count"] == 4
        assert sdlc["gates_count"] == 6
        assert sdlc["vsm_count"] == 1
        assert sdlc["workflows_count"] == 4
        assert len(sdlc["connector_health"]) == 3
        assert all(item["health"]["ok"] is True for item in sdlc["connector_health"])

        export_resp = client.post(
            "/api/v1/packs/export/ws-mon-compte",
            params={"pack_id": "orcia-pack-sdlc"},
        )
        assert export_resp.status_code == 200
        assert export_resp.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(export_resp.content), "r") as zf:
            names = zf.namelist()
            assert "sdlc/pack.yaml" in names
            assert "sdlc/workflows/vsm-mon-compte-idea-to-prod.yaml" in names


def test_vsm_and_workflow_v2_draft_fork_and_what_if_simulation() -> None:
    """Verify VSM listing, workflow draft forking (`CA-9.1.2`), and What-If dry-run (`CA-9.3.4`)."""
    with TestClient(app) as client:
        vsm_resp = client.get("/api/v1/vsm/vsm-mon-compte-idea-to-prod")
        assert vsm_resp.status_code == 200
        vsm = vsm_resp.json()
        assert len(vsm["phases"]) == 4

        wf_resp = client.get("/api/v1/workflows/v2/wf-01-qualification-prd")
        assert wf_resp.status_code == 200
        wf = wf_resp.json()
        assert wf["status"] == "published"

        # Modify a PUBLISHED workflow -> auto-forks as -draft
        modified_wf = dict(wf)
        modified_wf["title"] = "Qualification & PRD (Fork Studio)"
        put_resp = client.put(
            "/api/v1/workflows/v2/wf-01-qualification-prd",
            json={"workflow": modified_wf, "publish": False},
        )
        assert put_resp.status_code == 200
        saved = put_resp.json()
        assert saved["forked_as_draft"] is True
        assert saved["workflow"]["status"] == "draft"
        assert saved["workflow"]["version"].endswith("-draft")

        # Run What-If sandbox simulation -> 0 external writes
        what_if_resp = client.post(
            "/api/v1/workflows/v2/wf-01-qualification-prd/what-if",
            json={"sample_inputs": {"demande_source": "MCIA-101"}},
        )
        assert what_if_resp.status_code == 200
        impact = what_if_resp.json()
        assert impact["sandbox_isolated"] is True
        assert impact["external_writes_executed"] == 0
        assert impact["sub_steps_evaluated"] == 3


def test_dbos_bounded_workflow_claim_check_amend_diff_and_return_loop() -> None:
    """Verify cyclic idempotency (`:iter-{iteration}`), S3 Claim-Check, diff amend, and loops."""
    with TestClient(app) as client:
        # 1. Start wf-01-qualification-prd (3 sub-steps: qualification -> prd -> jira)
        start_resp = client.post(
            "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
            json={"inputs": {"demande_source": "MCIA-42"}},
        )
        assert start_resp.status_code == 200
        run = start_resp.json()["run"]
        run_id = run["run_id"]
        assert run["status"] == "WAITING_SUBSTEP_HITL"
        assert len(run["sub_step_records"]) == 1
        sub1 = run["sub_step_records"][0]
        assert sub1["sub_step_id"] == "qualification"
        assert sub1["idempotency_key"] == f"{run_id}:qualification:iter-1"
        assert sub1["artifact_pointer"]["s3_uri"].startswith(f"s3://orcia-artifacts/{run_id}/")
        orig_sha = sub1["artifact_pointer"]["sha256"]

        # 2. Approve sub-step 1 (with amended markdown in S3) -> advances to sub-step 2 (prd)
        sig1 = client.post(
            f"/api/v1/runs/{run_id}/hitl-signal",
            json={
                "action": "AMEND_DIFF",
                "actor_id": "u-claire-po",
                "amended_markdown": (
                    "# PRD\n\n## Contexte\nBesoin qualifié et amendé par le PO.\n\n"
                    "## Objectifs & KPI\nKPI +25% conversion.\n\n"
                    "## Critères d'acceptation\nGherkin complet.\n\n"
                    "## WSJF\nScore WSJF = 8.5\n"
                ),
            },
        )
        assert sig1.status_code == 200
        run = sig1.json()["run"]
        assert run["sub_step_records"][0]["artifact_pointer"]["sha256"] != orig_sha
        assert len(run["sub_step_records"]) == 2
        assert run["sub_step_records"][1]["sub_step_id"] == "prd"

        # 3. Approve sub-step 2 (prd) -> advances to sub-step 3 (jira, with WritePreviewCard)
        sig2 = client.post(
            f"/api/v1/runs/{run_id}/hitl-signal",
            json={"action": "APPROVE", "actor_id": "u-claire-po"},
        )
        assert sig2.status_code == 200
        run = sig2.json()["run"]
        assert len(run["sub_step_records"]) == 3
        sub3 = run["sub_step_records"][2]
        assert sub3["sub_step_id"] == "jira"
        assert sub3["status"] == "WAITING_WRITE_PREVIEW"
        assert sub3["write_preview_card"] is not None

        # 4. Approve sub-step 3 WritePreviewCard -> runs Gates Pipeline -> WAITING_FINAL_ANCHOR
        sig3 = client.post(
            f"/api/v1/runs/{run_id}/hitl-signal",
            json={"action": "APPROVE", "actor_id": "u-claire-po"},
        )
        assert sig3.status_code == 200
        run = sig3.json()["run"]
        assert run["status"] == "WAITING_FINAL_ANCHOR"
        assert run["gate_report"] is not None

        # 5. Trigger Action 3 on Final Anchor Card: REJECT_AND_LOOP -> iter-2 in corrections mode
        sig_loop = client.post(
            f"/api/v1/runs/{run_id}/hitl-signal",
            json={
                "action": "REJECT_AND_LOOP",
                "actor_id": "u-comite-accueil",
                "target_step_num": "02",
                "target_sub_step_id": "prd",
                "correction_remarks": "Préciser les hypothèses de gain WSJF sur le segment pro.",
            },
        )
        assert sig_loop.status_code == 200
        run = sig_loop.json()["run"]
        assert run["status"] == "RETURN_LOOP_TRIGGERED"
        assert run["iteration"] == 2
        assert run["reentry_mode"] == "corrections"
        last_rec = run["sub_step_records"][-1]
        assert last_rec["idempotency_key"] == f"{run_id}:prd:iter-2"
        assert "segment pro" in (last_rec["correction_remarks_applied"] or "")


def test_external_delegated_gate_workflow_mode() -> None:
    """Verify `EXTERNAL_DELEGATED_GATE` (`wf-08-dev-external-gate`) exposes MCP bundle & gates."""
    with TestClient(app) as client:
        start_resp = client.post(
            "/api/v1/workflows/v2/wf-08-dev-external-gate/runs",
            json={"inputs": {"us_key": "MCIA-US-204"}},
        )
        assert start_resp.status_code == 200
        run = start_resp.json()["run"]
        run_id = run["run_id"]
        assert run["execution_mode"] == "external_delegated"
        assert run["status"] == "WAITING_EXTERNAL_GATE"
        assert run["mcp_context_bundle"]["expected_event"] == "git:pr_opened"

        # Simulate external git:pr_opened completion -> runs Gatekeeper -> WAITING_FINAL_ANCHOR
        ext_sig = client.post(
            f"/api/v1/runs/{run_id}/hitl-signal",
            json={
                "action": "APPROVE",
                "actor_id": "webhook-git-provider",
                "amended_markdown": (
                    "# Rapport de Sas Externe PR\n\n"
                    "Implémentation complète de MCIA-US-204 validée par les tests unitaires."
                ),
            },
        )
        assert ext_sig.status_code == 200
        run = ext_sig.json()["run"]
        assert run["status"] == "WAITING_FINAL_ANCHOR"
        assert run["gate_report"]["deterministic_passed"] is True
