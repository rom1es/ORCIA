"""Provenance Dossier & Sealed Compliance Exporter (`Story 6.1`)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from orcia_core.audit_finops._audit_finops_locales import get_audit_finops_locale_bundle
from orcia_core.audit_finops._internal.sql_audit_ledger import SqlAuditLedgerService
from orcia_core.audit_finops.errors import AuditRunNotFoundError
from orcia_core.audit_finops.models import (
    AuditLedgerEntry,
    AuditProvenanceExport,
    AuditProvenanceSummary,
)
from orcia_kernel.enums import DEFAULT_LOCALE


class ProvenanceExporterService:
    """Service generating structured and human-readable compliance dossiers."""

    def __init__(self, ledger_service: SqlAuditLedgerService) -> None:
        self._ledger = ledger_service

    async def get_provenance_summary(self, run_id: str) -> AuditProvenanceSummary:
        """Compute the consolidated provenance summary for a given workflow run."""
        entries = await self._ledger.get_run_provenance_entries(run_id)
        if not entries:
            raise AuditRunNotFoundError(
                detail_code="ERR_AUDIT_RUN_NOT_FOUND_DETAIL",
                detail_params={"run_id": run_id},
            )

        manifest_sha = await self._ledger.get_run_lock_manifest_sha(run_id)
        models_set: set[str] = set()
        actors_set: set[str] = set()
        cas_refs_set: set[str] = set()
        total_in = total_out = 0
        total_cost = 0.0
        run_lock_sha: str | None = None
        contract_sha: str | None = None
        root_run_id: str | None = None

        for e in entries:
            if e.model_id:
                models_set.add(e.model_id)
            if e.actor_id:
                actors_set.add(e.actor_id)
            cas_refs_set.update(e.cas_references)
            total_in += e.input_tokens
            total_out += e.output_tokens
            total_cost += e.cost_usd
            if e.run_lock_sha256 and not run_lock_sha:
                run_lock_sha = e.run_lock_sha256
            if e.workflow_contract_sha256 and not contract_sha:
                contract_sha = e.workflow_contract_sha256
            if e.root_run_id and not root_run_id:
                root_run_id = e.root_run_id

        effective_lock_sha = run_lock_sha or manifest_sha
        is_aligned = not (manifest_sha and run_lock_sha and manifest_sha != run_lock_sha)
        return AuditProvenanceSummary(
            run_id=run_id,
            root_run_id=root_run_id,
            total_events=len(entries),
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_cost_usd=round(total_cost, 6),
            models_invoked=sorted(models_set),
            actors_involved=sorted(actors_set),
            run_lock_sha256=effective_lock_sha,
            workflow_contract_sha256=contract_sha,
            cas_references=sorted(cas_refs_set),
            is_run_lock_aligned=is_aligned,
            first_event_at=entries[0].created_at,
            last_event_at=entries[-1].created_at,
        )

    async def export_dossier(
        self,
        run_id: str,
        export_format: Literal["json", "md"] = "json",
        *,
        locale: str = DEFAULT_LOCALE,
    ) -> AuditProvenanceExport:
        """Export the sealed audit dossier in either JSON or Markdown format."""
        entries = await self._ledger.get_run_provenance_entries(run_id)
        if not entries:
            raise AuditRunNotFoundError(
                detail_code="ERR_AUDIT_RUN_NOT_FOUND_DETAIL",
                detail_params={"run_id": run_id},
            )

        summary = await self.get_provenance_summary(run_id)
        now_iso = datetime.now(UTC).isoformat()

        if export_format == "json":
            payload = {
                "schema_version": "orcia.provenance.v1",
                "run_id": run_id,
                "exported_at": now_iso,
                "certification": {
                    "is_immutable": True,
                    "storage_engine": "PostgreSQL 18 append-only",
                    "trigger_active": True,
                    "is_run_lock_aligned": summary.is_run_lock_aligned,
                    "manifest_sha256": summary.run_lock_sha256,
                    "workflow_contract_sha256": summary.workflow_contract_sha256,
                },
                "summary": {
                    "root_run_id": summary.root_run_id,
                    "total_events": summary.total_events,
                    "total_input_tokens": summary.total_input_tokens,
                    "total_output_tokens": summary.total_output_tokens,
                    "total_cost_usd": summary.total_cost_usd,
                    "models_invoked": summary.models_invoked,
                    "actors_involved": summary.actors_involved,
                    "first_event_at": summary.first_event_at,
                    "last_event_at": summary.last_event_at,
                    "cas_references_count": len(summary.cas_references),
                    "cas_references": summary.cas_references,
                },
                "events_timeline": [
                    {
                        "id": e.id,
                        "source_event_id": e.source_event_id,
                        "event_type": e.event_type,
                        "summary": e.summary,
                        "actor_type": e.actor_type,
                        "actor_id": e.actor_id,
                        "actor_display_name": e.actor_display_name,
                        "model_id": e.model_id,
                        "cost_usd": e.cost_usd,
                        "input_tokens": e.input_tokens,
                        "output_tokens": e.output_tokens,
                        "latency_ms": e.latency_ms,
                        "trace_id": e.trace_id,
                        "run_lock_sha256": e.run_lock_sha256,
                        "workflow_contract_sha256": e.workflow_contract_sha256,
                        "cas_references": e.cas_references,
                        "created_at": e.created_at,
                    }
                    for e in entries
                ],
            }
            content = json.dumps(payload, indent=2, ensure_ascii=False)
        else:
            content = self._render_markdown_report(summary, entries, now_iso, locale=locale)

        return AuditProvenanceExport(
            run_id=run_id,
            format=export_format,
            content=content,
            exported_at=now_iso,
            manifest_sha256=summary.run_lock_sha256,
            entries_count=len(entries),
        )

    def _render_markdown_report(
        self,
        summary: AuditProvenanceSummary,
        entries: list[AuditLedgerEntry],
        exported_at: str,
        *,
        locale: str = DEFAULT_LOCALE,
    ) -> str:
        bundle = get_audit_finops_locale_bundle(locale)
        aligned_label = bundle.prov_aligned if summary.is_run_lock_aligned else bundle.prov_diverged
        models_str = ", ".join(summary.models_invoked) or bundle.prov_none_models
        actors_str = ", ".join(summary.actors_involved) or bundle.prov_system_actor
        token_str = f"{summary.total_input_tokens:,} in / {summary.total_output_tokens:,} out"
        period_str = f"{summary.first_event_at or 'N/A'} -> {summary.last_event_at or 'N/A'}"

        lines: list[str] = [
            bundle.prov_title_tpl.format(run_id=summary.run_id),
            "",
            bundle.prov_attestation,
            bundle.prov_certifies_tpl.format(run_id=summary.run_id),
            bundle.prov_exported_at_tpl.format(exported_at=exported_at),
            "",
            bundle.prov_sec1_title,
            "",
            bundle.prov_lbl_align.format(aligned_label=aligned_label),
            bundle.prov_lbl_run_lock.format(sha=summary.run_lock_sha256 or "N/A"),
            bundle.prov_lbl_contract.format(sha=summary.workflow_contract_sha256 or "N/A"),
            bundle.prov_lbl_events.format(count=summary.total_events),
            bundle.prov_lbl_tokens.format(tokens=token_str),
            bundle.prov_lbl_cost.format(cost=summary.total_cost_usd),
            bundle.prov_lbl_models.format(models=models_str),
            bundle.prov_lbl_actors.format(actors=actors_str),
            bundle.prov_lbl_period.format(period=period_str),
            "",
            bundle.prov_sec2_title,
            "",
            bundle.prov_table_header,
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for e in entries:
            ts = e.created_at or "N/A"
            actor = e.actor_display_name or e.actor_id
            model = e.model_id or "-"
            cost = f"${e.cost_usd:.4f}"
            summary_clean = e.summary.replace("|", "/")
            lines.append(
                f"| `{ts}` | `{e.event_type}` | {actor} | `{model}` | {cost} | {summary_clean} |"
            )

        lines.extend(["", bundle.prov_sec3_title, ""])
        if summary.cas_references:
            lines.extend(f"- CAS Ref : `{ref}`" for ref in summary.cas_references)
        else:
            lines.append(bundle.prov_no_cas)
        lines.extend(["", "---", bundle.prov_footer])
        return "\n".join(lines)
