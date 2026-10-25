"use client";

import {
  BootstrapOnboardingPanel,
  CatalogExplorerPanel,
  HumanLedAnchorCard,
  StatusBadge,
  type UiBootstrapWorkflowView,
  type UiModuleKey,
  WorkspaceTopologyPanel,
} from "@orcia/ui";
import React, { useState } from "react";
import { useI18n } from "../i18n";
import { usePersonaContext } from "./ShellContainer";
import {
  computePersonaTopology,
  DEFAULT_CATALOG_EXPLORER_ITEMS,
  DEFAULT_CATALOG_RESOURCES,
  DEFAULT_RUN_LOCK_TRIPLETS,
} from "./workspaceFixtures";

const DEFAULT_BOOTSTRAP_WORKFLOWS: UiBootstrapWorkflowView[] = [
  { uri: "orcia://system/bootstrap/init-organization", title: "init-organization", requiredRole: "PLATFORM_ADMIN", scopeLevel: "GLOBAL", gateRules: ["GATE-LLM-ORTHOGONALITY-MIN-2-FAMILIES"] },
  { uri: "orcia://system/bootstrap/init-workspace", title: "init-workspace", requiredRole: "TEAM_LEAD", scopeLevel: "TEAM", gateRules: ["GATE-ONTOLOGY-L3-NO-UPSTREAM-CONFLICT"] },
  { uri: "orcia://system/bootstrap/init-datasource", title: "init-datasource", requiredRole: "TEAM_LEAD", scopeLevel: "WORKSPACE", gateRules: ["GATE-PERMISSION-BROKER-HUMAN-ANCHOR-SIGNED"] },
  { uri: "orcia://system/bootstrap/init-existing-project", title: "init-existing-project", requiredRole: "TEAM_LEAD", scopeLevel: "WORKSPACE", gateRules: ["GATE-BROWNFIELD-SCAN-VERIFIED"] },
  { uri: "orcia://system/bootstrap/init-skill", title: "init-skill", requiredRole: "CONTRIBUTOR", scopeLevel: "WORKSPACE", gateRules: ["GATE-SKILL-SCHEMA-VALID"] },
  { uri: "orcia://system/bootstrap/init-user", title: "init-user", requiredRole: "CONTRIBUTOR", scopeLevel: "WORKSPACE", gateRules: ["GATE-PASSTHROUGH-AES256GCM-ENCRYPTED"] },
];

export function ModuleWorkspaceView({ moduleKey }: { moduleKey: UiModuleKey }) {
  const { dictionary } = useI18n();
  const {
    fixtureMode,
    activeModuleKey,
    activePersona,
    setActivePersona,
    brokerActionBanner,
    triggerPermissionDeniedStep,
    triggerConfusedDeputyCheck,
  } = usePersonaContext();

  const currentModule = activeModuleKey ?? moduleKey;
  const pageCopy = dictionary.modulePages[currentModule];
  const [customAnchorText, setCustomAnchorText] = useState<string | null>(null);
  const anchorText = customAnchorText ?? dictionary.humanAnchor.defaultValue;
  const topologyData = fixtureMode
    ? computePersonaTopology(activePersona)
    : { workspaces: [], finopsTotal: 0 };

  return (
    <div
      data-testid={`module-view-${currentModule}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "20px",
      }}
    >
      {/* Single Module Theme Header Card */}
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

      {/* Strictly ONE Feature Displayed in the Central Panel According to the Active Left Menu Entry */}
      {currentModule === "cockpit" && (
        <div className="orcia-bento-card">
          <HumanLedAnchorCard
            sectionKey="architecture-intent"
            sectionTitle={dictionary.humanAnchor.defaultSectionTitle}
            authorName={dictionary.humanAnchor.defaultAuthorName}
            value={anchorText}
            labels={dictionary.humanAnchor}
            onChange={setCustomAnchorText}
          />
        </div>
      )}

      {currentModule === "catalog" && (
        <div className="orcia-bento-card">
          <CatalogExplorerPanel
            activePersona={activePersona}
            items={fixtureMode ? DEFAULT_CATALOG_EXPLORER_ITEMS : []}
            runLockTriplets={fixtureMode ? DEFAULT_RUN_LOCK_TRIPLETS : []}
            labels={dictionary.catalogExplorer}
          />
        </div>
      )}

      {currentModule === "gates" && (
        <section
          data-testid="permission-broker-simulator-panel"
          className="orcia-bento-card"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          <div>
            <strong style={{ fontSize: "15px" }}>
              {dictionary.permissionBroker.simulatorTitle}
            </strong>
            <p
              style={{
                margin: "4px 0 0 0",
                color: "var(--color-muted-foreground)",
                fontSize: "var(--font-size-body)",
              }}
            >
              {dictionary.permissionBroker.simulatorSubtitle}
            </p>
          </div>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button
              type="button"
              data-testid="simulate-permission-denied-git-btn"
              onClick={() => triggerPermissionDeniedStep("git")}
              style={{
                backgroundColor: "var(--color-arbitration-amber)",
                color: "var(--color-primary-foreground)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "7px 12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {dictionary.permissionBroker.simulateGitDenialLabel}
            </button>

            <button
              type="button"
              data-testid="simulate-permission-denied-confluence-btn"
              onClick={() => triggerPermissionDeniedStep("confluence")}
              style={{
                backgroundColor: "var(--color-surface-hover)",
                color: "var(--color-foreground)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "7px 12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {dictionary.permissionBroker.simulateConfluenceDenialLabel}
            </button>

            <button
              type="button"
              data-testid="simulate-permission-denied-jira-btn"
              onClick={() => triggerPermissionDeniedStep("jira")}
              style={{
                backgroundColor: "var(--color-surface-hover)",
                color: "var(--color-foreground)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "7px 12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {dictionary.permissionBroker.simulateJiraDenialLabel}
            </button>

            <button
              type="button"
              data-testid="simulate-confused-deputy-btn"
              onClick={triggerConfusedDeputyCheck}
              style={{
                backgroundColor: "var(--color-stale-bg)",
                color: "var(--color-stale-crimson)",
                border: "1px solid var(--color-stale-crimson)",
                borderRadius: "var(--radius-sm)",
                padding: "7px 12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {dictionary.permissionBroker.simulateConfusedDeputyLabel}
            </button>
          </div>

          {brokerActionBanner && (
            <div
              data-testid="permission-broker-action-banner"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "var(--font-size-mono)",
                padding: "8px 10px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-arbitration-bg)",
                border: "1px solid var(--color-arbitration-amber)",
                wordBreak: "break-all",
              }}
            >
              {brokerActionBanner}
            </div>
          )}
        </section>
      )}

      {currentModule === "admin" && (
        <div className="orcia-bento-card">
          <WorkspaceTopologyPanel
            activePersona={activePersona}
            workspaces={topologyData.workspaces}
            consolidatedFinopsUsd={topologyData.finopsTotal}
            catalogResources={fixtureMode ? DEFAULT_CATALOG_RESOURCES : []}
            labels={dictionary.workspaceTopology}
            showPersonaSimulator={fixtureMode}
            onSelectPersona={setActivePersona}
          />
        </div>
      )}

      {currentModule === "bootstrap" && (
        <div className="orcia-bento-card">
          <BootstrapOnboardingPanel
            activePersona={activePersona}
            workflows={DEFAULT_BOOTSTRAP_WORKFLOWS}
            labels={dictionary.bootstrapOnboarding}
          />
        </div>
      )}
    </div>
  );
}
