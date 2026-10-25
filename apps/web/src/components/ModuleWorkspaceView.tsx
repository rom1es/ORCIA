"use client";

import {
  CatalogExplorerPanel,
  HumanLedAnchorCard,
  StatusBadge,
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

export function ModuleWorkspaceView({ moduleKey }: { moduleKey: UiModuleKey }) {
  const { dictionary } = useI18n();
  const {
    activePersona,
    setActivePersona,
    brokerActionBanner,
    triggerPermissionDeniedStep,
    triggerConfusedDeputyCheck,
  } = usePersonaContext();
  const pageCopy = dictionary.modulePages[moduleKey];
  const [customAnchorText, setCustomAnchorText] = useState<string | null>(null);
  const anchorText = customAnchorText ?? dictionary.humanAnchor.defaultValue;
  const { workspaces, finopsTotal } = computePersonaTopology(activePersona);

  return (
    <div
      data-testid={`module-view-${moduleKey}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <div
        style={{
          backgroundColor: "var(--color-surface-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          padding: "16px",
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
          <strong>{pageCopy.subtitle}</strong>
          <StatusBadge
            testId={`module-uri-badge-${moduleKey}`}
            label={pageCopy.uriBadgeExample}
            tone="cobalt"
            monospace
          />
        </div>
        <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>{pageCopy.description}</p>
      </div>

      {moduleKey === "cockpit" && (
        <HumanLedAnchorCard
          sectionKey="architecture-intent"
          sectionTitle={dictionary.humanAnchor.defaultSectionTitle}
          authorName={dictionary.humanAnchor.defaultAuthorName}
          value={anchorText}
          labels={dictionary.humanAnchor}
          onChange={setCustomAnchorText}
        />
      )}

      {(moduleKey === "cockpit" || moduleKey === "catalog" || moduleKey === "gates") && (
        <section
          data-testid="permission-broker-simulator-panel"
          style={{
            backgroundColor: "var(--color-surface-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <div>
            <strong>{dictionary.permissionBroker.simulatorTitle}</strong>
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
                padding: "6px 10px",
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
                backgroundColor: "var(--color-surface-bg)",
                color: "var(--color-foreground)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 10px",
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
                backgroundColor: "var(--color-surface-bg)",
                color: "var(--color-foreground)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 10px",
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
                padding: "6px 10px",
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

      <CatalogExplorerPanel
        activePersona={activePersona}
        items={DEFAULT_CATALOG_EXPLORER_ITEMS}
        runLockTriplets={DEFAULT_RUN_LOCK_TRIPLETS}
        labels={dictionary.catalogExplorer}
      />

      <WorkspaceTopologyPanel
        activePersona={activePersona}
        workspaces={workspaces}
        consolidatedFinopsUsd={finopsTotal}
        catalogResources={DEFAULT_CATALOG_RESOURCES}
        labels={dictionary.workspaceTopology}
        onSelectPersona={setActivePersona}
      />
    </div>
  );
}
