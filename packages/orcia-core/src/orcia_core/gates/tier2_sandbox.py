"""Tier 2 Container Sandbox Runner & Bimodal Sandbox Adapter (`AD-9`, `P5`, `M8`, `Story 4.1a`).

Implements:
- `ContainerSandboxSpec` & `build_tier2_container_cli_args`: constructs the strict rootless /
  `gVisor runsc` container invocation (`--network=none`, `--read-only`,
  `--tmpfs /tmp:rw,noexec,nosuid,size=256m`, `--memory=1024m`, `--cpus=2.0`, `--pids-limit=64`,
  `--security-opt=no-new-privileges:true`, read-only CAS mount).
- `ContainerSandboxRunner`: executes `TIER_2_CONTAINER` requests out-of-process (`< 60 000 ms`,
  `1 024 MB`) for `pytest`, `ruff`, `mypy`, `tsc`, `vitest` and TDD `Red -> Green` loops (`UJ-12`).
- `BimodalSandboxAdapter`: routes `TIER_1_WASM` (`< 5 000 ms`, `256 MB`) to
  `SubprocessTier1SandboxAdapter` and `TIER_2_CONTAINER` (`< 60 000 ms`, `1 024 MB`) to
  `ContainerSandboxRunner`.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import json
import os
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from orcia_core.gates.sandbox import SubprocessTier1SandboxAdapter, classify_sandbox_failure
from orcia_kernel.ports import (
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxPort,
)

ContainerRuntimeType = Literal["gvisor_runsc", "podman_rootless", "docker_rootless"]


def _resolve_tier2_runner_script() -> pathlib.Path:
    """Resolve the absolute path to `infra/sandbox/tier2_runner.py`."""
    current = pathlib.Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "infra" / "sandbox" / "tier2_runner.py"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not locate infra/sandbox/tier2_runner.py in workspace.")


@dataclass(frozen=True, slots=True)
class ContainerSandboxSpec:
    """Immutable specification of a Tier 2 isolated container execution (`AD-9`, `P5`)."""

    runtime: ContainerRuntimeType = "podman_rootless"
    image: str = "orcia-sandbox-tier2:latest"
    network_mode: str = "none"
    read_only_rootfs: bool = True
    tmpfs_mount: str = "/tmp:rw,noexec,nosuid,size=256m"
    memory_limit: str = "1024m"
    cpus: str = "2.0"
    pids_limit: int = 64
    timeout_ms: int = 60000
    cas_readonly_host_dir: str | None = None


def build_tier2_container_cli_args(spec: ContainerSandboxSpec) -> tuple[str, ...]:
    """Build the exact rootless / `gVisor runsc` CLI command for Tier 2 container isolation."""
    binary = "podman" if spec.runtime == "podman_rootless" else "docker"
    args: list[str] = [
        binary,
        "run",
        "--rm",
        "-i",
        f"--network={spec.network_mode}",
    ]
    if spec.runtime == "gvisor_runsc":
        args.append("--runtime=runsc")
    if spec.read_only_rootfs:
        args.append("--read-only")
    args.extend(
        [
            "--tmpfs",
            spec.tmpfs_mount,
            f"--memory={spec.memory_limit}",
            f"--cpus={spec.cpus}",
            f"--pids-limit={spec.pids_limit}",
            "--security-opt=no-new-privileges:true",
            "--cap-drop=ALL",
        ]
    )
    if spec.cas_readonly_host_dir:
        args.extend(["-v", f"{spec.cas_readonly_host_dir}:/workspace/cas:ro"])
    args.extend([spec.image, "python", "-I", "/app/infra/sandbox/tier2_runner.py"])
    return tuple(args)


@dataclass(frozen=True, slots=True)
class TddRemediationCheckInput:
    """Input for a closed-loop TDD `Red -> Green` verification in Tier 2 Sandbox (`UJ-12`)."""

    workspace_id: str
    run_id: str
    step_key: str
    buggy_files: dict[str, str]
    patched_files: dict[str, str]
    test_files: dict[str, str]
    tools: tuple[str, ...] = ("pytest", "ruff")
    cas_readonly_dir: str | None = None
    timeout_ms: int = 60000
    max_memory_mb: int = 1024


@dataclass(frozen=True, slots=True)
class TddRemediationCheckResult:
    """Result of a closed-loop TDD `Red -> Green` verification in Tier 2 Sandbox (`Story 4.1a`)."""

    passed: bool
    red_reproduced: bool
    red_exit_code: int
    red_stdout: str
    green_verified: bool
    green_tool_runs: tuple[dict[str, Any], ...]
    container_cli_args: tuple[str, ...]
    duration_ms: int
    sandbox_exit_code: int = 0
    sandbox_stderr: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class ContainerSandboxRunner(SandboxPort):
    """Out-of-process Tier 2 Container Sandbox runner (`< 60s`, `1024MB`, `--network=none`)."""

    def __init__(
        self,
        runner_script: pathlib.Path | None = None,
        runtime: ContainerRuntimeType = "podman_rootless",
    ) -> None:
        self._runner_script = runner_script or _resolve_tier2_runner_script()
        self._runtime: ContainerRuntimeType = runtime

    def build_container_spec(
        self, request: SandboxExecutionRequest
    ) -> tuple[ContainerSandboxSpec, tuple[str, ...]]:
        """Return the `ContainerSandboxSpec` and CLI command tuple for `request`."""
        timeout_ms = max(100, min(request.timeout_ms, 60000))
        max_memory_mb = max(64, min(request.max_memory_mb, 1024))
        cas_dir = request.payload.get("cas_readonly_dir")
        spec = ContainerSandboxSpec(
            runtime=self._runtime,
            memory_limit=f"{max_memory_mb}m",
            timeout_ms=timeout_ms,
            cas_readonly_host_dir=str(cas_dir) if cas_dir else None,
        )
        return spec, build_tier2_container_cli_args(spec)

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Execute `request` in the isolated Tier 2 out-of-process sandbox (`< 60 000 ms`)."""
        timeout_ms = max(50, min(request.timeout_ms, 60000))
        max_memory_mb = max(64, min(request.max_memory_mb, 1024))
        timeout_s = timeout_ms / 1000.0

        stdin_bytes = json.dumps(
            {
                "tier": "TIER_2_CONTAINER",
                "entrypoint": request.entrypoint,
                "max_memory_mb": max_memory_mb,
                "timeout_ms": timeout_ms,
                "payload": request.payload,
            },
            sort_keys=True,
        ).encode("utf-8")

        clean_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }

        start_ns = time.monotonic_ns()
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            str(self._runner_script),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=clean_env,
            start_new_session=True,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes),
                timeout=timeout_s,
            )
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
            duration_ms = max(timeout_ms, int((time.monotonic_ns() - start_ns) / 1_000_000))
            return SandboxExecutionResult(
                passed=False,
                exit_code=124,
                stdout="",
                stderr=(
                    f"ERR_SANDBOX_TIMEOUT_EXCEEDED: Tier 2 Container execution exceeded "
                    f"hardware limit of {timeout_ms} ms."
                ),
                duration_ms=duration_ms,
            )

        duration_ms = max(1, int((time.monotonic_ns() - start_ns) / 1_000_000))
        exit_code = int(proc.returncode if proc.returncode is not None else 1)
        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")

        return SandboxExecutionResult(
            passed=(exit_code == 0),
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_ms=duration_ms,
        )

    def execute_sync(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Synchronous helper running `execute(request)` safely from sync or async contexts."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute(request))
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(self.execute(request))).result()

    def verify_tdd_red_green(
        self, check_input: TddRemediationCheckInput, *, raise_on_failure: bool = False
    ) -> TddRemediationCheckResult:
        """Run a closed-loop TDD `Red -> Green` verification in the Tier 2 Sandbox (`UJ-12`)."""
        req = SandboxExecutionRequest(
            tier="TIER_2_CONTAINER",
            entrypoint="tdd_red_green",
            payload={
                "mode": "tdd_red_green",
                "buggy_files": dict(check_input.buggy_files),
                "patched_files": dict(check_input.patched_files),
                "test_files": dict(check_input.test_files),
                "tools": list(check_input.tools),
                "cas_readonly_dir": check_input.cas_readonly_dir,
            },
            timeout_ms=min(check_input.timeout_ms, 60000),
            max_memory_mb=min(check_input.max_memory_mb, 1024),
        )
        _, cli_args = self.build_container_spec(req)
        res = self.execute_sync(req)

        if res.exit_code in (124, 126, 137) and raise_on_failure:
            raise classify_sandbox_failure(res)

        parsed: dict[str, Any] = {}
        if res.stdout.strip():
            with contextlib.suppress(Exception):
                parsed = json.loads(res.stdout)

        result = TddRemediationCheckResult(
            passed=bool(parsed.get("passed", False)) and res.exit_code == 0,
            red_reproduced=bool(parsed.get("red_reproduced", False)),
            red_exit_code=int(parsed.get("red_exit_code", 0)),
            red_stdout=str(parsed.get("red_stdout", "")),
            green_verified=bool(parsed.get("green_verified", False)),
            green_tool_runs=tuple(dict(r) for r in (parsed.get("green_tool_runs") or [])),
            container_cli_args=cli_args,
            duration_ms=res.duration_ms,
            sandbox_exit_code=res.exit_code,
            sandbox_stderr=res.stderr,
        )
        if not result.passed and raise_on_failure:
            raise classify_sandbox_failure(res)
        return result


