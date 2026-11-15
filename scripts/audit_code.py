#!/usr/bin/env python3
"""
Audit statique déterministe du monorepo ORCIA (v2 - Sans bruit ni artefacts générés).
Exclut .gitnexus, les caches (.v8, ruff, mypy, pytest), les skills d'agents IA et generated/.
Sépare les classements Top 5 entre Python et TypeScript/React.
"""

import ast
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# 1. Dossiers exclus (caches, bases locales, code généré, skills agents IA)
EXCLUDED_DIRS = {
    ".git",
    ".gitnexus",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".hypothesis",
    "coverage",
    ".nyc_output",
    ".vitest",
    "playwright-report",
    "test-results",
    ".cache",
    "tmp",
    "temp",
    "logs",
    "generated",  # Exclut packages/api-client/src/generated et apps/web/src/generated
    ".agent",
    ".agents",
    ".claude",  # Exclut les skills BMAD/GitNexus hors périmètre applicatif
}

# 2. Extensions de caches, binaires, bases locales et artefacts d'exécution exclus
EXCLUDED_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".wasm",
    ".v8",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".wal",
    ".shm",
    ".lbug",
    ".log",
    ".pid",
    ".tag",
    ".tsbuildinfo",
    ".baseline",
    ".lock",
}

# 3. Fichiers spécifiques exclus (lockfiles, rapports d'audit, specs OpenAPI générées)
EXCLUDED_FILES = {
    ".coverage",
    "coverage.xml",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "uv.lock",
    "poetry.lock",
    "openapi.json",
    "audit_report.md",
    "PKG-INFO",
}

# Regex pour détecter un fichier de cache nommé uniquement par un hash hexadécimal ou entier
HASH_FILENAME_RE = re.compile(r"^(?:[0-9]{5,}|[0-9a-f]{12,64})$")

CODE_PY_EXTS = {".py"}
CODE_TS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

PYTHON_STDLIB = set(getattr(sys, "stdlib_module_names", set())) | {
    "typing",
    "dataclasses",
    "pathlib",
    "collections",
    "datetime",
    "uuid",
    "json",
    "os",
    "sys",
    "re",
    "asyncio",
    "abc",
    "enum",
    "logging",
    "hashlib",
    "hmac",
    "base64",
    "time",
    "functools",
    "itertools",
    "contextlib",
    "unittest",
    "ast",
    "subprocess",
    "shutil",
    "tempfile",
    "io",
    "math",
    "random",
    "copy",
    "inspect",
    "urllib",
    "http",
    "decimal",
    "fractions",
    "statistics",
    "secrets",
    "traceback",
    "__future__",
}

INTERNAL_PY_PREFIXES = {
    "orcia_core",
    "orcia_api",
    "orcia_worker",
    "orcia_connectors",
    "orcia_kernel",
    "orcia_pack_sdlc",
    "orcia_pack_builder",
    "tests",
}
INTERNAL_TS_PREFIXES = ("@orcia/", ".", "..", "@/", "~/", "/")
VALID_NPM_PKG_RE = re.compile(r"^(?:@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]*$")


def is_excluded_dir(dirname: str) -> bool:
    return (
        dirname in EXCLUDED_DIRS or dirname.endswith(".egg-info") or dirname.startswith(".coverage")
    )


def is_test_path(rel_path: str) -> bool:
    p = rel_path.replace("\\", "/")
    return (
        p.startswith("tests/")
        or "/__tests__/" in p
        or "/tests/" in p
        or "/e2e/" in p
        or ".test." in p
        or ".spec." in p
        or "vitest" in Path(p).name.lower()
    )


