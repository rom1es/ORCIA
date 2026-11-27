"""Story 31.1 Layer 1a security, Starlark AST/DoS, and error catalog unit tests."""

from __future__ import annotations

import io
import stat
import time
import zipfile

import pytest
import yaml  # type: ignore[import-untyped]
from tests.unit.packs.test_story_31_1_apm_codec_and_security import (
    _build_zip_from_files,
    _sample_apm_files,
)

from orcia_api.errors._registry_classes import DOMAIN_ERROR_CLASSES
from orcia_core.packs import (
    ApmPackCodec,
    EntityReferencedByPackDraftError,
    PackBundleKind,
    PackClosureIncompleteError,
    PackExecutableHookForbiddenError,
    PackInvalidArchiveError,
    PackPiiOrInfraLeakError,
    PackSlotUnboundError,
    PackVersionConflictError,
    ResourcePinnedByActiveRunsError,
)
from orcia_kernel.errors import ERROR_CATALOG


@pytest.mark.parametrize(
    "bad_path",
    [
        "../outside.txt",
        "agents/../../etc/passwd",
        "/etc/passwd",
        "C:\\temp\\evil.yaml",
    ],
)
def test_apm_codec_rejects_zip_slip_and_symlinks(bad_path: str) -> None:
    codec = ApmPackCodec()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        zf.writestr("apm.yml", b"name: x\nversion: 1.0.0\n")
        zf.writestr(bad_path, b"evil")
    with pytest.raises(PackInvalidArchiveError):
        codec.decode_zip_bytes(buf.getvalue())

    sym_buf = io.BytesIO()
    with zipfile.ZipFile(sym_buf, mode="w") as zf:
        zf.writestr("apm.yml", b"name: x\nversion: 1.0.0\n")
        zinfo = zipfile.ZipInfo("agents/link.agent.md")
        zinfo.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(zinfo, "/etc/passwd")
    with pytest.raises(PackInvalidArchiveError, match="Symbolic link"):
        codec.decode_zip_bytes(sym_buf.getvalue())


def test_apm_codec_rejects_corrupt_zip_and_entry_limit() -> None:
    codec = ApmPackCodec()
    with pytest.raises(PackInvalidArchiveError, match="Corrupted ZIP"):
        codec.decode_zip_bytes(b"not-a-zip")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        zf.writestr("apm.yml", b"name: bomb\nversion: 1.0.0\n")
        for idx in range(505):
            zf.writestr(f"agents/a{idx}.agent.md", b"# a")
    with pytest.raises(PackInvalidArchiveError, match="entries limit"):
        codec.decode_zip_bytes(buf.getvalue())


@pytest.mark.parametrize(
    ("entry_path", "entry_bytes"),
    [
        ("scripts/install.txt", b"echo hi"),
        (".apm/hooks/pre_install.txt", b"echo hook"),
        ("hooks/post.md", b"hook"),
        ("agents/evil.py", b"import os"),
        ("skills/run/tool.sh", b"#!/bin/sh"),
        ("agents/runner.js", b"console.log(1)"),
        ("agents/native.wasm", b"\x00asm"),
        ("agents/script.rb", b"puts 1"),
        ("agents/script.php", b"<?php"),
        ("agents/shebang.md", b"#!/usr/bin/env python3\n"),
        ("agents/binary.md", b"\x7fELF\x02\x01"),
    ],
)
def test_apm_codec_fails_closed_on_executable_hooks_and_scripts(
    entry_path: str, entry_bytes: bytes
) -> None:
    codec = ApmPackCodec()
    files = {"apm.yml": b"name: hook-pack\nversion: 1.0.0\n", entry_path: entry_bytes}
    with pytest.raises(PackExecutableHookForbiddenError) as exc_info:
        codec.decode_zip_bytes(_build_zip_from_files(files))
    assert exc_info.value.http_status == 422
    assert exc_info.value.error_code == "ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN"


