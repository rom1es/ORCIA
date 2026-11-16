"""Mappers and SQL query builders for PostgreSQL 18 append-only audit ledger (`Story 6.1`)."""

from __future__ import annotations

import json
from typing import Any, cast

import sqlalchemy as sa

from orcia_core.audit_finops.models import (
    AuditLedgerEntry,
    AuditLedgerFilterParams,
)
from orcia_core.ports.finops_telemetry import CostSource


def parse_row_to_entry(row: dict[str, Any]) -> AuditLedgerEntry:
    """Parse a raw SQL mapping row into an immutable AuditLedgerEntry domain model."""
    cas_refs_raw = row.get("cas_references_jsonb")
    if isinstance(cas_refs_raw, str):
        try:
            cas_refs = json.loads(cas_refs_raw)
        except Exception:
            cas_refs = []
    elif isinstance(cas_refs_raw, list):
        cas_refs = cas_refs_raw
    else:
        cas_refs = []

    meta_raw = row.get("metadata_jsonb")
    if isinstance(meta_raw, str):
        try:
            meta = json.loads(meta_raw)
        except Exception:
            meta = {}
    elif isinstance(meta_raw, dict):
        meta = meta_raw
    else:
        meta = {}

    created_at_val = row.get("created_at")
    created_at_str = created_at_val.isoformat() if created_at_val is not None else None

    cost_val = row.get("cost_usd")
    cost_usd = float(cost_val) if cost_val is not None else 0.0

    native_val = row.get("native_metric_value")
    native_metric_value = float(native_val) if native_val is not None else None

    cost_src_raw = str(row.get("cost_source") or "INTERNAL_VERIFIED")
    cost_source: CostSource = (
        cast(CostSource, cost_src_raw)
        if cost_src_raw in ("INTERNAL_VERIFIED", "EXTERNAL_REPORTED", "ESTIMATED_SCALE")
        else "INTERNAL_VERIFIED"
    )

    return AuditLedgerEntry(
        id=str(row["id"]),
        source_event_id=str(row["source_event_id"]),
        workspace_id=str(row["workspace_id"]) if row.get("workspace_id") else None,
        org_unit_id=str(row["org_unit_id"]) if row.get("org_unit_id") else None,
        scope_path=str(row.get("scope_path") or "GLOBAL"),
        run_id=str(row["run_id"]) if row.get("run_id") else None,
        root_run_id=str(row["root_run_id"]) if row.get("root_run_id") else None,
        step_execution_id=str(row["step_execution_id"]) if row.get("step_execution_id") else None,
        actor_type=str(row.get("actor_type") or "USER"),
        actor_id=str(row.get("actor_id") or "system"),
        actor_display_name=str(row["actor_display_name"])
        if row.get("actor_display_name")
        else None,
        actor_email=str(row["actor_email"]) if row.get("actor_email") else None,
        event_type=str(row.get("event_type") or "UnknownEvent"),
        summary=str(row.get("summary") or ""),
        model_id=str(row["model_id"]) if row.get("model_id") else None,
        inference_tier=str(row["inference_tier"]) if row.get("inference_tier") else None,
        effort=str(row["effort"]) if row.get("effort") else None,
        input_tokens=int(row.get("input_tokens") or 0),
        output_tokens=int(row.get("output_tokens") or 0),
        cost_usd=cost_usd,
        cost_source=cost_source,
        native_metric_type=str(row["native_metric_type"])
        if row.get("native_metric_type")
        else None,
        native_metric_value=native_metric_value,
        native_currency=str(row["native_currency"]) if row.get("native_currency") else None,
        reported_by_remote=bool(row.get("reported_by_remote") or False),
        latency_ms=int(row.get("latency_ms") or 0),
        trace_id=str(row.get("trace_id") or "00000000000000000000000000000000"),
        run_lock_sha256=str(row["run_lock_sha256"]) if row.get("run_lock_sha256") else None,
        pre_prompt_sha256=str(row["pre_prompt_sha256"]) if row.get("pre_prompt_sha256") else None,
        workflow_contract_sha256=str(row["workflow_contract_sha256"])
        if row.get("workflow_contract_sha256")
        else None,
        cas_references=cas_refs,
        metadata=meta,
        created_at=created_at_str,
    )


