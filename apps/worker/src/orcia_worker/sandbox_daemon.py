"""Internal non-privileged HTTP sidecar daemon for `sandbox-runner` (`AD-9`, `Story 7.0c`)."""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import os
import pathlib
import signal
import sys
import tempfile
import time
from http import HTTPStatus
from typing import Any

from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.worker.sandbox_daemon")
MAX_REQUEST_BODY_BYTES = 1024 * 1024


def resolve_tier1_runner_script() -> pathlib.Path:
    """Resolve `infra/sandbox/tier1_runner.py` from workspace or container `/app`."""
    for parent in pathlib.Path(__file__).resolve().parents:
        candidate = parent / "infra" / "sandbox" / "tier1_runner.py"
        if candidate.is_file():
            return candidate
    app_candidate = pathlib.Path("/app/infra/sandbox/tier1_runner.py")
    if app_candidate.is_file():
        return app_candidate
    raise FileNotFoundError("Could not locate infra/sandbox/tier1_runner.py.")


def resolve_sandbox_tmp_dir(explicit_tmp_dir: str | None = None) -> pathlib.Path:
    """Resolve scratch directory confined under `/tmp` (or explicit override)."""
    raw = (
        explicit_tmp_dir
        if explicit_tmp_dir is not None
        else os.environ.get("ORCIA_SANDBOX_TMP_DIR", "/tmp")
    )
    candidate = pathlib.Path(raw or "/tmp").resolve()
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


