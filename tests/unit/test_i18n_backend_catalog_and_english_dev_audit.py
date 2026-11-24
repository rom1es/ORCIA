"""Gate 4 — Backend RFC 9457 Bilingual Completeness, Prompt Neutrality & English Dev Audit.

Enforces Epic 27 Decisions D2 & D3 across `packages/orcia-core`, `apps/api`, and `apps/worker`,
plus English-only comments/docstrings on added/modified Python and TypeScript lines vs `main`.
"""

from __future__ import annotations

import ast
import io
import json
import re
import subprocess
import tokenize
from pathlib import Path

import orcia_api.errors.registry as error_registry
from orcia_kernel.errors import ERROR_CATALOG, get_localized_error_text, resolve_locale

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = Path(__file__).resolve().parent / "i18n_backend_audit_baseline.json"
BACKEND_SRC_DIRS = (
    REPO_ROOT / "packages" / "orcia-core" / "src",
    REPO_ROOT / "packages" / "orcia-connectors" / "src",
    REPO_ROOT / "apps" / "api" / "src",
    REPO_ROOT / "apps" / "worker" / "src",
)
EXCLUDED_BACKEND_SUFFIXES = (
    "_error_catalog.py",
    "_error_catalog_2.py",
    "_auth_error_catalog.py",
    "assistant_prompt_locales.py",
    "_assistant_turn_locale_messages.py",
    "_locales.py",
    "_locale_messages.py",
)
FRENCH_CHAR_RE = re.compile(r"[àâäçéèêëîïôöùûüÿœæÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ]")
FRENCH_STOPWORDS_RE = re.compile(
    r"\b(?:dans|pour|avec|sans|depuis|sont|être|avoir|vérifie|vérifier|retourne|retourner|"
    r"crée|créer|ajoute|ajouter|supprime|supprimer|empêche|empêcher|données|utilisateur|"
    r"chaîne|français|réponse|requête|toujours)\b",
    re.IGNORECASE,
)
PROMPT_DIRECTIVE_RE = re.compile(
    r"(?:Réponds\s+(?:toujours\s+)?en\s+français|Always\s+reply\s+in\s+English|"
    r"Respond\s+only\s+in\s+(?:French|English)|Tu\s+es\s+un\s+assistant)",
    re.IGNORECASE,
)


def _load_baseline() -> dict[str, object]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _extract_docstring_node(node: ast.AST) -> ast.Constant | None:
    if (
        isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        return node.body[0].value
    return None


def _scan_python_literals(src: str, rel: str) -> tuple[int, int]:
    tree = ast.parse(src, filename=rel)
    docstring_ids: set[int] = set()
    for node in ast.walk(tree):
        doc_node = _extract_docstring_node(node)
        if doc_node is not None:
            docstring_ids.add(id(doc_node))

    prompt_count, french_count = 0, 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstring_ids:
                continue
            if PROMPT_DIRECTIVE_RE.search(node.value):
                prompt_count += 1
            elif FRENCH_CHAR_RE.search(node.value):
                french_count += 1
    return prompt_count, french_count


def _has_french_prose(text: str) -> bool:
    if FRENCH_CHAR_RE.search(text):
        return True
    return len(FRENCH_STOPWORDS_RE.findall(text)) >= 2


def _find_french_in_python_comments(src: str, target_lines: set[int] | None = None) -> list[str]:
    issues: list[str] = []
    tree = ast.parse(src)
    for node in ast.walk(tree):
        doc_node = _extract_docstring_node(node)
        if doc_node is None:
            continue
        start = doc_node.lineno
        end = doc_node.end_lineno or start
        in_target = target_lines is None or any(ln in target_lines for ln in range(start, end + 1))
        if in_target and _has_french_prose(doc_node.value):
            issues.append(f"L{start} docstring: {doc_node.value.splitlines()[0][:60]}")

    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type != tokenize.COMMENT:
            continue
        ln = tok.start[0]
        if (target_lines is None or ln in target_lines) and _has_french_prose(tok.string):
            issues.append(f"L{ln} comment: {tok.string[:60]}")
    return issues


def _find_french_in_ts_comments(added_lines: list[tuple[int, str]]) -> list[str]:
    issues: list[str] = []
    for ln, line in added_lines:
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")) and _has_french_prose(stripped):
            issues.append(f"L{ln} ts-comment: {stripped[:60]}")
    return issues


def _resolve_base_ref() -> str | None:
    for ref in ("main", "origin/main"):
        res = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return ref
    return None


def _collect_added_lines_vs_base(base_ref: str) -> dict[str, list[tuple[int, str]]]:
    diff = subprocess.check_output(
        ["git", "diff", "--unified=0", base_ref],
        cwd=REPO_ROOT,
        text=True,
        errors="replace",
    )
    by_file: dict[str, list[tuple[int, str]]] = {}
    current_file: str | None = None
    next_ln = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@ ") and current_file:
            m = re.search(r"\+(\d+)", line)
            next_ln = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++") and current_file:
            by_file.setdefault(current_file, []).append((next_ln, line[1:]))
            next_ln += 1

    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        text=True,
    )
    for rel in untracked.splitlines():
        if rel.endswith((".py", ".ts", ".tsx")) and (REPO_ROOT / rel).is_file():
            content = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            by_file[rel] = [(idx, txt) for idx, txt in enumerate(content.splitlines(), 1)]
    return by_file


