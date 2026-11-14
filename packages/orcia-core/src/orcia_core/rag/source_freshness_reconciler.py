"""Differential Freshness Reconciler & 24h Probe Logic (`FR-23`, `FR-24`, `AD-12`, `AD-19`).

Pure domain hexagonal service — zero SQL, zero HTTP/FastAPI dependencies.
Guarantees 0 $ LLM cost on quiet weekends (Arbitrage 2A) and lightweight AST indexing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

RECONCILE_OUTCOME_NO_OP_UNCHANGED = "NO_OP_UNCHANGED"
RECONCILE_OUTCOME_DELTA_SYNC_REQUIRED = "DELTA_SYNC_REQUIRED"
RECONCILE_OUTCOME_QUIET_UNCHANGED = "QUIET_UNCHANGED"
RECONCILE_OUTCOME_AUTO_HEAL_DELTA_SYNC = "AUTO_HEAL_DELTA_SYNC"
RECONCILE_OUTCOME_STALE_DETECTED = "STALE_DETECTED"
RECONCILE_OUTCOME_RECENT_SIGNALS_OK = "RECENT_SIGNALS_OK"

FRESHNESS_STATUS_SYNCED = "SYNCED"
FRESHNESS_STATUS_STALE = "STALE"
FRESHNESS_STATUS_SYNC_ERROR = "SYNC_ERROR"


def normalize_fingerprint(fingerprint: str | None) -> str:
    """Normalize a SHA-256 fingerprint string (lowercase, stripped)."""
    if fingerprint is None:
        return ""
    return fingerprint.strip().lower()


def reconcile_incoming_fingerprint(
    stored_hash: str | None,
    incoming_hash: str,
) -> str:
    """Compare stored and incoming fingerprints (0 $ LLM if unchanged).

    Returns:
        "NO_OP_UNCHANGED" if hashes match identically.
        "DELTA_SYNC_REQUIRED" if hashes differ or stored hash is None.
    """
    normalized_stored = normalize_fingerprint(stored_hash)
    normalized_incoming = normalize_fingerprint(incoming_hash)
    if normalized_stored and normalized_stored == normalized_incoming:
        return RECONCILE_OUTCOME_NO_OP_UNCHANGED
    return RECONCILE_OUTCOME_DELTA_SYNC_REQUIRED


class RemoteFingerprintProbePort(Protocol):
    """Hexagonal SPI port for active remote fingerprint probing (0 $ LLM)."""

    async def probe_remote_fingerprint(
        self,
        *,
        datasource_id: str,
        target_ref: str | None = None,
        target_scope: str | None = None,
    ) -> str | None:
        """Probe remote repository or datasource head SHA or revision hash."""
        ...


@dataclass(frozen=True, slots=True)
class FreshnessEvaluationResult:
    """Immutable result of a 24h freshness evaluation."""

    freshness_status: str
    outcome: str
    elapsed_hours: float
    delta_sync_needed: bool
    stored_fingerprint: str | None
    probed_fingerprint: str | None


async def evaluate_24h_freshness_probe(
    *,
    stored_hash: str | None,
    last_signal_at: datetime | None,
    current_time: datetime | None = None,
    probe: RemoteFingerprintProbePort | None = None,
    datasource_id: str = "",
    target_ref: str | None = None,
    target_scope: str | None = None,
) -> FreshnessEvaluationResult:
    """Evaluate datasource freshness and probe remote status if > 24h since last signal.

    Decision Matrix (Arbitrage 2A):
    - elapsed_hours <= 24.0: SYNCED / RECENT_SIGNALS_OK (no probe required)
    - elapsed_hours > 24.0 and probe returns matching hash:
      SYNCED / QUIET_UNCHANGED (quiet weekend, 0 $ LLM cost)
    - elapsed_hours > 24.0 and probe returns different hash:
      SYNCED / AUTO_HEAL_DELTA_SYNC (delta sync needed)
    - elapsed_hours > 24.0 and probe fails or absent:
      STALE / STALE_DETECTED (marks datasource stale and alerts)
    """
    now = current_time or datetime.now(UTC)
    if last_signal_at is None:
        elapsed_hours = 999999.0
    else:
        if last_signal_at.tzinfo is None:
            last_signal_at = last_signal_at.replace(tzinfo=UTC)
        elapsed_seconds = max(0.0, (now - last_signal_at).total_seconds())
        elapsed_hours = elapsed_seconds / 3600.0

    norm_stored = normalize_fingerprint(stored_hash) or None

    if elapsed_hours <= 24.0:
        return FreshnessEvaluationResult(
            freshness_status=FRESHNESS_STATUS_SYNCED,
            outcome=RECONCILE_OUTCOME_RECENT_SIGNALS_OK,
            elapsed_hours=round(elapsed_hours, 2),
            delta_sync_needed=False,
            stored_fingerprint=norm_stored,
            probed_fingerprint=norm_stored,
        )

    # > 24h without signal: probe remote state
    if probe is not None:
        try:
            raw_probed = await probe.probe_remote_fingerprint(
                datasource_id=datasource_id,
                target_ref=target_ref,
                target_scope=target_scope,
            )
            norm_probed = normalize_fingerprint(raw_probed) or None
        except Exception:
            norm_probed = None

        if norm_probed is not None:
            if norm_stored and norm_stored == norm_probed:
                # Quiet source (e.g. weekend): maintain SYNCED at 0 $ LLM cost
                return FreshnessEvaluationResult(
                    freshness_status=FRESHNESS_STATUS_SYNCED,
                    outcome=RECONCILE_OUTCOME_QUIET_UNCHANGED,
                    elapsed_hours=round(elapsed_hours, 2),
                    delta_sync_needed=False,
                    stored_fingerprint=norm_stored,
                    probed_fingerprint=norm_probed,
                )
            # Diverged hash: trigger auto-heal delta sync
            return FreshnessEvaluationResult(
                freshness_status=FRESHNESS_STATUS_SYNCED,
                outcome=RECONCILE_OUTCOME_AUTO_HEAL_DELTA_SYNC,
                elapsed_hours=round(elapsed_hours, 2),
                delta_sync_needed=True,
                stored_fingerprint=norm_stored,
                probed_fingerprint=norm_probed,
            )

    # Probe absent or failed after 24h
    return FreshnessEvaluationResult(
        freshness_status=FRESHNESS_STATUS_STALE,
        outcome=RECONCILE_OUTCOME_STALE_DETECTED,
        elapsed_hours=round(elapsed_hours, 2),
        delta_sync_needed=False,
        stored_fingerprint=norm_stored,
        probed_fingerprint=None,
    )


def compute_content_sha256(content: str | bytes) -> str:
    """Compute standard lowercase SHA-256 hex digest of raw content."""
    content_bytes = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(content_bytes).hexdigest()
