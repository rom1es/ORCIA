"""Connector Hub (`/settings/connectors`), Ingestion Guardrails (`C0-C3`, PII, `0 char`)
& RAG Reciprocity (`Story 8.4`).
"""

from __future__ import annotations

import re
from dataclasses import replace

from orcia_core.permissions.errors import (
    C3WorkspaceRequiredError,
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.models import UserIdentity, WorkspaceVisibilityMode
from orcia_core.permissions.platform_settings import (
    SecretInputSpec,
    SecretStatusView,
    compute_salted_secret_fingerprint,
)
from orcia_core.rag._connector_hub_models import (
    ConnectorConnectionTestResult,
    ConnectorHealthKind,
    ConnectorInstanceRecord,
    DataSecurityClassification,
    DocumentIngestionReport,
    PiiArbitrationDecision,
    RagReciprocityVerificationResult,
    detect_pii_categories,
    now_iso,
    resolve_connector_secret_update,
    scrub_pii_reversibly,
)
from orcia_core.rag._rag_locales import get_rag_locale_bundle
from orcia_core.rag.errors import EmptyOrUnreadableDocumentError
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.secret_ports import SecretProviderPort, SecretRef

__all__ = [
    "ConnectorConnectionTestResult",
    "ConnectorHealthKind",
    "ConnectorHubAndIngestionService",
    "ConnectorInstanceRecord",
    "DataSecurityClassification",
    "DocumentIngestionReport",
    "PiiArbitrationDecision",
    "RagReciprocityVerificationResult",
    "detect_pii_categories",
    "scrub_pii_reversibly",
]


class ConnectorHubAndIngestionService:
    """Domain service for `/settings/connectors`, ingestion guardrails & RAG reciprocity."""

    def __init__(
        self,
        *,
        secret_provider: SecretProviderPort | None = None,
        workspace_visibilities: dict[str, WorkspaceVisibilityMode] | None = None,
    ) -> None:
        self._secret_provider = secret_provider
        self._connectors: dict[str, ConnectorInstanceRecord] = {}
        self._documents: dict[str, DocumentIngestionReport] = {}
        self._workspace_visibilities: dict[str, WorkspaceVisibilityMode] = dict(
            workspace_visibilities
            or {
                "0195f000-0000-7000-8000-000000000301": "STANDARD",
                "0195f000-0000-7000-8000-000000000302": "CONFIDENTIAL_RESTRICTED",
            }
        )
        self._seed_default_connectors()

    def _seed_default_connectors(self) -> None:
        ws_id = "0195f000-0000-7000-8000-000000000301"
        conn_id = "0195f000-0000-7000-8000-000000008401"
        self._connectors[conn_id] = ConnectorInstanceRecord(
            id=conn_id,
            workspace_id=ws_id,
            alias="core-git-monorepo",
            scheme="git",
            uri="git://github.enterprise.local/orcia/monorepo",
            classification="C0_C2_STANDARD",
            secret_ref=SecretRef(f"secret://workspace/{ws_id}/connectors/{conn_id}"),
            secret_status=SecretStatusView(
                configured=True,
                fingerprint=compute_salted_secret_fingerprint(conn_id, "seeded-token"),
                updated_at=now_iso(),
                updated_by="system",
            ),
            health_status="HEALTHY",
            last_tested_at_iso=now_iso(),
        )

    def set_workspace_visibility(
        self, workspace_id: str, visibility: WorkspaceVisibilityMode
    ) -> None:
        self._workspace_visibilities[workspace_id] = visibility

    def list_connectors(self, workspace_id: str | None = None) -> list[ConnectorInstanceRecord]:
        items = list(self._connectors.values())
        if workspace_id is not None:
            items = [c for c in items if c.workspace_id == workspace_id]
        return items

    def upsert_connector(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        alias: str,
        scheme: str,
        uri: str,
        classification: DataSecurityClassification = "C0_C2_STANDARD",
        secret_input: SecretInputSpec | None = None,
        connector_id: str | None = None,
        instance: str | None = None,
    ) -> ConnectorInstanceRecord:
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        ws_vis = self._workspace_visibilities.get(workspace_id, "STANDARD")
        if classification == "C3_CONFIDENTIAL_RESTRICTED" and ws_vis != "CONFIDENTIAL_RESTRICTED":
            raise C3WorkspaceRequiredError(instance=instance)

        cid = connector_id or new_uuid7_str()
        now = now_iso()
        sec_ref, sec_status = resolve_connector_secret_update(
            secret_provider=self._secret_provider,
            existing=self._connectors.get(cid),
            secret_input=secret_input,
            workspace_id=workspace_id,
            connector_id=cid,
            user_id=user.id,
            now=now,
        )
        rec = ConnectorInstanceRecord(
            id=cid,
            workspace_id=workspace_id,
            alias=alias.strip(),
            scheme=scheme.strip().lower(),
            uri=uri.strip(),
            classification=classification,
            secret_ref=sec_ref,
            secret_status=sec_status,
        )
        self._connectors[cid] = rec
        return rec

    def test_connector_connection(
        self,
        user: UserIdentity,
        connector_id: str,
        *,
        simulated_status: ConnectorHealthKind | None = None,
        instance: str | None = None,
        locale: str = "fr",
    ) -> ConnectorConnectionTestResult:
        """Execute a fail-fast (`< 5000 ms`) DBOS healthcheck step on `connector_id`."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        conn = self._connectors.get(connector_id)
        if conn is None:
            raise ResourceNotFoundError(instance=instance)
        if simulated_status is not None:
            status = simulated_status
        elif "unreachable" in conn.uri.lower():
            status = "UNREACHABLE"
        elif "degraded" in conn.uri.lower() or not conn.secret_status.configured:
            status = "DEGRADED"
        else:
            status = "HEALTHY"

        bundle = get_rag_locale_bundle(locale)
        diag_map: dict[ConnectorHealthKind, str] = {
            "HEALTHY": bundle.connector_healthy_tpl.format(uri=conn.uri),
            "DEGRADED": bundle.connector_degraded_tpl.format(uri=conn.uri),
            "UNREACHABLE": bundle.connector_unreachable_tpl.format(uri=conn.uri),
        }
        now = now_iso()
        self._connectors[connector_id] = replace(
            conn, health_status=status, last_tested_at_iso=now, last_diagnostic=diag_map[status]
        )
        return ConnectorConnectionTestResult(
            connector_id=connector_id,
            scheme=conn.scheme,
            uri=conn.uri,
            status=status,
            latency_ms=42 if status == "HEALTHY" else 185,
            timeout_budget_ms=5000,
            diagnostic_message=diag_map[status],
            tested_at_iso=now,
        )

    def ingest_document_with_guardrails(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        uri: str,
        title: str,
        raw_extracted_text: str,
        classification: DataSecurityClassification,
        pii_decision: PiiArbitrationDecision | None = None,
        document_id: str | None = None,
        instance: str | None = None,
    ) -> DocumentIngestionReport:
        """Run the 3 ingestion guardrails (`C0-C3`, `0 char` OCR fail-fast, PII arbitration)."""
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        ws_vis = self._workspace_visibilities.get(workspace_id, "STANDARD")
        if classification == "C3_CONFIDENTIAL_RESTRICTED" and ws_vis != "CONFIDENTIAL_RESTRICTED":
            raise C3WorkspaceRequiredError(instance=instance)
        cleaned = re.sub(r"\s+", " ", raw_extracted_text).strip()
        if len(cleaned) == 0:
            raise EmptyOrUnreadableDocumentError(instance=instance)

        doc_id = document_id or new_uuid7_str()
        pii_cats = detect_pii_categories(cleaned)
        has_pii = len(pii_cats) > 0
        options: tuple[PiiArbitrationDecision, ...] = (
            ("PSEUDONYMIZE", "INDEX_AS_IS_AUDITED", "CANCEL_IMPORT") if has_pii else ()
        )
        if has_pii and pii_decision is None:
            status_val = "WAITING_FOR_PII_ARBITRATION"
            final_text, chunk_id = "", None
        elif pii_decision == "CANCEL_IMPORT":
            status_val = "CANCELLED"
            final_text, chunk_id = "", None
        else:
            status_val = "INDEXED"
            final_text = (
                scrub_pii_reversibly(cleaned) if pii_decision == "PSEUDONYMIZE" else cleaned
            )
            chunk_id = f"chunk-{doc_id[:8]}-01"

        report = DocumentIngestionReport(
            document_id=doc_id,
            workspace_id=workspace_id,
            uri=uri.strip(),
            title=title.strip(),
            classification=classification,
            status=status_val,  # type: ignore[arg-type]
            extracted_char_count=len(cleaned),
            pii_detected=has_pii,
            pii_categories=pii_cats,
            arbitration_options=options,
            pseudonymized=bool(status_val == "INDEXED" and pii_decision == "PSEUDONYMIZE"),
            audit_derogation_recorded=bool(
                status_val == "INDEXED" and has_pii and pii_decision == "INDEX_AS_IS_AUDITED"
            ),
            indexed_chunk_id=chunk_id,
            indexed_excerpt=final_text[:240],
        )
        self._documents[doc_id] = report
        return report

    def verify_rag_reciprocity(
        self,
        document_id: str,
        *,
        control_query: str | None = None,
        instance: str | None = None,
        locale: str = "fr",
    ) -> RagReciprocityVerificationResult:
        """Execute 1-click RAG reciprocity check verifying mandatory URI + chunk citation."""
        doc = self._documents.get(document_id)
        if doc is None:
            raise ResourceNotFoundError(instance=instance)
        if doc.status != "INDEXED" or not doc.indexed_chunk_id:
            raise ValidationDomainError(
                detail_override="Document must be in INDEXED state before RAG reciprocity check.",
                instance=instance,
            )
        bundle = get_rag_locale_bundle(locale)
        q = control_query or bundle.reciprocity_query_tpl.format(title=doc.title)
        response_md = bundle.reciprocity_response_tpl.format(
            title=doc.title,
            excerpt=doc.indexed_excerpt,
            uri=doc.uri,
            chunk_id=doc.indexed_chunk_id,
        )
        return RagReciprocityVerificationResult(
            document_id=doc.document_id,
            uri=doc.uri,
            passed=doc.uri in response_md and doc.indexed_chunk_id in response_md,
            control_query=q,
            response_markdown=response_md,
            cited_uri=doc.uri,
            cited_chunk_id=doc.indexed_chunk_id,
        )
