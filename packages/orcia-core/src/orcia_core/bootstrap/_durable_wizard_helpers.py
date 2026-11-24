"""Sanitization & step transition helper for durable onboarding wizards (`Story 8.6`)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from orcia_core.bootstrap._bootstrap_locales import DEMO_WORKSPACE_NAME_LOCALES
from orcia_core.bootstrap._durable_wizard_models import (
    DemoWorkspaceProvisionResult,
    WizardSessionRecord,
    WizardSessionRepositoryPort,
    WizardSessionStatus,
    _now_iso,
)
from orcia_core.permissions.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.platform_settings import SecretInputSpec
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale
from orcia_kernel.secret_ports import SecretProviderPort, SecretRef


def sanitize_and_store_wizard_step(
    secret_provider: SecretProviderPort,
    user: UserIdentity,
    session: WizardSessionRecord,
    *,
    step_index: int,
    step_payload: dict[str, Any],
    secret_input: SecretInputSpec | None,
    step_back: bool,
    instance: str | None,
) -> WizardSessionRecord:
    """Validate step payload (no plaintext secrets), persist SecretRef, and advance/step back."""
    if step_index < 1 or step_index > session.total_steps:
        raise ValidationDomainError(
            detail_override=f"step_index must be between 1 and {session.total_steps}.",
            instance=instance,
        )

    sanitized_payload: dict[str, Any] = {}
    for k, v in step_payload.items():
        low_k = k.lower()
        if any(tok in low_k for tok in ("password", "secret", "api_key", "private_key")):
            raise ValidationDomainError(
                detail_override=(
                    f"Plaintext secret key '{k}' is forbidden in wizard state_jsonb; "
                    "use secret_input (SecretProviderPort)."
                ),
                instance=instance,
            )
        sanitized_payload[k] = v

    if secret_input is not None and secret_input.action == "set":
        assert secret_input.plaintext_value is not None
        sec_ref = SecretRef(
            uri=f"secret://wizards/{session.id}/step-{step_index}",
            workspace_id=session.scope_id,
        )
        secret_provider.store_secret(sec_ref, secret_input.plaintext_value, actor_id=user.id)
        sanitized_payload["secret_ref_uri"] = sec_ref.uri

    merged_state = dict(session.state_jsonb)
    if step_back:
        if sanitized_payload:
            existing_step = merged_state.get(f"step_{step_index}")
            base_step = dict(existing_step) if isinstance(existing_step, dict) else {}
            merged_state[f"step_{step_index}"] = {**base_step, **sanitized_payload}
        prev_step = max(1, step_index - 1)
        return replace(
            session,
            current_step_index=prev_step,
            state_jsonb=merged_state,
            status="IN_PROGRESS",
            updated_at_iso=_now_iso(),
        )

    merged_state[f"step_{step_index}"] = {**sanitized_payload, "fail_fast_verified": True}
    completed = tuple(sorted({*session.completed_steps, step_index}))
    is_final = step_index >= session.total_steps
    next_step = session.total_steps if is_final else step_index + 1

    return replace(
        session,
        current_step_index=next_step,
        state_jsonb=merged_state,
        status="COMPLETED" if is_final else "IN_PROGRESS",
        completed_steps=completed,
        rag_reciprocity_verified=is_final or session.rag_reciprocity_verified,
        updated_at_iso=_now_iso(),
    )


def apply_discard_draft_or_abort(
    session: WizardSessionRecord,
    *,
    discard_draft_only: bool = True,
) -> WizardSessionRecord:
    """Remove unsaved draft keys or mark a wizard session ABANDONED."""
    cleaned_state = {k: v for k, v in session.state_jsonb.items() if not k.startswith("draft_")}
    next_status: WizardSessionStatus = session.status if discard_draft_only else "ABANDONED"
    return replace(
        session,
        state_jsonb=cleaned_state,
        status=next_status,
        updated_at_iso=_now_iso(),
    )


def build_demo_workspace_result(
    *,
    scope_id: str,
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> DemoWorkspaceProvisionResult:
    """Build localized DemoWorkspaceProvisionResult."""
    return DemoWorkspaceProvisionResult(
        workspace_id=scope_id,
        workspace_slug="demo-zero-empty-state",
        workspace_name=DEMO_WORKSPACE_NAME_LOCALES.get(
            locale, DEMO_WORKSPACE_NAME_LOCALES[DEFAULT_LOCALE]
        ),
        ontology_concepts_seeded=12,
        kb_documents_indexed=4,
        published_workflow_uri="orcia://catalog/workflows/architecture-review",
        rag_reciprocity_verified=True,
        plaintext_secrets_count=0,
    )


async def persist_discard_draft_or_abort_async(
    repository: WizardSessionRepositoryPort,
    current: WizardSessionRecord,
    *,
    session_id: str,
    discard_draft_only: bool,
    instance: str | None,
) -> WizardSessionRecord:
    """Apply draft discard/abort transition and persist to repository."""
    updated = apply_discard_draft_or_abort(current, discard_draft_only=discard_draft_only)
    persisted = await repository.update_session_state_async(
        session_id=session_id,
        state_jsonb=updated.state_jsonb,
        status=updated.status,
    )
    if persisted is None:
        raise ResourceNotFoundError(instance=instance)
    return persisted


__all__ = [
    "apply_discard_draft_or_abort",
    "build_demo_workspace_result",
    "persist_discard_draft_or_abort_async",
    "sanitize_and_store_wizard_step",
]
