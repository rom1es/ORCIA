"""Remise à zéro Jour 0 de la base E2E éphémère (TEST-01).

Délègue à `infra/scripts/maintenance/09_reset_db_first_boot.py --apply`, mais uniquement après
vérification que la base cible est la base E2E isolée (jamais la base de développement).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e2e_stack_config import (  # noqa: E402
    REPO_ROOT,
    build_api_env,
    is_isolated_e2e_database_url,
    process_env,
    read_state,
)

RESET_SCRIPT = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"


def main() -> int:
    state = read_state()
    if not is_isolated_e2e_database_url(state["database_url"]):
        print("[e2e-reset] REFUS : base non isolée.", file=sys.stderr)
        return 2
    env = build_api_env(
        base_env=process_env(),
        database_url=state["database_url"],
        redis_url=state["redis_url"],
        api_port=int(state["api_port"]),
    )
    return subprocess.run(
        [sys.executable, str(RESET_SCRIPT), "--apply"], cwd=REPO_ROOT, env=env, check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