def count_lines_by_lang(filepath: Path, ext: str):
    """Compte précisément SLOC, lignes de commentaires et lignes vides."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0, 0, 0, 0

    lines = content.splitlines()
    total = len(lines)
    blank = 0
    comments = 0
    sloc = 0

    in_block_comment = False
    block_delim = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            blank += 1
            continue

        if ext == ".py":
            if in_block_comment:
                comments += 1
                if block_delim in line:
                    in_block_comment = False
                continue
            if line.startswith("#"):
                comments += 1
                continue
            if line.startswith('"""') or line.startswith("'''"):
                delim = line[:3]
                comments += 1
                if line.count(delim) == 1:
                    in_block_comment = True
                    block_delim = delim
                continue
            sloc += 1

        elif ext in CODE_TS_EXTS or ext == ".css":
            if in_block_comment:
                comments += 1
                if "*/" in line:
                    in_block_comment = False
                continue
            if line.startswith("//"):
                comments += 1
                continue
            if line.startswith("/*"):
                comments += 1
                if "*/" not in line[2:]:
                    in_block_comment = True
                continue
            sloc += 1

        elif ext in {".html", ".md"}:
            if in_block_comment:
                comments += 1
                if "-->" in line:
                    in_block_comment = False
                continue
            if line.startswith("<!--"):
                comments += 1
                if "-->" not in line[4:]:
                    in_block_comment = True
                continue
            sloc += 1

        elif ext in {".yaml", ".yml", ".toml", ".sh", ".ini"} or filepath.name.startswith(".env"):
            if line.startswith("#"):
                comments += 1
            else:
                sloc += 1
        else:
            sloc += 1

    return total, sloc, comments, blank


