"""Unit tests for rule size/ID linter, fixture index generator, and Stage 1 wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.receipts import compute_worktree_digest
from scripts.agent_check_lib.static_gates import build_static_gates
from scripts.check_agent_rules import (
    MAX_AGENTS_CORE_BYTES,
    MAX_RULE_FILE_BYTES,
    RuleLintError,
    expand_rule_includes,
    lint_agent_rules,
)
from scripts.check_agent_rules import (
    main as rules_main,
)
from scripts.generate_test_fixture_index import (
    main as fixture_main,
)
from scripts.generate_test_fixture_index import (
    render_fixture_index,
    sync_or_check,
)


def _seed_rules_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".agents" / "rules").mkdir(parents=True)
    (repo / "docs" / "agent-playbooks").mkdir(parents=True)
    (repo / "AGENTS.md").write_text(
        "# Core\n- [R-CORE-01] Use .venv.\n",
        encoding="utf-8",
    )
    (repo / ".agents" / "rules" / "bmad-model-routing.md").write_text(
        "---\ntrigger: always_on\n---\n- [R-ROUTE-01] Route by tier.\n",
        encoding="utf-8",
    )
    (repo / "docs" / "agent-playbooks" / "coder.md").write_text(
        "# Coder\n- [R-CODE-01] Follow R-CORE-01.\n",
        encoding="utf-8",
    )
    return repo


def test_rules_lint_passes_valid_and_detects_oversize_includes_cycles_and_dupes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _seed_rules_repo(tmp_path)
    assert lint_agent_rules(repo) == []
    assert rules_main(["--root", str(repo)]) == 0
    assert "PASS" in capsys.readouterr().out

    # Expand @[label](path) include pushing AGENTS.md over 12 KB
    (repo / "docs" / "big.md").write_text("x" * (MAX_AGENTS_CORE_BYTES + 50), encoding="utf-8")
    (repo / "AGENTS.md").write_text(
        "# Core\n- [R-CORE-01] Rule.\n@[big](docs/big.md)\n",
        encoding="utf-8",
    )
    errors = lint_agent_rules(repo)
    assert any("12,288" in e or "AGENTS.md" in e for e in errors)

    # Always-on rule file > 20,480 B margin (< 24,000 B cap)
    (repo / "AGENTS.md").write_text("# Core\n- [R-CORE-01] Rule.\n", encoding="utf-8")
    (repo / ".agents" / "rules" / "extra.md").write_text(
        "y" * (MAX_RULE_FILE_BYTES + 10),
        encoding="utf-8",
    )
    assert any("extra.md" in e for e in lint_agent_rules(repo))
    (repo / ".agents" / "rules" / "extra.md").unlink()

    # Duplicate Rule ID across core and playbook
    (repo / "docs" / "agent-playbooks" / "coder.md").write_text(
        "# Coder\n- [R-CORE-01] Duplicate.\n",
        encoding="utf-8",
    )
    assert any("R-CORE-01" in e for e in lint_agent_rules(repo))

    # Truncation marker check
    (repo / "docs" / "agent-playbooks" / "coder.md").write_text(
        "# Coder\n- [R-CODE-01] Clean.\n",
        encoding="utf-8",
    )
    (repo / "AGENTS.md").write_text(
        "# Core\n- [R-CORE-01] <truncated 100 bytes>\n",
        encoding="utf-8",
    )
    assert any("truncated" in e.lower() for e in lint_agent_rules(repo))

    # Circular include detection
    (repo / "a.md").write_text("@[b](b.md)\n", encoding="utf-8")
    (repo / "b.md").write_text("@[a](a.md)\n", encoding="utf-8")
    with pytest.raises(RuleLintError, match="Circular"):
        expand_rule_includes(repo / "a.md", repo)

    # Missing include target and GEMINI.md symlink deduplication
    (repo / "GEMINI.md").symlink_to("AGENTS.md")
    (repo / "AGENTS.md").write_text(
        "# Core\n- [R-CORE-01] Ok.\n@[missing](file://docs/does-not-exist.md)\n",
        encoding="utf-8",
    )
    assert any("Missing rule include target" in e for e in lint_agent_rules(repo))
    assert rules_main(["--root", str(repo)]) == 1
    assert rules_main(["--root", str(tmp_path / "missing")]) == 1


def test_fixture_index_generation_determinism_and_check_mode(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "tests" / "unit" / "fakes").mkdir(parents=True)
    (repo / "tests" / "integration").mkdir(parents=True)
    (repo / "apps" / "web" / "src" / "__tests__" / "setup").mkdir(parents=True)

    (repo / "tests" / "conftest.py").write_text(
        '"""Global pytest fixtures."""\n\nimport pytest\n\n'
        "@pytest.fixture(scope='session')\ndef app_client():\n    return None\n",
        encoding="utf-8",
    )
    (repo / "tests" / "unit" / "fakes" / "in_memory_stores.py").write_text(
        '"""In-memory test doubles."""\n\nclass InMemoryStore:\n    pass\n'
        "def make_fake():\n    return None\n",
        encoding="utf-8",
    )
    (repo / "tests" / "integration" / "_tc_socket_helpers.py").write_text(
        '"""Testcontainers socket helpers."""\n\ndef open_pg18_alembic_container():\n    pass\n',
        encoding="utf-8",
    )
    (repo / "apps" / "web" / "src" / "__tests__" / "setup" / "mockState.ts").write_text(
        "// Shared Vitest mock state\nexport function resetMockState() {}\n"
        "export const DEFAULT_USER = 'admin';\n",
        encoding="utf-8",
    )
    (repo / "apps" / "web" / "src" / "__tests__" / "setup" / "manyExports.ts").write_text(
        "\n".join(f"export const EXP_{i} = {i};" for i in range(12)) + "\n",
        encoding="utf-8",
    )
    (repo / "tests" / "unit" / "fakes" / "broken_and_plain.py").write_text(
        "def helper():\n    return 1\n",
        encoding="utf-8",
    )
    (repo / "tests" / "unit" / "fakes" / "syntax_err.py").write_text(
        "def broken(:\n",
        encoding="utf-8",
    )

    assert sync_or_check(repo, check=True) == 1  # Missing tests/README.md
    assert fixture_main(["--root", str(repo)]) == 0
    readme = (repo / "tests" / "README.md").read_text(encoding="utf-8")
    assert "app_client" in readme
    assert "InMemoryStore" in readme
    assert "open_pg18_alembic_container" in readme
    assert "resetMockState" in readme
    assert "+2 more" in readme
    assert "Python test helper module." in readme
    assert fixture_main(["--root", str(repo), "--check"]) == 0
    assert render_fixture_index(repo) == readme

    (repo / "tests" / "README.md").write_text("stale\n", encoding="utf-8")
    assert fixture_main(["--root", str(repo), "--check"]) == 1


def test_static_gates_wires_rules_lint_and_fixture_index_and_receipts_hash_scripts(
    tmp_path: Path,
) -> None:
    (tmp_path / "scripts" / "agent_check_lib").mkdir(parents=True)
    (tmp_path / "scripts" / "agent_check.py").write_text("# cli\n", encoding="utf-8")
    (tmp_path / "scripts" / "agent_check_lib" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "scripts" / "check_agent_rules.py").write_text("# rules\n", encoding="utf-8")
    (tmp_path / "scripts" / "generate_test_fixture_index.py").write_text(
        "# index\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")

    env_info = ToolchainEnv(
        repo_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        python_bin=tmp_path / ".venv" / "bin" / "python",
        ruff_bin=tmp_path / ".venv" / "bin" / "ruff",
        mypy_bin=tmp_path / ".venv" / "bin" / "mypy",
        lint_imports_bin=tmp_path / ".venv" / "bin" / "lint-imports",
        pnpm_bin="pnpm",
        node_bin="node",
        pythonpath=str(tmp_path),
    )
    gates, _ = build_static_gates(env_info, touched_files=[], no_skip=False)
    names = [name for name, _ in gates]
    assert "rules-lint" in names
    assert "fixture-index" in names

    d1 = compute_worktree_digest(tmp_path, env_info, node_version="v22.0.0")
    (tmp_path / "scripts" / "check_agent_rules.py").write_text("# rules v2\n", encoding="utf-8")
    d2 = compute_worktree_digest(tmp_path, env_info, node_version="v22.0.0")
    assert d1 != d2