def test_rfc9457_error_catalog_bilingual_completeness() -> None:
    """Every registered error code and domain exception must provide valid FR & EN copies."""
    import orcia_connectors._error_catalog  # noqa: F401
    import orcia_core.blackboard.errors  # noqa: F401
    import orcia_core.observability.errors  # noqa: F401
    import orcia_core.permissions.ssrf_policy  # noqa: F401

    baseline = _load_baseline()
    assert baseline["missingErrorCatalogCodes"] == []

    incomplete: list[str] = []
    for code, locales in sorted(ERROR_CATALOG.items()):
        for lang in ("fr", "en"):
            copy = locales.get(lang)
            if copy is None or not copy.title.strip() or not copy.detail.strip():
                incomplete.append(f"{code}:{lang}")
    assert incomplete == [], f"Incomplete ERROR_CATALOG entries: {incomplete}"

    for cls in error_registry.DOMAIN_ERROR_CLASSES:
        assert cls.error_code in ERROR_CATALOG, f"{cls.__name__} missing in ERROR_CATALOG"

    ast_missing: list[str] = []
    for base in BACKEND_SRC_DIRS:
        for py_path in sorted(base.rglob("*.py")):
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and any(
                    "OrciaDomainError" in ast.unparse(b) for b in node.bases
                ):
                    for stmt in node.body:
                        if isinstance(stmt, ast.Assign):
                            for tgt in stmt.targets:
                                if (
                                    isinstance(tgt, ast.Name)
                                    and tgt.id == "error_code"
                                    and isinstance(stmt.value, ast.Constant)
                                    and isinstance(stmt.value.value, str)
                                    and stmt.value.value not in ERROR_CATALOG
                                ):
                                    ast_missing.append(f"{node.name}:{stmt.value.value}")
    assert ast_missing == [], f"New OrciaDomainError classes missing ERROR_CATALOG: {ast_missing}"

    assert resolve_locale(None) == "fr"
    assert resolve_locale("fr-FR") == "fr"
    assert resolve_locale("en-US,fr;q=0.8") == "en"
    fr_copy = get_localized_error_text("ERR_OBSERVER_MODE_READ_ONLY", "fr")
    en_copy = get_localized_error_text("ERR_OBSERVER_MODE_READ_ONLY", "en")
    assert fr_copy.title != en_copy.title


def test_backend_prompt_locale_neutrality_and_french_literal_ratchet() -> None:
    """Zero hardcoded single-language prompt directives and zero backend French literals."""
    baseline = _load_baseline()
    assert baseline["totalPromptDirectiveViolations"] == 0
    assert baseline["promptDirectiveFiles"] == {}
    assert baseline["totalNonCatalogFrenchLiterals"] == 0
    assert baseline["nonCatalogFrenchFiles"] == {}

    regressions: list[str] = []
    for base in BACKEND_SRC_DIRS:
        for py_path in sorted(base.rglob("*.py")):
            rel = py_path.relative_to(REPO_ROOT).as_posix()
            if (
                rel.endswith(EXCLUDED_BACKEND_SUFFIXES)
                or rel.endswith("/errors.py")
                or "/testing/" in rel
            ):
                continue
            p_cnt, f_cnt = _scan_python_literals(py_path.read_text(encoding="utf-8"), rel)
            if p_cnt > 0:
                regressions.append(f"{rel}: prompt directives = {p_cnt}")
            if f_cnt > 0:
                regressions.append(f"{rel}: french literals = {f_cnt}")
    assert regressions == [], "Backend i18n regressions:\n" + "\n".join(regressions)

    p_syn, f_syn = _scan_python_literals(
        'PROMPT = "Réponds toujours en français"\nERR = "Erreur réseau interne"\n',
        "synthetic.py",
    )
    assert (p_syn, f_syn) == (1, 1)


def test_english_only_comments_and_docstrings_on_diff_against_main() -> None:
    """All added/modified Python & TS comments and docstrings vs main must be English-only."""
    fr_py = '# Vérifie les données\ndef f():\n    """Retourne la chaîne."""\n    pass\n'
    en_py = '# Verify input payload\ndef f():\n    """Return normalized string."""\n    pass\n'
    assert _find_french_in_python_comments(fr_py)
    assert _find_french_in_ts_comments([(1, "// Vérifie l'état utilisateur")])
    assert _find_french_in_python_comments(en_py) == []

    base_ref = _resolve_base_ref()
    assert base_ref is not None, (
        "Neither 'main' nor 'origin/main' git ref is available for English-only diff audit."
    )

    excluded_prefixes = (
        "apps/web/src/i18n/locales/",
        "apps/web/src/generated/",
        "packages/api-client/src/generated/",
        "docs/",
        "scripts/",
    )
    violations: list[str] = []
    for rel, added in sorted(_collect_added_lines_vs_base(base_ref).items()):
        if rel.startswith(excluded_prefixes) or rel.endswith(EXCLUDED_BACKEND_SUFFIXES):
            continue
        if rel.endswith("/errors.py") or "/_error_catalog" in rel:
            continue
        if rel.endswith(".py") and (REPO_ROOT / rel).is_file():
            target_lns = {ln for ln, _ in added}
            src = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            for issue in _find_french_in_python_comments(src, target_lns):
                violations.append(f"{rel}:{issue}")
        elif rel.endswith((".ts", ".tsx")):
            for issue in _find_french_in_ts_comments(added):
                violations.append(f"{rel}:{issue}")

    assert violations == [], "Non-English comments/docstrings in diff vs main:\n" + "\n".join(
        violations
    )
