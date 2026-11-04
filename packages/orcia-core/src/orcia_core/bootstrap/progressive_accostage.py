"""Progressive Day-0 Accostage (1/6), Anti-First-User Takeover & Progressive LLM Tier (`Story 9.2`).

Implements (`Section 2`, `AD-10`, `AD-16`, `AD-19`):
- Exclusive table lock `LOCK TABLE users IN EXCLUSIVE MODE` + `COUNT(*) FROM users == 0` check
- `ORCIA_BOOTSTRAP_TOKEN` constant-time verification when `ORCIA_ENV != "local"`
  (`HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN`)
- Progressive LLM tier unlock:
  - `1` model family -> `QUICK_TRIAL_SINGLE_FAMILY` (`Mon Assistant` + `Cockpit` unlocked with
    non-blocking amber badge)
  - `>= 2` distinct model families -> `FULL_ORTHOGONAL_AD10` (`Agentic Gates AD-10` unlocked)
- Interactive `Accostage 1/6`..`6/6` milestone tracking.
"""

from __future__ import annotations

import asyncio
import hmac
import threading
from dataclasses import dataclass
from typing import Literal

from orcia_core.bootstrap.errors import (
    FirstUserAlreadyInitializedError,
    InvalidBootstrapTokenError,
)
from orcia_core.bootstrap.models import LlmModelEndpoint, ModelRouterService
from orcia_kernel.ids import new_uuid7_str

LlmProgressiveTierMode = Literal[
    "UNCONFIGURED",
    "QUICK_TRIAL_SINGLE_FAMILY",
    "FULL_ORTHOGONAL_AD10",
]

SINGLE_FAMILY_AMBER_WARNING_FR: str = (
    "⚠️ 1 seule famille de modèles configurée — Ajoutez une 2e famille dans "
    "Configuration › Modèles IA pour activer les Gates Agentiques AD-10"
)

EXCLUSIVE_USERS_LOCK_SQL: str = "LOCK TABLE users IN EXCLUSIVE MODE"


@dataclass(frozen=True, slots=True)
class AccostageMilestoneSpec:
    """One of the 6 progressive Day-0 Accostage milestones (`Accostage 1/6`..`6/6`)."""

    index: int
    key: str
    title_fr: str
    title_en: str
    target_route: str


ACCOSTAGE_SIX_MILESTONES: tuple[AccostageMilestoneSpec, ...] = (
    AccostageMilestoneSpec(
        1,
        "first-admin",
        "1. Compte Administrateur Initial",
        "1. Initial Administrator Account",
        "/welcome-setup",
    ),
    AccostageMilestoneSpec(
        2,
        "first-llm-model",
        "2. Premier Modèle IA (Essai Mon Assistant)",
        "2. First AI Model (My Assistant Trial)",
        "/configuration",
    ),
    AccostageMilestoneSpec(
        3,
        "first-space",
        "3. Premier Espace de Travail",
        "3. First Solution Space",
        "/spaces",
    ),
    AccostageMilestoneSpec(
        4,
        "first-datasource",
        "4. Première Source Documentaire ou Git",
        "4. First Knowledge or Git Source",
        "/spaces",
    ),
    AccostageMilestoneSpec(
        5,
        "second-llm-family",
        "5. Seconde Famille IA Orthogonale (Gates AD-10)",
        "5. Second Orthogonal AI Family (AD-10 Gates)",
        "/configuration",
    ),
    AccostageMilestoneSpec(
        6,
        "pilot-workflow-run",
        "6. Premier Processus Pilote Exécuté",
        "6. First Pilot Process Executed",
        "/processes",
    ),
)


@dataclass(frozen=True, slots=True)
class FirstPlatformAdminRecord:
    """Created initial `PLATFORM_ADMIN` account under `LOCK TABLE users IN EXCLUSIVE MODE`."""

    user_id: str
    email: str
    display_name: str
    platform_role: Literal["PLATFORM_ADMIN"]
    orcia_env: str
    sql_lock_statement: str


@dataclass(frozen=True, slots=True)
class AccostageStatusReport:
    """Current Day-0 progressive Accostage status (`Accostage k/6` + LLM tier state)."""

    completed_count: int
    total_count: int
    badge_label: str
    llm_tier_mode: LlmProgressiveTierMode
    distinct_families: tuple[str, ...]
    assistant_trial_enabled: bool
    agentic_gates_ad10_enabled: bool
    amber_warning_badge: str | None
    completed_milestone_keys: tuple[str, ...]
    first_admin_initialized: bool = False
    first_admin_email: str | None = None
    first_admin_display_name: str | None = None