def build_audit_ledger_where(
    params: AuditLedgerFilterParams,
) -> tuple[str, dict[str, Any]]:
    """Build parameterised WHERE clause and parameter dict for audit_ledger queries."""
    where_clauses: list[str] = ["1=1"]
    sql_params: dict[str, Any] = {}

    if params.scope_path and params.scope_path != "GLOBAL":
        where_clauses.append("(scope_path = :scope_path OR scope_path ILIKE :scope_pattern)")
        sql_params["scope_path"] = params.scope_path
        sql_params["scope_pattern"] = f"%{params.scope_path}%"

    if params.workspace_id:
        where_clauses.append("workspace_id = CAST(:workspace_id AS uuid)")
        sql_params["workspace_id"] = params.workspace_id

    if params.actor_type and params.actor_type != "ALL":
        where_clauses.append("actor_type = :actor_type")
        sql_params["actor_type"] = params.actor_type

    if params.actor_id and params.actor_id != "ALL":
        where_clauses.append("actor_id = :actor_id")
        sql_params["actor_id"] = params.actor_id

    if params.actor_query:
        where_clauses.append(
            "("
            "actor_id ILIKE :actor_query OR "
            "actor_display_name ILIKE :actor_query OR "
            "actor_email ILIKE :actor_query"
            ")"
        )
        sql_params["actor_query"] = f"%{params.actor_query}%"

    if params.event_type and params.event_type != "ALL":
        where_clauses.append("event_type = :event_type")
        sql_params["event_type"] = params.event_type

    if params.run_id:
        where_clauses.append("run_id = CAST(:run_id AS uuid)")
        sql_params["run_id"] = params.run_id

    if params.time_window == "1H":
        where_clauses.append("created_at >= NOW() - INTERVAL '1 hour'")
    elif params.time_window == "24H":
        where_clauses.append("created_at >= NOW() - INTERVAL '24 hours'")
    elif params.time_window == "7D":
        where_clauses.append("created_at >= NOW() - INTERVAL '7 days'")
    elif params.time_window == "30D":
        where_clauses.append("created_at >= NOW() - INTERVAL '30 days'")

    if params.date_from:
        where_clauses.append("created_at >= CAST(:date_from AS timestamptz)")
        sql_params["date_from"] = params.date_from

    if params.date_to:
        where_clauses.append("created_at <= CAST(:date_to AS timestamptz)")
        sql_params["date_to"] = params.date_to

    return " AND ".join(where_clauses), sql_params


SQL_INSERT_ENTRY = sa.text(
    """
    INSERT INTO audit_ledger (
        id,
        source_event_id,
        workspace_id,
        org_unit_id,
        scope_path,
        run_id,
        root_run_id,
        step_execution_id,
        actor_type,
        actor_id,
        actor_display_name,
        actor_email,
        event_type,
        summary,
        model_id,
        inference_tier,
        effort,
        input_tokens,
        output_tokens,
        cost_usd,
        cost_source,
        native_metric_type,
        native_metric_value,
        native_currency,
        reported_by_remote,
        latency_ms,
        trace_id,
        run_lock_sha256,
        pre_prompt_sha256,
        workflow_contract_sha256,
        cas_references_jsonb,
        metadata_jsonb,
        created_at
    ) VALUES (
        CAST(:id AS uuid),
        CAST(:source_event_id AS uuid),
        CAST(:workspace_id AS uuid),
        CAST(:org_unit_id AS uuid),
        :scope_path,
        CAST(:run_id AS uuid),
        CAST(:root_run_id AS uuid),
        CAST(:step_execution_id AS uuid),
        :actor_type,
        :actor_id,
        :actor_display_name,
        :actor_email,
        :event_type,
        :summary,
        :model_id,
        :inference_tier,
        :effort,
        :input_tokens,
        :output_tokens,
        :cost_usd,
        :cost_source,
        :native_metric_type,
        :native_metric_value,
        :native_currency,
        :reported_by_remote,
        :latency_ms,
        :trace_id,
        :run_lock_sha256,
        :pre_prompt_sha256,
        :workflow_contract_sha256,
        CAST(:cas_references_jsonb AS jsonb),
        CAST(:metadata_jsonb AS jsonb),
        COALESCE(CAST(:created_at AS timestamptz), NOW())
    )
    ON CONFLICT (source_event_id) DO NOTHING
    RETURNING id;
    """
)

SQL_LOOKUP_EXISTING_ID = sa.text(
    "SELECT id FROM audit_ledger WHERE source_event_id = CAST(:source_event_id AS uuid);"
)

SQL_PROVENANCE_ENTRIES = sa.text(
    """
    SELECT *
    FROM audit_ledger
    WHERE run_id = CAST(:run_id AS uuid)
    ORDER BY created_at ASC;
    """
)

SQL_RUN_LOCK_MANIFEST_SHA = sa.text(
    """
    SELECT manifest_sha256
    FROM run_lock_manifests
    WHERE run_id = CAST(:run_id AS uuid);
    """
)