async def execute_tier1_isolated(
    request_data: dict[str, Any],
    *,
    tmp_dir: pathlib.Path,
    runner_script: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Execute Tier 1 runner in `python -I` using an ephemeral dir under `tmp_dir`."""
    script = runner_script or resolve_tier1_runner_script()
    timeout_ms = max(50, min(int(request_data.get("timeout_ms", 5000)), 5000))
    max_memory_mb = max(16, min(int(request_data.get("max_memory_mb", 256)), 256))
    entrypoint = str(request_data.get("entrypoint", "deterministic_checks"))
    stdin_bytes = json.dumps(
        {
            "tier": "TIER_1_WASM",
            "entrypoint": entrypoint,
            "max_memory_mb": max_memory_mb,
            "timeout_ms": timeout_ms,
            "payload": dict(request_data.get("payload") or {}),
        },
        sort_keys=True,
    ).encode("utf-8")

    start_ns = time.monotonic_ns()
    with tempfile.TemporaryDirectory(prefix="orcia-sandbox-t1-", dir=str(tmp_dir)) as scratch:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            **{k: scratch for k in ("HOME", "TMPDIR", "TMP", "TEMP")},
        }
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            str(script),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=scratch,
            start_new_session=True,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes), timeout=timeout_ms / 1000.0
            )
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
            elapsed = max(timeout_ms, int((time.monotonic_ns() - start_ns) / 1_000_000))
            return {
                "passed": False,
                "exit_code": 124,
                "duration_ms": elapsed,
                "entrypoint": entrypoint,
                "result": None,
                "stderr": f"ERR_SANDBOX_TIMEOUT_EXCEEDED: exceeded {timeout_ms} ms.",
            }

    elapsed = max(1, int((time.monotonic_ns() - start_ns) / 1_000_000))
    exit_code = int(proc.returncode if proc.returncode is not None else 1)
    stdout_text = stdout_b.decode("utf-8", errors="replace")
    parsed_result: dict[str, Any] | None = None
    if stdout_text.strip():
        with contextlib.suppress(ValueError):
            decoded = json.loads(stdout_text)
            if isinstance(decoded, dict):
                parsed_result = decoded
    return {
        "passed": exit_code == 0,
        "exit_code": exit_code,
        "duration_ms": elapsed,
        "entrypoint": entrypoint,
        "result": parsed_result,
        "stderr": stderr_b.decode("utf-8", errors="replace"),
    }


def _http_json(status: HTTPStatus, payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    head = (
        f"HTTP/1.1 {status.value} {status.phrase}\r\n"
        f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii")
    return head + body


class SandboxDaemonServer:
    """Asyncio HTTP/1.1 sidecar server for `sandbox-runner` (zero Podman-in-Pod)."""

    def __init__(
        self,
        *,
        host: str = "0.0.0.0",
        port: int = 8096,
        tmp_dir: str | None = None,
        internal_token: str | None = None,
        runner_script: pathlib.Path | None = None,
    ) -> None:
        self.host, self.requested_port = host, port
        self.tmp_dir = resolve_sandbox_tmp_dir(tmp_dir)
        tok = (
            internal_token
            if internal_token is not None
            else os.environ.get("ORCIA_SANDBOX_INTERNAL_TOKEN", "")
        )
        self.internal_token = tok.strip()
        env_name = os.environ.get("ORCIA_ENV", "local").strip().lower() or "local"
        if not self.internal_token and env_name not in ("local", "test"):
            raise ValueError(
                "ORCIA_SANDBOX_INTERNAL_TOKEN must be configured outside local/test environments."
            )
        self.runner_script = runner_script
        self._server: asyncio.Server | None = None

    @property
    def port(self) -> int:
        if self._server is None or not self._server.sockets:
            return self.requested_port
        return int(self._server.sockets[0].getsockname()[1])

    async def start(self) -> None:
        """Bind TCP listener and start serving requests."""
        self._server = await asyncio.start_server(
            self._handle_client, host=self.host, port=self.requested_port
        )
        logger.info("sandbox_daemon.started", host=self.host, port=self.port)

    async def close(self) -> None:
        """Gracefully close listener."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("sandbox_daemon.stopped")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        resp = _http_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error_code": "ERR_SANDBOX_INTERNAL"})
        try:
            resp = await self._dispatch_http(reader)
        except Exception as exc:
            logger.warning("sandbox_daemon.request_error", error_type=type(exc).__name__)
        finally:
            try:
                writer.write(resp)
                await writer.drain()
            except Exception as exc:
                logger.warning("sandbox_daemon.write_failed", error_type=type(exc).__name__)
            finally:
                writer.close()
                with contextlib.suppress(Exception):
                    await writer.wait_closed()

    async def _dispatch_http(self, reader: asyncio.StreamReader) -> bytes:
        raw_head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5.0)
        lines = raw_head.decode("latin-1").split("\r\n")
        parts = lines[0].split(" ")
        if len(parts) < 2:
            return _http_json(HTTPStatus.BAD_REQUEST, {"error_code": "ERR_BAD_REQUEST"})
        method, path = parts[0].upper(), parts[1].split("?", 1)[0]
        headers = {
            k.strip().lower(): v.strip()
            for ln in lines[1:]
            if ":" in ln
            for k, v in [ln.split(":", 1)]
        }
        if method == "GET" and path == "/health":
            return _http_json(HTTPStatus.OK, {"status": "ok", "role": "sandbox-runner"})
        if method != "POST" or path != "/execute-tier1":
            return _http_json(HTTPStatus.NOT_FOUND, {"error_code": "ERR_NOT_FOUND"})
        if self.internal_token:
            tok = headers.get("x-orcia-sandbox-token", "")
            if not tok:
                return _http_json(HTTPStatus.UNAUTHORIZED, {"error_code": "ERR_AUTH_REQUIRED"})
            if not hmac.compare_digest(tok, self.internal_token):
                return _http_json(HTTPStatus.FORBIDDEN, {"error_code": "ERR_AUTH_INVALID"})
        try:
            content_len = int(headers.get("content-length", "0") or "0")
        except ValueError:
            return _http_json(HTTPStatus.BAD_REQUEST, {"error_code": "ERR_BAD_CONTENT_LENGTH"})
        if content_len < 0 or content_len > MAX_REQUEST_BODY_BYTES:
            return _http_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error_code": "ERR_TOO_LARGE"})
        raw_body = (
            await asyncio.wait_for(reader.readexactly(content_len), timeout=5.0)
            if content_len
            else b"{}"
        )
        try:
            parsed = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return _http_json(HTTPStatus.BAD_REQUEST, {"error_code": "ERR_INVALID_JSON"})
        if not isinstance(parsed, dict):
            return _http_json(HTTPStatus.BAD_REQUEST, {"error_code": "ERR_INVALID_JSON"})
        out = await execute_tier1_isolated(
            parsed, tmp_dir=self.tmp_dir, runner_script=self.runner_script
        )
        return _http_json(HTTPStatus.OK, out)


async def serve_sandbox_daemon(
    *,
    host: str | None = None,
    port: int | None = None,
    tmp_dir: str | None = None,
    internal_token: str | None = None,
    once: bool = False,
) -> int:
    """Run `SandboxDaemonServer` until `SIGINT`/`SIGTERM` (or exit immediately if `once=True`)."""
    server = SandboxDaemonServer(
        host=host or os.environ.get("ORCIA_SANDBOX_HOST", "0.0.0.0"),
        port=port if port is not None else int(os.environ.get("ORCIA_SANDBOX_PORT", "8096")),
        tmp_dir=tmp_dir,
        internal_token=internal_token,
    )
    await server.start()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)
    try:
        if not once:
            await stop_event.wait()
        return 0
    finally:
        await server.close()
