"""Models and PII helpers for `ConnectorHubAndIngestionService` (`Story 8.4`)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from orcia_core.permissions.platform_settings import (
    SecretInputSpec,
    SecretStatusView,
    compute_salted_secret_fingerprint,
)
from orcia_core.rag._rag_locales import get_rag_locale_bundle
from orcia_kernel.secret_ports import SecretProviderPort, SecretRef

DataSecurityClassification = Literal["C0_C2_STANDARD", "C3_CONFIDENTIAL_RESTRICTED"]
PiiArbitrationDecision = Literal["PSEUDONYMIZE", "INDEX_AS_IS_AUDITED", "CANCEL_IMPORT"]
ConnectorHealthKind = Literal["HEALTHY", "DEGRADED", "UNREACHABLE"]

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
PHONE_RE = re.compile(r"\b(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4}\b")
NIR_RE = re.compile(r"\b[12]\s?\d{2}\s?(?:0[1-9]|1[0-2])\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b")


def now_iso() -> str:
    """Return UTC ISO-8601 timestamp ending in `Z`."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def detect_pii_categories(text: str) -> tuple[str, ...]:
    """Scan `text` for personal data categories (EMAIL, IBAN, PHONE, NIR)."""
    found: list[str] = []
    if EMAIL_RE.search(text):
        found.append("EMAIL")
    if IBAN_RE.search(text):
        found.append("IBAN")
    if PHONE_RE.search(text):
        found.append("PHONE")
    if NIR_RE.search(text):
        found.append("NIR")
    return tuple(found)


def scrub_pii_reversibly(text: str) -> str:
    """Replace detected PII tokens with reversible deterministic placeholders."""
    scrubbed = EMAIL_RE.sub("[PII_EMAIL_REDACTED]", text)
    scrubbed = IBAN_RE.sub("[PII_IBAN_REDACTED]", scrubbed)
    scrubbed = PHONE_RE.sub("[PII_PHONE_REDACTED]", scrubbed)
    return NIR_RE.sub("[PII_NIR_REDACTED]", scrubbed)


@dataclass(frozen=True, slots=True)
class ConnectorInstanceRecord:
    """Configured connector datasource instance in `/settings/connectors` (`Story 8.4`)."""

    id: str
    workspace_id: str
    alias: str
    scheme: str
    uri: str
    classification: DataSecurityClassification
    secret_ref: SecretRef | None
    secret_status: SecretStatusView
    health_status: ConnectorHealthKind = "HEALTHY"
    last_tested_at_iso: str | None = None
    last_diagnostic: str = field(
        default_factory=lambda: get_rag_locale_bundle("fr").connector_nominal
    )


@dataclass(frozen=True, slots=True)
class ConnectorConnectionTestResult:
    """Result of `POST /api/v1/settings/connectors/{id}/test-connection` (`< 5 s`, `Story 8.4`)."""

    connector_id: str
    scheme: str
    uri: str
    status: ConnectorHealthKind
    latency_ms: int
    timeout_budget_ms: int
    diagnostic_message: str
    tested_at_iso: str = field(default_factory=now_iso)


@dataclass(frozen=True, slots=True)
class DocumentIngestionReport:
    """Result of the guarded document ingestion pipeline (`Story 8.4`, `AD-21`)."""

    document_id: str
    workspace_id: str
    uri: str
    title: str
    classification: DataSecurityClassification
    status: Literal["INDEXED", "WAITING_FOR_PII_ARBITRATION", "CANCELLED"]
    extracted_char_count: int
    pii_detected: bool
    pii_categories: tuple[str, ...]
    arbitration_options: tuple[PiiArbitrationDecision, ...]
    pseudonymized: bool
    audit_derogation_recorded: bool
    indexed_chunk_id: str | None = None
    indexed_excerpt: str = ""


@dataclass(frozen=True, slots=True)
class RagReciprocityVerificationResult:
    """1-click RAG reciprocity check result (`Story 8.4`)."""

    document_id: str
    uri: str
    passed: bool
    control_query: str
    response_markdown: str
    cited_uri: str
    cited_chunk_id: str


def resolve_connector_secret_update(
    *,
    secret_provider: SecretProviderPort | None,
    existing: ConnectorInstanceRecord | None,
    secret_input: SecretInputSpec | None,
    workspace_id: str,
    connector_id: str,
    user_id: str,
    now: str,
) -> tuple[SecretRef | None, SecretStatusView]:
    """Compute updated `SecretRef` and `SecretStatusView` when upserting a connector."""
    sec_ref = existing.secret_ref if existing else None
    sec_status = (
        existing.secret_status
        if existing
        else SecretStatusView(
            configured=False, fingerprint=None, updated_at=now, updated_by=user_id
        )
    )
    if secret_input is not None:
        if secret_input.action == "set":
            assert secret_input.plaintext_value is not None
            sec_ref = SecretRef(
                uri=f"secret://workspace/{workspace_id}/connectors/{connector_id}",
                workspace_id=workspace_id,
            )
            if secret_provider is not None:
                secret_provider.store_secret(
                    sec_ref, secret_input.plaintext_value, actor_id=user_id
                )
            fp = compute_salted_secret_fingerprint(connector_id, secret_input.plaintext_value)
            sec_status = SecretStatusView(
                configured=True, fingerprint=fp, updated_at=now, updated_by=user_id
            )
        elif secret_input.action == "clear":
            sec_ref = None
            sec_status = SecretStatusView(
                configured=False, fingerprint=None, updated_at=now, updated_by=user_id
            )
    return sec_ref, sec_status