class PythonAnalyzer(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.is_test = is_test_path(rel_path)
        self.classes = 0
        self.functions = []
        self.imports = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name.split(".")[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.level == 0 and node.module:
            self.imports.append(node.module.split(".")[0])
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes += 1
        self.generic_visit(node)

    def _analyze_func(self, node):
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        length = max(1, end - start + 1)

        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.AsyncFor,
                    ast.ExceptHandler,
                    ast.With,
                    ast.AsyncWith,
                    ast.IfExp,
                ),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif hasattr(ast, "match_case") and isinstance(child, ast.match_case):
                complexity += 1

        def calc_depth(n, current=0):
            max_d = current
            for ch in ast.iter_child_nodes(n):
                if isinstance(
                    ch,
                    (
                        ast.If,
                        ast.For,
                        ast.AsyncFor,
                        ast.While,
                        ast.Try,
                        ast.With,
                        ast.AsyncWith,
                        ast.Match,
                    ),
                ):
                    max_d = max(max_d, calc_depth(ch, current + 1))
                elif not isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    max_d = max(max_d, calc_depth(ch, current))
            return max_d

        self.functions.append(
            {
                "name": f"{self.rel_path}::{node.name}",
                "lang": "Python",
                "is_test": self.is_test,
                "length": length,
                "complexity": complexity,
                "max_depth": calc_depth(node, 0),
            }
        )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._analyze_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._analyze_func(node)


TS_IMPORT_LINE_RE = re.compile(
    r"""^\s*(?:import|export)\s+(?:type\s+)?(?:[^'"\n]*?\s+from\s+)?['"]([^'"\n]+)['"]""",
    re.MULTILINE,
)
TS_CLASS_RE = re.compile(
    r"""^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z0-9_$]+)"""
)
TS_FUNC_PATTERNS = [
    re.compile(
        r"""^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*[<(]"""
    ),
    re.compile(
        r"""^\s*(?:export\s+)?const\s+([A-Za-z0-9_$]+)\s*(?::\s*[^=]+)?=\s*(?:async\s+)?(?:\([^)]*\)|[A-Za-z0-9_$]+)\s*=>"""
    ),
    re.compile(
        r"""^\s*(?:public|private|protected|static|async|\s)*([A-Za-z0-9_$]+)\s*\([^;]*\)\s*(?::\s*[^{]+)?\{$"""
    ),
]


def analyze_ts_file(filepath: Path, rel_path: str):
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0, [], []

    is_test = is_test_path(rel_path)
    lines = content.splitlines()
    classes = 0
    functions = []
    imports = []

    # Extraction stricte des packages NPM valides
    for match in TS_IMPORT_LINE_RE.finditer(content):
        mod = match.group(1).strip()
        if mod.startswith("node:") or mod.startswith(INTERNAL_TS_PREFIXES):
            continue
        pkg = "/".join(mod.split("/")[:2]) if mod.startswith("@") else mod.split("/")[0]
        if VALID_NPM_PKG_RE.match(pkg):
            imports.append(pkg)

    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            i += 1
            continue

        if TS_CLASS_RE.match(line):
            classes += 1

        func_name = None
        for pat in TS_FUNC_PATTERNS:
            m = pat.match(line)
            if m and m.group(1) not in {"if", "for", "while", "switch", "catch", "return"}:
                func_name = m.group(1)
                break

        if func_name:
            brace_balance = 0
            started = False
            end_idx = i
            for j in range(i, n):
                clean_l = re.sub(r"""(['"`])(?:\\.|(?!\1).)*\1""", '""', lines[j])
                clean_l = re.sub(r"//.*$", "", clean_l)
                opens = clean_l.count("{")
                closes = clean_l.count("}")
                if opens > 0:
                    started = True
                brace_balance += opens - closes
                end_idx = j
                if started and brace_balance <= 0:
                    break
                if not started and j - i > 6:
                    end_idx = j
                    break

            func_lines = lines[i : end_idx + 1]
            length = len(func_lines)
            block_text = "\n".join(func_lines)

            cc = 1
            cc += len(re.findall(r"\b(?:if|for|while|case|catch)\b", block_text))
            cc += block_text.count("&&") + block_text.count("||") + block_text.count("??")
            cc += len(re.findall(r"\?[^.:]", block_text))

            max_depth = 0
            cur_depth = 0
            control_stack = []
            local_brace = 0
            for fl in func_lines:
                cl = re.sub(r"//.*$", "", fl).strip()
                is_ctrl = bool(
                    re.match(r"^(?:}\s*)?(?:else\s+if|if|for|while|switch|try|catch)\b", cl)
                )
                if is_ctrl and "{" in cl:
                    cur_depth += 1
                    max_depth = max(max_depth, cur_depth)
                    control_stack.append(local_brace + cl.count("{") - cl.count("}"))
                local_brace += cl.count("{") - cl.count("}")
                while control_stack and local_brace < control_stack[-1]:
                    control_stack.pop()
                    cur_depth = max(0, cur_depth - 1)

            functions.append(
                {
                    "name": f"{rel_path}::{func_name}",
                    "lang": "TS/JS",
                    "is_test": is_test,
                    "length": length,
                    "complexity": cc,
                    "max_depth": max_depth,
                }
            )
        i += 1

    return classes, functions, imports


def print_top_files(title: str, files_list: list):
    print(f"\n### {title}")
    print("| Rang | Périmètre | Fichier | SLOC | Lignes Totales |")
    print("| :---: | :---: | :--- | :---: | :---: |")
    for idx, (path, _ext, tot, sloc, is_test) in enumerate(
        sorted(files_list, key=lambda x: x[3], reverse=True)[:5], 1
    ):
        tag = "TEST" if is_test else "PROD"
        print(f"| {idx} | `{tag}` | `{path}` | **{sloc:,}** | {tot:,} |")


def print_top_funcs_length(title: str, funcs_list: list):
    print(f"\n### {title}")
    print(
        "| Rang | Périmètre | Fonction / Composant | Lignes | Complexité (McCabe) | Imbrication |"
    )
    print("| :---: | :---: | :--- | :---: | :---: | :---: |")
    for idx, fn in enumerate(sorted(funcs_list, key=lambda x: x["length"], reverse=True)[:5], 1):
        tag = "TEST" if fn["is_test"] else "PROD"
        print(
            f"| {idx} | `{tag}` | `{fn['name']}` | **{fn['length']}** | "
            f"{fn['complexity']} | {fn['max_depth']} |"
        )


def print_top_funcs_complexity(title: str, funcs_list: list):
    print(f"\n### {title}")
    print(
        "| Rang | Périmètre | Fonction / Composant | Complexité (McCabe) "
        "| Imbrication Max | Lignes |"
    )
    print("| :---: | :---: | :--- | :---: | :---: | :---: |")
    for idx, fn in enumerate(
        sorted(funcs_list, key=lambda x: (x["complexity"], x["max_depth"]), reverse=True)[:5], 1
    ):
        tag = "TEST" if fn["is_test"] else "PROD"
        print(
            f"| {idx} | `{tag}` | `{fn['name']}` | **{fn['complexity']}** | "
            f"{fn['max_depth']} | {fn['length']} |"
        )


def main(root_dir: str = "."):
    root = Path(root_dir).resolve()
    script_name = Path(__file__).name

    ext_stats = defaultdict(lambda: {"files": 0, "total": 0, "sloc": 0, "comments": 0, "blank": 0})
    py_files = []
    ts_files = []
    all_functions = []
    total_classes = {"Python": 0, "TS/JS": 0}
    py_deps = Counter()
    ts_deps = Counter()

    analyzed_files = 0
    skipped_artifacts = 0

    for dirpath, dirnames, filenames in os.walk(root):
        # Élagage en place des dossiers exclus
        dirnames[:] = [d for d in dirnames if not is_excluded_dir(d)]

        for fname in filenames:
            if fname == script_name or fname in EXCLUDED_FILES or fname.startswith(".coverage"):
                skipped_artifacts += 1
                continue

            fpath = Path(dirpath) / fname
            if fpath.is_symlink():
                continue

            ext = fpath.suffix.lower()
            if ext in EXCLUDED_EXTS:
                skipped_artifacts += 1
                continue

            # Exclusion des fichiers sans extension qui sont des hash/IDs de cache
            # (ruff, mypy, git, etc.)
            if not ext and HASH_FILENAME_RE.match(fname):
                skipped_artifacts += 1
                continue

            rel_path = str(fpath.relative_to(root))
            ext_label = ext if ext else f"({fname})"
            analyzed_files += 1

            total, sloc, comments, blank = count_lines_by_lang(fpath, ext)
            ext_stats[ext_label]["files"] += 1
            ext_stats[ext_label]["total"] += total
            ext_stats[ext_label]["sloc"] += sloc
            ext_stats[ext_label]["comments"] += comments
            ext_stats[ext_label]["blank"] += blank

            test_flag = is_test_path(rel_path)

            if ext in CODE_PY_EXTS:
                py_files.append((rel_path, ext, total, sloc, test_flag))
                try:
                    tree = ast.parse(fpath.read_text(encoding="utf-8", errors="ignore"))
                    analyzer = PythonAnalyzer(rel_path)
                    analyzer.visit(tree)
                    total_classes["Python"] += analyzer.classes
                    all_functions.extend(analyzer.functions)
                    for imp in analyzer.imports:
                        if (
                            imp not in PYTHON_STDLIB
                            and imp not in INTERNAL_PY_PREFIXES
                            and not imp.startswith("_")
                        ):
                            py_deps[imp] += 1
                except SyntaxError:
                    pass

            elif ext in CODE_TS_EXTS:
                ts_files.append((rel_path, ext, total, sloc, test_flag))
                c_cnt, funcs, imps = analyze_ts_file(fpath, rel_path)
                total_classes["TS/JS"] += c_cnt
                all_functions.extend(funcs)
                for imp in imps:
                    ts_deps[imp] += 1

    # --- GÉNÉRATION DU RAPPORT MARKDOWN ---
    print("# Rapport d'Audit Statique Purifié — ORCIA (Hors Caches, `.gitnexus` & `generated/`)\n")

    tot_sloc = sum(v["sloc"] for v in ext_stats.values())
    tot_comm = sum(v["comments"] for v in ext_stats.values())
    tot_blank = sum(v["blank"] for v in ext_stats.values())
    tot_lines = sum(v["total"] for v in ext_stats.values())

    print("## 1. Volumétrie globale (Périmètre Source & Documentation)")
    print(
        f"- **Fichiers sources analysés** : {analyzed_files} "
        f"*(fichiers de cache/binaires/générés ignorés : {skipped_artifacts})*"
    )
    print(
        f"- **Total lignes** : {tot_lines:,} | **SLOC** : {tot_sloc:,} | "
        f"**Commentaires** : {tot_comm:,} | **Vides** : {tot_blank:,}\n"
    )
    print(
        "| Extension | Fichiers | Lignes Totales | SLOC (Effectives) "
        "| Commentaires | Lignes Vides |"
    )
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for ext, st in sorted(ext_stats.items(), key=lambda x: x[1]["sloc"], reverse=True):
        print(
            f"| `{ext}` | {st['files']} | {st['total']:,} | {st['sloc']:,} | "
            f"{st['comments']:,} | {st['blank']:,} |"
        )

    # 2. Structure et modularité (Ventilation PROD vs TEST)
    py_funcs = [f for f in all_functions if f["lang"] == "Python"]
    py_prod = [f for f in py_funcs if not f["is_test"]]
    ts_funcs = [f for f in all_functions if f["lang"] == "TS/JS"]
    ts_prod = [f for f in ts_funcs if not f["is_test"]]

    def avg(lst: list) -> float:
        return (sum(f["length"] for f in lst) / len(lst)) if lst else 0.0

    print("\n## 2. Structure et modularité")
    print(
        "| Périmètre | Fonctions Totales | dont Fonctions `PROD` | Classes "
        "| Taille moy. Globale (lignes) | Taille moy. `PROD` (lignes) |"
    )
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")
    print(
        f"| **Python (`.py`)** | {len(py_funcs)} | {len(py_prod)} | "
        f"{total_classes['Python']} | {avg(py_funcs):.1f} | **{avg(py_prod):.1f}** |"
    )
    print(
        f"| **TypeScript / React (`.ts`, `.tsx`, `.mjs`)** | {len(ts_funcs)} | "
        f"{len(ts_prod)} | {total_classes['TS/JS']} | {avg(ts_funcs):.1f} | "
        f"**{avg(ts_prod):.1f}** |"
    )
    print(
        f"| **Total Combiné** | **{len(all_functions)}** | "
        f"**{len(py_prod) + len(ts_prod)}** | **{sum(total_classes.values())}** | "
        f"**{avg(all_functions):.1f}** | **{avg(py_prod + ts_prod):.1f}** |"
    )

    # 3. Complexité ventilée Python vs TypeScript (Focus PROD + Vue Globale)
    print("\n## 3. Complexité — Écosystème Python")
    py_files_prod = [f for f in py_files if not f[4]]
    print_top_files("Top 5 des fichiers Python `PROD` les plus longs", py_files_prod)
    print_top_funcs_length("Top 5 des fonctions Python `PROD` les plus longues", py_prod)
    print_top_funcs_complexity(
        "Top 5 des fonctions Python `PROD` à plus forte complexité cyclomatique", py_prod
    )

    print("\n## 4. Complexité — Écosystème TypeScript / React")
    ts_files_prod = [f for f in ts_files if not f[4]]
    print_top_files(
        "Top 5 des fichiers TypeScript `PROD` les plus longs (hors `generated/`)", ts_files_prod
    )
    print_top_funcs_length(
        "Top 5 des fonctions / composants TypeScript `PROD` les plus longs", ts_prod
    )
    print_top_funcs_complexity(
        "Top 5 des fonctions / composants TypeScript `PROD` à plus forte complexité", ts_prod
    )
    print_top_funcs_complexity(
        "Rappel — Top 5 des fonctions de `TEST` (Python + TS) les plus complexes",
        [f for f in all_functions if f["is_test"]],
    )

    # 5. Dépendances externes
    print("\n## 5. Dépendances externes les plus importées")
    print("### Écosystème Python (Top 15)")
    print("| Bibliothèque externe | Occurrences d'import |")
    print("| :--- | :---: |")
    for pkg, count in py_deps.most_common(15):
        print(f"| `{pkg}` | {count} |")

    print("\n### Écosystème TypeScript / Frontend (Top 15)")
    print("| Bibliothèque externe | Occurrences d'import |")
    print("| :--- | :---: |")
    for pkg, count in ts_deps.most_common(15):
        print(f"| `{pkg}` | {count} |")


if __name__ == "__main__":
    main("..")
