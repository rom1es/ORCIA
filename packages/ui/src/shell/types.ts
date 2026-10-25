export type UiModuleKey =
  | "cockpit"
  | "inbox"
  | "catalog"
  | "ontology"
  | "gates"
  | "finops"
  | "admin";

export type UiScopeLevel = "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";

export type UiAccessMode = "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";

export type UiMobileTabKey = "inbox" | "chat" | "briefing";

export type UiPersonaKey = "karim" | "claire" | "marc" | "nadia" | "partenaire";

export type UiDatasourceScheme = "git" | "jira" | "confluence" | "db" | "nexus";

export type UiFederatedScheme = "git" | "nexus" | "db" | "confluence" | "jira" | "orcia";

export type UiCatalogVisibilityScope =
  | "DRAFT"
  | "SHARED_WORKSPACE"
  | "SHARED_TEAM"
  | "SHARED_BU"
  | "PENDING_APPROVAL"
  | "PUBLISHED_ORG";

export type UiCatalogPermissionKey =
  | "DISCOVER"
  | "EXECUTE"
  | "READ_SOURCE"
  | "EDIT"
  | "ADMIN";

export interface UiShellModuleItem {
  key: UiModuleKey;
  order: number;
  route: string;
  icon: string;
  contributorBadgeCount: number;
  hasStaleWarning: boolean;
  enabled: boolean;
}

export interface UiScopeNode {
  id: string;
  level: UiScopeLevel;
  name: string;
  parentId?: string | null;
  accessMode: UiAccessMode;
}

export interface UiHumanProfileBadge {
  archetypeKey: string;
  displayName: string;
  accessMode: UiAccessMode;
  role?: string;
  orgUnitName?: string;
}

export interface UiWorkspaceDatasourceView {
  id: string;
  alias: string;
  scheme: UiDatasourceScheme;
  uri: string;
  role: string;
}

export interface UiWorkspaceCardView {
  id: string;
  name: string;
  ownerOrgUnitName: string;
  visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED";
  effectiveRole: string;
  accessMode: UiAccessMode;
  accessOrigin: "DIRECT_TEAM" | "ROLLUP_PARENT" | "PARTNER_INVITE" | "GLOBAL_ADMIN";
  finopsCostUsd: number | null;
  datasources: UiWorkspaceDatasourceView[];
}

export interface UiCatalogResourcePermissionView {
  resourceId: string;
  resourceUri: string;
  title: string;
  visibilityScope: string;
  grantedPermissions: UiCatalogPermissionKey[];
  sourceMasked: boolean;
}

export interface UiCatalogExplorerItemView {
  resourceId: string;
  uri: string;
  scheme: UiFederatedScheme;
  title: string;
  description: string;
  resourceType: "workflow" | "agent" | "skill" | "template" | "datasource";
  sourceFormat: "ORCIA" | "BMAD_PACK";
  version: string;
  sha256Short: string;
  casKey: string;
  visibilityScope: UiCatalogVisibilityScope;
  grantedPermissions: UiCatalogPermissionKey[];
  sourceMasked: boolean;
}

export interface UiRunLockTripletView {
  alias: string;
  scheme: UiFederatedScheme;
  uri: string;
  resolvedVersion: string;
  sha256Short: string;
}

export interface UiCatalogExplorerLabels {
  panelTitle: string;
  panelSubtitle: string;
  filterAllSchemesLabel: string;
  maskedSourceBadgeLabel: string;
  openSourceBadgeLabel: string;
  resolveCasButtonLabel: string;
  casResolvedBannerPrefix: string;
  promoteScopeButtonLabel: string;
  promotedBannerPrefix: string;
  promoteDeniedObserverBanner: string;
  overrideSectionTitle: string;
  overrideSectionSubtitle: string;
  overrideLayers: {
    base: string;
    teamParent: string;
    teamSub: string;
    workspace: string;
    user: string;
  };
  runLockTitle: string;
  bmadAdapterTitle: string;
  bmadImportButtonLabel: string;
  bmadImportedBanner: string;
}

export interface UiWorkspaceTopologyLabels {
  panelTitle: string;
  panelSubtitle: string;
  personaSelectorLabel: string;
  personas: Record<UiPersonaKey, string>;
  finopsRollupPrefix: string;
  confidentialExcludedNotice: string;
  datasourcesCountPrefix: string;
  catalogPermissionsTitle: string;
  sourceMaskedBadgeLabel: string;
  sourceOpenBadgeLabel: string;
  inspectSourceButtonLabel: string;
  sourceDeniedErrorBanner: string;
  sourceAllowedBannerPrefix: string;
  mutationGuardButtonLabel: string;
  mutationAllowedBanner: string;
  mutationDeniedObserverBanner: string;
}

export interface UiShellLabels {
  brandTitle: string;
  brandSubtitle: string;
  sidebarNavigationAriaLabel: string;
  sidebarToggleExpandLabel: string;
  sidebarToggleCollapseLabel: string;
  scopeSwitcherButtonLabel: string;
  scopeSwitcherDialogTitle: string;
  scopeSwitcherCloseLabel: string;
  scopeLevels: Record<UiScopeLevel, string>;
  accessModes: Record<UiAccessMode, string>;
  modules: Record<UiModuleKey, string>;
  staleWarningBadgeLabel: string;
  humanProfilePrefixLabel: string;
  conciergeDockTitle: string;
  conciergeDockSubtitle: string;
  conciergeDockToggleExpandLabel: string;
  conciergeDockToggleCollapseLabel: string;
  conciergePermissionBrokerReadyLabel: string;
  conciergeInputPlaceholder: string;
  conciergeSendLabel: string;
  localeSwitchLabel: string;
  mobileTabs: Record<UiMobileTabKey, string>;
}
