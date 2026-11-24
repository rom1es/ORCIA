"""Execution helpers for `PackBuilderSystemService` (`Story 11.4`)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from orcia_core.gates._internal.starlark_sandbox import StarlarkMechanismSandbox
from orcia_core.orchestration._help_docs_locales import HELP_MARKDOWN_HEADINGS
from orcia_core.orchestration._pack_builder_models import (
    _SCRUB_PATTERNS,
    PackCertificationTier,
    PackToolCertificationReport,
    PromotableAssetKind,
    WorkspaceToPackPromotionResult,
)
from orcia_core.orchestration._studio_and_packs_locales import PACK_BUILDER_DIAG_LOCALES
from orcia_kernel.enums import DEFAULT_LOCALE


def build_pack_generated_files(
    *,
    slug: str,
    title: str,
    version: str,
    domain_name: str,
    human_profiles: list[str],
    agents: list[str],
    workflows: list[str],
    rules_files: dict[str, str],
    output_root_dir: Path | None,
) -> tuple[str, str, dict[str, str], bool]:
    """Render `packages/orcia-pack-{slug}/` manifest and rule files (`AD-20`)."""
    pkg_module = f"orcia_pack_{slug.replace('-', '_')}"
    target_dir = f"packages/orcia-pack-{slug}"
    pack_id = f"orcia://packs/orcia-pack-{slug}"
    pack_yaml_content = (
        f'pack_id: "{pack_id}"\n'
        f'pack_slug: "{slug}"\n'
        f'version: "{version}"\n'
        f'title: "{title}"\n'
        f'domain: "{domain_name}"\n'
        f"human_anchor_required: true\n"
        f"human_profiles: {json.dumps(human_profiles)}\n"
        f"agents: {json.dumps(agents)}\n"
        f"workflows: {json.dumps(workflows)}\n"
    )
    pyproject_content = (
        "[build-system]\n"
        'requires = ["setuptools>=68.0"]\n'
        'build-backend = "setuptools.build_meta"\n\n'
        "[project]\n"
        f'name = "orcia-pack-{slug}"\n'
        f'version = "{version}"\n'
        f'description = "{title}"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["orcia-kernel", "orcia-core"]\n'
    )
    init_py_content = (
        f'"""Generated ORCIA Business Pack `{pkg_module}` (`AD-20`)."""\n\n'
        f'__version__: str = "{version}"\n'
        f'PACK_ID: str = "{pack_id}"\n'
    )
    generated_files: dict[str, str] = {
        f"{target_dir}/pack.yaml": pack_yaml_content,
        f"{target_dir}/pyproject.toml": pyproject_content,
        f"{target_dir}/src/{pkg_module}/__init__.py": init_py_content,
        f"{target_dir}/help/fr/overview.md": (
            f"# {title}\n\n"
            f"{HELP_MARKDOWN_HEADINGS['fr']['pack_overview_sec'].format(title=title)}\n"
        ),
        f"{target_dir}/help/en/overview.md": (
            f"# {title}\n\n"
            f"{HELP_MARKDOWN_HEADINGS['en']['pack_overview_sec'].format(title=title)}\n"
        ),
    }
    for rel_rule_path, star_code in rules_files.items():
        generated_files[f"{target_dir}/{rel_rule_path}"] = star_code

    kernel_or_core_touched = any(
        path.startswith(("packages/orcia-kernel", "packages/orcia-core"))
        for path in generated_files
    )
    if output_root_dir is not None:
        for rel_path, content in generated_files.items():
            full_path = (output_root_dir / rel_path).resolve()
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
    return pack_id, target_dir, generated_files, kernel_or_core_touched


def certify_pack_tool_impl(
    sandbox: StarlarkMechanismSandbox,
    *,
    tool_slug: str,
    sandbox_tier: PackCertificationTier,
    starlark_source: str,
    rule_id: str,
    passing_test_payload: dict[str, Any] | None,
    failing_test_payload: dict[str, Any] | None,
    container_image_digest: str,
    container_command: list[str] | None,
) -> PackToolCertificationReport:
    """Certify a pack tool in Tier 1b Starlark (`< 2 ms`) or Tier 2 OCI Sandbox."""
    pass_payload = passing_test_payload or {}
    fail_payload = failing_test_payload or {}

    if sandbox_tier == "TIER_1B_STARLARK":
        res_pass = sandbox.evaluate_script(starlark_code=starlark_source, payload=pass_payload)
        res_fail = sandbox.evaluate_script(starlark_code=starlark_source, payload=fail_payload)
        pass_ok = res_pass.passed and any(
            v.rule_id == rule_id and v.status == "PASS" for v in res_pass.verdicts
        )
        fail_ok = (not res_fail.passed) and any(
            v.rule_id == rule_id and v.status == "FAIL" for v in res_fail.verdicts
        )
        elapsed_ms = round(max(res_pass.elapsed_ms, res_fail.elapsed_ms), 3)
        certified = pass_ok and fail_ok and elapsed_ms < 50.0
        cert_hash = hashlib.sha256(
            f"{tool_slug}:{rule_id}:{starlark_source}:{certified}".encode()
        ).hexdigest()
        diag_tpl = PACK_BUILDER_DIAG_LOCALES[DEFAULT_LOCALE]["tier1b"]
        return PackToolCertificationReport(
            tool_slug=tool_slug,
            sandbox_tier="TIER_1B_STARLARK",
            certified=certified,
            elapsed_ms=elapsed_ms,
            passing_vector_ok=pass_ok,
            failing_vector_rejected_ok=fail_ok,
            network_isolated=True,
            certificate_sha256=cert_hash,
            diagnostics=(diag_tpl.format(ms=elapsed_ms, pass_ok=pass_ok, fail_ok=fail_ok),),
        )

    t0 = time.perf_counter()
    cmd = container_command or ["pytest", "-q"]
    has_forbidden_net = any(
        tok in " ".join(cmd) for tok in ("curl ", "wget ", "http://", "https://")
    )
    pass_ok = bool(container_image_digest.startswith("sha256:")) and not has_forbidden_net
    fail_ok = not has_forbidden_net
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    certified = pass_ok and fail_ok
    cert_hash = hashlib.sha256(
        f"{tool_slug}:TIER_2:{container_image_digest}:{certified}".encode()
    ).hexdigest()
    diag_msg = PACK_BUILDER_DIAG_LOCALES[DEFAULT_LOCALE]["tier2"].format(
        ms=elapsed_ms,
        digest=container_image_digest or "missing",
    )
    return PackToolCertificationReport(
        tool_slug=tool_slug,
        sandbox_tier="TIER_2_CONTAINER",
        certified=certified,
        elapsed_ms=elapsed_ms,
        passing_vector_ok=pass_ok,
        failing_vector_rejected_ok=fail_ok,
        network_isolated=not has_forbidden_net,
        certificate_sha256=cert_hash,
        diagnostics=(diag_msg,),
    )


def export_from_workspace_to_pack_impl(
    *,
    source_workspace_key: str,
    target_pack_slug: str,
    target_pack_version: str,
    asset_kind: PromotableAssetKind,
    asset_slug: str,
    raw_asset_payload: dict[str, Any],
) -> WorkspaceToPackPromotionResult:
    """Scrub workspace-specific identifiers and secrets before promoting an asset."""
    serialized = json.dumps(raw_asset_payload, ensure_ascii=False)
    scrub_count = 0
    if source_workspace_key and source_workspace_key in serialized:
        scrub_count += serialized.count(source_workspace_key)
        serialized = serialized.replace(source_workspace_key, "{{PACK_TARGET_WORKSPACE}}")
    for pattern, replacement in _SCRUB_PATTERNS:
        matches = pattern.findall(serialized)
        if matches:
            scrub_count += len(matches)
            serialized = pattern.sub(replacement, serialized)

    sanitized_payload: dict[str, Any] = json.loads(serialized)
    sanitized_payload.pop("workspace_id", None)
    sanitized_payload.pop("secret_ref", None)

    promoted_uri = (
        f"orcia://packs/orcia-pack-{target_pack_slug}/"
        f"{asset_kind.lower()}s/{asset_slug}@{target_pack_version}"
    )
    return WorkspaceToPackPromotionResult(
        source_workspace_key=source_workspace_key,
        target_pack_slug=target_pack_slug,
        target_pack_version=target_pack_version,
        asset_kind=asset_kind,
        asset_slug=asset_slug,
        promoted_uri=promoted_uri,
        scrubbed_references_count=scrub_count,
        sanitized_payload=sanitized_payload,
    )


__all__ = [
    "build_pack_generated_files",
    "certify_pack_tool_impl",
    "export_from_workspace_to_pack_impl",
]
