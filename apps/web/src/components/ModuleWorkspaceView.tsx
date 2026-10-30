import { StatusBadge, type UiModuleKey } from "@orcia/ui";
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
import { useShellNavigation } from "./ShellContainer";

export function ModuleWorkspaceView({ moduleKey }: { moduleKey: UiModuleKey }) {
  const { dictionary } = useI18n();
  const { activeModuleKey } = useShellNavigation();

  const currentModule = activeModuleKey ?? moduleKey;
  const pageCopy = dictionary.modulePages[currentModule];

  return (
    <div
      data-testid={`module-view-${currentModule}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "20px",
      }}
    >
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
          <strong style={{ fontSize: "16px" }}>{pageCopy.subtitle}</strong>
          <StatusBadge
            testId={`module-uri-badge-${currentModule}`}
            label={pageCopy.uriBadgeExample}
            tone="cobalt"
            monospace
          />
        </div>
        <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>{pageCopy.description}</p>
      </div>

      {currentModule === "cockpit" && <CockpitFeaturePanel />}
      {currentModule === "inbox" && <InboxFeaturePanel />}
      {currentModule === "catalog" && <CatalogFeaturePanel />}
      {currentModule === "ontology" && <OntologyFeaturePanel />}
      {currentModule === "gates" && <GatesFeaturePanel />}
      {currentModule === "finops" && <FinopsFeaturePanel />}
      {currentModule === "admin" && <WorkspacesFeaturePanel />}
      {currentModule === "bootstrap" && <AdminFeaturePanel />}
    </div>
  );
}
