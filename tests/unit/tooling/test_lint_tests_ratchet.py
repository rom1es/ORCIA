"""Unit tests for `scripts/lint_tests.py` (`T-D10` ratchet mode, `<= 250 L`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.lint_tests import main as lint_tests_main
from scripts.lint_tests import run_ratchet
from scripts.lint_tests_lib.checks import _has_fake_sql_engine_ast
from scripts.lint_tests_lib.diff_and_routes import check_removed_assertions

pytestmark = pytest.mark.story("32.3")
REPO_ROOT = Path(__file__).resolve().parents[3]


def _init_mini_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "mini_repo"
    (repo / "tests" / "unit").mkdir(parents=True)
    (repo / "apps" / "api" / "src" / "orcia_api" / "routers").mkdir(parents=True)
    (repo / "packages" / "orcia-core" / "src").mkdir(parents=True)
    (repo / "packages" / "orcia-core" / "src" / "core.py").write_text("x = 1\n", encoding="utf-8")
    ratchet = repo / "lint_tests_ratchet.json"
    ratchet.write_text(
        json.dumps(
            {
                "fake_sql_engine_files": ["tests/unit/test_legacy_fake.py"],
                "legacy_story_test_files": ["tests/unit/test_story_1_1_legacy.py"],
                "redundancy_audit_exempt_files": ["tests/unit/test_audited.py"],
                "unguarded_routes_allowlist": [
                    "apps/api/src/orcia_api/routers/legacy.py:legacy_route"
                ],
            }
        ),
        encoding="utf-8",
    )
    (repo / "tests" / "unit" / "test_legacy_fake.py").write_text(
        "class FakeSqlEngine:\n    pass\n", encoding="utf-8"
    )
    (repo / "tests" / "unit" / "test_story_1_1_legacy.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    (repo / "apps" / "api" / "src" / "orcia_api" / "routers" / "legacy.py").write_text(
        "@router.get('/ws/{workspace_id}')\ndef legacy_route(workspace_id: str):\n    return {}\n",
        encoding="utf-8",
    )
    return repo, ratchet


def test_ratchet_passes_when_only_allowlisted_legacy_exists(tmp_path: Path) -> None:
    repo, ratchet = _init_mini_repo(tmp_path)
    rc, lines = run_ratchet(repo, ratchet, strict=False, diff_text="")
    assert rc == 0
    assert any("INFO [lint-tests] proportionality:" in ln for ln in lines)
    assert any("PASS [lint-tests]: 0 ratchet violations" in ln for ln in lines)


def test_strict_default_ignores_fake_sql_and_redundancy_allowlists(tmp_path: Path) -> None:
    repo, ratchet = _init_mini_repo(tmp_path)
    diff_removed = "\n".join(
        [
            "diff --git a/tests/unit/test_audited.py b/tests/unit/test_audited.py",
            "--- a/tests/unit/test_audited.py",
            "+++ b/tests/unit/test_audited.py",
            "@@ -10,1 +10,0 @@",
            "-    assert ok is True",
        ]
    )
    rc, lines = run_ratchet(repo, ratchet, diff_text=diff_removed)
    assert rc == 1
    joined = "\n".join(lines)
    assert "[fake-sql]" in joined and "test_legacy_fake.py" in joined
    assert "[removed-assert]" in joined and "test_audited.py" in joined


def test_fake_sql_ast_catches_stub_and_mock_sql_without_inmemory_false_positive() -> None:
    assert _has_fake_sql_engine_ast("class _StubSqlSession:\n    pass\n") is True
    assert (
        _has_fake_sql_engine_ast("class _MockSqlRepo:\n    async def execute(self): ...\n") is True
    )
    assert _has_fake_sql_engine_ast("class _InMemoryRagStub:\n    def search(self): ...\n") is False
    assert _has_fake_sql_engine_ast("class _InMemorySqlStub:\n    def get(self): ...\n") is False


def test_ratchet_blocks_new_fake_sql_engine_and_new_story_file(tmp_path: Path) -> None:
    repo, ratchet = _init_mini_repo(tmp_path)
    (repo / "tests" / "unit" / "test_new_bad.py").write_text(
        "class _FakeEngine:\n    async def execute(self, sql):\n        return None\n",
        encoding="utf-8",
    )
    (repo / "tests" / "unit" / "test_story_99_1_bad.py").write_text(
        "def test_x():\n    assert True\n", encoding="utf-8"
    )
    rc, lines = run_ratchet(repo, ratchet, diff_text="")
    assert rc == 1
    joined = "\n".join(lines)
    assert "[fake-sql]" in joined and "test_new_bad.py" in joined
    assert "[story-filename]" in joined and "test_story_99_1_bad.py" in joined


def test_ratchet_blocks_removed_assertions_unless_redundancy_allowlisted() -> None:
    diff_removed = "\n".join(
        [
            "diff --git a/tests/unit/test_existing.py b/tests/unit/test_existing.py",
            "--- a/tests/unit/test_existing.py",
            "+++ b/tests/unit/test_existing.py",
            "@@ -10,1 +10,0 @@",
            "-    assert result == 42",
        ]
    )
    violations = check_removed_assertions(diff_removed, redundancy_audit_allowlist=set())
    assert len(violations) == 1
    assert "test_existing.py" in violations[0]

    # Refactoring 1 assert into 1 replacement assert is allowed
    diff_replaced = diff_removed + "\n+    assert result == 43\n"
    assert check_removed_assertions(diff_replaced, redundancy_audit_allowlist=set()) == []

    # Redundancy audit allowlist exempts pruned assertions in legacy ratchet mode only
    assert (
        check_removed_assertions(
            diff_removed, redundancy_audit_allowlist={"tests/unit/test_existing.py"}
        )
        == []
    )

    # Deleted file requires cumulative >= removed_cnt in new files within same directory
    diff_deleted_short = "\n".join(
        [
            "diff --git a/tests/unit/test_old.py b/tests/unit/test_old.py",
            "deleted file mode 100644",
            "-    assert a == 1",
            "-    assert b == 2",
            "diff --git a/tests/unit/test_split.py b/tests/unit/test_split.py",
            "new file mode 100644",
            "+    assert a == 1",
        ]
    )
    assert len(check_removed_assertions(diff_deleted_short, redundancy_audit_allowlist=set())) == 1
    diff_deleted_full = diff_deleted_short + "\n+    assert b == 2\n"
    assert check_removed_assertions(diff_deleted_full, redundancy_audit_allowlist=set()) == []


def test_ratchet_blocks_new_unguarded_route_and_allows_guarded_route(tmp_path: Path) -> None:
    repo, ratchet = _init_mini_repo(tmp_path)
    (repo / "apps" / "api" / "src" / "orcia_api" / "routers" / "new_routes.py").write_text(
        "@router.post('/runs/{run_id}')\n"
        "async def unguarded_run(run_id: str):\n"
        "    return {'run_id': run_id}\n\n"
        "@router.get('/ws/{workspace_id}')\n"
        "async def guarded_ws(workspace_id: str):\n"
        "    ScopeAccessGuard.check(workspace_id)\n"
        "    return {'workspace_id': workspace_id}\n",
        encoding="utf-8",
    )
    rc, lines = run_ratchet(repo, ratchet, diff_text="")
    assert rc == 1
    joined = "\n".join(lines)
    assert "new_routes.py:unguarded_run" in joined
    assert "guarded_ws" not in joined


def test_repo_ratchet_passes_live() -> None:
    rc, lines = run_ratchet(
        REPO_ROOT, REPO_ROOT / "scripts" / "lint_tests_ratchet.json", diff_text=""
    )
    assert rc == 0
    assert any("PASS [lint-tests]: 0 strict violations" in ln for ln in lines)


def test_lint_tests_cli_flags_on_mini_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, ratchet = _init_mini_repo(tmp_path)
    monkeypatch.setattr("scripts.lint_tests.collect_git_test_diff", lambda _root: "")
    rc_strict, _ = run_ratchet(repo, ratchet, strict=True, diff_text="")
    assert rc_strict == 1
    assert lint_tests_main(["--ratchet-file", str(ratchet)]) in (0, 1)
