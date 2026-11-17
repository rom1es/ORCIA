"""Operational Deployment Roles CLI for `apps/worker` (`M9`, `AD-19`, `Story 4.1a`, `7.0c`)."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import signal

from orcia_core.gates.tier2_sandbox import (
    CANONICAL_DEPLOYMENT_ROLES,
    DeploymentRoleName,
    DeploymentRoleSpec,
    get_deployment_role_spec,
    list_deployment_role_specs,
    verify_role_process_isolation,
)
from orcia_core.observability import configure_tracing, instrument_runtime
from orcia_core.observability.logging import configure_logging, get_logger
from orcia_worker.sandbox_daemon import serve_sandbox_daemon
from orcia_worker.trigger_dispatcher_daemon import serve_trigger_dispatcher_daemon

logger = get_logger("orcia.worker.roles")


async def _serve_signal_loop(role_name: DeploymentRoleName, *, once: bool = False) -> int:
    """Run an interruptible worker role service loop until `SIGINT`/`SIGTERM` (or `once`)."""
    logger.info("worker.role.started", role=role_name, once=once)
    if once:
        logger.info("worker.role.stopped", role=role_name, reason="once")
        return 0

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()
    logger.info("worker.role.stopped", role=role_name, reason="signal")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for `python -m orcia_worker.roles --role <role> [--serve] [--once]`."""
    parser = argparse.ArgumentParser(description="ORCIA Deployment Role Runner")
    parser.add_argument(
        "--role",
        required=True,
        choices=list(CANONICAL_DEPLOYMENT_ROLES.keys()),
        help="Operational deployment role to verify/start",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run the operational runtime loop for the selected deployment role.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Perform a single startup/readiness cycle and exit cleanly (used in tests).",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Optional bind host override (used by `sandbox-runner`).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Optional bind port override (used by `sandbox-runner`).",
    )
    args = parser.parse_args(argv)
    role_name: DeploymentRoleName = args.role
    service_name = os.environ.get("ORCIA_WORKER_ROLE", role_name)
    configure_logging(service=service_name)
    configure_tracing(service_name=service_name)
    instrument_runtime(instrument_httpx=True)
    verify_role_process_isolation(role_name)

    if not args.serve:
        return 0

    if role_name == "sandbox-runner":
        return asyncio.run(
            serve_sandbox_daemon(
                host=args.host,
                port=args.port,
                once=bool(args.once),
            )
        )

    if role_name == "trigger-dispatcher":
        return asyncio.run(serve_trigger_dispatcher_daemon(once=bool(args.once)))

    return asyncio.run(_serve_signal_loop(role_name, once=bool(args.once)))


__all__ = [
    "CANONICAL_DEPLOYMENT_ROLES",
    "DeploymentRoleName",
    "DeploymentRoleSpec",
    "get_deployment_role_spec",
    "list_deployment_role_specs",
    "main",
    "verify_role_process_isolation",
]


if __name__ == "__main__":
    raise SystemExit(main())
