import {
  OrciaIcon,
  PermissionGuard,
  type InferenceTierAndEffortLabels,
} from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import { usePlatformSetup } from "../components/platformSetupStore";
import { useShellNavigation } from "../components/ShellContainer";
import { useI18n } from "../i18n";
import {
  SETTINGS_TAB_ICON_NAMES,
  resolveSettingsAccess,
  useAuthSessionStore,
  type SettingsTabKey,
} from "../stores/authSessionStore";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";
import { SettingsAiModelsSection } from "./SettingsAiModelsSection";
import { SettingsIamOrganizationSection } from "./SettingsIamOrganizationSection";
import { SettingsOrganizationUnitsBlock } from "./SettingsOrganizationUnitsBlock";
import { SettingsPacksSection } from "./SettingsPacksSection";
import { SettingsSecondaryTabsSection } from "./SettingsSecondaryTabsSection";

export type SettingsSectionTab = SettingsTabKey;

export function SettingsHubView() {
  const { dictionary, locale } = useI18n();
  const { openHelpSection } = useShellNavigation();
  const copy = dictionary.settingsHub;
  const isFr = locale === "fr";

  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const setUserSettingsModalOpen = useAuthSessionStore((s) => s.setUserSettingsModalOpen);

  const access = resolveSettingsAccess({
    roles,
    activeHat,
    readOnlyObserver,
  });

  const {
    platformAdmin,
    orgUnits,
    rbacGrants,
    llmTiers,
    workspaces,
    datasources,
    packs,
    toggleAdminTeamMembership,
    addOrgUnit,
    removeOrgUnit,
    addRbacGrant,
    removeRbacGrant,
    upsertLlmTier,
    registerDatasource,
    registerPack,
    removePack,
  } = usePlatformSetup();

  const [activeTab, setActiveTab] = useState<SettingsSectionTab>("organization");
  const effectiveTab: SettingsSectionTab | null =
    access.visibleTabs.length === 0
      ? null
      : access.visibleTabs.includes(activeTab)
        ? activeTab
        : access.visibleTabs[0]!;

  const tierAndEffortLabels: InferenceTierAndEffortLabels = {
    tierLabel: copy.tabs.models,
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

  return (
    <div
      data-testid="settings-hub-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <header
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "6px" }}
      >
        <h1 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>{copy.hubTitle}</h1>
        <p
          style={{
            margin: 0,
            fontSize: "var(--font-size-body)",
            color: "var(--color-muted-foreground)",
          }}
        >
          {copy.hubSubtitle}
        </p>

        {access.visibleTabs.length > 0 && (
          <nav
            role="tablist"
            data-testid="settings-domain-tabs"
            aria-label="Settings hub navigation"
            className="orcia-ds-tabs"
            style={{ marginTop: "8px" }}
          >
            {access.visibleTabs.map((tabKey) => {
              const isSelected = effectiveTab === tabKey;
              return (
                <button
                  key={tabKey}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  data-testid={`settings-tab-${tabKey}`}
                  onClick={() => setActiveTab(tabKey)}
                  className="orcia-ds-tab"
                >
                  <OrciaIcon name={SETTINGS_TAB_ICON_NAMES[tabKey]} size={15} />
                  <span>{copy.tabs[tabKey]}</span>
                </button>
              );
            })}
          </nav>
        )}
      </header>

      {access.isReadOnlyRestricted || effectiveTab === null ? (
        <section
          data-testid="settings-readonly-access-banner"
          className="orcia-bento-card"
          style={{ display: "flex", flexDirection: "column", gap: "12px" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <OrciaIcon name="lock" size={16} />
            <h2 style={{ margin: 0, fontSize: "15px" }}>{copy.readOnlyRestrictedTitle}</h2>
          </div>
          <p
            style={{
              margin: 0,
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {copy.readOnlyRestrictedBody}
          </p>
          <div>
            <button
              type="button"
              data-testid="open-my-account-from-settings-btn"
              onClick={() => setUserSettingsModalOpen(true)}
              className="orcia-ds-btn orcia-ds-btn-primary"
            >
              <OrciaIcon name="nav.account" size={15} />
              <span>{copy.openMyAccountCta}</span>
            </button>
          </div>
        </section>
      ) : (
        <PermissionGuard
          scopePath="GLOBAL"
          verb="read"
          allowedVerbs={access.allowedVerbs}
          labels={{
            passiveLockBadge: isFr ? "Accès restreint" : "Restricted access",
            passiveLockDescription: copy.lockedSectionNotice,
            requestAccessCta: copy.requestAccessLabel,
            disabledHint: copy.lockedSectionNotice,
          }}
        >
          <div
            data-testid={`settings-panel-${effectiveTab}`}
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            {effectiveTab === "organization" ? (
              <SettingsOrganizationUnitsBlock
                isFr={isFr}
                canMutate={access.canMutate}
                platformAdmin={platformAdmin}
                orgUnits={orgUnits}
                openHelpSection={openHelpSection}
                toggleAdminTeamMembership={toggleAdminTeamMembership}
                addOrgUnit={addOrgUnit}
                removeOrgUnit={removeOrgUnit}
              />
            ) : effectiveTab === "iam" ? (
              <SettingsIamOrganizationSection
                isFr={isFr}
                canMutate={access.canMutate}
                allowedVerbs={access.allowedVerbs}
                orgUnits={orgUnits}
                workspaces={workspaces}
                rbacGrants={rbacGrants}
                openHelpSection={openHelpSection}
                addRbacGrant={addRbacGrant}
                removeRbacGrant={removeRbacGrant}
              />
            ) : effectiveTab === "models" ? (
              <SettingsAiModelsSection
                isFr={isFr}
                tierAndEffortLabels={tierAndEffortLabels}
                llmTiers={llmTiers}
                openHelpSection={openHelpSection}
                upsertLlmTier={upsertLlmTier}
              />
            ) : effectiveTab === "packs" ? (
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
                isFr={isFr}
                copy={copy}
                workspaces={workspaces}
                datasources={datasources}
                openHelpSection={openHelpSection}
                registerDatasource={registerDatasource}
              />
            )}
          </div>
        </PermissionGuard>
      )}
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings",
  validateSearch: validateOrciaRouteSearch,
  component: SettingsHubView,
});
