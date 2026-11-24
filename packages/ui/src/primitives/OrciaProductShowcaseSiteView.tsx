import React, { useMemo, useState } from "react";
import { OrciaButton, OrciaSectionCard, OrciaTabBar } from "./DesignSystemControls";
import { OrciaShowcaseArchitectureTab } from "./OrciaShowcaseArchitectureTab";
import { OrciaShowcaseChangelogTab } from "./OrciaShowcaseChangelogTab";
import { OrciaShowcaseFeaturesTab } from "./OrciaShowcaseFeaturesTab";
import { OrciaShowcaseMacroTab } from "./OrciaShowcaseMacroTab";
import type {
  OrciaProductShowcaseSiteViewProps,
  OrciaShowcasePillarTabKey,
} from "./OrciaShowcaseTypes";
import { StatusBadge } from "./StatusBadge";

export type {
  OrciaProductShowcaseSiteViewProps,
  OrciaShowcaseArchitectureDecisionItem,
  OrciaShowcaseArchitectureLabels,
  OrciaShowcaseBadgeCard,
  OrciaShowcaseChangelogLabels,
  OrciaShowcaseFeaturesLabels,
  OrciaShowcaseInstalledPackItem,
  OrciaShowcaseLabels,
  OrciaShowcaseMacroLabels,
  OrciaShowcaseManifestData,
  OrciaShowcaseManifestStats,
  OrciaShowcasePillarTabKey,
  OrciaShowcaseScreenGuideItem,
  OrciaShowcaseStackComponentItem,
  OrciaShowcaseTechLeadReportItem,
  OrciaShowcaseTitleDescCard,
} from "./OrciaShowcaseTypes";

/**
 * Pure `@orcia/ui` component presenting the ORCIA Product & Architecture Showcase Site (`/showcase`).
 * All copy is injected via typed `labels` props from the host application.
 */
export function OrciaProductShowcaseSiteView({
  manifest,
  labels,
  initialTab = "macro",
  onNavigateToRoute,
  onOpenHelpSection,
  onDownloadStandaloneHtml,
}: OrciaProductShowcaseSiteViewProps): React.ReactElement {
  const [activeTab, setActiveTab] = useState<OrciaShowcasePillarTabKey>(initialTab);
  const [changelogFilter, setChangelogFilter] = useState<string>("");
  const [exportedBannerVisible, setExportedBannerVisible] = useState<boolean>(false);

  const filteredReports = useMemo(() => {
    const q = changelogFilter.trim().toLowerCase();
    if (!q) {
      return manifest.techLeadReports;
    }
    return manifest.techLeadReports.filter((item) => {
      const haystack =
        `${item.date} ${item.phaseOrStory} ${item.reportFile} ${item.domain} ${item.summary}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [changelogFilter, manifest.techLeadReports]);

  const handleExportTrigger = (): void => {
    setExportedBannerVisible(true);
    onDownloadStandaloneHtml?.();
  };

  const tabChangelogLabel = labels.tabChangelogLabelTemplate.replace(
    "{count}",
    String(manifest.stats.techLeadReportsCount),
  );

  return (
    <div
      data-testid="orcia-product-showcase-site-view"
      className="orcia-ds-page"
    >
      <OrciaSectionCard
        testId="showcase-hero-card"
        title={labels.heroTitle}
        subtitle={labels.heroSubtitle}
        helpSectionId="showcase-overview"
        helpLabel={labels.heroHelpLabel}
        onOpenHelpSection={onOpenHelpSection}
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge
              testId="showcase-sync-date-badge"
              label={`${labels.syncedBadgePrefix} ${manifest.lastSyncedDate}`}
              tone="emerald"
              monospace
            />
            <OrciaButton
              testId="showcase-export-standalone-btn"
              variant="secondary"
              onClick={handleExportTrigger}
            >
              {labels.exportStandaloneButton}
            </OrciaButton>
          </div>
        }
      >
        {exportedBannerVisible && (
          <div
            data-testid="showcase-standalone-export-banner"
            className="orcia-ds-alert orcia-ds-alert-success"
          >
            {labels.exportBannerMessage}
          </div>
        )}

        <OrciaTabBar
          ariaLabel={labels.tabsAriaLabel}
          activeTab={activeTab}
          onSelectTab={(key) => setActiveTab(key as OrciaShowcasePillarTabKey)}
          tabs={[
            {
              key: "macro",
              label: labels.tabMacroLabel,
              testId: "showcase-tab-macro",
            },
            {
              key: "features",
              label: labels.tabFeaturesLabel,
              testId: "showcase-tab-features",
            },
            {
              key: "architecture",
              label: labels.tabArchitectureLabel,
              testId: "showcase-tab-architecture",
            },
            {
              key: "changelog",
              label: tabChangelogLabel,
              testId: "showcase-tab-changelog",
            },
          ]}
        />
      </OrciaSectionCard>

      {activeTab === "macro" && <OrciaShowcaseMacroTab labels={labels.macro} />}
      {activeTab === "features" && (
        <OrciaShowcaseFeaturesTab
          labels={labels.features}
          onNavigateToRoute={onNavigateToRoute}
        />
      )}
      {activeTab === "architecture" && (
        <OrciaShowcaseArchitectureTab labels={labels.architecture} />
      )}
      {activeTab === "changelog" && (
        <OrciaShowcaseChangelogTab
          labels={labels.changelog}
          manifest={manifest}
          filteredReports={filteredReports}
          changelogFilter={changelogFilter}
          onChangelogFilterChange={setChangelogFilter}
          onOpenHelpSection={onOpenHelpSection}
        />
      )}
    </div>
  );
}
