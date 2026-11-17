"""Datasource and RAG domain events for Outbox (`Story 18.2`, `Story 19.7`, `AD-24.7`).

Pure kernel module — zero framework or business domain dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.kernel._events_base import DomainEvent
from orcia_core.kernel.ids import new_uuid7_str


@dataclass(frozen=True, slots=True)
class DatasourceSyncRequested(DomainEvent):
    """Published when an incremental sync is required for a workspace datasource (`Story 18.2`)."""

    datasource_id: str = ""
    source_nature: str = ""
    trigger_reason: str = "WEBHOOK_PUSH"

    @classmethod
    def create(
        cls,
        *,
        datasource_id: str,
        workspace_id: str,
        source_nature: str,
        trigger_reason: str = "WEBHOOK_PUSH",
        target_ref: str | None = None,
        delivery_key: str | None = None,
        remote_fingerprint_sha256: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
    ) -> DatasourceSyncRequested:
        return cls(
            event_id=new_uuid7_str(),
            event_type="DatasourceSyncRequested",
            aggregate_type="workspace_datasource",
            aggregate_id=datasource_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "datasource_id": datasource_id,
                "workspace_id": workspace_id,
                "source_nature": source_nature,
                "trigger_reason": trigger_reason,
                "target_ref": target_ref,
                "delivery_key": delivery_key,
                "remote_fingerprint_sha256": remote_fingerprint_sha256,
            },
            trace_id=trace_id,
            datasource_id=datasource_id,
            source_nature=source_nature,
            trigger_reason=trigger_reason,
        )


@dataclass(frozen=True, slots=True)
class DatasourceFreshnessEvaluated(DomainEvent):
    """Published when a freshness probe evaluates a workspace datasource (`Story 18.2`)."""

    datasource_id: str = ""
    freshness_status: str = "SYNCED"
    outcome: str = "QUIET_UNCHANGED"

    @classmethod
    def create(
        cls,
        *,
        datasource_id: str,
        workspace_id: str,
        source_nature: str,
        freshness_status: str,
        outcome: str,
        elapsed_hours: float = 0.0,
        stored_fingerprint: str | None = None,
        probed_fingerprint: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
    ) -> DatasourceFreshnessEvaluated:
        return cls(
            event_id=new_uuid7_str(),
            event_type="DatasourceFreshnessEvaluated",
            aggregate_type="workspace_datasource",
            aggregate_id=datasource_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "datasource_id": datasource_id,
                "workspace_id": workspace_id,
                "source_nature": source_nature,
                "freshness_status": freshness_status,
                "outcome": outcome,
                "elapsed_hours": elapsed_hours,
                "stored_fingerprint": stored_fingerprint,
                "probed_fingerprint": probed_fingerprint,
            },
            trace_id=trace_id,
            datasource_id=datasource_id,
            freshness_status=freshness_status,
            outcome=outcome,
        )


@dataclass(frozen=True, slots=True)
class EmbeddingReindexStarted(DomainEvent):
    """Published when a global RAG vector reindexing job starts (`Story 19.7`, `AD-24.7`)."""

    job_id: str = ""
    target_model_id: str = ""
    target_model_name: str = ""
    total_chunks: int = 0

    @classmethod
    def create(
        cls,
        *,
        job_id: str,
        target_model_id: str,
        target_model_name: str,
        total_chunks: int = 0,
        trace_id: str = "00000000000000000000000000000000",
    ) -> EmbeddingReindexStarted:
        return cls(
            event_id=new_uuid7_str(),
            event_type="EmbeddingReindexStarted",
            aggregate_type="rag_reindex_job",
            aggregate_id=job_id,
            run_id=None,
            workspace_id=None,
            payload={
                "job_id": job_id,
                "target_model_id": target_model_id,
                "target_model_name": target_model_name,
                "total_chunks": total_chunks,
            },
            trace_id=trace_id,
            job_id=job_id,
            target_model_id=target_model_id,
            target_model_name=target_model_name,
            total_chunks=total_chunks,
        )


@dataclass(frozen=True, slots=True)
class EmbeddingReindexCompleted(DomainEvent):
    """Published when a global RAG vector reindexing job completes (`Story 19.7`, `AD-24.7`)."""

    job_id: str = ""
    target_model_id: str = ""
    total_chunks: int = 0
    processed_chunks: int = 0

    @classmethod
    def create(
        cls,
        *,
        job_id: str,
        target_model_id: str,
        total_chunks: int,
        processed_chunks: int,
        trace_id: str = "00000000000000000000000000000000",
    ) -> EmbeddingReindexCompleted:
        return cls(
            event_id=new_uuid7_str(),
            event_type="EmbeddingReindexCompleted",
            aggregate_type="rag_reindex_job",
            aggregate_id=job_id,
            run_id=None,
            workspace_id=None,
            payload={
                "job_id": job_id,
                "target_model_id": target_model_id,
                "total_chunks": total_chunks,
                "processed_chunks": processed_chunks,
            },
            trace_id=trace_id,
            job_id=job_id,
            target_model_id=target_model_id,
            total_chunks=total_chunks,
            processed_chunks=processed_chunks,
        )


@dataclass(frozen=True, slots=True)
class EmbeddingReindexFailed(DomainEvent):
    """Published when a global RAG vector reindexing job fails (`Story 19.7`, `AD-24.7`)."""

    job_id: str = ""
    target_model_id: str = ""
    error_message: str = ""
    processed_chunks: int = 0

    @classmethod
    def create(
        cls,
        *,
        job_id: str,
        target_model_id: str,
        error_message: str,
        processed_chunks: int = 0,
        trace_id: str = "00000000000000000000000000000000",
    ) -> EmbeddingReindexFailed:
        return cls(
            event_id=new_uuid7_str(),
            event_type="EmbeddingReindexFailed",
            aggregate_type="rag_reindex_job",
            aggregate_id=job_id,
            run_id=None,
            workspace_id=None,
            payload={
                "job_id": job_id,
                "target_model_id": target_model_id,
                "error_message": error_message,
                "processed_chunks": processed_chunks,
            },
            trace_id=trace_id,
            job_id=job_id,
            target_model_id=target_model_id,
            error_message=error_message,
            processed_chunks=processed_chunks,
        )
