"""AST audit forbidding manual `app.state.*` & `dependency_overrides` tampering in Layer 2 tests.

Ensures vertical PostgreSQL 18 integration tests exercise the real Composition Root
(`create_app()` + `app.router.lifespan_context(app)` / `initialize_app_services(app)`)
without injecting fake DB engines, repositories, services, or FastAPI dependency overrides.
Only explicit `0 $` external HTTP transport mocks (`app.state.http_client`) and outbound
email sinks (`app.state.otp_email_sink`) are permitted on `app.state`.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_TESTS_DIR = REPO_ROOT / "tests" / "integration"

# Documented external I/O boundaries (`0 $` LLM HTTP transport & outbound OTP email sink).
ALLOWED_EXTERNAL_TRANSPORT_ATTRS: frozenset[str] = frozenset(
    {
        "http_client",
        "otp_email_sink",
    }
)


def _is_app_state_expr(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "state"


def _is_dependency_overrides_expr(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "dependency_overrides"


def _find_manual_app_state_violations(tree: ast.AST, label: str) -> list[str]:
    violations: list[str] = []
    mutating_methods = {
        "update",
        "setdefault",
        "pop",
        "popitem",
        "clear",
        "__setitem__",
        "__delitem__",
    }

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.ctx, ast.Store | ast.Del)
            and _is_dependency_overrides_expr(node.value)
        ):
            violations.append(f"{label}:{node.lineno} forbids mutating `dependency_overrides[...]`")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in mutating_methods
            and _is_dependency_overrides_expr(node.func.value)
        ):
            violations.append(
                f"{label}:{node.lineno} forbids `dependency_overrides.{node.func.attr}()`"
            )

        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AugAssign | ast.AnnAssign):
            targets = [node.target]
        else:
            targets = []

        for target in targets:
            if _is_dependency_overrides_expr(target):
                violations.append(
                    f"{label}:{target.lineno} forbids assigning `dependency_overrides`"
                )
            if (
                isinstance(target, ast.Attribute)
                and _is_app_state_expr(target.value)
                and target.attr not in ALLOWED_EXTERNAL_TRANSPORT_ATTRS
            ):
                violations.append(
                    f"{label}:{target.lineno} forbids manual `*.state.{target.attr}` assignment"
                )

        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "setattr"
            and len(node.args) >= 2
            and _is_app_state_expr(node.args[0])
        ):
            attr_arg = node.args[1]
            attr_name = (
                attr_arg.value
                if isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str)
                else "<dynamic>"
            )
            if attr_name not in ALLOWED_EXTERNAL_TRANSPORT_ATTRS:
                violations.append(
                    f"{label}:{node.lineno} forbids `setattr(*.state, {attr_name!r}, ...)`"
                )

    return violations


def test_integration_suite_uses_real_composition_root_without_overrides_or_state_tampering() -> (
    None
):
    """Verify `tests/integration/**/*.py` avoids overrides and `app.state` tampering."""
    py_files = sorted(INTEGRATION_TESTS_DIR.rglob("*.py"))
    assert len(py_files) >= 1

    violations: list[str] = []
    for path in py_files:
        rel = str(path.relative_to(REPO_ROOT))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        violations.extend(_find_manual_app_state_violations(tree, rel))

    assert violations == [], (
        "Layer 2 integration tests must not override Composition Root or `app.state`:\n"
        + "\n".join(violations)
    )


def test_audit_detector_catches_state_assignment_setattr_and_dependency_overrides() -> None:
    """Verify the AST detector catches synthetic `app.state`, `setattr`, and overrides."""
    synthetic = (
        "app.state.dbos_uow = fake_uow\n"
        "setattr(app.state, 'auth_service', fake_auth)\n"
        "app.dependency_overrides[get_auth_service] = lambda: fake_auth\n"
        "app.state.http_client = fake_http_client\n"
        "app.state.otp_email_sink = fake_sink\n"
    )
    violations = _find_manual_app_state_violations(ast.parse(synthetic), "<synthetic>")
    assert len(violations) == 3
    assert any("dbos_uow" in v for v in violations)
    assert any("auth_service" in v for v in violations)
    assert any("dependency_overrides" in v for v in violations)
