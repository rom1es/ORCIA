import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";

export type UiProgressiveLlmTierMode =
  | "UNCONFIGURED"
  | "QUICK_TRIAL_SINGLE_FAMILY"
  | "FULL_ORTHOGONAL_AD10";

export interface UiAccostageMilestoneItem {
  readonly index: number;
  readonly key: string;
  readonly title: string;
  readonly completed: boolean;
  readonly targetRoute: string;
}

export interface ProgressiveDay0AccostageLabels {
  readonly bannerTitle: string;
  readonly welcomeWizardTitle?: string;
  readonly step1AdminTitle?: string;
  readonly step2LlmTitle?: string;
  readonly step3SpaceTitle?: string;
  readonly bootstrapTokenLabel?: string;
  readonly bootstrapTokenPlaceholder?: string;
  readonly bootstrapTokenDeniedBanner?: string;
  readonly createFirstAdminCta?: string;
  readonly addFirstModelCta?: string;
  readonly addSecondModelFamilyCta?: string;
  readonly singleFamilyAmberWarning: string;
  readonly dualFamilyAd10UnlockedBadge: string;
  readonly assistantTrialReadyBadge?: string;
  readonly progressLabelPrefix?: string;
  readonly progressFormatTemplate?: string;
  readonly collapseGuideLabel?: string;
  readonly expandGuideLabel?: string;
  readonly milestoneDoneLabel?: string;
  readonly milestoneOpenLabel?: string;
  readonly adminInitializedBadge?: string;
}

export interface ProgressiveDay0AccostageBannerProps {
  readonly completedCount: number;
  readonly totalCount?: number;
  readonly defaultCompact?: boolean;
  readonly orciaEnv?: "local" | "staging" | "production";
  readonly canConfigurePlatform?: boolean;
  readonly adminCreated?: boolean;
  readonly adminDisplayName?: string | null;
  readonly adminEmail?: string | null;
  readonly initialFamilies?: readonly string[];
  readonly milestones: readonly UiAccostageMilestoneItem[];
  readonly labels: ProgressiveDay0AccostageLabels;
  readonly onSubmitFirstAdmin?: (payload: {
    email: string;
    displayName: string;
    bootstrapToken: string;
  }) => boolean;
  readonly onRegisterModelFamily?: (familySlug: string) => void;
  readonly onNavigateMilestone?: (targetRoute: string) => void;
}

