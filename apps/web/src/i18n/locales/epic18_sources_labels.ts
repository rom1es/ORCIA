/**
 * Story 18.1 — Bilingual FR / EN label types and re-exports for Workspace Multi-Nature Sources & GitNexus Governance.
 *
 * Strict Direction C token alignment, zero raw string in JSX.
 */

export interface Epic18SourcesLabels {
  filters: {
    all: string;
    docKb: string;
    tracker: string;
    code: string;
    schema: string;
  };
  columns: {
    nature: string;
    alias: string;
    connector: string;
    target: string;
    mode: string;
    freshness: string;
    gitnexus: string;
    actions: string;
  };
  syncModes: {
    webhook: string;
    polling24h: string;
  };
  freshnessStatuses: {
    synced: string;
    stale: string;
    syncError: string;
    pendingInitial: string;
  };
  codegraph: {
    title: string;
    switchLabel: string;
    readyBadge: string;
    indexingBadge: string;
    disabledBadge: string;
    pausedBadge: string;
    serviceAccountLabel: string;
    leadTokenLabel: string;
    leadRequiredTooltip: string;
    switchNotice: string;
  };
  actions: {
    syncBtn: string;
    syncTriggered: string;
    attachSourceBtn: string;
    editSourceBtn: string;
    deleteSourceBtn: string;
    deleteConfirmTitle: string;
    deleteConfirmDesc: string;
    cancelBtn: string;
    confirmDeleteBtn: string;
    saveBtn: string;
    createSuccess: string;
    updateSuccess: string;
    deleteSuccess: string;
    reconcileBtn: string;
    reconciling: string;
    reconcileSuccess: string;
  };
  modal: {
    createTitle: string;
    editTitle: string;
    description: string;
    natureLabel: string;
    natureDoc: string;
    natureTracker: string;
    natureCode: string;
    natureSchema: string;
    aliasLabel: string;
    aliasPlaceholder: string;
    schemeLabel: string;
    uriLabel: string;
    uriPlaceholder: string;
    targetScopeLabel: string;
    targetRefLabel: string;
    connectorLabel: string;
    connectorNone: string;
    syncModeLabel: string;
    ragIdentityLabel: string;
    ragServiceAccount: string;
    ragReferentUser: string;
    referentUserIdLabel: string;
    serviceAccountIdLabel: string;
    gitnexusSectionTitle: string;
    gitnexusEnableLabel: string;
    gitnexusAuthModeLabel: string;
    gitnexusOwnerUserLabel: string;
    observerBlockedError: string;
    leadRequiredError: string;
    ragEmbeddingRequiredTitle: string;
    ragEmbeddingRequiredDescription: string;
    ragEmbeddingRequiredCta: string;
    ragOptionDisabledSuffix: string;
    cancelBtn: string;
    updateBtn: string;
    attachBtn: string;
  };
  settingsDeportBanner: {
    title: string;
    description: string;
    buttonLabel: string;
  };
}

export { EPIC18_SOURCES_LABELS_FR } from "./epic18_sources_labels_fr";
export { EPIC18_SOURCES_LABELS_EN } from "./epic18_sources_labels_en";
