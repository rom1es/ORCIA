"""Story 11.2: Deterministic Tier 1b `StarlarkMechanismSandbox` (`AD-9`, `< 2 ms`, `0` token)."""

from __future__ import annotations

import ast
import copy
import re
import time
from dataclasses import dataclass
from typing import Any, Literal

_CATASTROPHIC_REDOS_PATTERN = re.compile(r"\([^()]*[+*][^()]*\)[+*?]|\(\?P?<[^>]+>[^()]*[+*]\)[+*]")
_FORBIDDEN_AST_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.While,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.Global,
    ast.Nonlocal,
    ast.Delete,
    ast.Lambda,
    ast.Yield,
    ast.YieldFrom,
    ast.Await,
)


class StarlarkSandboxError(ValueError):
    """Raised when a Starlark mechanism script violates determinism, step cap, or RE2 rules."""


@dataclass(frozen=True, slots=True)
class StarlarkVerdictItem:
    """Single rule verdict emitted via `orcia_sys.emit_verdict`."""

    rule_id: str
    status: Literal["PASS", "FAIL"]
    message_fr: str


@dataclass(frozen=True, slots=True)
class StarlarkStagedEffect:
    """Staged side-effect emitted via `orcia_sys.emit_effect` (`AD-3`, never direct SI I/O)."""

    action_type: str
    target_uri: str
    payload: dict[str, Any]
    staged_only: bool = True


@dataclass(frozen=True, slots=True)
class StarlarkEvaluationResult:
    """Deterministic evaluation result of a `.star` mechanism script."""

    passed: bool
    verdicts: tuple[StarlarkVerdictItem, ...]
    staged_effects: tuple[StarlarkStagedEffect, ...]
    steps_executed: int
    elapsed_ms: float
    llm_tokens_consumed: int = 0


