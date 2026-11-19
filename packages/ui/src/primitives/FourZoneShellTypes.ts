import type React from "react";
import {
  getOrciaIconGlyph,
  ORCIA_EIGHT_MENU_ICON_NAMES,
  type OrciaIconName,
} from "../components/icons";

export type EightFixedMenuKey =
  | "cockpit"
  | "assistant"
  | "processes"
  | "agents"
  | "spaces"
  | "finops"
  | "configuration"
  | "help";

export interface EightFixedMenuEntrySpec {
  readonly key: EightFixedMenuKey;
  readonly iconName: OrciaIconName;
  readonly icon: string;
  readonly route: string;
}

export const DEFAULT_EIGHT_FIXED_MENU_ENTRIES: readonly EightFixedMenuEntrySpec[] = [
  { key: "cockpit", iconName: ORCIA_EIGHT_MENU_ICON_NAMES.cockpit, get icon() { return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.cockpit); }, route: "/cockpit" },
  { key: "assistant", iconName: ORCIA_EIGHT_MENU_ICON_NAMES.assistant, get icon() { return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.assistant); }, route: "/assistant" },
  { key: "processes", iconName: ORCIA_EIGHT_MENU_ICON_NAMES.processes, get icon() { return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.processes); }, route: "/processes" },
  { key: "agents", iconName: ORCIA_EIGHT_MENU_ICON_NAMES.agents, get icon() { return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.agents); }, route: "/agents" },
  { key: "spaces", iconName: ORCIA_EIGHT_MENU_ICON_NAMES.spaces, get icon() { return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.spaces); }, route: "/spaces" },
  { key: "finops", iconName: ORCIA_EIGHT_MENU_ICON_NAMES.finops, get icon() { return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.finops); }, route: "/finops" },
  { key: "configuration", iconName: ORCIA_EIGHT_MENU_ICON_NAMES.configuration, get icon() { return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.configuration); }, route: "/configuration" },
  { key: "help", iconName: ORCIA_EIGHT_MENU_ICON_NAMES.help, get icon() { return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.help); }, route: "/help" },
] as const;

export type UiNotificationCenterItemKind =
  | "SETUP_PREREQUISITE"
  | "ACTION_REQUIRED"
  | "DECISION_WAITING"
  | "INFO";

export interface UiNotificationCenterItem {
  readonly id: string;
  readonly kind: UiNotificationCenterItemKind;
  readonly badgeLabel: string;
  readonly title: string;
  readonly description: string;
  readonly targetRoute?: string;
  readonly ctaLabel?: string;
  readonly triggerLabel?: string;
  readonly isAutonomousNominal?: boolean;
  readonly isAutonomousPriority?: boolean;
}

export interface ShellBreadcrumbItem {
  readonly label: string;
  readonly route?: string;
}

export interface ScopeOptionItem {
  readonly id: string;
  readonly label: string;
}

export interface DoubleScopeSelectorLabels {
  readonly teamBuLabel: string;
  readonly workspaceLabel: string;
  readonly allWorkspacesOption: string;
}

export type MobileCompanionBottomTabKey = "cockpit" | "assistant" | "decisions";

export interface MobileCompanionTabLabels {
  readonly navAriaLabel: string;
  readonly cockpit: string;
  readonly assistant: string;
  readonly decisions: string;
  readonly menuLabel: string;
}

export interface FourZoneDirectionCShellLabels {
  readonly workspacePrefix: string;
  readonly searchTriggerPlaceholder: string;
  readonly contextualHelpButtonLabel: string;
  readonly notificationsButtonLabel: string;
  readonly notificationsDrawerTitle: string;
  readonly notificationsEmptyText: string;
  readonly notificationsVsActivityHint?: string;
  readonly notificationsOpenActivityCta?: string;
  readonly autonomousNominalGroupTitle?: string;
  readonly autonomousDefaultTriggerLabel?: string;
  readonly sidebarAriaLabel: string;
  readonly railCollapseLabel: string;
  readonly railExpandLabel: string;
  readonly packSelectorLabel: string;
  readonly helpColumnTitle: string;
  readonly helpColumnExpectedTitle: string;
  readonly helpColumnExpectedBody: string;
  readonly helpColumnScrollMoreLabel?: string;
  readonly menuEntries: Record<EightFixedMenuKey, string>;
  readonly organizationMenuLabel?: string;
  readonly activityMenuLabel?: string;
  readonly doubleSelector?: DoubleScopeSelectorLabels;
  readonly mobileTabs?: MobileCompanionTabLabels;
  readonly mobileDesktopRecommendedText?: string;
}

export interface WorkspaceSwitcherOption {
  readonly id: string;
  readonly label: string;
  readonly groupLabel?: string;
}

export interface FourZoneDirectionCShellProps {
  readonly activeMenuKey: EightFixedMenuKey | null;
  readonly showOrganizationMenu?: boolean;
  readonly organizationMenuActive?: boolean;
  readonly activityMenuActive?: boolean;
  readonly breadcrumbItems?: readonly ShellBreadcrumbItem[];
  readonly onNavigateBreadcrumb?: (route: string) => void;
  readonly activeWorkspaceName: string;
  readonly activeScopeId?: string;
  readonly workspaceOptions?: readonly WorkspaceSwitcherOption[];
  readonly teamBuOptions?: readonly ScopeOptionItem[];
  readonly activeTeamBuId?: string;
  readonly onSelectTeamBu?: (scopeId: string) => void;
  readonly workspaceSelectorOptions?: readonly ScopeOptionItem[];
  readonly activeWorkspaceSelectorId?: string;
  readonly onSelectWorkspaceFromSidebar?: (scopeId: string) => void;
  readonly doubleSelectorLabels?: DoubleScopeSelectorLabels;
  readonly activePackKey: string;
  readonly availablePacks: readonly string[];
  readonly userDisplayName?: string;
  readonly userHatLabel?: string;
  readonly pendingDecisionsTotal: number;
  readonly notifications?: readonly UiNotificationCenterItem[];
  readonly onSelectNotification?: (item: UiNotificationCenterItem) => void;
  readonly viewportWidth?: number;
  readonly isDesktopOnlyRoute?: boolean;
  readonly mobileDesktopRecommendedText?: string;
  readonly activeMobileBottomTab?: MobileCompanionBottomTabKey | null;
  readonly onSelectMobileBottomTab?: (tab: MobileCompanionBottomTabKey) => void;
  readonly labels: FourZoneDirectionCShellLabels;
  readonly disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>;
  readonly hiddenMenuKeys?: readonly EightFixedMenuKey[];
  readonly onSelectMenu: (key: EightFixedMenuKey, route: string) => void;
  readonly onSelectOrganizationMenu?: (route: string) => void;
  readonly onSelectActivityMenu?: (route: string) => void;
  readonly onOpenWorkspaceSwitcher?: () => void;
  readonly onSelectWorkspace?: (scopeId: string) => void;
  readonly onOpenSearchCommand?: () => void;
  readonly onSelectPack?: (packKey: string) => void;
  readonly onOpenUserDropdown?: () => void;
  readonly headerUserControl?: React.ReactNode;
  readonly sidebarSecondarySlot?: React.ReactNode;
  readonly renderSidebarFooter?: (railCollapsed: boolean) => React.ReactNode;
  readonly helpColumnContent?: React.ReactNode;
  readonly helpColumnOpen?: boolean;
  readonly onHelpColumnOpenChange?: (open: boolean) => void;
  readonly mobileDrawerCloseSignal?: string | boolean | number;
  readonly children: React.ReactNode;
}