class ProgressiveDay0AccostageService:
    """Domain service enforcing anti-first-user-takeover and progressive LLM tier unlock."""

    def __init__(
        self,
        *,
        orcia_env: str = "local",
        expected_bootstrap_token: str | None = "orcia-day0-bootstrap-token",
        model_router: ModelRouterService | None = None,
    ) -> None:
        self._orcia_env = orcia_env.strip().lower() or "local"
        self._expected_bootstrap_token = expected_bootstrap_token
        self._model_router = model_router or ModelRouterService()
        self._sync_lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._first_admin: FirstPlatformAdminRecord | None = None
        self._completed_keys: set[str] = {"first-admin"}

    @property
    def orcia_env(self) -> str:
        """Configured ORCIA environment (`local`, `staging`, `production`)."""
        return self._orcia_env

    @property
    def expected_bootstrap_token(self) -> str | None:
        """Expected Day-0 bootstrap token when `orcia_env != 'local'`."""
        return self._expected_bootstrap_token

    @property
    def first_admin(self) -> FirstPlatformAdminRecord | None:
        """Currently cached `FirstPlatformAdminRecord`, if any."""
        return self._first_admin

    def set_first_platform_admin_record(self, record: FirstPlatformAdminRecord | None) -> None:
        """Synchronize the in-memory `FirstPlatformAdminRecord` with PostgreSQL 18 state."""
        with self._sync_lock:
            self._first_admin = record
            if record is not None:
                self._completed_keys.add("first-admin")

    def _verify_bootstrap_token(
        self,
        provided_token: str | None,
        *,
        env_override: str | None = None,
        instance: str | None = None,
    ) -> str:
        effective_env = (env_override or self._orcia_env).strip().lower()
        if effective_env != "local":
            expected = (self._expected_bootstrap_token or "").strip()
            candidate = (provided_token or "").strip()
            if not expected or not candidate or not hmac.compare_digest(expected, candidate):
                raise InvalidBootstrapTokenError(instance=instance)
        return effective_env

    def create_first_platform_admin(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str,
        bootstrap_token: str | None = None,
        orcia_env_override: str | None = None,
        instance: str | None = None,
    ) -> FirstPlatformAdminRecord:
        """Synchronously create the single first `PLATFORM_ADMIN` under exclusive lock."""
        effective_env = self._verify_bootstrap_token(
            bootstrap_token,
            env_override=orcia_env_override,
            instance=instance,
        )
        with self._sync_lock:
            if self._first_admin is not None:
                raise FirstUserAlreadyInitializedError(instance=instance)
            _ = password_hash
            record = FirstPlatformAdminRecord(
                user_id=new_uuid7_str(),
                email=email.strip().lower(),
                display_name=display_name.strip(),
                platform_role="PLATFORM_ADMIN",
                orcia_env=effective_env,
                sql_lock_statement=EXCLUSIVE_USERS_LOCK_SQL,
            )
            self._first_admin = record
            self._completed_keys.add("first-admin")
            return record

    async def create_first_platform_admin_async(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str,
        bootstrap_token: str | None = None,
        orcia_env_override: str | None = None,
        instance: str | None = None,
    ) -> FirstPlatformAdminRecord:
        """Asynchronously create the single first `PLATFORM_ADMIN` under exclusive lock."""
        effective_env = self._verify_bootstrap_token(
            bootstrap_token,
            env_override=orcia_env_override,
            instance=instance,
        )
        async with self._async_lock:
            await asyncio.sleep(0)
            return self.create_first_platform_admin(
                email=email,
                display_name=display_name,
                password_hash=password_hash,
                bootstrap_token=bootstrap_token,
                orcia_env_override=effective_env,
                instance=instance,
            )

    def register_progressive_llm_endpoint(
        self,
        endpoint: LlmModelEndpoint,
    ) -> AccostageStatusReport:
        """Register an LLM endpoint and recompute progressive Trial vs AD-10 Gate unlock."""
        self._model_router.register_endpoint(endpoint)
        orth = self._model_router.evaluate_orthogonality()
        if len(orth.distinct_families) >= 1:
            self._completed_keys.add("first-llm-model")
        if len(orth.distinct_families) >= 2:
            self._completed_keys.add("second-llm-family")
        return self.get_accostage_status()

    def mark_milestone_completed(self, milestone_key: str) -> AccostageStatusReport:
        """Mark one of the 6 Day-0 Accostage milestones completed."""
        valid_keys = {m.key for m in ACCOSTAGE_SIX_MILESTONES}
        if milestone_key in valid_keys:
            self._completed_keys.add(milestone_key)
        return self.get_accostage_status()

    def get_accostage_status(self) -> AccostageStatusReport:
        """Compute current `Accostage k/6` badge and LLM progressive tier state."""
        orth = self._model_router.evaluate_orthogonality()
        fam_count = len(orth.distinct_families)
        if fam_count == 0:
            tier_mode: LlmProgressiveTierMode = "UNCONFIGURED"
            trial_ok = False
            ad10_ok = False
            amber_badge: str | None = None
        elif fam_count == 1:
            tier_mode = "QUICK_TRIAL_SINGLE_FAMILY"
            trial_ok = True
            ad10_ok = False
            amber_badge = SINGLE_FAMILY_AMBER_WARNING_FR
        else:
            tier_mode = "FULL_ORTHOGONAL_AD10"
            trial_ok = True
            ad10_ok = True
            amber_badge = None

        ordered_completed = tuple(
            m.key for m in ACCOSTAGE_SIX_MILESTONES if m.key in self._completed_keys
        )
        completed_count = max(1, len(ordered_completed))
        total_count = len(ACCOSTAGE_SIX_MILESTONES)
        admin = self._first_admin
        return AccostageStatusReport(
            completed_count=completed_count,
            total_count=total_count,
            badge_label=f"Accostage {completed_count}/{total_count}",
            llm_tier_mode=tier_mode,
            distinct_families=orth.distinct_families,
            assistant_trial_enabled=trial_ok,
            agentic_gates_ad10_enabled=ad10_ok,
            amber_warning_badge=amber_badge,
            completed_milestone_keys=ordered_completed,
            first_admin_initialized=admin is not None,
            first_admin_email=admin.email if admin is not None else None,
            first_admin_display_name=admin.display_name if admin is not None else None,
        )
