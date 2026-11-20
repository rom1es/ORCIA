import { ContextualInfoTriggerButton, StatusBadge, type UiModuleKey } from "@orcia/ui";
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
  const { dictionary, locale } = useI18n();
  const { pathname } = useOrciaNavigation();
  const { activeModuleKey, openHelpSection } = useShellNavigation();

  const currentModule = activeModuleKey ?? moduleKey;
  const isInboxNotifications =
    currentModule === "inbox" &&
    (inboxMode === "notifications" || Boolean(pathname?.startsWith("/inbox")));
  const pageCopy = dictionary.modulePages[currentModule];
  const isFr = locale === "fr";
  const headerSubtitle = isInboxNotifications
    ? isFr
      ? "Centre de Notifications & Prises en Charge Équipe"
      : "Team Notification & Claim Center"
    : pageCopy.subtitle;
  const headerDescription = isInboxNotifications
    ? isFr
      ? "Suivi temps réel des arbitrages humains, validations en attente et prises en charge d'équipe."
      : "Real-time tracking of human arbitrations, pending gates, and team claims."
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
      currentModule === "inbox" ? null : (
        <div
          className="orcia-bento-card"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "8px",
              flexWrap: "wrap",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <strong style={{ fontSize: "16px" }}>{headerSubtitle}</strong>
              <ContextualInfoTriggerButton
                sectionId="module-overview"
                label={
                  isFr
                    ? `Afficher l'aide sur ${headerSubtitle}`
                    : `Show help for ${headerSubtitle}`
                }
                onOpenHelpSection={openHelpSection}
              />
            </div>
            <StatusBadge
              testId={`module-uri-badge-${currentModule}`}
              label={pageCopy.uriBadgeExample}
              tone="cobalt"
            />
          </div>
          <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>{headerDescription}</p>
        </div>
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
