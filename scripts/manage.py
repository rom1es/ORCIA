#!/usr/bin/env python3
"""ORCIA Stack Manager (`scripts/manage.py` & `./manage.sh`).

Provides unified `start`, `stop`, `restart`, `status`, and `logs` lifecycle control
across all ORCIA components or per individual component, reading all hosts, ports,
and paths from the root `.env` file via `orcia_core.config`.

Supported targets:
- `all` (default): `infra` + `api` + `worker` + `web`
- `infra`: `postgres` + `redis` + `minio`
- `postgres`: Docker container `orcia-postgres`
- `redis`: Docker container `orcia-redis`
- `minio`: Docker container `orcia-minio`
- `api`: FastAPI (`uvicorn`) background daemon
- `worker`: Dramatiq (`orcia_worker.broker`) background daemon
- `web`: Next.js (`apps/web`) background daemon
"""

from __future__ import annotations

import argparse
import contextlib
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for rel_src in ("packages/orcia-core/src", "apps/api/src", "apps/worker/src"):
    candidate = str(REPO_ROOT / rel_src)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from orcia_core.config import (  # noqa: E402
    get_env,
    get_env_int,
    init_or_rotate_env_secrets,
    load_orcia_env,
    resolve_api_host_and_port,
    resolve_redis_url,
    resolve_web_host_and_port,
)

DOCKER_SERVICES: tuple[str, ...] = ("postgres", "redis", "minio")
PROCESS_SERVICES: tuple[str, ...] = ("api", "worker", "web")
ALL_COMPONENTS: tuple[str, ...] = (*DOCKER_SERVICES, *PROCESS_SERVICES)
VALID_TARGETS: tuple[str, ...] = ("all", "infra", *ALL_COMPONENTS)


@dataclass(frozen=True, slots=True)
class ComponentStatus:
    """Runtime status snapshot for a single ORCIA component."""

    name: str
    kind: str
    running: bool
    detail: str
    endpoint: str


def get_run_dir() -> Path:
    """Resolve and create the runtime PID/log directory (`.orcia-run/`)."""
    rel = get_env("ORCIA_RUN_DIR", ".orcia-run")
    run_dir = REPO_ROOT / rel
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def resolve_targets(target: str) -> list[str]:
    """Expand `all` or `infra` into ordered component names."""
    normalized = target.strip().lower()
    if normalized == "all":
        return list(ALL_COMPONENTS)
    if normalized == "infra":
        return list(DOCKER_SERVICES)
    if normalized in ALL_COMPONENTS:
        return [normalized]
    raise ValueError(f"Unknown component '{target}'. Valid targets: {', '.join(VALID_TARGETS)}")


