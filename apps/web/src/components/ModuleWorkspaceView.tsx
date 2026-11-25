import {
  ORCIA_MODULE_ICON_NAMES,
  OrciaPageHeader,
  StatusBadge,
  type UiModuleKey,
} from "@orcia/ui";
import React from "react";
import { AdminFeaturePanel } from "../features/admin";
import { CatalogFeaturePanel } from "../features/catalog";
import { CockpitFeaturePanel } from "../features/cockpit";
import { FinopsFeaturePanel } from "../features/finops";
import { GatesFeaturePanel } from "../features/gates";
import { InboxFeaturePanel } from "../features/inbox";
import { OntologyFeaturePanel } from "../features/ontology";
import { WorkspacesFeaturePanel } from "../features/workspaces";
import { useI18n } from "../i18n";
import { useOrciaNavigation } from "./navigationAdapter";
import { useShellNavigation } from "./ShellContainer";

export interface ModuleWorkspaceViewProps {
  readonly moduleKey: UiModuleKey;
  readonly initialWorkspaceId?: string;
  readonly initialTab?: string;
  readonly catalogMode?: "catalog" | "agents";
  readonly inboxMode?: "assistant" | "notifications";
}

export function ModuleWorkspaceView({
  moduleKey,
  initialWorkspaceId,
  initialTab,
  catalogMode,
  inboxMode,
}: ModuleWorkspaceViewProps) {
  const { dictionary } = useI18n();
  const { pathname } = useOrciaNavigation();
  const { activeModuleKey } = useShellNavigation();

  const currentModule = activeModuleKey ?? moduleKey;
  const isInboxNotifications =
    currentModule === "inbox" &&
    (inboxMode === "notifications" || Boolean(pathname?.startsWith("/inbox")));
  const pageCopy = dictionary.modulePages[currentModule];
  const headerSubtitle = isInboxNotifications
    ? dictionary.shellChrome.inboxNotificationsSubtitle
    : pageCopy.subtitle;
  const headerDescription = isInboxNotifications
    ? dictionary.shellChrome.inboxNotificationsDescription
    : pageCopy.description;

  return (
    <div
      data-testid={`module-view-${currentModule}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "20px",
      }}
    >
      {currentModule === "cockpit" ||
      currentModule === "catalog" ||
      currentModule === "finops" ||
      currentModule === "inbox" ||
      currentModule === "admin" ? null : (
        <OrciaPageHeader
          testId={`module-header-${currentModule}`}
          icon={ORCIA_MODULE_ICON_NAMES[currentModule]}
          title={headerSubtitle}
          subtitle={headerDescription}
          contextBadge={
            <StatusBadge
              testId={`module-uri-badge-${currentModule}`}
              label={pageCopy.uriBadgeExample}
              tone="cobalt"
            />
          }
        />
      )}

      {currentModule === "cockpit" && <CockpitFeaturePanel />}
      {currentModule === "inbox" && (
        <InboxFeaturePanel mode={isInboxNotifications ? "notifications" : "assistant"} />
      )}
      {currentModule === "catalog" && <CatalogFeaturePanel catalogMode={catalogMode} />}
      {currentModule === "ontology" && <OntologyFeaturePanel />}
      {currentModule === "gates" && <GatesFeaturePanel />}
      {currentModule === "finops" && <FinopsFeaturePanel />}
      {currentModule === "admin" && (
        <WorkspacesFeaturePanel
          initialWorkspaceId={initialWorkspaceId}
          initialTab={initialTab}
        />
      )}
      {currentModule === "bootstrap" && <AdminFeaturePanel />}
    </div>
  );
}
