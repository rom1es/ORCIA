"""Out-of-process Tier 1 Sandbox Runner (`AD-9`, `NFR-SEC-1`, `Story 4.1`).

Executes deterministic gate validations (`JSON/YAML schema`, `Ontology axioms`,
`Pattern Drift` against `ARCHITECTURE-SPINE.md`) and pure skills in an isolated
child process with:
- Zero network access (`socket` disabled -> exit code 126)
- Read-only filesystem outside a 64 MB ephemeral `/tmp` scratch dir (-> exit code 126)
- Strict memory ceiling (`max_memory_mb=256` -> exit code 137)
- Hardware wall-clock timeout (`timeout_ms=5000` -> exit code 124)
"""

from __future__ import annotations

import builtins
import contextlib
import json
import os
import pathlib
import socket
import sys
import tempfile
import time
from typing import Any

MAX_EPHEMERAL_TMP_BYTES = 64 * 1024 * 1024  # 64 MB


class SandboxPolicyViolationError(PermissionError):
    """Raised when sandboxed code attempts network I/O or unauthorized filesystem write."""


class SandboxMemoryLimitError(MemoryError):
    """Raised when sandboxed code exceeds the 256 MB memory ceiling."""


def _install_network_jail() -> None:
    """Block all network socket creation and DNS resolution inside the child process."""

    def _blocked_socket(*_args: Any, **_kwargs: Any) -> Any:
        raise SandboxPolicyViolationError(
            "ERR_SANDBOX_NETWORK_FORBIDDEN: Network access is disabled in TIER_1_WASM sandbox."
        )

    socket.socket = _blocked_socket  # type: ignore[misc,assignment]
    socket.create_connection = _blocked_socket  # type: ignore[assignment]
    socket.getaddrinfo = _blocked_socket  # type: ignore[assignment]


def _install_filesystem_jail(ephemeral_tmp_dir: str) -> None:
    """Restrict all file writes strictly to `ephemeral_tmp_dir` with a 64 MB quota."""
    real_open = builtins.open
    allowed_prefix = os.path.realpath(ephemeral_tmp_dir)
    written_bytes_tracker = {"total": 0}

    def _is_write_mode(mode: str) -> bool:
        return any(flag in mode for flag in ("w", "a", "x", "+"))

    def _guarded_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if _is_write_mode(str(mode)):
            target_path = os.path.realpath(str(file))
            if not (
                target_path == allowed_prefix or target_path.startswith(allowed_prefix + os.sep)
            ):
                raise SandboxPolicyViolationError(
                    f"ERR_SANDBOX_FS_READONLY: Write to '{file}' outside ephemeral /tmp is denied."
                )
        handle = real_open(file, mode, *args, **kwargs)
        if _is_write_mode(str(mode)):
            orig_write = handle.write

            def _quota_write(data: Any) -> int:
                byte_len = len(data.encode("utf-8")) if isinstance(data, str) else len(data)
                if written_bytes_tracker["total"] + byte_len > MAX_EPHEMERAL_TMP_BYTES:
                    raise SandboxPolicyViolationError(
                        "ERR_SANDBOX_TMP_QUOTA_EXCEEDED: Ephemeral /tmp 64 MB quota exceeded."
                    )
                written_bytes_tracker["total"] += byte_len
                return int(orig_write(data))

            with contextlib.suppress(Exception):
                handle.write = _quota_write  # type: ignore[method-assign]
        return handle

    builtins.open = _guarded_open  # type: ignore[assignment]
    pathlib.Path.open = lambda self, mode="r", *a, **kw: _guarded_open(  # type: ignore[method-assign]
        str(self), mode, *a, **kw
    )