class BimodalSandboxAdapter(SandboxPort):
    """Bimodal `SandboxPort` routing `TIER_1_WASM` (< 5s) & `TIER_2_CONTAINER` (< 60s)."""

    def __init__(
        self,
        tier1_adapter: SubprocessTier1SandboxAdapter | None = None,
        tier2_runner: ContainerSandboxRunner | None = None,
    ) -> None:
        self.tier1_adapter = tier1_adapter or SubprocessTier1SandboxAdapter()
        self.tier2_runner = tier2_runner or ContainerSandboxRunner()

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        if request.tier == "TIER_2_CONTAINER":
            return await self.tier2_runner.execute(request)
        return await self.tier1_adapter.execute(request)

    def execute_sync(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        if request.tier == "TIER_2_CONTAINER":
            return self.tier2_runner.execute_sync(request)
        return self.tier1_adapter.execute_sync(request)


DeploymentRoleName = Literal[
    "api",
    "worker-orchestration",
    "worker-indexing",
    "trigger-dispatcher",
    "sandbox-runner",
]


@dataclass(frozen=True, slots=True)
class DeploymentRoleSpec:
    """Declarative specification for one of the 5 operational deployment roles (`Story 4.1a`)."""

    role: DeploymentRoleName
    description: str
    entrypoint_command: tuple[str, ...]
    required_extras: tuple[str, ...]
    loads_docling: bool
    forbidden_modules_in_process: tuple[str, ...]
    supported_sandbox_tiers: tuple[str, ...] = ()


CANONICAL_DEPLOYMENT_ROLES: dict[DeploymentRoleName, DeploymentRoleSpec] = {
    "api": DeploymentRoleSpec(
        role="api",
        description="FastAPI HTTP/REST (OpenAPI 3.1) + Server-Sent Events (SSE) API Server",
        entrypoint_command=("uvicorn", "orcia_api.main:app", "--host", "0.0.0.0", "--port", "8000"),
        required_extras=(),
        loads_docling=False,
        forbidden_modules_in_process=("docling", "orcia_worker.docling_indexer"),
    ),
    "worker-orchestration": DeploymentRoleSpec(
        role="worker-orchestration",
        description="DBOS Transact durable workflow execution & transactional Outbox relay",
        entrypoint_command=(
            "python",
            "-m",
            "orcia_worker.roles",
            "--role",
            "worker-orchestration",
        ),
        required_extras=(),
        loads_docling=False,
        forbidden_modules_in_process=("docling", "orcia_worker.docling_indexer"),
    ),
    "worker-indexing": DeploymentRoleSpec(
        role="worker-indexing",
        description="Dramatiq heavy document/PDF/AST indexer isolating Docling 2.91 & tree-sitter",
        entrypoint_command=("dramatiq", "orcia_worker.docling_indexer", "--queues", "indexing"),
        required_extras=("orcia-worker[indexing]",),
        loads_docling=True,
        forbidden_modules_in_process=(),
    ),
    "trigger-dispatcher": DeploymentRoleSpec(
        role="trigger-dispatcher",
        description="Idempotent webhook, log-sink & cron trigger dispatcher",
        entrypoint_command=(
            "python",
            "-m",
            "orcia_worker.roles",
            "--role",
            "trigger-dispatcher",
        ),
        required_extras=(),
        loads_docling=False,
        forbidden_modules_in_process=("docling", "orcia_worker.docling_indexer"),
    ),
    "sandbox-runner": DeploymentRoleSpec(
        role="sandbox-runner",
        description=(
            "Out-of-process bimodal Sandbox service (Tier 1 WASM < 5s & Tier 2 Container < 60s)"
        ),
        entrypoint_command=(
            "python",
            "-m",
            "orcia_worker.roles",
            "--role",
            "sandbox-runner",
        ),
        required_extras=(),
        loads_docling=False,
        forbidden_modules_in_process=("docling", "orcia_worker.docling_indexer"),
        supported_sandbox_tiers=("TIER_1_WASM", "TIER_2_CONTAINER"),
    ),
}


def get_deployment_role_spec(role: DeploymentRoleName) -> DeploymentRoleSpec:
    """Return the `DeploymentRoleSpec` for `role`."""
    if role not in CANONICAL_DEPLOYMENT_ROLES:
        raise ValueError(f"Unknown ORCIA deployment role: {role!r}")
    return CANONICAL_DEPLOYMENT_ROLES[role]


def list_deployment_role_specs() -> list[DeploymentRoleSpec]:
    """Return all 5 canonical deployment role specifications in deterministic order."""
    return [
        CANONICAL_DEPLOYMENT_ROLES["api"],
        CANONICAL_DEPLOYMENT_ROLES["worker-orchestration"],
        CANONICAL_DEPLOYMENT_ROLES["worker-indexing"],
        CANONICAL_DEPLOYMENT_ROLES["trigger-dispatcher"],
        CANONICAL_DEPLOYMENT_ROLES["sandbox-runner"],
    ]


def verify_role_process_isolation(role: DeploymentRoleName) -> bool:
    """Verify that none of the role's forbidden modules are loaded in `sys.modules`."""
    spec = get_deployment_role_spec(role)
    for forbidden in spec.forbidden_modules_in_process:
        if forbidden in sys.modules:
            raise RuntimeError(
                f"Role '{role}' violated process isolation: module '{forbidden}' is loaded!"
            )
    return True
