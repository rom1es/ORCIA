"""Scheduled CRON, LogSink anomaly & opt-in WorkflowPublished handlers (`Story 7.2`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from orcia_core.orchestration._triggers_crud_helpers import TriggerDispatchOutcome
from orcia_core.orchestration._triggers_log_cron import (
    LogSinkAnomalyScanner,
    cron_matches_timestamp,
)
from orcia_core.ports.log_sink import LogSinkQueryPort
from orcia_kernel.events import DomainEvent

if TYPE_CHECKING:
    from orcia_core.orchestration.triggers_dispatcher import TriggerDispatcherService


async def run_log_sink_trigger_scan(
    dispatcher: TriggerDispatcherService,
    *,
    workspace_id: str | None = None,
    now_utc: datetime | None = None,
    log_sink: LogSinkQueryPort | None = None,
) -> list[TriggerDispatchOutcome]:
    """Scan `LogSinkQueryPort` for active `LOG_SINK_ALERT` triggers and dispatch idempotently."""
    sink = log_sink or dispatcher.log_sink
    if sink is None:
        return []
    scanner = LogSinkAnomalyScanner(sink)
    triggers = (
        await dispatcher.list_triggers(workspace_id=workspace_id)
        if workspace_id is not None
        else await dispatcher.list_active_by_type("LOG_SINK_ALERT")
    )
    outcomes: list[TriggerDispatchOutcome] = []
    for trig in triggers:
        if trig.trigger_type != "LOG_SINK_ALERT" or trig.status != "ACTIVE":
            continue
        for anomaly in await scanner.scan_trigger(trig, now_utc=now_utc):
            outcomes.append(
                await dispatcher.dispatch_trigger(
                    trigger_id=trig.id,
                    idempotency_key=anomaly.idempotency_key,
                    payload={"fingerprint": anomaly.fingerprint, "service": anomaly.service},
                    raise_on_circuit_open=False,
                )
            )
    return outcomes


async def run_cron_trigger_evaluation(
    dispatcher: TriggerDispatcherService,
    *,
    workspace_id: str | None = None,
    now_utc: datetime | None = None,
) -> list[TriggerDispatchOutcome]:
    """Evaluate active `CRON` triggers against minute-bucket UTC timestamp."""
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    bucket = now.strftime("%Y%m%d%H%M")
    triggers = (
        await dispatcher.list_triggers(workspace_id=workspace_id)
        if workspace_id is not None
        else await dispatcher.list_active_by_type("CRON")
    )
    outcomes: list[TriggerDispatchOutcome] = []
    for trig in triggers:
        if (
            trig.trigger_type == "CRON"
            and trig.status == "ACTIVE"
            and trig.cron_expr
            and cron_matches_timestamp(trig.cron_expr, now)
        ):
            outcomes.append(
                await dispatcher.dispatch_trigger(
                    trigger_id=trig.id,
                    idempotency_key=f"cron:{bucket}",
                    payload={"scheduled_minute_utc": bucket},
                    raise_on_circuit_open=False,
                )
            )
    return outcomes


async def run_workflow_published_optin_help(
    dispatcher: TriggerDispatcherService,
    event: DomainEvent,
    *,
    help_service: Any | None = None,
) -> list[TriggerDispatchOutcome]:
    """Trigger `generate-and-attach-help` ONLY when `auto_help_on_publish == True`."""
    ws_id = event.workspace_id
    wf_id = str(event.payload.get("workflow_id") or event.aggregate_id)
    version = str(event.payload.get("version") or "1.0.0")
    if not ws_id or not wf_id:
        return []
    triggers = await dispatcher.list_triggers(workspace_id=ws_id, workflow_id=wf_id)
    outcomes: list[TriggerDispatchOutcome] = []
    for trig in triggers:
        if (
            trig.trigger_type != "OUTBOX_EVENT"
            or trig.status != "ACTIVE"
            or not trig.auto_help_on_publish
        ):
            continue

        async def _run_help(_wf: str = wf_id, _ver: str = version) -> dict[str, Any]:
            if help_service is None:
                return {"help_attached": False}
            title = str(event.payload.get("title") or _wf)
            res = await help_service.generate_and_attach_help(
                article_id=f"help-{_wf}",
                article_slug=f"{_wf}-help",
                version=_ver,
                pack_slug=str(event.payload.get("pack_slug") or "orcia-docs"),
                title_fr=f"Aide — {title}",
                title_en=f"Help — {title}",
                bound_routes=["/processes"],
                roles_allowed=["TEAM_LEAD", "CONTRIBUTOR"],
                glossary_terms=["Processus"],
                related_workflows=[_wf],
                purpose_fr=f"Documentation du processus {title}.",
                purpose_en=f"Documentation for process {title}.",
                steps_fr=["Ouvrir le processus dans le studio."],
                steps_en=["Open the process in studio."],
                faq_fr=["Comment relancer ? Utiliser le bouton Tester."],
                faq_en=["How to re-run? Use the Test button."],
                trigger_regime="AUTONOMOUS_CONTRACT",
            )
            return {"help_attached": True, "article_id": res.article_id}

        outcomes.append(
            await dispatcher.dispatch_trigger(
                trigger_id=trig.id,
                idempotency_key=f"publish:{wf_id}:{version}",
                headers=None,
                payload=dict(event.payload),
                execution_fn=_run_help,
                trace_id=event.trace_id,
                raise_on_circuit_open=False,
            )
        )
    return outcomes


__all__ = [
    "run_cron_trigger_evaluation",
    "run_log_sink_trigger_scan",
    "run_workflow_published_optin_help",
]
