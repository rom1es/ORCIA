import React from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaAlertBanner } from "./OrciaAlertBanner";
import { OrciaDataCard } from "./OrciaDataCard";
import { OrciaPageHeader } from "./OrciaPageHeader";
import type { UiLocalePreference } from "./UserAccountDropdownTypes";
import type {
  UiUserProfileSummaryView,
  UserProfileOverviewLabels,
} from "./UserProfileOverviewTypes";
import { computeUserInitials, resolveUserRoleDisplayLabel } from "./UserRoleDisplayLabels";

export interface UserProfileOverviewPageProps {
  readonly profile: UiUserProfileSummaryView;
  readonly locale: UiLocalePreference;
  readonly labels: UserProfileOverviewLabels;
  readonly isLoading?: boolean;
  readonly errorMessage?: string | null;
  readonly onRetry?: () => void;
  readonly onEditAccount: () => void;
  readonly onSelectPopularItem: (targetRoute: string) => void;
  readonly onExploreAgents: () => void;
}

export function UserProfileOverviewPage({
  profile,
  locale,
  labels,
  isLoading = false,
  errorMessage = null,
  onRetry,
  onEditAccount,
  onSelectPopularItem,
  onExploreAgents,
}: UserProfileOverviewPageProps): React.ReactElement {
  const initials = computeUserInitials(profile.displayName || profile.email);
  const numFmt = new Intl.NumberFormat(locale);
  const distinctRoles = Array.from(new Set(profile.roles.length > 0 ? profile.roles : [profile.primaryRole]));
  const fmtDays = (n: number): string => `${n} ${n === 1 ? labels.daysUnitSingular : labels.daysUnitPlural}`;

  const orgBadgeGroups = [
    { key: "bu", prefix: labels.ledBuBadgePrefix, items: profile.ledBusinessUnits, bg: "var(--color-surface-muted)", fg: "var(--color-text-primary)" },
    { key: "onto", prefix: labels.ontologyBuBadgePrefix, items: profile.ontologyBusinessUnits, bg: "var(--color-ontology-bg)", fg: "var(--color-ontology-cyan)" },
    { key: "lt", prefix: labels.ledTeamBadgePrefix, items: profile.ledTeams, bg: "var(--color-gate-emerald-bg)", fg: "var(--color-gate-emerald)" },
    { key: "mt", prefix: labels.memberTeamBadgePrefix, items: profile.memberTeams, bg: "var(--color-surface-base)", fg: "var(--color-text-secondary)" },
  ];

  const kpiCards = [
    { testId: "profile-kpi-total-tokens", label: labels.totalTokensLabel, value: numFmt.format(profile.totalTokens), hint: labels.totalTokensHint, icon: "sparkles" as const },
    { testId: "profile-kpi-peak-tokens", label: labels.peakDailyTokensLabel, value: numFmt.format(profile.peakDailyTokens), hint: labels.peakDailyTokensHint, icon: "lightning" as const },
    { testId: "profile-kpi-longest-streak", label: labels.longestStreakLabel, value: fmtDays(profile.longestStreakDays), hint: "", icon: "target" as const },
    { testId: "profile-kpi-current-streak", label: labels.currentStreakLabel, value: fmtDays(profile.currentStreakDays), hint: "", icon: "clock" as const },
  ];

  const allKpisZero =
    !isLoading &&
    profile.totalTokens === 0 &&
    profile.peakDailyTokens === 0 &&
    profile.longestStreakDays === 0 &&
    profile.currentStreakDays === 0;

  return (
    <div data-testid="user-profile-overview-page" className="orcia-ds-page">
      <OrciaPageHeader
        testId="profile-page-header"
        icon="user"
        title={profile.displayName}
        titleTestId="profile-display-name"
        subtitle={`@${profile.handle}${profile.email ? ` · ${profile.email}` : ""}`}
        subtitleTestId="profile-handle-email"
        contextBadge={
          <div
            data-testid="profile-avatar-initials"
            className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold"
            style={{ backgroundColor: "var(--color-action-primary-subtle)", color: "var(--color-action-primary)" }}
          >
            {initials}
          </div>
        }
        secondaryActions={
          <button
            type="button"
            data-testid="profile-open-account-settings-btn"
            onClick={onEditAccount}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm inline-flex items-center gap-1.5"
          >
            <OrciaIcon name="pen" size={14} />
            <span>{labels.editButtonLabel}</span>
          </button>
        }
        alertSlot={
          errorMessage ? (
            <OrciaAlertBanner
              tone="crimson"
              role="alert"
              testId="profile-error-banner"
              action={
                onRetry ? (
                  <button
                    type="button"
                    data-testid="profile-retry-btn"
                    onClick={onRetry}
                    className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
                  >
                    {labels.retryLabel}
                  </button>
                ) : undefined
              }
            >
              {errorMessage}
            </OrciaAlertBanner>
          ) : undefined
        }
      />

      <OrciaDataCard testId="profile-org-badges-card">
        <div data-testid="profile-org-badges" className="flex flex-wrap items-center gap-2">
          {distinctRoles.map((roleKey) => (
            <span
              key={roleKey}
              className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium"
              style={{ backgroundColor: "var(--color-badge-cobalt-bg)", color: "var(--color-badge-cobalt-fg)", borderColor: "var(--color-badge-cobalt-border)" }}
            >
              {resolveUserRoleDisplayLabel(roleKey, labels.roleDisplayLabels)}
            </span>
          ))}
          {orgBadgeGroups.flatMap((grp) =>
            grp.items.map((name) => (
              <span
                key={`${grp.key}-${name}`}
                className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium"
                style={{ backgroundColor: grp.bg, color: grp.fg, borderColor: "var(--color-border-subtle)" }}
              >
                {grp.prefix} {name}
              </span>
            )),
          )}
        </div>
      </OrciaDataCard>

      {isLoading ? (
        <OrciaDataCard testId="profile-kpis-loading">
          <span className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{labels.loadingLabel}</span>
        </OrciaDataCard>
      ) : allKpisZero ? (
        <OrciaDataCard testId="profile-kpis-empty-state">
          <span className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{labels.emptyKpisMessage}</span>
        </OrciaDataCard>
      ) : (
        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {kpiCards.map((kpi) => (
            <OrciaDataCard key={kpi.testId} testId={kpi.testId}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>{kpi.label}</span>
                <OrciaIcon name={kpi.icon} size={15} />
              </div>
              <div className="text-xl font-semibold tabular-nums" style={{ color: "var(--color-text-primary)" }}>
                {kpi.value}
              </div>
              {kpi.hint && <span className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>{kpi.hint}</span>}
            </OrciaDataCard>
          ))}
        </section>
      )}

      <OrciaDataCard
        testId="profile-popular-items-section"
        title={labels.popularSectionTitle}
        subtitle={labels.popularSectionSubtitle}
      >
        {isLoading ? (
          <p className="py-4 text-xs" style={{ color: "var(--color-text-secondary)" }}>{labels.loadingLabel}</p>
        ) : profile.popularItems.length === 0 ? (
          <div
            data-testid="profile-popular-items-empty"
            className="flex flex-col items-start justify-between gap-3 rounded-xl border border-dashed p-5 sm:flex-row sm:items-center"
            style={{ borderColor: "var(--color-border-strong)", backgroundColor: "var(--color-surface-base)" }}
          >
            <div className="space-y-1">
              <p className="text-xs font-semibold" style={{ color: "var(--color-text-primary)" }}>{labels.emptyPopularTitle}</p>
              <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{labels.emptyPopularDescription}</p>
            </div>
            <button type="button" data-testid="profile-explore-agents-btn" onClick={onExploreAgents} className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm shrink-0">
              {labels.exploreAgentsCta}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {profile.popularItems.map((item) => {
              const countUnit = item.usageCount === 1 ? labels.usageCountSingular : labels.usageCountPlural;
              return (
                <button
                  key={`${item.itemType}-${item.itemKey}`}
                  type="button"
                  data-testid={`profile-popular-item-${item.itemKey}`}
                  onClick={() => onSelectPopularItem(item.targetRoute)}
                  className="flex items-center justify-between gap-3 rounded-xl border px-4 py-3 text-left transition-colors hover:bg-surface-hover"
                  style={{ borderColor: "var(--color-border-subtle)", backgroundColor: "var(--color-surface-base)" }}
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase"
                        style={{ backgroundColor: "var(--color-badge-cobalt-bg)", color: "var(--color-badge-cobalt-fg)" }}
                      >
                        {labels.itemTypeLabels[item.itemType]}
                      </span>
                      <span className="truncate text-xs font-semibold" style={{ color: "var(--color-text-primary)" }}>{item.title}</span>
                    </div>
                    <p className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>{numFmt.format(item.usageCount)} {countUnit}</p>
                  </div>
                  <OrciaIcon name="chevronRight" size={14} />
                </button>
              );
            })}
          </div>
        )}
      </OrciaDataCard>
    </div>
  );
}
