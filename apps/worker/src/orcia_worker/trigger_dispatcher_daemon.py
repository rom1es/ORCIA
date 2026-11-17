"""Real `trigger-dispatcher` daemon for `apps/worker` (`Story 7.2`, `AD-18`, `AD-23`)."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from orcia_core.audit_finops import SqlAuditLedgerService
from orcia_core.bootstrap import SqlAutonomyContractRepository
from orcia_core.config import resolve_database_url
from orcia_core.observability import build_log_sink_from_env
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration import (
    DbosSqlAlchemyUnitOfWork,
    SqlWorkflowTriggerRepository,
    TriggerDispatcherService,
)
from orcia_core.orchestration.help_generator_and_validator import (
    HelpGenerationAndHotAttachmentService,
)
from orcia_core.permissions import (
    AutonomyContractService,
    HierarchicalRbacService,
    PassthroughVaultCipher,
)
from orcia_worker.outbox_relay import DramatiqOutboxRelay, OutboxEventBus

logger = get_logger("orcia.worker.trigger_dispatcher")


@dataclass(frozen=True, slots=True)
class TriggerDispatcherCycleSummary:
    """Summary of one bounded `trigger-dispatcher` polling cycle."""

    log_sink_dispatched: int
    cron_dispatched: int
    outbox_relayed: int


async def run_trigger_dispatcher_cycle(
    dispatcher: TriggerDispatcherService,
    *,
    engine: AsyncEngine | None = None,
    help_service: HelpGenerationAndHotAttachmentService | None = None,
    now_utc: datetime | None = None,
) -> TriggerDispatcherCycleSummary:
    """Execute one bounded cycle: LogSink scan, CRON evaluation, and Outbox relay."""
    now = now_utc or datetime.now(UTC)
    log_outcomes = await dispatcher.scan_log_sink_triggers(now_utc=now)
    cron_outcomes = await dispatcher.evaluate_cron_triggers(now_utc=now)
    outbox_count = 0
    if engine is not None:
        uow = await DbosSqlAlchemyUnitOfWork.create("", engine=engine, run_migrations=False)
        help_svc = help_service or HelpGenerationAndHotAttachmentService()
        bus = OutboxEventBus(
            audit_sink=SqlAuditLedgerService(engine=engine),
            on_workflow_published=lambda evt: dispatcher.handle_workflow_published(
                evt, help_service=help_svc
            ),
        )
        relay = DramatiqOutboxRelay(event_bus=bus, engine=engine)
        outbox_count = await relay.relay_sql_pending_batch(uow, batch_size=50)
    return TriggerDispatcherCycleSummary(
        log_sink_dispatched=sum(1 for o in log_outcomes if o.dispatched),
        cron_dispatched=sum(1 for o in cron_outcomes if o.dispatched),
        outbox_relayed=outbox_count,
    )


async def serve_trigger_dispatcher_daemon(
    *,
    once: bool = False,
    poll_interval_seconds: float = 5.0,
    database_url: str | None = None,
) -> int:
    """Run the `trigger-dispatcher` operational daemon until `SIGINT`/`SIGTERM` or `once`."""
    db_url = database_url or resolve_database_url()
    engine: AsyncEngine | None = None
    if db_url and not once or db_url and os.environ.get("ORCIA_TRIGGER_DAEMON_USE_DB", "") == "1":
        engine = create_async_engine(db_url, poolclass=NullPool)

    try:
        log_sink = build_log_sink_from_env()
        rbac = HierarchicalRbacService()
        contract_repo = (
            SqlAutonomyContractRepository(
                engine=engine, audit_ledger_sink=SqlAuditLedgerService(engine=engine)
            )
            if engine is not None
            else None
        )
        contract_svc = AutonomyContractService(rbac_service=rbac, repository=contract_repo)
        trigger_repo = (
            SqlWorkflowTriggerRepository(
                engine=engine, audit_ledger_sink=SqlAuditLedgerService(engine=engine)
            )
            if engine is not None
            else None
        )
        dispatcher = TriggerDispatcherService(
            contract_service=contract_svc,
            repository=trigger_repo,
            vault_cipher=PassthroughVaultCipher(
                os.environ.get("ORCIA_PASSTHROUGH_MASTER_KEY", "0" * 32)
            ),
            log_sink=log_sink,
        )
        logger.info("worker.trigger_dispatcher.started", once=once)
        summary = await run_trigger_dispatcher_cycle(dispatcher, engine=engine)
        logger.info(
            "worker.trigger_dispatcher.cycle",
            log_sink_dispatched=summary.log_sink_dispatched,
            cron_dispatched=summary.cron_dispatched,
            outbox_relayed=summary.outbox_relayed,
        )
        if once:
            logger.info("worker.trigger_dispatcher.stopped", reason="once")
            return 0

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, stop_event.set)

        interval = max(0.5, float(poll_interval_seconds))
        while not stop_event.is_set():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            if stop_event.is_set():
                break
            await run_trigger_dispatcher_cycle(dispatcher, engine=engine)
        logger.info("worker.trigger_dispatcher.stopped", reason="signal")
        return 0
    finally:
        if engine is not None:
            await engine.dispose()


__all__ = [
    "TriggerDispatcherCycleSummary",
    "run_trigger_dispatcher_cycle",
    "serve_trigger_dispatcher_daemon",
]
