"""Story 18.4 Infrastructure Tests: Docker Compose GitNexus MCP Sidecar & Isolation.

Verifies:
- gitnexus_graphs named volume isolation.
- gitnexus-mcp container mounted strictly read-only (:ro).
- worker-indexing mounted read-write.
- codegraph-internal isolated network marked internal: true.
- Zero ports exposed to the host on gitnexus-mcp.
- Zero Git provider tokens (GITLAB_TOKEN, GITHUB_TOKEN) in gitnexus-mcp environment.
- Container hardening flags: read_only: true, no-new-privileges:true, tmpfs.
- CODEGRAPH_MCP_ENDPOINT wired to api and worker-orchestration.
- Documentation in .env.example.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PATH = REPO_ROOT / "infra" / "docker" / "docker-compose.yml"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"


def _load_compose() -> dict[str, Any]:
    assert COMPOSE_PATH.exists(), f"Compose file missing at {COMPOSE_PATH}"
    with open(COMPOSE_PATH, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return data


def test_docker_compose_named_volumes_and_networks() -> None:
    compose = _load_compose()
    volumes = compose.get("volumes", {})
    assert "gitnexus_graphs" in volumes, "gitnexus_graphs volume must be declared"

    networks = compose.get("networks", {})
    assert "codegraph-internal" in networks, "codegraph-internal network must be declared"
    net_config = networks["codegraph-internal"]
    assert net_config.get("internal") is True, "codegraph-internal network must be internal: true"


def test_gitnexus_mcp_sidecar_isolation_and_hardening() -> None:
    compose = _load_compose()
    services = compose.get("services", {})
    assert "gitnexus-mcp" in services, "gitnexus-mcp service must be defined"
    mcp_service = services["gitnexus-mcp"]

    # Strictly no host ports exposed
    assert "ports" not in mcp_service or not mcp_service["ports"], (
        "gitnexus-mcp must have ZERO ports exposed on host"
    )

    # Strictly read-only volume mount for graphs
    vols = mcp_service.get("volumes", [])
    assert any("gitnexus_graphs:/data/graphs:ro" in str(v) for v in vols), (
        f"gitnexus-mcp must mount gitnexus_graphs:/data/graphs:ro, found {vols}"
    )

    # Isolated internal network only
    mcp_networks = mcp_service.get("networks", [])
    assert "codegraph-internal" in mcp_networks, (
        "gitnexus-mcp must be attached to codegraph-internal"
    )
    assert "default" not in mcp_networks, (
        "gitnexus-mcp must NOT be exposed to the default public/app network"
    )

    # Container hardening
    assert mcp_service.get("read_only") is True, "gitnexus-mcp must have read_only: true"
    sec_opts = mcp_service.get("security_opt", [])
    assert "no-new-privileges:true" in sec_opts, "gitnexus-mcp must enforce no-new-privileges:true"
    assert mcp_service.get("tmpfs"), "gitnexus-mcp must configure tmpfs"

    # Environment isolation - zero Git tokens
    env = mcp_service.get("environment", {})
    if isinstance(env, list):
        env_dict = {item.split("=")[0]: item.split("=")[1] if "=" in item else "" for item in env}
    else:
        env_dict = env

    assert "GITLAB_TOKEN" not in env_dict, "gitnexus-mcp must not hold GITLAB_TOKEN"
    assert "GITHUB_TOKEN" not in env_dict, "gitnexus-mcp must not hold GITHUB_TOKEN"
    assert env_dict.get("GITNEXUS_STORAGE_ROOT") == "/data/graphs"
    assert env_dict.get("GITNEXUS_CONTENT_RETENTION") == "symbol"


def test_worker_indexing_mounts_graphs_rw() -> None:
    compose = _load_compose()
    services = compose.get("services", {})
    assert "worker-indexing" in services, "worker-indexing service must be defined"
    indexer = services["worker-indexing"]

    vols = indexer.get("volumes", [])
    assert any("gitnexus_graphs:/data/graphs" in str(v) and ":ro" not in str(v) for v in vols), (
        f"worker-indexing must mount gitnexus_graphs:/data/graphs read-write, found {vols}"
    )

    env = indexer.get("environment", {})
    assert env.get("GITNEXUS_STORAGE_ROOT") == "/data/graphs"
    assert env.get("GITNEXUS_CONTENT_RETENTION") == "symbol"


def test_api_and_orchestrator_codegraph_wiring() -> None:
    compose = _load_compose()
    services = compose.get("services", {})

    for service_name in ("api", "worker-orchestration"):
        assert service_name in services, f"{service_name} must exist"
        svc = services[service_name]
        svc_networks = svc.get("networks", [])
        assert "codegraph-internal" in svc_networks, (
            f"{service_name} must have codegraph-internal network attached"
        )
        env = svc.get("environment", {})
        assert env.get("CODEGRAPH_MCP_ENDPOINT") == "http://gitnexus-mcp:8095/mcp"
        assert "CODEGRAPH_PROVIDER" in env


def test_env_example_documents_codegraph_variables() -> None:
    assert ENV_EXAMPLE_PATH.exists(), f".env.example missing at {ENV_EXAMPLE_PATH}"
    content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    assert "CODEGRAPH_PROVIDER" in content
    assert "CODEGRAPH_MCP_ENDPOINT" in content
    assert "ORCIA_CODEGRAPH_INTERNAL_TOKEN" in content
    assert "GITNEXUS_STORAGE_ROOT" in content
    assert "GITNEXUS_CONTENT_RETENTION" in content
