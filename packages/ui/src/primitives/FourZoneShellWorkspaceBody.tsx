import React from "react";
import { OrciaIcon } from "../components/icons";
import { FourZoneHelpAsideColumn } from "./FourZoneHelpAsideColumn";
import type {
  DoubleScopeSelectorLabels,
  EightFixedMenuKey,
  FourZoneDirectionCShellLabels,
  ScopeOptionItem,
  UnifiedScopeOptionGroup,
} from "./FourZoneShellTypes";
import { FourZoneSidebarRail } from "./FourZoneSidebarRail";

export interface FourZoneShellWorkspaceBodyProps {
  readonly isMobile: boolean;
  readonly railCollapsed: boolean;
  readonly onToggleRailCollapsed: () => void;
  readonly activeMenuKey: EightFixedMenuKey | null;
  readonly activePackKey: string;
  readonly availablePacks: readonly string[];
  readonly labels: FourZoneDirectionCShellLabels;
  readonly disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>;
  readonly hiddenMenuKeys?: readonly EightFixedMenuKey[];
  readonly onSelectMenu: (key: EightFixedMenuKey, route: string) => void;
  readonly onSelectPack?: (packKey: string) => void;
  readonly workspaceSelectorOptions?: readonly ScopeOptionItem[];
  readonly activeWorkspaceSelectorId?: string;
  readonly onSelectWorkspaceFromSidebar?: (scopeId: string) => void;
  readonly unifiedScopeGroups?: readonly UnifiedScopeOptionGroup[];
  readonly unifiedAllSpacesOption?: ScopeOptionItem;
  readonly unifiedScopeLabel?: string;
  readonly activeUnifiedScopeId?: string;
  readonly onSelectUnifiedScope?: (scopeId: string) => void;
  readonly doubleSelectorLabels?: DoubleScopeSelectorLabels;
  readonly sidebarSecondarySlot?: React.ReactNode;
  readonly renderSidebarFooter?: (railCollapsed: boolean) => React.ReactNode;
  readonly isDesktopOnlyRoute: boolean;
  readonly mobileDesktopRecommendedText?: string;
  readonly helpColumnOpen: boolean;
  readonly helpColumnContent?: React.ReactNode;
  readonly onCloseHelpColumn: () => void;
  readonly children: React.ReactNode;
}

export function FourZoneShellWorkspaceBody({
  isMobile,
  railCollapsed,
  onToggleRailCollapsed,
  activeMenuKey,
  activePackKey,
  availablePacks,
  labels,
  disabledMenuKeys,
  hiddenMenuKeys,
  onSelectMenu,
  onSelectPack,
  workspaceSelectorOptions,
  activeWorkspaceSelectorId,
  onSelectWorkspaceFromSidebar,
  unifiedScopeGroups,
  unifiedAllSpacesOption,
  unifiedScopeLabel,
  activeUnifiedScopeId,
  onSelectUnifiedScope,
  doubleSelectorLabels,
  sidebarSecondarySlot,
  renderSidebarFooter,
  isDesktopOnlyRoute,
  mobileDesktopRecommendedText,
  helpColumnOpen,
  helpColumnContent,
  onCloseHelpColumn,
  children,
}: FourZoneShellWorkspaceBodyProps): React.ReactElement {
  const recommendedMsg =
    mobileDesktopRecommendedText ?? labels.mobileDesktopRecommendedText ?? "";
  return (
    <div className={isMobile ? "flex min-h-0 flex-1" : "flex min-h-0 flex-1 overflow-hidden"}>
      {!isMobile && (
        <FourZoneSidebarRail
          railCollapsed={railCollapsed}
          onToggleRailCollapsed={onToggleRailCollapsed}
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
        />
      )}

      <main
        data-testid="four-zone-central-workspace"
        className={
          isMobile
            ? "min-h-0 min-w-0 flex-1 p-3 pb-20"
            : "relative h-full min-h-0 min-w-0 flex-1 overflow-y-auto p-6"
        }
        style={{
          overflowY: isMobile ? undefined : "auto",
          backgroundColor: "var(--color-bg-canvas)",
        }}
      >
        {isMobile && isDesktopOnlyRoute && recommendedMsg && (
          <div
            role="status"
            data-testid="mobile-desktop-recommended-banner"
            className="mb-3 flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-state-warning, var(--color-border-subtle))",
              color: "var(--color-text-primary)",
            }}
          >
            <OrciaIcon name="desktop" size={14} />
            <span>{recommendedMsg}</span>
          </div>
        )}
        {children}
      </main>

      {helpColumnOpen && (
        <FourZoneHelpAsideColumn
          isMobile={isMobile}
          labels={labels}
          helpColumnContent={helpColumnContent}
          onClose={onCloseHelpColumn}
        />
      )}
    </div>
  );
}
