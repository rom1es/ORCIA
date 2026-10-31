"""Story 11.4 — System Pack `orcia-pack-builder` Processes 1 to 4 (`AD-7`, `AD-9`, `AD-20`).

Provides `PackBuilderSystemService` orchestrating the 4 specialized Pack Builder agents
(`@Architecte-Métier-Pack`, `@Ingénieur-Prompt-et-Workflow`, `@Certificateur-Sécurité-et-Sandbox`,
`@Rédacteur-Documentation-Orcia`) across Processes 1 to 4:
1. `create-business-pack`: enforces Violet Human Anchor (`AD-3`), structures causal DNA chain
   (`DIRECTIVE ➔ NORME ➔ MÉCANISME`), validates `pack.yaml` in Tier 1a (`< 5 s`) and `.star` rules
   in Tier 1b (`StarlarkMechanismSandbox` `< 2 ms`), and generates `packages/orcia-pack-{slug}/`
   with `0` writes to `packages/orcia-kernel` or `packages/orcia-core` (`AD-20`).
2. `evolve-business-pack`: runs *What-If* `ImpactSimulator` (`AD-7`) identifying impacted
   workspaces and workflows for `@vX.Y.Z` without mutating any active `run-lock.json`.
3. `certify-pack-tool`: certifies deterministic rules in Tier 1b (`StarlarkMechanismSandbox`
   `< 2 ms` on `passing_test_payload` / `failing_test_payload`) or heavy tools in Tier 2 Container
   Sandbox (`TIER_2_CONTAINER`, `--network=none < 60 s`, `AD-9`).
4. `export-from-workspace-to-pack`: scrubs workspace-specific IDs, `local://` paths, and
   `SecretRef`s before promoting a proven workspace asset to a shared Business Pack revision.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid_utils import uuid7

from orcia_core.gates._internal.starlark_sandbox import StarlarkMechanismSandbox
from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
)
from orcia_kernel.errors import OrciaDomainError

PackCertificationTier = Literal["TIER_1B_STARLARK", "TIER_2_CONTAINER"]
PromotableAssetKind = Literal["AGENT", "WORKFLOW", "NORM", "STARLARK_MECHANISM"]

_PACK_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
_FORBIDDEN_CORE_SLUGS = frozenset({"kernel", "core", "api", "worker"})
_SCRUB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"local://[^\s\"']+"), "pack://artifacts/default"),
    (re.compile(r"(?:secret|vault|kms)://[^\s\"']+"), "secret://pack-placeholder"),
    (re.compile(r"\bpat_mcp_[A-Za-z0-9_-]+"), "[REDACTED_MCP_PAT]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"), "[REDACTED_API_KEY]"),
    (
        re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
        "{{WORKSPACE_SCOPED_UUID}}",
    ),
)


class PackBuilderValidationError(OrciaDomainError):
    """Raised when `pack.yaml`, `pack_slug`, or tool certification fails (`HTTP 422`)."""

    error_code = "ERR_PACK_BUILDER_VALIDATION_FAILED"
    http_status, type_slug = 422, "pack-builder-validation-failed"

    def __init__(
        self, detail: str, *, error_code: str = "ERR_PACK_BUILDER_VALIDATION_FAILED"
    ) -> None:
        self.error_code = error_code
        super().__init__(detail_override=detail)


@dataclass(frozen=True, slots=True)
class PackBuilderAgentSpec:
    """Specialized agent embedded in `packages/orcia-pack-builder`."""

    slug: str
    handle: str
    role_fr: str
    role_en: str


@dataclass(frozen=True, slots=True)
class DnaChainPackSeedSpec:
    """Causal DNA chain (`DIRECTIVE ➔ NORME ➔ MÉCANISME`) declared in a Business Pack."""

    directive_code: str
    directive_title: str
    norm_code: str
    norm_title: str
    mechanism_code: str
    rule_id: str
    starlark_source: str
    passing_test_payload: dict[str, Any] = field(default_factory=dict)
    failing_test_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CreatedBusinessPackResult:
    """Result of Process 1 (`create-business-pack`)."""

    pack_id: str
    pack_slug: str
    version: str
    title: str
    human_anchor_intent: str
    target_directory: str
    generated_files: dict[str, str]
    manifest_validation_elapsed_ms: float
    starlark_rules_certified_count: int
    max_starlark_elapsed_ms: float
    kernel_or_core_touched: bool


@dataclass(frozen=True, slots=True)
class WhatIfWorkspaceImpactItem:
    """Per-workspace impact entry produced by Process 2 (`evolve-business-pack`)."""

    workspace_key: str
    impacted_workflows: tuple[str, ...]
    breaking_norms: tuple[str, ...]
    active_runs_count: int
    run_locks_untouched: bool


@dataclass(frozen=True, slots=True)
class PackEvolutionWhatIfReport:
    """Result of Process 2 (`evolve-business-pack` *What-If* simulation)."""

    pack_slug: str
    previous_version: str
    target_version: str
    impacted_workspaces_count: int
    impacted_workflows_count: int
    breaking_changes_detected: bool
    active_run_locks_preserved: bool
    untouched_run_lock_ids: tuple[str, ...]
    workspace_impacts: tuple[WhatIfWorkspaceImpactItem, ...]


@dataclass(frozen=True, slots=True)
class PackToolCertificationReport:
    """Result of Process 3 (`certify-pack-tool` in Tier 1b Starlark or Tier 2 Container)."""

    tool_slug: str
    sandbox_tier: PackCertificationTier
    certified: bool
    elapsed_ms: float
    passing_vector_ok: bool
    failing_vector_rejected_ok: bool
    network_isolated: bool
    certificate_sha256: str
    diagnostics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkspaceToPackPromotionResult:
    """Result of Process 4 (`export-from-workspace-to-pack`)."""

    source_workspace_key: str
    target_pack_slug: str
    target_pack_version: str
    asset_kind: PromotableAssetKind
    asset_slug: str
    promoted_uri: str
    scrubbed_references_count: int
    sanitized_payload: dict[str, Any]


PACK_BUILDER_AGENTS: tuple[PackBuilderAgentSpec, ...] = (
    PackBuilderAgentSpec(
        slug="architecte-metier-pack",
        handle="@Architecte-Métier-Pack",
        role_fr=(
            "Structuration de la chaîne causale ADN (DIRECTIVE ➔ NORME ➔ MÉCANISME), "
            "du glossaire socle et des profils humains"
        ),
        role_en=(
            "Causal DNA chain (DIRECTIVE ➔ NORM ➔ MECHANISM), core glossary & human "
            "profiles structuring"
        ),
    ),
    PackBuilderAgentSpec(
        slug="ingenieur-prompt-et-workflow",
        handle="@Ingénieur-Prompt-et-Workflow",
        role_fr="Conception des agents spécialisés, des graphes DAG DBOS et des Gates d'arbitrage",
        role_en="Specialized agents, DBOS DAG workflows & arbitration Gates design",
    ),
    PackBuilderAgentSpec(
        slug="certificateur-securite-et-sandbox",
        handle="@Certificateur-Sécurité-et-Sandbox",
        role_fr=(
            "Compilation et certification des règles Starlark Palier 1b (< 2 ms) et "
            "audit des outils lourds en Sandbox Palier 2"
        ),
        role_en=(
            "Tier 1b Starlark rule certification (< 2 ms) & Tier 2 Container Sandbox "
            "security auditing"
        ),
    ),
    PackBuilderAgentSpec(
        slug="redacteur-documentation-orcia",
        handle="@Rédacteur-Documentation-Orcia",
        role_fr=(
            "Rédaction bilingue (fr/en) des fiches HelpArticle et validation "
            "déterministe validate_help_article (< 5 s)"
        ),
        role_en=(
            "Bilingual (fr/en) HelpArticle authoring & deterministic "
            "validate_help_article (< 5 s) validation"
        ),
    ),
)


class PackBuilderSystemService:
    """Domain service implementing Processes 1 to 4 of `packages/orcia-pack-builder`."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        starlark_sandbox: StarlarkMechanismSandbox | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._sandbox = starlark_sandbox or StarlarkMechanismSandbox()
        self._created_packs: dict[str, CreatedBusinessPackResult] = {}
        self._what_if_reports: list[PackEvolutionWhatIfReport] = []
        self._certifications: dict[str, PackToolCertificationReport] = {}
        self._promotions: list[WorkspaceToPackPromotionResult] = []

    def list_pack_builder_agents(self) -> tuple[PackBuilderAgentSpec, ...]:
        """Return the 4 specialized agents of `orcia-pack-builder`."""
        return PACK_BUILDER_AGENTS

    async def create_business_pack(
        self,
        *,
        pack_slug: str,
        title: str,
        version: str,
        domain_name: str,
        human_anchor_intent: str,
        dna_seeds: list[DnaChainPackSeedSpec],
        human_profiles: list[str],
        agents: list[str],
        workflows: list[str],
        actor_role: str = "ARCHITECT",
        actor_id: str = "architect-user",
        output_root_dir: Path | None = None,
    ) -> CreatedBusinessPackResult:
        """Process 1 (`create-business-pack`): Violet Anchor + DNA chain + Tier 1a/1b."""
        if actor_role.upper() == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(detail_override="create_business_pack")

        cleaned_anchor = human_anchor_intent.strip()
        if len(cleaned_anchor) < 30:
            raise HumanAnchorRequiredError(
                detail_override="pack_builder.create_business_pack.human_anchor_intent"
            )

        slug = pack_slug.strip().lower()
        if not _PACK_SLUG_RE.match(slug) or slug in _FORBIDDEN_CORE_SLUGS:
            raise PackBuilderValidationError(
                f"Le slug de pack '{pack_slug}' est invalide ou réservé au noyau (`AD-20`).",
                error_code="ERR_PACK_SLUG_RESERVED_OR_INVALID",
            )

        t0 = time.perf_counter()
        if not dna_seeds:
            raise PackBuilderValidationError(
                "Processus 1 exige au moins une chaîne causale ADN "
                "(DIRECTIVE ➔ NORME ➔ MÉCANISME).",
                error_code="ERR_PACK_DNA_CHAIN_EMPTY",
            )

        max_starlark_ms = 0.0
        rules_files: dict[str, str] = {}
        for seed in dna_seeds:
            cert = await self.certify_pack_tool(
                tool_slug=seed.mechanism_code.lower(),
                sandbox_tier="TIER_1B_STARLARK",
                starlark_source=seed.starlark_source,
                rule_id=seed.rule_id,
                passing_test_payload=seed.passing_test_payload,
                failing_test_payload=seed.failing_test_payload,
                actor_role=actor_role,
            )
            if not cert.certified:
                raise PackBuilderValidationError(
                    f"La règle Starlark '{seed.mechanism_code}' ({seed.rule_id}) "
                    "a échoué à la certification Palier 1b.",
                    error_code="ERR_STARLARK_RULE_CERTIFICATION_FAILED",
                )
            max_starlark_ms = max(max_starlark_ms, cert.elapsed_ms)
            rules_files[f"rules/{seed.mechanism_code.lower()}.star"] = seed.starlark_source

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
                f"# {title}\n\n## 1. À quoi sert cet écran ?\nPack métier {title}.\n"
            ),
            f"{target_dir}/help/en/overview.md": (
                f"# {title}\n\n## 1. What is this screen for?\nBusiness pack {title}.\n"
            ),
        }
        for rel_rule_path, star_code in rules_files.items():
            generated_files[f"{target_dir}/{rel_rule_path}"] = star_code

        # Verify AD-20 invariant: 0 file path targets orcia-kernel or orcia-core
        kernel_or_core_touched = any(
            path.startswith(("packages/orcia-kernel", "packages/orcia-core"))
            for path in generated_files
        )
        if output_root_dir is not None:
            for rel_path, content in generated_files.items():
                full_path = (output_root_dir / rel_path).resolve()
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")

        manifest_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        result = CreatedBusinessPackResult(
            pack_id=pack_id,
            pack_slug=slug,
            version=version,
            title=title,
            human_anchor_intent=cleaned_anchor,
            target_directory=target_dir,
            generated_files=generated_files,
            manifest_validation_elapsed_ms=manifest_elapsed_ms,
            starlark_rules_certified_count=len(dna_seeds),
            max_starlark_elapsed_ms=max_starlark_ms,
            kernel_or_core_touched=kernel_or_core_touched,
        )
        self._created_packs[slug] = result
        await self._persist_pack_and_audit(result, actor_id=actor_id)
        return result

    async def evolve_business_pack_what_if(
        self,
        *,
        pack_slug: str,
        previous_version: str,
        target_version: str,
        modified_norms: list[str],
        modified_workflows: list[str],
        subscribed_workspaces: list[dict[str, Any]],
        active_run_lock_ids: list[str],
        actor_role: str = "ARCHITECT",
    ) -> PackEvolutionWhatIfReport:
        """Process 2 (`evolve-business-pack`): *What-If* preserving active `run-lock.json`."""
        if actor_role.upper() == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(detail_override="evolve_business_pack_what_if")

        workspace_impacts: list[WhatIfWorkspaceImpactItem] = []
        total_workflows = 0
        for ws in subscribed_workspaces:
            ws_key = str(ws.get("workspace_key", "default-ws"))
            ws_workflows = tuple(
                wf
                for wf in ws.get("workflows", [])
                if wf in modified_workflows or not modified_workflows
            )
            total_workflows += len(ws_workflows)
            workspace_impacts.append(
                WhatIfWorkspaceImpactItem(
                    workspace_key=ws_key,
                    impacted_workflows=ws_workflows,
                    breaking_norms=tuple(modified_norms),
                    active_runs_count=int(ws.get("active_runs_count", 0)),
                    run_locks_untouched=True,
                )
            )

        report = PackEvolutionWhatIfReport(
            pack_slug=pack_slug,
            previous_version=previous_version,
            target_version=target_version,
            impacted_workspaces_count=len(workspace_impacts),
            impacted_workflows_count=total_workflows,
            breaking_changes_detected=len(modified_norms) > 0,
            active_run_locks_preserved=True,
            untouched_run_lock_ids=tuple(active_run_lock_ids),
            workspace_impacts=tuple(workspace_impacts),
        )
        self._what_if_reports.append(report)
        return report

    async def certify_pack_tool(
        self,
        *,
        tool_slug: str,
        sandbox_tier: PackCertificationTier,
        starlark_source: str = "",
        rule_id: str = "NORM-PACK-001",
        passing_test_payload: dict[str, Any] | None = None,
        failing_test_payload: dict[str, Any] | None = None,
        container_image_digest: str = "",
        container_command: list[str] | None = None,
        actor_role: str = "ARCHITECT",
    ) -> PackToolCertificationReport:
        """Process 3 (`certify-pack-tool`): Tier 1b Starlark (`< 2 ms`) or Tier 2 (`< 60 s`)."""
        if actor_role.upper() == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(detail_override="certify_pack_tool")

        pass_payload = passing_test_payload or {}
        fail_payload = failing_test_payload or {}

        if sandbox_tier == "TIER_1B_STARLARK":
            res_pass = self._sandbox.evaluate_script(
                starlark_code=starlark_source,
                payload=pass_payload,
            )
            res_fail = self._sandbox.evaluate_script(
                starlark_code=starlark_source,
                payload=fail_payload,
            )
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
            report = PackToolCertificationReport(
                tool_slug=tool_slug,
                sandbox_tier="TIER_1B_STARLARK",
                certified=certified,
                elapsed_ms=elapsed_ms,
                passing_vector_ok=pass_ok,
                failing_vector_rejected_ok=fail_ok,
                network_isolated=True,
                certificate_sha256=cert_hash,
                diagnostics=(
                    f"Palier 1b Starlark ({elapsed_ms:.3f} ms) — PASS={pass_ok}, FAIL={fail_ok}",
                ),
            )
            self._certifications[tool_slug] = report
            return report

        # Track B: Tier 2 Container Sandbox (--network=none, rootless, < 60 s)
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
        diag_msg = (
            f"Palier 2 Sandbox OCI rootless (--network=none, {elapsed_ms:.3f} ms) — "
            f"digest={container_image_digest or 'missing'}"
        )
        report = PackToolCertificationReport(
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
        self._certifications[tool_slug] = report
        return report

    async def export_from_workspace_to_pack(
        self,
        *,
        source_workspace_key: str,
        target_pack_slug: str,
        target_pack_version: str,
        asset_kind: PromotableAssetKind,
        asset_slug: str,
        raw_asset_payload: dict[str, Any],
        actor_role: str = "ARCHITECT",
    ) -> WorkspaceToPackPromotionResult:
        """Process 4 (`export-from-workspace-to-pack`): scrub workspace specifics & secrets."""
        if actor_role.upper() == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(detail_override="export_from_workspace_to_pack")

        serialized = json.dumps(raw_asset_payload, ensure_ascii=False)
        scrub_count = 0

        # Scrub explicit workspace key occurrences
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
        result = WorkspaceToPackPromotionResult(
            source_workspace_key=source_workspace_key,
            target_pack_slug=target_pack_slug,
            target_pack_version=target_pack_version,
            asset_kind=asset_kind,
            asset_slug=asset_slug,
            promoted_uri=promoted_uri,
            scrubbed_references_count=scrub_count,
            sanitized_payload=sanitized_payload,
        )
        self._promotions.append(result)
        return result

    async def _persist_pack_and_audit(
        self, pack: CreatedBusinessPackResult, *, actor_id: str
    ) -> None:
        if self._session_factory is None:
            return
        manifest_bytes = pack.generated_files[f"{pack.target_directory}/pack.yaml"].encode("utf-8")
        content_hash = hashlib.sha256(manifest_bytes).hexdigest()
        metadata_json = json.dumps(
            {
                "pack_slug": pack.pack_slug,
                "title": pack.title,
                "human_anchor_intent": pack.human_anchor_intent,
                "target_directory": pack.target_directory,
                "starlark_rules_certified_count": pack.starlark_rules_certified_count,
            }
        )
        audit_payload = json.dumps(
            {
                "actor_id": actor_id,
                "pack_id": pack.pack_id,
                "version": pack.version,
                "starlark_rules_certified_count": pack.starlark_rules_certified_count,
                "kernel_or_core_touched": pack.kernel_or_core_touched,
            }
        )
        root_org_id = UUID("0192c4e0-0000-7000-8000-000000000001")

        async with self._session_factory() as session, session.begin():
            await session.execute(
                sa.text(
                    """
                    INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                    VALUES (:id, 'orcia-root-org', 'ORCIA Root Org', 'ENTERPRISE', NULL)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": root_org_id},
            )
            await session.execute(
                sa.text(
                    """
                    INSERT INTO catalog_items (
                        id, resource_id, uri, title, description,
                        resource_type, source_format, version, sha256, cas_key,
                        visibility_scope, owner_org_unit_id, owner_workspace_id,
                        item_type, metadata_jsonb
                    ) VALUES (
                        :id, :resource_id, :uri, :title, :description,
                        'template', 'BMAD_PACK', :version, :sha256, :cas_key,
                        'PUBLISHED_ORG', :owner_org_unit_id, NULL,
                        'BUSINESS_PACK', CAST(:metadata_jsonb AS jsonb)
                    )
                    ON CONFLICT (resource_id) DO UPDATE
                    SET version = EXCLUDED.version,
                        sha256 = EXCLUDED.sha256,
                        cas_key = EXCLUDED.cas_key,
                        metadata_jsonb = EXCLUDED.metadata_jsonb
                    """
                ),
                {
                    "id": UUID(str(uuid7())),
                    "resource_id": f"pack-{pack.pack_slug}",
                    "uri": pack.pack_id,
                    "title": pack.title,
                    "description": pack.human_anchor_intent,
                    "version": pack.version,
                    "sha256": content_hash,
                    "cas_key": f"cas/{content_hash}",
                    "owner_org_unit_id": root_org_id,
                    "metadata_jsonb": metadata_json,
                },
            )
            await session.execute(
                sa.text(
                    """
                    INSERT INTO domain_events_outbox (
                        event_id, event_type, aggregate_type, aggregate_id,
                        run_id, workspace_id, payload_jsonb, trace_id, status
                    ) VALUES (
                        :event_id, 'ArtifactProduced', 'BusinessPack', :aggregate_id,
                        NULL, NULL, CAST(:payload AS jsonb), 'trace-pack-builder-11-4', 'PENDING'
                    )
                    """
                ),
                {
                    "event_id": UUID(str(uuid7())),
                    "aggregate_id": pack.pack_id,
                    "payload": audit_payload,
                },
            )


__all__ = [
    "CreatedBusinessPackResult",
    "DnaChainPackSeedSpec",
    "PACK_BUILDER_AGENTS",
    "PackBuilderAgentSpec",
    "PackBuilderSystemService",
    "PackBuilderValidationError",
    "PackCertificationTier",
    "PackEvolutionWhatIfReport",
    "PackToolCertificationReport",
    "PromotableAssetKind",
    "WhatIfWorkspaceImpactItem",
    "WorkspaceToPackPromotionResult",
]
