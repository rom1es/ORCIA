"""Sequential Governance Guards & Anti-Injection Delimiters (`Story 26.6b`, `H-03`, `H-29`).

Implements:
- Step A: `PermissionBrokerService` (`passthrough` + `READ_SOURCE` + workspace scope/observer).
- Step B: Deterministic Lock V5 & per-tool Human-Anchor guard (zero lexical user-text heuristic).
- Step E: Secret scrubbing + `<untrusted_tool_output>` delimiter & prompt-tag neutralization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orcia_core.kernel.errors import OrciaDomainError
from orcia_core.kernel.events import HumanArbitrationRequested
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.permissions.broker import PermissionBrokerService
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolExecutionRequest,
    AuthorizedToolDescriptor,
)

_PROTECTED_ANCHOR_SECTIONS: frozenset[str] = frozenset({
    "intention-metier", "business-intent", "architecture-decision-rationale",
    "human-anchor", "primary-anchor",
})  # fmt: skip
_WRITE_ACTION_KEYWORDS: frozenset[str] = frozenset({
    "write", "create", "update", "delete", "transition", "publish",
    "deploy", "direct_si_write", "publish_v1_vault", "commit", "merge",
})  # fmt: skip


@dataclass(frozen=True, slots=True)
class ToolGuardVerdict:
    """Deterministic verdict returned by Step A or Step B governance guards."""

    allowed: bool
    reason_code: str = ""
    detail: str = ""
    requires_approval: bool = False
    approval_proposal: dict[str, Any] | None = None
    outbox_event: HumanArbitrationRequested | None = None


def _coerce_optional_uuid(raw_id: str | None) -> str | None:
    if not raw_id:
        return None
    from uuid import UUID

    try:
        return str(UUID(str(raw_id).strip()))
    except (ValueError, TypeError):
        return None


def resolve_target_uri_from_request(
    request: AssistantToolExecutionRequest, descriptor: AuthorizedToolDescriptor
) -> str:
    """Resolve target URI from structured tool arguments or descriptor metadata."""
    for key in ("target_uri", "resource_uri", "uri", "target_resource_uri"):
        val = request.arguments.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return descriptor.source_uri_or_scope.strip()


_ALLOWED_ROLES: frozenset[str] = frozenset(
    {
        "PLATFORM_ADMIN",
        "SECOPS",
        "BU_DIRECTOR",
        "BU_LEAD",
        "TEAM_LEAD",
        "ONTOLOGY_LEAD",
        "CONTRIBUTOR",
        "GATE_REVIEWER",
        "ONTOLOGY_STEWARD_L3",
        "OBSERVER",
    }
)


def _build_user_identity(request: AssistantToolExecutionRequest) -> UserIdentity:
    if isinstance(request.user_identity, UserIdentity):
        return request.user_identity
    role_raw = (request.user_role or "OBSERVER").strip().upper()
    role = role_raw if role_raw in _ALLOWED_ROLES else "OBSERVER"
    return UserIdentity(
        id=request.user_id,
        email=request.user_email or f"{request.user_id}@orcia.local",
        display_name=request.user_display_name or request.user_id,
        auth_mode="LOCAL",
        human_profile_archetype=request.active_hat or "ARCHITECT",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id="",
        roles=tuple(request.user_roles),
    )


async def evaluate_permission_broker_step(
    *,
    request: AssistantToolExecutionRequest,
    descriptor: AuthorizedToolDescriptor,
    permission_broker: PermissionBrokerService | None,
    evaluator: MatrixPermissionEvaluator | None,
) -> ToolGuardVerdict:
    """Step A: Enforce `passthrough` identity, workspace scope, `READ_SOURCE` & broker policy."""
    if request.execution_identity != "passthrough":
        return ToolGuardVerdict(
            allowed=False,
            reason_code="ERR_CONFUSED_DEPUTY_BLOCKED",
            detail="Assistant tools strictly require execution_identity='passthrough'.",
        )

    user = _build_user_identity(request)
    is_observer = user.platform_role in ("OBSERVER", "BU_DIRECTOR")
    if is_observer and (not descriptor.read_only or descriptor.required_permission == "execute"):
        return ToolGuardVerdict(
            allowed=False,
            reason_code="ERR_OBSERVER_MODE_READ_ONLY",
            detail="READ_ONLY_OBSERVER cannot execute skills or mutating tools.",
        )

    target_uri = resolve_target_uri_from_request(request, descriptor)
    if evaluator is not None and request.workspace_id not in ("", "scope-global"):
        ws = evaluator.get_workspace(request.workspace_id)
        if ws is None:
            return ToolGuardVerdict(
                allowed=False,
                reason_code="ERR_SCOPE_ACCESS_DENIED",
                detail=f"Workspace '{request.workspace_id}' is unknown or unauthorized.",
            )
        ws_access = evaluator.resolve_workspace_access(user, ws.id)
        if ws_access is None:
            return ToolGuardVerdict(
                allowed=False,
                reason_code="ERR_SCOPE_ACCESS_DENIED",
                detail=f"User lacks access to workspace '{request.workspace_id}'.",
            )
        if ws_access.access_mode == "READ_ONLY_OBSERVER" and (
            not descriptor.read_only or descriptor.required_permission == "execute"
        ):
            return ToolGuardVerdict(
                allowed=False,
                reason_code="ERR_OBSERVER_MODE_READ_ONLY",
                detail="Workspace READ_ONLY_OBSERVER mode forbids executing this tool.",
            )
        if target_uri:
            acl = evaluator.get_catalog_acl_by_uri(target_uri)
            if acl is not None:
                try:
                    eff, _ = evaluator.evaluate_catalog_resource(
                        user,
                        acl.resource_id,
                        workspace_id=ws.id,
                        require_read_source=True,
                    )
                    if not eff.can_read_source:
                        return ToolGuardVerdict(
                            allowed=False,
                            reason_code="ERR_READ_SOURCE_DENIED",
                            detail=f"READ_SOURCE denied for '{target_uri}'.",
                        )
                except OrciaDomainError as exc:
                    return ToolGuardVerdict(
                        allowed=False,
                        reason_code=exc.error_code,
                        detail=str(exc),
                    )

    is_external_scheme = "://" in target_uri and not target_uri.startswith(
        ("orcia://", "local://", "pack://")
    )
    if permission_broker is not None and is_external_scheme:
        try:
            outcome = await permission_broker.check_or_intercept_access_async(
                user,
                target_uri=target_uri,
                execution_identity="passthrough",
                step_key=descriptor.tool_name,
                step_number=max(1, request.iteration + 1),
                workspace_id=_coerce_optional_uuid(request.workspace_id),
                granted_external_roles=request.granted_external_roles,
                raise_on_denied=False,
                instance=f"assistant_tool:{descriptor.tool_name}",
            )
        except OrciaDomainError as exc:
            return ToolGuardVerdict(
                allowed=False,
                reason_code=exc.error_code,
                detail=str(exc),
            )
        if not outcome.allowed:
            hint = outcome.permission_broker_hint or f"Access denied for '{target_uri}'."
            return ToolGuardVerdict(
                allowed=False,
                reason_code="ERR_PERMISSION_BROKER_DENIED",
                detail=hint,
            )

    return ToolGuardVerdict(allowed=True)


def evaluate_v5_and_human_anchor_step(
    *,
    request: AssistantToolExecutionRequest,
    descriptor: AuthorizedToolDescriptor,
) -> ToolGuardVerdict:
    """Step B: Deterministic Lock V5 & per-tool Human-Anchor guard (`AD-3`, `AD-15`, `H-03`)."""
    args = request.arguments
    target_uri = resolve_target_uri_from_request(request, descriptor)
    section_key = str(args.get("section_key") or "").strip().lower()
    action_raw = str(args.get("action") or args.get("action_type") or "").strip().lower()

    is_human_anchor = bool(
        descriptor.human_authored_required
        or args.get("human_authored_required") is True
        or section_key in _PROTECTED_ANCHOR_SECTIONS
    )
    is_external_target = "://" in target_uri and not target_uri.startswith(
        ("orcia://", "local://", "pack://")
    )
    is_write_action = action_raw in _WRITE_ACTION_KEYWORDS or not descriptor.read_only
    is_si_write = bool(
        descriptor.is_si_write
        or args.get("is_si_write") is True
        or (is_write_action and is_external_target)
        or (action_raw in _WRITE_ACTION_KEYWORDS)
    )

    if not is_human_anchor and not is_si_write:
        return ToolGuardVerdict(allowed=True)

    reason_code = (
        "ERR_HUMAN_ANCHOR_REQUIRED"
        if is_human_anchor
        else "ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE"
    )
    arbitration_id = new_uuid7_str()
    proposal = {
        "transition_action": "CONTINUE_IN_PROCESS",
        "reason_code": reason_code,
        "arbitration_id": arbitration_id,
        "tool_call_id": request.tool_call_id,
        "tool_name": descriptor.tool_name,
        "target_uri": target_uri,
        "human_authored_required": is_human_anchor,
        "is_si_write": is_si_write,
        "requires_process_gate": True,
    }
    extra = {
        "turn_id": request.turn_id, "tool_call_id": request.tool_call_id,
        "reason_code": reason_code, "target_uri": target_uri,
        "transition_action": "CONTINUE_IN_PROCESS",
    }  # fmt: skip
    outbox_event = HumanArbitrationRequested.create(
        arbitration_id=arbitration_id,
        run_id=None,
        workspace_id=_coerce_optional_uuid(request.workspace_id),
        step_key=descriptor.tool_name,
        options_count=2,
        trace_id=request.trace_id or ("0" * 32),
        extra_payload=extra,
    )
    detail = (
        f"{reason_code}: Tool '{descriptor.tool_name}' cannot execute directly in chat; "
        "surface CONTINUE_IN_PROCESS human arbitration proposal."
    )
    return ToolGuardVerdict(
        allowed=False,
        reason_code=reason_code,
        detail=detail,
        requires_approval=True,
        approval_proposal=proposal,
        outbox_event=outbox_event,
    )


__all__ = [
    "ToolGuardVerdict",
    "evaluate_permission_broker_step",
    "evaluate_v5_and_human_anchor_step",
    "resolve_target_uri_from_request",
]
