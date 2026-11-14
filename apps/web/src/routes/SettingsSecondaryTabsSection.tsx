import type {
  ControlCenterDatasourceItem,
  ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React from "react";
import type { PlatformSetupContextValue } from "../components/platformSetupStore";
import { useShellNavigation } from "../components/ShellContainer";
import { EnterpriseConnectorsSettingsSection } from "../features/admin/connectors/EnterpriseConnectorsSettingsSection";
import { useI18n } from "../i18n";
import type { TranslationDictionary } from "../i18n/types";

export interface SettingsSecondaryTabsSectionProps {
  readonly isFr: boolean;
  readonly copy: TranslationDictionary["settingsHub"];
  readonly workspaces?: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources?: readonly ControlCenterDatasourceItem[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly registerDatasource?: PlatformSetupContextValue["registerDatasource"];
}

export function SettingsSecondaryTabsSection({
  isFr,
  copy,
  workspaces = [],
  openHelpSection,
}: SettingsSecondaryTabsSectionProps): React.ReactElement {
  const { dictionary } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const bannerCopy = dictionary.epic18Sources.settingsDeportBanner;

  const targetWsId = workspaces[0]?.workspaceId || "default";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <EnterpriseConnectorsSettingsSection
        isFr={isFr}
        copy={copy}
        openHelpSection={openHelpSection}
        canMutate={true}
      />

      <section
        data-testid="settings-deported-sources-banner"
        className="orcia-bento-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <strong style={{ fontSize: "14px" }}>{bannerCopy.title}</strong>
          <span
            style={{
              fontSize: "12px",
              color: "var(--color-muted-foreground)",
              maxWidth: "600px",
            }}
          >
            {bannerCopy.description}
          </span>
        </div>
        <button
          type="button"
          data-testid="settings-goto-workspace-sources-btn"
          className="orcia-ds-btn orcia-ds-btn-primary"
          onClick={() => {
            navigateToRoute(`/workspaces/${encodeURIComponent(targetWsId)}/sources`);
          }}
        >
          {bannerCopy.buttonLabel} →
        </button>
      </section>
    </div>
  );
}
