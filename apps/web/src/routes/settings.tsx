import {
  OrciaIcon,
  PermissionGuard,
  type InferenceTierAndEffortLabels,
} from "@orcia/ui";
import { createRoute, useNavigate } from "@tanstack/react-router";
import React, { useEffect, useState } from "react";
import { usePlatformSetup } from "../components/platformSetupStore";
import { ignoreBenignStorageError } from "../utils/benignBrowserError";
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
import { SettingsAuthenticationSection } from "../features/admin/auth/SettingsAuthenticationSection";
import { SettingsIamOrganizationSection } from "./SettingsIamOrganizationSection";
import { SettingsPacksSection } from "./SettingsPacksSection";
import { SettingsSecondaryTabsSection } from "./SettingsSecondaryTabsSection";

export type SettingsSectionTab = SettingsTabKey;

const VALID_SETTINGS_TABS: readonly string[] = [
  "iam",
  "authentication",
  "models",
  "packs",
  "connectors",
];

function resolveInitialSettingsTab(initialTab?: SettingsSectionTab): SettingsSectionTab {
  if (initialTab) return initialTab;
  try {
    const sp = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "");
    const tabParam = sp.get("tab") as SettingsSectionTab | null;
    if (tabParam && VALID_SETTINGS_TABS.includes(tabParam)) return tabParam;
  } catch (err: unknown) {
    ignoreBenignStorageError("settings.url_redirect", err);
  }
  return "iam";
}

export interface SettingsHubViewProps {
  readonly initialTab?: SettingsSectionTab;
}

export function SettingsHubView({ initialTab }: SettingsHubViewProps = {}) {
  const { dictionary, locale } = useI18n();
  const { openHelpSection, navigateToRoute } = useShellNavigation();
  const copy = dictionary.settingsHub;
  const isFr = locale === "fr";
  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const setUserSettingsModalOpen = useAuthSessionStore((s) => s.setUserSettingsModalOpen);
  const access = resolveSettingsAccess({ roles, activeHat, readOnlyObserver });
  const {
    orgUnits, rbacGrants, workspaces, datasources, packs,
    syncOrgUnitsFromServer, syncRbacGrantsFromServer,
    registerDatasource, registerPack, removePack,
  } = usePlatformSetup();

  useEffect(() => {
    try {
      const sp = new URLSearchParams(typeof window !== "undefined" ? window.location.search : "");
      if (sp.get("tab") === "organization") navigateToRoute("/organization");
    } catch (err: unknown) {
      ignoreBenignStorageError("settings.url_redirect", err);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [activeTab, setActiveTab] = useState<SettingsSectionTab>(() =>
    resolveInitialSettingsTab(initialTab),
  );
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
        <p style={{ margin: 0, fontSize: "var(--font-size-body)", color: "var(--color-muted-foreground)" }}>
          {copy.hubSubtitle}
        </p>

        {access.visibleTabs.length > 0 && (
          <nav
            role="tablist"
            data-testid="settings-domain-tabs"
            aria-label="Settings hub navigation"
            className="orcia-ds-tabs"
            style={{ marginTop: "8px", flexWrap: "nowrap", gap: "6px", overflowX: "auto" }}
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
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                    padding: "5px 8px",
                    fontSize: "12px",
                    whiteSpace: "nowrap",
                    flexShrink: 0,
                  }}
                >
                  <OrciaIcon name={SETTINGS_TAB_ICON_NAMES[tabKey]} size={13} />
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
            {effectiveTab === "iam" ? (
              <SettingsIamOrganizationSection
                isFr={isFr}
                canMutate={access.canMutate}
                iamLabels={copy.iamTab}
                orgUnits={orgUnits}
                workspaces={workspaces}
                rbacGrants={rbacGrants}
                openHelpSection={openHelpSection}
                syncOrgUnitsFromServer={syncOrgUnitsFromServer}
                syncRbacGrantsFromServer={syncRbacGrantsFromServer}
              />
            ) : effectiveTab === "authentication" ? (
              <SettingsAuthenticationSection
                canMutate={access.canMutate}
                onNavigateToConnectors={() => setActiveTab("connectors")}
              />
            ) : effectiveTab === "models" ? (
              <SettingsAiModelsSection
                isFr={isFr}
                tierAndEffortLabels={tierAndEffortLabels}
                openHelpSection={openHelpSection}
                allowedVerbs={access.allowedVerbs}
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

function SettingsRouteComponent(): React.ReactElement {
  const search = Route.useSearch();
  const navigate = useNavigate();

  useEffect(() => {
    if (search.tab === "organization") {
      void navigate({ to: "/organization", replace: true });
    }
  }, [search.tab, navigate]);

  if (search.tab === "organization") {
    return <div data-testid="settings-org-redirect-placeholder" />;
  }
  const initialTab: SettingsSectionTab | undefined =
    search.tab && VALID_SETTINGS_TABS.includes(search.tab)
      ? (search.tab as SettingsSectionTab)
      : undefined;
  return <SettingsHubView initialTab={initialTab} />;
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings",
  validateSearch: validateOrciaRouteSearch,
  component: SettingsRouteComponent,
});
