"""ORCIA Async Worker package (`apps/worker`, `AD-19`, `Story 4.1a`).

Uses lazy attribute resolution for `docling_indexer` so that importing `orcia_worker`
from `worker-orchestration`, `trigger-dispatcher`, or `sandbox-runner` never loads
`orcia_worker.docling_indexer` into `sys.modules`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from orcia_worker.broker import (
    ProcessedPingRegistry,
    configure_broker,
    execute_system_ping,
    system_ping_actor,
)
from orcia_worker.dbos_workflow_runner import (
    StepRunnerExecutionResult,
    dbos_step_runner_workflow,
    dispatch_durable_step,
    execute_step_runner_job,
)
from orcia_worker.outbox_relay import (
    DbosOutboxRelay,
    DramatiqOutboxRelay,
    OutboxEventBus,
    dbos_outbox_relay_workflow,
    outbox_relay_actor,
)
from orcia_worker.roles import (
    CANONICAL_DEPLOYMENT_ROLES,
    DeploymentRoleName,
    DeploymentRoleSpec,
    get_deployment_role_spec,
    list_deployment_role_specs,
    verify_role_process_isolation,
)

if TYPE_CHECKING:
    from orcia_worker.codegraph_indexer import (
        CodegraphIndexExecutionResult,
        codegraph_indexer_actor,
        execute_codegraph_index_job,
        execute_codegraph_index_job_async,
        purge_confined_graph_dir,
        resolve_confined_graph_dir,
    )
    from orcia_worker.docling_indexer import (
        DoclingIndexExecutionResult,
        docling_indexer_actor,
        execute_docling_index_job,
    )

_DOCLING_EXPORTS = {
    "DoclingIndexExecutionResult",
    "docling_indexer_actor",
    "execute_docling_index_job",
}

_CODEGRAPH_EXPORTS = {
    "CodegraphIndexExecutionResult",
    "codegraph_indexer_actor",
    "execute_codegraph_index_job",
    "execute_codegraph_index_job_async",
    "purge_confined_graph_dir",
    "resolve_confined_graph_dir",
}


def __getattr__(name: str) -> Any:
    if name in _DOCLING_EXPORTS:
        from orcia_worker import docling_indexer

        return getattr(docling_indexer, name)
    if name in _CODEGRAPH_EXPORTS:
        from orcia_worker import codegraph_indexer

        return getattr(codegraph_indexer, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CANONICAL_DEPLOYMENT_ROLES",
    "CodegraphIndexExecutionResult",
    "DbosOutboxRelay",
    "DeploymentRoleName",
    "DeploymentRoleSpec",
    "DoclingIndexExecutionResult",
    "DramatiqOutboxRelay",
    "OutboxEventBus",
    "ProcessedPingRegistry",
    "StepRunnerExecutionResult",
    "codegraph_indexer_actor",
    "configure_broker",
    "dbos_outbox_relay_workflow",
    "dbos_step_runner_workflow",
    "dispatch_durable_step",
    "docling_indexer_actor",
    "execute_codegraph_index_job",
    "execute_codegraph_index_job_async",
    "execute_docling_index_job",
    "execute_step_runner_job",
    "execute_system_ping",
    "get_deployment_role_spec",
    "list_deployment_role_specs",
    "outbox_relay_actor",
    "purge_confined_graph_dir",
    "resolve_confined_graph_dir",
    "system_ping_actor",
    "verify_role_process_isolation",
]
