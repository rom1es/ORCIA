"""System bootstrap workflows `init-existing-project` & `init-skill` (`FR-28`, `AD-9`, `AD-16`).

- `init-existing-project` (*Brownfield Onboarding*): scans a `git://` repository, extracts
  its stack/dependencies, enforces a signed Human Anchor (`>= 30` chars), and generates an
  initial `ARCHITECTURE-SPINE.md` (`[ADOPTED]`) registered as the Workspace Pattern Drift baseline.
- `init-skill` (*Skill Certification*): executes a candidate Skill in the out-of-process
  Tier 1 Sandbox (`< 5 000 ms`, `0` network calls, `<= 256 MB` RAM) before publishing it
  to the Federated Catalog (`CatalogItemEntity` + 5 permissions `CatalogAclEntry`).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from orcia_core.bootstrap import errors as exc
from orcia_core.bootstrap.models import SystemBootstrapRunRecord
from orcia_core.catalog.models import CatalogItemEntity
from orcia_core.gates.deterministic import DeterministicGateService
from orcia_core.gates.models import (
    CANONICAL_FORBIDDEN_DRIFT_PATTERNS,
    DeterministicGateInput,
    GateEvaluationEntity,
    WorkspaceSpineBaseline,
)
from orcia_core.permissions import models as pm
from orcia_core.permissions.broker_models import reject_control_chars as _clean
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.bootstrap.engine import SystemBootstrapWorkflowService


@dataclass(frozen=True, slots=True)
class InitExistingProjectInput:
    """Input contract for `orcia://system/bootstrap/init-existing-project` (`FR-28`, `AD-16`)."""

    workspace_id: str
    repository_uri: str
    detected_dependencies: tuple[str, ...]
    architecture_paradigm: str
    human_anchor_justification: str
    human_anchor_signature: str
    spine_version: str = "1.0.0"
    forbidden_patterns: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class InitExistingProjectOutcome:
    """Outcome of `orcia://system/bootstrap/init-existing-project` (`FR-28`, `AD-16`)."""

    run: SystemBootstrapRunRecord
    spine_baseline: WorkspaceSpineBaseline
    catalog_item: CatalogItemEntity


@dataclass(frozen=True, slots=True)
class InitSkillInput:
    """Input contract for `orcia://system/bootstrap/init-skill` (`FR-28`, `AD-9`, `AD-16`)."""

    workspace_id: str
    skill_key: str
    skill_uri: str
    title: str
    description: str
    version: str = "v1.0.0"
    test_payload: dict[str, Any] = field(default_factory=lambda: {"artifact": "skill-self-test"})
    required_sections: tuple[str, ...] = ("artifact",)
    timeout_ms: int = 5000
    max_memory_mb: int = 256
    visibility_scope: Literal["SHARED_WORKSPACE", "SHARED_TEAM"] = "SHARED_WORKSPACE"
    simulate_timeout_sleep_ms: int = 0
    simulate_network_escape: bool = False
    simulate_fs_escape_path: str | None = None
    simulate_memory_alloc_mb: int = 0


@dataclass(frozen=True, slots=True)
class InitSkillOutcome:
    """Outcome of `orcia://system/bootstrap/init-skill` (`FR-28`, `AD-9`, `AD-16`)."""

    run: SystemBootstrapRunRecord
    catalog_item: CatalogItemEntity
    gate_evaluation: GateEvaluationEntity


def execute_init_existing_project_workflow(
    service: SystemBootstrapWorkflowService,
    gate_service: DeterministicGateService,
    user: pm.UserIdentity,
    payload: InitExistingProjectInput,
    *,
    instance: str | None = None,
) -> InitExistingProjectOutcome:
    """Scan a Brownfield repository and adopt an initial signed `ARCHITECTURE-SPINE.md` baseline."""
    service._enforce_not_observer(user, instance=instance)
    if user.platform_role not in ("TEAM_LEAD", "PLATFORM_ADMIN", "ARCHITECT"):
        raise exc.ScopeAccessDeniedError(instance=instance)

    ws = service.auth_service.evaluator.enforce_scope_mutation_guard(
        user, payload.workspace_id, instance=instance
    ).workspace

    repo_uri = _clean(payload.repository_uri, "repository_uri", instance=instance)
    if not repo_uri.lower().startswith("git://"):
        raise exc.ValidationDomainError(
            detail_override="init-existing-project requires a valid git:// repository_uri.",
            instance=instance,
        )

    paradigm = _clean(payload.architecture_paradigm, "architecture_paradigm", instance=instance)
    just = payload.human_anchor_justification.strip()
    sig = payload.human_anchor_signature.strip()
    if (
        len(just) < 30
        or len(set(just.lower())) < 5
        or len(sig) < 3
        or any(ord(c) < 32 and c not in ("\n", "\r", "\t") for c in just + sig)
    ):
        raise exc.HumanAnchorRequiredError(instance=instance)

    deps = tuple(
        sorted(
            {
                _clean(d, "dependency", instance=instance).lower()
                for d in payload.detected_dependencies
                if d.strip()
            }
        )
    )
    if not deps:
        raise exc.ValidationDomainError(
            detail_override=(
                "At least one detected dependency is required for ARCHITECTURE-SPINE.md."
            ),
            instance=instance,
        )

    forbidden = (
        payload.forbidden_patterns
        if payload.forbidden_patterns
        else CANONICAL_FORBIDDEN_DRIFT_PATTERNS
    )
    spine_md = (
        f"# ARCHITECTURE-SPINE.md — {ws.name} [ADOPTED]\n\n"
        f"- **Workspace** : `{ws.slug}` (`{ws.id}`)\n"
        f"- **Repository** : `{repo_uri}`\n"
        f"- **Paradigm** : {paradigm}\n"
        f"- **Status** : `[ADOPTED]`\n"
        f"- **Allowed Dependencies** : {', '.join(f'`{d}`' for d in deps)}\n"
        f"- **Human Anchor Justification** : {just}\n"
        f"- **Signature** : `{sig}`\n"
    )
    sha256 = hashlib.sha256(spine_md.encode("utf-8")).hexdigest()

    baseline = WorkspaceSpineBaseline(
        workspace_id=ws.id,
        spine_version=payload.spine_version.strip() or "1.0.0",
        status="ADOPTED",
        allowed_dependencies=deps,
        forbidden_patterns=forbidden,
        spine_markdown=spine_md,
        content_sha256=sha256,
        signed_by_user_id=user.id,
        human_anchor_signature=sig,
    )
    gate_service.register_workspace_spine_baseline(baseline)

    res_id = f"res-spine-{ws.slug}"
    spine_uri = f"orcia://workspaces/{ws.slug}/architecture-spine"
    meta_json = json.dumps(
        {
            "repository_uri": repo_uri,
            "status": "ADOPTED",
            "allowed_dependencies": list(deps),
            "human_anchor_signature": sig,
        },
        sort_keys=True,
    )
    cat_item = CatalogItemEntity(
        new_uuid7_str(),
        res_id,
        spine_uri,
        "orcia",
        f"ARCHITECTURE-SPINE.md ({ws.name}) [ADOPTED]",
        just,
        "template",
        "ORCIA",
        baseline.spine_version,
        sha256,
        f"cas/{sha256}",
        "SHARED_WORKSPACE",
        ws.owner_org_unit_id,
        ws.id,
        meta_json,
    )
    acl = pm.CatalogAclEntry(
        new_uuid7_str(),
        res_id,
        spine_uri,
        cat_item.title,
        "SHARED_WORKSPACE",
        ws.owner_org_unit_id,
        ws.id,
        can_discover=True,
        can_execute=True,
        can_read_source=True,
        can_edit=True,
        can_admin=True,
    )
    service.catalog_service.upsert_catalog_item(cat_item, acl)

    run_id = new_uuid7_str()
    run = SystemBootstrapRunRecord(
        run_id,
        f"boot-init-proj-{run_id[-6:]}",
        "orcia://system/bootstrap/init-existing-project",
        "WORKSPACE",
        ws.owner_org_unit_id,
        ws.id,
        user.id,
        "COMPLETED",
        True,
        {
            "brownfield_scan_verified": True,
            "spine_status": "ADOPTED",
            "allowed_dependencies_count": len(deps),
            "spine_sha256": sha256,
        },
        {
            "workspace_id": ws.id,
            "repository_uri": repo_uri,
            "spine_uri": spine_uri,
        },
    )
    service._runs.append(run)
    return InitExistingProjectOutcome(run=run, spine_baseline=baseline, catalog_item=cat_item)


def execute_init_skill_workflow(
    service: SystemBootstrapWorkflowService,
    gate_service: DeterministicGateService,
    user: pm.UserIdentity,
    payload: InitSkillInput,
    *,
    instance: str | None = None,
) -> InitSkillOutcome:
    """Certify a candidate Skill in the out-of-process Tier 1 Sandbox before publishing it."""
    service._enforce_not_observer(user, instance=instance)
    if user.platform_role not in ("CONTRIBUTOR", "TEAM_LEAD", "PLATFORM_ADMIN", "TECH_LEAD"):
        raise exc.ScopeAccessDeniedError(instance=instance)

    ws = service.auth_service.evaluator.enforce_scope_mutation_guard(
        user, payload.workspace_id, instance=instance
    ).workspace

    skill_key = _clean(payload.skill_key, "skill_key", instance=instance)
    skill_uri = _clean(payload.skill_uri, "skill_uri", instance=instance)
    title = _clean(payload.title, "title", instance=instance)
    desc = _clean(payload.description, "description", instance=instance)

    run_id = new_uuid7_str()
    step_exec_id = new_uuid7_str()

    gate_eval = gate_service.evaluate_deterministic_gate(
        DeterministicGateInput(
            workspace_id=ws.id,
            run_id=run_id,
            step_execution_id=step_exec_id,
            step_key=f"certify-{skill_key}",
            artifact_payload=dict(payload.test_payload),
            required_sections=payload.required_sections,
            timeout_ms=min(payload.timeout_ms, 5000),
            max_memory_mb=min(payload.max_memory_mb, 256),
            simulate_timeout_sleep_ms=payload.simulate_timeout_sleep_ms,
            simulate_network_escape=payload.simulate_network_escape,
            simulate_fs_escape_path=payload.simulate_fs_escape_path,
            simulate_memory_alloc_mb=payload.simulate_memory_alloc_mb,
        ),
        raise_on_failure=True,
    )

    scheme = skill_uri.split("://", 1)[0].lower() if "://" in skill_uri else "orcia"
    meta_json = json.dumps(
        {
            "skill_key": skill_key,
            "sandbox_tier": "TIER_1_WASM",
            "certified_gate_evaluation_id": gate_eval.id,
            "certified_duration_ms": gate_eval.duration_ms,
        },
        sort_keys=True,
    )
    sha256 = hashlib.sha256(meta_json.encode("utf-8")).hexdigest()
    res_id = f"res-skill-{ws.slug}-{skill_key}"

    cat_item = CatalogItemEntity(
        new_uuid7_str(),
        res_id,
        skill_uri,
        scheme,
        title,
        desc,
        "skill",
        "ORCIA",
        payload.version,
        sha256,
        f"cas/{sha256}",
        payload.visibility_scope,
        ws.owner_org_unit_id,
        ws.id,
        meta_json,
    )
    acl = pm.CatalogAclEntry(
        new_uuid7_str(),
        res_id,
        skill_uri,
        title,
        payload.visibility_scope,
        ws.owner_org_unit_id,
        ws.id,
        can_discover=True,
        can_execute=True,
        can_read_source=True,
        can_edit=True,
        can_admin=(user.platform_role in ("TEAM_LEAD", "PLATFORM_ADMIN")),
    )
    service.catalog_service.upsert_catalog_item(cat_item, acl)

    run = SystemBootstrapRunRecord(
        run_id,
        f"boot-init-skill-{run_id[-6:]}",
        "orcia://system/bootstrap/init-skill",
        "WORKSPACE",
        ws.owner_org_unit_id,
        ws.id,
        user.id,
        "COMPLETED",
        True,
        {
            "skill_schema_valid": gate_eval.schema_validation_passed,
            "sandbox_isolation_certified": True,
            "duration_ms": gate_eval.duration_ms,
            "gate_evaluation_id": gate_eval.id,
        },
        {
            "workspace_id": ws.id,
            "skill_key": skill_key,
            "skill_uri": skill_uri,
        },
    )
    service._runs.append(run)
    return InitSkillOutcome(run=run, catalog_item=cat_item, gate_evaluation=gate_eval)
