import {
  PermissionGuard,
  type InferenceTierAndEffortLabels,
  type UiPermissionVerb,
} from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import { usePlatformSetup } from "../components/platformSetupStore";
import { useShellNavigation } from "../components/ShellContainer";
import { useI18n } from "../i18n";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";
import { SettingsAiModelsSection } from "./SettingsAiModelsSection";
import { SettingsIamOrganizationSection } from "./SettingsIamOrganizationSection";
import { SettingsPacksSection } from "./SettingsPacksSection";
import { SettingsSecondaryTabsSection } from "./SettingsSecondaryTabsSection";

export type SettingsSectionTab =
  | "iam"
  | "connectors"
  | "ai-models"
  | "packs"
  | "workflows";

export function SettingsHubView() {
  const { dictionary, locale } = useI18n();
  const { openHelpSection } = useShellNavigation();
  const copy = dictionary.settingsHub;
  const isFr = locale === "fr";

  const {
    orgUnits,
    rbacGrants,
    llmTiers,
    workspaces,
    datasources,
    packs,
    workflows,
    addOrgUnit,
    removeOrgUnit,
    addRbacGrant,
    removeRbacGrant,
    upsertLlmTier,
    registerDatasource,
    registerPack,
    removePack,
    upsertWorkflow,
  } = usePlatformSetup();

  const [activeTab, setActiveTab] = useState<SettingsSectionTab>("iam");
  const [allowedVerbs] = useState<readonly UiPermissionVerb[]>([
    "create",
    "read",
    "update",
    "delete",
    "execute",
    "grant",
  ]);

  const tierAndEffortLabels: InferenceTierAndEffortLabels = {
    tierLabel: copy.tabs.aiModels,
    effortLabel: "Effort",
    simpleBadge: copy.tierLabels.simple,
    mediumBadge: copy.tierLabels.medium,
    complexBadge: copy.tierLabels.complex,
    autoBadge: copy.tierLabels.auto,
    effortDefault: copy.effortLabels.default,
    effortFast: copy.effortLabels.fast,
    effortBalanced: copy.effortLabels.balanced,
    effortDeep: copy.effortLabels.deep,
  };

  const tabs: readonly { key: SettingsSectionTab; label: string }[] = [
    { key: "iam", label: copy.tabs.iam },
    { key: "ai-models", label: copy.tabs.aiModels },
    { key: "connectors", label: copy.tabs.connectors },
    { key: "packs", label: copy.tabs.packs },
    { key: "workflows", label: copy.tabs.workflows },
  ];

  return (
    <div
      data-testid="settings-hub-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <header className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <h1 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>{copy.hubTitle}</h1>
        <p style={{ margin: 0, fontSize: "var(--font-size-body)", color: "var(--color-muted-foreground)" }}>
          {copy.hubSubtitle}
        </p>

        <nav
          role="tablist"
          aria-label="Settings hub navigation"
          style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "8px" }}
        >
          {tabs.map((tab) => {
            const isSelected = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={isSelected}
                data-testid={`settings-tab-${tab.key}`}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: isSelected
                    ? "1px solid var(--color-primary-cobalt)"
                    : "1px solid var(--color-border)",
                  backgroundColor: isSelected
                    ? "var(--color-primary-cobalt)"
                    : "var(--color-surface-card)",
                  color: isSelected
                    ? "var(--color-primary-foreground)"
                    : "var(--color-foreground)",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </header>

      <PermissionGuard
        scopePath="GLOBAL"
        verb="read"
        allowedVerbs={allowedVerbs}
        labels={{
          passiveLockBadge: "🔒 Accès restreint",
          passiveLockDescription: copy.lockedSectionNotice,
          requestAccessCta: copy.requestAccessLabel,
          disabledHint: copy.lockedSectionNotice,
        }}
      >
        <div
          data-testid={`settings-panel-${activeTab}`}
          style={{ display: "flex", flexDirection: "column", gap: "16px" }}
        >
          {activeTab === "iam" ? (
            <SettingsIamOrganizationSection
              isFr={isFr}
              allowedVerbs={allowedVerbs}
              orgUnits={orgUnits}
              workspaces={workspaces}
              rbacGrants={rbacGrants}
              openHelpSection={openHelpSection}
              addOrgUnit={addOrgUnit}
              removeOrgUnit={removeOrgUnit}
              addRbacGrant={addRbacGrant}
              removeRbacGrant={removeRbacGrant}
            />
          ) : activeTab === "ai-models" ? (
            <SettingsAiModelsSection
              isFr={isFr}
              tierAndEffortLabels={tierAndEffortLabels}
              llmTiers={llmTiers}
              openHelpSection={openHelpSection}
              upsertLlmTier={upsertLlmTier}
            />
          ) : activeTab === "packs" ? (
            <SettingsPacksSection
              isFr={isFr}
              packs={packs}
              orgUnits={orgUnits}
              workspaces={workspaces}
              registerPack={registerPack}
              removePack={removePack}
              openHelpSection={openHelpSection}
            />
          ) : (
            <SettingsSecondaryTabsSection
              activeTab={activeTab}
              isFr={isFr}
              copy={copy}
              tierAndEffortLabels={tierAndEffortLabels}
              llmTiers={llmTiers}
              workspaces={workspaces}
              datasources={datasources}
              packs={packs}
              workflows={workflows}
              openHelpSection={openHelpSection}
              upsertLlmTier={upsertLlmTier}
              registerDatasource={registerDatasource}
              registerPack={registerPack}
              upsertWorkflow={upsertWorkflow}
            />
          )}
        </div>
      </PermissionGuard>
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings",
  validateSearch: validateOrciaRouteSearch,
  component: SettingsHubView,
});
