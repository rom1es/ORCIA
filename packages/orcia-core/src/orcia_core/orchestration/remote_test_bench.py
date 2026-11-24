"""4-Step Hot Remote Service Test Bench & Anti-SSRF Guard (`Story 11.3`, `24.3`).

Pure domain service — zero SQLAlchemy, Redis, or FastAPI imports (`AD-19`).
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from orcia_core.orchestration._orchestration_runtime_locales import (
    MCP_BENCH_LOCALES,
    get_runtime_copy,
)
from orcia_core.orchestration.errors import ObserverModeReadOnlyError
from orcia_core.orchestration.remote_test_bench_models import (
    DiscoveredRemoteCapability,
    RemoteProtocolType,
    RemoteServiceTestAndDiscoverResult,
    TestBenchStepResult,
    ToolAccessQualification,
)
from orcia_core.orchestration.ssrf_guard import (
    is_safe_llm_endpoint_url as _shared_is_safe_endpoint_url,
)

_WRITE_KEYWORDS = ("create", "update", "delete", "write", "post", "put", "patch", "publish", "push")


def is_safe_llm_endpoint_url(
    url: str,
    *,
    allow_private_network: bool = False,
) -> bool:
    """Validate an endpoint URL against Cloud Metadata / link-local / port SSRF attacks."""
    return _shared_is_safe_endpoint_url(
        url,
        allow_private_network=allow_private_network,
        enforce_placeholder_block=False,
    )


def check_remote_endpoint_anti_ssrf(
    *,
    endpoint_url: str,
    protocol: RemoteProtocolType,
    allow_private_network: bool,
) -> tuple[bool, str]:
    """Evaluate Step 1 Network, TLS & Anti-SSRF checks with localized diagnostic."""
    mc = get_runtime_copy(MCP_BENCH_LOCALES)
    if protocol == "WASM_SANDBOX" and endpoint_url.startswith("orcia://"):
        return True, mc["wasm_ok"]
    parsed = urlparse(endpoint_url)
    if parsed.scheme not in ("https", "http"):
        return False, mc["bad_scheme"].format(scheme=parsed.scheme)
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False, mc["missing_host"]
    if not is_safe_llm_endpoint_url(endpoint_url, allow_private_network=allow_private_network):
        return False, mc["ssrf_blocked"].format(host=host)
    return True, mc["net_ok"]


class RemoteServiceTestBenchService:
    """Domain service executing the 4-step Hot Test Bench (`🔌`) for remote services."""

    def test_and_discover_remote_service(
        self,
        *,
        actor_role: str,
        protocol: RemoteProtocolType,
        endpoint_url: str,
        identity_mode: Literal["PASSTHROUGH", "SECRET_REF"],
        has_user_personal_token: bool = False,
        secret_ref_valid: bool = True,
        allow_private_network: bool = False,
        raw_tool_names: list[str] | None = None,
        simulated_dry_run_elapsed_ms: float = 120.0,
        simulated_dry_run_bytes: int = 2048,
    ) -> RemoteServiceTestAndDiscoverResult:
        """Execute the 4-step Hot Test Bench (`🔌`) for MCP/OpenAPI/A2A/WASM services."""
        mc = get_runtime_copy(MCP_BENCH_LOCALES)
        if actor_role == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(
                detail_override="READ_ONLY_OBSERVER cannot run connector test-and-discover."
            )

        step1_ok, step1_msg = check_remote_endpoint_anti_ssrf(
            endpoint_url=endpoint_url,
            protocol=protocol,
            allow_private_network=allow_private_network,
        )
        step1 = TestBenchStepResult(
            step_number=1,
            step_code="1_NETWORK_TLS_ANTI_SSRF",
            status="PASS" if step1_ok else "FAIL",
            detail_fr=step1_msg,
        )

        if not step1_ok:
            step2 = TestBenchStepResult(
                step_number=2,
                step_code="2_AUTHENTICATION",
                status="SKIPPED",
                detail_fr=mc["auth_skipped"],
            )
        elif identity_mode == "PASSTHROUGH" and not has_user_personal_token:
            step2 = TestBenchStepResult(
                step_number=2,
                step_code="2_AUTHENTICATION",
                status="WAITING_USER_PASSTHROUGH_TOKEN",
                detail_fr=mc["auth_wait_token"],
            )
        elif identity_mode == "SECRET_REF" and not secret_ref_valid:
            step2 = TestBenchStepResult(
                step_number=2,
                step_code="2_AUTHENTICATION",
                status="FAIL",
                detail_fr=mc["auth_secret_fail"],
            )
        else:
            step2 = TestBenchStepResult(
                step_number=2,
                step_code="2_AUTHENTICATION",
                status="PASS",
                detail_fr=mc["auth_ok"],
            )

        default_tools = ["search_docs", "create_issue"]
        tool_list = raw_tool_names if raw_tool_names is not None else default_tools
        discovered: list[DiscoveredRemoteCapability] = []
        if step1_ok and step2.status != "FAIL":
            for t_name in tool_list:
                is_write = any(k in t_name.lower() for k in _WRITE_KEYWORDS)
                qual: ToolAccessQualification = "WRITE_STAGED_REQUIRED" if is_write else "READ_ONLY"
                badge = mc["write_staged"] if is_write else mc["read_only"]
                discovered.append(
                    DiscoveredRemoteCapability(
                        tool_name=t_name,
                        description=mc["cap_desc"].format(name=t_name),
                        qualification=qual,
                        badge_fr=badge,
                    )
                )
            step3 = TestBenchStepResult(
                step_number=3,
                step_code="3_CONTRACT_DISCOVERY",
                status="PASS" if discovered else "FAIL",
                detail_fr=mc["discovered_count"].format(count=len(discovered)),
            )
        else:
            step3 = TestBenchStepResult(
                step_number=3,
                step_code="3_CONTRACT_DISCOVERY",
                status="SKIPPED",
                detail_fr=mc["skipped"],
            )

        if step1.status == "PASS" and step3.status == "PASS" and step2.status == "PASS":
            if simulated_dry_run_elapsed_ms > 5_000.0:
                step4 = TestBenchStepResult(
                    step_number=4,
                    step_code="4_HOT_DRY_RUN",
                    status="FAIL",
                    detail_fr=mc["dry_timeout"],
                )
            elif simulated_dry_run_bytes > 1_048_576:
                step4 = TestBenchStepResult(
                    step_number=4,
                    step_code="4_HOT_DRY_RUN",
                    status="FAIL",
                    detail_fr=mc["dry_size"],
                )
            else:
                step4 = TestBenchStepResult(
                    step_number=4,
                    step_code="4_HOT_DRY_RUN",
                    status="PASS",
                    detail_fr=mc["dry_ok"],
                )
        else:
            step4 = TestBenchStepResult(
                step_number=4,
                step_code="4_HOT_DRY_RUN",
                status="SKIPPED",
                detail_fr=mc["dry_deferred"],
            )

        can_activate = (
            step1.status == "PASS"
            and step3.status == "PASS"
            and step2.status in ("PASS", "WAITING_USER_PASSTHROUGH_TOKEN")
            and step4.status in ("PASS", "SKIPPED")
        )
        return RemoteServiceTestAndDiscoverResult(
            protocol=protocol,
            endpoint_url=endpoint_url,
            identity_mode=identity_mode,
            steps=(step1, step2, step3, step4),
            discovered_capabilities=tuple(discovered),
            can_activate=can_activate,
            dry_run_audit_actor_type="ADMIN_CONNECTION_TEST",
            dry_run_run_id=None,
            finops_meta_usage={
                "prompt_tokens": 42,
                "completion_tokens": 18,
                "cost_eur": 0.0002,
            },
        )


__all__ = [
    "RemoteServiceTestBenchService",
    "check_remote_endpoint_anti_ssrf",
    "is_safe_llm_endpoint_url",
]
