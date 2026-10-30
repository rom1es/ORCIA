"""Story 4.1a tests: Tier 2 Container Sandbox, TDD Red->Green & 5 Deployment Roles (`ARCH-P5`)."""

from __future__ import annotations

import pathlib
import sys
import tempfile
import tomllib

import pytest
import yaml
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.gates import (
    BimodalSandboxAdapter,
    ContainerSandboxRunner,
    ContainerSandboxSpec,
    DeterministicGateService,
    PolicyDeniedError,
    TddRemediationCheckInput,
    UpstreamTimeoutError,
    build_tier2_container_cli_args,
)
from orcia_kernel.ports import SandboxExecutionRequest
from orcia_worker.roles import (
    list_deployment_role_specs,
    verify_role_process_isolation,
)
from orcia_worker.roles import (
    main as roles_cli_main,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKSPACE_ID = "0192c4e0-0000-7000-8000-000000000201"
RUN_ID = "0192c4e0-0000-7000-8000-000000004101"


def test_story_4_1a_container_spec_and_bimodal_tdd_red_green() -> None:
    """Verify Tier 2 Container CLI args (`gVisor`/`Podman`) and real `pytest` TDD Red -> Green."""
    # 1. Verify rootless Podman & gVisor runsc CLI flags (--network=none, --read-only, etc.)
    podman_args = build_tier2_container_cli_args(
        ContainerSandboxSpec(
            runtime="podman_rootless",
            cas_readonly_host_dir="/var/orcia/cas/sha256_abc",
        )
    )
    assert "--network=none" in podman_args
    assert "--read-only" in podman_args
    assert "/tmp:rw,noexec,nosuid,size=256m" in podman_args
    assert "--memory=1024m" in podman_args
    assert "--cpus=2.0" in podman_args
    assert "--pids-limit=64" in podman_args
    assert "/var/orcia/cas/sha256_abc:/workspace/cas:ro" in podman_args

    gvisor_args = build_tier2_container_cli_args(ContainerSandboxSpec(runtime="gvisor_runsc"))
    assert "--runtime=runsc" in gvisor_args
    assert "--network=none" in gvisor_args

    # 2. Prepare a read-only CAS snapshot directory and run a real TDD Red -> Green loop
    svc = DeterministicGateService()
    with tempfile.TemporaryDirectory(prefix="orcia_cas_ro_") as cas_dir:
        cas_helper = pathlib.Path(cas_dir) / "conftest_helper.py"
        cas_helper.write_text("CAS_SNAPSHOT_CONSTANT = 100\n", encoding="utf-8")

        tdd_res = svc.verify_tdd_red_green(
            TddRemediationCheckInput(
                workspace_id=WORKSPACE_ID,
                run_id=RUN_ID,
                step_key="step-tdd-remediation",
                buggy_files={
                    "calculator.py": (
                        "def compute_vat_cents(amount_cents: int) -> int:\n"
                        "    return amount_cents // 10  # BUG: 10% instead of 20%\n"
                    )
                },
                patched_files={
                    "calculator.py": (
                        "def compute_vat_cents(amount_cents: int) -> int:\n"
                        "    return (amount_cents * 20) // 100\n"
                    )
                },
                test_files={
                    "test_calculator.py": (
                        "from calculator import compute_vat_cents\n"
                        "from conftest_helper import CAS_SNAPSHOT_CONSTANT\n\n\n"
                        "def test_vat_20_percent() -> None:\n"
                        "    assert CAS_SNAPSHOT_CONSTANT == 100\n"
                        "    assert compute_vat_cents(1000) == 200\n"
                    )
                },
                tools=("pytest", "ruff"),
                cas_readonly_dir=cas_dir,
            ),
            raise_on_failure=True,
        )

    assert tdd_res.passed is True
    assert tdd_res.red_reproduced is True
    assert tdd_res.red_exit_code != 0
    assert tdd_res.green_verified is True
    assert len(tdd_res.green_tool_runs) == 2
    assert all(r["passed"] is True for r in tdd_res.green_tool_runs)
    assert len(svc.list_outbox_events()) == 1
    assert svc.list_evaluations(run_id=RUN_ID)[0].sandbox_tier == "TIER_2_CONTAINER"

    # 3. If the test already passes BEFORE the fix (Red not reproduced), TDD verification fails
    false_red = svc.verify_tdd_red_green(
        TddRemediationCheckInput(
            workspace_id=WORKSPACE_ID,
            run_id=RUN_ID,
            step_key="step-tdd-no-red",
            buggy_files={"calc.py": "def add(a: int, b: int) -> int:\n    return a + b\n"},
            patched_files={"calc.py": "def add(a: int, b: int) -> int:\n    return a + b\n"},
            test_files={
                "test_calc.py": (
                    "from calc import add\n\n\ndef test_add() -> None:\n    assert add(2, 2) == 4\n"
                )
            },
            tools=("pytest",),
        ),
        raise_on_failure=False,
    )
    assert false_red.red_reproduced is False
    assert false_red.passed is False


def test_story_4_1a_tier2_isolation_network_fs_memory_and_timeout() -> None:
    """Verify Tier 2 Sandbox isolation jails (`--network=none`, read-only FS, 1024MB, timeout)."""
    runner = ContainerSandboxRunner()
    bimodal = BimodalSandboxAdapter(tier2_runner=runner)

    # 1. Network escape -> exit_code 126
    net_res = bimodal.execute_sync(
        SandboxExecutionRequest(
            tier="TIER_2_CONTAINER",
            entrypoint="tool_run",
            payload={"simulate_network_escape": True},
        )
    )
    assert net_res.passed is False
    assert net_res.exit_code == 126
    assert "ERR_SANDBOX_NETWORK_DISABLED" in net_res.stderr

    # 2. Read-only filesystem escape outside /tmp -> exit_code 126
    fs_res = bimodal.execute_sync(
        SandboxExecutionRequest(
            tier="TIER_2_CONTAINER",
            entrypoint="tool_run",
            payload={"simulate_fs_escape_path": "/var/tmp/orcia_tier2_escape.txt"},
        )
    )
    assert fs_res.passed is False
    assert fs_res.exit_code == 126
    assert "ERR_SANDBOX_FS_READONLY" in fs_res.stderr

    # 3. Forbidden tool outside whitelist -> exit_code 126
    tool_res = bimodal.execute_sync(
        SandboxExecutionRequest(
            tier="TIER_2_CONTAINER",
            entrypoint="tool_run",
            payload={"tool": "curl", "files": {}},
        )
    )
    assert tool_res.passed is False
    assert tool_res.exit_code == 126
    assert "ERR_SANDBOX_TOOL_FORBIDDEN" in tool_res.stderr

    # 4. Empty test suite raises DeterministicGateFailedError when raise_on_failure=True
    from orcia_core.gates.errors import DeterministicGateFailedError
    from orcia_core.gates.sandbox import classify_sandbox_failure

    svc = DeterministicGateService(sandbox_port=bimodal)
    with pytest.raises(DeterministicGateFailedError):
        runner.verify_tdd_red_green(
            TddRemediationCheckInput(
                workspace_id=WORKSPACE_ID,
                run_id=RUN_ID,
                step_key="empty-tests",
                buggy_files={},
                patched_files={},
                test_files={},
            ),
            raise_on_failure=True,
        )

    # 5. Memory limit > 1024 MB -> exit_code 137 -> PolicyDeniedError
    mem_res = bimodal.execute_sync(
        SandboxExecutionRequest(
            tier="TIER_2_CONTAINER",
            entrypoint="tool_run",
            payload={"simulate_memory_alloc_mb": 2048},
            max_memory_mb=1024,
        )
    )
    assert mem_res.exit_code == 137
    assert isinstance(classify_sandbox_failure(mem_res), PolicyDeniedError)

    # 6. Hardware timeout -> exit_code 124 -> UpstreamTimeoutError
    timeout_res = bimodal.execute_sync(
        SandboxExecutionRequest(
            tier="TIER_2_CONTAINER",
            entrypoint="tool_run",
            payload={"simulate_timeout_sleep_ms": 500},
            timeout_ms=100,
        )
    )
    assert timeout_res.exit_code == 124
    assert isinstance(classify_sandbox_failure(timeout_res), UpstreamTimeoutError)
    assert svc.tier2_runner is runner


def test_story_4_1a_five_deployment_roles_and_docling_isolation_and_api() -> None:
    """Verify the 5 operational deployment roles, `Docling` isolation, and REST API endpoints."""
    # 1. Verify apps/worker/pyproject.toml defines `orcia-worker[indexing]` with docling
    worker_toml = tomllib.loads(
        (REPO_ROOT / "apps" / "worker" / "pyproject.toml").read_text(encoding="utf-8")
    )
    opt_deps = worker_toml["project"]["optional-dependencies"]
    assert "indexing" in opt_deps
    assert any("docling" in dep for dep in opt_deps["indexing"])

    # 2. Verify infra/docker/docker-compose.yml declares all 5 operational roles
    compose_data = yaml.safe_load(
        (REPO_ROOT / "infra" / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    )
    services = compose_data["services"]
    for role_name in (
        "api",
        "worker-orchestration",
        "worker-indexing",
        "trigger-dispatcher",
        "sandbox-runner",
    ):
        assert role_name in services, f"Missing service {role_name} in docker-compose.yml"

    # 3. Verify process isolation: `orcia_worker.docling_indexer` is NOT loaded in api/orchestration
    sys.modules.pop("orcia_worker.docling_indexer", None)
    assert verify_role_process_isolation("api") is True
    assert verify_role_process_isolation("worker-orchestration") is True
    assert roles_cli_main(["--role", "worker-orchestration"]) == 0
    assert roles_cli_main(["--role", "sandbox-runner"]) == 0

    roles = list_deployment_role_specs()
    assert len(roles) == 5
    indexing_role = [r for r in roles if r.role == "worker-indexing"][0]
    assert indexing_role.loads_docling is True
    assert "orcia-worker[indexing]" in indexing_role.required_extras

    # 4. Verify REST API endpoints for Story 4.1a
    app = create_app()
    client = TestClient(app)

    roles_res = client.get("/api/v1/gates/sandbox/deployment-roles?persona_key=karim")
    assert roles_res.status_code == 200
    assert len(roles_res.json()["roles"]) == 5

    tdd_api_res = client.post(
        "/api/v1/gates/sandbox/tier2/tdd-verify?persona_key=marc",
        json={
            "workspace_id": WORKSPACE_ID,
            "run_id": RUN_ID,
            "step_key": "step-api-tdd",
            "buggy_files": {"mod.py": "def is_valid() -> bool:\n    return False\n"},
            "patched_files": {"mod.py": "def is_valid() -> bool:\n    return True\n"},
            "test_files": {
                "test_mod.py": (
                    "from mod import is_valid\n\n\ndef test_ok() -> None:\n    assert is_valid()\n"
                )
            },
            "tools": ["pytest", "ruff"],
        },
    )
    assert tdd_api_res.status_code == 200, tdd_api_res.text
    tdd_body = tdd_api_res.json()
    assert tdd_body["passed"] is True
    assert tdd_body["red_reproduced"] is True
    assert tdd_body["green_verified"] is True
    assert "--network=none" in tdd_body["container_cli_args"]
