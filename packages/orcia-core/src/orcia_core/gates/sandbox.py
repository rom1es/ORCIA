"""Out-of-process Tier 1 Sandbox Adapter implementing `SandboxPort` (`AD-9`, `Story 4.1`).

Delegates execution out-of-process to `infra/sandbox/tier1_runner.py` with:
- Zero network access (`exit_code = 126` -> `PolicyDeniedError`)
- Read-only filesystem outside 64 MB ephemeral `/tmp` (`exit_code = 126` -> `PolicyDeniedError`)
- Memory ceiling `256 MB` (`exit_code = 137` -> `PolicyDeniedError`)
- Hardware wall-clock timeout `5 000 ms` (`exit_code = 124` -> `UpstreamTimeoutError`)
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

from orcia_core.gates.errors import (
    DeterministicGateFailedError,
    OrciaDomainError,
    PolicyDeniedError,
    UpstreamTimeoutError,
)
from orcia_kernel.ports import (
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxPort,
)


def _resolve_tier1_runner_script() -> pathlib.Path:
    """Resolve the absolute path to `infra/sandbox/tier1_runner.py`."""
    current = pathlib.Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "infra" / "sandbox" / "tier1_runner.py"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not locate infra/sandbox/tier1_runner.py in workspace.")


def classify_sandbox_failure(result: SandboxExecutionResult) -> OrciaDomainError:
    """Classify a failed `SandboxExecutionResult` into `orcia_kernel.errors` taxonomy (`Story 4.1`).

    - Timeout (`exit_code == 124`) -> `UpstreamTimeoutError` (retryable by `ConnectorInvoker`)
    - Isolation violation (`exit_code in (126, 137)`) -> `PolicyDeniedError` (non-retryable)
    - Functional validation failure -> `DeterministicGateFailedError` (non-retryable)
    """
    stderr_summary = (
        result.stderr.strip() or result.stdout.strip() or f"exit_code={result.exit_code}"
    )
    if result.exit_code == 124:
        return UpstreamTimeoutError(
            retry_after_s=0.05,
            detail_override=(
                f"Dépassement du délai matériel de la Sandbox ({result.duration_ms} ms): "
                f"{stderr_summary}"
            ),
        )
    if result.exit_code in (126, 137):
        return PolicyDeniedError(
            detail_override=(
                f"Violation d'isolation de la Sandbox Palier 1 (code {result.exit_code}): "
                f"{stderr_summary}"
            )
        )
    return DeterministicGateFailedError(
        detail_override=(
            f"Échec de validation dans la Sandbox Palier 1 (code {result.exit_code}): "
            f"{stderr_summary}"
        )
    )


class SubprocessTier1SandboxAdapter(SandboxPort):
    """Out-of-process Tier 1 Sandbox runner (`infra/sandbox/tier1_runner.py`, `AD-9`, `Q3: 3A`)."""

    def __init__(self, runner_script: pathlib.Path | None = None) -> None:
        self._runner_script = runner_script or _resolve_tier1_runner_script()

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Execute `request` in an isolated child process with hard timeout and resource caps."""
        timeout_ms = max(50, min(request.timeout_ms, 5000))
        max_memory_mb = max(16, min(request.max_memory_mb, 256))
        timeout_s = timeout_ms / 1000.0

        stdin_bytes = json.dumps(
            {
                "tier": str(request.tier),
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
                    f"ERR_SANDBOX_TIMEOUT_EXCEEDED: Execution exceeded hardware limit of "
                    f"{timeout_ms} ms."
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
        """Synchronous helper ready to call whether an event loop is already running or not."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute(request))
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(self.execute(request))).result()