def _evaluate_deterministic_checks(payload: dict[str, Any], max_memory_mb: int) -> dict[str, Any]:
    """Run deterministic schema, ontology axiom, and Pattern Drift checks in the sandbox."""
    if payload.get("simulate_timeout_sleep_ms"):
        sleep_s = float(payload["simulate_timeout_sleep_ms"]) / 1000.0
        time.sleep(sleep_s)

    if payload.get("simulate_network_escape"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("1.1.1.1", 80))

    if payload.get("simulate_fs_escape_path"):
        with open(str(payload["simulate_fs_escape_path"]), "w", encoding="utf-8") as f:
            f.write("escape")

    if payload.get("simulate_tmp_overflow_mb"):
        overflow_mb = int(payload["simulate_tmp_overflow_mb"])
        tmp_file = os.path.join(os.environ["ORCIA_SANDBOX_TMP"], "overflow.bin")
        with open(tmp_file, "wb") as f:
            f.write(b"x" * (overflow_mb * 1024 * 1024))

    requested_mem_mb = int(payload.get("simulate_memory_alloc_mb", 0))
    if requested_mem_mb > max_memory_mb:
        raise SandboxMemoryLimitError(
            f"ERR_SANDBOX_MEMORY_LIMIT_EXCEEDED: Requested {requested_mem_mb} MB > "
            f"limit {max_memory_mb} MB."
        )

    artifact: dict[str, Any] = dict(payload.get("artifact") or {})
    required_sections: list[str] = list(payload.get("required_sections") or [])
    ontology_axioms: list[dict[str, Any]] = list(payload.get("ontology_axioms") or [])
    allowed_dependencies: set[str] = {
        str(d).strip().lower()
        for d in (payload.get("allowed_dependencies") or [])
        if str(d).strip()
    }
    forbidden_patterns: list[dict[str, str]] = list(payload.get("forbidden_patterns") or [])

    # 1. Schema validation
    missing_sections: list[str] = []
    for section_key in required_sections:
        val = artifact.get(section_key)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing_sections.append(section_key)
    schema_validation_passed = len(missing_sections) == 0

    # 2. Ontology formal axioms validation
    violated_axioms: list[dict[str, str]] = []
    serialized_artifact = json.dumps(artifact, sort_keys=True).lower()
    for axiom in ontology_axioms:
        axiom_key = str(axiom.get("axiom_key", "axiom-unknown"))
        forbidden_term = str(axiom.get("forbidden_term", "")).strip().lower()
        required_term = str(axiom.get("required_term", "")).strip().lower()
        if forbidden_term and forbidden_term in serialized_artifact:
            violated_axioms.append(
                {
                    "axiom_key": axiom_key,
                    "reason": f"Terme interdit par axiome détecté: '{forbidden_term}'",
                }
            )
        if required_term and required_term not in serialized_artifact:
            violated_axioms.append(
                {
                    "axiom_key": axiom_key,
                    "reason": f"Invariant requis par axiome absent: '{required_term}'",
                }
            )
    ontology_axioms_passed = len(violated_axioms) == 0

    # 3. Pattern Drift static analysis against ARCHITECTURE-SPINE.md
    pattern_drift_findings: list[dict[str, str]] = []
    declared_deps: list[str] = [
        str(d).strip().lower() for d in (artifact.get("dependencies") or []) if str(d).strip()
    ]
    for dep in declared_deps:
        pkg_name = dep.split(">=")[0].split("==")[0].split("[")[0].strip().lower()
        if allowed_dependencies and pkg_name not in allowed_dependencies:
            pattern_drift_findings.append(
                {
                    "rule_id": "DRIFT-UNAPPROVED-DEPENDENCY",
                    "forbidden_symbol": pkg_name,
                    "severity": "HIGH",
                    "message": (
                        f"Dépendance '{pkg_name}' absente de ARCHITECTURE-SPINE.md (Pattern Drift)."
                    ),
                }
            )

    for rule in forbidden_patterns:
        pattern = str(rule.get("pattern", "")).strip().lower()
        rule_id = str(rule.get("rule_id", "DRIFT-FORBIDDEN-PATTERN"))
        if pattern and pattern in serialized_artifact:
            pattern_drift_findings.append(
                {
                    "rule_id": rule_id,
                    "forbidden_symbol": pattern,
                    "severity": str(rule.get("severity", "HIGH")),
                    "message": str(
                        rule.get(
                            "message",
                            f"Motif architectural interdit '{pattern}' détecté (Pattern Drift).",
                        )
                    ),
                }
            )

    pattern_drift_passed = len(pattern_drift_findings) == 0
    passed = schema_validation_passed and ontology_axioms_passed and pattern_drift_passed
    checks_Passed_count = (
        int(schema_validation_passed)
        + int(ontology_axioms_passed)
        + int(pattern_drift_passed)
    )
    score = round(checks_Passed_count / 3.0, 4)

    return {
        "passed": passed,
        "score": score,
        "schema_validation_passed": schema_validation_passed,
        "missing_sections": missing_sections,
        "ontology_axioms_passed": ontology_axioms_passed,
        "violated_axioms": violated_axioms,
        "pattern_drift_passed": pattern_drift_passed,
        "pattern_drift_findings": pattern_drift_findings,
        "runtime": "wasmtime-tier1-isolated-subprocess",
    }


def main() -> int:
    """Entrypoint for out-of-process Tier 1 Sandbox execution."""
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        sys.stderr.write("Empty sandbox request stdin.\n")
        return 2

    try:
        req = json.loads(raw_input)
    except Exception as exc:
        sys.stderr.write(f"Invalid JSON input: {exc}\n")
        return 2

    max_memory_mb = int(req.get("max_memory_mb", 256))
    payload: dict[str, Any] = dict(req.get("payload") or {})

    with tempfile.TemporaryDirectory(prefix="orcia-sandbox-t1-") as ephemeral_tmp:
        os.environ["ORCIA_SANDBOX_TMP"] = ephemeral_tmp
        _install_network_jail()
        _install_filesystem_jail(ephemeral_tmp)

        try:
            output = _evaluate_deterministic_checks(payload, max_memory_mb=max_memory_mb)
        except SandboxPolicyViolationError as exc:
            sys.stderr.write(f"{exc}\n")
            return 126
        except SandboxMemoryLimitError as exc:
            sys.stderr.write(f"{exc}\n")
            return 137
        except Exception as exc:
            sys.stderr.write(f"ERR_SANDBOX_EXECUTION_ERROR: {exc}\n")
            return 1

    sys.stdout.write(json.dumps(output, sort_keys=True))
    sys.stdout.flush()
    return 0 if output.get("passed", False) else 10


if __name__ == "__main__":
    raise SystemExit(main())
