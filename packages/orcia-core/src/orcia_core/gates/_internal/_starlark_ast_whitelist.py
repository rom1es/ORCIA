"""Strict AST node and attribute whitelist for deterministic Starlark (`AD-9`, `Story 31.1`)."""

from __future__ import annotations

import ast
import math
import re

from orcia_core.gates.errors import ValidationDomainError

MAX_STARLARK_AST_NODES = 5_000
MAX_STARLARK_NUMERIC_LITERAL = 1_000_000
MAX_STARLARK_STRING_LITERAL_LEN = 65_536
_SAFE_FORMAT_SPEC_RE = re.compile(r"^[.<>^=+\-0# ]{0,4}(?:\d{1,2})?(?:\.\d{1,2})?[fds]?$")

ALLOWED_STARLARK_AST_NODES: tuple[type[ast.AST], ...] = (
    ast.Module,
    ast.FunctionDef,
    ast.Return,
    ast.Assign,
    ast.AugAssign,
    ast.AnnAssign,
    ast.If,
    ast.For,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.Expr,
    ast.arguments,
    ast.arg,
    ast.Call,
    ast.keyword,
    ast.Attribute,
    ast.Subscript,
    ast.Slice,
    ast.Name,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.IfExp,
    ast.JoinedStr,
    ast.FormattedValue,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.And,
    ast.Or,
    ast.UAdd,
    ast.USub,
    ast.Not,
    ast.Invert,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
    ast.Load,
    ast.Store,
)

ALLOWED_STARLARK_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "input",
        "re_fullmatch",
        "re_search",
        "emit_verdict",
        "assert_rule",
        "emit_effect",
        "get",
        "keys",
        "values",
        "items",
        "strip",
        "lstrip",
        "rstrip",
        "lower",
        "upper",
        "startswith",
        "endswith",
        "split",
        "join",
        "replace",
        "find",
        "count",
        "append",
        "extend",
    }
)

FORBIDDEN_STARLARK_NAMES: frozenset[str] = frozenset(
    {
        "exec",
        "eval",
        "open",
        "__import__",
        "compile",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "dir",
        "breakpoint",
        "input",
        "type",
        "object",
        "super",
        "classmethod",
        "staticmethod",
    }
)


class StarlarkSandboxError(ValidationDomainError, ValueError):
    """Raised when a Starlark mechanism script violates determinism, step cap, or AST whitelist."""

    def __init__(self, message: str = "Starlark mechanism sandbox error.") -> None:
        ValidationDomainError.__init__(self, detail_override=message)
        ValueError.__init__(self, message)


def validate_starlark_ast(
    starlark_code: str,
    *,
    filename: str = "<mechanism.star>",
) -> ast.Module:
    """Parse and enforce the strict AST node, attribute, and identifier whitelist."""
    try:
        tree = ast.parse(starlark_code, filename=filename, mode="exec")
    except (SyntaxError, ValueError) as exc:
        raise StarlarkSandboxError(f"Starlark syntax error: {exc}") from exc

    for node_count, node in enumerate(ast.walk(tree), start=1):
        if node_count > MAX_STARLARK_AST_NODES:
            raise StarlarkSandboxError("Starlark AST exceeds 5,000 nodes limit.")
        if not isinstance(node, ALLOWED_STARLARK_AST_NODES):
            raise StarlarkSandboxError(
                f"Forbidden non-deterministic construct in Starlark: {type(node).__name__}"
            )
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or node.attr not in ALLOWED_STARLARK_ATTRIBUTES:
                raise StarlarkSandboxError(
                    f"Attribute access '{node.attr}' is forbidden in Starlark."
                )
        elif isinstance(node, ast.Name):
            if node.id.startswith("_") or node.id in FORBIDDEN_STARLARK_NAMES:
                raise StarlarkSandboxError(f"Identifier '{node.id}' is forbidden in Starlark.")
        elif isinstance(node, ast.FunctionDef):
            if node.name.startswith("_") or node.decorator_list:
                raise StarlarkSandboxError(
                    f"Function definition '{node.name}' or decorators are forbidden in Starlark."
                )
        elif isinstance(node, ast.arg):
            if node.arg.startswith("_"):
                raise StarlarkSandboxError(
                    f"Underscore parameter '{node.arg}' is forbidden in Starlark."
                )
        elif isinstance(node, ast.keyword) and (node.arg is None or node.arg.startswith("_")):
            raise StarlarkSandboxError(
                "Kwargs unpacking or underscore keyword is forbidden in Starlark."
            )
        elif isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Mult):
            if not isinstance(node.target, ast.Name):
                raise StarlarkSandboxError(
                    "In-place multiplication is only permitted on local variables in Starlark."
                )
        elif isinstance(node, ast.Constant):
            _validate_starlark_constant(node.value)
        elif isinstance(node, ast.FormattedValue) and node.format_spec is not None:
            _validate_format_spec(node.format_spec)
    return tree


def _validate_starlark_constant(value: object) -> None:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value) or abs(value) > MAX_STARLARK_NUMERIC_LITERAL:
            raise StarlarkSandboxError(f"Numeric literal {value!r} exceeds sandbox limit.")
    elif (
        isinstance(value, int)
        and not isinstance(value, bool)
        and abs(value) > MAX_STARLARK_NUMERIC_LITERAL
    ):
        raise StarlarkSandboxError(f"Integer literal {value!r} exceeds sandbox limit.")
    elif isinstance(value, (str, bytes)) and len(value) > MAX_STARLARK_STRING_LITERAL_LEN:
        raise StarlarkSandboxError(
            f"String/bytes literal exceeds {MAX_STARLARK_STRING_LITERAL_LEN} length limit."
        )


def _validate_format_spec(format_spec: ast.AST) -> None:
    if not isinstance(format_spec, ast.JoinedStr) or any(
        not isinstance(part, ast.Constant) or not isinstance(part.value, str)
        for part in format_spec.values
    ):
        raise StarlarkSandboxError("Dynamic format_spec is forbidden in Starlark.")
    spec_text = "".join(
        str(part.value) for part in format_spec.values if isinstance(part, ast.Constant)
    )
    if spec_text and not _SAFE_FORMAT_SPEC_RE.match(spec_text):
        raise StarlarkSandboxError(f"Format spec {spec_text!r} exceeds Starlark safety bounds.")


__all__ = [
    "ALLOWED_STARLARK_AST_NODES",
    "ALLOWED_STARLARK_ATTRIBUTES",
    "FORBIDDEN_STARLARK_NAMES",
    "StarlarkSandboxError",
    "validate_starlark_ast",
]
