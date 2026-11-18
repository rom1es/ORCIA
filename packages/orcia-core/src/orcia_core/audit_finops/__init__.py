"""Bounded Context 8: Audit & FinOps (Append-Only Ledger, Token Cost Tracking & Circuit Breaker)."""

from __future__ import annotations

from orcia_core.audit_finops._internal.sql_audit_ledger import SqlAuditLedgerService
from orcia_core.audit_finops._internal.sql_user_profile_stats import (
    fetch_user_profile_summary_sql,
)
from orcia_core.audit_finops.budget_guard_service import BudgetGuardService
from orcia_core.audit_finops.cognitive_impact_service import (
    CognitiveImpactService,
    CognitiveMasteryDashboard,
    GatePolicyRecommendation,
    WorkflowCognitiveMetrics,
)
from orcia_core.audit_finops.connector_quota_service import SqlConnectorQuotaGuardService
from orcia_core.audit_finops.errors import (
    AuditLedgerImmutableViolationError,
    AuditRunNotFoundError,
)
from orcia_core.audit_finops.finops_accounting_service import FinopsAccountingService
from orcia_core.audit_finops.finops_models import (
    DEFAULT_AMORTIZATION_RUNS,
    DEFAULT_EUR_USD_RATE,
    DEFAULT_HOURLY_RATE_USD,
    ConnectorQuotaRecord,
    FinopsBreakdown,
    FinopsBudgetOverride,
    FinopsOverview,
    FinopsProcessItem,
    FinopsScopeBudget,
    FinopsTierEffortItem,
    FinopsWorkflowBaseline,
    ScopeType,
)
from orcia_core.audit_finops.models import (
    AuditLedgerEntry,
    AuditLedgerFilterParams,
    AuditProvenanceExport,
    AuditProvenanceSummary,
    AuditTimeWindow,
)
from orcia_core.audit_finops.outbox_subscriber import (
    AUDITABLE_EVENT_TYPES,
    AuditLedgerOutboxSubscriber,
    map_domain_event_to_ledger_entry,
)
from orcia_core.audit_finops.post_hoc_audit import (
    AutonomousGovernanceMetrics,
    PostHocAuditSampleRecord,
    PostHocAuditService,
    PostHocReviewStatus,
    compute_autonomous_governance_metrics,
    select_post_hoc_sample_deterministic,
)
from orcia_core.audit_finops.provenance_exporter import ProvenanceExporterService
from orcia_core.audit_finops.remote_usage_sanitizer import (
    RemoteUsageSanitizer,
    extract_remote_usage_payload,
)
from orcia_core.audit_finops.user_profile_service import (
    PopularItemType,
    PopularUsageItem,
    UserProfileSummary,
    compute_activity_streaks,
    derive_user_handle,
    rank_popular_usage_items,
)

DOMAIN_NAME: str = "audit_finops"

__all__ = [
    "AUDITABLE_EVENT_TYPES",
    "AuditLedgerEntry",
    "AuditLedgerFilterParams",
    "AuditLedgerImmutableViolationError",
    "AuditLedgerOutboxSubscriber",
    "AuditProvenanceExport",
    "AuditProvenanceSummary",
    "AuditRunNotFoundError",
    "AuditTimeWindow",
    "AutonomousGovernanceMetrics",
    "BudgetGuardService",
    "CognitiveImpactService",
    "CognitiveMasteryDashboard",
    "ConnectorQuotaRecord",
    "DEFAULT_AMORTIZATION_RUNS",
    "DEFAULT_EUR_USD_RATE",
    "DEFAULT_HOURLY_RATE_USD",
    "DOMAIN_NAME",
    "FinopsAccountingService",
    "FinopsBreakdown",
    "FinopsBudgetOverride",
    "FinopsOverview",
    "FinopsProcessItem",
    "FinopsScopeBudget",
    "FinopsTierEffortItem",
    "FinopsWorkflowBaseline",
    "GatePolicyRecommendation",
    "PopularItemType",
    "PopularUsageItem",
    "PostHocAuditSampleRecord",
    "PostHocAuditService",
    "PostHocReviewStatus",
    "ProvenanceExporterService",
    "RemoteUsageSanitizer",
    "ScopeType",
    "SqlAuditLedgerService",
    "SqlConnectorQuotaGuardService",
    "UserProfileSummary",
    "WorkflowCognitiveMetrics",
    "compute_activity_streaks",
    "compute_autonomous_governance_metrics",
    "derive_user_handle",
    "extract_remote_usage_payload",
    "fetch_user_profile_summary_sql",
    "map_domain_event_to_ledger_entry",
    "rank_popular_usage_items",
    "select_post_hoc_sample_deterministic",
]
