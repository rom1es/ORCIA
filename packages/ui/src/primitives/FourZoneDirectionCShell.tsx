import React, { useEffect, useState } from "react";
import {
  getOrciaIconGlyph,
  ORCIA_EIGHT_MENU_ICON_NAMES,
  OrciaIcon,
  type OrciaIconName,
} from "../components/icons";
import { FourZoneNotificationsDrawer } from "./FourZoneNotificationsDrawer";
import { FourZoneSidebarRail } from "./FourZoneSidebarRail";
import { FourZoneTopHeaderSection } from "./FourZoneTopHeaderSection";

export type EightFixedMenuKey =
  | "cockpit"
  | "assistant"
  | "processes"
  | "agents"
  | "spaces"
  | "finops"
  | "configuration"
  | "glossary";

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
  { key: "glossary", iconName: ORCIA_EIGHT_MENU_ICON_NAMES.glossary, get icon() { return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.glossary); }, route: "/ontology" },
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
  readonly menuEntries: Record<EightFixedMenuKey, string>;
  readonly organizationMenuLabel?: string;
  readonly activityMenuLabel?: string;
}

export interface WorkspaceSwitcherOption {
  readonly id: string;
  readonly label: string;
  readonly groupLabel?: string;
}

export interface FourZoneDirectionCShellProps {
  readonly activeMenuKey: EightFixedMenuKey;
  readonly showOrganizationMenu?: boolean;
  readonly organizationMenuActive?: boolean;
  readonly activityMenuActive?: boolean;
  readonly activeWorkspaceName: string;
  readonly activeScopeId?: string;
  readonly workspaceOptions?: readonly WorkspaceSwitcherOption[];
  readonly activePackKey: string;
  readonly availablePacks: readonly string[];
  readonly userDisplayName?: string;
  readonly userHatLabel?: string;
  readonly pendingDecisionsTotal: number;
  readonly notifications?: readonly UiNotificationCenterItem[];
  readonly onSelectNotification?: (item: UiNotificationCenterItem) => void;
  readonly viewportWidth?: number;
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
  readonly children: React.ReactNode;
}

export function computeDefaultHelpColumnOpen(
  viewportWidth: number,
  pendingDecisionsTotal: number,
): boolean {
  if (viewportWidth < 1024) {
    return false;
  }
  if (viewportWidth < 1440 && pendingDecisionsTotal >= 1) {
    return false;
  }
  return true;
}