export function ProgressiveDay0AccostageBanner({
  completedCount,
  totalCount = 6,
  defaultCompact = false,
  adminCreated = false,
  adminDisplayName,
  adminEmail: serverAdminEmail,
  initialFamilies = [],
  milestones,
  labels,
  onNavigateMilestone,
}: ProgressiveDay0AccostageBannerProps): React.ReactElement {
  const [isCompact, setIsCompact] = useState<boolean>(defaultCompact);

  const effectiveCompletedCount = Math.max(0, Math.min(totalCount, completedCount));
  const isAllCompleted = effectiveCompletedCount >= totalCount;
  const effectiveCompact = isAllCompleted ? isCompact : false;

  useEffect(() => {
    setIsCompact(isAllCompleted ? defaultCompact : false);
  }, [defaultCompact, isAllCompleted]);

  const distinctFamilies = Array.from(
    new Set(initialFamilies.map((f) => f.trim().toLowerCase()).filter(Boolean)),
  );
  const llmTierMode: UiProgressiveLlmTierMode =
    distinctFamilies.length === 0
      ? "UNCONFIGURED"
      : distinctFamilies.length === 1
        ? "QUICK_TRIAL_SINGLE_FAMILY"
        : "FULL_ORTHOGONAL_AD10";

  const progressText = labels.progressFormatTemplate
    ? labels.progressFormatTemplate
        .replace("{completed}", String(effectiveCompletedCount))
        .replace("{total}", String(totalCount))
    : `${labels.progressLabelPrefix ?? ""} ${effectiveCompletedCount}/${totalCount}`.trim();

  return (
    <section
      data-testid="progressive-day0-accostage-banner"
      data-compact={effectiveCompact ? "true" : "false"}
      className="flex flex-col gap-3 rounded border p-3.5"
      style={{
        backgroundColor: "var(--color-bg-surface)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xs font-semibold">{labels.bannerTitle}</h2>
          <span
            data-testid="accostage-progress-pill"
            className="rounded px-2 py-0.5 font-mono text-xs font-bold"
            style={{
              backgroundColor: isAllCompleted
                ? "var(--color-gate-pass-bg)"
                : "var(--color-action-primary-subtle)",
              color: isAllCompleted
                ? "var(--color-gate-pass)"
                : "var(--color-sidebar-active-fg)",
            }}
          >
            {progressText}
          </span>
          {adminCreated &&
            (adminDisplayName || serverAdminEmail) &&
            !milestones.some((m) => m.key === "first-admin" && m.completed) && (
              <span
                className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                  color: "var(--color-text-secondary)",
                }}
              >
                {labels.adminInitializedBadge && <span>{labels.adminInitializedBadge} :</span>}
                <span data-testid="welcome-setup-admin-identity-name" className="font-medium">
                  {adminDisplayName || serverAdminEmail}
                </span>
              </span>
            )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {llmTierMode === "QUICK_TRIAL_SINGLE_FAMILY" && (
            <span
              data-testid="accostage-single-family-amber-badge"
              className="rounded border px-2.5 py-1 text-xs font-medium"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-state-warning)",
                color: "var(--color-state-warning)",
              }}
            >
              {labels.singleFamilyAmberWarning}
            </span>
          )}

          {llmTierMode === "FULL_ORTHOGONAL_AD10" && (
            <span
              data-testid="accostage-dual-family-ad10-badge"
              className="rounded border px-2.5 py-1 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-gate-pass-bg)",
                borderColor: "var(--color-gate-pass)",
                color: "var(--color-gate-pass)",
              }}
            >
              {labels.dualFamilyAd10UnlockedBadge}
            </span>
          )}

          {isAllCompleted && (
            <button
              type="button"
              data-testid="accostage-compact-toggle-btn"
              aria-expanded={!effectiveCompact}
              onClick={() => setIsCompact((prev) => !prev)}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
            >
              <OrciaIcon name={effectiveCompact ? "chevronRight" : "chevronDown"} size={13} />
              <span>
                {effectiveCompact
                  ? (labels.expandGuideLabel ?? "")
                  : (labels.collapseGuideLabel ?? "")}
              </span>
            </button>
          )}
        </div>
      </div>

      {!effectiveCompact && milestones.length > 0 && (
        <div
          data-testid="accostage-milestones-list"
          className="flex flex-col gap-1.5"
        >
          {milestones.map((m) => {
            const detailHint =
              m.key === "first-admin" && m.completed && (adminDisplayName || serverAdminEmail)
                ? (adminDisplayName || serverAdminEmail || "")
                : m.completed
                  ? (labels.milestoneDoneLabel ?? "")
                  : (labels.milestoneOpenLabel ?? "");
            return (
              <button
                key={m.key}
                type="button"
                data-testid={`accostage-milestone-${m.key}`}
                data-completed={m.completed ? "true" : "false"}
                onClick={() => onNavigateMilestone?.(m.targetRoute)}
                className={
                  m.completed
                    ? "grid grid-cols-[minmax(200px,260px)_24px_minmax(0,1fr)] sm:grid-cols-[minmax(220px,280px)_24px_1fr] items-center gap-3 rounded border px-3 py-1.5 text-left text-xs transition-colors bg-[var(--color-gate-pass-bg)] border-[var(--color-gate-pass)] text-[var(--color-gate-pass)]"
                    : "grid grid-cols-[minmax(200px,260px)_24px_minmax(0,1fr)] sm:grid-cols-[minmax(220px,280px)_24px_1fr] items-center gap-3 rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] hover:border-[var(--color-action-primary)] px-3 py-1.5 text-left text-xs transition-colors"
                }
              >
                <span className="truncate font-medium leading-snug">{m.title}</span>
                <span className="flex items-center justify-center">
                  <OrciaIcon
                    name={m.completed ? "check" : "arrowRight"}
                    size={14}
                    className="shrink-0"
                  />
                </span>
                <span
                  data-testid={
                    m.key === "first-admin" && m.completed
                      ? "welcome-setup-admin-identity-name"
                      : undefined
                  }
                  className="truncate text-[11px] opacity-80"
                >
                  {detailHint}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