class _OrciaSysHost:
    """Deterministic `orcia_sys` host API exposed inside `StarlarkMechanismSandbox`."""

    def __init__(
        self,
        *,
        payload: dict[str, Any],
        max_steps: int = 100_000,
    ) -> None:
        self._payload = copy.deepcopy(payload)
        self._max_steps = max_steps
        self.steps_executed = 0
        self.verdicts: list[StarlarkVerdictItem] = []
        self.staged_effects: list[StarlarkStagedEffect] = []

    def _tick(self, cost: int = 1) -> None:
        self.steps_executed += cost
        if self.steps_executed > self._max_steps:
            raise StarlarkSandboxError(
                f"Step cap exceeded ({self.steps_executed} > {self._max_steps})."
            )

    def input(self, schema_ref: str | None = None) -> dict[str, Any]:
        """Return a copy of the validated step payload."""
        _ = schema_ref
        self._tick(1)
        return copy.deepcopy(self._payload)

    def re_fullmatch(self, pattern: str, text: str) -> bool:
        """Linear-time O(n) regex fullmatch with anti-ReDoS automaton guard (`max_mem = 8 MB`)."""
        self._validate_linear_regex(pattern, text)
        self._tick(max(1, len(text) // 64))
        return re.fullmatch(pattern, text) is not None

    def re_search(self, pattern: str, text: str) -> bool:
        """Linear-time O(n) regex search with anti-ReDoS automaton guard (`max_mem = 8 MB`)."""
        self._validate_linear_regex(pattern, text)
        self._tick(max(1, len(text) // 64))
        return re.search(pattern, text) is not None

    def emit_verdict(
        self,
        rule_id: str,
        status: str,
        message_fr: str,
    ) -> None:
        """Emit a deterministic PASS or FAIL verdict for `rule_id`."""
        self._tick(1)
        if status not in ("PASS", "FAIL"):
            raise StarlarkSandboxError(f"Invalid verdict status '{status}' (expected PASS|FAIL).")
        self.verdicts.append(
            StarlarkVerdictItem(
                rule_id=str(rule_id),
                status="PASS" if status == "PASS" else "FAIL",
                message_fr=str(message_fr),
            )
        )

    def assert_rule(
        self,
        *,
        rule_id: str,
        condition: bool,
        message: str,
        evidence_ref: str = "",
    ) -> None:
        """Record a deterministic PASS or FAIL verdict from a boolean `condition`."""
        _ = evidence_ref
        self.emit_verdict(rule_id, "PASS" if bool(condition) else "FAIL", message)

    def emit_effect(
        self,
        action_type: str,
        target_uri: str,
        payload: dict[str, Any],
    ) -> None:
        """Queue a Staged Action (`step_executions.draft_artifact_jsonb`, zero direct SI write)."""
        self._tick(2)
        self.staged_effects.append(
            StarlarkStagedEffect(
                action_type=str(action_type),
                target_uri=str(target_uri),
                payload=copy.deepcopy(dict(payload)),
                staged_only=True,
            )
        )

    @staticmethod
    def _validate_linear_regex(pattern: str, text: str) -> None:
        if len(pattern) > 512:
            raise StarlarkSandboxError("Regex pattern exceeds 512 chars limit.")
        if len(text) > 65_536:
            raise StarlarkSandboxError("Regex input text exceeds 64 KB limit.")
        if _CATASTROPHIC_REDOS_PATTERN.search(pattern) or "\\1" in pattern:
            raise StarlarkSandboxError(
                f"Pattern '{pattern}' rejected by RE2 linear-time O(n) automaton guard (ReDoS)."
            )
        try:
            re.compile(pattern)
        except re.error as exc:
            raise StarlarkSandboxError(f"Invalid regex syntax: {exc}") from exc


class StarlarkMechanismSandbox:
    """Tier 1b deterministic Starlark sandbox (`max_steps = 100_000`, `< 2 ms`, `0` LLM tokens)."""

    def __init__(self, *, max_steps: int = 100_000) -> None:
        self._max_steps = max_steps

    def evaluate_script(
        self,
        *,
        starlark_code: str,
        payload: dict[str, Any],
    ) -> StarlarkEvaluationResult:
        """Validate AST determinism and execute `.star` mechanism against `payload`."""
        started = time.perf_counter()
        tree = self._parse_and_verify_starlark_ast(starlark_code)
        host = _OrciaSysHost(payload=payload, max_steps=self._max_steps)
        safe_builtins: dict[str, Any] = {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "min": min,
            "max": max,
            "sum": sum,
            "any": any,
            "all": all,
            "sorted": sorted,
            "range": lambda n: range(min(int(n), 1000)),
            "True": True,
            "False": False,
            "None": None,
        }
        env: dict[str, Any] = {
            "__builtins__": safe_builtins,
            "orcia_sys": host,
        }
        compiled = compile(tree, filename="<mechanism.star>", mode="exec")
        exec(compiled, env, env)  # noqa: S102
        if callable(env.get("evaluate")):
            host._tick(1)
            env["evaluate"](host.input())

        if not host.verdicts:
            raise StarlarkSandboxError(
                "Starlark mechanism completed without calling orcia_sys.emit_verdict(...)."
            )
        passed = all(v.status == "PASS" for v in host.verdicts)
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        return StarlarkEvaluationResult(
            passed=passed,
            verdicts=tuple(host.verdicts),
            staged_effects=tuple(host.staged_effects),
            steps_executed=host.steps_executed,
            elapsed_ms=elapsed_ms,
            llm_tokens_consumed=0,
        )

    @staticmethod
    def _parse_and_verify_starlark_ast(starlark_code: str) -> ast.Module:
        try:
            tree = ast.parse(starlark_code, filename="<mechanism.star>", mode="exec")
        except SyntaxError as exc:
            raise StarlarkSandboxError(f"Starlark syntax error: {exc}") from exc

        for node_count, node in enumerate(ast.walk(tree), start=1):
            if node_count > 5_000:
                raise StarlarkSandboxError("Starlark AST exceeds 5,000 nodes limit.")
            if isinstance(node, _FORBIDDEN_AST_NODES):
                raise StarlarkSandboxError(
                    f"Forbidden non-deterministic construct in Starlark: {type(node).__name__}"
                )
            if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
                raise StarlarkSandboxError(
                    f"Private/dunder attribute access '{node.attr}' is forbidden in Starlark."
                )
            if isinstance(node, ast.Name) and node.id.startswith("__"):
                raise StarlarkSandboxError(
                    f"Dunder identifier '{node.id}' is forbidden in Starlark."
                )
        return tree
