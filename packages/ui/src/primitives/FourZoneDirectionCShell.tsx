import React, { useEffect, useState } from "react";
import { useResponsiveBreakpoint } from "../hooks/useResponsiveBreakpoint";
import { FourZoneNotificationsDrawer } from "./FourZoneNotificationsDrawer";
import {
  DEFAULT_EIGHT_FIXED_MENU_ENTRIES,
  type DoubleScopeSelectorLabels,
  type EightFixedMenuEntrySpec,
  type EightFixedMenuKey,
  type FourZoneDirectionCShellLabels,
  type FourZoneDirectionCShellProps,
  type MobileCompanionBottomTabKey,
  type MobileCompanionTabLabels,
  type ScopeOptionItem,
  type ShellBreadcrumbItem,
  type UiNotificationCenterItem,
  type UiNotificationCenterItemKind,
  type UnifiedScopeOptionGroup,
  type WorkspaceSwitcherOption,
} from "./FourZoneShellTypes";
import { FourZoneShellWorkspaceBody } from "./FourZoneShellWorkspaceBody";
import { FourZoneTopHeaderSection } from "./FourZoneTopHeaderSection";
import {
  MobileCompanionBottomBar,
  MobileShellNavigationDrawer,
} from "./MobileCompanionBottomBar";
import { useFourZoneShellHotkeys } from "./useFourZoneShellHotkeys";

export {
  DEFAULT_EIGHT_FIXED_MENU_ENTRIES,
  type DoubleScopeSelectorLabels,
  type EightFixedMenuEntrySpec,
  type EightFixedMenuKey,
  type FourZoneDirectionCShellLabels,
  type FourZoneDirectionCShellProps,
  type MobileCompanionBottomTabKey,
  type MobileCompanionTabLabels,
  type ScopeOptionItem,
  type ShellBreadcrumbItem,
  type UiNotificationCenterItem,
  type UiNotificationCenterItemKind,
  type UnifiedScopeOptionGroup,
  type WorkspaceSwitcherOption,
};

export function computeDefaultHelpColumnOpen(
  viewportWidth: number,
  pendingDecisionsTotal: number,
): boolean {
  if (viewportWidth < 1024) return false;
  if (viewportWidth < 1440 && pendingDecisionsTotal >= 1) return false;
  return true;
}