export function FourZoneDirectionCShell({
  activeMenuKey,
  showOrganizationMenu = false,
  organizationMenuActive = false,
  activityMenuActive = false,
  activeWorkspaceName,
  activeScopeId,
  workspaceOptions,
  activePackKey,
  availablePacks,
  userDisplayName,
  userHatLabel,
  pendingDecisionsTotal,
  notifications = [],
  onSelectNotification,
  viewportWidth = 1440,
  labels,
  disabledMenuKeys,
  hiddenMenuKeys,
  onSelectMenu,
  onSelectOrganizationMenu,
  onSelectActivityMenu,
  onOpenWorkspaceSwitcher,
  onSelectWorkspace,
  onOpenSearchCommand,
  onSelectPack,
  onOpenUserDropdown,
  headerUserControl,
  sidebarSecondarySlot,
  renderSidebarFooter,
  helpColumnContent,
  helpColumnOpen: controlledHelpColumnOpen,
  onHelpColumnOpenChange,
  children,
}: FourZoneDirectionCShellProps): React.ReactElement {
  const [railCollapsed, setRailCollapsed] = useState<boolean>(() => viewportWidth < 768);
  const [notificationsOpen, setNotificationsOpen] = useState<boolean>(false);
  const [workspaceDropdownOpen, setWorkspaceDropdownOpen] = useState<boolean>(false);
  const [internalHelpColumnOpen, setInternalHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(viewportWidth, pendingDecisionsTotal),
  );

  const helpColumnOpen =
    controlledHelpColumnOpen !== undefined
      ? controlledHelpColumnOpen
      : internalHelpColumnOpen;

  const updateHelpColumnOpen = (nextOpen: boolean): void => {
    setInternalHelpColumnOpen(nextOpen);
    onHelpColumnOpenChange?.(nextOpen);
  };

  useEffect(() => {
    if (controlledHelpColumnOpen === undefined) {
      setInternalHelpColumnOpen(
        computeDefaultHelpColumnOpen(viewportWidth, pendingDecisionsTotal),
      );
    }
  }, [viewportWidth, pendingDecisionsTotal, controlledHelpColumnOpen]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement | null;
      const isEditable =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        Boolean(target?.isContentEditable);
      if (event.key === "[" && !isEditable) {
        setRailCollapsed((prev) => !prev);
      } else if (event.key === "Escape") {
        setNotificationsOpen(false);
        setWorkspaceDropdownOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const effectiveNotificationCount =
    notifications.length > 0 ? notifications.length : pendingDecisionsTotal;

  return (
    <div
      data-testid="four-zone-direction-c-shell"
      className="flex h-screen min-h-screen flex-col overflow-hidden"
      style={{
        height: "100vh",
        overflow: "hidden",
        backgroundColor: "var(--color-bg-canvas)",
        color: "var(--color-text-primary)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <FourZoneTopHeaderSection
        activeWorkspaceName={activeWorkspaceName}
        activeScopeId={activeScopeId}
        workspaceOptions={workspaceOptions}
        workspaceDropdownOpen={workspaceDropdownOpen}
        onToggleWorkspaceDropdown={() => setWorkspaceDropdownOpen((prev) => !prev)}
        onCloseWorkspaceDropdown={() => setWorkspaceDropdownOpen(false)}
        onOpenWorkspaceSwitcher={onOpenWorkspaceSwitcher}
        onSelectWorkspace={onSelectWorkspace}
        onOpenSearchCommand={onOpenSearchCommand}
        helpColumnOpen={helpColumnOpen}
        onToggleHelpColumn={() => updateHelpColumnOpen(!helpColumnOpen)}
        notificationsOpen={notificationsOpen}
        onToggleNotifications={() => setNotificationsOpen((prev) => !prev)}
        effectiveNotificationCount={effectiveNotificationCount}
        labels={labels}
      />

      {notificationsOpen && (
        <FourZoneNotificationsDrawer
          notifications={notifications}
          labels={labels}
          onClose={() => setNotificationsOpen(false)}
          onSelectNotification={onSelectNotification}
          onSelectActivityMenu={onSelectActivityMenu}
          onSelectMenu={onSelectMenu}
        />
      )}

      <div
        className="flex min-h-0 flex-1 overflow-hidden"
        style={{ height: "calc(100vh - 52px)", overflow: "hidden" }}
      >
        <FourZoneSidebarRail
          railCollapsed={railCollapsed}
          onToggleRailCollapsed={() => setRailCollapsed((prev) => !prev)}
          activeMenuKey={activeMenuKey}
          showOrganizationMenu={showOrganizationMenu}
          organizationMenuActive={organizationMenuActive}
          activityMenuActive={activityMenuActive}
          activePackKey={activePackKey}
          availablePacks={availablePacks}
          labels={labels}
          disabledMenuKeys={disabledMenuKeys}
          hiddenMenuKeys={hiddenMenuKeys}
          onSelectMenu={onSelectMenu}
          onSelectOrganizationMenu={onSelectOrganizationMenu}
          onSelectActivityMenu={onSelectActivityMenu}
          onSelectPack={onSelectPack}
          sidebarSecondarySlot={sidebarSecondarySlot}
          renderSidebarFooter={renderSidebarFooter}
        />

        <main
          data-testid="four-zone-central-workspace"
          className="min-h-0 min-w-0 flex-1 overflow-y-auto p-6"
          style={{
            maxHeight: "calc(100vh - 52px)",
            overflowY: "auto",
            backgroundColor: "var(--color-bg-canvas)",
          }}
        >
          {children}
        </main>

        {helpColumnOpen && (
          <aside
            data-testid="four-zone-contextual-help-column"
            className="min-h-0 shrink-0 overflow-y-auto border-l p-4"
            style={{
              width: "340px",
              maxHeight: "calc(100vh - 52px)",
              overflowY: "auto",
              position: "sticky",
              top: "52px",
              backgroundColor: "var(--color-bg-surface)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold">{labels.helpColumnTitle}</h2>
              <button
                type="button"
                data-testid="contextual-help-close-btn"
                onClick={() => updateHelpColumnOpen(false)}
                className="text-xs"
              >
                <OrciaIcon name="close" />
              </button>
            </div>
            <div
              className="mt-3 rounded border p-3"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <h3 className="text-xs font-semibold">{labels.helpColumnExpectedTitle}</h3>
              <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                {labels.helpColumnExpectedBody}
              </p>
            </div>
            {helpColumnContent && <div className="mt-3">{helpColumnContent}</div>}
          </aside>
        )}
      </div>
    </div>
  );
}
