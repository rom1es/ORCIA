"""Permanent AST & Architectural Anti-Pattern Audit across the ORCIA Python codebase.

Enforces the 4 Architectural Invariants defined in `GEMINI.md` (`Section 4`):
1. Rule 1 — Zero sync HTTP, ThreadPoolExecutor, or on-the-fly DB engines in FastAPI routers.
2. Rule 2 — Zero fake word-by-word `.split(" ")` SSE streaming.
3. Rule 3 — Zero vendor-named functions (`*ollama*`), hardcoded hat dicts, or French-only rules.
4. Rule 4 — Zero silent `except Exception:` without structured logging in `orcia_api/routers/`,
   plus mandatory SSRF guard (`is_safe_llm_endpoint_url`).
"""

from __future__ import annotations

import ast
from pathlib import Path

from orcia_api.routers.assistant_llm_providers import is_safe_llm_endpoint_url

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROUTERS_DIR = REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "routers"
ALL_PYTHON_SRC_DIRS = (
    REPO_ROOT / "apps" / "api" / "src",
    REPO_ROOT / "apps" / "worker" / "src",
    REPO_ROOT / "packages" / "orcia-core" / "src",
    REPO_ROOT / "packages" / "orcia-kernel" / "src",
)


def _iter_py_files(roots: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(sorted(root.rglob("*.py")))
    return files


def test_rule_1_zero_sync_http_threads_or_on_the_fly_db_engines_in_api_routers() -> None:
    """Verify `apps/api/src/orcia_api/routers/` never blocks ASGI loop or leaks DB pools."""
    forbidden_patterns = (
        "httpx.Client",
        "requests.",
        "urllib.request",
        "ThreadPoolExecutor",
        "asyncio.run(",
        "create_async_engine(",
    )
    violations: list[str] = []
    for path in _iter_py_files((API_ROUTERS_DIR,)):
        rel = path.relative_to(REPO_ROOT)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pat in forbidden_patterns:
                if pat in stripped:
                    violations.append(f"{rel}:{lineno} uses forbidden `{pat}`: {stripped}")
    assert violations == [], "Rule 1 violations in API routers:\n" + "\n".join(violations)


def test_rule_2_zero_fake_word_split_streaming_in_sse_generators() -> None:
    """Verify no streaming generator in `apps/api` or `orcia_core` splits by `.split(' ')`."""
    violations: list[str] = []
    for path in _iter_py_files(ALL_PYTHON_SRC_DIRS):
        rel = path.relative_to(REPO_ROOT)
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(rel))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "stream" in node.name:
                fn_seg = ast.get_source_segment(src, node) or ""
                if '.split(" ")' in fn_seg or ".split(' ')" in fn_seg:
                    violations.append(
                        f"{rel}:{node.lineno} streaming function `{node.name}` uses `.split(' ')`"
                    )
    assert violations == [], "Rule 2 fake-streaming violations:\n" + "\n".join(violations)


def test_rule_3_zero_vendor_coupled_functions_or_hardcoded_french_only_prompts() -> None:
    """Verify `apps/api` has zero `*ollama*` functions, hardcoded hats, or French-only rules."""
    violations: list[str] = []
    for path in _iter_py_files((REPO_ROOT / "apps" / "api" / "src",)):
        rel = path.relative_to(REPO_ROOT)
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(rel))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_lower = node.name.lower()
                if "ollama" in fn_lower or fn_lower == "_humanize_hat_label_fr":
                    violations.append(
                        f"{rel}:{node.lineno} defines vendor/hat-hardcoded function `{node.name}`"
                    )
        for lineno, line in enumerate(src.splitlines(), 1):
            if "Réponds toujours en français" in line:
                violations.append(f"{rel}:{lineno} hardcodes French-only rule: {line.strip()}")
            if '"think": False' in line or "'think': False" in line:
                violations.append(
                    f"{rel}:{lineno} hardcodes proprietary `think: False`: {line.strip()}"
                )
    assert violations == [], "Rule 3 agnosticism violations:\n" + "\n".join(violations)


def test_rule_4_zero_silent_except_exception_in_api_routers_and_ssrf_guard() -> None:
    """Verify every `except Exception` in `apps/api/src/orcia_api/routers/` logs or re-raises."""
    violations: list[str] = []
    for path in _iter_py_files((API_ROUTERS_DIR,)):
        rel = path.relative_to(REPO_ROOT)
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                t_name = ast.unparse(node.type) if node.type else "bare"
                if "Exception" in t_name or t_name == "bare":
                    seg = ast.get_source_segment(src, node) or ""
                    if (
                        "logger." not in seg
                        and "get_logger(" not in seg
                        and "_log_provider_error(" not in seg
                        and "raise" not in seg
                    ):
                        violations.append(
                            f"{rel}:{node.lineno} silent `except {t_name}:` without structured log"
                        )
    assert violations == [], "Rule 4 silent exception violations:\n" + "\n".join(violations)

    assert not is_safe_llm_endpoint_url("http://169.254.169.254/latest/meta-data/")
    assert not is_safe_llm_endpoint_url("http://metadata.google.internal/computeMetadata/v1/")
    assert is_safe_llm_endpoint_url("http://ollama.corp.local:11434")
    assert is_safe_llm_endpoint_url("https://vllm.ai.internal:8443/v1")