@pytest.mark.parametrize(
    "hook_key",
    ["hooks", "lifecycle_hooks", "pre_install", "post_install", "scripts", "shell", "exec"],
)
def test_apm_codec_rejects_forbidden_yaml_hook_keys(hook_key: str) -> None:
    codec = ApmPackCodec()
    files = {"apm.yml": f"name: yaml-hook\nversion: 1.0.0\n{hook_key}:\n  run: echo hi\n".encode()}
    with pytest.raises(PackExecutableHookForbiddenError) as exc_info:
        codec.decode_zip_bytes(_build_zip_from_files(files))
    assert exc_info.value.http_status == 422


@pytest.mark.parametrize(
    "bad_star",
    [
        "import os\ndef evaluate(p): pass\n",
        "def evaluate(p):\n    while True:\n        pass\n",
        "def evaluate(p):\n    return eval('1+1')\n",
        "def evaluate(p):\n    return p.__class__\n",
        "def evaluate(p):\n    return __builtins__\n",
        "def evaluate(p):\n    match 0:\n        case int(__class__=c):\n            return c\n",
        "def evaluate(p):\n    return 9**9**9\n",
        "def evaluate(p):\n    return [x for x in [1, 2]]\n",
        "def evaluate(p):\n    try:\n        pass\n    except* Exception:\n        pass\n",
        "def _hidden(p):\n    return 1\n",
        "def evaluate(_p):\n    return 1\n",
        "def evaluate(p):\n    return orcia_sys.assert_rule(_secret='x')\n",
        "def evaluate(p):\n    return 'a' * 1000000000\n",
        "def evaluate(p):\n    return f\"{'x':1000000000}\"\n",
        "def evaluate(p):\n    n = 10\n    return f\"{'x':{n}}\"\n",
        "def evaluate(p):\n    return 1e9\n",
        "def evaluate(p):\n    x = [1]\n    x[0] *= 2\n",
        f"def evaluate(p):\n    return '{'a' * 66000}'\n",
    ],
)
def test_apm_codec_rejects_unsafe_starlark_ast(bad_star: str) -> None:
    from orcia_core.gates import StarlarkMechanismSandbox, StarlarkSandboxError

    codec = ApmPackCodec()
    files = {
        "apm.yml": b"name: star-pack\nversion: 1.0.0\n",
        "ontology/mechanisms/bad.star": bad_star.encode("utf-8"),
    }
    with pytest.raises(PackInvalidArchiveError):
        codec.decode_zip_bytes(_build_zip_from_files(files))
    with pytest.raises(StarlarkSandboxError):
        StarlarkMechanismSandbox().evaluate_script(starlark_code=bad_star, payload={})


def test_apm_codec_rejects_system_or_global_upload_and_yaml_bombs() -> None:
    codec = ApmPackCodec()
    sys_files = {
        "apm.yml": (
            b"name: sys-spoof\nversion: 1.0.0\n"
            b"x-orcia:\n  bundle_kind: SYSTEM\n  scope_type: GLOBAL\n"
        )
    }
    zip_bytes = _build_zip_from_files(sys_files)
    with pytest.raises(PackInvalidArchiveError, match="SYSTEM bundle_kind"):
        codec.decode_zip_bytes(zip_bytes, allow_system_kind=False)
    allowed = codec.decode_zip_bytes(zip_bytes, allow_system_kind=True)
    assert allowed.manifest.bundle_kind == PackBundleKind.SYSTEM

    dup_yaml = {"apm.yml": b"name: dup\nname: dup2\nversion: 1.0.0\n"}
    with pytest.raises(PackInvalidArchiveError, match="duplicate key"):
        codec.decode_zip_bytes(_build_zip_from_files(dup_yaml))

    aliases = "\n".join(f"  k{i}: *a" for i in range(70))
    bomb_yaml = {
        "apm.yml": f"name: bomb\nversion: 1.0.0\nx-orcia:\n  anchor: &a x\n{aliases}\n".encode()
    }
    with pytest.raises(PackInvalidArchiveError, match="alias count"):
        codec.decode_zip_bytes(_build_zip_from_files(bomb_yaml))

    flow_aliases = ",".join("*a" for _ in range(70))
    flow_bomb_yaml = {
        "apm.yml": (
            f"name: flow-bomb\nversion: 1.0.0\nx-orcia:\n"
            f"  anchor: &a x\n  flow: [{flow_aliases}]\n".encode()
        )
    }
    with pytest.raises(PackInvalidArchiveError, match="alias count"):
        codec.decode_zip_bytes(_build_zip_from_files(flow_bomb_yaml))


