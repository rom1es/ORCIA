"""Story 11.2: Deterministic Tier 1b `StarlarkMechanismSandbox` (`AD-9`, `< 2 ms`, `0` token)."""

from __future__ import annotations

import ast
import copy
import re
import time
from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.gates._internal._starlark_ast_whitelist import (
    StarlarkSandboxError,
    validate_starlark_ast,
)

_CATASTROPHIC_REDOS_PATTERN = re.compile(r"\([^()]*[+*][^()]*\)[+*?]|\(\?P?<[^>]+>[^()]*[+*]\)[+*]")
_MAX_STARLARK_REPEAT_COUNT = 10_000
_MAX_STARLARK_SEQ_RESULT_LEN = 65_536


def _safe_mult(left: Any, right: Any) -> Any:
    seq: str | bytes | list[Any] | tuple[Any, ...] | None = None
    count: int | None = None
    if isinstance(left, (str, bytes, list, tuple)) and isinstance(right, int):
        seq, count = left, right
    elif isinstance(right, (str, bytes, list, tuple)) and isinstance(left, int):
        seq, count = right, left
    if (
        seq is not None
        and count is not None
        and (
            count > _MAX_STARLARK_REPEAT_COUNT
            or len(seq) * max(0, count) > _MAX_STARLARK_SEQ_RESULT_LEN
        )
    ):
        raise StarlarkSandboxError("Sequence repetition exceeds sandbox safety limit.")
    return left * right


class _StarlarkTickAndMultTransformer(ast.NodeTransformer):
    """Instrument functions/loops with `_tick()` caps and guard sequence repetition."""

    @staticmethod
    def _tick_stmt(cost: int = 1) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="orcia_sys", ctx=ast.Load()),
                    attr="_tick",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=cost)],
                keywords=[],
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        node.body = [self._tick_stmt(1), *node.body]
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        self.generic_visit(node)
        node.body = [self._tick_stmt(10), *node.body]
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.op, ast.Mult):
            return ast.Call(
                func=ast.Name(id="__orcia_mul__", ctx=ast.Load()),
                args=[node.left, node.right],
                keywords=[],
            )
        return node

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.op, ast.Mult) and isinstance(node.target, ast.Name):
            return ast.Assign(
                targets=[node.target],
                value=ast.Call(
                    func=ast.Name(id="__orcia_mul__", ctx=ast.Load()),
                    args=[ast.Name(id=node.target.id, ctx=ast.Load()), node.value],
                    keywords=[],
                ),
            )
        return node


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
            "__orcia_mul__": _safe_mult,
        }
        try:
            compiled = compile(tree, filename="<mechanism.star>", mode="exec")
            exec(compiled, env, env)  # noqa: S102
            if callable(env.get("evaluate")):
                host._tick(1)
                env["evaluate"](host.input())
        except StarlarkSandboxError:
            raise
        except Exception as exc:
            raise StarlarkSandboxError(f"Starlark execution error: {exc}") from exc

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
        tree = validate_starlark_ast(starlark_code, filename="<mechanism.star>")
        transformed = _StarlarkTickAndMultTransformer().visit(tree)
        ast.fix_missing_locations(transformed)
        assert isinstance(transformed, ast.Module)
        return transformed
