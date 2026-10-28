"""Finance Vertical Fixture ("Rapprochement de factures", `Story 3.2f`, `AC-F5`).

Demonstrates that ORCIA Core executes a complete non-SDLC vertical workflow (`mode: "standard"`,
`erp://` connector scheme, `AGENT`, `HTTP_ACTION`, `HUMAN_TASK`, `POST_ACTION_VERIFICATION`)
with `orcia-pack-sdlc` completely deactivated (`core-without-sdlc`).
"""

from __future__ import annotations

import json
from typing import Any

from orcia_kernel.errors import (
    FunctionalConnectorError,
    OrciaDomainError,
    PermanentInfraError,
    RateLimitedError,
)
from orcia_kernel.ids import compute_bytes_sha256
from orcia_kernel.ports import (
    ConnectorCapabilities,
    ConnectorFetchResult,
    ConnectorHealthStatus,
    ConnectorInvokeResult,
    ConnectorPort,
)

FINANCE_INVOICE_RECONCILIATION_YAML = """
uri: "orcia://workflows/finance-invoice-reconciliation"
title: "Rapprochement de Factures Fournisseurs & Bon de Commande ERP"
description: "Workflow Finance hors-SDLC validant le socle universel ORCIA Core (AC-F5)."
version: "1.0.0"
criticality: "STANDARD"
execution_regime: "INTERACTIVE_COACHING"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
adaptive_gate_policy: "STANDARD"
max_cost_usd: 15.0
datasources:
  - "erp://sap-finance/invoices/INV-2026-8841?ref=2026.10"
  - "db://finance_ledger/purchase_orders/PO-2026-8841"
steps:
  - step_key: "extract-and-match-invoice"
    title: "Extraction et rapprochement tripartite Facture / BC / Réception"
    step_type: "AGENT"
    agent_uri: "orcia://agents/finance-reconciler"
    instructions: "Analyser la facture INV-2026-8841 et vérifier la concordance avec PO-2026-8841."
  - step_key: "post-erp-voucher"
    title: "Comptabilisation de l'écriture dans le grand livre ERP"
    step_type: "HTTP_ACTION"
    skill_uri: "erp://sap-finance/post_voucher"
    depends_on:
      - "extract-and-match-invoice"
    instructions: "Enregistrer le bon à payer dans l'ERP financier."
  - step_key: "approve-payment-release"
    title: "Approbation trésorerie du décaissement fournisseur"
    step_type: "HUMAN_TASK"
    depends_on:
      - "post-erp-voucher"
    requires_human_gate: true
    instructions: "Valider le déblocage du règlement fournisseur de 14 250,00 EUR."
  - step_key: "verify-ledger-balance"
    title: "Vérification post-comptabilisation de l'équilibre du journal"
    step_type: "POST_ACTION_VERIFICATION"
    depends_on:
      - "approve-payment-release"
    verification_window_seconds: 60
    instructions: "Vérifier l'équilibre débit/crédit du journal auxiliaire fournisseurs."
"""


class FakeFinanceErpConnector(ConnectorPort):
    """Deterministic `erp://` connector double for Finance Invoice Reconciliation (`AC-F3..F5`)."""

    def __init__(self) -> None:
        self._idempotency_cache: dict[str, ConnectorInvokeResult] = {}
        self._scripted_errors: list[Exception] = []
        self.call_count: int = 0

    def script_error(self, exc: Exception) -> None:
        """Queue an exception to be raised on the next `invoke(...)` call."""
        self._scripted_errors.append(exc)

    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            scheme="erp",
            display_name="SAP / Finance ERP Connector (Test Fixture)",
            pack_name="orcia-fixture-finance",
            supports_read=True,
            supports_write=True,
            version_resolution_mode="ref_or_latest",
        )

    def fetch(self, uri: str) -> ConnectorFetchResult:
        payload = json.dumps(
            {
                "uri": uri,
                "invoice_id": "INV-2026-8841",
                "po_id": "PO-2026-8841",
                "amount_eur": 14250.00,
                "currency": "EUR",
                "three_way_match": "MATCHED",
            },
            sort_keys=True,
        ).encode("utf-8")
        return ConnectorFetchResult(
            uri=uri,
            scheme="erp",
            resolved_version="2026.10",
            content_bytes=payload,
            content_type="application/json",
            sha256=compute_bytes_sha256(payload),
        )

    def invoke(
        self, action: str, payload: dict[str, Any], idempotency_key: str
    ) -> ConnectorInvokeResult:
        self.call_count += 1
        if self._scripted_errors:
            exc = self._scripted_errors.pop(0)
            raise exc

        cached = self._idempotency_cache.get(idempotency_key)
        if cached is not None:
            return ConnectorInvokeResult(
                scheme="erp",
                action=action,
                idempotency_key=idempotency_key,
                replayed_from_idempotency_cache=True,
                status=cached.status,
                output=dict(cached.output),
            )

        res = ConnectorInvokeResult(
            scheme="erp",
            action=action,
            idempotency_key=idempotency_key,
            replayed_from_idempotency_cache=False,
            status="SUCCEEDED",
            output={
                "voucher_id": f"VOUCHER-{idempotency_key[-8:]}",
                "journal": "AP-LEDGER-2026",
                "posted_amount_eur": 14250.00,
                "input_keys": sorted(payload.keys()),
            },
        )
        self._idempotency_cache[idempotency_key] = res
        return res

    def health(self) -> ConnectorHealthStatus:
        return ConnectorHealthStatus(scheme="erp", state="HEALTHY", latency_ms=2.1, detail="OK")

    def map_error(self, exc: Exception) -> OrciaDomainError:
        if isinstance(exc, OrciaDomainError):
            return exc
        msg = str(exc)
        if "429" in msg:
            return RateLimitedError(retry_after_s=2.0, detail_override=msg)
        if "422" in msg or "FUNCTIONAL" in msg.upper():
            return FunctionalConnectorError(detail_override=msg)
        return PermanentInfraError(detail_override=msg)
