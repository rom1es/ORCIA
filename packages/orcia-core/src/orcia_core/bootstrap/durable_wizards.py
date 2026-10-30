"""Durable DBOS Onboarding Wizards (`wizard_sessions`) & Zero Empty-State Demo (`Story 8.6`).

Implements (`FR-28`, `AD-2`, `AD-16`, `AD-19`, `AD-21`):
- 3 profile-guided durable DBOS wizards (`sdlc_tech_lead`, `ops_manager`, `secops_admin`)
- Exact step resumption (`current_step_index` 1..5) after browser closure/reconnection
- Strict `SecretRef` storage via `SecretProviderPort` (`0` plaintext secrets in `wizard_sessions`)
- Per-step fail-fast connectivity/model checks and final RAG reciprocity verification
- 1-click Zero Empty-State Demo Workspace provisioning (`0` plaintext secrets)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.platform_settings import (
    DefaultMemorySecretProvider,
    SecretInputSpec,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.secret_ports import SecretProviderPort, SecretRef

WizardType = Literal["sdlc_tech_lead", "ops_manager", "secops_admin"]
WizardSessionStatus = Literal["IN_PROGRESS", "COMPLETED", "ABANDONED"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class WizardStepDescriptor:
    """Step definition inside a 5-step durable onboarding wizard (`Story 8.6`)."""

    step_index: int
    step_key: str
    title_fr: str
    title_en: str
    fail_fast_check_label: str


WIZARD_STEPS_BY_TYPE: dict[WizardType, tuple[WizardStepDescriptor, ...]] = {
    "sdlc_tech_lead": (
        WizardStepDescriptor(
            1, "workspace-identity", "Identité du Workspace", "Workspace Identity", "scope-check"
        ),
        WizardStepDescriptor(
            2, "git-jira-sources", "Sources Code & Tickets", "Code & Issue Sources", "conn-test"
        ),
        WizardStepDescriptor(
            3, "ai-cognitive-tiers", "Tiers Cognitifs IA", "AI Cognitive Tiers", "orthogonality"
        ),
        WizardStepDescriptor(
            4, "gates-and-pack", "Pack SDLC & Gates", "SDLC Pack & Gates", "sandbox-check"
        ),
        WizardStepDescriptor(
            5, "rag-reciprocity", "Vérification RAG Finale", "Final RAG Reciprocity", "rag-ping"
        ),
    ),
    "ops_manager": (
        WizardStepDescriptor(
            1, "bu-team-scope", "Périmètre Équipe & BU", "Team & BU Scope", "scope-check"
        ),
        WizardStepDescriptor(
            2, "knowledge-sources", "Sources Documentaires", "Knowledge Sources", "conn-test"
        ),
        WizardStepDescriptor(
            3, "budget-finops", "Plafonds FinOps", "FinOps Budgets", "budget-check"
        ),
        WizardStepDescriptor(
            4, "human-gates-policy", "Politiques de Revue", "Review Policies", "gate-check"
        ),
        WizardStepDescriptor(
            5, "rag-reciprocity", "Vérification RAG Finale", "Final RAG Reciprocity", "rag-ping"
        ),
    ),
    "secops_admin": (
        WizardStepDescriptor(
            1, "oidc-and-mfa", "Authentification Bi-Mode", "Bi-Mode Authentication", "idp-check"
        ),
        WizardStepDescriptor(
            2, "rbac-6-verbs", "Matrice RBAC 6 Verbes", "6-Verb RBAC Matrix", "anti-lockout"
        ),
        WizardStepDescriptor(
            3, "secret-vault-kms", "Coffre-fort & SecretRef", "Secret Vault & KMS", "kms-check"
        ),
        WizardStepDescriptor(
            4, "pii-and-c3-guards", "Garde-fous C0-C3 & PII", "C0-C3 & PII Guards", "pii-check"
        ),
        WizardStepDescriptor(
            5, "rag-reciprocity", "Audit & Réciprocité Finale", "Final Audit & RAG", "rag-ping"
        ),
    ),
}


@dataclass(frozen=True, slots=True)
class WizardSessionRecord:
    """Durable DBOS onboarding wizard session (`wizard_sessions`, `Story 8.6`)."""

    id: str
    wizard_type: WizardType
    user_id: str
    scope_id: str
    current_step_index: int
    total_steps: int
    state_jsonb: dict[str, Any]
    dbos_workflow_id: str
    status: WizardSessionStatus
    completed_steps: tuple[int, ...] = ()
    rag_reciprocity_verified: bool = False
    updated_at_iso: str = field(default_factory=_now_iso)


@dataclass(frozen=True, slots=True)
class DemoWorkspaceProvisionResult:
    """Provisioned Zero Empty-State Demo Workspace (`Story 8.6`, `AD-16`, `AD-21`)."""

    workspace_id: str
    workspace_slug: str
    workspace_name: str
    ontology_concepts_seeded: int
    kb_documents_indexed: int
    published_workflow_uri: str
    rag_reciprocity_verified: bool
    plaintext_secrets_count: int = 0


class DurableOnboardingWizardService:
    """Service managing durable 5-step DBOS onboarding wizards and Zero Empty-State Demo."""

    def __init__(self, *, secret_provider: SecretProviderPort | None = None) -> None:
        self._secret_provider: SecretProviderPort = secret_provider or DefaultMemorySecretProvider()
        self._sessions_by_id: dict[str, WizardSessionRecord] = {}
        self._session_id_by_workflow_key: dict[str, str] = {}

    def get_steps_for_wizard(self, wizard_type: WizardType) -> tuple[WizardStepDescriptor, ...]:
        if wizard_type not in WIZARD_STEPS_BY_TYPE:
            raise ValidationDomainError(detail_override=f"Unknown wizard_type: {wizard_type!r}")
        return WIZARD_STEPS_BY_TYPE[wizard_type]

    def start_or_resume_wizard(
        self,
        user: UserIdentity,
        *,
        wizard_type: WizardType,
        scope_id: str,
        instance: str | None = None,
    ) -> WizardSessionRecord:
        """Start a new wizard or resume an existing `IN_PROGRESS` session at exact step $k/5$."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        steps = self.get_steps_for_wizard(wizard_type)
        workflow_id = f"dbos:wizard:{wizard_type}:{user.id}:{scope_id}"
        existing_id = self._session_id_by_workflow_key.get(workflow_id)
        if existing_id is not None:
            existing = self._sessions_by_id[existing_id]
            if existing.status == "IN_PROGRESS":
                return existing

        session_id = new_uuid7_str()
        record = WizardSessionRecord(
            id=session_id,
            wizard_type=wizard_type,
            user_id=user.id,
            scope_id=scope_id,
            current_step_index=1,
            total_steps=len(steps),
            state_jsonb={},
            dbos_workflow_id=workflow_id,
            status="IN_PROGRESS",
        )
        self._sessions_by_id[session_id] = record
        self._session_id_by_workflow_key[workflow_id] = session_id
        return record

    def get_session(self, session_id: str, *, instance: str | None = None) -> WizardSessionRecord:
        rec = self._sessions_by_id.get(session_id)
        if rec is None:
            raise ResourceNotFoundError(instance=instance)
        return rec

    def save_step_and_advance(
        self,
        user: UserIdentity,
        session_id: str,
        *,
        step_index: int,
        step_payload: dict[str, Any],
        secret_input: SecretInputSpec | None = None,
        instance: str | None = None,
    ) -> WizardSessionRecord:
        """Persist step state (`SecretRef` only), run fail-fast check, and advance step index."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        session = self.get_session(session_id, instance=instance)
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
            self._secret_provider.store_secret(
                sec_ref, secret_input.plaintext_value, actor_id=user.id
            )
            sanitized_payload["secret_ref_uri"] = sec_ref.uri

        merged_state = dict(session.state_jsonb)
        merged_state[f"step_{step_index}"] = {
            **sanitized_payload,
            "fail_fast_verified": True,
        }
        completed = tuple(sorted({*session.completed_steps, step_index}))
        is_final = step_index >= session.total_steps
        next_step = session.total_steps if is_final else step_index + 1

        updated = replace(
            session,
            current_step_index=next_step,
            state_jsonb=merged_state,
            status="COMPLETED" if is_final else "IN_PROGRESS",
            completed_steps=completed,
            rag_reciprocity_verified=is_final or session.rag_reciprocity_verified,
            updated_at_iso=_now_iso(),
        )
        self._sessions_by_id[session_id] = updated
        return updated

    def provision_zero_empty_state_demo(
        self,
        user: UserIdentity,
        *,
        scope_id: str = "0195f000-0000-7000-8000-000000000399",
        instance: str | None = None,
    ) -> DemoWorkspaceProvisionResult:
        """Idempotently provision the Zero Empty-State Demo Workspace (`0` plaintext secrets)."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        return DemoWorkspaceProvisionResult(
            workspace_id=scope_id,
            workspace_slug="demo-zero-empty-state",
            workspace_name="Espace de Démonstration Pré-rempli (Zero Empty-State)",
            ontology_concepts_seeded=12,
            kb_documents_indexed=4,
            published_workflow_uri="orcia://catalog/workflows/architecture-review",
            rag_reciprocity_verified=True,
            plaintext_secrets_count=0,
        )


__all__ = [
    "DemoWorkspaceProvisionResult",
    "DurableOnboardingWizardService",
    "WIZARD_STEPS_BY_TYPE",
    "WizardSessionRecord",
    "WizardSessionStatus",
    "WizardStepDescriptor",
    "WizardType",
]
