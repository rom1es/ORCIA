import type { UiScopeLevel } from "./types";

export interface UiBootstrapWorkflowView {
  uri: string;
  title: string;
  requiredRole: string;
  scopeLevel: UiScopeLevel;
  gateRules: string[];
}

export interface UiBootstrapOnboardingLabels {
  panelTitle: string;
  panelSubtitle: string;
  orthogonalityTitle: string;
  orthogonalityPassBadge: string;
  orthogonalityFailBanner: string;
  simulateSingleFamilyLabel: string;
  simulateDualFamilyLabel: string;
  initWorkspaceTitle: string;
  initWorkspaceButtonLabel: string;
  initWorkspaceSuccessBanner: string;
  initDatasourceTitle: string;
  initDatasourceButtonLabel: string;
  initDatasourceSuccessBanner: string;
  humanAnchorErrorBanner: string;
  initUserTitle: string;
  initUserButtonLabel: string;
  initUserSuccessBanner: string;
  observerDeniedBanner: string;
  humanAnchorCardLabels: {
    badgeTitle: string;
    authorLabel: string;
    sectionTitle: string;
    placeholderText: string;
    signatureLabel: string;
    signaturePlaceholder: string;
    submitLabel: string;
  };
}

export type UiOntologyLevel =
  | "1_ENTERPRISE"
  | "2_DOMAIN"
  | "3_TEAM"
  | "3_WORKSPACE"
  | "4_WORKSPACE"
  | "4_RUN_EPHEMERAL";

export interface UiOntologyConceptView {
  conceptKey: string;
  canonicalTerm: string;
  level: UiOntologyLevel;
  scopeId: string;
  definitionText: string;
  immutable: boolean;
  synonyms: string[];
  profileTranslations: Record<string, string>;
  impactedTemplates: string[];
  impactedWorkflows: string[];
  impactedRuns: string[];
  canEdit?: boolean;
  canProposePromotion?: boolean;
  nextPromotionLevel?: UiOntologyLevel | null;
  nextPromotionScopeId?: string | null;
}

export interface UiTripartiteEdgeView {
  edgeKey: string;
  sourceUri: string;
  targetUri: string;
  relationType: string;
  jiraIssueKey: string | null;
}

export interface UiStaleAlertView {
  alertKey: string;
  documentKey: string;
  sourceUri: string;
  diagnosticMarker: string;
  justifyingJiraKey: string | null;
  impactedRunIds: string[];
}

export interface UiOntologyExplorerLabels {
  panelTitle: string;
  panelSubtitle: string;
  emptyStateMessage: string;
  columns: Record<Exclude<UiOntologyLevel, "4_WORKSPACE">, string> & {
    "4_WORKSPACE"?: string;
  };
  profileSelectorLabel: string;
  whatIfButtonLabel: string;
  promoteButtonLabel: string;
  promotedBannerPrefix: string;
  immutableConflictBanner: string;
  hybridRagTitle: string;
  hybridRagSearchPlaceholder: string;
  hybridRagSearchButtonLabel: string;
  tripartiteTitle: string;
  staleAlertsTitle: string;
  docObsoleteBadgeLabel: string;
  auditSubmitLabel?: string;
  auditConfluencePlaceholder?: string;
  auditGitPlaceholder?: string;
  auditJiraPlaceholder?: string;
  profileDisplayLabels?: Partial<Record<string, string>>;
  immutableRuleBadgeLabel?: string;
  impactPreviewPrefix?: string;
  impactTemplatesLabel?: string;
  impactWorkflowsLabel?: string;
  impactRunsLabel?: string;
  staleJiraPrefix?: string;
  staleRunsPrefix?: string;
}
