"""Unit & structural compliance tests for Story 7.0c (OpenShift SCC, /ready, sandbox-runner)."""

from __future__ import annotations

import logging
import pathlib
import time
from typing import Any

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.observability.logging import (
    clear_trace_context,
    configure_logging,
)
from orcia_worker.roles import main as roles_cli_main
from orcia_worker.sandbox_daemon import SandboxDaemonServer

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ready_probes_respond_under_100ms_without_sql_and_handle_uninitialized(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `/ready` and `/api/v1/ready` answer in `< 100 ms` and filter 200 access logs."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    clear_trace_context()
    configure_logging(service="api", log_level="INFO")
    app = create_app()
    client = TestClient(app)
    trace_id = "0195f00070c07000800000000000070c"

    # Warm TestClient's lazy AnyIO portal and FastAPI route-state cache without
    # entering `with TestClient(app)` (which would trigger PG/DBOS lifespan).
    warmup_res = client.get("/ready", headers={"X-Trace-Id": trace_id})
    assert warmup_res.status_code == 200

    for path in ("/ready", "/api/v1/ready"):
        start_ns = time.monotonic_ns()
        res = client.get(path, headers={"X-Trace-Id": trace_id})
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000
        assert res.status_code == 200
        assert elapsed_ms < 100.0
        body = res.json()
        assert body["status"] == "ready"
        assert body["initialized"] is True
        assert body["trace_id"] == trace_id
        assert body["version"]

    # Simulate regular 200 probe access logs: must be filtered by HealthProbeLogFilter
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.info('127.0.0.1:42000 - "GET /ready HTTP/1.1" 200')
    access_logger.info('127.0.0.1:42000 - "GET /api/v1/ready HTTP/1.1" 200')
    assert capsys.readouterr().out.strip() == ""

    # When Composition Root services are missing, readiness returns 503 RFC 9457
    app.state.orchestration_service = None
    not_ready = client.get("/ready", headers={"X-Trace-Id": trace_id})
    assert not_ready.status_code == 503
    assert not_ready.headers["content-type"].startswith("application/problem+json")
    err = not_ready.json()
    assert err["error_code"] == "ERR_API_NOT_READY"
    assert err["trace_id"] == trace_id


@pytest.mark.asyncio
async def test_sandbox_daemon_http_auth_tmp_isolation_and_roles_cli(
    tmp_path: pathlib.Path,
) -> None:
    """Verify `sandbox_daemon.py` on ephemeral port (`127.0.0.1:0`), auth, `/tmp` & `--serve`."""
    daemon_tmp = tmp_path / "sandbox-tmp"
    internal_token = "orcia-test-sandbox-token-70c"  # pragma: allowlist secret
    server = SandboxDaemonServer(
        host="127.0.0.1",
        port=0,
        tmp_dir=str(daemon_tmp),
        internal_token=internal_token,
    )
    await server.start()
    try:
        base_url = f"http://127.0.0.1:{server.port}"
        async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
            health = await client.get("/health")
            assert health.status_code == 200
            assert health.json() == {"status": "ok", "role": "sandbox-runner"}

            unauth = await client.post("/execute-tier1", json={"payload": {}})
            assert unauth.status_code == 401

            forbidden = await client.post(
                "/execute-tier1",
                headers={"X-Orcia-Sandbox-Token": "wrong-token"},  # pragma: allowlist secret
                json={"payload": {}},
            )
            assert forbidden.status_code == 403

            bad_json = await client.post(
                "/execute-tier1",
                headers={
                    "X-Orcia-Sandbox-Token": internal_token,
                    "Content-Type": "application/json",
                },
                content=b"{not-json",
            )
            assert bad_json.status_code == 400

            unknown = await client.get("/unknown-path")
            assert unknown.status_code == 404

            ok_res = await client.post(
                "/execute-tier1",
                headers={"X-Orcia-Sandbox-Token": internal_token},
                json={
                    "entrypoint": "gate_check",
                    "payload": {
                        "artifact": {"summary": "valid"},
                        "required_sections": ["summary"],
                    },
                },
            )
            assert ok_res.status_code == 200
            ok_body = ok_res.json()
            assert ok_body["passed"] is True
            assert ok_body["exit_code"] == 0
            assert ok_body["result"]["schema_validation_passed"] is True

            # Network escape inside Tier 1 sandbox must fail with exit_code 126
            net_res = await client.post(
                "/execute-tier1",
                headers={"X-Orcia-Sandbox-Token": internal_token},
                json={"payload": {"simulate_network_escape": True}},
            )
            assert net_res.status_code == 200
            assert net_res.json()["passed"] is False
            assert net_res.json()["exit_code"] == 126

            # Hardware timeout inside Tier 1 sandbox must fail with exit_code 124
            timeout_res = await client.post(
                "/execute-tier1",
                headers={"X-Orcia-Sandbox-Token": internal_token},
                json={"timeout_ms": 80, "payload": {"simulate_timeout_sleep_ms": 400}},
            )
            assert timeout_res.status_code == 200
            assert timeout_res.json()["passed"] is False
            assert timeout_res.json()["exit_code"] == 124
            assert "ERR_SANDBOX_TIMEOUT_EXCEEDED" in timeout_res.json()["stderr"]

            # Ephemeral scratch directories under daemon_tmp must be cleaned up
            assert list(daemon_tmp.iterdir()) == []
    finally:
        await server.close()

    # Verify zero nested podman/docker invocations in executable code of daemon and roles modules
    import ast

    for rel in (
        "apps/worker/src/orcia_worker/sandbox_daemon.py",
        "apps/worker/src/orcia_worker/roles.py",
    ):
        tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_src = ast.unparse(node).lower()
                assert "podman" not in call_src
                assert "docker" not in call_src


def test_roles_cli_serve_once_exits_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify CLI `--serve --once` exits cleanly for operational worker roles."""
    import sys

    monkeypatch.delitem(sys.modules, "orcia_worker.docling_indexer", raising=False)
    assert (
        roles_cli_main(
            ["--role", "sandbox-runner", "--serve", "--once", "--host", "127.0.0.1", "--port", "0"]
        )
        == 0
    )
    assert roles_cli_main(["--role", "worker-orchestration", "--serve", "--once"]) == 0
    assert roles_cli_main(["--role", "trigger-dispatcher", "--serve", "--once"]) == 0


def test_dockerfiles_and_compose_openshift_rootless_hardening() -> None:
    """Verify non-root Dockerfiles, nginx `/tmp` config, and hardened `docker-compose.yml`."""
    dockerfile = (REPO_ROOT / "infra" / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.12-slim" in dockerfile
    assert "uv.lock" not in dockerfile
    assert "--frozen" not in dockerfile
    assert "chgrp -R 0 /app" in dockerfile
    assert "chmod -R g=u /app" in dockerfile
    assert "USER 10001:0" in dockerfile
    assert "--no-access-log" in dockerfile

    dockerfile_web = (REPO_ROOT / "infra" / "docker" / "Dockerfile.web").read_text(encoding="utf-8")
    assert "node:24-alpine" in dockerfile_web
    assert "nginxinc/nginx-unprivileged:1.27-alpine" in dockerfile_web
    assert "USER 101:0" in dockerfile_web
    assert "EXPOSE 8080" in dockerfile_web

    nginx_conf = (REPO_ROOT / "infra" / "docker" / "nginx.conf").read_text(encoding="utf-8")
    assert "pid /tmp/nginx.pid;" in nginx_conf
    assert "listen 8080;" in nginx_conf
    assert "/tmp/nginx_client_temp" in nginx_conf

    compose = yaml.safe_load(
        (REPO_ROOT / "infra" / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    )
    services = compose["services"]
    for role in (
        "api",
        "worker-orchestration",
        "worker-indexing",
        "trigger-dispatcher",
        "sandbox-runner",
    ):
        svc = services[role]
        assert svc["user"] == "10001:0"
        assert svc["read_only"] is True
        assert "no-new-privileges:true" in svc["security_opt"]
        tmpfs_entries = svc["tmpfs"]
        assert any(str(entry).startswith("/tmp:") for entry in tmpfs_entries)
        if role == "sandbox-runner":
            assert any("256m" in str(entry) for entry in tmpfs_entries)


def test_kustomize_base_openshift_overlay_and_clusterlogforwarder_contract() -> None:
    """Validate 100% of single-doc Kustomize YAML manifests (`base` & `openshift`) and contract."""
    base_dir = REPO_ROOT / "infra" / "k8s" / "base"
    overlay_dir = REPO_ROOT / "infra" / "k8s" / "overlays" / "openshift"

    # Every YAML under infra/k8s must be a single-document YAML (`check-yaml` compliant)
    for yaml_path in sorted((REPO_ROOT / "infra" / "k8s").rglob("*.yaml")):
        loaded = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert isinstance(loaded, dict), f"Expected single YAML mapping in {yaml_path}"

    base_kustomize = yaml.safe_load((base_dir / "kustomization.yaml").read_text(encoding="utf-8"))
    assert "secret-template.yaml" not in base_kustomize["resources"]
    assert set(base_kustomize["resources"]) >= {
        "configmap.yaml",
        "deployment-api.yaml",
        "deployment-worker-orchestration.yaml",
        "deployment-worker-indexing.yaml",
        "deployment-trigger-dispatcher.yaml",
        "deployment-sandbox-runner.yaml",
        "deployment-web.yaml",
        "service-api.yaml",
        "service-web.yaml",
        "service-sandbox-runner.yaml",
        "networkpolicy-sandbox-runner.yaml",
        "networkpolicy-runtime-egress.yaml",
    }

    secret_tpl = yaml.safe_load((base_dir / "secret-template.yaml").read_text(encoding="utf-8"))
    assert secret_tpl["kind"] == "Secret"
    for val in secret_tpl["stringData"].values():
        assert val == ""

    deployments: list[dict[str, Any]] = [
        yaml.safe_load(p.read_text(encoding="utf-8"))
        for p in sorted(base_dir.glob("deployment-*.yaml"))
    ]
    assert len(deployments) == 6
    by_name = {d["metadata"]["name"]: d for d in deployments}
    for dep_name in (
        "orcia-api",
        "orcia-worker-orchestration",
        "orcia-worker-indexing",
        "orcia-trigger-dispatcher",
        "orcia-sandbox-runner",
        "orcia-web",
    ):
        dep = by_name[dep_name]
        pod_spec = dep["spec"]["template"]["spec"]
        pod_sc = pod_spec["securityContext"]
        assert pod_sc["runAsNonRoot"] is True
        assert pod_sc["seccompProfile"]["type"] == "RuntimeDefault"
        assert "runAsUser" not in pod_sc
        assert "fsGroup" not in pod_sc

        container = pod_spec["containers"][0]
        c_sc = container["securityContext"]
        assert c_sc["allowPrivilegeEscalation"] is False
        assert c_sc["readOnlyRootFilesystem"] is True
        assert c_sc["capabilities"]["drop"] == ["ALL"]
        assert "runAsUser" not in c_sc

        mounts = {m["mountPath"]: m["name"] for m in container["volumeMounts"]}
        assert "/tmp" in mounts
        vols = {v["name"]: v for v in pod_spec["volumes"]}
        tmp_vol = vols[mounts["/tmp"]]["emptyDir"]
        assert tmp_vol["medium"] == "Memory"
        expected_limit = "256Mi" if dep_name == "orcia-sandbox-runner" else "64Mi"
        assert tmp_vol["sizeLimit"] == expected_limit

    api_container = by_name["orcia-api"]["spec"]["template"]["spec"]["containers"][0]
    assert api_container["livenessProbe"]["httpGet"]["path"] == "/api/v1/health"
    assert api_container["readinessProbe"]["httpGet"]["path"] == "/ready"

    netpols: list[dict[str, Any]] = [
        yaml.safe_load(p.read_text(encoding="utf-8"))
        for p in sorted(base_dir.glob("networkpolicy-*.yaml"))
    ]
    netpol_map = {n["metadata"]["name"]: n for n in netpols}
    sandbox_np = netpol_map["orcia-sandbox-runner-isolation"]
    assert sandbox_np["spec"]["egress"] == []
    assert sandbox_np["spec"]["policyTypes"] == ["Ingress", "Egress"]

    # Overlay OpenShift must never hardcode runAsUser or fsGroup
    for yaml_path in sorted(overlay_dir.glob("*.yaml")):
        raw = yaml_path.read_text(encoding="utf-8")
        assert "runAsUser" not in raw, f"Hardcoded runAsUser forbidden in {yaml_path}"
        assert "fsGroup" not in raw, f"Hardcoded fsGroup forbidden in {yaml_path}"
        doc = yaml.safe_load(raw)
        assert isinstance(doc, dict)

    patches = [
        yaml.safe_load(p.read_text(encoding="utf-8"))
        for p in sorted(overlay_dir.glob("patch-scc-*.yaml"))
    ]
    assert len(patches) == 6

    routes = [
        yaml.safe_load(p.read_text(encoding="utf-8"))
        for p in sorted(overlay_dir.glob("route-*.yaml"))
    ]
    assert {r["metadata"]["name"] for r in routes} == {"orcia-web", "orcia-api"}
    for route in routes:
        assert route["kind"] == "Route"
        assert route["spec"]["tls"]["termination"] == "edge"

    contract_path = REPO_ROOT / "docs" / "operations" / "openshift-clusterlogforwarder-contract.md"
    contract_text = contract_path.read_text(encoding="utf-8")
    for required_clause in (
        "OPS-OPENSHIFT-LOGGING-01",
        "structuredTypeKey",
        "LogSinkQueryPort",
        "NetworkPolicy",
        "NFR-SEC-4",
    ):
        assert required_clause in contract_text
