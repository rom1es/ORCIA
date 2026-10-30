"""Operational Deployment Roles CLI for `apps/worker` (`M9`, `AD-19`, `Story 4.1a`)."""

from __future__ import annotations

import argparse

from orcia_core.gates.tier2_sandbox import (
    CANONICAL_DEPLOYMENT_ROLES,
    DeploymentRoleName,
    DeploymentRoleSpec,
    get_deployment_role_spec,
    list_deployment_role_specs,
    verify_role_process_isolation,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for `python -m orcia_worker.roles --role <role>`."""
    parser = argparse.ArgumentParser(description="ORCIA Deployment Role Runner")
    parser.add_argument(
        "--role",
        required=True,
        choices=list(CANONICAL_DEPLOYMENT_ROLES.keys()),
        help="Operational deployment role to verify/start",
    )
    args = parser.parse_args(argv)
    role_name: DeploymentRoleName = args.role
    verify_role_process_isolation(role_name)
    return 0


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