export function FourZoneDirectionCShell({
  activeMenuKey,
  breadcrumbItems,
  onNavigateBreadcrumb,
  activeWorkspaceName,
  activeScopeId,
  workspaceOptions,
  workspaceSelectorOptions,
  activeWorkspaceSelectorId,
  onSelectWorkspaceFromSidebar,
  unifiedScopeGroups,
  unifiedAllSpacesOption,
  unifiedScopeLabel,
  activeUnifiedScopeId,
  onSelectUnifiedScope,
  onNavigateHome,
  doubleSelectorLabels,
  activePackKey,
  availablePacks,
  pendingDecisionsTotal,
  notifications = [],
  onSelectNotification,
  viewportWidth,
  isDesktopOnlyRoute = false,
  mobileDesktopRecommendedText,
  activeMobileBottomTab = null,
  onSelectMobileBottomTab,
  labels,
  disabledMenuKeys,
  hiddenMenuKeys,
  onSelectMenu,
  onSelectActivityMenu,
  onOpenWorkspaceSwitcher,
  onSelectWorkspace,
  onOpenSearchCommand,
  onSelectPack,
  sidebarSecondarySlot,
  renderSidebarFooter,
  helpColumnContent,
  helpColumnOpen: controlledHelpColumnOpen,
  onHelpColumnOpenChange,
  mobileDrawerCloseSignal,
  children,
}: FourZoneDirectionCShellProps): React.ReactElement {
  const { viewportWidthPx, tier, isMobile } = useResponsiveBreakpoint(viewportWidth);
  const [railCollapsed, setRailCollapsed] = useState<boolean>(() => isMobile);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [notificationsOpen, setNotificationsOpen] = useState<boolean>(false);
  const [workspaceDropdownOpen, setWorkspaceDropdownOpen] = useState<boolean>(false);
  const [internalHelpColumnOpen, setInternalHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(viewportWidthPx, pendingDecisionsTotal),
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
        computeDefaultHelpColumnOpen(viewportWidthPx, pendingDecisionsTotal),
      );
    }
  }, [viewportWidthPx, pendingDecisionsTotal, controlledHelpColumnOpen]);

  const breadcrumbSig = (breadcrumbItems ?? [])
    .map((item) => item.route ?? item.label)
    .join("|");

  useEffect(() => {
    if (!isMobile) setMobileMenuOpen(false);
  }, [isMobile]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [breadcrumbSig, mobileDrawerCloseSignal]);

  useFourZoneShellHotkeys({
    onToggleRailCollapsed: () => setRailCollapsed((prev) => !prev),
    onEscapeClose: () => {
      setNotificationsOpen(false);
      setWorkspaceDropdownOpen(false);
      setMobileMenuOpen(false);
    },
  });

  const effectiveNotificationCount =
    notifications.length > 0 ? notifications.length : pendingDecisionsTotal;

  const mobileTabsLabels: MobileCompanionTabLabels = labels.mobileTabs ?? {
    navAriaLabel: labels.sidebarAriaLabel,
    cockpit: labels.menuEntries.cockpit,
    assistant: labels.menuEntries.assistant,
    decisions: labels.notificationsButtonLabel,
    menuLabel: labels.sidebarAriaLabel,
  };

  const resolvedMobileTab: MobileCompanionBottomTabKey | null =
    activeMobileBottomTab ??
    (activeMenuKey === "cockpit"
      ? "cockpit"
      : activeMenuKey === "assistant"
        ? "assistant"
        : null);

  return (
    <div
      data-testid="four-zone-direction-c-shell"
      data-breakpoint-tier={tier}
      className={
        isMobile
          ? "flex min-h-screen flex-col"
          : "relative flex h-dvh max-h-dvh flex-col overflow-hidden"
      }
      style={{
        height: isMobile ? "auto" : "100dvh",
        maxHeight: isMobile ? undefined : "100dvh",
        minHeight: isMobile ? "100vh" : undefined,
        overflow: isMobile ? "visible" : "hidden",
        backgroundColor: "var(--color-bg-canvas)",
        color: "var(--color-text-primary)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <FourZoneTopHeaderSection
        isMobile={isMobile}
        railCollapsed={railCollapsed}
        mobileMenuOpen={mobileMenuOpen}
        onToggleMobileMenu={() => setMobileMenuOpen((prev) => !prev)}
        breadcrumbItems={breadcrumbItems}
        onNavigateBreadcrumb={onNavigateBreadcrumb}
        onNavigateHome={
          onNavigateHome ??
          (() => {
            if (onNavigateBreadcrumb) onNavigateBreadcrumb("/cockpit");
            else onSelectMenu("cockpit", "/cockpit");
          })
        }
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

      {isMobile && (
        <MobileShellNavigationDrawer
          open={mobileMenuOpen}
          activeMenuKey={activeMenuKey}
          labels={labels}
          disabledMenuKeys={disabledMenuKeys}
          hiddenMenuKeys={hiddenMenuKeys}
          workspaceSelectorOptions={workspaceSelectorOptions}
          activeWorkspaceSelectorId={activeWorkspaceSelectorId}
          onSelectWorkspaceFromSidebar={onSelectWorkspaceFromSidebar}
          unifiedScopeGroups={unifiedScopeGroups}
          unifiedAllSpacesOption={unifiedAllSpacesOption}
          unifiedScopeLabel={unifiedScopeLabel}
          activeUnifiedScopeId={activeUnifiedScopeId}
          onSelectUnifiedScope={onSelectUnifiedScope}
          doubleSelectorLabels={doubleSelectorLabels}
          renderSidebarFooter={renderSidebarFooter}
          onSelectMenu={onSelectMenu}
          onClose={() => setMobileMenuOpen(false)}
        />
      )}

      <FourZoneShellWorkspaceBody
        isMobile={isMobile}
        railCollapsed={railCollapsed}
        onToggleRailCollapsed={() => setRailCollapsed((prev) => !prev)}
        activeMenuKey={activeMenuKey}
        activePackKey={activePackKey}
        availablePacks={availablePacks}
        labels={labels}
        disabledMenuKeys={disabledMenuKeys}
        hiddenMenuKeys={hiddenMenuKeys}
        onSelectMenu={onSelectMenu}
        onSelectPack={onSelectPack}
        workspaceSelectorOptions={workspaceSelectorOptions}
        activeWorkspaceSelectorId={activeWorkspaceSelectorId}
        onSelectWorkspaceFromSidebar={onSelectWorkspaceFromSidebar}
        unifiedScopeGroups={unifiedScopeGroups}
        unifiedAllSpacesOption={unifiedAllSpacesOption}
        unifiedScopeLabel={unifiedScopeLabel}
        activeUnifiedScopeId={activeUnifiedScopeId}
        onSelectUnifiedScope={onSelectUnifiedScope}
        doubleSelectorLabels={doubleSelectorLabels}
        sidebarSecondarySlot={sidebarSecondarySlot}
        renderSidebarFooter={renderSidebarFooter}
        isDesktopOnlyRoute={isDesktopOnlyRoute}
        mobileDesktopRecommendedText={mobileDesktopRecommendedText}
        helpColumnOpen={helpColumnOpen}
        helpColumnContent={helpColumnContent}
        onCloseHelpColumn={() => updateHelpColumnOpen(false)}
      >
        {children}
      </FourZoneShellWorkspaceBody>

      {isMobile && (
        <MobileCompanionBottomBar
          activeTab={resolvedMobileTab}
          labels={mobileTabsLabels}
          onSelectTab={(tab) => {
            if (onSelectMobileBottomTab) {
              onSelectMobileBottomTab(tab);
              return;
            }
            if (tab === "cockpit") {
              onSelectMenu("cockpit", "/cockpit");
            } else if (tab === "assistant") {
              onSelectMenu("assistant", "/assistant");
            } else {
              onSelectMenu("assistant", "/inbox");
            }
          }}
        />
      )}
    </div>
  );
}