def is_pid_alive(pid: int) -> bool:
    """Return True if a process with `pid` exists and is not a zombie."""
    if pid <= 0:
        return False
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.is_file():
        try:
            content = proc_stat.read_text(encoding="utf-8")
            state = content.rsplit(")", 1)[-1].split()[0]
            if state == "Z":
                return False
        except OSError:
            pass
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def is_tcp_port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    """Return True if `host:port` accepts TCP connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def read_pid_file(component: str) -> int | None:
    """Read PID from `.orcia-run/<component>.pid` if present and valid."""
    pid_file = get_run_dir() / f"{component}.pid"
    if not pid_file.is_file():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def write_pid_file(component: str, pid: int) -> Path:
    """Write `pid` to `.orcia-run/<component>.pid`."""
    pid_file = get_run_dir() / f"{component}.pid"
    pid_file.write_text(f"{pid}\n", encoding="utf-8")
    return pid_file


def remove_pid_file(component: str) -> None:
    """Remove `.orcia-run/<component>.pid` if it exists."""
    pid_file = get_run_dir() / f"{component}.pid"
    pid_file.unlink(missing_ok=True)


def _docker_compose_base_cmd() -> list[str]:
    compose_rel = get_env("ORCIA_DOCKER_COMPOSE_FILE", "infra/docker/docker-compose.yml")
    env_file = REPO_ROOT / ".env"
    cmd = ["docker", "compose"]
    if env_file.is_file():
        cmd.extend(["--env-file", str(env_file)])
    cmd.extend(["-f", str(REPO_ROOT / compose_rel)])
    return cmd


def _inspect_docker_container(service: str) -> tuple[bool, str]:
    container_name = f"orcia-{service}"
    res = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
            container_name,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return False, "stopped"
    raw = res.stdout.strip()
    parts = raw.split("|", 1)
    state = parts[0] if parts else "unknown"
    health = parts[1] if len(parts) > 1 else "none"
    running = state == "running"
    detail = f"{state} ({health})" if health != "none" else state
    return running, detail


def get_component_status(component: str) -> ComponentStatus:
    """Inspect current status of a Docker or daemon component."""
    if component == "postgres":
        host = get_env("POSTGRES_HOST", "127.0.0.1")
        port = get_env_int("POSTGRES_PORT", 5433)
        running, detail = _inspect_docker_container("postgres")
        return ComponentStatus("postgres", "docker", running, detail, f"{host}:{port}")

    if component == "redis":
        host = get_env("REDIS_HOST", "127.0.0.1")
        port = get_env_int("REDIS_PORT", 6380)
        running, detail = _inspect_docker_container("redis")
        return ComponentStatus("redis", "docker", running, detail, f"{host}:{port}")

    if component == "minio":
        host = get_env("MINIO_HOST", "127.0.0.1")
        api_port = get_env_int("MINIO_API_PORT", 9000)
        console_port = get_env_int("MINIO_CONSOLE_PORT", 9001)
        running, detail = _inspect_docker_container("minio")
        return ComponentStatus(
            "minio",
            "docker",
            running,
            detail,
            f"http://{host}:{api_port} (console :{console_port})",
        )

    if component == "api":
        host, port = resolve_api_host_and_port()
        pid = read_pid_file("api")
        pid_ok = pid is not None and is_pid_alive(pid)
        port_ok = is_tcp_port_open(host, port)
        running = pid_ok or port_ok
        if pid_ok:
            detail = f"running (pid={pid})"
        elif port_ok:
            detail = f"running (external process on :{port})"
        else:
            detail = "stopped"
        return ComponentStatus("api", "process", running, detail, f"http://{host}:{port}")

    if component == "worker":
        redis_url = resolve_redis_url()
        pid = read_pid_file("worker")
        pid_ok = pid is not None and is_pid_alive(pid)
        detail = f"running (pid={pid})" if pid_ok else "stopped"
        return ComponentStatus("worker", "process", pid_ok, detail, redis_url)

    if component == "web":
        host, port = resolve_web_host_and_port()
        pid = read_pid_file("web")
        pid_ok = pid is not None and is_pid_alive(pid)
        port_ok = is_tcp_port_open(host, port)
        running = pid_ok or port_ok
        if pid_ok:
            detail = f"running (pid={pid})"
        elif port_ok:
            detail = f"running (external process on :{port})"
        else:
            detail = "stopped"
        return ComponentStatus("web", "process", running, detail, f"http://{host}:{port}")

    raise ValueError(f"Unknown component: {component}")


def _build_process_env() -> dict[str, str]:
    env = os.environ.copy()
    py_paths = [
        str(REPO_ROOT / "packages" / "orcia-core" / "src"),
        str(REPO_ROOT / "apps" / "api" / "src"),
        str(REPO_ROOT / "apps" / "worker" / "src"),
    ]
    existing = env.get("PYTHONPATH", "")
    if existing:
        py_paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(py_paths)
    return env


def start_component(component: str) -> bool:
    """Start a single component if not already running."""
    status = get_component_status(component)
    if status.running:
        print(f"✔ [{component}] déjà démarré ({status.detail}) -> {status.endpoint}")
        return True

    if component in DOCKER_SERVICES:
        print(f"▶ Démarrage du conteneur Docker [{component}]...")
        cmd = [*_docker_compose_base_cmd(), "up", "-d", "--wait", component]
        res = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
        updated = get_component_status(component)
        if res.returncode == 0 and updated.running:
            print(f"✔ [{component}] démarré ({updated.detail}) -> {updated.endpoint}")
            return True
        print(f"✖ Échec du démarrage de [{component}] (code={res.returncode})")
        return False

    run_dir = get_run_dir()
    log_path = run_dir / f"{component}.log"
    env = _build_process_env()

    if component == "api":
        host, port = resolve_api_host_and_port()
        cmd = [
            str(REPO_ROOT / ".venv" / "bin" / "uvicorn"),
            "orcia_api.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ]
        cwd = REPO_ROOT
        wait_host_port: tuple[str, int] | None = (host, port)
    elif component == "worker":
        env["ORCIA_WORKER_STUB_BROKER"] = "0"
        env["REDIS_URL"] = resolve_redis_url()
        cmd = [
            str(REPO_ROOT / ".venv" / "bin" / "dramatiq"),
            "orcia_worker.broker",
            "--processes",
            "1",
            "--threads",
            "2",
        ]
        cwd = REPO_ROOT
        wait_host_port = None
    elif component == "web":
        host, port = resolve_web_host_and_port()
        cmd = ["node", "scripts/run-next.mjs", "dev"]
        cwd = REPO_ROOT / "apps" / "web"
        wait_host_port = (host, port)
    else:  # pragma: no cover
        raise ValueError(f"Unsupported process component: {component}")

    print(f"▶ Démarrage de [{component}] (logs: {log_path.relative_to(REPO_ROOT)})...")
    with log_path.open("ab") as log_file:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    write_pid_file(component, proc.pid)

    if wait_host_port is not None:
        w_host, w_port = wait_host_port
        for _ in range(40):
            if not is_pid_alive(proc.pid):
                break
            if is_tcp_port_open(w_host, w_port):
                break
            time.sleep(0.25)
    else:
        time.sleep(0.6)

    updated = get_component_status(component)
    if updated.running:
        print(f"✔ [{component}] démarré ({updated.detail}) -> {updated.endpoint}")
        return True

    remove_pid_file(component)
    print(
        f"✖ [{component}] s'est arrêté prématurément. Consultez {log_path.relative_to(REPO_ROOT)}"
    )
    return False


def stop_component(component: str) -> bool:
    """Stop a single component gracefully."""
    if component in DOCKER_SERVICES:
        status = get_component_status(component)
        if not status.running:
            print(f"• [{component}] déjà arrêté")
            return True
        print(f"■ Arrêt du conteneur Docker [{component}]...")
        cmd = [*_docker_compose_base_cmd(), "stop", component]
        res = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
        if res.returncode == 0:
            print(f"✔ [{component}] arrêté")
            return True
        print(f"✖ Échec de l'arrêt de [{component}]")
        return False

    pid = read_pid_file(component)
    if pid is None or not is_pid_alive(pid):
        remove_pid_file(component)
        print(f"• [{component}] déjà arrêté")
        return True

    print(f"■ Arrêt de [{component}] (pid={pid})...")
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except OSError:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGTERM)

    for _ in range(25):
        if not is_pid_alive(pid):
            break
        time.sleep(0.2)

    if is_pid_alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except OSError:
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGKILL)

    remove_pid_file(component)
    print(f"✔ [{component}] arrêté")
    return True


def print_status_table(components: list[str]) -> int:
    """Print formatted status table for all requested components."""
    print(f"{'COMPOSANT':<12} {'TYPE':<9} {'STATUT':<10} {'DÉTAIL':<28} {'ENDPOINT / CIBLE'}")
    print("-" * 88)
    for comp in components:
        st = get_component_status(comp)
        badge = "RUNNING" if st.running else "STOPPED"
        print(f"{st.name:<12} {st.kind:<9} {badge:<10} {st.detail:<28} {st.endpoint}")
    return 0


def show_component_logs(components: list[str], lines: int = 40) -> int:
    """Display the last `lines` of logs for the requested components."""
    run_dir = get_run_dir()
    for comp in components:
        print(f"\n=== Logs [{comp}] (dernières {lines} lignes) ===")
        if comp in DOCKER_SERVICES:
            subprocess.run(
                ["docker", "logs", "--tail", str(lines), f"orcia-{comp}"],
                check=False,
            )
        else:
            log_file = run_dir / f"{comp}.log"
            if not log_file.is_file():
                print(f"(Aucun fichier de log : {log_file.relative_to(REPO_ROOT)})")
                continue
            all_lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in all_lines[-lines:]:
                print(line)
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser for `manage.py`."""
    parser = argparse.ArgumentParser(
        prog="manage",
        description=(
            "Gestionnaire unifié ORCIA : start | stop | restart | status | logs | init-secrets "
            "pour toute la stack (all) ou par composant."
        ),
    )
    parser.add_argument(
        "action",
        choices=("start", "stop", "restart", "status", "logs", "init-secrets"),
        help="Action à exécuter sur la cible.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=VALID_TARGETS,
        help="Composant cible (défaut: all).",
    )
    parser.add_argument(
        "--lines",
        "-n",
        type=int,
        default=40,
        help="Nombre de lignes à afficher pour l'action 'logs' (défaut: 40).",
    )
    parser.add_argument(
        "--rotate",
        action="store_true",
        default=False,
        help="Forcer la rotation des secrets applicatifs dans .env (pour 'init-secrets').",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for `scripts/manage.py`."""
    load_orcia_env()
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.action == "init-secrets":
        updated = init_or_rotate_env_secrets(force_rotate=bool(args.rotate))
        for key, was_rotated in updated.items():
            state = (
                "généré / régénéré (256 bits, chmod 600)" if was_rotated else "déjà fort (conservé)"
            )
            print(f"🔐 {key}: {state}")
        return 0

    components = resolve_targets(args.target)

    if args.action == "status":
        return print_status_table(components)

    if args.action == "logs":
        return show_component_logs(components, lines=max(1, int(args.lines)))

    if args.action == "start":
        ok = all(start_component(c) for c in components)
        print()
        print_status_table(components)
        return 0 if ok else 1

    if args.action == "stop":
        # Stop application processes before Docker infrastructure
        stop_order = list(reversed(components))
        ok = all(stop_component(c) for c in stop_order)
        print()
        print_status_table(components)
        return 0 if ok else 1

    if args.action == "restart":
        stop_order = list(reversed(components))
        for c in stop_order:
            stop_component(c)
        ok = all(start_component(c) for c in components)
        print()
        print_status_table(components)
        return 0 if ok else 1

    return 1  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
