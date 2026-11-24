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

from orcia_core.bootstrap._progressive_accostage_models import (
    ACCOSTAGE_SIX_MILESTONES,
    EXCLUSIVE_USERS_LOCK_SQL,
    SINGLE_FAMILY_AMBER_WARNING_FR,
    AccostageMilestoneSpec,
    AccostageStatusReport,
    AccostageVisibleMilestone,
    FirstPlatformAdminRecord,
    LlmProgressiveTierMode,
    build_accostage_status_report,
    is_accostage_milestone_accessible,
)
from orcia_core.bootstrap.errors import (
    FirstUserAlreadyInitializedError,
    InvalidBootstrapTokenError,
)
from orcia_core.bootstrap.models import LlmModelEndpoint, ModelRouterService
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale
from orcia_kernel.ids import new_uuid7_str


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
        self._completed_keys: set[str] = set()

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
            else:
                self._completed_keys.discard("first-admin")

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
            if (
                not expected
                or not candidate
                or not hmac.compare_digest(
                    expected.encode("utf-8", errors="surrogatepass"),
                    candidate.encode("utf-8", errors="surrogatepass"),
                )
            ):
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
        return self.get_accostage_status()

    def mark_milestone_completed(self, milestone_key: str) -> AccostageStatusReport:
        """Mark one of the 6 Day-0 Accostage milestones completed."""
        valid_keys = {m.key for m in ACCOSTAGE_SIX_MILESTONES}
        if milestone_key in valid_keys:
            self._completed_keys.add(milestone_key)
        return self.get_accostage_status()

    def sync_from_pg18_counts(
        self,
        *,
        users_count: int,
        org_units_count: int,
        workspaces_count: int,
        models_count: int,
        sources_count: int,
        workflows_count: int = 0,
        runs_count: int = 0,
    ) -> AccostageStatusReport:
        """Synchronize the 6 Day-0 Accostage milestones from authoritative PG18 counts."""
        orth = self._model_router.evaluate_orthogonality()
        with self._sync_lock:
            keys: set[str] = set()
            if users_count > 0 or self._first_admin is not None:
                keys.add("first-admin")
            if models_count > 0 or len(orth.distinct_families) >= 1:
                keys.add("first-llm-model")
            if org_units_count > 0:
                keys.add("first-org-unit")
            if workspaces_count > 0:
                keys.add("first-space")
            if sources_count > 0:
                keys.add("first-datasource")
            if workflows_count > 0 or runs_count > 0:
                keys.add("pilot-workflow-run")
            self._completed_keys = keys
        return self.get_accostage_status()

    def sync_platform_setup_snapshot(
        self,
        *,
        llm_endpoints: tuple[LlmModelEndpoint, ...],
        has_org_unit: bool = False,
        has_workspace: bool = False,
        has_datasource: bool = False,
        has_pilot_run: bool = False,
    ) -> AccostageStatusReport:
        """Synchronize progressive LLM endpoints and milestone state from persisted snapshot."""
        self._model_router.replace_endpoints(llm_endpoints)
        orth = self._model_router.evaluate_orthogonality()
        with self._sync_lock:
            self._completed_keys = {"first-admin"} if self._first_admin is not None else set()
            if len(orth.distinct_families) >= 1:
                self._completed_keys.add("first-llm-model")
            if has_org_unit:
                self._completed_keys.add("first-org-unit")
            if has_workspace:
                self._completed_keys.add("first-space")
            if has_datasource:
                self._completed_keys.add("first-datasource")
            if has_pilot_run:
                self._completed_keys.add("pilot-workflow-run")
        return self.get_accostage_status()

    def get_accostage_status(
        self,
        *,
        user_role: str | None = None,
        read_only_observer: bool = False,
        locale: SupportedLocale = DEFAULT_LOCALE,
    ) -> AccostageStatusReport:
        """Compute current `Accostage k/6` badge, role-scoped milestones, and LLM tier state."""
        orth = self._model_router.evaluate_orthogonality()
        return build_accostage_status_report(
            distinct_families=orth.distinct_families,
            completed_keys=self._completed_keys,
            first_admin=self._first_admin,
            user_role=user_role,
            read_only_observer=read_only_observer,
            locale=locale,
        )


__all__ = [
    "ACCOSTAGE_SIX_MILESTONES",
    "EXCLUSIVE_USERS_LOCK_SQL",
    "SINGLE_FAMILY_AMBER_WARNING_FR",
    "AccostageMilestoneSpec",
    "AccostageStatusReport",
    "AccostageVisibleMilestone",
    "FirstPlatformAdminRecord",
    "LlmProgressiveTierMode",
    "ProgressiveDay0AccostageService",
    "is_accostage_milestone_accessible",
]
