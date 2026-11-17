"""Bridge connecting `TriggerDispatcherService` to `orcia_connectors` autonomous runs."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from orcia_connectors.autonomous_runner import (
    AutonomousActionRequest,
    AutonomousGateInput,
    execute_autonomous_contract_run,
)
from orcia_connectors.protocol import (
    ConnectorHealthStatus,
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
    verify_signed_approval_token,
)
from orcia_core.kernel.secret_ports import SecretProviderPort
from orcia_core.orchestration._triggers_dispatch_helpers import (
    AutonomousTriggerExecutor,
    TriggerAutonomousExecutionContext,
)
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService
from orcia_core.orchestration.help_generator_and_validator import (
    HelpGenerationAndHotAttachmentService,
)
from orcia_core.permissions.autonomy_contracts import AutonomyContractService


class InternalCatalogActionAdapter:
    """`OrciaConnectorProtocol` implementation bridging catalog/help mutations."""

    connector_type: str = "catalog"

    def __init__(
        self,
        *,
        help_generator: HelpGenerationAndHotAttachmentService,
        run_id: str,
        contract_label: str,
        trigger_label: str,
    ) -> None:
        self._help = help_generator
        self._run_id = run_id
        self._contract_label = contract_label
        self._trigger_label = trigger_label

    async def healthcheck(self) -> ConnectorHealthStatus:
        """Report local catalog connector availability."""
        return ConnectorHealthStatus(connector_type=self.connector_type, ok=True, latency_ms=1)

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read metadata snapshot for a catalog resource URI."""
        return {"resource_uri": resource_uri, "query": dict(query or {})}

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        """Build write preview digest for catalog mutation actions."""
        digest = compute_payload_sha256(action, payload)
        return WritePreviewCard(
            connector_type=self.connector_type,
            target_resource_uri=str(payload.get("article_id") or "orcia://catalog/help"),
            action_summary=f"{action} ({self._trigger_label})",
            diff_or_payload_preview=dict(payload),
            payload_sha256=digest,
        )

    async def execute_write(
        self,
        approval_token: SignedApprovalToken,
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Verify `SignedApprovalToken` and persist generated `HelpArticle` if applicable."""
        verify_signed_approval_token(approval_token, action=action, payload=payload)
        article_id = str(payload.get("article_id") or "")
        if "help" in action or article_id:
            resolved_id = article_id or f"help.auto.{self._run_id[:8]}"
            routes = [str(r) for r in (payload.get("bound_routes") or ["/processes"])]
            attached = await self._help.generate_and_attach_help(
                article_id=resolved_id,
                article_slug=str(payload.get("article_slug") or resolved_id.replace(".", "-")),
                version=str(payload.get("version") or "1.0.1"),
                pack_slug=str(payload.get("pack_slug") or "core"),
                title_fr=str(payload.get("title_fr") or "Aide mise à jour sous contrat"),
                title_en=str(payload.get("title_en") or "Contract-updated contextual help"),
                bound_routes=routes,
                roles_allowed=["CONTRIBUTOR", "ARCHITECT", "PLATFORM_ADMIN"],
                glossary_terms=list(payload.get("glossary_terms") or ["Processus"]),
                related_workflows=[self._contract_label],
                purpose_fr=str(payload.get("purpose_fr") or "Aide générée sous contrat."),
                purpose_en=str(payload.get("purpose_en") or "Contract-generated help."),
                steps_fr=list(payload.get("steps_fr") or ["Vérifier l'exécution autonome."]),
                steps_en=list(payload.get("steps_en") or ["Verify autonomous execution."]),
                faq_fr=list(payload.get("faq_fr") or ["Consultable dans l'écran cible."]),
                faq_en=list(payload.get("faq_en") or ["Available in the target screen."]),
                autonomous_run_id=self._run_id,
                contract_label=self._contract_label,
                trigger_label=self._trigger_label,
            )
            return {
                "article_id": attached.article_id,
                "help_resource_id": f"{attached.article_id}-fr",
                "version": attached.version,
                "fr_cas_key": attached.fr_cas_key,
            }
        return {"action": action, "status": "applied", "run_id": self._run_id}


def build_autonomous_trigger_executor(
    *,
    contract_service: AutonomyContractService,
    supervision_service: AutonomousSupervisionService,
    help_generator: HelpGenerationAndHotAttachmentService,
    secret_provider: SecretProviderPort | None = None,
) -> AutonomousTriggerExecutor:
    """Create an async bridge running `execute_autonomous_contract_run` for fired triggers."""

    async def _execute_trigger(ctx: TriggerAutonomousExecutionContext) -> dict[str, Any]:
        raw_actions = ctx.payload.get("actions")
        actions: list[AutonomousActionRequest] = []
        if isinstance(raw_actions, list) and raw_actions:
            for item in raw_actions:
                if isinstance(item, dict):
                    actions.append(AutonomousActionRequest.model_validate(item))
        if not actions:
            default_action = (
                ctx.contract.allowed_write_actions[0]
                if ctx.contract.allowed_write_actions
                else "catalog.write"
            )
            scheme = (
                default_action.split(":", 1)[0]
                if ":" in default_action
                else default_action.split(".", 1)[0]
            )
            actions.append(
                AutonomousActionRequest(
                    action_key=default_action,
                    scheme=scheme or "catalog",
                    payload=dict(ctx.payload),
                )
            )
        raw_gates = ctx.payload.get("gates")
        gate_input = (
            AutonomousGateInput.model_validate(raw_gates)
            if isinstance(raw_gates, dict)
            else AutonomousGateInput(
                estimated_cost_usd=float(ctx.payload.get("estimated_cost_usd", 0.05))
            )
        )
        catalog_adapter = InternalCatalogActionAdapter(
            help_generator=help_generator,
            run_id=ctx.run_id,
            contract_label=ctx.contract.workflow_id,
            trigger_label=ctx.trigger.trigger_key,
        )
        outcome, _events = await execute_autonomous_contract_run(
            contract=ctx.contract,
            criticality=str(ctx.payload.get("criticality", "STANDARD")),
            actions=actions,
            gates=gate_input,
            run_id=ctx.run_id,
            contract_refresh_fn=lambda: contract_service.get_active_contract(
                workspace_id=ctx.contract.workspace_id,
                workflow_id=ctx.contract.workflow_id,
            ),
            kill_switch_check_fn=supervision_service.is_run_stopped,
            connectors_by_scheme={"catalog": catalog_adapter},
            secret_provider=secret_provider,
            trace_id=ctx.trace_id,
        )
        help_res_id: str | None = None
        for act in outcome.executed_actions:
            res_map = act.get("result")
            if isinstance(res_map, dict) and res_map.get("help_resource_id"):
                help_res_id = str(res_map["help_resource_id"])
                break
        await supervision_service.register_autonomous_run(
            run_id=ctx.run_id,
            workspace_id=ctx.contract.workspace_id,
            workflow_id=ctx.contract.workflow_id,
            contract_id=ctx.contract.id,
            status=outcome.status,
            trigger_id=ctx.trigger.id,
            trigger_label=ctx.trigger.trigger_key,
            trigger_type=ctx.trigger.trigger_type,
            trigger_status=ctx.trigger.status,
            sampling_rate=ctx.contract.post_hoc_sampling_rate,
            cost_usd=Decimal(str(gate_input.estimated_cost_usd)),
            help_resource_id=help_res_id,
            force_post_hoc_sample=bool(ctx.payload.get("force_post_hoc_sample", False)),
            trace_id=ctx.trace_id,
        )
        return {
            "run_id": outcome.run_id,
            "status": outcome.status,
            "executed_actions": outcome.executed_actions,
            "help_resource_id": help_res_id,
        }

    return _execute_trigger


__all__ = ["InternalCatalogActionAdapter", "build_autonomous_trigger_executor"]
