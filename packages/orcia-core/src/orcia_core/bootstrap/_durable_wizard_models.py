"""Dataclasses, step descriptors & repository port for durable onboarding wizards (`Story 8.6`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from orcia_core.bootstrap._bootstrap_locales import WIZARD_STEP_TITLES_LOCALES

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


_STEP_SPECS: dict[WizardType, tuple[tuple[int, str, str], ...]] = {
    "sdlc_tech_lead": (
        (1, "workspace-identity", "scope-check"),
        (2, "git-jira-sources", "conn-test"),
        (3, "ai-cognitive-tiers", "orthogonality"),
        (4, "gates-and-pack", "sandbox-check"),
        (5, "rag-reciprocity", "rag-ping"),
    ),
    "ops_manager": (
        (1, "bu-team-scope", "scope-check"),
        (2, "knowledge-sources", "conn-test"),
        (3, "budget-finops", "budget-check"),
        (4, "human-gates-policy", "gate-check"),
        (5, "rag-reciprocity", "rag-ping"),
    ),
    "secops_admin": (
        (1, "oidc-and-mfa", "idp-check"),
        (2, "rbac-6-verbs", "anti-lockout"),
        (3, "secret-vault-kms", "kms-check"),
        (4, "pii-and-c3-guards", "pii-check"),
        (5, "rag-reciprocity", "rag-ping"),
    ),
}

WIZARD_STEPS_BY_TYPE: dict[WizardType, tuple[WizardStepDescriptor, ...]] = {
    wtype: tuple(
        WizardStepDescriptor(
            step_index=idx,
            step_key=key,
            title_fr=WIZARD_STEP_TITLES_LOCALES["fr"][wtype][idx - 1],
            title_en=WIZARD_STEP_TITLES_LOCALES["en"][wtype][idx - 1],
            fail_fast_check_label=check_label,
        )
        for idx, key, check_label in specs
    )
    for wtype, specs in _STEP_SPECS.items()
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


class WizardSessionRepositoryPort(Protocol):
    """Hexagonal persistence port for durable `wizard_sessions` (`AD-19`)."""

    async def start_or_resume_wizard_async(
        self,
        *,
        user_id: str,
        wizard_type: WizardType,
        scope_id: str,
        total_steps: int,
    ) -> WizardSessionRecord: ...

    async def get_session_async(self, session_id: str) -> WizardSessionRecord | None: ...

    async def list_sessions_for_user_async(self, user_id: str) -> list[WizardSessionRecord]: ...

    async def save_step_and_advance_async(
        self,
        *,
        session_id: str,
        current_step_index: int,
        state_jsonb: dict[str, Any],
        status: WizardSessionStatus,
        completed_steps: tuple[int, ...],
        rag_reciprocity_verified: bool,
    ) -> WizardSessionRecord | None: ...

    async def update_session_state_async(
        self,
        *,
        session_id: str,
        state_jsonb: dict[str, Any],
        status: WizardSessionStatus,
    ) -> WizardSessionRecord | None: ...


__all__ = [
    "DemoWorkspaceProvisionResult",
    "WIZARD_STEPS_BY_TYPE",
    "WizardSessionRecord",
    "WizardSessionRepositoryPort",
    "WizardSessionStatus",
    "WizardStepDescriptor",
    "WizardType",
    "_now_iso",
]
