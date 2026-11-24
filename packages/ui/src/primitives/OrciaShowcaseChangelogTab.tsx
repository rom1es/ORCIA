import React from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { OrciaSectionCard } from "./DesignSystemControls";
import type {
  OrciaShowcaseChangelogLabels,
  OrciaShowcaseManifestData,
  OrciaShowcaseTechLeadReportItem,
} from "./OrciaShowcaseTypes";
import { StatusBadge } from "./StatusBadge";

export interface OrciaShowcaseChangelogTabProps {
  readonly labels: OrciaShowcaseChangelogLabels;
  readonly manifest: OrciaShowcaseManifestData;
  readonly filteredReports: readonly OrciaShowcaseTechLeadReportItem[];
  readonly changelogFilter: string;
  readonly onChangelogFilterChange: (value: string) => void;
  readonly onOpenHelpSection?: (sectionId: string) => void;
}

function formatShowcaseTemplate(
  template: string,
  vars: Readonly<Record<string, string | number>>,
): string {
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_match, key: string) =>
    vars[key] !== undefined ? String(vars[key]) : `{${key}}`,
  );
}

export function OrciaShowcaseChangelogTab({
  labels,
  manifest,
  filteredReports,
  changelogFilter,
  onChangelogFilterChange,
  onOpenHelpSection,
}: OrciaShowcaseChangelogTabProps): React.ReactElement {
  return (
    <section
      data-testid="showcase-pillar-changelog"
      className="orcia-ds-page"
    >
      <OrciaSectionCard
        testId="showcase-changelog-live-stats"
        title={labels.statsTitle}
        subtitle={labels.statsSubtitle}
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div
            data-testid="showcase-stat-routes"
            className="rounded-lg border p-3 text-center"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div
              className="text-lg font-bold"
              style={{ color: "var(--color-action-primary)" }}
            >
              {manifest.stats.activeRoutesCount}
            </div>
            <div style={{ color: "var(--color-text-secondary)" }}>
              {labels.activeRoutesStatLabel}
            </div>
          </div>

          <div
            data-testid="showcase-stat-primitives"
            className="rounded-lg border p-3 text-center"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div
              className="text-lg font-bold"
              style={{ color: "var(--color-action-primary)" }}
            >
              {manifest.stats.uiPrimitivesCount}
            </div>
            <div style={{ color: "var(--color-text-secondary)" }}>
              {labels.uiPrimitivesStatLabel}
            </div>
          </div>

          <div
            data-testid="showcase-stat-migrations"
            className="rounded-lg border p-3 text-center"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div
              className="text-lg font-bold"
              style={{ color: "var(--color-action-primary)" }}
            >
              {manifest.stats.alembicMigrationsCount}
            </div>
            <div style={{ color: "var(--color-text-secondary)" }}>
              {labels.alembicMigrationsStatLabel}
            </div>
          </div>

          <div
            data-testid="showcase-stat-reports"
            className="rounded-lg border p-3 text-center"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div
              className="text-lg font-bold"
              style={{ color: "var(--color-action-primary)" }}
            >
              {manifest.stats.techLeadReportsCount}
            </div>
            <div style={{ color: "var(--color-text-secondary)" }}>
              {labels.techLeadReportsStatLabel}
            </div>
          </div>

          {manifest.stats.capabilitiesCount !== undefined ? (
            <div
              data-testid="showcase-stat-capabilities"
              className="rounded-lg border p-3 text-center"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div
                className="text-lg font-bold"
                style={{ color: "var(--color-action-primary)" }}
              >
                {manifest.stats.verifiedCapabilitiesCount ?? 0} /{" "}
                {manifest.stats.liveCapabilitiesCount ??
                  manifest.stats.capabilitiesCount}
              </div>
              <div style={{ color: "var(--color-text-secondary)" }}>
                {labels.verifiedCapabilitiesStatLabel}
              </div>
            </div>
          ) : null}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 text-xs">
          <div
            className="rounded-lg border p-3.5 space-y-2"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="flex items-center justify-between">
              <strong className="text-sm">
                {formatShowcaseTemplate(labels.installedPacksTitleTemplate, {
                  count: manifest.stats.installedPacksCount,
                })}
              </strong>
              <ContextualInfoTriggerButton
                sectionId="showcase-packs"
                label={labels.installedPacksHelpLabel}
                onOpenHelpSection={onOpenHelpSection}
              />
            </div>
            <div className="space-y-1.5">
              {manifest.installedPacks.map((pack) => (
                <div key={pack.key} className="orcia-ds-row">
                  <StatusBadge
                    label={`${pack.key}@${pack.version}`}
                    tone="emerald"
                    monospace
                  />
                  <span style={{ color: "var(--color-text-secondary)" }}>
                    {pack.description}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-2"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">
              {formatShowcaseTemplate(labels.stackVersionsTitleTemplate, {
                count: manifest.stats.stackComponentsCount,
              })}
            </strong>
            <div className="max-h-[220px] overflow-y-auto space-y-1">
              {manifest.stackComponents.map((comp) => (
                <div key={comp.name} className="orcia-ds-row">
                  <span className="font-semibold">{comp.name}</span>
                  <StatusBadge label={comp.version} tone="cobalt" monospace />
                </div>
              ))}
            </div>
          </div>
        </div>
      </OrciaSectionCard>

      <OrciaSectionCard
        testId="showcase-changelog-reports-card"
        title={formatShowcaseTemplate(labels.reportsTimelineTitleTemplate, {
          filtered: filteredReports.length,
          total: manifest.stats.techLeadReportsCount,
        })}
        subtitle={labels.reportsTimelineSubtitle}
      >
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          spellCheck={false}
          data-testid="showcase-changelog-search-input"
          value={changelogFilter}
          onChange={(e) => onChangelogFilterChange(e.target.value)}
          placeholder={labels.searchPlaceholder}
          className="orcia-ds-input w-full"
        />

        <div
          data-testid="showcase-changelog-reports-list"
          className="space-y-2.5 max-h-[600px] overflow-y-auto"
        >
          {filteredReports.map((rep) => (
            <article
              key={rep.reportFile}
              data-testid={`showcase-report-item-${rep.reportFile}`}
              className="rounded-lg border p-3.5 space-y-1.5 text-xs"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                  <StatusBadge label={rep.date} tone="cobalt" monospace />
                  <StatusBadge label={rep.phaseOrStory} tone="emerald" />
                </div>
                <span
                  className="font-mono text-[11px]"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {rep.reportFile}
                </span>
              </div>
              <div
                className="font-bold text-sm"
                style={{ color: "var(--color-text-primary)" }}
              >
                {rep.domain}
              </div>
              <p style={{ color: "var(--color-text-secondary)" }}>
                {rep.summary}
              </p>
            </article>
          ))}
        </div>
      </OrciaSectionCard>
    </section>
  );
}
