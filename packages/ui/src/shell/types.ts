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