def test_starlark_sandbox_trips_nested_for_loop_and_sequence_repetition_dos() -> None:
    from orcia_core.gates import StarlarkMechanismSandbox, StarlarkSandboxError

    nested_loop = (
        "def evaluate(p):\n"
        "    total = 0\n"
        "    for a in range(1000):\n"
        "        for b in range(1000):\n"
        "            total += 1\n"
        "    orcia_sys.assert_rule(rule_id='R', condition=total >= 0, message='ok')\n"
    )
    t0 = time.perf_counter()
    with pytest.raises(StarlarkSandboxError, match="Step cap exceeded"):
        StarlarkMechanismSandbox().evaluate_script(starlark_code=nested_loop, payload={})
    assert (time.perf_counter() - t0) * 1000.0 < 250.0

    for repeat_code in (
        "def evaluate(p):\n    return 'x' * 70000\n",
        "def evaluate(p):\n    n = 500000\n    s = 'a' * n\n",
        "def evaluate(p):\n    n = 500000\n    s = n * 'a'\n",
        "def evaluate(p):\n    s = 'a'\n    s *= 500000\n",
    ):
        with pytest.raises(StarlarkSandboxError, match="Sequence repetition"):
            StarlarkMechanismSandbox().evaluate_script(starlark_code=repeat_code, payload={})

    valid_repeat = (
        "def evaluate(p):\n"
        "    s = 'a' * 2\n"
        "    s *= 2\n"
        "    cond = len(s) == 4 and (2 * 3 == 6)\n"
        "    orcia_sys.assert_rule(rule_id='R', condition=cond, message='ok')\n"
    )
    assert StarlarkMechanismSandbox().evaluate_script(starlark_code=valid_repeat, payload={}).passed


def test_apm_codec_rejects_failing_starlark_test_vectors() -> None:
    codec = ApmPackCodec()
    files = _sample_apm_files(include_lock=False)
    files["ontology/mechanisms/check-title.yaml"] = yaml.safe_dump(
        {
            "mechanism_slug": "check-title",
            "name": "Title Length Check",
            "passing_test_payload": {"title": "No"},
        }
    ).encode("utf-8")
    with pytest.raises(PackInvalidArchiveError, match="passing_test_payload"):
        codec.decode_zip_bytes(_build_zip_from_files(files))


def test_pack_domain_errors_registered_with_bilingual_rfc9457_catalog() -> None:
    expected = [
        (PackExecutableHookForbiddenError, "ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN", 422),
        (PackInvalidArchiveError, "ERR_PACK_INVALID_ARCHIVE", 422),
        (PackVersionConflictError, "ERR_PACK_VERSION_CONFLICT", 409),
        (PackSlotUnboundError, "ERR_PACK_SLOT_UNBOUND", 422),
        (PackClosureIncompleteError, "ERR_PACK_CLOSURE_INCOMPLETE", 422),
        (PackPiiOrInfraLeakError, "ERR_PACK_PII_OR_INFRA_LEAK", 422),
        (ResourcePinnedByActiveRunsError, "ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS", 409),
        (EntityReferencedByPackDraftError, "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT", 409),
    ]
    for cls, code, status in expected:
        assert cls in DOMAIN_ERROR_CLASSES
        assert cls.error_code == code
        assert cls.http_status == status
        assert code in ERROR_CATALOG
        err = cls()
        assert err.localize("fr").title.strip()
        assert err.localize("en").title.strip()
        assert err.localize("fr").title != err.localize("en").title
